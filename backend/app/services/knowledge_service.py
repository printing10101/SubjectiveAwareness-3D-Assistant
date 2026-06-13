"""知识库管理服务模块.

提供知识条目 CRUD、标签管理和关联关系操作，包含权限验证和异常处理。
所有数据库操作均使用异步 API。
"""

from __future__ import annotations

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entry_relation import EntryRelation
from app.models.entry_tag import EntryTag
from app.models.knowledge_entry import EntryCategory, EntryStatus, KnowledgeEntry
from app.models.knowledge_tag import KnowledgeTag
from app.models.user import User, UserRole
from app.schemas.case import PaginatedResponse
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


def _build_sort_column(sort_by: str, sort_order: str) -> func.asc | func.desc:
    """构建排序表达式，安全地规避SQL注入.

    Args:
        sort_by: 已验证的排序字段名
        sort_order: 已验证的排序方向

    Returns:
        排序表达式
    """
    column = getattr(KnowledgeEntry, sort_by)
    return column.desc() if sort_order == "desc" else column.asc()


def _check_permission(
    entry: KnowledgeEntry,
    user: User | None,
    action: str,
) -> None:
    """验证用户对知识条目的操作权限.

    仅创建者或系统管理员可执行更新/删除操作。

    Args:
        entry: 知识条目实例
        user: 当前用户
        action: 操作描述（用于日志和错误信息）

    Raises:
        HTTPException 401: 未登录
        HTTPException 403: 无权限
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"需要登录后才能{action}知识条目",
        )
    is_creator: bool = entry.created_by == user.id
    is_admin: bool = user.role == UserRole.admin
    if not is_creator and not is_admin:
        logger.warning(
            "权限不足: user={} 尝试{action} entry={}",
            user.id,
            action,
            entry.id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"无权限{action}此知识条目，仅条目创建者或管理员可以{action}",
        )


async def get_entries_paginated(  # noqa: PLR0913
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
    _validate_pagination_params(page, page_size, sort_by, sort_order)

    base_stmt = select(KnowledgeEntry)

    if category_filter:
        base_stmt = base_stmt.where(KnowledgeEntry.category == category_filter)
    if status_filter:
        base_stmt = base_stmt.where(KnowledgeEntry.status == status_filter)
    if tag_filter:
        base_stmt = base_stmt.join(
            EntryTag, KnowledgeEntry.id == EntryTag.entry_id
        ).where(EntryTag.tag_id == tag_filter)

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    count_result = await db.execute(count_stmt)
    total: int = count_result.scalar_one()

    sort_expr = _build_sort_column(sort_by, sort_order)
    offset = (page - 1) * page_size
    items_stmt = (
        base_stmt.order_by(sort_expr)
        .offset(offset)
        .limit(page_size)
        .options(selectinload(KnowledgeEntry.tags))
    )
    items_result = await db.execute(items_stmt)
    items: list[KnowledgeEntry] = list(items_result.scalars().all())

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_entry(
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
    result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.id == entry_id)
        .options(
            selectinload(KnowledgeEntry.tags),
            selectinload(KnowledgeEntry.creator),
            selectinload(KnowledgeEntry.verifier),
        )
    )
    return result.scalar_one_or_none()


async def create_entry(
    db: AsyncSession,
    entry_data: KnowledgeEntryCreate,
    user: User | None = None,
) -> KnowledgeEntry:
    """手动创建知识条目.

    Args:
        db: 异步数据库会话
        entry_data: 条目创建数据
        user: 当前用户

    Returns:
        KnowledgeEntry: 新创建的知识条目

    Raises:
        HTTPException 401: 未登录
        HTTPException 500: 数据库操作失败
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要登录后才能创建知识条目",
        )

    db_entry = KnowledgeEntry(
        title=entry_data.title,
        content=entry_data.content,
        summary=entry_data.summary,
        category=entry_data.category,
        status=entry_data.status,
        confidence=entry_data.confidence,
        decay_coefficient=entry_data.decay_coefficient,
        source_type=entry_data.source_type,
        source_id=entry_data.source_id,
        created_by=user.id,
    )
    try:
        db.add(db_entry)
        await db.commit()
        await db.refresh(db_entry)
        logger.info(
            "知识条目已创建: id={}, title={}, user={}",
            db_entry.id,
            db_entry.title,
            user.id,
        )
        return db_entry
    except Exception as e:
        await db.rollback()
        logger.error(f"创建知识条目失败: error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建知识条目失败，请稍后重试",
        ) from e


