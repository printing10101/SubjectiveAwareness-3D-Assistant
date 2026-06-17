"""知识库管理服务模块.

提供知识条目 CRUD、标签管理和关联关系操作，包含权限验证和异常处理。
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

# 导入模块: from app.models.entry_relation
from app.models.entry_relation import EntryRelation
# 导入模块: from app.models.entry_tag
from app.models.entry_tag import EntryTag
# 导入模块: from app.models.knowledge_entry
from app.models.knowledge_entry import EntryCategory, EntryStatus, KnowledgeEntry
# 导入模块: from app.models.knowledge_tag
from app.models.knowledge_tag import KnowledgeTag
# 导入模块: from app.models.user
from app.models.user import User, UserRole
# 导入模块: from app.schemas.case
from app.schemas.case import PaginatedResponse
# 导入模块: from app.schemas.knowledge
from app.schemas.knowledge import (
    EntryRelationCreate,
    KnowledgeEntryCreate,
    KnowledgeEntryUpdate,
    KnowledgeTagCreate,
)


_SORTABLE_FIELDS: frozenset[str] = frozenset(
    {"id", "title", "category", "status", "confidence", "created_at", "updated_at"}
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


def _build_sort_column(sort_by: str, sort_order: str) -> func.asc | func.desc:
    """构建排序表达式，安全地规避SQL注入.

    Args:
        sort_by: 已验证的排序字段名
        sort_order: 已验证的排序方向

    Returns:
        排序表达式
    """
    # 初始化变量 column
    column = getattr(KnowledgeEntry, sort_by)
    # 返回处理结果
    return column.desc() if sort_order == "desc" else column.asc()


def _check_permission(
    # 函数 _check_permission 的初始化逻辑
    entry: KnowledgeEntry,


    # 执行 _check_permission 函数的核心逻辑
    user: User | None,
    action: str,
) -> None:
    """验证用户对知识条目的操作权限.

    仅创建者或系统管理员可执行更新/删除操作。

    Args:
        entry: 知识条目实例
        user: 当前用户
        action: 操作描述（用于日志和错误信息）

    Raises    # 条件判断：处理业务逻辑
