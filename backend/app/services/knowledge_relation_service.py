"""相关知识推荐服务模块.

基于 LLM 为知识条目推荐相关内容，支持自动建立关联关系和知识图谱构建。
复用 similar_cases.py 的 LLM 调用模式和错误处理机制。
"""

from collections import deque
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry_relation import EntryRelation, RelationType
from app.models.knowledge_entry import KnowledgeEntry
from app.services.ollama_client import get_client
from app.services.prompts import SUGGEST_RELATED_ENTRIES_PROMPT


_MAX_EXISTING_ENTRIES: int = 50
_MAX_CONTENT_SNIPPET_LENGTH: int = 500

_LLM_RELATION_TYPE_MAP: dict[str, RelationType] = {
    "references": RelationType.references,
    "contradicts": RelationType.contradicts,
    "supersedes": RelationType.supersedes,
    "extends": RelationType.extends,
    "depends_on": RelationType.depends_on,
    "similar": RelationType.references,
    "supports": RelationType.depends_on,
}


def _truncate_content(content: str, max_length: int = _MAX_CONTENT_SNIPPET_LENGTH) -> str:
    """截断内容文本至指定长度.

    Args:
        content: 原始内容文本
        max_length: 最大字符长度

    Returns:
        str: 截断后的文本
    """
    if len(content) <= max_length:
        return content
    return content[:max_length] + "..."


def _map_relation_type(relation_type_str: str) -> RelationType:
    """将LLM返回的关系类型字符串映射为RelationType枚举.

    Args:
        relation_type_str: LLM返回的关系类型字符串

    Returns:
        RelationType: 对应的关系类型枚举值，默认返回references
    """
    return _LLM_RELATION_TYPE_MAP.get(relation_type_str, RelationType.references)


async def find_related_entries(
    db: AsyncSession,
    entry_id: int,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """使用LLM查找与指定条目最相关的知识条目.

    首先通过entry_id准确获取目标条目的完整内容信息，
    然后调用LLM使用专门的推荐提示词模板来推荐相关知识条目，
    最后对LLM返回的推荐结果进行严格验证。

    Args:
        db: 异步数据库会话
        entry_id: 目标知识条目ID
        top_k: 返回的最大推荐条目数（默认5）

    Returns:
        list[dict]: 推荐条目列表，每个元素包含:
            - entry_id: 条目ID
            - title: 条目标题
            - relation_type: 关系类型字符串
            - similarity: 相似度评分（0-1）
            - reason: 推荐理由文本

    Raises:
        ValueError: entry_id无效或为None
        LookupError: 目标条目不存在

    Example:
        >>> results = await find_related_entries(db, 1, top_k=3)
        >>> results[0]["entry_id"]
        2
    """
    if not isinstance(entry_id, int) or entry_id <= 0:
        msg = f"无效的条目ID: {entry_id}"
        raise ValueError(msg)

    target_entry = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    target_entry = target_entry.scalar_one_or_none()
    if not target_entry:
        msg = f"知识条目不存在: entry_id={entry_id}"
        raise LookupError(msg)

    logger.info(
        "开始查找相关知识条目: entry_id={}, title={}, top_k={}",
        entry_id,
        target_entry.title,
        top_k,
    )

    existing_result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.id != entry_id)
        .limit(_MAX_EXISTING_ENTRIES)
    )
    existing_entries: list[KnowledgeEntry] = list(existing_result.scalars().all())

    if not existing_entries:
        logger.info("知识库中没有其他条目可供推荐: entry_id={}", entry_id)
        return []

    existing_entries_str = "\n".join(
        f"- ID: {e.id}, 标题: {e.title}, 分类: {e.category.value if e.category else 'unknown'}, "
        f"摘要: {e.summary or '无摘要'}"
        for e in existing_entries
    )

    prompt = SUGGEST_RELATED_ENTRIES_PROMPT.format(
        entry_title=target_entry.title,
        entry_category=target_entry.category.value if target_entry.category else "unknown",
        entry_summary=target_entry.summary or "无摘要",
        entry_content_snippet=_truncate_content(target_entry.content),
        existing_entries=existing_entries_str,
        top_k=top_k,
    )

    try:
        client = get_client()
        data = await client.generate_json(prompt, field="related_entries")
        raw_entries: list[dict] = []
        if isinstance(data, list):
            raw_entries = data
        elif isinstance(data, dict):
            raw_entries = data.get("related_entries", [])
    except Exception as e:  # noqa: BLE001
        logger.error(f"LLM推荐相关知识条目失败: entry_id={entry_id}, error={e}")
        return []

    if not raw_entries:
        logger.info("LLM未找到相关知识条目: entry_id={}", entry_id)
        return []

    valid_entry_ids: set[int] = {e.id for e in existing_entries}
    results: list[dict[str, Any]] = []

    for item in raw_entries:
        if not isinstance(item, dict):
            logger.warning("跳过非字典格式的推荐结果: {}", item)
            continue

        recommended_id = item.get("entry_id")
        if not isinstance(recommended_id, int) or recommended_id <= 0:
            logger.warning("跳过无效的推荐条目ID: {}", recommended_id)
            continue

        if recommended_id not in valid_entry_ids:
            logger.warning(
                "推荐条目ID不在现有条目列表中: entry_id={}, recommended_id={}",
                entry_id,
                recommended_id,
            )
            continue

        similarity = item.get("similarity", 0.0)
        if not isinstance(similarity, (int, float)) or similarity < 0 or similarity > 1:
            similarity = 0.0
        similarity = round(float(similarity), 4)

        recommended_entry = next(
            (e for e in existing_entries if e.id == recommended_id), None
        )

        results.append({
            "entry_id": recommended_id,
            "title": recommended_entry.title if recommended_entry else "",
            "relation_type": item.get("relation_type", "similar"),
            "similarity": similarity,
            "reason": item.get("reason", ""),
        })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    results = results[:top_k]

    logger.info(
        "知识条目推荐完成: entry_id={}, 返回结果数={}",
        entry_id,
        len(results),
    )
    return results


