"""知识图谱可视化服务模块.

提供图谱数据查询、邻居节点发现和最短路径计算功能，
包含数据缓存机制以减少重复计算与数据库查询。
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_async_db_session
from app.models.entry_relation import EntryRelation, RelationType
from app.models.knowledge_entry import EntryCategory, KnowledgeEntry
from app.utils.cache import get_unified_cache


CATEGORY_COLORS: dict[str, str] = {
    "law": "#4F46E5",
    "methodology": "#059669",
    "case": "#D97706",
    "other": "#6B7280",
}

RELATION_LINE_STYLES: dict[str, str] = {
    "references": "solid",
    "contradicts": "dashed",
    "supersedes": "dotted",
    "extends": "solid",
    "depends_on": "dashed",
}

RELATION_LABELS: dict[str, str] = {
    "references": "引用",
    "contradicts": "矛盾",
    "supersedes": "取代",
    "extends": "扩展",
    "depends_on": "依赖",
}

_CACHE_TTL: int = 300


def _build_graph_cache_key(prefix: str, params: dict[str, Any]) -> str:
    raw = json.dumps(params, sort_keys=True, ensure_ascii=False, default=str)
    return f"kg:{prefix}:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def _entry_to_node(entry: KnowledgeEntry) -> dict[str, Any]:
    """将知识条目模型转换为图谱节点格式.

    Args:
        entry: 知识条目模型实例

    Returns:
        dict: 节点数据
    """
    tag_names = [tag.name for tag in entry.tags] if entry.tags else []
    relations_count = (
        len(entry.outgoing_relations) + len(entry.incoming_relations)
    )
    category_str = (
        entry.category.value
        if isinstance(entry.category, EntryCategory)
        else str(entry.category)
    )
    return {
        "id": entry.id,
        "label": entry.title,
        "category": category_str,
        "properties": {
            "status": entry.status.value if entry.status else "draft",
            "confidence": entry.confidence,
            "summary": entry.summary,
            "tags": tag_names,
            "relation_count": relations_count,
            "updated_at": (
                entry.updated_at.isoformat() if entry.updated_at else None
            ),
        },
        "color": CATEGORY_COLORS.get(category_str, "#6B7280"),
        "size": _calculate_node_size(entry.confidence, relations_count),
    }


def _calculate_node_size(
    confidence: float | None, relations_count: int
) -> float:
    base = 10.0
    confidence_bonus = (confidence or 0.5) * 8.0
    relation_bonus = min(relations_count * 0.8, 12.0)
    size = base + confidence_bonus + relation_bonus
    return round(min(max(size, 8.0), 30.0), 1)


def _relation_to_edge(rel: EntryRelation) -> dict[str, Any]:
    """将条目关系模型转换为图谱边格式.

    Args:
        rel: 条目关系模型实例

    Returns:
        dict: 边数据
    """
    rel_type_str = (
        rel.relation_type.value
        if isinstance(rel.relation_type, RelationType)
        else str(rel.relation_type)
    )
    return {
        "source": rel.source_entry_id,
        "target": rel.target_entry_id,
        "type": rel_type_str,
        "label": RELATION_LABELS.get(rel_type_str, rel_type_str),
        "lineStyle": RELATION_LINE_STYLES.get(rel_type_str, "solid"),
    }


async def get_graph_data(  # noqa: PLR0913
    db: AsyncSession,
    category_filters: list[str] | None = None,
    tag_filters: list[str] | None = None,
    relation_type_filters: list[str] | None = None,
    search_query: str | None = None,
    entry_ids: list[int] | None = None,
) -> dict[str, Any]:
    """根据筛选条件返回图谱节点和边数据.

    Args:
        db: 异步数据库会话
        category_filters: 分类筛选列表
        tag_filters: 标签名称筛选列表
        relation_type_filters: 关系类型筛选列表
        search_query: 标题搜索关键词
        entry_ids: 指定条目ID列表（迷你模式使用）

    Returns:
        dict: 包含 nodes 和 edges 的图谱数据
    """
    cache_params = {
        "category_filters": (
            sorted(category_filters) if category_filters else None
        ),
        "tag_filters": sorted(tag_filters) if tag_filters else None,
        "relation_type_filters": (
            sorted(relation_type_filters) if relation_type_filters else None
        ),
        "search_query": search_query,
        "entry_ids": sorted(entry_ids) if entry_ids else None,
    }
    cache_key = _build_graph_cache_key("graph_data", cache_params)
    cache = get_unified_cache()
    cached = await cache.get(cache_key)
    if cached is not None:
        logger.debug(f"图谱数据缓存命中: {cache_key}")
        return cached

    entry_stmt = select(KnowledgeEntry).options(
        selectinload(KnowledgeEntry.tags),
        selectinload(KnowledgeEntry.outgoing_relations)
        .selectinload(EntryRelation.target_entry),
        selectinload(KnowledgeEntry.incoming_relations)
        .selectinload(EntryRelation.source_entry),
    )

    if entry_ids:
        entry_stmt = entry_stmt.where(KnowledgeEntry.id.in_(entry_ids))
    if category_filters:
        entry_stmt = entry_stmt.where(
            KnowledgeEntry.category.in_(category_filters)
        )
    if search_query:
        entry_stmt = entry_stmt.where(
            KnowledgeEntry.title.ilike(f"%{search_query}%")
        )

    result = await db.execute(entry_stmt)
    entries = list(result.scalars().all())

    if tag_filters:
        entries = [
            e for e in entries
            if any(tag.name in tag_filters for tag in e.tags)
        ]

    entry_id_set = {e.id for e in entries}
    nodes: list[dict[str, Any]] = []
    for entry in entries:
        node = _entry_to_node(entry)
        nodes.append(node)

    relation_stmt = select(EntryRelation).options(
        selectinload(EntryRelation.source_entry),
        selectinload(EntryRelation.target_entry),
    )
    if relation_type_filters:
        relation_stmt = relation_stmt.where(
            EntryRelation.relation_type.in_(relation_type_filters)
        )

    rel_result = await db.execute(relation_stmt)
    all_relations = list(rel_result.scalars().all())

    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[int, int, str]] = set()
    for rel in all_relations:
        if (
            rel.source_entry_id in entry_id_set
            and rel.target_entry_id in entry_id_set
        ):
            edge_key = (
                rel.source_entry_id,
                rel.target_entry_id,
                rel.relation_type.value,
            )
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append(_relation_to_edge(rel))

    graph_data: dict[str, Any] = {"nodes": nodes, "edges": edges}
    await cache.set(cache_key, graph_data, _CACHE_TTL)
    logger.info(f"图谱数据已缓存: nodes={len(nodes)}, edges={len(edges)}")
    return graph_data


async def get_node_neighbors(
    db: AsyncSession,
    entry_id: int,
    depth: int = 1,
) -> dict[str, Any]:
    """获取指定节点的直接邻居节点及关联边.

    使用BFS算法按深度层级获取邻居节点。

    Args:
        db: 异步数据库会话
        entry_id: 中心节点条目ID
        depth: 邻居获取深度（默认1层）

    Returns:
        dict: 包含 nodes 和 edges 的邻居图谱数据
    """
    cache_key = _build_graph_cache_key(
        "neighbors", {"entry_id": entry_id, "depth": depth}
    )
    cache = get_unified_cache()
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    entry_result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.id == entry_id)
        .options(
            selectinload(KnowledgeEntry.tags),
            selectinload(KnowledgeEntry.outgoing_relations),
            selectinload(KnowledgeEntry.incoming_relations),
        )
    )
    center_entry = entry_result.scalar_one_or_none()
    if not center_entry:
        return {"nodes": [], "edges": []}

    visited: set[int] = {entry_id}
    current_layer: set[int] = {entry_id}
    all_entries: dict[int, KnowledgeEntry] = {entry_id: center_entry}
    all_relations: list[EntryRelation] = []

    for _d in range(depth):
        next_layer: set[int] = set()
        layer_relations: list[EntryRelation] = []

        for node_id in current_layer:
            node_relations = await db.execute(
                select(EntryRelation).where(
                    (EntryRelation.source_entry_id == node_id)
                    | (EntryRelation.target_entry_id == node_id)
                )
            )
            for rel in node_relations.scalars().all():
                neighbor_id = (
                    rel.target_entry_id
                    if rel.source_entry_id == node_id
                    else rel.source_entry_id
                )
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    next_layer.add(neighbor_id)
                    edge_tuple = (
                        rel.source_entry_id,
                        rel.target_entry_id,
                        str(rel.relation_type.value),
                    )
                    existing_edges = {
                        (
                            r.source_entry_id,
                            r.target_entry_id,
                            str(r.relation_type.value),
                        )
                        for r in layer_relations
                    }
                    if edge_tuple not in existing_edges:
                        layer_relations.append(rel)

        if next_layer:
            neighbors_result = await db.execute(
                select(KnowledgeEntry)
                .where(KnowledgeEntry.id.in_(list(next_layer)))
                .options(selectinload(KnowledgeEntry.tags))
            )
            for entry in neighbors_result.scalars().all():
                all_entries[entry.id] = entry

        all_relations.extend(layer_relations)
        current_layer = next_layer

    nodes = [_entry_to_node(entry) for entry in all_entries.values()]
    edges = [_relation_to_edge(rel) for rel in all_relations]

    result = {"nodes": nodes, "edges": edges}
    await cache.set(cache_key, result, _CACHE_TTL)
    return result


async def get_shortest_path(  # noqa: PLR0912, PLR0915
    db: AsyncSession,
    source_id: int,
    target_id: int,
) -> dict[str, Any]:
    """计算并返回两个节点间的最短路径.

    使用BFS算法在关系图谱中查找最短路径。

    Args:
        db: 异步数据库会话
        source_id: 起始节点ID
        target_id: 目标节点ID

    Returns:
        dict: 包含 path_nodes, path_edges 和 path_length 的最短路径数据
    """
    cache_key = _build_graph_cache_key(
        "shortest_path",
        {"source_id": source_id, "target_id": target_id},
    )
    cache = get_unified_cache()
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    if source_id == target_id:
        entry_result = await db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.id == source_id)
            .options(selectinload(KnowledgeEntry.tags))
        )
        entry = entry_result.scalar_one_or_none()
        if not entry:
            return {"path_nodes": [], "path_edges": [], "path_length": 0}
        node = _entry_to_node(entry)
        return {"path_nodes": [node], "path_edges": [], "path_length": 0}

    adjacency: dict[int, list[tuple[int, EntryRelation]]] = {}

    all_relations_result = await db.execute(
        select(EntryRelation)
    )
    all_relations = list(all_relations_result.scalars().all())

    for rel in all_relations:
        src = rel.source_entry_id
        tgt = rel.target_entry_id
        if src not in adjacency:
            adjacency[src] = []
        if tgt not in adjacency:
            adjacency[tgt] = []
        adjacency[src].append((tgt, rel))
        adjacency[tgt].append((src, rel))

    if source_id not in adjacency or target_id not in adjacency:
        return {"path_nodes": [], "path_edges": [], "path_length": -1}

    queue: deque[int] = deque([source_id])
    visited: set[int] = {source_id}
    parent: dict[int, tuple[int, EntryRelation] | None] = {source_id: None}

    while queue:
        current = queue.popleft()
        if current == target_id:
            break
        for neighbor, rel in adjacency.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = (current, rel)
                queue.append(neighbor)

    if target_id not in parent:
        return {"path_nodes": [], "path_edges": [], "path_length": -1}

    path_node_ids: list[int] = []
    path_edges: list[dict[str, Any]] = []
    current: int = target_id
    while current is not None and current in parent:
        path_node_ids.append(current)
        parent_info = parent[current]
        if parent_info is not None:
            _prev_node, rel = parent_info
            path_edges.append(_relation_to_edge(rel))
        current = parent_info[0] if parent_info else (
            None
            if current == source_id
            else parent.get(current, (None,))[0]
        )

    path_node_ids.reverse()

    entries_result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.id.in_(path_node_ids))
        .options(selectinload(KnowledgeEntry.tags))
    )
    entries_map: dict[int, KnowledgeEntry] = {
        e.id: e for e in entries_result.scalars().all()
    }

    path_nodes = [
        _entry_to_node(entries_map[nid])
        for nid in path_node_ids
        if nid in entries_map
    ]
    path_edges.reverse()

    result_data: dict[str, Any] = {
        "path_nodes": path_nodes,
        "path_edges": path_edges,
        "path_length": len(path_nodes) - 1,
    }
    await cache.set(cache_key, result_data, _CACHE_TTL)
    return result_data


async def get_graph_data_public(
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """公开接口：从数据库获取图谱数据.

    Args:
        filters: 筛选条件字典

    Returns:
        dict: 包含 nodes 和 edges 的图谱数据
    """
    params = filters or {}
    async with get_async_db_session() as db:
        return await get_graph_data(
            db,
            category_filters=params.get("category_filters"),
            tag_filters=params.get("tag_filters"),
            relation_type_filters=params.get("relation_type_filters"),
            search_query=params.get("search_query"),
            entry_ids=params.get("entry_ids"),
        )


async def get_node_neighbors_public(
    entry_id: int, depth: int = 1
) -> dict[str, Any]:
    """公开接口：获取节点邻居.

    Args:
        entry_id: 中心节点ID
        depth: 邻居深度

    Returns:
        dict: 邻居图谱数据
    """
    async with get_async_db_session() as db:
        return await get_node_neighbors(db, entry_id, depth)


async def get_shortest_path_public(
    source_id: int, target_id: int
) -> dict[str, Any]:
    """公开接口：计算最短路径.

    Args:
        source_id: 起始节点ID
        target_id: 目标节点ID

    Returns:
        dict: 最短路径数据
    """
    async with get_async_db_session() as db:
        return await get_shortest_path(db, source_id, target_id)
