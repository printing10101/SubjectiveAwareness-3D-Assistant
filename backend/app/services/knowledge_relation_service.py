"""相关知识推荐服务模块.

基于 LLM 为知识条目推荐相关内容，支持自动建立关联关系和知识图谱构建。
复用 similar_cases.py 的 LLM 调用模式和错误处理机制。
"""

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

# 导入模块: from app.models.entry_relation
from app.models.entry_relation import EntryRelation, RelationType
# 导入模块: from app.models.knowledge_entry
from app.models.knowledge_entry import KnowledgeEntry
# 导入模块: from app.services.ollama_client
from app.services.ollama_client import get_client
# 导入模块: from app.services.prompts
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
    # 条件判断：处理业务逻辑
    if len(content) <= max_length:
        # 返回处理结果
        return content
    # 返回处理结果
    return content[:max_length] + "..."


def _map_relation_type(relation_type_str: str) -> RelationType:
    """将LLM返回的关系类型字符串映射为RelationType枚举.

    Args:
        relation_type_str: LLM返回的关系类型字符串

    Returns:
        RelationType: 对应的关系类型枚举值，默认返回references
    """
    # 返回处理结果
    return _LLM_RELATION_TYPE_MAP.get(relation_type_str, RelationType.references)


async def find_related_entries(
    # 函数 find_related_entries 的初始化逻辑
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
        # 异步等待操作完成
        >>> results = await find_related_entries(db, 1, top_k=3)
        >>> results[0]["entry_id"]
    # 条件判断：处理业务逻辑
        2
    """
    # 条件判断: 检查 not isinstance(entry_id, int) or entry_i
    if not isinstance(entry_id, int) or entry_id <= 0:
        msg = f"无效的条目ID: {entry_id}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    # 初始化变量 target_entry
    target_entry = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    target_entry     # 条件判断：处理业务逻辑
= target_entry.scalar_one_or_none()
    # 条件判断: 检查 not target_entry
    if not target_entry:
        msg = f"知识条目不存在: entry_id={entry_id}"
        # 抛出异常，处理错误情况
        raise LookupError(msg)

    # 记录日志信息
    logger.info(
        "开始查找相关知识条目: entry_id={}, title={}, top_k={}",
        entry_id,
        target_entry.title,
        top_k,
    )

    # 初始化变量 existing_result
    existing_result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.id != entry_id)
        .limit(_MAX_EXISTING_ENTRIES)
    )
    existing_entries: list[Kn
    # 条件判断：处理业务逻辑
owledgeEntry] = list(existing_result.scalars().all())

    # 条件判断: 检查 not existing_entries
    if not existing_entries:
        # 记录日志信息
        logger.info("知识库中没有其他条目可供推荐: entry_id={}", entry_id)
        # 返回处理结果
        return []

    # 初始化变量 existing_entries_str
    existing_entries_str = "\n".join(
        f"- ID: {e.id}, 标题: {e.title}, 分类: {e.category.value if e.category else 'unknown'}, "
        f"摘要: {e.summary or '无摘要'}"
        # 循环遍历：处理业务逻辑
        for e in existing_entries
    )

    # 初始化变量 prompt
    prompt = SUGGEST_RELATED_ENTRIES_PROMPT.format(
        # 初始化变量 entry_title
        entry_title=target_entry.title,
        # 初始化变量 entry_category
        entry_category=target_entry.category.value if target_entry.category else "unknown",
        # 初始化变量 entry_summary
        entry_summary=target_entry.summary or "无摘要",
        # 初始化变量 entry_content_snippet
        entry_content_snippet=_truncate_content(target_entry.content),
        # 初始化变量 existing_entries
        existing_entries=existing_entries_str,
        # 初始化变量 top_k
        top_k=top_k,
    )

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 client
        client = get_client()
        # 初始化变量 data
        data = await client.generate_js        # 条件判断：处理业务逻辑
on(prompt, field="related_entries")
        raw_entries: list[dict] = []
        # 条件判断: 检查 isinstance(data, list)
        if isinstance(data, list):
            # 初始化变量 raw_entries
            raw_entries = data
        # 条件判断: 检查 elisinstance(data, dict)
        elif isinstance(data, dict):
            # 初始化变量 raw_entries
            raw_entries = data.get("related_entries", [])
    # 捕获并处理异常
    except Exception as e:  # noqa: B
    # 条件判断：处理业务逻辑
LE001
        # 记录日志信息
        logger.error(f"LLM推荐相关知识条目失败: entry_id={entry_id}, error={e}")
        # 返回处理结果
        return []

    # 条件判断: 检查 not raw_entries
    if not raw_entries:
        # 记录日志信息
        logger.info("LLM未找到相关知识条目: entry_id={}", entry_id)
        # 返回处理结果
        return []

    valid_entry_ids:        # 条件判断：处理业务逻辑
 set[int] = {e.id for e in existing_entries}
    results: list
    # 循环遍历：处理业务逻辑
[dict[str, Any]] = []

    # 遍历: for item in raw_entries:
    for item in raw_entries:
        # 条件判断: 检查 not isinstanc        # 条件判断：处理业务逻辑
        if not isinstanc        # 条件判断：处理业务逻辑
e(item, dict):
            # 记录日志信息
            logger.warning("跳过非字典格式的推荐结果: {}", item)
            continue

        # 初始化变量 recommended_id
        recommended_id = item.get("entry_i
        # 条件判断：处理业务逻辑
d")
        # 条件判断: 检查 not isinstance(recommended_id, int) or r
        if not isinstance(recommended_id, int) or recommended_id <= 0:
            # 记录日志信息
            logger.warning("跳过无效的推荐条目ID: {}", recommended_id)
            continue

        # 条件判断: 检查 recommended_id not in valid_entry_ids
        if recommended_id not in valid_entry_ids:
            # 记录日志信息
            logger.warning(
                "推荐条目ID不在现有条目        # 条件判断：处理业务逻辑
列表中: entry_id={}, recommended_id={}",
                entry_id,
                recommended_id,
            )
            continue

        # 初始化变量 similarity
        similarity = item.get("similarity", 0.0)
        # 条件判断: 检查 not isinstance(similarity, (int, float))
        if not isinstance(similarity, (int, float)) or similarity < 0 or similarity > 1:
            # 初始化变量 similarity
            similarity = 0.0
        # 初始化变量 similarity
        similarity = round(float(similarity), 4)

        # 初始化变量 recommended_entry
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
    # 初始化变量 results
    results = results[:top_k]

    # 记录日志信息
    logger.info(
        "知识条目推荐完成: entry_id={}, 返回结果数={}",
        entry_id,
        len(results),
    )
    # 返回处理结果
    return results


async def auto_link_entries(
    # 函数 auto_link_entries 的初始化逻辑
    db: AsyncSession,
    entry_id: int,
) -> int:
    """自动为指定条目创建知识关联关系.

    调用find_related_entries方法获取推荐结果，根据推荐结果创建EntryRelation记录，
    确保数据完整性和一致性。

    Args:
        db: 异步数据库会话
        entry_id: 源知识条目ID

    Retur    # 条件判断：处理业务逻辑
ns:
        int: 成功创建的关联关系数量

    Raises:
        ValueError: entry_id无效
        LookupError: 目标条目不存在

    Example:
        # 异步等待操作完成
        >>> count = await auto_link_entries(db, 1)
        >>> count
        3
    """
    # 条件判断: 检查 not isinst    # 条件判断：处理业务逻辑
    if not isinst    # 条件判断：处理业务逻辑
ance(entry_id, int) or entry_id <= 0:
        msg = f"无效的条目ID: {entry_id}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    # 初始化变量 target_exists
    target_exists = await db.execute(
        select(KnowledgeEntry.id).where(KnowledgeEntry.id == entry_id)
    )
    # 条件判断: 检查 not t    # 条件判断：处理业务逻辑
    if not t    # 条件判断：处理业务逻辑
arget_exists.scalar_one_or_none():
        msg = f"知识条目不存在: entry_id={entry_id}"
        # 抛出异常，处理错误情况
        raise LookupError(msg)

    # 记录日志信息
    logger.info("开始自动建立关联关系: entry_id={}", entry_id)

    # 初始化变量 recommendations
    recommendations = await find_related_entries(db, entry_id, top_k=5)
    # 条件判断: 检查 not recommendations
    if not recommendations:
        # 记录日志信息
        logger.info("无推荐条目可用于自动关联: entry_id={}", entry_id)
        # 返回处理结果
        return 0

    # 初始化变量 created_count
    created_count = 0
    # 遍历: for rec in recommendations:
    for rec in recommendations:
        # 初始化变量 target_id
        target_id = rec["entry_id"]
        # 初始化变量 relation_type_str
        relation_type_str = rec["relation_type"]
        # 初始化变量 relation_type
        relation_type = _ma        # 条件判断：处理业务逻辑
p_relation_type(relation_type_str)

        # 初始化变量 existing
        existing = await db.execute(
            select(EntryRelation).where(
                EntryRelation.source_entry_id == entry_id,
                EntryRelation.target_entry_id == target_id,
            )
        )
        # 条件判断: 检查 existing.scalar_one_or_none()
        if existing.scalar_one_or_none():
            # 记录日志信息
            logger.debug(
                "关联关系已存在，跳过: source={}, target={}",
                entry_id,
                target_id,
            )
            continue

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 db_relation
            db_relation = EntryRelation(
                # 初始化变量 source_entry_id
                source_entry_id=entry_id,
                # 初始化变量 target_entry_id
                target_entry_id=target_id,
                # 初始化变量 relation_type
                relation_type=relation_type,
            )
            db.add(db_relation)
            created_count += 1
            # 记录日志信息
            logger.info(
                "关联关系已创建: source={}, target={}, type={}",
                entry_id,
                target_id,
                relation_type.value,
            )
        # 捕获并处理异常
        except Exception as e:  # noqa: BLE001
            logger.error(
                "创建关联关系失败: source={}, target={}, error={}",
                entry_id,
                target_id,
                e,
            )

    # 尝试执行可能抛出异常的代码
    try:
        # 异步等待操作完成
        await db.commit()
    # 捕获异常：处理业务逻辑
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"提交关联关系事务失败: entry_id={entry_id}, error={e}")
        raise

    # 记录日志信息
    logger.info(
        "自动关联完成: entry_id={}, 创建了{}条关联关系",
        entry_id,
        created_count,
    )
    # 返回处理结果
    return created_count


async def build_knowledge_graph(
    # 函数 build_knowledge_graph 的初始化逻辑
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
        # 异步等待操作完成
        >>> graph = await build_knowledge_graph(db)
        >>> len(graph["nodes"])
        15
        >>> len(graph["edges"])
        23
    """
    # 记录日志信息
    logger.info("开始构建知识图谱")

    # 初始化变量 entries_result
    entries_result = await db.execute(select(KnowledgeEntry))
    entries: list[KnowledgeEntry] = list(entries_result.scalars().all())

    nodes: list[dict[str, Any]] = [
        {
            "id": entry.id,
            "title": entry.title,
            "category": entry.category.value if         # 循环遍历：处理业务逻辑
entry.category else "unknown",
        }
        # 遍历: for entry in entries
        for entry in entries
    ]

    # 初始化变量 relations_result
    relations_result = await db.execute(select(EntryRelation))
    relations: list[EntryRelation] = list(relations_result.scalars().all())

    edges: list[dict[str, Any]] = [
        {
            "source": rel.source_entry_id,
            "target": rel.target_en        # 循环遍历：处理业务逻辑
try_id,
            "type": rel.relation_type.value,
        }
        # 遍历: for rel in relations
        for rel in relations
    ]

    # 记录日志信息
    logger.info(
        "知识图谱构建完成: 节点数={}, 边数={}",
        len(nodes),
        len(edges),
    )
    # 返回处理结果
    return {"nodes": nodes, "edges": edges}


async def traverse_graph(
    # 函数 traverse_graph 的初始化逻辑
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
            - path: 从起始节点到当前节点的路径 [(entry_id, rel    # 条件判断：处理业务逻辑
ation_type), ...]

    Raises:
        ValueError: 参数无效(start_entry_id <= 0, max_depth <= 0)
        LookupError: 起始条目不存在

     # 条件判断：处理业务逻辑
   Example:
        # 异步等待操作完成
        >>> results = await traverse_graph(db, 1, ["references", "extends"], max_depth=2)
        >>> results[0]["entry_id"]
        1
    """
    # 条件判断: 检查 not isinstance(start_entry_id, int) or s
    if not isinstance(start_entry_id, int) or start_entry_id <= 0:
        msg = f"无效的起始条目ID: {sta    # 条件判断：处理业务逻辑
rt_entry_id}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)
    # 条件判断: 检查 max_depth <= 0
    if max_depth <= 0:
        msg = f"遍历深度必须大于0: max_depth={max_depth}"
        # 抛出异常，处理错误情况
        raise ValueEr    # 条件判断：处理业务逻辑
ror(msg)

    # 初始化变量 start_entry
    start_entry = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == start_entry_id)
    )
    # 初始化变量 start_entry
    start_entry = start_entry.scalar_one_or_none()
    # 条件判断: 检查 not start_entry
    if not start_entry:
        msg = f"起始知识条目不存在: start_entry_id={start_entry_id}"
        # 抛出异常，处理错误情况
        raise LookupError(msg)

    valid_types: set[str] | None = None
    # 条件判断: 检查 relation_types
    if relation_types:
        # 初始化变量 valid_types
        valid_types = set(relation_types)

    # 记录日志信息
    logger.info(
        "开始遍历知识图谱: start_entry_id={}, max_depth={}, relation_types={}",
         # 条件判断：处理业务逻辑
       start_entry_id,
        max_depth,
        relation_types,
    )

    # 初始化变量 all_relations_result
    all_relations_result = await db.execute(select(EntryRelation))
    all_relations: list[EntryRelation] = list(all_rel    # 循环遍历：处理业务逻辑
ations_result.scalars().all())

    adjacency: dict[int, list[tuple[int, str]]] = {}
    # 遍历: for rel in all_relations:
    for rel in all_relations:
        # 初始化变量 rel_type
        rel_type = rel.relation_type.value
        # 条件判断: 检查 valid_types and rel_type not in valid_ty
        if valid_types and rel_type not in valid_types:
            continue
        adjacency.setdefault(rel.source_entry_id, []).append(
            (rel.target_entry_id, rel_type)
        )
        adjacency.setdefault(rel.target_entry_id, []).append(
            (rel.source_entry_id, rel_type)
        )

    # 初始化变量 all_entries_result
    all_entries_result = await db.exec    # 条件判断：处理业务逻辑
ute(select(KnowledgeEntry))
    entry_map: dict[int, KnowledgeEntry] = {
        e.id: e for e in all_entries_result.scalars().all()
    }

    visited: set[int] = {start_entry_id}
    queue: deque[tuple[int, int, list[tuple[int, str]]]] = deque()
    queue.append((start_entry_id, 0, []))

    result
        # 条件判断：处理业务逻辑
s: list[dict[str, Any]] = []

    # 初始化变量 entry
    entry = entry_map.get(start_entry_id)
    # 条件判断: 检查 entry
    if entry:
        resul            # 条件判断：处理业务逻辑
ts.append({
            "entry_id": start_entry_id,
            "title": entry.title,
            "category": entry.category.value if entry.category else "unknown",
            "depth": 0,
            "path": [],
        })

    # 循环条件: while queue:
    while queue:
            # 条件判断：处理业务逻辑

        # 循环遍历：处理业务逻辑
        current_id, depth, path = queue.popleft()

        # 条件判断: 检查 depth >= max_depth
        if depth >= max_depth:
            continue

        # 遍历: for neighbor_id, rel_type in adjacency.get(current
        for neighbor_id, rel_type in adjacency.get(current_id, []):
            # 条件判断: 检查 neighbor_id in visited
            if neighbor_id in visited:
                                   # 条件判断：处理业务逻辑
     continue

            visited.add(neighbor_id)
            new_path: list[tuple[int, str]] = list(path)
            new_path.append((current_id, rel_type))

            # 初始化变量 neighbor_entry
            neighbor_entry = entry_map.get(neighbor_id)
            # 条件判断: 检查 neighbor_entry
            if neighbor_entry:
                results.append({
                    "entry_id": neighbor_id,
                    "title": neighbor_entry.title,
                    "category": (
                        neighbor_entry.category.value
                        # 条件判断: 检查 neighbor_entry.category
                        if neighbor_entry.category
                        else "unknown"
                    ),
                    "depth": depth + 1,
                    "path": new_path,
                })

            queue.append((neighbor_id, depth + 1, new_path))

    # 记录日志信息
    logger.info(
        "知识图谱遍历完成: start_entry_id={}, 访问节点数={}, 最大深度={}",
        start_entry_id,
        len(results),
        max_depth,
    )
    # 返回处理结果
    return results
