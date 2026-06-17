"""冲突检测器单元测试.

覆盖以下方面:
- Conflict 数据结构与 to_dict 序列化
- C001 规则冲突检测
- C002 标签互斥冲突检测
- C003 维度间结论矛盾检测
- C004 证据不足检测
- C005 超量刑范围检测
- C006 适用法律版本冲突检测
- 模块级便捷函数 detect_conflicts
- 边界情况:空输入、未知 check_id 等
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: pytest
import pytest

# 导入模块: from app.services.conflict_detector
from app.services.conflict_detector import (
    Conflict,
    ConflictDetector,
    detect_conflicts,
)
# 导入模块: from app.services.rule_engine
from app.services.rule_engine import (
    ConflictCheck,
    Rule,
    load_conflicts,
)
# 导入模块: from app.services.tag_extractor
from app.services.tag_extractor import TagMatch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# 应用装饰器: pytest.fixture
@pytest.fixture
def base_rules() -> list[Rule]:
    """构造一组基础规则,覆盖六类检测需要的字段."""

    # 返回处理结果
    return [
        Rule(
            # 初始化变量 rule_id
            rule_id="R005",
            # 初始化变量 name
            name="推定明知-规避调查",
            # 初始化变量 source_law
            source_law="帮信解释(法释〔2019〕15号)",
            # 初始化变量 article
            article="第11条",
            # 初始化变量 conditions
            conditions="x",
            # 初始化变量 conclusion
            conclusion="y",
            # 初始化变量 weight
            weight=0.85,
            # 初始化变量 conflicting_rules
            conflicting_rules=[],
        ),
        Rule(
            # 初始化变量 rule_id
            rule_id="R032",
            # 初始化变量 name
            name="出罪-无主观明知",
            # 初始化变量 source_law
            source_law="帮信解释(法释〔2019〕15号)",
            # 初始化变量 article
            article="第12条",
            # 初始化变量 conditions
            conditions="x",
            # 初始化变量 conclusion
            conclusion="y",
            # 初始化变量 weight
            weight=0.7,
            # 初始化变量 conflicting_rules
            conflicting_rules=[],
        ),
        Rule(
            # 初始化变量 rule_id
            rule_id="R008",
            # 初始化变量 name
            name="帮信解释-支付结算",
            # 初始化变量 source_law
            source_law="帮信解释(法释〔2019〕15号)",
            # 初始化变量 article
            article="第12条",
            # 初始化变量 conditions
            conditions="x",
            # 初始化变量 conclusion
            conclusion="y",
            # 初始化变量 weight
            weight=0.8,
            # 初始化变量 conflicting_rules
            conflicting_rules=[],
        ),
        Rule(
            # 初始化变量 rule_id
            rule_id="R013",
            # 初始化变量 name
            name="两高意见-支付结算",
            # 初始化变量 source_law
            source_law="最高人民法院、最高人民检察院、公安部 2025 意见",
            # 初始化变量 article
            article="第5条",
            # 初始化变量 conditions
            conditions="x",
            # 初始化变量 conclusion
            conclusion="y",
            # 初始化变量 weight
            weight=0.8,
            # 初始化变量 conflicting_rules
            conflicting_rules=[],
        ),
        Rule(
            # 初始化变量 rule_id
            rule_id="R009",
            # 初始化变量 name
            name="情节严重",
            # 初始化变量 source_law
            source_law="刑法",
            # 初始化变量 article
            article="第287条之二",
            # 初始化变量 conditions
            conditions="x",
            # 初始化变量 conclusion
            conclusion="y",
            # 初始化变量 weight
            weight=0.85,
            # 初始化变量 conflicting_rules
            conflicting_rules=[],
        ),
        Rule(
            # 初始化变量 rule_id
            rule_id="R040",
            # 初始化变量 name
            name="出罪-无证据",
            # 初始化变量 source_law
            source_law="帮信解释(法释〔2019〕15号)",
            # 初始化变量 article
            article="第12条",
            # 初始化变量 conditions
            conditions="x",
            # 初始化变量 conclusion
            conclusion="y",
            # 初始化变量 weight
            weight=0.7,
            # 初始化变量 conflicting_rules
            conflicting_rules=[],
        ),
    ]


# 应用装饰器: pytest.fixture
@pytest.fixture
def conflicting_rules() -> list[Rule]:
    """构造一组明确声明互相冲突的规则."""

    # 返回处理结果
    return [
        Rule(
            # 初始化变量 rule_id
            rule_id="RA",
            # 初始化变量 name
            name="规则A",
            # 初始化变量 source_law
            source_law="刑法",
            # 初始化变量 article
            article="第1条",
            # 初始化变量 conditions
            conditions="x",
            # 初始化变量 conclusion
            conclusion="y",
            # 初始化变量 conflicting_rules
            conflicting_rules=["RB"],
        ),
        Rule(
            # 初始化变量 rule_id
            rule_id="RB",
            # 初始化变量 name
            name="规则B",
            # 初始化变量 source_law
            source_law="刑法",
            # 初始化变量 article
            article="第1条",
            # 初始化变量 conditions
            conditions="x",
            # 初始化变量 conclusion
            conclusion="y",
            # 初始化变量 conflicting_rules
            conflicting_rules=["RA"],
        ),
    ]


# 应用装饰器: pytest.fixture
@pytest.fixture
def mutex_tags() -> list[TagMatch]:
    """构造一组互斥的标签匹配."""

    # 返回处理结果
    return [
        TagMatch(
            # 初始化变量 tag_id
            tag_id="F001",
            # 初始化变量 matched_text
            matched_text="开卡",
            # 初始化变量 confidence
            confidence=0.8,
            # 初始化变量 source_span
            source_span=(0, 2),
        ),
        TagMatch(
            # 初始化变量 tag_id
            tag_id="F002",
            # 初始化变量 matched_text
            matched_text="卖卡",
            # 初始化变量 confidence
            confidence=0.75,
            # 初始化变量 source_span
            source_span=(3, 5),
        ),
    ]


# ---------------------------------------------------------------------------
# Conflict 数据结构
# ---------------------------------------------------------------------------


# 定义 TestConflictDataclass 类
class TestConflictDataclass:
    """Conflict 数据结构与 to_dict."""

    def test_to_dict_returns_serializable(self) -> None:

        # 执行 test_to_dict_returns_serializable 函数的核心逻辑
        conflict = Conflict(
            # 初始化变量 check_id
            check_id="C001",
            # 初始化变量 name
            name="测试冲突",
            # 初始化变量 severity
            severity="high",
            # 初始化变量 involved
            involved=["R005", "R032"],
            # 初始化变量 description
            description="测试描述",
            # 初始化变量 resolution_strategy
            resolution_strategy="测试策略",
            # 初始化变量 raw_payload
            raw_payload={"k": "v"},
        )
        # 初始化变量 result
        result = conflict.to_dict()
        assert result["check_id"] == "C001"
        assert result["name"] == "测试冲突"
        assert result["severity"] == "high"
        assert result["involved"] == ["R005", "R032"]
        assert result["description"] == "测试描述"
        assert result["resolution_strategy"] == "测试策略"
        assert result["raw_payload"] == {"k": "v"}

    def test_default_raw_payload(self) -> None:
        # 函数 test_default_raw_payload 的初始化逻辑
        conflict = Conflict(
            # 初始化变量 check_id
            check_id="C001",
            # 初始化变量 name
            name="x",
            # 初始化变量 severity
            severity="low",
            # 初始化变量 involved
            involved=[],
            # 初始化变量 description
            description="d",
            # 初始化变量 resolution_strategy
            resolution_strategy="r",
        )
        assert conflict.raw_payload == {}

    def test_involved_is_list(self) -> None:

        # 执行 test_involved_is_list 函数的核心逻辑
        conflict = Conflict(
            # 初始化变量 check_id
            check_id="C001",
            # 初始化变量 name
            name="x",
            # 初始化变量 severity
            severity="low",
            # 初始化变量 involved
            involved=["A", "B"],
            # 初始化变量 description
            description="d",
            # 初始化变量 resolution_strategy
            resolution_strategy="r",
        )
        assert isinstance(conflict.involved, list)


# ---------------------------------------------------------------------------
# C001 规则冲突
# ---------------------------------------------------------------------------


# 定义 TestRuleConflict 类
class TestRuleConflict:
    """C001: 规则间存在声明的冲突."""

    def test_no_conflict_when_no_overlap(
        # 函数 test_no_conflict_when_no_overlap 的初始化逻辑
        self, base_rules: list[Rule]
    ) -> None:
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(tags=[], rule_hits=base_rules, dimension_results={})
        ids = {c.check_id for c in result}
        assert "C001" not in ids

    def test_conflict_detected(self, conflicting_rules: list[Rule]) -> None:

        # 执行 test_conflict_detected 函数的核心逻辑
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[],
            # 初始化变量 rule_hits
            rule_hits=conflicting_rules,
            # 初始化变量 dimension_results
            dimension_results={},
        )
        # 初始化变量 c001
        c001 = [c for c in result if c.check_id == "C001"]
        assert len(c001) == 1
        assert c001[0].severity == "high"
        assert "RA" in c001[0].involved
        assert "RB" in c001[0].involved

    def test_conflict_payload(self, conflicting_rules: list[Rule]) -> None:

        # 执行 test_conflict_payload 函数的核心逻辑
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[],
            # 初始化变量 rule_hits
            rule_hits=conflicting_rules,
            # 初始化变量 dimension_results
            dimension_results={},
        )
        # 初始化变量 c001
        c001 = [c for c in result if c.check_id == "C001"][0]
        assert "conflicting_pairs" in c001.raw_payload


# ---------------------------------------------------------------------------
# C002 标签互斥冲突
# ---------------------------------------------------------------------------


# 定义 TestTagMutex 类
class TestTagMutex:
    """C002: 互斥标签同时出现."""

    def test_no_conflict_when_no_mutex(
        # 函数 test_no_conflict_when_no_mutex 的初始化逻辑
        self,
    ) -> None:
        # 初始化变量 tags
        tags = [
            TagMatch(tag_id="F001", matched_text="开卡", confidence=0.7, source_span=(0, 2)),
            TagMatch(tag_id="F011", matched_text="凌晨", confidence=0.7, source_span=(3, 5)),
        ]
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(tags=tags, rule_hits=[], dimension_results={})
        # 初始化变量 c002
        c002 = [c for c in result if c.check_id == "C002"]
        assert len(c002) == 0

    def test_conflict_detected(self, mutex_tags: list[TagMatch]) -> None:

        # 执行 test_conflict_detected 函数的核心逻辑
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=mutex_tags,
            # 初始化变量 rule_hits
            rule_hits=[],
            # 初始化变量 dimension_results
            dimension_results={},
        )
        # 初始化变量 c002
        c002 = [c for c in result if c.check_id == "C002"]
        assert len(c002) == 1
        assert c002[0].severity == "medium"
        assert "F001" in c002[0].involved
        assert "F002" in c002[0].involved

    def test_mutex_pairs_in_payload(self, mutex_tags: list[TagMatch]) -> None:

        # 执行 test_mutex_pairs_in_payload 函数的核心逻辑
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=mutex_tags,
            # 初始化变量 rule_hits
            rule_hits=[],
            # 初始化变量 dimension_results
            dimension_results={},
        )
        # 初始化变量 c002
        c002 = [c for c in result if c.check_id == "C002"][0]
        assert "mutex_pairs" in c002.raw_payload


# ---------------------------------------------------------------------------
# C003 维度间结论矛盾
# ---------------------------------------------------------------------------


# 定义 TestDimensionContradiction 类
class TestDimensionContradiction:
    """C003: 维度1 说情节严重,维度2 说情节轻微."""

    def test_no_conflict_when_consistent(self) -> None:
        # 函数 test_no_conflict_when_consistent 的初始化逻辑
        dimension_results = {
            "dimension1": {"score": 8.0, "reasoning": "情节严重"},
            "dimension2": {"score": 7.0, "reasoning": "情节严重,有从宽因素"},
        }
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=[], dimension_results=dimension_results
        )
        # 初始化变量 c003
        c003 = [c for c in result if c.check_id == "C003"]
        assert len(c003) == 0

    def test_conflict_detected(self) -> None:

        # 执行 test_conflict_detected 函数的核心逻辑
        dimension_results = {
            "dimension1": {"score": 8.0, "reasoning": "流水50万,情节严重"},
            "dimension2": {"score": 4.0, "reasoning": "情节显著轻微,建议从宽处理"},
        }
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=[], dimension_results=dimension_results
        )
        # 初始化变量 c003
        c003 = [c for c in result if c.check_id == "C003"]
        assert len(c003) == 1
        assert c003[0].severity == "high"
        assert "dimension1" in c003[0].involved
        assert "dimension2" in c003[0].involved

    def test_no_conflict_when_dimension_missing(self) -> None:

        # 执行 test_no_conflict_when_dimension_missing 函数的核心逻辑
        dimension_results = {
            "dimension1": {"score": 8.0, "reasoning": "情节严重"},
        }
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=[], dimension_results=dimension_results
        )
        # 初始化变量 c003
        c003 = [c for c in result if c.check_id == "C003"]
        assert len(c003) == 0


# ---------------------------------------------------------------------------
# C004 证据不足
# ---------------------------------------------------------------------------


# 定义 TestEvidenceShortage 类
class TestEvidenceShortage:
    """C004: 命中高权重规则但缺核心证据."""

    def test_no_conflict_when_no_heavy_rules(self, base_rules: list[Rule]) -> None:
        """没有 weight>=0.8 的规则时不触发 C004."""
        # 删掉所有 weight>=0.8 的规则
        light_rules = [r for r in base_rules if r.weight < 0.8]
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=light_rules, dimension_results={}
        )
        # 初始化变量 c004
        c004 = [c for c in result if c.check_id == "C004"]
        assert len(c004) == 0

    def test_no_conflict_when_evidence_present(
        # 函数 test_no_conflict_when_evidence_present 的初始化逻辑
        self, base_rules: list[Rule]

        # 执行 test_no_conflict_when_evidence_present 函数的核心逻辑
    ) -> None:
        """有审计报告+银行流水时不触发."""
        # 初始化变量 dimension_results
        dimension_results = {
            "dimension1": {

        # 执行 test_conflict_detected_when_evidence_missing 函数的核心逻辑
                "score": 8.0,
                "reasoning": "审计报告与银行流水证实流水50万",
            }
        }
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[],
            # 初始化变量 rule_hits
            rule_hits=base_rules,
            # 初始化变量 dimension_results
            dimension_results=dimension_results,
        )
        # 初始化变量 c004
        c004 = [c for c in result if c.check_id == "C004"]
        assert len(c004) == 0

    def test_conflict_detected_when_evidence_missing(
        # 函数 test_conflict_detected_when_evidence_missing 的初始化逻辑
        self, base_rules: list[Rule]
    ) -> None:
        """高权重规则 + 缺核心证据 → C004 触发."""
        # 初始化变量 dimension_results
        dimension_results = {
            "dimension1": {
                "score": 8.0,
                "reasoning": "流水50万,情节严重",  # 没有审计报告/银行流水等关键词
            }
        }
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[],
            # 初始化变量 rule_hits
            rule_hits=base_rules,
            # 初始化变量 dimension_results
            dimension_results=dimension_results,
        )
        # 初始化变量 c004
        c004 = [c for c in result if c.check_id == "C004"]
        assert len(c004) == 1
        assert c004[0].severity == "medium"
        assert "evidence_hits" in c004[0].raw_payload
        # missing_evidence 应列出缺失的关键词
        assert "missing_evidence" in c004[0].raw_payload

    def test_conflict_not_triggered_when_no_rules(self) -> None:
        """无 rule_hits 时 C004 不触发."""
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=[], dimension_results={}
        )
        # 初始化变量 c004
        c004 = [c for c in result if c.check_id == "C004"]
        assert len(c004) == 0


# ---------------------------------------------------------------------------
# C005 超量刑范围
# ---------------------------------------------------------------------------


# 定义 TestSentenceOutOfRange 类
class TestSentenceOutOfRange:
    """C005: 量刑档位超出情节档位."""

    def test_no_conflict_when_consistent(self) -> None:

        # 执行 test_conflict_detected 函数的核心逻辑
        dimension_results = {
            "dimension2": {"score": 6.0, "reasoning": "情节严重"},
            "dimension3": {"score": 7.0, "reasoning": "二档量刑"},
        }
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=[], dimension_results=dimension_results
        )
        # 初始化变量 c005
        c005 = [c for c in result if c.check_id == "C005"]
        assert len(c005) == 0

    def test_conflict_detected(self) -> None:
        """维度3 适用三档,但维度2 评估为情节较轻 → 冲突."""
        # 初始化变量 dimension_results
        dimension_results = {
            "dimension2": {"score": 4.0, "reasoning": "情节较轻,建议从轻"},
            "dimension3": {
                "score": 9.0,

        # 执行 test_no_conflict_when_no_tier_keyword 函数的核心逻辑
                "reasoning": "情节特别严重,建议三档量刑",
            },
        }
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=[], dimension_results=dimension_results
        )
        # 初始化变量 c005
        c005 = [c for c in result if c.check_id == "C005"]
        assert len(c005) == 1
        assert c005[0].severity == "high"
        assert c005[0].raw_payload["sentencing_tier"] == 3
        assert c005[0].raw_payload["circumstance_tier"] == 1

    def test_no_conflict_when_no_tier_keyword(self) -> None:
        """dimension text 中无任何档位关键词时 C005 不触发."""
        # 初始化变量 dimension_results
        dimension_results = {
            "dimension2": {"score": 4.0, "reasoning": "普通评价"},
            "dimension3": {"score": 7.0, "reasoning": "普通评价"},
        }
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=[], dimension_results=dimension_results
        )
        # 初始化变量 c005
        c005 = [c for c in result if c.check_id == "C005"]
        assert len(c005) == 0

    def test_no_conflict_when_sentencing_not_higher(self) -> None:
        """量刑档位不高于情节档位时不应触发."""
        # 初始化变量 dimension_results
        dimension_results = {
            "dimension2": {"score": 7.0, "reasoning": "情节特别严重"},

        # 执行 test_no_conflict_single_version 函数的核心逻辑
            "dimension3": {"score": 6.0, "reasoning": "二档量刑"},
        }
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=[], dimension_results=dimension_results
        )
        # 初始化变量 c005
        c005 = [c for c in result if c.check_id == "C005"]
        assert len(c005) == 0


# ---------------------------------------------------------------------------
# C006 适用法律版本冲突
# ---------------------------------------------------------------------------


# 定义 TestLawVersionConflict 类
class TestLawVersionConflict:
    """C006: 2019 解释与 2025 意见同时被引用."""

    def test_no_conflict_single_version(self, base_rules: list[Rule]) -> None:
        """只引用 2019 解释时不应触发."""
        # 初始化变量 only_2019
        only_2019 = [r for r in base_rules if "2019" in r.source_law]
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=only_2019, dimension_results={}
        )
        # 初始化变量 c006
        c006 = [c for c in result if c.check_id == "C006"]
        assert len(c006) == 0

    def test_conflict_detected(self, base_rules: list[Rule]) -> None:
        """同时包含 2019 解释和 2025 意见 → 触发."""
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=base_rules, dimension_results={}
        )
        # 初始化变量 c006
        c006 = [c for c in result if c.check_id == "C006"]
        assert len(c006) == 1
        assert c006[0].severity == "critical"
        assert "2019" in c006[0].involved
        assert "2025" in c006[0].involved

    def test_conflict_severity_is_critical(self, base_rules: list[Rule]) -> None:

        # 执行 test_multiple_conflicts_returned 函数的核心逻辑
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=base_rules, dimension_results={}
        )
        # 初始化变量 c006
        c006 = [c for c in result if c.check_id == "C006"][0]
        assert c006.severity == "critical"


# ---------------------------------------------------------------------------
# 综合测试
# ---------------------------------------------------------------------------


# 定义 TestAllChecks 类
class TestAllChecks:
    """综合场景:多个冲突同时存在."""

    def test_multiple_conflicts_returned(self, base_rules: list[Rule]) -> None:
        """同时存在多种冲突时,应返回多个 Conflict 对象."""
        # 初始化变量 tags
        tags = [
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F001",
                # 初始化变量 matched_text
                matched_text="开卡",
                # 初始化变量 confidence
                confidence=0.8,
                # 初始化变量 source_span
                source_span=(0, 2),
            ),
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F002",
                # 初始化变量 matched_text
                matched_text="卖卡",
                # 初始化变量 confidence
                confidence=0.75,
                # 初始化变量 source_span
                source_span=(3, 5),
            ),
        ]
        # 初始化变量 dimension_results
        dimension_results = {
            "dimension1": {"score": 8.0, "reasoning": "流水50万"},  # 缺证据

        # 执行 test_no_conflict_clean_case 函数的核心逻辑
            "dimension2": {"score": 4.0, "reasoning": "情节较轻"},  # 矛盾
            "dimension3": {"score": 9.0, "reasoning": "三档量刑,情节特别严重"},  # 超量刑
        }
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=tags, rule_hits=base_rules, dimension_results=dimension_results
        )
        ids = {c.check_id for c in result}
        # 至少应包含 C002 C003 C004 C005 C006
        assert "C002" in ids  # 标签互斥
        assert "C003" in ids  # 维度矛盾
        assert "C004" in ids  # 证据不足
        assert "C005" in ids  # 超量刑
        assert "C006" in ids  # 法律版本

    def test_no_conflict_clean_case(self) -> None:
        """无任何冲突的干净案例."""
        # 初始化变量 dimension_results
        dimension_results = {
            "dimension1": {"score": 6.0, "reasoning": "流水30万,情节较轻"},
            "dimension2": {"score": 5.0, "reasoning": "情节较轻"},
            "dimension3": {"score": 5.0, "reasoning": "一档量刑"},
        }
        # 初始化变量 tags
        tags = [
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F031",
                # 初始化变量 matched_text
                matched_text="自首",
                # 初始化变量 confidence
                confidence=0.9,
                # 初始化变量 source_span
                source_span=(0, 2),
            ),
        ]
        # 不互相冲突的规则,也无 2025 版本
        rules = [
            Rule(
                # 初始化变量 rule_id
                rule_id="R001",
                # 初始化变量 name
                name="x",
                # 初始化变量 source_law
                source_law="帮信解释(法释〔2019〕15号)",
                # 初始化变量 article
                article="第11条",
                # 初始化变量 conditions
                conditions="x",
                # 初始化变量 conclusion
                conclusion="y",
                # 初始化变量 weight
                weight=0.5,  # 轻量,不会触发 C004
            )
        ]
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=tags, rule_hits=rules, dimension_results=dimension_results
        )
        # 应为空(无冲突)
        assert result == []


# ---------------------------------------------------------------------------
# 模块级便捷函数
# ---------------------------------------------------------------------------


# 定义 TestModuleLevelFunction 类
class TestModuleLevelFunction:
    """detect_conflicts 便捷函数测试."""

    def test_detect_conflicts_returns_list(self) -> None:
        # 函数 test_detect_conflicts_returns_list 的初始化逻辑
        result = detect_conflicts(
            # 初始化变量 tags
            tags=[],
            # 初始化变量 rule_hits
            rule_hits=[],
            # 初始化变量 dimension_results
            dimension_results={},
        )
        assert isinstance(result, list)

    def test_detect_conflicts_with_dimension_results(self) -> None:

        # 执行 test_unknown_check_id_is_skipped 函数的核心逻辑
        result = detect_conflicts(
            # 初始化变量 tags
            tags=[],
            # 初始化变量 rule_hits
            rule_hits=[],
            # 初始化变量 dimension_results
            dimension_results={"dimension1": {"score": 5.0, "reasoning": ""}},
        )
        assert isinstance(result, list)

    def test_detect_conflicts_none_dimension_results(self) -> None:
        """dimension_results=None 时不应崩溃."""
        # 初始化变量 result
        result = detect_conflicts(
            # 初始化变量 tags
            tags=[],
            # 初始化变量 rule_hits
            rule_hits=[],
            # 初始化变量 dimension_results
            dimension_results=None,
        )
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# 边界与错误处理
# ---------------------------------------------------------------------------


# 定义 TestEdgeCases 类
class TestEdgeCases:
    """边界场景与错误处理."""

    def test_unknown_check_id_is_skipped(self) -> None:
        """未知的 check_id 应被跳过,不抛异常."""
        # 初始化变量 checks
        checks = [
            ConflictCheck(
                # 初始化变量 check_id
                check_id="C999",  # 不存在
                name="未知",
                # 初始化变量 rule_a
                rule_a="",
                # 初始化变量 rule_b
                rule_b="",
                # 初始化变量 description
                description="d",
                # 初始化变量 resolution_strategy
                resolution_strategy="r",
            )
        ]
        # 初始化变量 detector
        detector = ConflictDetector(checks=checks)
        # 不应抛异常,返回空(因为该 check_id 无法匹配任何具体检测)
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=[], rule_hits=[], dimension_results={}
        )
        # C999 会被跳过,不会出现在结果中
        assert all(c.check_id != "C999" for c in result)

    def test_conflict_has_resolution_strategy(self) -> None:
        """所有检测到的 conflict 都应包含 resolution_strategy."""
        # 初始化变量 tags
        tags = [
            TagMatch(tag_id="F001", matched_text="开卡", confidence=0.8, source_span=(0, 2)),
            TagMatch(tag_id="F002", matched_text="卖卡", confidence=0.75, source_span=(3, 5)),
        ]
        # 初始化变量 detector
        detector = ConflictDetector()
        # 初始化变量 result
        result = detector.detect_conflicts(
            # 初始化变量 tags
            tags=tags, rule_hits=[], dimension_results={}
        )
        # 循环遍历：处理业务逻辑
        for c in result:
            assert c.resolution_strategy
            assert c.description

    def test_custom_checks_constructor(self) -> None:
        """自定义 checks 参数应被使用."""
        # 初始化变量 custom_checks
        custom_checks = load_conflicts()[:2]  # 只用前 2 个
        detector = ConflictDetector(checks=custom_checks)
        assert len(detector._checks) == 2