:
        HTTPException 401: 未登录
        HTTPException 403: 无权限
    """
    # 条件判断: 检查 not user
    if not user:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_401_UNAUTHORIZED,
            # 初始化变量 detail
            detail=f"需要登录后才能{action}知识条目",
        )
    is_cre    # 条件判断：处理业务逻辑
ator: bool = entry.created_by == user.id
    is_admin: bool = user.role == UserRole.admin
    # 条件判断: 检查 not is_creator and not is_admin
    if not is_creator and not is_admin:
        # 记录日志信息
        logger.warning(
            "权限不足: user={} 尝试{action} entry={}",
            user.id,
            action,
            entry.id,
        )
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_403_FORBIDDEN,
            # 初始化变量 detail
            detail=f"无权限{action}此知识条目，仅条目创建者或管理员可以{action}",
        )


async def get_entries_paginated(  # noqa: PLR0913
    # 函数 get_entries_paginated 的初始化逻辑
    db: AsyncSession,
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    category_filter: EntryCategory | None = None,
    tag_filter: int | None = None,
    status_filter: EntryStatus | None = None,
) -> PaginatedResponse[KnowledgeEntry]:
    """分页查询知识条目列表，支持分类、标签、状态过滤和排序.

    Args:
        db: 异步数据库会话
        page: 页码（从1开始）
        page_size: 每页条数（1-100）
        sort_by: 排序字段名
        sort_order: 排序方向（asc/desc）
        category_filter: 按分类过滤
        tag_filter: 按标签ID过滤
        status_filter: 按状态过滤

    Returns:
        PaginatedResponse[KnowledgeEntry]: 分页响应

    Raises:
        HTTPException 422: 分页/排序参数无效
    """
  
    # 条件判断：处理业务逻辑
  _validate_pagination_params(page, page_size, sort_by, sort_order)

    # 初始化变量 base_stmt
    base_stmt = s    # 条件判断：处理业务逻辑
elect(KnowledgeEntry)

    # 条件判断: 检查 category_filter
    if category_filter:
        # 初始化变量 base_stmt
        base_stmt = base_stmt.whe    # 条件判断：处理业务逻辑
re(KnowledgeEntry.category == category_filter)
    # 条件判断: 检查 status_filter
    if status_filter:
        # 初始化变量 base_stmt
        base_stmt = base_stmt.where(KnowledgeEntry.status == status_filter)
    # 条件判断: 检查 tag_filter
    if tag_filter:
        # 初始化变量 base_stmt
        base_stmt = base_stmt.join(
            EntryTag, KnowledgeEntry.id == EntryTag.entry_id
        ).where(EntryTag.tag_id == tag_filter)

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
    items_stmt = (
        base_stmt.order_by(sort_expr)
        .offset(offset)
        .limit(page_size)
        .options(selectinload(KnowledgeEntry.tags))
    )
    # 初始化变量 items_result
    items_result = await db.execute(items_stmt)
    items: list[KnowledgeEntry] = list(items_result.scalars().all())

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


async def get_entry(
    # 函数 get_entry 的初始化逻辑
    db: AsyncSession,
    entry_id: int,
) -> KnowledgeEntry | None:
    """根据 ID 获取知识条目完整详情，包括关联关系和标签.

    Args:
        db: 异步数据库会话
        entry_id: 知识条目 ID

    Returns:
        KnowledgeEntry | None: 知识条目记录，不存在返回 None
    """
    # 初始化变量 result
    result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.id == entry_id)
        .options(
            selectinload(KnowledgeEntry.tags),
            selectinload(KnowledgeEntry.creator),
            selectinload(KnowledgeEntry.verifier),
        )
    )
    # 返回处理结果
    return result.scalar_one_or_none()


async def create_entry(
    # 函数 create_entry 的初始化逻辑
    db: AsyncSession,
    entry_data: KnowledgeEntryCreate,
    user: User | None = None,
) -> KnowledgeEntry:
    """手动创建知识条目.

    Args:
        db: 异步数据库会话
        entry_dat    # 条件判断：处理业务逻辑
a: 条目创建数据
        user: 当前用户

    Returns:
        KnowledgeEntry: 新创建的知识条目

    Raises:
        HTTPException 401: 未登录
        HTTPException 500: 数据库操作失败
    """
    # 条件判断: 检查 not user
    if not user:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_401_UNAUTHORIZED,
            # 初始化变量 detail
            detail="需要登录后才能创建知识条目",
        )

    # 初始化变量 db_entry
    db_entry = KnowledgeEntry(
        # 初始化变量 title
        title=entry_data.title,
        # 初始化变量 content
        content=entry_data.content,
        # 初始化变量 category
        category=entry_data.category,
        # 初始化变量 source_type
        source_type=entry_data.source_type,
        # 初始化变量 created_by
        created_by=user.id,
    )
    # 异常处理：处理业务逻辑
    try:
        db.add(db_entry)
        # 异步等待操作完成
        await db.commit()
        # Re-query with selectinload to eagerly load tags relationship
        result = await db.execute(
            select(KnowledgeEntry)
            .options(selectinload(KnowledgeEntry.tags))
            .where(KnowledgeEntry.id == db_entry.id)
        )
        # 初始化变量 db_entry
        db_entry = result.scalar_one()
        # 记录日志信息
        logger.info(
            "知识条目已创建: id={}, title={}, user={}",
            db_entry.id,
            db_entry.title,
            user.id,
        )
        # 返回处理结果
        return db_entry
    # 捕获异常：处理业务逻辑
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"创建知识条目失败: error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # 初始化变量 detail
            detail="创建知识条目失败，请稍后重试",
        ) from e


async def update_entry(
    # 函数 update_entry 的初始化逻辑
    db: AsyncSession,
    entry_id: int,
    entry_data: KnowledgeEntryUpdate,
    user: User | None = None,
) -> KnowledgeEntry:
    """更新知识条目.

    仅条目创建者或系统管理员可执行更新操作。

    Args:
        db: 异步数据库会话
        entry_id: 条目 ID
        entry_data: 更新数据
        user: 当前用户

    Returns:
        KnowledgeEntry: 更新后的知识条目

    Raises:
        HTTPException 401    # 条件判断：处理业务逻辑
