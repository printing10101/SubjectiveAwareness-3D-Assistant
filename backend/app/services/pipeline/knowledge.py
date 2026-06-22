"""知识检索模块.

提供法律知识检索功能，支持 Neo4j 图数据库、SQLite FTS 全文搜索
和内存关键词匹配三级兜底策略。
"""

import re
from typing import Any

from loguru import logger

from app.config import settings
from app.database import get_async_db_session
from app.models.knowledge_entry import EntryStatus
from app.services.knowledge import ensure_fts_table, search_entries

from app.services.pipeline.complexity import _KEYWORD_LEGAL

_SUMMARY_SNIPPET_LENGTH = 200
_MIN_REMAINING = 20
_MAX_SNIPPET_LENGTH = 1000


async def _retrieve_neo4j_knowledge(
    case_text: str,
    max_entries: int = 5,
) -> list[dict[str, str]] | None:
    """从 Neo4j 图数据库中检索与案件相关的法律知识.

    策略：

    1. 若 ``settings.NEO4J_URI`` 为空，直接返回 ``None``，由调用方降级到 SQLite FTS。
    2. 尝试调用 Neo4j 驱动执行关键词查询；任何异常（连接失败、驱动不可用等）
       均返回 ``None``，由调用方降级。

    Returns:
        命中的知识条目摘要列表；若 Neo4j 未配置或不可用则返回 ``None``.
    """
    if settings.NEO4J_URI is None:
        return None

    try:
        # 延迟导入避免无 Neo4j 环境下拉起驱动
        from neo4j import GraphDatabase  # type: ignore
    except ImportError:
        logger.warning("Neo4j 驱动未安装，回退到 SQLite FTS")
        return None

    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    except Exception:  # noqa: BLE001
        logger.warning("Neo4j 驱动初始化失败，回退到 SQLite FTS", exc_info=True)
        return None

    keywords = [kw for kw in _KEYWORD_LEGAL if kw in case_text][:3]
    if not keywords:
        driver.close()
        return []

    query = (
        "MATCH (n:KnowledgeEntry) "
        "WHERE any(k IN $keywords WHERE n.title CONTAINS k OR n.summary CONTAINS k) "
        "RETURN n.title AS title, n.summary AS summary "
        "LIMIT $limit"
    )
    try:
        with driver.session() as session:
            result = session.run(query, keywords=keywords, limit=max_entries)
            records = [dict(record) for record in result]
    except Exception:  # noqa: BLE001
        logger.warning("Neo4j 查询失败，回退到 SQLite FTS", exc_info=True)
        driver.close()
        return None
    finally:
        driver.close()

    entries: list[dict[str, str]] = []
    for r in records:
        title = (r.get("title") or "").strip()
        summary = (r.get("summary") or "").strip()
        if not title:
            continue
        entries.append({"title": title, "summary": summary})
    return entries


def _format_knowledge_entries(
    entries: list[dict[str, str]],
) -> tuple[str, list[dict[str, str]]]:
    """将知识条目列表格式化为提示词注入片段.

    Args:
        entries: 知识条目列表，每项含 title 与 summary.

    Returns:
        tuple: (格式化的相关知识文本, 知识条目摘要列表).
    """
    if not entries:
        return "", []

    knowledge_parts = ["【相关知识】"]
    total_len = 0
    entries_info: list[dict[str, str]] = []

    for entry in entries:
        title = (entry.get("title") or "").strip()
        summary = (entry.get("summary") or "").strip()
        if not title:
            continue
        snippet = (
            summary[:_SUMMARY_SNIPPET_LENGTH]
            if len(summary) > _SUMMARY_SNIPPET_LENGTH
            else summary
        )
        entry_text = f"[{title}] {snippet}" if snippet else f"[{title}]"

        if total_len + len(entry_text) > _MAX_SNIPPET_LENGTH:
            remaining = _MAX_SNIPPET_LENGTH - total_len
            if remaining > _MIN_REMAINING:
                entry_text = entry_text[:remaining] + "..."
                knowledge_parts.append(entry_text)
            break

        knowledge_parts.append(entry_text)
        total_len += len(entry_text)
        entries_info.append({"title": title, "summary": snippet})

    if not entries_info:
        return "", []
    return "\n\n".join(knowledge_parts), entries_info


async def _retrieve_legal_knowledge(
    case_text: str,
    max_entries: int = 5,
) -> tuple[str, list[dict[str, str]]]:
    """从知识库中检索与案件相关的法律知识.

    检索优先级：**Neo4j > SQLite FTS > 内存关键词匹配**。

    1. **Neo4j**：若 ``settings.NEO4J_URI`` 已配置且驱动可用，优先使用 Neo4j 检索。
    2. **SQLite FTS**：若 Neo4j 未配置或不可用，回退到 SQLite FTS 全文搜索
       （基于 :func:`ensure_fts_table` + :func:`search_entries`）。
    3. **内存关键词匹配**：若 SQLite FTS 仍未命中，回退到 ``_KEYWORD_LEGAL``
       在案件文本中的字面匹配并构造最小摘要。

    Args:
        case_text: 案件文本
        max_entries: 最大返回条目数

    Returns:
        tuple: (格式化的相关知识文本, 知识条目摘要列表).
              三级兜底均无命中时返回 ("", [])。
    """
    try:
        # 1) 尝试 Neo4j
        neo4j_entries = await _retrieve_neo4j_knowledge(case_text, max_entries)
        if neo4j_entries:
            logger.info(f"Neo4j 命中 {len(neo4j_entries)} 条")
            return _format_knowledge_entries(neo4j_entries)

        # 2) 回退到 SQLite FTS
        keywords = [kw for kw in _KEYWORD_LEGAL if kw in case_text]
        if keywords:
            async with get_async_db_session() as db:
                await ensure_fts_table(db)
                results = await search_entries(
                    db,
                    " ".join(keywords[:3]),
                    status=EntryStatus.active,
                    limit=max_entries,
                )
            if results:
                logger.info(f"SQLite FTS 命中 {len(results)} 条")
                return _format_knowledge_entries(
                    [
                        {
                            "title": r.get("title", ""),
                            "summary": r.get("summary") or "",
                        }
                        for r in results
                    ]
                )

        # 3) 内存关键词兜底：基于 _KEYWORD_LEGAL 命中给出最简摘要
        if keywords:
            logger.info(f"使用内存关键词兜底: {keywords[:3]}")
            stub_entries = [
                {
                    "title": f"法律关键词命中：{kw}",
                    "summary": f"案件文本中检测到关键词 {kw}，建议结合相关法条进一步分析。",
                }
                for kw in keywords[:max_entries]
            ]
            return _format_knowledge_entries(stub_entries)

        logger.info("案件文本中未匹配到法律关键词，跳过知识检索")
        return "", []

    except Exception:  # noqa: BLE001
        logger.warning("知识检索异常，跳过知识注入", exc_info=True)
        return "", []
