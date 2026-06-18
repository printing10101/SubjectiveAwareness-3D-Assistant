"""知识库数据访问层.

整合原 knowledge_service.py 和 knowledge_search_service.py，
提供知识条目 CRUD、标签管理、关联关系操作和全文搜索功能。
"""
from __future__ import annotations

import re
import time
from typing import Any

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import func, select, text
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
_DEFAULT_SEARCH_LIMIT: int = 20
_MAX_SEARCH_LIMIT: int = 200
_PERF_WARN_THRESHOLD_MS: float = 300.0
_HIGHLIGHT_OPEN: str = "<mark>"
_HIGHLIGHT_CLOSE: str = "</mark>"
_SNIPPET_MAX_TOKENS: int = 64
_fts_table_name: str = "knowledge_fts"
_FTS5_TOKENIZER: str = "unicode61"

_CJK_PATTERN: re.Pattern = re.compile(
    r"([\u2E80-\u2EFF\u3000-\u303F\u3400-\u4DBF"
    r"\u4E00-\u9FFF\uF900-\uFAFF\uFE30-\uFE4F"
    r"\uFF00-\uFFEF])"
)
_FTS5_SPECIAL_CHARS: re.Pattern = re.compile(r'[\x00-\x1f"*]')
_CREATE_FTS_TABLE_SQL: str = (
    f"CREATE VIRTUAL TABLE IF NOT EXISTS {_fts_table_name} "
    f"USING fts5(title, content, summary, tokenize='{_FTS5_TOKENIZER}')"
)
_INSERT_FTS_SQL: str = (
    f"INSERT OR REPLACE INTO {_fts_table_name}(rowid, title, content, summary) "
    "VALUES (:rowid, :title, :content, :summary)"
)
_DELETE_FTS_SQL: str = f"DELETE FROM {_fts_table_name} WHERE rowid = :rowid"
_COUNT_FTS_SQL: str = f"SELECT COUNT(*) FROM {_fts_table_name}"


def _validate_pagination_params(page: int, page_size: int, sort_by: str, sort_order: str) -> None:
    if page < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="页码必须大于等于1")
    if page_size < 1 or page_size > _MAX_PAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"每页条数必须在1到{_MAX_PAGE_SIZE}之间")
    if sort_by not in _SORTABLE_FIELDS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"无效的排序字段'{sort_by}'，允许的字段: {sorted(_SORTABLE_FIELDS)}")
    if sort_order not in _VALID_SORT_ORDERS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"无效的排序方向'{sort_order}'，仅支持'asc'和'desc'")


def _build_sort_column(sort_by: str, sort_order: str):
    column = getattr(KnowledgeEntry, sort_by)
    return column.desc() if sort_order == "desc" else column.asc()


def _check_permission(entry: KnowledgeEntry, user: User | None, action: str) -> None:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"需要登录后才能{action}知识条目")
    if entry.created_by != user.id and user.role != UserRole.admin:
        logger.warning("权限不足: user={} 尝试{action} entry={}", user.id, action, entry.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"无权限{action}此知识条目，仅条目创建者或管理员可以{action}")


def _segment_cjk(text: str) -> str:
    if not text:
        return text
    return _CJK_PATTERN.sub(r" \1 ", text)