: 未登录
        HTTPException 403: 无权限
        HTTPException 404: 条目不存在
        HTTPException 500: 数据库操作失败
    """
    # 异步等待操作完成
    db_entry: KnowledgeEntry | None = await get_entry(db, entry_id)
    # 条件判断: 检查 not db_entry
    if not db_entry:
        # 抛出异常，处理错误情况
        raise HTTPException(
       # 条件判断：处理业务逻辑
         status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail="知识条目不存在",
        )
    _check_permission(db_entry, user, "更新")

    update_data: dict = entry_data.model_dump(exclude_unset=True)
    # 条件判断: 检查 not update_data
    if not update_data:
        # 记录日志信息
        logger.info(f"知识条目更新无变化: id={entry_id}")
      
    # 异常处理：处理业务逻辑
  return db_entry

    # 尝试执行可能抛出异常的代码
    try:
        # 循环遍历：处理业务逻辑
        for key, value in update_data.items():
            setattr(db_entry, key, value)
        # 异步等待操作完成
        await db.commit()
        # 异步等待操作完成
        await db.refresh(db_entry)
        # 初始化变量 user_id
        user_id = user.id if user else "unknown"
        # 记录日志信息
        logger.info(f"知识条目已更新: id={db_entry.id}, user={user_id}")
          # 捕获异常：处理业务逻辑
  return db_entry
    # 捕获并处理异常
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"更新知识条目失败: id={entry_id}, error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # 初始化变量 detail
            detail="更新知识条目失败，请稍后重试",
        ) from e


async def delete_entry(
    # 函数 delete_entry 的初始化逻辑
    db: AsyncSession,
    entry_id: int,
    user: User | None = None,
) -> bool:
    """删除知识条目.

    仅条目创建者或系统管理员可执行删除操作。

    Args:
        db: 异步数据库会话
        entry_id: 条目 ID
        user: 当前用户

    Returns:
        bool: 删除成功返回 True

     # 条件判断：处理业务逻辑
   Raises:
        HTTPException 401: 未登录
        HTTPException 403: 无权限
        HTTPException 404: 条目不存在
        HTTPException 500: 数据库操作失败
    """
    # 异步等待操作完成
    db_entry: KnowledgeEntry | None = await get_entry(db, entry_id)
    # 条件判断: 检查 not db_entry
    if not db_entry:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail="知识条目不存在",
        )
    _ch
    # 异常处理：处理业务逻辑
eck_permission(db_entry, user, "删除")

    # 尝试执行可能抛出异常的代码
    try:
        # 异步等待操作完成
        await db.delete(db_entry)
        # 异步等待操作完成
        await db.commit()
        # 初始化变量 user_id
        user_id = user.id if user else "unknown"
        # 记录日志信息
        logger.info(f"知识条目已删除: id={entry_id}, u    # 捕获异常：处理业务逻辑
ser={user_id}")
        # 返回处理结果
        return True
    # 捕获并处理异常
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"删除知识条目失败: id={entry_id}, error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # 初始化变量 detail
            detail="删除知识条目失败，请稍后重试",
        ) from e


async def get_entry_relations(
    # 函数 get_entry_relations 的初始化逻辑
    db: AsyncSession,
    entry_id: int,
) -> list[EntryRelation]:
    """获取指定知识条目的所有关联关系.

    Args:
        db: 异步数据库会话
        entry_id: 知识条目 I    # 条件判断：处理业务逻辑
