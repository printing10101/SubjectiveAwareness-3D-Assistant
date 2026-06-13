"""分析路由模块.

提供案件分析 API 端点，支持直接文本分析和缓存机制。
所有数据库操作均使用异步 API。
"""

import json
from datetime import UTC, datetime

import sentry_sdk
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import select

from app.database import get_async_db_session
from app.models.analysis import Analysis
from app.models.case import Case
from app.models.user import User, UserRole
from app.schemas.analysis import AnalyzeRequest
from app.services.pipeline import analyze_pipeline
from app.types.analysis_v2 import AnalysisResultV2
from app.utils.auth import optional_current_user_dep
from app.utils.cache import cache_manager
from app.utils.common import generate_cache_key
from app.utils.rate_limit import get_analyze_rate_limit, limiter


router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze")
@limiter.limit(get_analyze_rate_limit)
async def analyze_case(
    request: Request,  # noqa: ARG001
    analyze_request: AnalyzeRequest,
    current_user: User | None = optional_current_user_dep,
) -> AnalysisResultV2:
    """执行案件分析.

    接收案件文本，调用分析管道进行智能分析。
    支持缓存机制，重复分析直接返回缓存结果。

    Args:
        request: HTTP 请求对象（由 FastAPI 自动注入）
        analyze_request: 分析请求体
        current_user: 当前用户（可选认证）

    Returns:
        AnalysisResult: 分析结果字典

    Raises:
        HTTPException 502: 分析服务不可用
        HTTPException 429: 请求过于频繁（由 slowapi 按角色差异化限流处理）
            - 匿名用户: 基于IP限流，配额由 AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS 决定
            - 普通用户: 基于用户ID限流，配额由 AnalysisConfig.RATE_LIMIT_ANALYZE_USER 决定
            - 管理员: 基于用户ID限流，配额由 AnalysisConfig.RATE_LIMIT_ANALYZE_ADMIN 决定
    """
    case_text: str = analyze_request.case_text
    # Pydantic 在 use_enum_values=True 下，analyze_request.mode 已是字符串
    # （如 "auto"/"single"/"multi"），不能再访问 .value，这里统一转 str 兜底，
    # 兼容 AnalysisMode 枚举和裸字符串两种情况。
    mode_value: str = (
        analyze_request.mode.value
        if hasattr(analyze_request.mode, "value")
        else str(analyze_request.mode)
    )
    case_id: int | None = analyze_request.case_id

    # 为 Sentry 提供丰富的业务上下文，便于错误定位
    sentry_sdk.set_context(
        "analysis_request",
        {
            "text_length": len(case_text),
            "mode": mode_value,
            "case_id": case_id,
            "has_existing_case": case_id is not None,
        },
    )
    sentry_sdk.set_tag("analysis_mode", mode_value)
    if current_user:
        sentry_sdk.set_user(
            {
                "id": str(current_user.id),
                "username": current_user.username,
                "role": current_user.role.value
                if hasattr(current_user.role, "value")
                else str(current_user.role),
            },
        )
    else:
        sentry_sdk.set_user(None)

    sentry_sdk.add_breadcrumb(
        category="business",
        message="analyze_request_received",
        level="info",
        data={
            "text_length": len(case_text),
            "mode": mode_value,
            "case_id": case_id,
            "user": current_user.username if current_user else "anonymous",
        },
    )

    logger.info(
        f"收到分析请求 (文本长度: {len(case_text)}, "
        f"用户: {current_user.username if current_user else '匿名'})"
    )

    if case_id:
        async with get_async_db_session() as db:
            result = await db.execute(select(Case).where(Case.id == case_id))
            db_case = result.scalar_one_or_none()

            if not db_case:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error_code": "CASE_NOT_FOUND",
                        "message": "Case not found",
                    },
                )

            if not current_user:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error_code": "PERMISSION_DENIED",
                        "message": "Permission denied to access this case",
                    },
                )

            is_creator = db_case.created_by == current_user.id
            is_admin = current_user.role == UserRole.admin
            if not is_creator and not is_admin:
                logger.warning(
                    f"权限不足: user={current_user.id} "
                    f"尝试分析 case={case_id}"
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error_code": "PERMISSION_DENIED",
                        "message": "Permission denied to access this case",
                    },
                )

    cache_key: str = generate_cache_key(case_text, mode_value)
    cached: AnalysisResult | None = cache_manager.get(cache_key)
    if cached:
        logger.info("分析结果来自缓存")
        return cached

    try:
        result: AnalysisResult = await analyze_pipeline(case_text, mode=mode_value)
    except Exception as e:
        logger.error(f"分析管道失败: {e}")
        raise HTTPException(status_code=502, detail="分析服务暂时不可用") from e

    if case_id:
        async with get_async_db_session() as db:
            # 事务由 get_async_db_session 上下文管理器统一管理：
            #   - 正常退出 → 自动 commit
            #   - 异常发生 → 自动 rollback
            db_analysis = Analysis(
                case_id=case_id,
                result_json=json.dumps(result, ensure_ascii=False),
                # mode_value 已是字符串，存为字符串与结果保持一致
                mode=mode_value,
                created_at=datetime.now(UTC),
            )
            db.add(db_analysis)
            # 不手动调用 db.commit()，避免与上下文管理器的自动 commit 形成双重提交

    cache_manager.set(cache_key, result)

    return result
