"""案件管理服务模块.

提供案件 CRUD 操作，包含权限验证和异常处理。
所有数据库操作均使用异步 API。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: from fastapi
from fastapi import HTTPException, status
# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import func, select
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession
# 导入模块: from sqlalchemy.orm
from sqlalchemy.orm import selectinload

# 导入模块: from app.models.case
from app.models.case import Case, CaseStatus
# 导入模块: from app.models.user
from app.models.user import User, UserRole
# 导入模块: from app.schemas.case
from app.schemas.case import CaseCreate, CaseUpdate, PaginatedResponse


_SORTABLE_FIELDS: frozenset[str] = frozenset(
    {"id", "title", "status", "created_by", "created_at", "updated_at"}
)
_VALID_SORT_ORDERS: frozenset[str] = frozenset({"asc", "desc"})
_MAX_PAGE_SIZE: int = 100
_DEFAULT_PAGE_SIZE: int = 20


def _validate_pagination_params(
    # 函数 _validate_pagination_params 的初始化逻辑
    page: int,


    # 执行 _validate_pagination_params 函数的核心逻辑
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
    # 条件判断：处理业务逻辑
    if page < 1:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            # 初始化变量 detail
            detail="页码必须    # 条件判断：处理业务逻辑
大于等于1",
        )
    # 条件判断: 检查 page_size < 1 or page_size > _MAX_PAGE_S
    if page_size < 1 or page_size > _MAX_PAGE_SIZE:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            # 初始化变量 detail
            detail=f"每页条数    # 条件判断：处理业务逻辑
必须在1到{_MAX_PAGE_SIZE}之间",
        )
    # 条件判断: 检查 sort_by not in _SORTABLE_FIELDS
    if sort_by not in _SORTABLE_FIELDS:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            # 初始化变量 detail
            detail=f"无效的排序字段'{so    # 条件判断：处理业务逻辑
rt_by}'，允许的字段: {sorted(_SORTABLE_FIELDS)}",
        )
    # 条件判断: 检查 sort_order not in _VALID_SORT_ORDERS
    if sort_order not in _VALID_SORT_ORDERS:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            # 初始化变量 detail
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
    # 初始化变量 column
    column = getattr(Case, sort_by)
    # 返回处理结果
    return column.desc() if sort_order == "desc" else column.asc()


async def get_cases(  # noqa: PLR0913
    # 函数 get_cases 的初始化逻辑
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
        # 异步等待操作完成
        >>> result = await get_cases(db, page=1, page_size=10,
        ...                          sort_by="created_at", sort_order="desc")
        >>> len(result.items)
        10
        >>> result.total_pages
        5
    """
    _validate_pagination_params(page, page_size, sort_by, sort_o    # 条件判断：处理业务逻辑
rder)

    # 初始化变量 base_stmt
    base_stmt = select(Case).options(selectinload(Case.creator))
    # 条件判断: 检查 status_filter
    if status_filter:
        # 初始化变量 base_stmt
        base_stmt = base_stmt.where(Case.status == status_filter)

    # 初始化变量 count_stmt
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    # 初始化变量 count_result
    count_result = await db.execute(count_stmt)
    total: int = count_result.scalar_one()

    # 初始化变量 sort_expr
    sort_expr = _build_sort_column(sort_by, sort_order)
    # 初始化变量 offset
    offset = (page - 1) * page_size
    # 初始化变量 items_stmt
    items_stmt = base_stmt.order_by(sort_expr).offset(offset).limit(page_size)
    # 初始化变量 items_result
    items_result = await db.execute(items_stmt)
    items: list[Case] = list(items_result.scalars().all())

    # 返回处理结果
    return PaginatedResponse(
        # 初始化变量 items
        items=items,
        # 初始化变量 total
        total=total,
        # 初始化变量 page
        page=page,
        # 初始化变量 page_size
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
    # 初始化变量 result
    result = await db.execute(
        select(Case).options(selectinload(Case.creator)).where(Case.id == case_id)
    )
    # 返回处理结果
    return result.scalar_one_or_none()


async def create_case(
    # 函数 create_case 的初始化逻辑
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
    # 初始化变量 db_case
    db_case = Case(
        # 初始化变量 title
        title=case_data.title,
        # 初始化变量 description
        description=case_data.description,
        # 初始化变量 case_text
        case_text=case_data.case_text,
        # 初始化变量 status
        status=case_data.status or CaseStatus.pending,
        # 初始化变量 created_by
        created_by=user.id if user else None,
    )
    # 异常处理：处理业务逻辑
    try:
        db.add(db_case)
        # 异步等待操作完成
        await db.commit()
        # 异步等待操作完成
        await db.refresh(db_case)
        # 初始化变量 user_id
        user_id = user.id if user else "anonymous"
        # 记录日志信息
        logger.info(
            "Case created: id={}, title={}, user={}",
            db_case.id,
            db_case.title,
            user_id,
        )
        # 返回处理结果
        return db_case
    # 捕获异常：处理业务逻辑
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"Failed to create case: error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # 初始化变量 detail
            detail="创建案件失败，请稍后重试",
        ) from e


async def update_case(
    # 函数 update_case 的初始化逻辑
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
            # 条件判断：处理业务逻辑
HTTPException 500: 数据库操作失败
    """
    # 异步等待操作完成
    db_case: Case | None = await get_case(db, case_id)
    # 条件判断: 检查 not db_case
    if not db_case:
        ra    # 条件判断：处理业务逻辑
ise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail="案件不存在",
               # 条件判断：处理业务逻辑
 )
    # 条件判断: 检查 user
    if user:
        is_creator: bool = db_case.created_by == user.id
        is_admin: bool = user.role == UserRole.admin
        # 条件判断: 检查 not is_creator and not is_admin
        if not is_creator and not is_admin:
            # 记录日志信息
            logger.warning(
                "权限不足: user={} 尝试更新 case={}",
                user.id,
                case_id,
            )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_403_FORBIDDEN,
                # 初始化变量 detail
                detail="无权限更新此案件，仅案件创建者或管理员可以更新",
            )
    # 其他情况的默认处理
    else:
        # 抛出异常，处理错误情况
        raise HTTPException(
            stat    # 条件判断：处理业务逻辑
us_code=status.HTTP_401_UNAUTHORIZED,
            # 初始化变量 detail
            detail="需要登录后才能更新案件",
        )

    update_data: dict = case_data.model_dump(exclude_unset=True)
    # 条件判断: 检查 not update_data
    if not update_data:
        # 记录日志信息
        logger.info(f"案件更新无变化: id={case_id}")
     
    # 异常处理：处理业务逻辑
   return db_case

    # 尝试执行可能抛出异常的代码
    try:
        # 循环遍历：处理业务逻辑
        for key, value in update_data.items():
            setattr(db_case, key, value)
        # 异步等待操作完成
        await db.commit()
        # 异步等待操作完成
        await db.refresh(db_case)
        # 记录日志信息
        logger.info(f"案件已更新: id={db_case.id}, user={user.id}")
         # 捕获异常：处理业务逻辑
   return db_case
    # 捕获并处理异常
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"更新案件失败: id={case_id}, error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # 初始化变量 detail
            detail="更新案件失败，请稍后重试",
        ) from e


async def delete_case(
    # 函数 delete_case 的初始化逻辑
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
        HTTPException 401:     # 条件判断：处理业务逻辑
未登录
        HTTPException 403: 无权限
        HTTPException 404: 案件不存在
        HTTPException 500: 数据库操作失败
    """
    db_ca
    # 条件判断：处理业务逻辑
se: Case | None = await get_case(db, case_id)
    # 条件判断: 检查 not db_case
    if not db_case:
        # 抛出异常，处理错误情况
        raise HTTPException(
                  # 条件判断：处理业务逻辑
  status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail="案件不存在",
        )

    # 条件判断: 检查 user
    if user:
        is_creator: bool = db_case.created_by == user.id
        is_admin: bool = user.role == UserRole.admin
        # 条件判断: 检查 not is_creator and not is_admin
        if not is_creator and not is_admin:
            # 记录日志信息
            logger.warning(
                "权限不足: user={} 尝试删除 case={}",
                user.id,
                case_id,
            )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_403_FORBIDDEN,
                # 初始化变量 detail
                detail="无权限删除此案件，仅案件创建者或管理员可以删除",
            )
    # 其他情况的默认处理
    else:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_401_UNAUTHORIZED,
       
    # 异常处理：处理业务逻辑
     detail="需要登录后才能删除案件",
        )

    # 尝试执行可能抛出异常的代码
    try:
        # 异步等待操作完成
        await db.delete(db_case)
        # 异步等待操作完成
        await db.commit()
        # 初始化变量 user_id
        user_id = user.id if user else "anonymous"
        # 记录日志信息
        logger.info(f"案件已删除: id={case_id}, u    # 捕获异常：处理业务逻辑
ser={user_id}")
        # 返回处理结果
        return True
    # 捕获并处理异常
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"删除案件失败: id={case_id}, error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # 初始化变量 detail
            detail="删除案件失败，请稍后重试",
        ) from e