D

    Returns:
        list[EntryRelation]: 关联关系列表，包含源条目和目标条目详情

    Raises:
        HTTPException 404: 知识条目不存在
    """
    # 初始化变量 entry_exists
    entry_exists = await db.execute(
        select(KnowledgeEntry.id).where(KnowledgeEntry.id == entry_id)
    )
    # 条件判断: 检查 not entry_exists.scalar_one_or_none()
    if not entry_exists.scalar_one_or_none():
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail="知识条目不存在",
        )

    # 初始化变量 result
    result = await db.execute(
        select(EntryRelation)
        .where(
            (EntryRelation.source_entry_id == entry_id)
            | (EntryRelation.target_entry_id == entry_id)
        )
        .options(
            selectinload(EntryRelation.source_entry),
            selectinload(EntryRelation.target_entry),
        )
    )
    # 返回处理结果
    return list(result.scalars().all())


async def add_entry_relation(
    # 函数 add_entry_relation 的初始化逻辑
    db: AsyncSession,
    source_entry_id: int,
    relation_data: EntryRelationCreate,
) -> EntryRelation:
    """在两个知识条目之间添加关联关系.

    Args:
        db: 异步数据库会话
        source_entr    # 条件判断：处理业务逻辑
y_id: 源条目 ID
        relation_data: 关联关系数据

    Returns:
        EntryRelation: 新创建的关联关系

    Raises:
        HTTPException 400: 关联数据不合法
        HTTPException 404: 源条目或目标条目不存在
        HTTPException 409: 关联关系重复
        HTTPException 500: 数据库操作失败
    """
    # 条件判断: 检查 source_entry_id == relatio    # 条件判断：处理业
    if source_entry_id == relatio    # 条件判断：处理业务逻辑
n_data.target_entry_id:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_400_BAD_REQUEST,
            # 初始化变量 detail
            detail="不能将条目关联到自身",
        )

    # 初始化变量 source_entry
    source_entry = await db.execute(
        select(KnowledgeEntry.id).where(KnowledgeEntry.id == source_entry_id)
    )
    # 条件判断: 检查 not source_entry.scalar_one_or_none()
    if not source_entry.scalar_one_or_none():
        # 抛出异常，处理错误情况
        raise    # 条件判断：处理业务逻辑
 HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail=f"源知识条目(id={source_entry_id})不存在",
        )

    # 初始化变量 target_entry
    target_entry = await db.execute(
        select(KnowledgeEntry.id).where(
            KnowledgeEntry.id == relation_data.target_entry_id
        )
    )
    # 条件判断: 检查 not target_entry.scalar_one_or_none()
    if not target_entry.scalar_one_or_none():
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail=f"目标知识条目(id={relation_data.target_entry_id})不存在",
    # 条件判断：处理业务逻辑
        )

    # 初始化变量 existing
    existing = await db.execute(
        select(EntryRelation).where(
            EntryRelation.source_entry_id == source_entry_id,
            EntryRelation.target_entry_id == relation_data.target_entry_id,
            EntryRelation.relation_type == relation_data.relation_type,
        )
    )
    # 条件判断: 检查 existing.scalar_one_or_none()
    if existing.scalar_one_or_none():
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_409_CONFLICT,
            # 初始化变量 detail
            detail="该类型的关联关系已存在",
        )

    # 初始化变量 db_relation
    db_relation = EntryRelation(
        # 初始化变量 source_entry_id
        source_entry_id=source_entry_id,
        # 初始化变量 target_entry_id
        target_entry_id=relation_data.target_entry_id,
     # 异常处理：处理业务逻辑
       relation_type=relation_data.relation_type,
    )
    # 尝试执行可能抛出异常的代码
    try:
        db.add(db_relation)
        # 异步等待操作完成
        await db.commit()
        # 异步等待操作完成
        await db.refresh(db_relation)
        # 记录日志信息
        logger.info(
            "关联关系已创建: source={}, target={}, type={}",
            source_entry_id,
            relation_data.target_entry_id,
            relation_data.rela    # 捕获异常：处理业务逻辑
tion_type.value,
        )
        # 返回处理结果
        return db_relation
    # 捕获并处理异常
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"创建关联关系失败: error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # 初始化变量 detail
            detail="创建关联关系失败，请稍后重试",
        ) from e


async def get_entry_tags(
    # 函数 get_entry_tags 的初始化逻辑
    db: AsyncSession,
    entry_id: int,
) -> list[KnowledgeTag]:
    """获取指定知识条目的所有标签.

    Args:
        db: 异步数据库会话
        ent    # 条件判断：处理业务逻辑
