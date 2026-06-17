"""知识图谱可视化服务模块.

提供图谱数据查询、邻居节点发现和最短路径计算功能，
包含数据缓存机制以减少重复计算与数据库查询。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: hashlib
import hashlib
# 导入模块: json
import json
# 导入模块: from collections
from collections import deque
# 导入模块: from typing
from typing import Any

# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import select
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession
# 导入模块: from sqlalchemy.orm
from sqlalchemy.orm import selectinload

# 导入模块: from app.database
from app.database import get_async_db_session
# 导入模块: from app.models.entry_relation
from app.models.entry_relation import EntryRelation, RelationType
# 导入模块: from app.models.knowledge_entry
from app.models.knowledge_entry import EntryCategory, KnowledgeEntry
# 导入模块: from app.utils.cache
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


    # 执行 _build_graph_cache_key 函数的核心逻辑
    raw = json.dumps(params, sort_keys=True, ensure_ascii=False, default=str)
    # 返回处理结果
    return f"kg:{prefix}:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def _entry_to_node(entry: KnowledgeEntry) -> dict[str, Any]:
    """将知识条目模型转换为图谱节点格式.

    Args:
        entry: 知识条目模型实例

    Returns:
        dict: 节点数据
    """
    # 初始化变量 tag_names
    tag_names = [tag.name for tag in entry.tags] if entry.tags else []
    # 初始化变量 relations_count
    relations_count = (
        len(entry.outgoing_relations) + len(entry.incoming_relations)
    )
    # 初始化变量 category_str
    category_str = (
        entry.category.value
        # 条件判断：处理业务逻辑
        if isinstance(entry.category, EntryCategory)
        else str(entry.category)
    )
    # 返回处理结果
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
    # 函数 _calculate_node_size 的初始化逻辑
    confidence: float | None, relations_count: int


    # 执行 _calculate_node_size 函数的核心逻辑
) -> float:
    # 初始化变量 base
    base = 10.0
    # 初始化变量 confidence_bonus
    confidence_bonus = (confidence or 0.5) * 8.0
    # 初始化变量 relation_bonus
    relation_bonus = min(relations_count * 0.8, 12.0)
    # 初始化变量 size
    size = base + confidence_bonus + relation_bonus
    # 返回处理结果
    return round(min(max(size, 8.0), 30.0), 1)


def _relation_to_edge(rel: EntryRelation) -> dict[str, Any]:
    """将条目关系模型转换为图谱边格式.

    Args:
        rel: 条目关系模型实例

    Returns:
        dict: 边数据
    """
    # 初始化变量 rel_type_str
    rel_type_str = (
        re        # 条件判断：处理业务逻辑
l.relation_type.value
        # 条件判断: 检查 isinstance(rel.relation_type, RelationTy
        if isinstance(rel.relation_type, RelationType)
        else str(rel.relation_type)
    )
    # 返回处理结果
    return {
        "source": rel.source_entry_id,
        "target": rel.target_entry_id,
        "type": rel_type_str,
        "label": RELATION_LABELS.get(rel_type_str, rel_type_str),
        "lineStyle": RELATION_LINE_STYLES.get(rel_type_str, "solid"),
    }


async def get_graph_data(  # noqa: PLR0913
    # 函数 get_graph_data 的初始化逻辑
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
    # 初始化变量 cache_params
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
    # 初始化变量 cache_key
    cache_key = _build_graph_cache_key("graph_data", cache_params)
    # 初始化变量 cache
    cache = get_unified_cach    # 条件判断：处理业务逻辑
e()
    # 初始化变量 cached
    cached = await cache.get(cache_key)
    # 条件判断: 检查 cached is not None
    if cached is not None:
        # 记录日志信息
        logger.debug(f"图谱数据缓存命中: {cache_key}")
        # 返回处理结果
        return cached

    # 初始化变量 entry_stmt
    entry_stmt = select(KnowledgeEntry).options(
        selectinload(KnowledgeEntry.tags),
        selectinload(KnowledgeEntry.outgoing_relations)
        .selectinload(EntryRelation.target_entry),
        selectinload(KnowledgeEntry.incoming_relati
    # 条件判断：处理业务逻辑
ons)
        .selectinload(EntryRelation.source_entry),
    )

    # 条件判断: 检查 en    # 条件判断：处理业务逻辑
    if en    # 条件判断：处理业务逻辑
try_ids:
        # 初始化变量 entry_stmt
        entry_stmt = entry_stmt.where(KnowledgeEntry.id.in_(entry_ids))
    # 条件判断: 检查 category_filters
    if category_filters:
            # 条件判断：处理业务逻辑
entry_stmt = entry_stmt.where(
            KnowledgeEntry.category.in_(category_filters)
        )
    # 条件判断: 检查 search_query
    if search_query:
        # 初始化变量 entry_stmt
        entry_stmt = entry_stmt.where(
            KnowledgeEntry.title.ilike(
    # 条件判断：处理业务逻辑
f"%{search_query}%")
        )

    # 初始化变量 result
    result = await db            # 条件判断：处理业务逻辑
.execute(entry_stmt)
    # 初始化变量 entries
    entries = list(result.scalars().all())

    # 条件判断: 检查 tag_filters
    if tag_filters:
        # 初始化变量 entries
        entries = [
            e for e in entries
            # 条件判断: 检查 any(tag.name in tag_filters for tag in e
            if any(tag.name in tag_filters for tag in e.tags)
        ]

    # 初始化变量 entry_id_set
    entry_id_set = {e.id for e in entries}
    nodes: list[dict[str, Any]] = []
    # 循环遍历：处理业务逻辑
    for entry in entries:
        # 初始化变量 node
        node = _entry_to_node(entry)
        nodes.append(no    # 条件判断：处理业务逻辑
de)

    # 初始化变量 relation_stmt
    relation_stmt = select(EntryRelation).options(
        selectinload(EntryRelation.source_entry),
        selectinload(EntryRelation.target_entry),
    )
    # 条件判断: 检查 relation_type_filters
    if relation_type_filters:
        # 初始化变量 relation_stmt
        relation_stmt = relation_stmt.where(
            EntryRelation.relation_type.in_(relation_type_filters)
        )

    # 初始化变量 rel_result
    rel_result = await db.execute(relati        # 条件判断：处理业务逻辑
on_stmt)
    # 初始化变量 all_relations
    all_relations = list(rel_result.scalars().all())

    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[int, i    # 循环遍历：处理业务逻辑
nt, str]] = set()
    # 遍历: for rel in all_relations:
    for rel in all_relations:
        # 条件判断: 检查 (
        if (
            rel.source_entry_id in entry_id_set
            and            # 条件判断：处理业务逻辑
 rel.target_entry_id in entry_id_set
        ):
            # 初始化变量 edge_key
            edge_key = (
                rel.source_entry_id,
                rel.target_entry_id,
                rel.relation_type.value,
            )
            # 条件判断: 检查 edge_key not in seen_edges
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append(_relation_to_edge(rel))

    graph_data: dict[str, Any] = {"nodes": nodes, "edges": edges}
    # 异步等待操作完成
    await cache.set(cache_key, graph_data, _CACHE_TTL)
    # 记录日志信息
    logger.info(f"图谱数据已缓存: nodes={len(nodes)}, edges={len(edges)}")
    # 返回处理结果
    return graph_data


async def get_node_neighbors(
    # 函数 get_node_neighbors 的初始化逻辑
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

    Return    # 条件判断：处理业务逻辑
s:
        dict: 包含 nodes 和 edges 的邻居图谱数据
    """
    # 初始化变量 cache_key
    cache_key = _build_graph_cache_key(
        "neighbors", {"entry_id": entry_id, "depth": depth}
    )
    # 初始化变量 cache
    cache = get_unified_cache()
    # 初始化变量 cached
    cached = await cache.get(cache_key)
    # 条件判断: 检查 cached is not None
    if cached is not None:
        # 返回处理结果
        return cached

    # 初始化变量 entry_result
    entry_result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.id == entry_id)
        .o    # 条件判断：处理业务逻辑
