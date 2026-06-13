"""知识问答服务模块.

提供基于知识库的智能问答功能，包括上下文搜索、答案生成和来源验证。
整合全文搜索、LLM 生成和事实核查，确保回答准确、可追溯。
"""

from __future__ import annotations

import re
import time
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_entry import EntryStatus, KnowledgeEntry
from app.services.knowledge_search_service import ensure_fts_table, search_entries
from app.services.knowledge_service import get_entry
from app.services.ollama_client import OllamaClient, get_client
from app.services.prompts import KNOWLEDGE_QA_PROMPT


_STOP_WORDS: frozenset[str] = frozenset(
    {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
        "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
        "什么", "怎么", "如何", "为什么", "哪", "吗", "呢", "啊", "吧", "哦",
        "可以", "应该", "需要", "能够", "可能", "已经", "还是", "因为",
        "所以", "但是", "如果", "虽然", "而且", "或者", "以及", "关于",
        "对于", "根据", "通过", "经过", "由于", "为了", "除了",
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "can", "could", "should", "may", "might", "shall", "must",
        "of", "in", "to", "for", "with", "on", "at", "from", "by",
        "about", "as", "into", "like", "through", "after", "over",
        "between", "out", "against", "during", "without", "before",
        "under", "around", "among", "and", "or", "but", "not", "if",
        "then", "else", "when", "up", "down", "this", "that", "these",
        "those", "it", "its", "they", "them", "their", "we", "us", "our",
        "you", "your", "he", "him", "his", "she", "her", "me", "my",
    }
)

_MIN_KEYWORD_LENGTH: int = 2
_DEFAULT_SEARCH_LIMIT: int = 5
_DEFAULT_SNIPPET_MAX_LENGTH: int = 200
_QA_TIMEOUT_WARN_MS: float = 3000.0
_MAX_CONTENT_PREVIEW_LENGTH: int = 1500
_MIN_VALIDATION_THRESHOLD: float = 0.5