async def update_entry(
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
        HTTPException 401: 未登录
        HTTPException 403: 无权限
        HTTPException 404: 条目不存在
        HTTPException 500: 数据库操作失败
    """
    db_entry: KnowledgeEntry | None = await get_entry(db, entry_id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识条目不存在",
        )
    _check_permission(db_entry, user, "更新")

    update_data: dict = entry_data.model_dump(exclude_unset=True)
    if not update_data:
        logger.info(f"知识条目更新无变化: id={entry_id}")
        return db_entry

    try:
        for key, value in update_data.items():
            setattr(db_entry, key, value)
        await db.commit()
        await db.refresh(db_entry)
        user_id = user.id if user else "unknown"
        logger.info(f"知识条目已更新: id={db_entry.id}, user={user_id}")
        return db_entry
    except Exception as e:
        await db.rollback()
        logger.error(f"更新知识条目失败: id={entry_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新知识条目失败，请稍后重试",
        ) from e


async def delete_entry(
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

    Raises:
        HTTPException 401: 未登录
        HTTPException 403: 无权限
        HTTPException 404: 条目不存在
        HTTPException 500: 数据库操作失败
    """
    db_entry: KnowledgeEntry | None = await get_entry(db, entry_id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识条目不存在",
        )
    _check_permission(db_entry, user, "删除")

    try:
        await db.delete(db_entry)
        await db.commit()
        user_id = user.id if user else "unknown"
        logger.info(f"知识条目已删除: id={entry_id}, user={user_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"删除知识条目失败: id={entry_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除知识条目失败，请稍后重试",
        ) from e


async def get_entry_relations(
    db: AsyncSession,
    entry_id: int,
) -> list[EntryRelation]:
    """获取指定知识条目的所有关联关系.

    Args:
        db: 异步数据库会话
        entry_id: 知识条目 ID

    Returns:
        list[EntryRelation]: 关联关系列表，包含源条目和目标条目详情

    Raises:
        HTTPException 404: 知识条目不存在
    """
    entry_exists = await db.execute(
        select(KnowledgeEntry.id).where(KnowledgeEntry.id == entry_id)
    )
    if not entry_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识条目不存在",
        )

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
    return list(result.scalars().all())


async def add_entry_relation(
    db: AsyncSession,
    source_entry_id: int,
    relation_data: EntryRelationCreate,
) -> EntryRelation:
    """在两个知识条目之间添加关联关系.

    Args:
        db: 异步数据库会话
        source_entry_id: 源条目 ID
        relation_data: 关联关系数据

    Returns:
        EntryRelation: 新创建的关联关系

    Raises:
        HTTPException 400: 关联数据不合法
        HTTPException 404: 源条目或目标条目不存在
        HTTPException 409: 关联关系重复
        HTTPException 500: 数据库操作失败
    """
    if source_entry_id == relation_data.target_entry_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能将条目关联到自身",
        )

    source_entry = await db.execute(
        select(KnowledgeEntry.id).where(KnowledgeEntry.id == source_entry_id)
    )
    if not source_entry.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"源知识条目(id={source_entry_id})不存在",
        )

    target_entry = await db.execute(
        select(KnowledgeEntry.id).where(
            KnowledgeEntry.id == relation_data.target_entry_id
        )
    )
    if not target_entry.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标知识条目(id={relation_data.target_entry_id})不存在",
        )

    existing = await db.execute(
        select(EntryRelation).where(
            EntryRelation.source_entry_id == source_entry_id,
            EntryRelation.target_entry_id == relation_data.target_entry_id,
            EntryRelation.relation_type == relation_data.relation_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该类型的关联关系已存在",
        )

    db_relation = EntryRelation(
        source_entry_id=source_entry_id,
        target_entry_id=relation_data.target_entry_id,
        relation_type=relation_data.relation_type,
    )
    try:
        db.add(db_relation)
        await db.commit()
        await db.refresh(db_relation)
        logger.info(
            "关联关系已创建: source={}, target={}, type={}",
            source_entry_id,
            relation_data.target_entry_id,
            relation_data.relation_type.value,
        )
        return db_relation
    except Exception as e:
        await db.rollback()
        logger.error(f"创建关联关系失败: error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建关联关系失败，请稍后重试",
        ) from e


async def get_entry_tags(
    db: AsyncSession,
    entry_id: int,
) -> list[KnowledgeTag]:
    """获取指定知识条目的所有标签.

    Args:
        db: 异步数据库会话
        entry_id: 知识条目 ID

    Returns:
        list[KnowledgeTag]: 标签列表

    Raises:
        HTTPException 404: 知识条目不存在
    """
    entry = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.id == entry_id)
        .options(selectinload(KnowledgeEntry.tags))
    )
    db_entry = entry.scalar_one_or_none()
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识条目不存在",
        )
    return list(db_entry.tags)