async def auto_link_entries(
    db: AsyncSession,
    entry_id: int,
) -> int:
    """自动为指定条目创建知识关联关系.

    调用find_related_entries方法获取推荐结果，根据推荐结果创建EntryRelation记录，
    确保数据完整性和一致性。

    Args:
        db: 异步数据库会话
        entry_id: 源知识条目ID

    Returns:
        int: 成功创建的关联关系数量

    Raises:
        ValueError: entry_id无效
        LookupError: 目标条目不存在

    Example:
        >>> count = await auto_link_entries(db, 1)
        >>> count
        3
    """
    if not isinstance(entry_id, int) or entry_id <= 0:
        msg = f"无效的条目ID: {entry_id}"
        raise ValueError(msg)

    target_exists = await db.execute(
        select(KnowledgeEntry.id).where(KnowledgeEntry.id == entry_id)
    )
    if not target_exists.scalar_one_or_none():
        msg = f"知识条目不存在: entry_id={entry_id}"
        raise LookupError(msg)

    logger.info("开始自动建立关联关系: entry_id={}", entry_id)

    recommendations = await find_related_entries(db, entry_id, top_k=5)
    if not recommendations:
        logger.info("无推荐条目可用于自动关联: entry_id={}", entry_id)
        return 0

    created_count = 0
    for rec in recommendations:
        target_id = rec["entry_id"]
        relation_type_str = rec["relation_type"]
        relation_type = _map_relation_type(relation_type_str)

        existing = await db.execute(
            select(EntryRelation).where(
                EntryRelation.source_entry_id == entry_id,
                EntryRelation.target_entry_id == target_id,
            )
        )
        if existing.scalar_one_or_none():
            logger.debug(
                "关联关系已存在，跳过: source={}, target={}",
                entry_id,
                target_id,
            )
            continue

        try:
            db_relation = EntryRelation(
                source_entry_id=entry_id,
                target_entry_id=target_id,
                relation_type=relation_type,
            )
            db.add(db_relation)
            created_count += 1
            logger.info(
                "关联关系已创建: source={}, target={}, type={}",
                entry_id,
                target_id,
                relation_type.value,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(
                "创建关联关系失败: source={}, target={}, error={}",
                entry_id,
                target_id,
                e,
            )

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"提交关联关系事务失败: entry_id={entry_id}, error={e}")
        raise

    logger.info(
        "自动关联完成: entry_id={}, 创建了{}条关联关系",
        entry_id,
        created_count,
    )
    return created_count


async def build_knowledge_graph(
    db: AsyncSession,
) -> dict[str, list[dict[str, Any]]]:
    """构建完整的知识图谱数据结构.

    查询所有知识条目和所有关系记录，构建节点和边结构。

    Args:
        db: 异步数据库会话

    Returns:
        dict: 包含nodes和edges的知识图谱数据:
            - nodes: [{id, title, category}]
            - edges: [{source, target, type}]

    Example:
        >>> graph = await build_knowledge_graph(db)
        >>> len(graph["nodes"])
        15
        >>> len(graph["edges"])
        23
    """
    logger.info("开始构建知识图谱")

    entries_result = await db.execute(select(KnowledgeEntry))
    entries: list[KnowledgeEntry] = list(entries_result.scalars().all())

    nodes: list[dict[str, Any]] = [
        {
            "id": entry.id,
            "title": entry.title,
            "category": entry.category.value if entry.category else "unknown",
        }
        for entry in entries
    ]

    relations_result = await db.execute(select(EntryRelation))
    relations: list[EntryRelation] = list(relations_result.scalars().all())

    edges: list[dict[str, Any]] = [
        {
            "source": rel.source_entry_id,
            "target": rel.target_entry_id,
            "type": rel.relation_type.value,
        }
        for rel in relations
    ]

    logger.info(
        "知识图谱构建完成: 节点数={}, 边数={}",
        len(nodes),
        len(edges),
    )
    return {"nodes": nodes, "edges": edges}


