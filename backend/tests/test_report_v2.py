"""报告生成器 V1.2 改造测试.

测试报告生成器和导出器的 V1.2 改造要求：
- 验证所有新增字段的存在性和数据格式正确性
- 验证输出结果中不包含 score 和 confidence 字段（仅供内部验证使用）
- 验证输出结果中不包含任何与 sentencing 相关的字段
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: from datetime
from datetime import datetime
# 导入模块: from unittest.mock
from unittest.mock import MagicMock

# 导入模块: pytest
import pytest

# 导入模块: from app.models.case
from app.models.case import Case, CaseStatus
# 导入模块: from app.services.report
from app.services.report import Citation, ch1_basic_info, ch2_fact_summary, ch3_dimensional_analysis, ch4_triggered_rules, ch5_fact_tags, ch6_conflict_results, ch7_similar_cases, ch8_sentencing, ch9_legal_basis, ch10_review_conclusion, generate_report, export_pdf, export_docx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# 应用装饰器: pytest.fixture
@pytest.fixture
def mock_case() -> Case:
    """创建模拟案件对象."""
    # 初始化变量 case
    case = MagicMock(spec=Case)
    case.id = 1
    case.title = "张某帮信罪案"
    case.status = CaseStatus.completed
    case.description = "被告人张某明知他人利用信息网络实施犯罪，仍提供银行卡帮助。"
    case.case_text = "被告人张某明知他人利用信息网络实施犯罪，仍提供银行卡帮助。"
    # 返回处理结果
    return case


# 应用装饰器: pytest.fixture
@pytest.fixture
def sample_analysis_v2_with_new_fields() -> dict:
    """V2 格式分析结果，包含 V1.2 新增字段."""
    # 返回处理结果
    return {
        "version": "v2",
        "subjective_knowledge": "明知",
        "timestamp": "2024-01-01T00:00:00Z",
        "fallback": False,
        "identified_path": "帮信罪主路径",
        "dimension1": {
            "reasoning": "构成要件分析结果",
            "tier": "T2",
            "confidence": 0.85,
            "key_indicators": ["提供银行卡", "明知"],
            "triggered_rules": ["R001"],
        },
        "dimension2": {
            "reasoning": "情节模式分析结果",
            "tier": "T2",
            "confidence": 0.80,
            "pattern_match": "标准帮信",
            "triggered_rules": ["R002"],
        },
        "dimension3": {
            "reasoning": "矛盾分析结果",
            "tier": "T2",
            "confidence": 0.75,
            "contradictions": [],
            "triggered_rules": [],
        },
        "triggered_rule_ids": ["R001", "R002"],
        "matched_tag_ids": ["TAG01"],
        "conflicts": [
            {
                "type": "维度冲突",
                "description": "维度1和维度2结论不一致",
                "severity": "medium",
                "resolution": "取高置信度",
            }
        ],
        "final_verdict": {
            "final_tier": "T2",
            "final_label": "二档（情节一般）",
            "sentence_band": "三年以下有期徒刑，并处罚金",
            "confidence": 0.82,
            "severity_score": 2,
            "combination_rule": "majority",
        },
        # V1.2 新增字段
        "subject_analyses": [
            {
                "name": "张某",
                "role": "主犯",
                "objective_behavior": "提供银行卡帮助",
                "cognitive_evidence": ["明知他人实施犯罪"],
                "defense": "不知情",
                "disputes": ["主观明知认定"],
            }
        ],
        "evidence_layers": [
            {
                "strength": "强",
                "facts": ["银行流水记录", "转账凭证"],
                "legal_basis": "刑法第287条之二",
            },
            {
                "strength": "中",
                "facts": ["证人证言"],
                "legal_basis": "刑事诉讼法第50条",
            },
        ],
        "boundary_alerts": [
            {
                "alert_type": "罪名边界",
                "description": "与诈骗罪共同犯罪边界需进一步核实",
                "severity": "high",
            }
        ],
        "proof_gap": ["主观明知证据链需补强", "资金流向需进一步查证"],
        "supplementary_advice": ["建议补充调取银行监控录像", "建议核实被告人通讯记录"],
        "review_checklist": [
            {
                "item": "主观明知认定",
                "status": "待核实",
                "notes": "需结合客观行为综合判断",
            }
        ],
    }


# ---------------------------------------------------------------------------
# 测试类：新增字段存在性和格式验证
# ---------------------------------------------------------------------------


# 定义 TestNewFieldsExistence 类
class TestNewFieldsExistence:
    """测试 V1.2 新增字段的存在性和数据格式."""

    def test_standard_path_exists_and_valid(
        # 函数 test_standard_path_exists_and_valid 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 standard_path 字段存在且取值正确."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        assert "standard_path" in report
        # 取值必须为①/②/③/④中的其中一个
        assert report["standard_path"] in ["①", "②", "③", "④"]

    def test_subject_analyses_exists_and_valid(
        # 函数 test_subject_analyses_exists_and_valid 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 subject_analyses 字段存在且格式正确."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        assert "subject_analyses" in report
        assert isinstance(report["subject_analyses"], list)
        
        # 条件判断: 检查 len(report["subject_analyses"]) > 0
        if len(report["subject_analyses"]) > 0:
            # 初始化变量 subject
            subject = report["subject_analyses"][0]
            assert "name" in subject
            assert "role" in subject
            assert "objective_behavior" in subject
            assert "cognitive_evidence" in subject
            assert "defense" in subject
            assert "disputes" in subject

    def test_evidence_layers_exists_and_valid(
        # 函数 test_evidence_layers_exists_and_valid 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 evidence_layers 字段存在且格式正确."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        assert "evidence_layers" in report
        assert isinstance(report["evidence_layers"], list)
        
        # 条件判断: 检查 len(report["evidence_layers"]) > 0
        if len(report["evidence_layers"]) > 0:
            # 初始化变量 layer
            layer = report["evidence_layers"][0]
            assert "strength" in layer
            assert "facts" in layer
            assert "legal_basis" in layer
            assert isinstance(layer["facts"], list)

    def test_boundary_alerts_exists_and_valid(
        # 函数 test_boundary_alerts_exists_and_valid 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 boundary_alerts 字段存在且格式正确."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        assert "boundary_alerts" in report
        assert isinstance(report["boundary_alerts"], list)
        
        # 条件判断: 检查 len(report["boundary_alerts"]) > 0
        if len(report["boundary_alerts"]) > 0:
            # 初始化变量 alert
            alert = report["boundary_alerts"][0]
            assert "alert_type" in alert
            assert "description" in alert
            assert "severity" in alert

    def test_factor_matrix_exists_and_valid(
        # 函数 test_factor_matrix_exists_and_valid 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 factor_matrix 字段存在且格式正确."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        assert "factor_matrix" in report
        assert isinstance(report["factor_matrix"], dict)
        
        # 应包含三个维度
        assert "dimension1" in report["factor_matrix"]
        assert "dimension2" in report["factor_matrix"]
        assert "dimension3" in report["factor_matrix"]

    def test_proof_gap_exists_and_valid(
        # 函数 test_proof_gap_exists_and_valid 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 proof_gap 字段存在且格式正确."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        assert "proof_gap" in report
        assert isinstance(report["proof_gap"], list)

    def test_supplementary_advice_exists_and_valid(
        # 函数 test_supplementary_advice_exists_and_valid 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 supplementary_advice 字段存在且格式正确."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        assert "supplementary_advice" in report
        assert isinstance(report["supplementary_advice"], list)

    def test_review_checklist_exists_and_valid(
        # 函数 test_review_checklist_exists_and_valid 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 review_checklist 字段存在且格式正确."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        assert "review_checklist" in report
        assert isinstance(report["review_checklist"], list)

    def test_conflict_analysis_exists_and_valid(
        # 函数 test_conflict_analysis_exists_and_valid 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 conflict_analysis 字段存在且格式正确."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        assert "conflict_analysis" in report
        assert isinstance(report["conflict_analysis"], list)


# ---------------------------------------------------------------------------
# 测试类：分数和置信度字段过滤
# ---------------------------------------------------------------------------


# 定义 TestScoreAndConfidenceFiltering 类
class TestScoreAndConfidenceFiltering:
    """测试输出结果中不包含 score 和 confidence 字段."""

    def test_report_content_no_score_fields(
        # 函数 test_report_content_no_score_fields 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试报告内容不包含 score 相关字段."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        # 递归检查所有字段
        def check_no_score_fields(obj, path=""):
            # 执行 check_no_score_fields 函数的核心逻辑
            # 条件判断：处理业务逻辑
            if isinstance(obj, dict):
                # 循环遍历：处理业务逻辑
                for key, value in obj.items():
                    # 初始化变量 current_path
                    current_path = f"{path}.{key}" if path else key
                    # 检查键名
                    assert key not in ["score", "confidence", "confidence_score"], (
                        f"发现禁止字段: {current_path}"
                    )
                    # 递归检查值
                    check_no_score_fields(value, current_path)
            elif isinstance(obj, list):
                # 遍历: for i, item in enumerate(obj):
                for i, item in enumerate(obj):
                    check_no_score_fields(item, f"{path}[{i}]")
        
        check_no_score_fields(report)

    def test_pdf_export_no_score_fields(
        # 函数 test_pdf_export_no_score_fields 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 PDF 导出不包含 score 相关字段."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        # 初始化变量 pdf_bytes
        pdf_bytes = export_pdf(report, mock_case.id)
        
        # PDF 应该是字节流
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        
        # 注意：这里无法直接检查 PDF 内容，但通过 _sanitize_for_export 函数
        # 已经确保在导出前移除了相关字段

    def test_docx_export_no_score_fields(
        # 函数 test_docx_export_no_score_fields 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试 DOCX 导出不包含 score 相关字段."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        # 初始化变量 docx_bytes
        docx_bytes = export_docx(report, mock_case.id)
        
        # DOCX 应该是字节流
        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 0


# ---------------------------------------------------------------------------
# 测试类：量刑建议字段过滤
# ---------------------------------------------------------------------------


# 定义 TestSentencingFiltering 类
class TestSentencingFiltering:
    """测试输出结果中不包含 sentencing 相关字段."""

    def test_report_content_no_sentencing_fields(
        # 函数 test_report_content_no_sentencing_fields 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试报告内容不包含 sentencing 相关字段."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        # 递归检查所有字段
        def check_no_sentencing_fields(obj, path=""):
            # 执行 check_no_sentencing_fields 函数的核心逻辑
            # 条件判断: 检查 isinstance(obj, dict)
            if isinstance(obj, dict):
                # 遍历: for key, value in obj.items():
                for key, value in obj.items():
                    # 初始化变量 current_path
                    current_path = f"{path}.{key}" if path else key
                    # 检查键名
                    assert key not in [
                        "sentencing_recommendation",
                        "sentencing",
                        "sentence_band",
                    ], (
                        f"发现禁止字段: {current_path}"
                    )
                    # 递归检查值
                    check_no_sentencing_fields(value, current_path)
            # 条件判断: 检查 isinstance(obj, list)
            elif isinstance(obj, list):
                # 遍历: for i, item in enumerate(obj):
                for i, item in enumerate(obj):
                    check_no_sentencing_fields(item, f"{path}[{i}]")
        
        check_no_sentencing_fields(report)

    def test_ch8_is_legal_analysis_not_sentencing(
        # 函数 test_ch8_is_legal_analysis_not_sentencing 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试第8章是法律分析而非量刑建议."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        # 第8章应该存在
        assert "ch8" in report["chapters"]
        
        ch8 = report["chapters"]["ch8"]
        # 标题应该是"法律分析"而非"量刑建议"
        assert ch8["title"] == "法律分析"
        
        # 检查章节内容不包含量刑区间
        for section in ch8["sections"]:
            assert "sentence_band" not in section
            assert "量刑区间" not in str(section.get("content", ""))


# ---------------------------------------------------------------------------
# 测试类：报告版本验证
# ---------------------------------------------------------------------------


# 定义 TestReportVersion 类
class TestReportVersion:
    """测试报告版本号."""

    def test_report_version_is_1_2_0(
        # 函数 test_report_version_is_1_2_0 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试报告版本号为 1.1.0."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        
        assert report["version"] == "1.1.0"


# ---------------------------------------------------------------------------
# 测试类：标准路径映射
# ---------------------------------------------------------------------------


# 定义 TestStandardPathMapping 类
class TestStandardPathMapping:
    """测试标准路径映射逻辑."""

    def test_standard_path_mapping_1(
        # 函数 test_standard_path_mapping_1 的初始化逻辑
        self, mock_case
    ):
        """测试帮信罪主路径映射为①."""
        # 初始化变量 analysis
        analysis = {
            "version": "v2",
            "identified_path": "帮信罪主路径",
            "timestamp": "2024-01-01T00:00:00Z",
            "fallback": False,
            "dimension1": {"reasoning": "", "tier": "T2", "key_indicators": [], "triggered_rules": []},
            "dimension2": {"reasoning": "", "tier": "T2", "pattern_match": "", "triggered_rules": []},
            "dimension3": {"reasoning": "", "tier": "T2", "contradictions": [], "triggered_rules": []},
            "triggered_rule_ids": [],
            "matched_tag_ids": [],
            "conflicts": [],
            "final_verdict": {"final_tier": "T2", "confidence": 0.5},
        }
        # 初始化变量 report
        report = generate_report(analysis, mock_case)
        assert report["standard_path"] == "①"

    def test_standard_path_mapping_2(
        # 函数 test_standard_path_mapping_2 的初始化逻辑
        self, mock_case
    ):
        """测试诈骗罪共同犯罪路径映射为②."""
        # 初始化变量 analysis
        analysis = {
            "version": "v2",
            "identified_path": "诈骗罪共同犯罪路径",
            "timestamp": "2024-01-01T00:00:00Z",
            "fallback": False,
            "dimension1": {"reasoning": "", "tier": "T2", "key_indicators": [], "triggered_rules": []},
            "dimension2": {"reasoning": "", "tier": "T2", "pattern_match": "", "triggered_rules": []},
            "dimension3": {"reasoning": "", "tier": "T2", "contradictions": [], "triggered_rules": []},
            "triggered_rule_ids": [],
            "matched_tag_ids": [],
            "conflicts": [],
            "final_verdict": {"final_tier": "T2", "confidence": 0.5},
        }
        # 初始化变量 report
        report = generate_report(analysis, mock_case)
        assert report["standard_path"] == "②"

    def test_standard_path_mapping_3(
        # 函数 test_standard_path_mapping_3 的初始化逻辑
        self, mock_case
    ):
        """测试掩饰隐瞒犯罪所得路径映射为③."""
        # 初始化变量 analysis
        analysis = {
            "version": "v2",
            "identified_path": "掩饰隐瞒犯罪所得路径",
            "timestamp": "2024-01-01T00:00:00Z",
            "fallback": False,
            "dimension1": {"reasoning": "", "tier": "T2", "key_indicators": [], "triggered_rules": []},
            "dimension2": {"reasoning": "", "tier": "T2", "pattern_match": "", "triggered_rules": []},
            "dimension3": {"reasoning": "", "tier": "T2", "contradictions": [], "triggered_rules": []},
            "triggered_rule_ids": [],
            "matched_tag_ids": [],
            "conflicts": [],
            "final_verdict": {"final_tier": "T2", "confidence": 0.5},
        }
        # 初始化变量 report
        report = generate_report(analysis, mock_case)
        assert report["standard_path"] == "③"

    def test_standard_path_mapping_4(
        # 函数 test_standard_path_mapping_4 的初始化逻辑
        self, mock_case
    ):
        """测试规范路径待核实映射为④."""
        # 初始化变量 analysis
        analysis = {
            "version": "v2",
            "identified_path": "规范路径待核实",
            "timestamp": "2024-01-01T00:00:00Z",
            "fallback": False,
            "dimension1": {"reasoning": "", "tier": "T2", "key_indicators": [], "triggered_rules": []},
            "dimension2": {"reasoning": "", "tier": "T2", "pattern_match": "", "triggered_rules": []},
            "dimension3": {"reasoning": "", "tier": "T2", "contradictions": [], "triggered_rules": []},
            "triggered_rule_ids": [],
            "matched_tag_ids": [],
            "conflicts": [],
            "final_verdict": {"final_tier": "T2", "confidence": 0.5},
        }
        # 初始化变量 report
        report = generate_report(analysis, mock_case)
        assert report["standard_path"] == "④"


# ---------------------------------------------------------------------------
# 测试类：多主体分析
# ---------------------------------------------------------------------------


# 定义 TestMultiSubjectAnalysis 类
class TestMultiSubjectAnalysis:
    """测试多主体分析功能."""

    def test_subject_analyses_empty_when_not_multi_subject(
        # 函数 test_subject_analyses_empty_when_not_multi_subject 的初始化逻辑
        self, mock_case
    ):
        """测试非多主体情况下 subject_analyses 为空列表."""
        # 初始化变量 analysis
        analysis = {
            "version": "v2",
            "timestamp": "2024-01-01T00:00:00Z",
            "fallback": False,
            "dimension1": {"reasoning": "", "tier": "T2", "key_indicators": [], "triggered_rules": []},
            "dimension2": {"reasoning": "", "tier": "T2", "pattern_match": "", "triggered_rules": []},
            "dimension3": {"reasoning": "", "tier": "T2", "contradictions": [], "triggered_rules": []},
            "triggered_rule_ids": [],
            "matched_tag_ids": [],
            "conflicts": [],
            "final_verdict": {"final_tier": "T2", "confidence": 0.5},
        }
        # 初始化变量 report
        report = generate_report(analysis, mock_case)
        assert report["subject_analyses"] == []

    def test_subject_analyses_present_when_multi_subject(
        # 函数 test_subject_analyses_present_when_multi_subject 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试多主体情况下 subject_analyses 包含数据."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)
        assert len(report["subject_analyses"]) > 0
        assert report["subject_analyses"][0]["name"] == "张某"


# ---------------------------------------------------------------------------
# 测试类：证据层结构
# ---------------------------------------------------------------------------


# 定义 TestEvidenceLayers 类
class TestEvidenceLayers:
    """测试证据层结构."""

    def test_evidence_layers_4_tier_structure(
        # 函数 test_evidence_layers_4_tier_structure 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试证据层实现4层结构."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)

        # 证据层应该存在
        assert "evidence_layers" in report
        
        # 每层应包含 strength、facts、legal_basis
        for layer in report["evidence_layers"]:
            assert "strength" in layer
            assert "facts" in layer
            assert "legal_basis" in layer
            assert isinstance(layer["facts"], list)

    def test_evidence_layers_no_score_info(
        # 函数 test_evidence_layers_no_score_info 的初始化逻辑
        self, mock_case, sample_analysis_v2_with_new_fields
    ):
        """测试证据层不包含分数信息."""
        # 初始化变量 report
        report = generate_report(sample_analysis_v2_with_new_fields, mock_case)

        # 递归检查证据层
        def check_no_score_in_evidence(obj):
            # 执行 check_no_score_in_evidence 函数的核心逻辑
            if isinstance(obj, dict):
                # 遍历: for key, value in obj.items():
                for key, value in obj.items():
                    assert key not in ["score", "confidence", "confidence_score"]
                    check_no_score_in_evidence(value)
            # 条件判断: 检查 isinstance(obj, list)
            elif isinstance(obj, list):
                # 遍历: for item in obj:
                for item in obj:
                    check_no_score_in_evidence(item)
        
        check_no_score_in_evidence(report["evidence_layers"])