def _sanitize_query(query: str) -> str:
    if not query or not query.strip():
        raise ValueError("搜索查询不能为空")
    cleaned = query.strip()[:500]
    cleaned = _FTS5_SPECIAL_CHARS.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) < 1:
        raise ValueError("搜索查询长度不足，至少需要1个字符")
    cleaned = _segment_cjk(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _build_filter_conditions(category: EntryCategory | None, tag_id: int | None, status_filter: EntryStatus | None) -> tuple[str, dict[str, Any]]:
    conditions: list[str] = []
    params: dict[str, Any] = {}
    if category is not None:
        conditions.append("ke.category = :category")
        params["category"] = category.value if hasattr(category, "value") else category
    if status_filter is not None:
        conditions.append("ke.status = :status")
        params["status"] = status_filter.value if hasattr(status_filter, "value") else status_filter
    if tag_id is not None:
        conditions.append("EXISTS (SELECT 1 FROM entry_tags et WHERE et.entry_id = ke.id AND et.tag_id = :tag_id)")
        params["tag_id"] = tag_id
    filter_sql = "AND " + " AND ".join(conditions) if conditions else ""
    return filter_sql, params


def _build_highlight_snippet(title: str, summary: str | None, original_query: str) -> str:
    base_text = summary or title or ""
    if not base_text:
        return ""
    original_query = original_query.strip()
    query_terms = _FTS5_SPECIAL_CHARS.sub(" ", original_query).split()
    if not query_terms:
        return base_text[:300] + ("..." if len(base_text) > 300 else "")
    pattern = re.compile(f"({'|'.join(re.escape(t) for t in query_terms)})", re.IGNORECASE)
    result = pattern.sub(lambda m: f"{_HIGHLIGHT_OPEN}{m.group(0)}{_HIGHLIGHT_CLOSE}", base_text)
    return result[:300] + ("..." if len(result) > 300 else "")


# --- CRUD 操作 ---

async def get_entries_paginated(  # noqa: PLR0913
    db: AsyncSession, page: int = 1, page_size: int = _DEFAULT_PAGE_SIZE,
    sort_by: str = "created_at", sort_order: str = "desc",
    category_filter: EntryCategory | None = None, tag_filter: int | None = None,
    status_filter: EntryStatus | None = None,
) -> PaginatedResponse[KnowledgeEntry]:
    _validate_pagination_params(page, page_size, sort_by, sort_order)
    base_stmt = select(KnowledgeEntry)
    if category_filter:
        base_stmt = base_stmt.where(KnowledgeEntry.category == category_filter)
    if status_filter:
        base_stmt = base_stmt.where(KnowledgeEntry.status == status_filter)
    if tag_filter:
        base_stmt = base_stmt.join(EntryTag, KnowledgeEntry.id == EntryTag.entry_id).where(EntryTag.tag_id == tag_filter)
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()
    sort_expr = _build_sort_column(sort_by, sort_order)
    offset = (page - 1) * page_size
    items_stmt = base_stmt.order_by(sort_expr).offset(offset).limit(page_size).options(selectinload(KnowledgeEntry.tags))
    items: list[KnowledgeEntry] = list((await db.execute(items_stmt)).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


async def get_entry(db: AsyncSession, entry_id: int) -> KnowledgeEntry | None:
    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id).options(
            selectinload(KnowledgeEntry.tags), selectinload(KnowledgeEntry.creator), selectinload(KnowledgeEntry.verifier)
        )
    )
    return result.scalar_one_or_none()


async def create_entry(db: AsyncSession, entry_data: KnowledgeEntryCreate, user: User | None = None) -> KnowledgeEntry:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要登录后才能创建知识条目")
    db_entry = KnowledgeEntry(title=entry_data.title, content=entry_data.content, category=entry_data.category, source_type=entry_data.source_type, created_by=user.id)
    try:
        db.add(db_entry)
        await db.commit()
        result = await db.execute(select(KnowledgeEntry).options(selectinload(KnowledgeEntry.tags)).where(KnowledgeEntry.id == db_entry.id))
        db_entry = result.scalar_one()
        logger.info("知识条目已创建: id={}, title={}, user={}", db_entry.id, db_entry.title, user.id)
        return db_entry
    except Exception as e:
        await db.rollback()
        logger.error(f"创建知识条目失败: error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建知识条目失败，请稍后重试") from e


async def update_entry(db: AsyncSession, entry_id: int, entry_data: KnowledgeEntryUpdate, user: User | None = None) -> KnowledgeEntry:
    db_entry = await get_entry(db, entry_id)
    if not db_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
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
        logger.info(f"知识条目已更新: id={db_entry.id}, user={user.id if user else 'unknown'}")
        return db_entry
    except Exception as e:
        await db.rollback()
        logger.error(f"更新知识条目失败: id={entry_id}, error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新知识条目失败，请稍后重试") from e


