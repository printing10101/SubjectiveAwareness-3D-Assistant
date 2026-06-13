"""知识库全文搜索服务模块.

基于 SQLite FTS5 实现高效全文搜索，支持多维度过滤和关键词高亮。
采用零外部依赖方案（FTS5 内置于 SQLite），为后续升级至 PostgreSQL tsvector
或 BM25 + jieba 预留扩展空间。

对于中文文本，在写入 FTS5 索引前自动在 CJK 字符间插入空格，
使 unicode61 分词器能逐字索引，确保中文全文搜索的召回率。
未来升级至方案二或方案三时可直接替换分词预处理逻辑。

所有数据库操作均使用异步 API，搜索响应时间目标不超过 300ms。
"""

from __future__ import annotations

import re
import time
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_entry import EntryCategory, EntryStatus


_fts_table_name: str = "knowledge_fts"
_DEFAULT_SEARCH_LIMIT: int = 20
_MAX_SEARCH_LIMIT: int = 200
_MIN_QUERY_LENGTH: int = 1
_MAX_QUERY_LENGTH: int = 500
_PERF_WARN_THRESHOLD_MS: float = 300.0
_FTS5_TOKENIZER: str = "unicode61"
_HIGHLIGHT_OPEN: str = "<mark>"
_HIGHLIGHT_CLOSE: str = "</mark>"
_SNIPPET_MAX_TOKENS: int = 64

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
    f"INSERT OR REPLACE INTO {_fts_table_name}(rowid, title, content, summary) "  # noqa: S608
    "VALUES (:rowid, :title, :content, :summary)"
)

_DELETE_FTS_SQL: str = (
    f"DELETE FROM {_fts_table_name} WHERE rowid = :rowid"  # noqa: S608
)

_COUNT_FTS_SQL: str = (
    f"SELECT COUNT(*) FROM {_fts_table_name}"  # noqa: S608
)


def _segment_cjk(text: str) -> str:
    """在中文（CJK）字符之间插入空格，使 unicode61 分词器能逐字索引.

    FTS5 的 unicode61 默认将 CJK 字符视为分隔符而非 token 字符，
    导致中文文本无法被正确索引。通过在 CJK 字符间插入空格，
    每个字符成为一个独立 token，MATCH 查询可正常匹配连续字符序列。

    Args:
        text: 原始文本

    Returns:
        在 CJK 字符间插入空格后的文本
    """
    if not text:
        return text
    return _CJK_PATTERN.sub(r" \1 ", text)


