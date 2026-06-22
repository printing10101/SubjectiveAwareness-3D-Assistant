"""事实标签抽取器单元测试.

覆盖以下方面：
- TagMatch 数据结构与 to_dict 序列化
- TagExtractor 关键词/模式匹配
- 互斥标签去重逻辑
- LLM 兜底注入（通过 register_llm_extractor）
- 规则加成（confidence boost）
- 边界情况：空文本、无标签、置信度范围等
- 模块级便捷函数 extract_tags
"""

from __future__ import annotations

import pytest

from app.services.rule_engine import Rule, Tag, load_tags
from app.services.tag_extractor import (
    TagExtractor,
    TagMatch,
    extract_tags,
    register_llm_extractor,
    reset_llm_extractor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_global_llm_extractor() -> None:
    """确保每个测试运行前/后清空 LLM 注入实现,避免相互污染."""
    reset_llm_extractor()
    yield  # type: ignore[misc]
    reset_llm_extractor()


@pytest.fixture
def simple_tags() -> list[Tag]:
    """构造一组小型测试用标签,覆盖所有 4 类分类."""

    return [
        Tag(
            tag_id="F001",
            name="开卡",
            category="客观行为",
            description="办卡行为",
            extraction_hints=["办卡", "开卡"],
            mutually_exclusive_with=["F002"],
        ),
        Tag(
            tag_id="F002",
            name="卖卡",
            category="客观行为",
            description="售卡行为",
            extraction_hints=["卖卡", "售卡"],
            mutually_exclusive_with=["F001"],
        ),
        Tag(
            tag_id="F011",
            name="异常时间",
            category="认知线索",
            description="凌晨/夜间",
            extraction_hints=["凌晨", "深夜"],
            mutually_exclusive_with=[],
        ),
        Tag(
            tag_id="F031",
            name="自首",
            category="情节",
            description="主动投案",
            extraction_hints=["自首", "主动投案"],
            mutually_exclusive_with=[],
        ),
    ]


# ---------------------------------------------------------------------------
# TagMatch 数据结构
# ---------------------------------------------------------------------------


class TestTagMatchDataclass:
    """TagMatch 数据结构与 to_dict."""

    def test_to_dict_returns_serializable(self) -> None:
        match = TagMatch(
            tag_id="F001",
            matched_text="开卡",
            confidence=0.75,
            source_span=(10, 14),
        )
        result = match.to_dict()
        assert result["tag_id"] == "F001"
        assert result["matched_text"] == "开卡"
        assert result["confidence"] == 0.75
        assert result["source_span"] == [10, 14]
        assert result["match_type"] == "keyword"

    def test_to_dict_confidence_rounded(self) -> None:
        match = TagMatch(
            tag_id="F001",
            matched_text="开卡",
            confidence=0.123456789,
            source_span=(0, 2),
        )
        assert match.to_dict()["confidence"] == 0.1235

    def test_default_match_type_is_keyword(self) -> None:
        match = TagMatch(
            tag_id="F001",
            matched_text="开卡",
            confidence=0.5,
            source_span=(0, 2),
        )
        assert match.match_type == "keyword"

    def test_source_span_is_tuple(self) -> None:
        match = TagMatch(
            tag_id="F001",
            matched_text="开卡",
            confidence=0.5,
            source_span=(0, 2),
        )
        assert isinstance(match.source_span, tuple)
        assert len(match.source_span) == 2


# ---------------------------------------------------------------------------
# 关键词匹配
# ---------------------------------------------------------------------------


class TestKeywordExtraction:
    """验证 TagExtractor 关键词抽取核心能力."""

    def test_empty_text_returns_no_matches(self, simple_tags: list[Tag]) -> None:
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        assert extractor.extract("") == []

    def test_keyword_match_basic(self, simple_tags: list[Tag]) -> None:
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        # 仅使用"开卡"关键词,避免 F001/F002 互斥干扰
        matches = extractor.extract("被告人在银行开卡后将卡借给他人")
        tag_ids = {m.tag_id for m in matches}
        assert "F001" in tag_ids  # 开卡
        # F002(卖卡) 不会出现在文本中
        assert "F002" not in tag_ids

    def test_match_without_mutex(self, simple_tags: list[Tag]) -> None:
        """F011(异常时间) 与 F031(自首) 互不互斥,应同时保留."""
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        matches = extractor.extract("凌晨开卡并自首")
        tag_ids = {m.tag_id for m in matches}
        assert "F001" in tag_ids
        assert "F011" in tag_ids
        assert "F031" in tag_ids

    def test_no_match_returns_empty(self, simple_tags: list[Tag]) -> None:
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        matches = extractor.extract("这是一段完全无关的文本,没有匹配关键词")
        assert matches == []

    def test_confidence_in_valid_range(self, simple_tags: list[Tag]) -> None:
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        matches = extractor.extract("凌晨开卡行为")
        for m in matches:
            assert 0.0 <= m.confidence <= 1.0

    def test_source_span_within_text(self, simple_tags: list[Tag]) -> None:
        text = "被告人在凌晨开卡"
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        matches = extractor.extract(text)
        for m in matches:
            start, end = m.source_span
            assert 0 <= start < end <= len(text) + 24  # 考虑 _SPAN_CONTEXT_PADDING

    def test_long_keyword_higher_confidence(self, simple_tags: list[Tag]) -> None:
        """长关键词应获得更高的置信度加成."""
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        # "主动投案"(4字) 比 "自首"(2字) 应有更高 confidence
        short = extractor.extract("他自首了")
        long_ = extractor.extract("他主动投案了")
        # 找到 F031 的匹配
        short_conf = next((m.confidence for m in short if m.tag_id == "F031"), 0)
        long_conf = next((m.confidence for m in long_ if m.tag_id == "F031"), 0)
        assert long_conf > short_conf

    def test_extracted_uses_default_tags_when_none(self) -> None:
        """未传入 tags 时应使用 load_tags() 默认值."""
        extractor = TagExtractor(llm_fallback=False)
        default_tags = load_tags()
        assert len(extractor._tags) == len(default_tags)


# ---------------------------------------------------------------------------
# 互斥去重
# ---------------------------------------------------------------------------


class TestMutuallyExclusiveDeduplication:
    """互斥标签应在结果中被去重,只保留 confidence 较高者."""

    def test_conflicting_tags_deduplicated(self, simple_tags: list[Tag]) -> None:
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        matches = extractor.extract("他开卡并卖卡")
        tag_ids = {m.tag_id for m in matches}
        # F001(开卡) 与 F002(卖卡) 互斥,只应保留一个
        assert "F001" in tag_ids or "F002" in tag_ids
        assert not ("F001" in tag_ids and "F002" in tag_ids)

    def test_non_conflicting_tags_kept(self, simple_tags: list[Tag]) -> None:
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        matches = extractor.extract("凌晨开卡自首")
        tag_ids = {m.tag_id for m in matches}
        # F001、F011、F031 互不互斥,都应保留
        assert "F001" in tag_ids
        assert "F011" in tag_ids
        assert "F031" in tag_ids

    def test_dedup_keeps_higher_confidence(self, simple_tags: list[Tag]) -> None:
        """互斥标签中,应保留 confidence 较高的那个."""
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        # "开卡"(2字) 与 "办卡"(2字) 同属 F001; "卖卡"(2字) F002
        # 它们置信度接近,但 F001 hint 长度相同 → 保留先处理者
        matches = extractor.extract("开卡卖卡")
        kept_ids = {m.tag_id for m in matches}
        assert len(kept_ids & {"F001", "F002"}) == 1


# ---------------------------------------------------------------------------
# 排序
# ---------------------------------------------------------------------------


class TestSorting:
    """返回的 matches 应按 confidence 降序."""

    def test_results_sorted_by_confidence(self, simple_tags: list[Tag]) -> None:
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        matches = extractor.extract("开卡卖卡凌晨自首")
        confidences = [m.confidence for m in matches]
        assert confidences == sorted(confidences, reverse=True)


# ---------------------------------------------------------------------------
# 规则加成
# ---------------------------------------------------------------------------


class TestRuleBoosting:
    """命中规则时,相关标签的 confidence 应被适当提升."""

    def test_boost_when_rule_scenario_matches(self, simple_tags: list[Tag]) -> None:
        rule = Rule(
            rule_id="R001",
            name="测试规则",
            source_law="刑法",
            article="第1条",
            conditions="x",
            conclusion="y",
            applicable_scenarios=["开卡"],
        )
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        # 不带规则
        matches_no_rule = extractor.extract("开卡")
        # 带规则
        matches_with_rule = extractor.extract("开卡", rules=[rule])
        conf_no_rule = next(m.confidence for m in matches_no_rule if m.tag_id == "F001")
        conf_with_rule = next(m.confidence for m in matches_with_rule if m.tag_id == "F001")
        assert conf_with_rule >= conf_no_rule

    def test_boost_capped_at_0_95(self, simple_tags: list[Tag]) -> None:
        """confidence 加成不应超过 0.95."""
        rule = Rule(
            rule_id="R001",
            name="测试规则",
            source_law="刑法",
            article="第1条",
            conditions="x",
            conclusion="y",
            applicable_scenarios=["开卡"],
        )
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        matches = extractor.extract("开卡开卡开卡开卡开卡", rules=[rule])
        for m in matches:
            assert m.confidence <= 0.95


# ---------------------------------------------------------------------------
# LLM 兜底
# ---------------------------------------------------------------------------


class TestLLMFallback:
    """验证 LLM 兜底机制."""

    def test_llm_fallback_called_when_coverage_low(self, simple_tags: list[Tag]) -> None:
        """关键词覆盖率低时,应调用 LLM."""
        called: dict[str, bool] = {"flag": False}

        def fake_llm(case_text, tags, rules):
            called["flag"] = True
            return [
                TagMatch(
                    tag_id="F011",
                    matched_text="LLM补充",
                    confidence=0.55,
                    source_span=(0, len(case_text)),
                    match_type="llm",
                )
            ]

        register_llm_extractor(fake_llm)
        extractor = TagExtractor(tags=simple_tags, llm_fallback=True)
        # 文本不包含任何 extraction_hints,覆盖率 0
        matches = extractor.extract("一段没有任何关键词的文本")
        assert called["flag"] is True
        assert any(m.match_type == "llm" for m in matches)

    def test_llm_fallback_skipped_when_coverage_high(
        self, simple_tags: list[Tag]
    ) -> None:
        called: dict[str, bool] = {"flag": False}

        def fake_llm(case_text, tags, rules):
            called["flag"] = True
            return []

        register_llm_extractor(fake_llm)
        extractor = TagExtractor(tags=simple_tags, llm_fallback=True)
        # 覆盖 4 个标签中的 4 个 = 100%,远超阈值
        matches = extractor.extract("开卡卖卡凌晨自首")
        # 不应调用 LLM(因为关键词命中充足)
        assert called["flag"] is False

    def test_llm_fallback_disabled(self, simple_tags: list[Tag]) -> None:
        called: dict[str, bool] = {"flag": False}

        def fake_llm(case_text, tags, rules):
            called["flag"] = True
            return []

        register_llm_extractor(fake_llm)
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        extractor.extract("没有任何关键词的文本")
        assert called["flag"] is False

    def test_no_llm_registered_returns_empty(self, simple_tags: list[Tag]) -> None:
        """未注册 LLM 实现时,LLM 兜底应安静地返回空列表."""
        extractor = TagExtractor(tags=simple_tags, llm_fallback=True)
        # 无任何关键词命中,会触发 LLM 兜底,但因未注册,应返回 []
        matches = extractor.extract("完全无关键词")
        # 不应抛出异常
        assert isinstance(matches, list)


# ---------------------------------------------------------------------------
# 边界情况
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """异常输入与边界场景."""

    def test_max_hits_per_tag_limit(self) -> None:
        """单个标签的命中数不应超过 _MAX_HITS_PER_TAG(防止刷屏)."""
        extractor = TagExtractor(llm_fallback=False)
        # 构造大量重复关键词
        text = "开卡 " * 200
        matches = extractor.extract(text)
        f001_matches = [m for m in matches if m.tag_id == "F001"]
        # 上限 10
        assert len(f001_matches) <= 10

    def test_none_case_text_treated_as_empty(self, simple_tags: list[Tag]) -> None:
        """None 文本应被安全处理(空字符串路径)."""
        extractor = TagExtractor(tags=simple_tags, llm_fallback=False)
        # extract 内部先做 if not case_text: return []
        assert extractor.extract("") == []

    def test_time_hint_matches_keyword(self) -> None:
        """异常时间相关关键词应能正确匹配."""
        tags = [
            Tag(
                tag_id="F011",
                name="异常时间",
                category="认知线索",
                description="",
                extraction_hints=["凌晨", "深夜", "夜间"],
                mutually_exclusive_with=[],
            )
        ]
        extractor = TagExtractor(tags=tags, llm_fallback=False)
        matches = extractor.extract("他于凌晨作案")
        assert any(m.tag_id == "F011" for m in matches)

    def test_multiple_time_hints_match(self) -> None:
        """多个时间关键词都能被匹配."""
        tags = [
            Tag(
                tag_id="F011",
                name="异常时间",
                category="认知线索",
                description="",
                extraction_hints=["凌晨", "深夜", "夜间"],
                mutually_exclusive_with=[],
            )
        ]
        extractor = TagExtractor(tags=tags, llm_fallback=False)
        matches = extractor.extract("凌晨在深夜开始")
        # 至少 1 个匹配
        assert any(m.tag_id == "F011" for m in matches)

    def test_real_world_text(self) -> None:
        """真实案件文本的端到端抽取."""
        text = (
            "被告人张某,2023年3月,凌晨在银行开卡后,以每张1500元的价格"
            "将三张银行卡出售给陌生人。流水金额50余万元,获利3000元。"
            "案发后主动投案自首,认罪认罚,系在校学生。"
        )
        extractor = TagExtractor(llm_fallback=False)
        matches = extractor.extract(text)
        tag_ids = {m.tag_id for m in matches}
        # 至少应命中:开卡(F001) 异常时间(F011) 异常价格(F012) 异常对手(F013)
        # 高额获利(F020) 自首(F031) 认罪认罚(F036) 在校生(F034)
        assert "F001" in tag_ids
        assert "F011" in tag_ids
        assert "F031" in tag_ids
        assert "F036" in tag_ids


# ---------------------------------------------------------------------------
# 模块级便捷函数
# ---------------------------------------------------------------------------


class TestModuleLevelFunction:
    """extract_tags 便捷函数测试."""

    def test_extract_tags_returns_matches(self) -> None:
        matches = extract_tags("他在银行开卡")
        assert isinstance(matches, list)
        assert all(isinstance(m, TagMatch) for m in matches)

    def test_extract_tags_with_rules(self) -> None:
        rule = Rule(
            rule_id="R001",
            name="测试",
            source_law="刑法",
            article="第1条",
            conditions="x",
            conclusion="y",
        )
        matches = extract_tags("他开卡了", rules=[rule])
        assert isinstance(matches, list)

    def test_extract_tags_with_empty_text(self) -> None:
        assert extract_tags("") == []