async def traverse_graph(
    db: AsyncSession,
    start_entry_id: int,
    relation_types: list[str] | None = None,
    max_depth: int = 3,
) -> list[dict[str, Any]]:
    """使用广度优先搜索(BFS)算法遍历知识图谱.

    从起始条目出发，沿指定的关系类型逐层遍历可达节点。

    Args:
        db: 异步数据库会话
        start_entry_id: 起始知识条目ID
        relation_types: 可遍历的关系类型列表，None表示所有类型
        max_depth: 最大遍历深度（默认3）

    Returns:
        list[dict]: 所有从start_entry_id可达的条目及其路径信息，每个元素包含:
            - entry_id: 条目ID
            - title: 条目标题
            - category: 条目分类
            - depth: 距离起始节点的深度
            - path: 从起始节点到当前节点的路径 [(entry_id, relation_type), ...]

    Raises:
        ValueError: 参数无效(start_entry_id <= 0, max_depth <= 0)
        LookupError: 起始条目不存在

    Example:
        >>> results = await traverse_graph(db, 1, ["references", "extends"], max_depth=2)
        >>> results[0]["entry_id"]
        1
    """
    if not isinstance(start_entry_id, int) or start_entry_id <= 0:
        msg = f"无效的起始条目ID: {start_entry_id}"
        raise ValueError(msg)
    if max_depth <= 0:
        msg = f"遍历深度必须大于0: max_depth={max_depth}"
        raise ValueError(msg)

    start_entry = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == start_entry_id)
    )
    start_entry = start_entry.scalar_one_or_none()
    if not start_entry:
        msg = f"起始知识条目不存在: start_entry_id={start_entry_id}"
        raise LookupError(msg)

    valid_types: set[str] | None = None
    if relation_types:
        valid_types = set(relation_types)

    logger.info(
        "开始遍历知识图谱: start_entry_id={}, max_depth={}, relation_types={}",
        start_entry_id,
        max_depth,
        relation_types,
    )

    all_relations_result = await db.execute(select(EntryRelation))
    all_relations: list[EntryRelation] = list(all_relations_result.scalars().all())

    adjacency: dict[int, list[tuple[int, str]]] = {}
    for rel in all_relations:
        rel_type = rel.relation_type.value
        if valid_types and rel_type not in valid_types:
            continue
        adjacency.setdefault(rel.source_entry_id, []).append(
            (rel.target_entry_id, rel_type)
        )
        adjacency.setdefault(rel.target_entry_id, []).append(
            (rel.source_entry_id, rel_type)
        )

    all_entries_result = await db.execute(select(KnowledgeEntry))
    entry_map: dict[int, KnowledgeEntry] = {
        e.id: e for e in all_entries_result.scalars().all()
    }

    visited: set[int] = {start_entry_id}
    queue: deque[tuple[int, int, list[tuple[int, str]]]] = deque()
    queue.append((start_entry_id, 0, []))

    results: list[dict[str, Any]] = []

    entry = entry_map.get(start_entry_id)
    if entry:
        results.append({
            "entry_id": start_entry_id,
            "title": entry.title,
            "category": entry.category.value if entry.category else "unknown",
            "depth": 0,
            "path": [],
        })

    while queue:
        current_id, depth, path = queue.popleft()

        if depth >= max_depth:
            continue

        for neighbor_id, rel_type in adjacency.get(current_id, []):
            if neighbor_id in visited:
                continue

            visited.add(neighbor_id)
            new_path: list[tuple[int, str]] = list(path)
            new_path.append((current_id, rel_type))

            neighbor_entry = entry_map.get(neighbor_id)
            if neighbor_entry:
                results.append({
                    "entry_id": neighbor_id,
                    "title": neighbor_entry.title,
                    "category": (
                        neighbor_entry.category.value
                        if neighbor_entry.category
                        else "unknown"
                    ),
                    "depth": depth + 1,
                    "path": new_path,
                })

            queue.append((neighbor_id, depth + 1, new_path))

    logger.info(
        "知识图谱遍历完成: start_entry_id={}, 访问节点数={}, 最大深度={}",
        start_entry_id,
        len(results),
        max_depth,
    )
    return results