class KnowledgeQAService:
    """知识库问答服务.

    整合全文搜索、LLM 生成和来源验证，提供端到端的知识问答能力。
    支持通过构造函数注入外部依赖，便于单元测试和扩展。

    Attributes:
        db: 异步数据库会话
        ollama_client: Ollama LLM 客户端实例（可选注入）
    """

    def __init__(
        self,
        db: AsyncSession,
        ollama_client: OllamaClient | None = None,
    ) -> None:
        """初始化知识问答服务.

        Args:
            db: 异步数据库会话，用于知识库查询
            ollama_client: Ollama 客户端实例，为 None 时使用全局单例
        """
        self.db: AsyncSession = db
        self._ollama: OllamaClient | None = ollama_client

    @property
    def ollama(self) -> OllamaClient:
        """惰性获取 Ollama 客户端实例.

        Returns:
            OllamaClient: LLM 调用客户端
        """
        if self._ollama is None:
            self._ollama = get_client()
        return self._ollama

    def _extract_keywords(self, question: str) -> list[str]:
        """从用户问题中提取关键词和关键概念.

        使用正则表达式从中文和英文混合文本中提取有意义的词序列，
        过滤停用词后按原始出现顺序返回。

        Args:
            question: 用户提出的问题字符串

        Returns:
            去重后的关键词列表，保持原始出现顺序

        Example:
            >>> service._extract_keywords("什么是故意伤害罪？")
            ['故意伤害罪']
        """
        segments: list[str] = re.split(
            r'[，。！？、；：""'r'（）【】《》\s,.!?;:()\[\]{}]+',
            question,
        )
        keywords: list[str] = []
        for seg in segments:
            _seg = seg.strip()
            if not _seg:
                continue
            chinese_words: list[str] = re.findall(
                rf"[\u4e00-\u9fff]{{{_MIN_KEYWORD_LENGTH},}}", _seg
            )
            for w in chinese_words:
                if w not in _STOP_WORDS:
                    keywords.append(w)  # noqa: PERF401
            english_words: list[str] = re.findall(r"[a-zA-Z]{2,}", seg)
            for w in english_words:
                if w.lower() not in _STOP_WORDS:
                    keywords.append(w)  # noqa: PERF401

        seen: set[str] = set()
        unique: list[str] = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        return unique

    def _build_search_query(self, keywords: list[str]) -> str:
        """根据关键词列表构建 FTS5 搜索查询字符串.

        将关键词用空格连接，FTS5 默认按 OR 逻辑匹配。
        若关键词超过3个，仅使用最前面（最重要）的3个。

        Args:
            keywords: 提取的关键词列表

        Returns:
            FTS5 兼容的搜索查询字符串

        Raises:
            ValueError: 关键词列表为空
        """
        if not keywords:
            msg: str = "无法从问题中提取有效关键词"
            raise ValueError(msg)
        top_keywords: list[str] = keywords[:3]
        return " ".join(top_keywords)

    def _compute_relevance_rank(
        self,
        fts_score: float,
        entry_confidence: float | None,
        keyword_count: int,
    ) -> float:
        """综合计算知识条目的相关性排名分数.

        结合 FTS5 相关性评分、条目置信度和关键词命中数，
        生成综合排名分数（数值越低越相关）。

        Args:
            fts_score: FTS5 原始排名分数
            entry_confidence: 条目标注的置信度（0-1或None）
            keyword_count: 条目内容中匹配到的关键词数量

        Returns:
            综合相关性分数
        """
        confidence_factor: float = 1.0
        if entry_confidence is not None:
            confidence_factor = 2.0 - entry_confidence

        keyword_penalty: float = 1.0 / max(keyword_count, 1)

        return fts_score * confidence_factor * keyword_penalty

    def _extract_snippet(self, content: str, question: str) -> str:
        """从条目正文中提取与问题相关的摘要片段.

        优先返回关键词匹配位置附近的上下文，若无匹配则返回开头部分。

        Args:
            content: 条目正文内容
            question: 用户问题

        Returns:
            截取的相关内容片段
        """
        keywords: list[str] = self._extract_keywords(question)
        content_lower: str = content.lower()

        best_pos: int = -1
        for kw in keywords:
            pos = content_lower.find(kw.lower())
            if pos != -1:
                best_pos = max(pos - 50, 0)
                break

        start: int = max(best_pos, 0)
        end: int = min(start + _DEFAULT_SNIPPET_MAX_LENGTH, len(content))
        snippet: str = content[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet

    async def search_for_context(self, question: str) -> list[dict[str, Any]]:
        """根据用户问题搜索相关的知识库条目.

        使用 NLP 技术从问题中提取关键概念和实体，
        基于提取的关键词执行全文搜索并应用相关性排序。

        Args:
            question: 用户提出的问题字符串

        Returns:
            3-5条最相关的知识条目，每条包含:
            - entry_id: 知识条目的唯一标识符
            - title: 知识条目的标题
            - content: 知识条目的完整正文内容
            - relevance_score: 综合相关性评分
            - snippet: 与问题相关的摘要片段

        Raises:
            ValueError: 无法从问题中提取有效关键词
            RuntimeError: 知识库搜索失败或数据异常

        Example:
            >>> results = await service.search_for_context("什么是故意伤害罪？")
            >>> results[0]["title"]
            '故意伤害罪构成要件分析'
        """
        await ensure_fts_table(self.db)

        keywords: list[str] = self._extract_keywords(question)
        if not keywords:
            logger.warning("问题中未提取到有效关键词: question={}", question)
            msg: str = "无法从问题中提取有效关键词，请提供更具体的问题"
            raise ValueError(msg)

        search_query: str = self._build_search_query(keywords)
        logger.info("知识问答上下文搜索: keywords={}, query={}", keywords, search_query)

        try:
            fts_results: list[dict[str, Any]] = await search_entries(
                self.db,
                search_query,
                status=EntryStatus.active,
                limit=_DEFAULT_SEARCH_LIMIT,
            )
        except RuntimeError:
            logger.error("全文搜索失败: question={}", question)
            raise
        except Exception as e:
            logger.error("知识库搜索异常: question={}, error={}", question, e)
            msg: str = f"知识库搜索服务暂时不可用: {e}"
            raise RuntimeError(msg) from e

        if not fts_results:
            logger.info("未找到与问题相关的知识条目: question={}", question)
            return []

        context_entries: list[dict[str, Any]] = []
        for result in fts_results:
            entry_id: int = result["entry_id"]
            try:
                entry: KnowledgeEntry | None = await get_entry(self.db, entry_id)
            except Exception as e:  # noqa: BLE001
                logger.warning("获取知识条目失败: entry_id={}, error={}", entry_id, e)
                continue

            if entry is None or not entry.content:
                continue

            content_text: str = entry.content
            snippet: str = self._extract_snippet(content_text, question)

            kw_count: int = sum(
                1 for kw in keywords if kw.lower() in content_text.lower()
            )
            fts_score: float = float(result.get("score", 1.0))
            confidence: float | None = entry.confidence

            relevance: float = self._compute_relevance_rank(
                fts_score, confidence, kw_count
            )

            context_entries.append(
                {
                    "entry_id": entry_id,
                    "title": entry.title,
                    "content": content_text,
                    "relevance_score": round(relevance, 4),
                    "snippet": snippet,
                }
            )

        context_entries.sort(key=lambda x: x["relevance_score"])
        logger.info(
            "上下文搜索完成: question={}, found={}",
            question,
            len(context_entries),
        )
        return context_entries

    def _format_entries_for_prompt(
        self, entries: list[dict[str, Any]]
    ) -> str:
        """将知识条目列表格式化为提示词模板所需的文本.

        Args:
            entries: 知识条目列表

        Returns:
            格式化的条目文本，包含标题和内容
        """
        if not entries:
            return "（未找到相关知识点）"

        parts: list[str] = []
        for i, entry in enumerate(entries, 1):
            title: str = entry.get("title", "未知标题")
            content: str = entry.get("content", "")
            if len(content) > _MAX_CONTENT_PREVIEW_LENGTH:
                content = content[:_MAX_CONTENT_PREVIEW_LENGTH] + "..."
            parts.append(f"【条目{i} - {title}】\n{content}")

        return "\n\n---\n\n".join(parts)

    def _compute_confidence(
        self,
        sources: list[dict[str, Any]],
        fts_results: list[dict[str, Any]],
    ) -> float:
        """计算回答的综合置信度.

        基于来源数量、FTS 相关性评分和条目置信度综合评估。

        Args:
            sources: 引用的知识来源列表
            fts_results: 全文搜索结果

        Returns:
            0-1之间的置信度分数
        """
        if not sources:
            return 0.0

        base_score: float = min(len(sources) / _DEFAULT_SEARCH_LIMIT, 1.0)

        fts_score_map: dict[int, float] = {}
        for r in fts_results:
            fts_score_map[r["entry_id"]] = float(r.get("score", 1.0))

        avg_relevance: float = 0.0
        for src in sources:
            eid: int = src.get("entry_id", -1)
            avg_relevance += 1.0 / max(fts_score_map.get(eid, 1.0), 0.01)

        if sources:
            avg_relevance /= len(sources)

        avg_relevance = min(avg_relevance, 1.0)

        confidence: float = round(base_score * 0.4 + avg_relevance * 0.6, 4)
        return max(0.0, min(confidence, 1.0))

    async def answer_question(
        self,
        question: str,
        context_entries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """接收用户问题并返回基于知识库的准确回答.

        完整处理流程：
        1. 若未提供 context_entries，自动调用 search_for_context 获取相关上下文
        2. 调用 search_entries 获取与问题最相关的前5条知识条目
        3. 提取条目内容作为生成回答的上下文信息
        4. 复用 ollama_client 的 LLM 调用能力，使用 KNOWLEDGE_QA_PROMPT 生成回答

        Args:
            question: 用户提出的问题字符串
            context_entries: 可选参数，预提供的上下文知识条目列表，
                             每项需包含 entry_id、title 和 content 字段

        Returns:
            包含以下字段的字典:
            - answer: 生成的自然语言回答字符串
            - sources: 引用的知识来源列表，每项包含 entry_id、title、snippet
            - confidence: 回答置信度分数（0-1之间的浮点数）

        Raises:
            ValueError: question为空或context_entries格式不正确
            RuntimeError: LLM调用失败或知识库连接错误

        Example:
            >>> result = await service.answer_question("什么是故意伤害罪？")
            >>> result["answer"]
            '故意伤害罪是指...【来源：故意伤害罪构成要件分析】'
            >>> len(result["sources"])
            3
        """
        if not question or not question.strip():
            msg: str = "问题不能为空"
            raise ValueError(msg)

        question = question.strip()
        start_time: float = time.perf_counter()

        if context_entries is not None:
            for entry in context_entries:
                if not all(k in entry for k in ("entry_id", "title", "content")):
                    msg: str = (
                        "context_entries 每项必须包含 entry_id、title 和 content 字段"
                    )
                    raise ValueError(msg)
            search_context: list[dict[str, Any]] = context_entries
        else:
            try:
                search_context = await self.search_for_context(question)
            except (ValueError, RuntimeError):
                raise
            except Exception as e:
                logger.error("搜索上下文失败: question={}, error={}", question, e)
                msg: str = f"知识库搜索失败: {e}"
                raise RuntimeError(msg) from e

        try:
            fts_results: list[dict[str, Any]] = await search_entries(
                self.db,
                self._build_search_query(
                    self._extract_keywords(question) or [question]
                ),
                status=EntryStatus.active,
                limit=_DEFAULT_SEARCH_LIMIT,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("FTS搜索异常，继续使用上下文结果: error={}", e)
            fts_results = [
                {"entry_id": e["entry_id"], "score": 1.0, "title": e["title"]}
                for e in search_context
            ]

        formatted_entries: str = self._format_entries_for_prompt(search_context)

        prompt: str = KNOWLEDGE_QA_PROMPT.format(
            user_question=question,
            relevant_entries=formatted_entries,
        )

        try:
            answer: str = await self.ollama.generate(
                prompt=prompt,
                temperature=0.3,
                dynamic_timeout=True,
            )
        except Exception as e:
            logger.error("LLM调用失败: question={}, error={}", question, e)
            msg: str = f"AI模型调用失败，请稍后重试: {e}"
            raise RuntimeError(msg) from e

        sources: list[dict[str, Any]] = []
        for entry in search_context:
            snippet: str = entry.get(
                "snippet",
                self._extract_snippet(entry.get("content", ""), question),
            )
            sources.append(
                {
                    "entry_id": entry["entry_id"],
                    "title": entry["title"],
                    "snippet": snippet,
                }
            )

        confidence: float = self._compute_confidence(sources, fts_results)

        elapsed_ms: float = (time.perf_counter() - start_time) * 1000
        logger.info(
            "问答处理完成: question={}, sources={}, confidence={}, elapsed={:.1f}ms",
            question[:50],
            len(sources),
            confidence,
            elapsed_ms,
        )
        if elapsed_ms > _QA_TIMEOUT_WARN_MS:
            logger.warning(
                "问答处理耗时超标: {:.1f}ms > {:.0f}ms",
                elapsed_ms,
                _QA_TIMEOUT_WARN_MS,
            )

        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
        }

    async def validate_answer_with_sources(
        self,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """验证回答与引用来源的一致性和准确性.

        执行以下验证检查：
        1. 检查回答中的事实性陈述是否能在提供的sources中找到支持
        2. 验证每个引用的entry_id是否在知识库中真实存在
        3. 评估回答内容与来源信息的相关性和一致性

        Args:
            answer: 生成的回答字符串
            sources: 回答引用的知识来源列表，每项需包含 entry_id

        Returns:
            包含验证结果的字典:
            - is_valid: 布尔值，表示验证是否通过
            - validation_details: 验证详情说明字符串
            - source_check: 来源验证结果列表，每项包含 entry_id、exists、relevant
            - content_coverage: 回答内容被来源覆盖的比例（0-1）

        Raises:
            ValueError: answer或sources为空
            RuntimeError: 数据库查询异常

        Example:
            >>> result = await service.validate_answer_with_sources(
            ...     "故意伤害罪是...",
            ...     [{"entry_id": 1, "title": "故意伤害罪"}]
            ... )
            >>> result["is_valid"]
            True
        """
        if not answer or not answer.strip():
            msg: str = "回答不能为空"
            raise ValueError(msg)
        if not sources:
            msg: str = "来源列表不能为空"
            raise ValueError(msg)

        validation_details: list[str] = []
        source_checks: list[dict[str, Any]] = []
        total_sources: int = len(sources)
        found_sources: int = 0
        relevant_sources: int = 0

        for source in sources:
            entry_id: int = source.get("entry_id", -1)
            source_title: str = source.get("title", "未知")

            exists: bool = False
            entry_content: str = ""
            try:
                entry: KnowledgeEntry | None = await get_entry(self.db, entry_id)
                if entry is not None:
                    exists = True
                    entry_content = entry.content or ""
                    source_checks.append(
                        {
                            "entry_id": entry_id,
                            "exists": True,
                            "relevant": False,
                            "title": entry.title,
                        }
                    )
                else:
                    source_checks.append(
                        {
                            "entry_id": entry_id,
                            "exists": False,
                            "relevant": False,
                            "title": source_title,
                        }
                    )
                    validation_details.append(
                        f"来源条目 (id={entry_id}, title={source_title}) 在知识库中不存在"
                    )
            except Exception as e:  # noqa: BLE001
                logger.error("验证来源条目失败: entry_id={}, error={}", entry_id, e)
                source_checks.append(
                    {
                        "entry_id": entry_id,
                        "exists": False,
                        "relevant": False,
                        "title": source_title,
                    }
                )
                validation_details.append(
                    f"无法验证来源条目 (id={entry_id}): {e}"
                )

            if exists:
                found_sources += 1
                keywords: list[str] = self._extract_keywords(answer)
                match_count: int = sum(
                    1 for kw in keywords if kw.lower() in entry_content.lower()
                )
                if match_count > 0:
                    relevant_sources += 1
                    source_checks[-1]["relevant"] = True

        source_existence_ratio: float = found_sources / total_sources if total_sources else 0.0
        content_relevance_ratio: float = (
            relevant_sources / max(found_sources, 1)
        )

        if found_sources == 0:
            validation_details.append("所有引用的来源条目在知识库中均不存在")
        elif relevant_sources == 0:
            validation_details.append(
                "回答内容与引用的来源条目之间未检测到明显关联"
            )

        is_valid: bool = source_existence_ratio >= _MIN_VALIDATION_THRESHOLD

        if not validation_details:
            validation_details.append(
                f"验证通过：{found_sources}/{total_sources} 个来源存在于知识库中，"
                f"{relevant_sources}/{found_sources} 个与回答内容相关"
            )

        content_coverage: float = round(
            (
                source_existence_ratio * 0.5
                + content_relevance_ratio * 0.5
            ),
            4,
        )

        logger.info(
            "答案验证完成: is_valid={}, source_ratio={:.2f}, "
            "relevance_ratio={:.2f}, coverage={:.2f}",
            is_valid,
            source_existence_ratio,
            content_relevance_ratio,
            content_coverage,
        )

        return {
            "is_valid": is_valid,
            "validation_details": "; ".join(validation_details),
            "source_check": source_checks,
            "content_coverage": content_coverage,
        }