ptions(
            selectinload(KnowledgeEntry.tags),
            selectinload(KnowledgeEntry.outgoing_relations),
            selectinload(KnowledgeEntry.incoming_relations),
        )
    )
    # 初始化变量 center_entry
    center_entry = entry_result.scalar_one_or_none()
    # 条件判断: 检查 not center_entry
    if not center_entry:
        # 返回处理结果
        return {"nodes": [], "edges": []}

    visited: set[int] = {entry_id}
    current_layer: set[int] = {entry_id}
    all_entries: dict[int, KnowledgeEntry] = {entry_id: center_entry}
    all_
    # 循环遍历：处理业务逻辑
relations: list[EntryRelation] = []

    # 遍历: for _d in range(depth):
    for _d in range(depth):
        next_layer: set[int] = s
        # 循环遍历：处理业务逻辑
et()
        layer_relations: list[EntryRelation] = []

        # 遍历: for node_id in current_layer:
        for node_id in current_layer:
            # 初始化变量 node_relations
            node_relations = await db.execute(
                select(EntryRelation).where(
                    (En                    # 条件判断：处理业务逻辑
tryRelation.source_entry_id == node_id)
                    | (EntryRelation.target                # 条件判断：处理业务逻辑
_entry_id == node_id)
                )
            )
            # 遍历: for rel in node_relations.scalars().all():
            for rel in node_relations.scalars().all():
                # 初始化变量 neighbor_id
                neighbor_id = (
                    rel.target_entry_id
                    # 条件判断: 检查 rel.source_entry_id == node_id
                    if rel.source_entry_id == node_id
                    else rel.source_entry_id
                )
                # 条件判断: 检查 neighbor_id not in visited
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    next_layer.add(neighbor_id)
                    # 初始化变量 edge_tuple
                    edge_tuple = (
                        rel.source_entry_id,
                        rel.target_entry_id,
                        str(rel.relation_type.value),
                          # 条件判断：处理业务逻辑
              )
                    # 初始化变量 existing_edges
                    existing_edges = {
                    
        # 条件判断：处理业务逻辑
    (
                            r.source_entry_id,
                            r.target_entry_id,
                            # 循环遍历：处理业务逻辑
                        str(r.relation_type.value),
                        )
                        # 遍历: for r in layer_relations
                        for r in layer_relations
                    }
                    # 条件判断: 检查 edge_tuple not in existing_edges
                    if edge_tuple not in existing_edges:
                        layer_relations.append(rel)

        # 条件判断: 检查 next_layer
        if next_layer:
            # 初始化变量 neighbors_result
            neighbors_result = await db.execute(
                select(KnowledgeEntry)
                .where            # 循环遍历：处理业务逻辑
(KnowledgeEntry.id.in_(list(next_layer)))
                .options(selectinload(KnowledgeEntry.tags))
            )
            # 遍历: for entry in neighbors_result.scalars().all():
            for entry in neighbors_result.scalars().all():
                all_entries[entry.id] = entry

        all_relations.extend(layer_relations)
        # 初始化变量 current_layer
        current_layer = next_layer

    # 初始化变量 nodes
    nodes = [_entry_to_node(entry) for entry in all_entries.values()]
    # 初始化变量 edges
    edges = [_relation_to_edge(rel) for rel in all_relations]

    # 初始化变量 result
    result = {"nodes": nodes, "edges": edges}
    # 异步等待操作完成
    await cache.set(cache_key, result, _CACHE_TTL)
    # 返回处理结果
    return result