async def add_entry_tag(
    db: AsyncSession,
    entry_id: int,
    tag_id: int,
) -> KnowledgeTag:
    """为指定知识条目添加标签，处理标签不存在的情况.

    Args:
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
    entry = await db.execute(
        select(KnowledgeEntry.id).where(KnowledgeEntry.id == entry_id)
    )
    if not entry.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识条目不存在",
        )

    tag = await db.execute(
        select(KnowledgeTag).where(KnowledgeTag.id == tag_id)
    )
    db_tag = tag.scalar_one_or_none()
    if not db_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识标签不存在",
        )

    existing = await db.execute(
        select(EntryTag).where(
            EntryTag.entry_id == entry_id,
            EntryTag.tag_id == tag_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该标签已关联到此知识条目",
        )

    try:
        entry_tag = EntryTag(entry_id=entry_id, tag_id=tag_id)
        db.add(entry_tag)
        await db.commit()
        logger.info(f"标签已关联: entry={entry_id}, tag={tag_id}")
        return db_tag
    except Exception as e:
        await db.rollback()
        logger.error(f"添加条目标签失败: entry={entry_id}, tag={tag_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="添加条目标签失败，请稍后重试",
        ) from e


async def remove_entry_tag(
    db: AsyncSession,
    entry_id: int,
    tag_id: int,
) -> bool:
    """从指定知识条目中移除特定标签.

    Args:
        db: 异步数据库会话
        entry_id: 知识条目 ID
        tag_id: 标签 ID

    Returns:
        bool: 移除成功返回 True

    Raises:
        HTTPException 404: 关联关系不存在
        HTTPException 500: 数据库操作失败
    """
    result = await db.execute(
        select(EntryTag).where(
            EntryTag.entry_id == entry_id,
            EntryTag.tag_id == tag_id,
        )
    )
    entry_tag = result.scalar_one_or_none()
    if not entry_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该标签未关联到此知识条目",
        )

    try:
        await db.delete(entry_tag)
        await db.commit()
        logger.info(f"标签已移除: entry={entry_id}, tag={tag_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"移除条目标签失败: entry={entry_id}, tag={tag_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="移除条目标签失败，请稍后重试",
        ) from e


async def get_all_tags(
    db: AsyncSession,
) -> list[KnowledgeTag]:
    """获取系统中所有标签列表.

    Args:
        db: 异步数据库会话

    Returns:
        list[KnowledgeTag]: 所有标签
    """
    result = await db.execute(select(KnowledgeTag).order_by(KnowledgeTag.name))
    return list(result.scalars().all())


async def create_tag(
    db: AsyncSession,
    tag_data: KnowledgeTagCreate,
    user: User | None = None,
) -> KnowledgeTag:
    """创建新标签.

    Args:
        db: 异步数据库会话
        tag_data: 标签创建数据
        user: 当前用户

    Returns:
        KnowledgeTag: 新创建的标签

    Raises:
        HTTPException 401: 未登录
        HTTPException 409: 标签名称重复
        HTTPException 500: 数据库操作失败
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要登录后才能创建知识标签",
        )

    existing = await db.execute(
        select(KnowledgeTag).where(KnowledgeTag.name == tag_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"标签名称'{tag_data.name}'已存在",
        )

    db_tag = KnowledgeTag(
        name=tag_data.name,
        description=getattr(tag_data, "description", None),
        color=getattr(tag_data, "color", None),
    )
    try:
        db.add(db_tag)
        await db.commit()
        await db.refresh(db_tag)
        logger.info(f"知识标签已创建: id={db_tag.id}, name={db_tag.name}, user={user.id}")
        return db_tag
    except Exception as e:
        await db.rollback()
        logger.error(f"创建知识标签失败: error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建知识标签失败，请稍后重试",
        ) from e
