"""案件管理服务模块.

提供案件 CRUD 操作，包含权限验证和异常处理。
所有数据库操作均使用异步 API。
"""

from __future__ import annotations

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.case import Case, CaseStatus
from app.models.user import User, UserRole
from app.schemas.case import CaseCreate, CaseUpdate, PaginatedResponse


_SORTABLE_FIELDS: frozenset[str] = frozenset(
    {"id", "title", "status", "created_by", "created_at", "updated_at"}
)
_VALID_SORT_ORDERS: frozenset[str] = frozenset({"asc", "desc"})
_MAX_PAGE_SIZE: int = 100
_DEFAULT_PAGE_SIZE: int = 20


def _validate_pagination_params(
    page: int,
    page_size: int,
    sort_by: str,
    sort_order: str,
) -> None:
    """验证分页和排序参数.

    Args:
        page: 页码（从1开始）
        page_size: 每页条数
        sort_by: 排序字段名
        sort_order: 排序方向

    Raises:
        HTTPException 422: 参数无效
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="页码必须大于等于1",
        )
    if page_size < 1 or page_size > _MAX_PAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"每页条数必须在1到{_MAX_PAGE_SIZE}之间",
        )
    if sort_by not in _SORTABLE_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的排序字段'{sort_by}'，允许的字段: {sorted(_SORTABLE_FIELDS)}",
        )
    if sort_order not in _VALID_SORT_ORDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的排序方向'{sort_order}'，仅支持'asc'和'desc'",
        )


def _build_sort_column(sort_by: str, sort_order: str):  # noqa: ANN202
    """构建排序表达式，安全地规避SQL注入.

    Args:
        sort_by: 已验证的排序字段名
        sort_order: 已验证的排序方向

    Returns:
        排序表达式
    """
    column = getattr(Case, sort_by)
    return column.desc() if sort_order == "desc" else column.asc()


async def get_cases(  # noqa: PLR0913
    db: AsyncSession,
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    status_filter: CaseStatus | None = None,
) -> PaginatedResponse[Case]:
    """分页查询案件列表，支持排序和总数统计.

    使用单次数据库查询同时获取 count 和 items，
    并通过已验证的字段名拼接安全的排序表达式。

    Args:
        db: 异步数据库会话
        page: 页码（从1开始）
        page_size: 每页条数（1-100）
        sort_by: 排序字段名
        sort_order: 排序方向（asc/desc）
        status_filter: 状态筛选条件

    Returns:
        PaginatedResponse[Case]: 包含 items、total、total_pages 等字段的分页响应

    Raises:
        HTTPException 422: 分页/排序参数无效

    Example:
        >>> result = await get_cases(db, page=1, page_size=10,
        ...                          sort_by="created_at", sort_order="desc")
        >>> len(result.items)
        10
        >>> result.total_pages
        5
    """
    _validate_pagination_params(page, page_size, sort_by, sort_order)

    base_stmt = select(Case).options(selectinload(Case.creator))
    if status_filter:
        base_stmt = base_stmt.where(Case.status == status_filter)

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    count_result = await db.execute(count_stmt)
    total: int = count_result.scalar_one()

    sort_expr = _build_sort_column(sort_by, sort_order)
    offset = (page - 1) * page_size
    items_stmt = base_stmt.order_by(sort_expr).offset(offset).limit(page_size)
    items_result = await db.execute(items_stmt)
    items: list[Case] = list(items_result.scalars().all())

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_case(db: AsyncSession, case_id: int) -> Case | None:
    """根据 ID 查询单个案件.

    Args:
        db: 异步数据库会话
        case_id: 案件 ID

    Returns:
        Case | None: 案件记录，不存在返回 None
    """
    result = await db.execute(
        select(Case).options(selectinload(Case.creator)).where(Case.id == case_id)
    )
    return result.scalar_one_or_none()


async def create_case(
    db: AsyncSession,
    case_data: CaseCreate,
    user: User | None = None,
) -> Case:
    """创建新案件.

    包含事务管理和回滚机制。

    Args:
        db: 异步数据库会话
        case_data: 案件创建数据
        user: 当前用户（可选）

    Returns:
        Case: 新创建的案件记录

    Raises:
        HTTPException 500: 数据库操作失败
    """
    db_case = Case(
        title=case_data.title,
        description=case_data.description,
        case_text=case_data.case_text,
        status=case_data.status or CaseStatus.pending,
        created_by=user.id if user else None,
    )
    try:
        db.add(db_case)
        await db.commit()
        await db.refresh(db_case)
        user_id = user.id if user else "anonymous"
        logger.info(
            "Case created: id={}, title={}, user={}",
            db_case.id,
            db_case.title,
            user_id,
        )
        return db_case
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create case: error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建案件失败，请稍后重试",
        ) from e


async def update_case(
    db: AsyncSession,
    case_id: int,
    case_data: CaseUpdate,
    user: User | None = None,
) -> Case:
    """更新案件信息.

    仅允许案件创建者或管理员进行更新。

    Args:
        db: 异步数据库会话
        case_id: 案件 ID
        case_data: 更新数据
        user: 当前用户

    Returns:
        Case: 更新后的案件记录

    Raises:
        HTTPException 401: 未登录
        HTTPException 403: 无权限
        HTTPException 404: 案件不存在
        HTTPException 500: 数据库操作失败
    """
    db_case: Case | None = await get_case(db, case_id)
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="案件不存在",
        )
    if user:
        is_creator: bool = db_case.created_by == user.id
        is_admin: bool = user.role == UserRole.admin
        if not is_creator and not is_admin:
            logger.warning(
                "权限不足: user={} 尝试更新 case={}",
                user.id,
                case_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限更新此案件，仅案件创建者或管理员可以更新",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要登录后才能更新案件",
        )

    update_data: dict = case_data.model_dump(exclude_unset=True)
    if not update_data:
        logger.info(f"案件更新无变化: id={case_id}")
        return db_case

    try:
        for key, value in update_data.items():
            setattr(db_case, key, value)
        await db.commit()
        await db.refresh(db_case)
        logger.info(f"案件已更新: id={db_case.id}, user={user.id}")
        return db_case
    except Exception as e:
        await db.rollback()
        logger.error(f"更新案件失败: id={case_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新案件失败，请稍后重试",
        ) from e


async def delete_case(
    db: AsyncSession,
    case_id: int,
    user: User | None = None,
) -> bool:
    """删除案件.

    仅允许案件创建者或管理员进行删除。

    Args:
        db: 异步数据库会话
        case_id: 案件 ID
        user: 当前用户

    Returns:
        bool: 删除成功返回 True

    Raises:
        HTTPException 401: 未登录
        HTTPException 403: 无权限
        HTTPException 404: 案件不存在
        HTTPException 500: 数据库操作失败
    """
    db_case: Case | None = await get_case(db, case_id)
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="案件不存在",
        )

    if user:
        is_creator: bool = db_case.created_by == user.id
        is_admin: bool = user.role == UserRole.admin
        if not is_creator and not is_admin:
            logger.warning(
                "权限不足: user={} 尝试删除 case={}",
                user.id,
                case_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限删除此案件，仅案件创建者或管理员可以删除",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要登录后才能删除案件",
        )

    try:
        await db.delete(db_case)
        await db.commit()
        user_id = user.id if user else "anonymous"
        logger.info(f"案件已删除: id={case_id}, user={user_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"删除案件失败: id={case_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除案件失败，请稍后重试",
        ) from e