ry_id: 知识条目 ID

    Returns:
        list[KnowledgeTag]: 标签列表

    Raises:
        HTTPException 404: 知识条目不存在
    """
    # 初始化变量 entry
    entry = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.id == entry_id)
        .options(selectinload(KnowledgeEntry.tags))
    )
    # 初始化变量 db_entry
    db_entry = entry.scalar_one_or_none()
    # 条件判断: 检查 not db_entry
    if not db_entry:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail="知识条目不存在",
        )
    # 返回处理结果
    return list(db_entry.tags)


async def add_entry_tag(
    # 函数 add_entry_tag 的初始化逻辑
    db: AsyncSession,
    entry_id: int,
    tag_id: int,
) -> KnowledgeTag:
    """为指定知识条目添加标签，处理标签不存在的情况.

    Args:
     # 条件判断：处理业务逻辑
       db: 异步数据库会话
        entry_id: 知识条目 ID
        tag_id: 标签 ID

    Returns:
        KnowledgeTag: 添加的标签

    Raises:
        HTTPException 404: 知识条目或标签不存在
        HTTPException 409: 标签已关联
        HTTPException 500: 数据库操作失败
    """
    # 初始化变量 entry
    entry = await db.execute(
        se    # 条件判断：处理业务逻辑
lect(KnowledgeEntry.id).where(KnowledgeEntry.id == entry_id)
    )
    # 条件判断: 检查 not entry.scalar_one_or_none()
    if not entry.scalar_one_or_none():
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail="知识条目不存在",
        )

    tag = await db.execute(
        select(KnowledgeTag).w    # 条件判断：处理业务逻辑
here(KnowledgeTag.id == tag_id)
    )
    # 初始化变量 db_tag
    db_tag = tag.scalar_one_or_none()
    # 条件判断: 检查 not db_tag
    if not db_tag:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail="知识标签不存在",
        )

    # 初始化变量 existing
    existing = await db.execute(
        select(EntryTag).where(
            EntryTag.entry_id == entry_id,
            EntryTag.tag_id == tag_id,
        )
    )
    # 条件判断: 检查 existing.scalar_one_or_none()
    if existing.scalar_one_or_none():
        # 抛出异常，处理错误情况
        raise HTTPException(
            status_co
    # 异常处理：处理业务逻辑
de=status.HTTP_409_CONFLICT,
            # 初始化变量 detail
            detail="该标签已关联到此知识条目",
        )

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 entry_tag
        entry_tag = EntryTag(entry_id=entry_id, tag_id=tag_id)
        db.add(entry_tag)
        # 异步等待操作完成
        await db.commit()
        logg    # 捕获异常：处理业务逻辑
er.info(f"标签已关联: entry={entry_id}, tag={tag_id}")
        # 返回处理结果
        return db_tag
    # 捕获并处理异常
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"添加条目标签失败: entry={entry_id}, tag={tag_id}, error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # 初始化变量 detail
            detail="添加条目标签失败，请稍后重试",
        ) from e


async def remove_entry_tag(
    # 函数 remove_entry_tag 的初始化逻辑
    db: AsyncSession,
    entry_id: int,
    tag_id: int,
) -> bool:
    """从指定知识条目中移除特定标签.

    Args:
           # 条件判断：处理业务逻辑
 db: 异步数据库会话
        entry_id: 知识条目 ID
        tag_id: 标签 ID

    Returns:
        bool: 移除成功返回 True

    Raises:
        HTTPException 404: 关联关系不存在
        HTTPException 500: 数据库操作失败
    """
    # 初始化变量 result
    result = await db.execute(
        select(EntryTag).where(
            EntryTag.entry_id == entry_id,
            EntryTag.tag_id == tag_id,
        )
    )
    # 初始化变量 entry_tag
    entry_tag = result.scalar_one_or_none()
    # 条件判断: 检查 not entry_tag
    if not entry_tag:
        # 抛出异常，处理错误情况
        raise HTTPException(
   
    # 异常处理：处理业务逻辑
         status_code=status.HTTP_404_NOT_FOUND,
            # 初始化变量 detail
            detail="该标签未关联到此知识条目",
        )

    # 尝试执行可能抛出异常的代码
    try:
        # 异步等待操作完成
        await db.delete(entry_tag)
        # 异步等待操作完成
        await db.c    # 捕获异常：处理业务逻辑
ommit()
        # 记录日志信息
        logger.info(f"标签已移除: entry={entry_id}, tag={tag_id}")
        # 返回处理结果
        return True
    # 捕获并处理异常
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"移除条目标签失败: entry={entry_id}, tag={tag_id}, error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # 初始化变量 detail
            detail="移除条目标签失败，请稍后重试",
        ) from e


async def get_all_tags(
    # 函数 get_all_tags 的初始化逻辑
    db: AsyncSession,
) -> list[KnowledgeTag]:
    """获取系统中所有标签列表.

    Args:
        db: 异步数据库会话

    Returns:
        list[KnowledgeTag]: 所有标签
    """
    # 初始化变量 result
    result = await db.execute(
        select(KnowledgeTag)
        .options(selectinload(KnowledgeTag.entries))
        .order_by(KnowledgeTag.name)
    )
    ret    # 条件判断：处理业务逻辑
urn list(result.scalars().all())


async def create_tag(
    # 函数 create_tag 的初始化逻辑
    db: AsyncSession,
    tag_data: KnowledgeTagCreate,
    user: User | None = None,
) -> KnowledgeTag:
    """创建新标签.

    Args:
        db: 异步数据库会话
        tag_data: 标签创建数据
           # 条件判断：处理业务逻辑
 user: 当前用户

    Returns:
        KnowledgeTag: 新创建的标签

    Raises:
        HTTPException 401: 未登录
        HTTPException 409: 标签名称重复
        HTTPException 500: 数据库操作失败
    """
    # 条件判断: 检查 not user
    if not user:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_401_UNAUTHORIZED,
            # 初始化变量 detail
            detail="需要登录后才能创建知识标签",
        )

    # 初始化变量 existing
    existing = await db.execute(
        select(KnowledgeTag).where(KnowledgeTag.name == tag_data.name)
    )
    # 条件判断: 检查 existing.scalar_one_or_none()
    if existing.scalar_one_or_none():
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_409_CONFLICT,
            # 初始化变量 detail
            detail=f"标签名称'{tag_data.name}'已存在",
        )

    # 初始化变量 db_tag
    db_tag = KnowledgeTag(
        # 初始化变量 name
        name=tag_data.name,
      # 异常处理：处理业务逻辑
      description=getattr(tag_data, "description", None),
        # 初始化变量 color
        color=getattr(tag_data, "color", None),
    )
    # 尝试执行可能抛出异常的代码
    try:
        db.add(db_tag)
        # 异步等待操作完成
        await db.commit()
        # 异步等待操作完成
        await db.refresh(db_tag    # 捕获异常：处理业务逻辑
)
        # 记录日志信息
        logger.info(f"知识标签已创建: id={db_tag.id}, name={db_tag.name}, user={user.id}")
        # 返回处理结果
        return db_tag
    # 捕获并处理异常
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"创建知识标签失败: error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # 初始化变量 detail
            detail="创建知识标签失败，请稍后重试",
        ) from e
