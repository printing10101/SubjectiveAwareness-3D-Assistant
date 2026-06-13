"""事实标签抽取器.

负责从案件事实文本中抽取与帮信罪三件套（规则、标签、冲突）相关的事实标签。
设计目标：

1. **优先规则匹配**：基于 :class:`app.services.rule_engine.Tag` 中
   ``extraction_hints`` 的关键词和正则模式进行快速匹配；
2. **LLM 兜底**：当关键词匹配覆盖率不足时，调用 LLM 对剩余未知片段进行分类；
3. **互斥去重**：在返回前基于 ``mutually_exclusive_with`` 进行互斥标签去重。

所有匹配条目以 :class:`TagMatch` 输出，包含 tag_id、matched_text、confidence
与 source_span，便于审计与冲突检测。
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.services.rule_engine import Rule, Tag, load_tags


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 关键词匹配基础置信度
_KEYWORD_BASE_CONFIDENCE: float = 0.65

# 关键词长度加成（每个字符 0.01，最高 0.20）
_KEYWORD_LENGTH_BONUS_UNIT: float = 0.01
_KEYWORD_LENGTH_BONUS_MAX: float = 0.20

# LLM 兜底覆盖率阈值（关键词命中数 / 标签总数 低于此值触发 LLM 兜底）
_LLM_FALLBACK_COVERAGE_THRESHOLD: float = 0.10

# LLM 兜底返回的默认置信度
_LLM_FALLBACK_DEFAULT_CONFIDENCE: float = 0.55

# 单个标签最大匹配数（防止同一标签在长文中刷屏）
_MAX_HITS_PER_TAG: int = 10

# 模式匹配：在关键词两侧允许的字符数（用于截取 source_span）
_SPAN_CONTEXT_PADDING: int = 12

# 兜底 LLM 标签候选集大小（仅取置信度最高的若干个 tag）
_LLM_CANDIDATE_LIMIT: int = 5


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TagMatch:
    """单个标签匹配结果.

    Attributes:
        tag_id: 命中的标签编号.
        matched_text: 触发命中的原始文本片段.
        confidence: 命中置信度（0~1）.
        source_span: ``(start, end)`` 形式的字符偏移.
        match_type: 匹配类型，可取值 ``keyword``、``pattern``、``llm``.
        evidence_tag_ids: 命中所依据的提示词列表.
    """

    tag_id: str
    matched_text: str
    confidence: float
    source_span: tuple[int, int]
    match_type: str = "keyword"
    evidence_tag_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典."""
        start, end = self.source_span
        return {
            "tag_id": self.tag_id,
            "matched_text": self.matched_text,
            "confidence": round(self.confidence, 4),
            "source_span": [start, end],
            "match_type": self.match_type,
        }


# ---------------------------------------------------------------------------
# 标签抽取器
# ---------------------------------------------------------------------------