async def delete_entry(db: AsyncSession, entry_id: int, user: User | None = None) -> bool:
    db_entry = await get_entry(db, entry_id)
    if not db_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
    _check_permission(db_entry, user, "删除")
    try:
        await db.delete(db_entry)
        await db.commit()
        logger.info(f"知识条目已删除: id={entry_id}, user={user.id if user else 'unknown'}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"删除知识条目失败: id={entry_id}, error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除知识条目失败，请稍后重试") from e


# --- 关联关系 ---

async def get_entry_relations(db: AsyncSession, entry_id: int) -> list[EntryRelation]:
    entry_exists = await db.execute(select(KnowledgeEntry.id).where(KnowledgeEntry.id == entry_id))
    if not entry_exists.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
    result = await db.execute(
        select(EntryRelation).where(
            (EntryRelation.source_entry_id == entry_id) | (EntryRelation.target_entry_id == entry_id)
        ).options(selectinload(EntryRelation.source_entry), selectinload(EntryRelation.target_entry))
    )
    return list(result.scalars().all())


async def add_entry_relation(db: AsyncSession, source_entry_id: int, relation_data: EntryRelationCreate) -> EntryRelation:
    if source_entry_id == relation_data.target_entry_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能将条目关联到自身")
    for eid, label in [(source_entry_id, "源"), (relation_data.target_entry_id, "目标")]:
        exists = await db.execute(select(KnowledgeEntry.id).where(KnowledgeEntry.id == eid))
        if not exists.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label}知识条目(id={eid})不存在")
    existing = await db.execute(select(EntryRelation).where(
        EntryRelation.source_entry_id == source_entry_id,
        EntryRelation.target_entry_id == relation_data.target_entry_id,
        EntryRelation.relation_type == relation_data.relation_type,
    ))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该类型的关联关系已存在")
    db_relation = EntryRelation(source_entry_id=source_entry_id, target_entry_id=relation_data.target_entry_id, relation_type=relation_data.relation_type)
    try:
        db.add(db_relation)
        await db.commit()
        await db.refresh(db_relation)
        logger.info("关联关系已创建: source={}, target={}, type={}", source_entry_id, relation_data.target_entry_id, relation_data.relation_type.value)
        return db_relation
    except Exception as e:
        await db.rollback()
        logger.error(f"创建关联关系失败: error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建关联关系失败，请稍后重试") from e


# --- 标签管理 ---

async def get_entry_tags(db: AsyncSession, entry_id: int) -> list[KnowledgeTag]:
    entry = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id).options(selectinload(KnowledgeEntry.tags)))
    db_entry = entry.scalar_one_or_none()
    if not db_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
    return list(db_entry.tags)