async def get_shortest_path(  # noqa: PLR0912, PLR0915
    # 函数 get_shortest_path 的初始化逻辑
    db: AsyncSession,
    source_id: int,
    target_id: int,
) -> dict[str, Any]:
    """计算并返回两个节点间的最短路径.

    使用BF    # 条件判断：处理业务逻辑
S算法在关系图谱中查找最短路径。

    Args:
   
    # 条件判断：处理业务逻辑
     db: 异步数据库会话
        source_id: 起始节点ID
        target_id: 目标节点ID

    Returns:
        dict: 包含 path_nodes, path_edges 和 path_length 的最短路径数据
    """
    # 初始化变量 cache_key
    cache_key = _build_graph_cache_key(
        "shortest_path",
        {"source_id": source_id, "targ        # 条件判断：处理业务逻辑
et_id": target_id},
    )
    # 初始化变量 cache
    cache = get_unified_cache()
    # 初始化变量 cached
    cached = await cache.get(cache_key)
    # 条件判断: 检查 cached is not None
    if cached is not None:
        # 返回处理结果
        return cached

    # 条件判断: 检查 source_id == target_id
    if source_id == target_id:
        # 初始化变量 entry_result
        entry_result = await db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.id == source_id)
            .options(selectinload(KnowledgeEntry.tags))
        )
        # 初始化变量 entry
        entry = entry_result.scalar_one_or_none()
        # 条件判断: 检查 not entry
        if not entry:
            # 返回处理结果
            return {"path_nodes": [], "path_edges        # 条件判断：处理业务逻辑
": [], "path_length": 0}
        # 初始化变量 node
        node = _en        # 条件判断：处理业务逻辑
try_to_node(entry)
        # 返回处理结果
        return {"path_nodes": [node], "path_edges": [], "path_length": 0}

    adjacency: dict[int, list[tup
    # 条件判断：处理业务逻辑
le[int, EntryRelation]]] = {}

  
    # 循环遍历：处理业务逻辑
  all_relations_result = await db.execute(
        select(EntryRelation)
    )
    # 初始化变量 all_relations
    all_relations = list(all_relations_result.scalars().all())

    # 遍历: for rel in all_relations:
    for rel in all_relations:
        src = rel.source_entry_id
        tgt = rel.target_entry_id
        # 条件判断: 检查 src not in adjacency
        if src not in adjacency:
            adjacen        # 条件判断：处理业务逻辑
cy[src] = []
        # 条件判断: 检查 tgt not in adjacency
        if tgt not in adjacency:
            adjacency[tgt] = []
                    # 条件判断：处理业务逻辑
adjacency[src].append((tgt, rel))
        adjacency[tgt].append((src, rel))

    # 条件判断: 检查 source_id not in adjacency or target_id 
    if source_id not in adjacency or target_id not in adjacency:
        # 返回处理结果
        return {"path_nodes": [], "path_edges": [], "path_length": -1}

    queue: deque[int] = deque([source_id])
    visited: set[int] = {source_id}
    parent: dict[int, tuple[int, EntryRelation] # 循环遍历：处理业务逻辑
| None] = {source_id: None}

    # 循环条件: while queue:
    while queue:
        # 初始化变量 current
        current = queue.popleft()
        # 条件判断: 检查 current == target_id
        if current == target_id:
            break
                # 条件判断：处理业务逻辑
for neighbor, rel in adjacency.get(current, []):
            # 条件判断: 检查 neighbor not in visited
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = (current, rel)
                 # 条件判断：处理业务逻辑
           queue.append(neighbor)

    # 条件判断: 检查 target_id not in parent
    if target_id not in parent:
        # 返回处理结果
        return {"path_nodes": [], "path_edges": [], "path_length": -1}

    path_node_ids: list[int] = []
    path_edges: list[dict[str, Any]] = []
    current: int = target_id
    # 循环条件：处理业务逻辑
    while current is not None and current in parent:
        path_node_ids.append(current)
        # 初始化变量 parent_info
        parent_info = parent[current]
        # 条件判断: 检查 parent_info is not None
        if parent_info is not None:
            _prev_node, rel = parent_info
            path_edges.append(_r        # 条件判断：处理业务逻辑
elation_to_edge(rel))
        # 初始化变量 current
        current = parent_info[0] if parent_info else (
            None
            # 条件判断: 检查 current == source_id
            if current == source_id
            else parent.get(current, (None,))[0]
        )

    path_node_ids.reverse()

    # 初始化变量 entries_result
    entries_result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.id.in_(path_node_ids))
        .options(selectinload(KnowledgeEntry.tags))
         # 循环遍历：处理业务逻辑
   )
    entries_map: dict[int, KnowledgeEntry] = {
        e.id: e for e in entries_result.scalars().all()
    }

    # 初始化变量 path_nodes
    path_nodes = [
        _entry_to_node(entries_map[nid])
        # 遍历: for nid in path_node_ids
        for nid in path_node_ids
        # 条件判断: 检查 nid in entries_map
        if nid in entries_map
    ]
    path_edges.reverse()

    result_data: dict[str, Any] = {
        "path_nodes": path_nodes,
        "path_edges": path_edges,
        "path_length": len(path_nodes) - 1,
    }
    # 异步等待操作完成
    await cache.set(cache_key, result_data, _CACHE_TTL)
    # 返回处理结果
    return result_data


async def get_graph_data_public(
    # 函数 get_graph_data_public 的初始化逻辑
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """公开接口：从数据库获取图谱数据.

    Args:
        filters: 筛选条件字典

    Returns:
        dict: 包含 nodes 和 edges 的图谱数据
    """
    # 初始化变量 params
    params = filters or {}
    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_graph_data(
            db,
            # 初始化变量 category_filters
            category_filters=params.get("category_filters"),
            # 初始化变量 tag_filters
            tag_filters=params.get("tag_filters"),
            # 初始化变量 relation_type_filters
            relation_type_filters=params.get("relation_type_filters"),
            # 初始化变量 search_query
            search_query=params.get("search_query"),
            # 初始化变量 entry_ids
            entry_ids=params.get("entry_ids"),
        )


async def get_node_neighbors_public(
    # 函数 get_node_neighbors_public 的初始化逻辑
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
        # 返回处理结果
        return await get_node_neighbors(db, entry_id, depth)


async def get_shortest_path_public(
    # 函数 get_shortest_path_public 的初始化逻辑
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
        # 返回处理结果
        return await get_shortest_path(db, source_id, target_id)
