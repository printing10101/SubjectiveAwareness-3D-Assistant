"""报告内容生成器单元测试.

覆盖10章生成函数及 generate_report 核心函数，确保结构正确、引用完整。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.models.case import Case, CaseStatus
from app.services.report import (
    Citation,
    ch1_basic_info,
    ch2_fact_summary,
    ch3_dimensional_analysis,
    ch4_triggered_rules,
    ch5_fact_tags,
    ch6_conflict_results,
    ch7_similar_cases,
    ch8_sentencing,
    ch9_legal_basis,
    ch10_review_conclusion,
    generate_report,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_case() -> Case:
    """创建模拟案件对象."""
    case = MagicMock(spec=Case)
    case.id = 1
    case.title = "张某帮信罪案"
    case.status = CaseStatus.completed
    case.description = "被告人张某明知他人利用信息网络实施犯罪，仍提供银行卡帮助。"
    case.case_text = "被告人张某明知他人利用信息网络实施犯罪，仍提供银行卡帮助。"
    return case


@pytest.fixture
def sample_analysis_v2() -> dict:
    """V2 格式分析结果."""
    return {
        "subjective_knowledge": "明知",
        "sentence": "有期徒刑一年",
        "timestamp": "2024-01-01T00:00:00Z",
        "fallback": False,
        "dimension1": {
            "reasoning": "构成要件分析结果",
            "tier": "T2",
            "confidence": 0.85,
            "key_indicators": ["提供银行卡", "明知"],
        },
        "dimension2": {
            "reasoning": "情节模式分析结果",
            "tier": "T2",
            "confidence": 0.80,
            "pattern_match": "标准帮信",
        },
        "dimension3": {
            "reasoning": "矛盾分析结果",
            "tier": "T2",
            "confidence": 0.75,
            "contradictions": [],
        },
        "triggered_rule_ids": ["R001", "R002"],
        "matched_tag_ids": ["TAG01"],
        "conflicts": [],
        "final_verdict": {
            "final_tier": "T2",
            "confidence": 0.82,
        },
    }


@pytest.fixture
def sample_rule_hits() -> list[dict]:
    """规则命中列表."""
    return [
        {"rule_id": "R001", "description": "提供银行卡帮助", "severity": "high"},
        {"rule_id": "R002", "description": "流水金额超阈值", "severity": "medium"},
    ]


@pytest.fixture
def sample_tags() -> list[dict]:
    """标签列表."""
    return [
        {"tag_id": "TAG01", "name": "银行卡帮助", "description": "提供银行卡进行支付结算", "category": "行为方式"},
    ]


@pytest.fixture
def sample_similar_cases() -> list[dict]:
    """相似案例列表."""
    return [
        {
            "case_id": 100,
            "title": "李某帮信罪案",
            "summary": "李某提供银行卡帮助，判处有期徒刑八个月",
            "similarity": 0.92,
            "verdict": "有期徒刑八个月",
        },
    ]


# ---------------------------------------------------------------------------
# Citation 测试
# ---------------------------------------------------------------------------


class TestCitation:
    """Citation 数据结构测试."""

    def test_citation_init(self):
        """测试初始化."""
        c = Citation(0, 10, "测试文本")
        assert c.start == 0
        assert c.end == 10
        assert c.text == "测试文本"

    def test_citation_to_dict(self):
        """测试转字典."""
        c = Citation(5, 20, "引用内容")
        d = c.to_dict()
        assert d == {"start": 5, "end": 20, "text": "引用内容"}


# ---------------------------------------------------------------------------
# 各章节生成函数测试
# ---------------------------------------------------------------------------


class TestCh1BasicInfo:
    """第1章：基本信息."""

    def test_contains_required_fields(self, mock_case, sample_analysis_v2):
        """测试包含必要字段."""
        now = datetime.now()
        result = ch1_basic_info(mock_case, sample_analysis_v2, now)
        assert result["chapter_id"] == "ch1"
        assert result["title"] == "基本信息"
        assert len(result["sections"]) == 1
        content = result["sections"][0]["content"]
        assert "案件编号" in content
        assert "案件名称" in content
        assert "分析日期" in content

    def test_case_id_matches(self, mock_case, sample_analysis_v2):
        """测试案件编号一致."""
        result = ch1_basic_info(mock_case, sample_analysis_v2, datetime.now())
        assert result["sections"][0]["content"]["案件编号"] == "1"


class TestCh2FactSummary:
    """第2章：事实摘要."""

    def test_contains_citations(self, mock_case, sample_analysis_v2):
        """测试包含引用段落."""
        result = ch2_fact_summary(mock_case, sample_analysis_v2)
        assert result["chapter_id"] == "ch2"
        citations = result["sections"][0]["citations"]
        assert len(citations) > 0
        assert "start" in citations[0]
        assert "end" in citations[0]
        assert "text" in citations[0]

    def test_empty_description_fallback(self, mock_case, sample_analysis_v2):
        """测试空描述降级."""
        mock_case.description = None
        result = ch2_fact_summary(mock_case, sample_analysis_v2)
        assert result["sections"][0]["content"] == "无案件描述"


class TestCh3DimensionalAnalysis:
    """第3章：维度分析."""

    def test_three_dimensions(self, mock_case, sample_analysis_v2):
        """测试三个维度都生成."""
        result = ch3_dimensional_analysis(mock_case, sample_analysis_v2)
        assert result["chapter_id"] == "ch3"
        assert len(result["sections"]) == 3
        headings = [s["heading"] for s in result["sections"]]
        assert "维度1：构成要件分析" in headings
        assert "维度2：情节模式分析" in headings
        assert "维度3：矛盾分析" in headings

    def test_dimension_has_tier(self, mock_case, sample_analysis_v2):
        """测试维度包含档级信息."""
        result = ch3_dimensional_analysis(mock_case, sample_analysis_v2)
        for section in result["sections"]:
            assert "tier" in section
            assert "confidence" in section

    def test_missing_dimensions(self, mock_case):
        """测试缺少维度时不报错."""
        empty_result = {}
        result = ch3_dimensional_analysis(mock_case, empty_result)
        assert len(result["sections"]) == 0


class TestCh4TriggeredRules:
    """第4章：触发规则."""

    def test_with_rule_hits(self, mock_case, sample_analysis_v2, sample_rule_hits):
        """测试有规则命中."""
        result = ch4_triggered_rules(mock_case, sample_analysis_v2, sample_rule_hits)
        assert result["chapter_id"] == "ch4"
        assert len(result["sections"]) == 2

    def test_with_triggered_rule_ids(self, mock_case, sample_analysis_v2):
        """测试仅从分析结果提取规则ID."""
        result = ch4_triggered_rules(mock_case, sample_analysis_v2)
        assert len(result["sections"]) == 2  # R001, R002

    def test_no_rules(self, mock_case):
        """测试无规则命中."""
        result = ch4_triggered_rules(mock_case, {"triggered_rule_ids": []})
        assert result["sections"][0]["heading"] == "无触发规则"


class TestCh5FactTags:
    """第5章：事实标签."""

    def test_with_tags(self, mock_case, sample_analysis_v2, sample_tags):
        """测试有标签."""
        result = ch5_fact_tags(mock_case, sample_analysis_v2, sample_tags)
        assert result["chapter_id"] == "ch5"
        assert len(result["sections"]) == 1
        assert result["sections"][0]["tag_id"] == "TAG01"

    def test_no_tags(self, mock_case):
        """测试无标签."""
        result = ch5_fact_tags(mock_case, {"matched_tag_ids": []})
        assert result["sections"][0]["heading"] == "无事实标签"


class TestCh6ConflictResults:
    """第6章：冲突结果."""

    def test_with_conflicts(self, mock_case):
        """测试有冲突."""
        analysis = {
            "conflicts": [
                {"type": "维度冲突", "description": "维度1和维度2结论不一致", "severity": "medium", "resolution": "取高置信度"},
            ]
        }
        result = ch6_conflict_results(mock_case, analysis)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["heading"] == "维度冲突"

    def test_no_conflicts(self, mock_case):
        """测试无冲突."""
        result = ch6_conflict_results(mock_case, {"conflicts": []})
        assert result["sections"][0]["heading"] == "无冲突"


class TestCh7SimilarCases:
    """第7章：相似案例."""

    def test_with_similar_cases(self, mock_case, sample_analysis_v2, sample_similar_cases):
        """测试有相似案例."""
        result = ch7_similar_cases(mock_case, sample_analysis_v2, sample_similar_cases)
        assert result["chapter_id"] == "ch7"
        assert len(result["sections"]) == 1
        assert result["sections"][0]["similarity"] == 0.92

    def test_no_similar_cases(self, mock_case):
        """测试无相似案例."""
        result = ch7_similar_cases(mock_case, {})
        assert result["sections"][0]["heading"] == "无相似案例"


class TestCh8Sentencing:
    """第8章：量刑建议."""

    def test_tier_and_sentence(self, mock_case, sample_analysis_v2):
        """测试档级和量刑区间."""
        result = ch8_sentencing(mock_case, sample_analysis_v2)
        assert result["chapter_id"] == "ch8"
        main_section = result["sections"][0]
        assert main_section["tier"] == "T2"
        assert "sentence_band" in main_section

    def test_includes_subjective_knowledge(self, mock_case, sample_analysis_v2):
        """测试包含主观明知."""
        result = ch8_sentencing(mock_case, sample_analysis_v2)
        headings = [s["heading"] for s in result["sections"]]
        assert "主观明知程度" in headings

    def test_invalid_tier_fallback(self, mock_case):
        """测试无效档级降级为T2."""
        analysis = {"final_verdict": {"final_tier": "INVALID", "confidence": 0.5}}
        result = ch8_sentencing(mock_case, analysis)
        assert result["sections"][0]["tier"] == "T2"


class TestCh9LegalBasis:
    """第9章：法律依据."""

    def test_contains_laws(self, mock_case, sample_analysis_v2):
        """测试包含法律条文."""
        result = ch9_legal_basis(mock_case, sample_analysis_v2)
        assert result["chapter_id"] == "ch9"
        laws = result["sections"][0]["laws"]
        assert len(laws) >= 1
        assert "law" in laws[0]
        assert "article" in laws[0]


class TestCh10ReviewConclusion:
    """第10章：审查结论."""

    def test_conclusion_text(self, mock_case, sample_analysis_v2):
        """测试结论内容."""
        result = ch10_review_conclusion(mock_case, sample_analysis_v2)
        assert result["chapter_id"] == "ch10"
        main = result["sections"][0]
        assert "final_tier" in main
        assert "confidence" in main
        assert "综合分析" in main["content"] or "经过" in main["content"]

    def test_invalid_tier_fallback(self, mock_case):
        """测试无效档级降级."""
        analysis = {"final_verdict": {"final_tier": "XXX", "confidence": 0.5}}
        result = ch10_review_conclusion(mock_case, analysis)
        assert result["sections"][0]["final_tier"] == "T2"


# ---------------------------------------------------------------------------
# generate_report 核心函数测试
# ---------------------------------------------------------------------------


class TestGenerateReport:
    """核心报告生成函数测试."""

    def test_returns_10_chapters(
        self, mock_case, sample_analysis_v2, sample_rule_hits, sample_tags, sample_similar_cases
    ):
        """测试返回10个章节."""
        report = generate_report(
            analysis_result=sample_analysis_v2,
            case=mock_case,
            rule_hits=sample_rule_hits,
            tags=sample_tags,
            similar_cases=sample_similar_cases,
        )
        assert "chapters" in report
        assert len(report["chapters"]) == 10

    def test_chapter_ids_complete(self, mock_case, sample_analysis_v2):
        """测试章节ID完整."""
        report = generate_report(sample_analysis_v2, mock_case)
        expected_ids = {f"ch{i}" for i in range(1, 11)}
        actual_ids = set(report["chapters"].keys())
        assert actual_ids == expected_ids

    def test_report_metadata(self, mock_case, sample_analysis_v2):
        """测试报告元数据."""
        report = generate_report(sample_analysis_v2, mock_case)
        assert report["case_id"] == mock_case.id
        assert report["version"] == "1.0.0"
        assert "generated_at" in report
        assert report["metadata"]["total_chapters"] == 10

    def test_each_chapter_has_title(self, mock_case, sample_analysis_v2):
        """测试每章都有标题."""
        report = generate_report(sample_analysis_v2, mock_case)
        for ch_id, chapter in report["chapters"].items():
            assert "title" in chapter, f"{ch_id} 缺少 title"
            assert "sections" in chapter, f"{ch_id} 缺少 sections"

    def test_with_minimal_analysis(self, mock_case):
        """测试最小化分析结果不报错."""
        minimal = {"timestamp": "2024-01-01T00:00:00Z"}
        report = generate_report(minimal, mock_case)
        assert len(report["chapters"]) == 10

    def test_with_all_parameters(
        self, mock_case, sample_analysis_v2, sample_rule_hits, sample_tags, sample_similar_cases
    ):
        """测试所有参数传入."""
        report = generate_report(
            analysis_result=sample_analysis_v2,
            case=mock_case,
            rule_hits=sample_rule_hits,
            tags=sample_tags,
            similar_cases=sample_similar_cases,
        )
        # 验证第4章有规则数据
        ch4 = report["chapters"]["ch4"]
        assert len(ch4["sections"]) == 2
        # 验证第7章有相似案例
        ch7 = report["chapters"]["ch7"]
        assert len(ch7["sections"]) == 1