async def add_entry_tag(db: AsyncSession, entry_id: int, tag_id: int) -> KnowledgeTag:
    entry = await db.execute(select(KnowledgeEntry.id).where(KnowledgeEntry.id == entry_id))
    if not entry.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
    tag = await db.execute(select(KnowledgeTag).where(KnowledgeTag.id == tag_id))
    db_tag = tag.scalar_one_or_none()
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识标签不存在")
    existing = await db.execute(select(EntryTag).where(EntryTag.entry_id == entry_id, EntryTag.tag_id == tag_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该标签已关联到此知识条目")
    try:
        db.add(EntryTag(entry_id=entry_id, tag_id=tag_id))
        await db.commit()
        logger.info(f"标签已关联: entry={entry_id}, tag={tag_id}")
        return db_tag
    except Exception as e:
        await db.rollback()
        logger.error(f"添加条目标签失败: entry={entry_id}, tag={tag_id}, error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="添加条目标签失败，请稍后重试") from e


async def remove_entry_tag(db: AsyncSession, entry_id: int, tag_id: int) -> bool:
    result = await db.execute(select(EntryTag).where(EntryTag.entry_id == entry_id, EntryTag.tag_id == tag_id))
    entry_tag = result.scalar_one_or_none()
    if not entry_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该标签未关联到此知识条目")
    try:
        await db.delete(entry_tag)
        await db.commit()
        logger.info(f"标签已移除: entry={entry_id}, tag={tag_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"移除条目标签失败: entry={entry_id}, tag={tag_id}, error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="移除条目标签失败，请稍后重试") from e


async def get_all_tags(db: AsyncSession) -> list[KnowledgeTag]:
    result = await db.execute(select(KnowledgeTag).options(selectinload(KnowledgeTag.entries)).order_by(KnowledgeTag.name))
    return list(result.scalars().all())


async def create_tag(db: AsyncSession, tag_data: KnowledgeTagCreate, user: User | None = None) -> KnowledgeTag:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要登录后才能创建知识标签")
    existing = await db.execute(select(KnowledgeTag).where(KnowledgeTag.name == tag_data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"标签名称'{tag_data.name}'已存在")
    db_tag = KnowledgeTag(name=tag_data.name, description=getattr(tag_data, "description", None), color=getattr(tag_data, "color", None))
    try:
        db.add(db_tag)
        await db.commit()
        await db.refresh(db_tag)
        logger.info(f"知识标签已创建: id={db_tag.id}, name={db_tag.name}, user={user.id}")
        return db_tag
    except Exception as e:
        await db.rollback()
        logger.error(f"创建知识标签失败: error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建知识标签失败，请稍后重试") from e


# --- 全文搜索 ---

async def ensure_fts_table(db: AsyncSession) -> None:
    try:
        await db.execute(text(_CREATE_FTS_TABLE_SQL))
        await db.commit()
        logger.info("FTS5 全文搜索虚拟表已就绪: table={}", _fts_table_name)
    except Exception as e:
        logger.error("FTS5 表初始化失败: error={}", e)
        raise RuntimeError(f"全文搜索功能初始化失败: {e}") from e


async def sync_entry(db: AsyncSession, entry_id: int, title: str, content: str, summary: str | None = None) -> None:
    try:
        await db.execute(text(_INSERT_FTS_SQL), {"rowid": entry_id, "title": _segment_cjk(title), "content": _segment_cjk(content), "summary": _segment_cjk(summary or "")})
        await db.commit()
        logger.debug("FTS 索引已同步: entry_id={}", entry_id)
    except Exception as e:
        logger.error("FTS 索引同步失败: entry_id={}, error={}", entry_id, e)
        raise RuntimeError(f"全文索引同步失败(entry_id={entry_id}): {e}") from e


async def remove_entry_from_fts(db: AsyncSession, entry_id: int) -> None:
    try:
        await db.execute(text(_DELETE_FTS_SQL), {"rowid": entry_id})
        await db.commit()
        logger.debug("FTS 索引已删除: entry_id={}", entry_id)
    except Exception as e:
        logger.error("FTS 索引删除失败: entry_id={}, error={}", entry_id, e)
        raise RuntimeError(f"全文索引删除失败(entry_id={entry_id}): {e}") from e


async def get_fts_count(db: AsyncSession) -> int:
    result = await db.execute(text(_COUNT_FTS_SQL))
    return result.scalar_one()


async def search_entries(  # noqa: PLR0913
    db: AsyncSession, query: str, category: EntryCategory | None = None,
    tag_id: int | None = None, status: EntryStatus | None = None,
    limit: int = _DEFAULT_SEARCH_LIMIT,
) -> list[dict[str, Any]]:
    if limit < 1:
        raise ValueError("返回结果数量必须大于0")
    if limit > _MAX_SEARCH_LIMIT:
        raise ValueError(f"返回结果数量不能超过{_MAX_SEARCH_LIMIT}")
    original_query = query.strip()
    sanitized = _sanitize_query(query)
    filter_sql, filter_params = _build_filter_conditions(category, tag_id, status)
    search_sql = (
        f"SELECT ke.id AS entry_id, ke.title, ke.summary, fts.rank AS score, "
        f"snippet({_fts_table_name}, 1, '{_HIGHLIGHT_OPEN}', '{_HIGHLIGHT_CLOSE}', '...', {_SNIPPET_MAX_TOKENS}) AS highlight_snippet "
        f"FROM {_fts_table_name} fts JOIN knowledge_entries ke ON fts.rowid = ke.id "
        f"WHERE {_fts_table_name} MATCH :query {filter_sql} ORDER BY fts.rank LIMIT :limit"
    )
    params: dict[str, Any] = {"query": sanitized, "limit": limit}
    params.update(filter_params)
    start = time.perf_counter()
    try:
        result = await db.execute(text(search_sql), params)
        rows = result.fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("全文搜索完成: query='{}', results={}, elapsed={:.1f}ms", original_query, len(rows), elapsed_ms)
        if elapsed_ms > _PERF_WARN_THRESHOLD_MS:
            logger.warning("全文搜索响应时间超标: {:.1f}ms > {:.0f}ms, query='{}'", elapsed_ms, _PERF_WARN_THRESHOLD_MS, original_query)
        mapped: list[dict[str, Any]] = []
        for row in rows:
            highlight = row.highlight_snippet or _build_highlight_snippet(row.title, row.summary, original_query)
            mapped.append({"entry_id": row.entry_id, "title": row.title, "summary": row.summary, "score": row.score, "highlight_snippet": highlight})
        return mapped
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("全文搜索异常: query='{}', error={}, elapsed={:.1f}ms", original_query, e, elapsed_ms)
        raise RuntimeError(f"全文搜索服务暂时不可用: {e}") from e