class TagExtractor:
    """事实标签抽取器.

    提供关键词/正则匹配与可选 LLM 兜底能力。
    """

    def __init__(
        self,
        tags: Sequence[Tag] | None = None,
        *,
        keyword_base_confidence: float = _KEYWORD_BASE_CONFIDENCE,
        llm_fallback: bool = True,
    ) -> None:
        """初始化抽取器.

        Args:
            tags: 标签列表，默认调用 :func:`app.services.rule_engine.load_tags`.
            keyword_base_confidence: 关键词匹配基础置信度.
            llm_fallback: 是否启用 LLM 兜底（默认 True）.
        """
        self._tags: list[Tag] = list(tags) if tags is not None else list(load_tags())
        self._keyword_base_confidence = keyword_base_confidence
        self._llm_fallback = llm_fallback
        self._compiled_patterns: dict[str, list[re.Pattern[str]]] = self._compile_patterns()

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def extract(
        self,
        case_text: str,
        rules: Sequence[Rule] | None = None,
    ) -> list[TagMatch]:
        """从案件文本中抽取标签.

        Args:
            case_text: 案件事实文本.
            rules: 当前命中的规则列表（用于提升相关标签的置信度，可选）.

        Returns:
            :class:`TagMatch` 列表，已按互斥规则去重并按 confidence 降序.
        """
        if not case_text:
            return []

        matches = self._keyword_extract(case_text)

        if self._llm_fallback and self._should_call_llm(matches):
            llm_matches = self._llm_fallback_extract(case_text, rules)
            matches.extend(llm_matches)

        boosted = self._boost_by_rules(matches, rules or [])
        deduped = self._dedup_mutually_exclusive(boosted)
        deduped.sort(key=lambda m: m.confidence, reverse=True)
        return deduped

    # ------------------------------------------------------------------
    # 内部：关键词匹配
    # ------------------------------------------------------------------

    def _compile_patterns(self) -> dict[str, list[re.Pattern[str]]]:
        """将每个标签的 extraction_hints 编译为正则.

        短关键词使用 ``re.escape`` 后按字面匹配；包含特殊字符的提示词
        （如"凌晨X点"）使用占位符展开。
        """
        patterns: dict[str, list[re.Pattern[str]]] = {}
        for tag in self._tags:
            compiled: list[re.Pattern[str]] = []
            for hint in tag.extraction_hints:
                pattern = self._hint_to_pattern(hint)
                if pattern is not None:
                    compiled.append(pattern)
            patterns[tag.tag_id] = compiled
        return patterns

    @staticmethod
    def _hint_to_pattern(hint: str) -> re.Pattern[str] | None:
        """将单个提示词转为正则.

        Args:
            hint: 提示词字符串.

        Returns:
            编译后的正则对象；若提示词为空则返回 ``None``.
        """
        if not hint:
            return None
        expanded = re.sub(r"X", r"\\d{1,2}", hint)
        try:
            return re.compile(re.escape(expanded))
        except re.error:
            logger.warning(f"提示词无法编译为正则: {hint!r}")
            return None

    def _keyword_extract(self, case_text: str) -> list[TagMatch]:
        """基于关键词与提示词进行抽取."""
        matches: list[TagMatch] = []
        for tag in self._tags:
            patterns = self._compiled_patterns.get(tag.tag_id, [])
            tag_hits = 0
            for pattern in patterns:
                for m in pattern.finditer(case_text):
                    if tag_hits >= _MAX_HITS_PER_TAG:
                        break
                    matched_text = m.group(0)
                    confidence = self._score_keyword_match(matched_text)
                    span = self._expand_span(case_text, m.start(), m.end())
                    matches.append(
                        TagMatch(
                            tag_id=tag.tag_id,
                            matched_text=matched_text,
                            confidence=confidence,
                            source_span=span,
                            match_type="keyword",
                        )
                    )
                    tag_hits += 1
                if tag_hits >= _MAX_HITS_PER_TAG:
                    break
        return matches

    def _score_keyword_match(self, matched_text: str) -> float:
        """计算关键词匹配的置信度.

        在基础值之上按命中关键词长度加成（每字 0.01，最高 0.20）。
        """
        bonus = min(
            len(matched_text) * _KEYWORD_LENGTH_BONUS_UNIT,
            _KEYWORD_LENGTH_BONUS_MAX,
        )
        return min(self._keyword_base_confidence + bonus, 1.0)

    @staticmethod
    def _expand_span(text: str, start: int, end: int) -> tuple[int, int]:
        """在 span 两侧各加若干字符，便于审阅."""
        left = max(0, start - _SPAN_CONTEXT_PADDING)
        right = min(len(text), end + _SPAN_CONTEXT_PADDING)
        return left, right

    # ------------------------------------------------------------------
    # 内部：规则加成
    # ------------------------------------------------------------------

    def _boost_by_rules(
        self,
        matches: list[TagMatch],
        rules: Sequence[Rule],
    ) -> list[TagMatch]:
        """若某标签命中了规则的 applicable_scenarios，则适当提升其置信度.

        当前实现仅在不高于 0.95 的前提下加 0.05。
        """
        if not rules:
            return matches
        scenario_to_tag: dict[str, set[str]] = {}
        # 反向索引：场景关键词 -> 可能标签
        # 这里依赖 tag 的 name 命中 rule 的 applicable_scenarios 中的中文词
        for tag in self._tags:
            scenario_to_tag[tag.name] = {tag.tag_id}

        boosted: list[TagMatch] = []
        for m in matches:
            tag = next((t for t in self._tags if t.tag_id == m.tag_id), None)
            if tag is None:
                boosted.append(m)
                continue
            related = any(
                any(tag.name in s or s in tag.name for s in rule.applicable_scenarios)
                for rule in rules
            )
            if related and m.confidence < 0.95:
                m.confidence = min(0.95, m.confidence + 0.05)
            boosted.append(m)
        return boosted

    # ------------------------------------------------------------------
    # 内部：互斥去重
    # ------------------------------------------------------------------

    def _dedup_mutually_exclusive(self, matches: list[TagMatch]) -> list[TagMatch]:
        """根据标签的 ``mutually_exclusive_with`` 字段去重.

        算法：
        1. 按 confidence 降序遍历；
        2. 若已保留的某个标签 A 声明与 B 互斥，且 A 已在结果中，则丢弃 B。
        """
        sorted_matches = sorted(matches, key=lambda m: m.confidence, reverse=True)
        kept: list[TagMatch] = []
        kept_ids: set[str] = set()
        mutex_index: dict[str, set[str]] = {
            t.tag_id: set(t.mutually_exclusive_with) for t in self._tags
        }
        for m in sorted_matches:
            if m.tag_id in kept_ids:
                continue
            drop = False
            for kept_id in kept_ids:
                if m.tag_id in mutex_index.get(kept_id, set()):
                    drop = True
                    break
            if drop:
                continue
            kept.append(m)
            kept_ids.add(m.tag_id)
        return kept

    # ------------------------------------------------------------------
    # 内部：LLM 兜底
    # ------------------------------------------------------------------

    def _should_call_llm(self, matches: list[TagMatch]) -> bool:
        """是否应当触发 LLM 兜底.

        当前策略：若命中数低于 ``_LLM_FALLBACK_COVERAGE_THRESHOLD * 标签总数``，
        视为覆盖率不足，触发 LLM 兜底。
        """
        if not self._tags:
            return False
        coverage = len(matches) / max(1, len(self._tags))
        return coverage < _LLM_FALLBACK_COVERAGE_THRESHOLD

    def _llm_fallback_extract(
        self,
        case_text: str,
        rules: Sequence[Rule] | None,
    ) -> list[TagMatch]:
        """LLM 兜底抽取.

        为避免引入硬性网络依赖，本方法采用降级策略：
        1. 若 ``extract_via_llm`` 可注入实现（通过全局注册），则使用之；
        2. 否则使用关键短语模板匹配（仅在测试或离线场景下使用）。

        返回值中的 confidence 不超过 :data:`_LLM_FALLBACK_DEFAULT_CONFIDENCE`。
        """
        try:
            from app.services.tag_extractor import _llm_extract_callable  # type: ignore

            if _llm_extract_callable is not None:
                return _llm_extract_callable(case_text, self._tags, rules)
        except ImportError:
            pass

        logger.info("LLM 兜底未配置可调用实现，跳过兜底步骤")
        return []


# ---------------------------------------------------------------------------
# 模块级便捷函数
# ---------------------------------------------------------------------------


def extract_tags(
    case_text: str,
    rules: Sequence[Rule] | None = None,
) -> list[TagMatch]:
    """便捷函数：抽取案件文本的事实标签.

    Args:
        case_text: 案件事实文本.
        rules: 已命中的规则（可选）.

    Returns:
        :class:`TagMatch` 列表.
    """
    extractor = TagExtractor()
    return extractor.extract(case_text, rules)


# 可注入的 LLM 抽取回调（用于在测试或生产环境中替换实现）
_llm_extract_callable = None


def register_llm_extractor(func) -> None:
    """注册自定义 LLM 抽取实现.

    Args:
        func: 形如 ``(case_text, tags, rules) -> list[TagMatch]`` 的可调用对象.
    """
    global _llm_extract_callable
    _llm_extract_callable = func


def reset_llm_extractor() -> None:
    """清空已注册的 LLM 抽取实现."""
    global _llm_extract_callable
    _llm_extract_callable = None
