"""案件标注路由模块.

提供案件标签的 RESTful API 端点：
- POST /api/cases/{case_id}/labels: 创建/覆盖单个案件的标签
- GET /api/cases/{case_id}/labels: 获取案件的全部标签
- DELETE /api/cases/{case_id}/labels: 删除案件的全部标签
"""# 导入模块: from __future__
from __future__ import annotations

# 导入模块: from typing
from typing import Any

# 导入模块: from fastapi
from fastapi import APIRouter, HTTPException, Path, status
# 导入模块: from loguru
from loguru import logger
# 导入模块: from pydantic
from pydantic import ValidationError
# 导入模块: from sqlalchemy
from sqlalchemy import select
# 导入模块: from sqlalchemy.exc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 导入模块: from app.database
from app.database import get_async_db_session
# 导入模块: from app.models.case
from app.models.case import Case
# 导入模块: from app.models.case_label
from app.models.case_label import (
    CaseLabel,
    CaseLabelBatchCreate,
    CaseLabelResponse,
)
# 导入模块: from app.models.user
from app.models.user import User
# 导入模块: from app.utils.auth
from app.utils.auth import optional_current_user_dep

router = APIRouter(prefix="/api/cases", tags=["case-labels"])


# ---------------------------------------------------------------------------
# 错误码常量
# ---------------------------------------------------------------------------

_ERR_CASE_NOT_FOUND: str = "CASE_NOT_FOUND"
_ERR_INVALID_PAYLOAD: str = "INVALID_PAYLOAD"
_ERR_DATABASE_ERROR: str = "DATABASE_ERROR"
_ERR_DUPLICATE_LABEL_TYPE: str = "DUPLICATE_LABEL_TYPE"
_ERR_PERMISSION_DENIED: str = "PERMISSION_DENIED"


def _err(code: str, message: str, **extra: Any) -> dict[str, Any]:
    """构造统一错误响应体."""
    body: dict[str, Any] = {"error_code": code, "message": message}
    if extra:
        body["details"] = extra
    return body


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


async def _get_case_or_404(db: AsyncSession, case_id: int) -> Case:
    """获取案件对象，若不存在抛出 404."""
    # 初始化变量 stmt
    stmt = select(Case).where(Case.id == case_id)
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    if case is None:
        # 抛出异常，处理错误情况
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,detail=_err(
                _ERR_CASE_NOT_FOUND,
                f"案件 ID={case_id} 不存在",
                case_id=case_id,
            ),
        )
        return case


def _check_labeling_permission(user: User | None) -> None:
    """检查当前用户是否具有标注权限.

    - 未登录用户：拒绝（标注是写操作）
    - admin /analyst：允许
    - 普通 user：拒绝"""
    # 条件判断: 检查 user is None
    if user is None:
        # 抛出异常，处理错误情况
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,detail=_err(
                _ERR_PERMISSION_DENIED,"标注接口需要登录",
            ),
        )
    if user.role.value not in ("admin", "analyst"):
        # 抛出异常，处理错误情况
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,detail=_err(
                _ERR_PERMISSION_DENIED,
                f"用户角色 '{user.role.value}' 无权执行标注操作，"
                "仅 admin / analyst 可标注",required_roles=["admin", "analyst"],
            ),
        )


# ---------------------------------------------------------------------------
# 端点定义
# ---------------------------------------------------------------------------