def _sanitize_query(query: str) -> str:
    """清理搜索查询字符串，转义 FTS5 特殊字符并预处理中文.

    FTS5 查询语法中双引号(")和星号(*)具有特殊含义，
    需要对用户输入进行转义处理以防止语法错误。
    对 CJK 字符间插入空格以匹配索引格式。

    Args:
        query: 原始用户查询字符串

    Returns:
        清理并预处理后的安全查询字符串

    Raises:
        ValueError: 查询为空或仅含空白字符

    Example:
        >>> _sanitize_query('hello world')
        'hello world'
        >>> _sanitize_query('故意伤害')
        '故 意 伤 害'
    """
    if not query or not query.strip():
        msg = "搜索查询不能为空"
        raise ValueError(msg)

    cleaned = query.strip()[: _MAX_QUERY_LENGTH]
    cleaned = _FTS5_SPECIAL_CHARS.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) < _MIN_QUERY_LENGTH:
        msg = f"搜索查询长度不足，至少需要{_MIN_QUERY_LENGTH}个字符"
        raise ValueError(msg)

    cleaned = _segment_cjk(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _build_filter_conditions(
    category: EntryCategory | None,
    tag_id: int | None,
    status: EntryStatus | None,
) -> tuple[str, dict[str, Any]]:
    """构建额外的 WHERE 过滤条件和参数.

    Args:
        category: 分类过滤条件
        tag_id: 标签ID过滤条件
        status: 状态过滤条件

    Returns:
        包含 SQL 条件片段和参数字典的元组
    """
    conditions: list[str] = []
    params: dict[str, Any] = {}

    if category is not None:
        conditions.append("ke.category = :category")
        params["category"] = category.value if hasattr(category, "value") else category

    if status is not None:
        conditions.append("ke.status = :status")
        params["status"] = status.value if hasattr(status, "value") else status

    if tag_id is not None:
        conditions.append(
            "EXISTS (SELECT 1 FROM entry_tags et "
            "WHERE et.entry_id = ke.id AND et.tag_id = :tag_id)"
        )
        params["tag_id"] = tag_id

    filter_sql = ""
    if conditions:
        filter_sql = "AND " + " AND ".join(conditions)

    return filter_sql, params


def _build_highlight_snippet(
    title: str,
    summary: str | None,
    original_query: str,
) -> str:
    """构建关键词高亮摘要片段.

    当 FTS5 snippet() 不可用时（如通过 JOIN 查询不直接返回 snippet），
    使用正则匹配在摘要或标题中高亮查询关键词。

    Args:
        title: 条目标题（原始格式）
        summary: 条目摘要（原始格式）
        original_query: 原始搜索查询（预处理前）

    Returns:
        包含 <mark> 高亮标记的文本片段
    """
    base_text = summary or title or ""
    if not base_text:
        return ""

    original_query = original_query.strip()

    query_terms = _FTS5_SPECIAL_CHARS.sub(" ", original_query).split()
    pattern_parts = []
    for term in query_terms:
        escaped = re.escape(term)
        pattern_parts.append(escaped)

    if not pattern_parts:
        return _truncate_text(base_text)

    combined = "|".join(pattern_parts)
    pattern = re.compile(f"({combined})", re.IGNORECASE)

    result = pattern.sub(
        lambda m: f"{_HIGHLIGHT_OPEN}{m.group(0)}{_HIGHLIGHT_CLOSE}",
        base_text,
    )
    return _truncate_text(result)


def _truncate_text(text: str, max_chars: int = 300) -> str:
    """截断文本至指定最大长度.

    Args:
        text: 原始文本
        max_chars: 最大字符数

    Returns:
        截断后的文本
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


async def ensure_fts_table(db: AsyncSession) -> None:
    """确保 FTS5 全文搜索虚拟表存在.

    在应用启动或首次搜索前调用，若表不存在则自动创建。
    幂等操作，多次调用不会产生副作用。

    Args:
        db: 异步数据库会话

    Raises:
        RuntimeError: FTS5 表创建失败（通常为 SQLite 版本不支持 FTS5）
    """
    try:
        await db.execute(text(_CREATE_FTS_TABLE_SQL))
        await db.commit()
        logger.info("FTS5 全文搜索虚拟表已就绪: table={}", _fts_table_name)
    except Exception as e:
        logger.error("FTS5 表初始化失败: error={}", e)
        msg = f"全文搜索功能初始化失败: {e}"
        raise RuntimeError(msg) from e


async def sync_entry(
    db: AsyncSession,
    entry_id: int,
    title: str,
    content: str,
    summary: str | None = None,
) -> None:
    """将知识条目标题、正文和摘要同步至 FTS5 全文索引.

    自动对 CJK 文本进行预处理（字符间插入空格），
    支持插入或更新操作（INSERT OR REPLACE）。

    Args:
        db: 异步数据库会话
        entry_id: 知识条目 ID
        title: 条目标题
        content: 条目正文
        summary: 条目摘要（可选）

    Raises:
        RuntimeError: FTS 索引同步失败
    """
    try:
        await db.execute(
            text(_INSERT_FTS_SQL),
            {
                "rowid": entry_id,
                "title": _segment_cjk(title),
                "content": _segment_cjk(content),
                "summary": _segment_cjk(summary or ""),
            },
        )
        await db.commit()
        logger.debug("FTS 索引已同步: entry_id={}", entry_id)
    except Exception as e:
        logger.error("FTS 索引同步失败: entry_id={}, error={}", entry_id, e)
        msg = f"全文索引同步失败(entry_id={entry_id}): {e}"
        raise RuntimeError(msg) from e


async def remove_entry_from_fts(db: AsyncSession, entry_id: int) -> None:
    """从 FTS5 索引中删除指定条目.

    Args:
        db: 异步数据库会话
        entry_id: 知识条目 ID

    Raises:
        RuntimeError: FTS 索引删除失败
    """
    try:
        await db.execute(text(_DELETE_FTS_SQL), {"rowid": entry_id})
        await db.commit()
        logger.debug("FTS 索引已删除: entry_id={}", entry_id)
    except Exception as e:
        logger.error("FTS 索引删除失败: entry_id={}, error={}", entry_id, e)
        msg = f"全文索引删除失败(entry_id={entry_id}): {e}"
        raise RuntimeError(msg) from e


async def get_fts_count(db: AsyncSession) -> int:
    """获取 FTS5 索引中的条目总数.

    Args:
        db: 异步数据库会话

    Returns:
        FTS 索引条目数
    """
    result = await db.execute(text(_COUNT_FTS_SQL))
    return result.scalar_one()


async def search_entries(  # noqa: PLR0913
    db: AsyncSession,
    query: str,
    category: EntryCategory | None = None,
    tag_id: int | None = None,
    status: EntryStatus | None = None,
    limit: int = _DEFAULT_SEARCH_LIMIT,
) -> list[dict[str, Any]]:
    """使用 FTS5 MATCH 操作符执行知识库全文搜索.

    支持按分类(category)、标签(tag)、状态(status)等多维度过滤，
    搜索结果按 FTS5 相关性评分自动降序排列。

    Args:
        db: 异步数据库会话
        query: 搜索查询字符串
        category: 按分类过滤（可选）
        tag_id: 按标签ID过滤（可选）
        status: 按状态过滤（可选）
        limit: 返回结果数量上限，默认20，最大200

    Returns:
        搜索结果列表，每项包含:
        - entry_id: 知识条目标识ID
        - title: 条目标题
        - summary: 条目摘要信息
        - score: FTS5 相关性评分（数值型，越小相关性越高）
        - highlight_snippet: 搜索关键词高亮片段

    Raises:
        ValueError: 查询为空或无效
        RuntimeError: 数据库查询异常

    Example:
        >>> results = await search_entries(db, "故意伤害")
        >>> results[0]["entry_id"]
        42
        >>> results[0]["title"]
        '故意伤害罪构成要件分析'
    """
    if limit < 1:
        msg = "返回结果数量必须大于0"
        raise ValueError(msg)
    if limit > _MAX_SEARCH_LIMIT:
        msg = f"返回结果数量不能超过{_MAX_SEARCH_LIMIT}"
        raise ValueError(msg)

    original_query = query.strip()
    sanitized = _sanitize_query(query)

    filter_sql, filter_params = _build_filter_conditions(category, tag_id, status)

    search_sql = (
        f"SELECT ke.id AS entry_id, "  # noqa: S608
        f"ke.title, "
        f"ke.summary, "
        f"fts.rank AS score, "
        f"snippet({_fts_table_name}, 1, "
        f"'{_HIGHLIGHT_OPEN}', '{_HIGHLIGHT_CLOSE}', '...', {_SNIPPET_MAX_TOKENS}) "
        f"AS highlight_snippet "
        f"FROM {_fts_table_name} fts "
        f"JOIN knowledge_entries ke ON fts.rowid = ke.id "
        f"WHERE {_fts_table_name} MATCH :query "
        f"{filter_sql} "
        f"ORDER BY fts.rank "
        f"LIMIT :limit"
    )

    params: dict[str, Any] = {"query": sanitized, "limit": limit}
    params.update(filter_params)

    start = time.perf_counter()
    try:
        result = await db.execute(text(search_sql), params)
        rows = result.fetchall()

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "全文搜索完成: query='{}', results={}, elapsed={:.1f}ms",
            original_query,
            len(rows),
            elapsed_ms,
        )

        if elapsed_ms > _PERF_WARN_THRESHOLD_MS:
            logger.warning(
                "全文搜索响应时间超标: {:.1f}ms > {:.0f}ms, query='{}'",
                elapsed_ms,
                _PERF_WARN_THRESHOLD_MS,
                original_query,
            )

        mapped: list[dict[str, Any]] = []
        for row in rows:
            highlight = row.highlight_snippet
            if not highlight:
                highlight = _build_highlight_snippet(
                    row.title, row.summary, original_query
                )
            mapped.append(
                {
                    "entry_id": row.entry_id,
                    "title": row.title,
                    "summary": row.summary,
                    "score": row.score,
                    "highlight_snippet": highlight,
                }
            )
        return mapped

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "全文搜索异常: query='{}', error={}, elapsed={:.1f}ms",
            original_query,
            e,
            elapsed_ms,
        )
        msg = f"全文搜索服务暂时不可用: {e}"
        raise RuntimeError(msg) from e