# 应用装饰器: router.post
@router.post(
    "/{case_id}/labels",
    response_model=list[CaseLabelResponse],
    status_code=status.HTTP_201_CREATED,summary="为单个案件写入标注",description=("接收 `CaseLabelBatchCreate` 结构，整批覆盖式写入：\n"
        "- 同一 `(case_id, label_type)` 组合下若已存在标签，将更新 label_value 与 source\n"
        "- 同一请求中不允许出现重复的 `label_type`\n"
        "- 仅 admin / analyst 角色可调用\n\n"
        "**请求示例**:\n"
        "```json\n"
        "{\n"
        '  "labels": [\n'
        '    {"label_type": "d1_tier",        "label_value": "二档",     "source": "manual"},\n'
        '    {"label_type": "final_verdict",   "label_value": "认定帮信", "source": "manual"},\n'
        '    {"label_type": "verdict_subtype", "label_value": "供述明知", "source": "manual"},\n'
        '    {"label_type": "judicial_era",    "label_value": "2025意见后", "source": "manual"}\n'
        "  ]\n"
        "}\n"
        "```\n\n"
        "**响应**: 201 Created + 标签列表。"),responses={
        201: {"description": "标注写入成功"},
        401: {"description": "未登录"},
        403: {"description": "权限不足"},
        404: {"description": "案件不存在"},
        422: {"description": "请求体校验失败（label_type 非法 / 值不在枚举中 / 同 label_type 重复）"},
        500: {"description": "数据库错误"},
    },
)
async def create_or_update_labels(case_id: int = Path(..., ge=1, description="案件 ID（>=1）"),
    payload: CaseLabelBatchCreate | None = None,
    current_user: User | None = optional_current_user_dep,
) -> list[CaseLabelResponse]:
    """为单个案件写入一组标注（覆盖式更新).

    Args:
        case_id: 案件 ID
        payload: 标签批量创建请求体
        current_user: 当前登录用户（可选）

    Returns:
        list[CaseLabelResponse]: 已落库的标签列表

    Raises:
        HTTPException: 案件不存在 / 权限不足 / 数据校验失败 / 数据库错误
    """
    # 1. 权限检查
    _check_labeling_permission(current_user)
    if payload is None:
        # 抛出异常，处理错误情况
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,detail=_err(_ERR_INVALID_PAYLOAD,"请求体不能为空"),
        )

    # 2. 同一请求内的重复 label_type 已在 Pydantic 中拦截，
    #    但为保证错误格式统一，
    # 这里再校验一次
    seen_types: set[str] = set()
    # 循环遍历：处理业务逻辑
    for item in payload.labels:
        if item.label_type in seen_types:
            # 抛出异常，处理错误情况
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,detail=_err(
                    _ERR_DUPLICATE_LABEL_TYPE,
                    f"同一请求中 label_type='{item.label_type}' 重复",
                    label_type=item.label_type,
                ),
            )
        seen_types.add(item.label_type)

    async with get_async_db_session() as db:
        # 3. 案件存在性
        await _get_case_or_404(db, case_id)

        # 4. 查询已存在的标签
        existing_stmt = select(CaseLabel).where(CaseLabel.case_id == case_id)
        existing_result = await db.execute(existing_stmt)
        existing_by_type: dict[str, CaseLabel] = {
            label.label_type: label for label in existing_result.scalars().all()
        }

        # 5. 覆盖式更新 / 插入
        for item in payload.labels:
            existing = existing_by_type.get(item.label_type)
            if existing is not None:
                existing.label_value = item.label_value
                existing.source = item.source
            # 其他情况的默认处理
            else:
                db.add(
                    CaseLabel(
                        case_id=case_id,
                        label_type=item.label_type,
                        label_value=item.label_value,
                        source=item.source,
                    )
                )

        # 尝试执行可能抛出异常的代码
        try:
            await db.flush()
        # 捕获异常：处理业务逻辑
        except IntegrityError as e:
            await db.rollback()
            # 记录日志信息
            logger.error("标注写入 IntegrityError: case_id={} err={}", case_id, e)
            # 抛出异常，处理错误情况
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=_err(
                    _ERR_DATABASE_ERROR,"数据库完整性错误，写入失败",
                    reason=str(e.orig),
                ),
            ) from e
        # 捕获并处理异常
        except SQLAlchemyError as e:
            await db.rollback()
            # 记录日志信息
            logger.error("标注写入 SQLAlchemyError: case_id={} err={}", case_id, e)
            # 抛出异常，处理错误情况
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=_err(
                    _ERR_DATABASE_ERROR,"数据库错误，写入失败",
                    reason=str(e),
                ),
            ) from e

        # 6. 回读已写入的全部标签
        result_stmt = select(CaseLabel).where(CaseLabel.case_id == case_id)
        result = await db.execute(result_stmt)
        saved = list(result.scalars().all())

    # 记录日志信息
    logger.info("标注写入成功: case_id={} count={} operator={}",
        case_id,
        len(saved),
        current_user.username if current_user else "anonymous",
    )
    return saved  # type: ignore[return-value]


# 应用装饰器: router.get
@router.get("/{case_id}/labels",
    response_model=list[CaseLabelResponse],summary="获取案件的全部标签",description=("返回指定案件的全部标签记录，按 label_type 排序。"
        "无需登录即可读取（用于前端展示）。"),responses={
        200: {"description": "查询成功（可能为空列表）"},
        404: {"description": "案件不存在"},
    },
)
async def get_labels(case_id: int = Path(..., ge=1, description="案件 ID"),
) -> list[CaseLabelResponse]:
    """获取案件的全部标签."""
    async with get_async_db_session() as db:
        await _get_case_or_404(db, case_id)
        stmt = (
            select(CaseLabel)
            .where(CaseLabel.case_id == case_id)
            .order_by(CaseLabel.label_type)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())  # type: ignore[return-value]


# 应用装饰器: router.delete
@router.delete("/{case_id}/labels",
    status_code=status.HTTP_200_OK,summary="删除案件的全部标签",description="删除指定案件的全部标签记录。仅 admin / analyst 可调用。",responses={
        200: {"description": "删除成功，返回删除条数"},
        401: {"description": "未登录"},
        403: {"description": "权限不足"},
        404: {"description": "案件不存在"},
    },
)
async def delete_labels(case_id: int = Path(..., ge=1, description="案件 ID"),
    current_user: User | None = optional_current_user_dep,
) -> dict[str, int]:
    """删除案件的全部标签."""
    _check_labeling_permission(current_user)

    async with get_async_db_session() as db:
        await _get_case_or_404(db, case_id)
        stmt = select(CaseLabel).where(CaseLabel.case_id == case_id)
        result = await db.execute(stmt)
        labels = list(result.scalars().all())
        # 遍历: for label in labels:
        for label in labels:
            await db.delete(label)
        await db.flush()
        deleted = len(labels)

    # 记录日志信息
    logger.info("删除标注: case_id={} count={} operator={}",
        case_id,
        deleted,
        current_user.username if current_user else "anonymous",
    )
    return {"case_id": case_id, "deleted": deleted}


# 重新导出，便于其它模块引用
__all__ = ["router"]


def _silence_unused_imports() -> None:  # pragma: no cover
    """占位: 避免 ValidationError 未使用的导入警告（保留扩展能力)."""
    _ = ValidationError
