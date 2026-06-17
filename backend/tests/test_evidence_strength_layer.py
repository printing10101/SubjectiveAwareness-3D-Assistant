"""证据强度4层分级器测试.

测试场景：
1. 仅有客观异常 → 验证认知档级降一档
2. 同时有直接认知+客观异常 → 验证维持高档级
3. 4层都为空 → 验证返回低档级
4. 仅有认知增强因素和辩解检验材料 → 验证返回中低档级
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: json
import json
# 导入模块: from pathlib
from pathlib import Path

# 导入模块: pytest
import pytest

# 导入模块: from app.services.evidence_strength_layer
from app.services.evidence_strength_layer import (
    EvidenceLayer,
    EvidenceStrengthLayer,
    analyze_evidence_layers,
)
# 导入模块: from app.services.tag_extractor
from app.services.tag_extractor import TagMatch


# ---------------------------------------------------------------------------
# 测试数据加载
# ---------------------------------------------------------------------------


def _load_test_cases() -> list[dict]:
    """加载测试数据文件."""
    # 初始化变量 data_path
    data_path = Path(__file__).parent / "data" / "evidence_layer_cases.json"
    # 使用上下文管理器管理资源
    with open(data_path, encoding="utf-8") as f:
        # 初始化变量 data
        data = json.load(f)
    # 返回处理结果
    return data["test_cases"]


def _build_tag_match(tag_data: dict) -> TagMatch:
    """从测试数据构建 TagMatch 对象."""
    # 初始化变量 span
    span = tag_data["source_span"]
    # 返回处理结果
    return TagMatch(
        # 初始化变量 tag_id
        tag_id=tag_data["tag_id"],
        # 初始化变量 matched_text
        matched_text=tag_data["matched_text"],
        # 初始化变量 confidence
        confidence=tag_data["confidence"],
        # 初始化变量 source_span
        source_span=(span[0], span[1]),
        # 初始化变量 match_type
        match_type=tag_data.get("match_type", "keyword"),
    )


# ---------------------------------------------------------------------------
# 测试类
# ---------------------------------------------------------------------------


# 定义 TestEvidenceStrengthLayer 类
class TestEvidenceStrengthLayer:
    """证据强度4层分级器测试."""

    # 应用装饰器: pytest.fixture
    @pytest.fixture
    def analyzer(self) -> EvidenceStrengthLayer:
        """创建分级器实例."""
        # 返回处理结果
        return EvidenceStrengthLayer()

    # 应用装饰器: pytest.mark.parametrize
    @pytest.mark.parametrize("case_data", _load_test_cases(), ids=lambda c: c["case_id"])
    def test_layer_evidences(self, analyzer: EvidenceStrengthLayer, case_data: dict):
        """测试证据层级分析."""
        # 构建 TagMatch 列表
        tags = [_build_tag_match(t) for t in case_data["tags"]]

        # 执行分析
        report = analyzer.layer_evidences(tags)

        # 验证预期结果
        expected = case_data["expected"]
        assert report.has_direct_cognition == expected["has_direct_cognition"], (
            f"case {case_data['case_id']}: has_direct_cognition 不匹配"
        )
        assert report.has_objective_anomaly == expected["has_objective_anomaly"], (
            f"case {case_data['case_id']}: has_objective_anomaly 不匹配"
        )
        assert report.downgrade_applied == expected["downgrade_applied"], (
            f"case {case_data['case_id']}: downgrade_applied 不匹配"
        )
        assert report.cognition_tier == expected["cognition_tier"], (
            f"case {case_data['case_id']}: cognition_tier 不匹配"
        )

    def test_only_objective_anomaly_triggers_downgrade(self, analyzer: EvidenceStrengthLayer):
        """测试仅有客观异常时触发降档防护."""
        # 构建仅有客观异常的标签
        tags = [
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F001",
                # 初始化变量 matched_text
                matched_text="跨省取款",
                # 初始化变量 confidence
                confidence=0.85,
                # 初始化变量 source_span
                source_span=(0, 10),
                # 初始化变量 match_type
                match_type="keyword",
            ),
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F002",
                # 初始化变量 matched_text
                matched_text="夜间大额交易",
                # 初始化变量 confidence
                confidence=0.80,
                # 初始化变量 source_span
                source_span=(11, 25),
                # 初始化变量 match_type
                match_type="keyword",
            ),
        ]

        # 初始化变量 report
        report = analyzer.layer_evidences(tags)

        # 验证：无直接认知，有客观异常
        assert report.has_direct_cognition is False
        assert report.has_objective_anomaly is True

        # 验证：触发降档防护
        assert report.downgrade_applied is True

        # 验证：认知档级应为3（最低档）
        assert report.cognition_tier == 3

    def test_direct_cognition_plus_objective_anomaly_maintains_high_tier(
        # 函数 test_direct_cognition_plus_objective_anomaly_maintains_high_tier 的初始化逻辑
        self, analyzer: EvidenceStrengthLayer

        # 执行 test_direct_cognition_plus_objective_anomaly_maintains_high_tier 函数的核心逻辑
    ):
        """测试同时有直接认知和客观异常时维持高档级."""
        # 构建同时包含直接认知和客观异常的标签
        tags = [
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F003",
                # 初始化变量 matched_text
                matched_text="知道是洗黑钱",
                # 初始化变量 confidence
                confidence=0.90,
                # 初始化变量 source_span
                source_span=(0, 12),
                # 初始化变量 match_type
                match_type="keyword",
            ),
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F004",
                # 初始化变量 matched_text
                matched_text="承认知道资金异常",
                # 初始化变量 confidence
                confidence=0.85,
                # 初始化变量 source_span
                source_span=(13, 30),
                # 初始化变量 match_type
                match_type="keyword",
            ),
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F001",
                # 初始化变量 matched_text
                matched_text="跨省取款",
                # 初始化变量 confidence
                confidence=0.80,
                # 初始化变量 source_span
                source_span=(31, 41),
                # 初始化变量 match_type
                match_type="keyword",
            ),
        ]

        # 初始化变量 report
        report = analyzer.layer_evidences(tags)

        # 验证：有直接认知，有客观异常
        assert report.has_direct_cognition is True
        assert report.has_objective_anomaly is True

        # 验证：未触发降档防护
        assert report.downgrade_applied is False

        # 验证：认知档级应为1（最高档）
        assert report.cognition_tier == 1

    def test_all_layers_empty_returns_low_tier(self, analyzer: EvidenceStrengthLayer):
        """测试4层都为空时返回低档级."""
        tags: list[TagMatch] = []

        # 初始化变量 report
        report = analyzer.layer_evidences(tags)

        # 验证：无任何证据
        assert report.has_direct_cognition is False
        assert report.has_objective_anomaly is False

        # 验证：未触发降档防护（因为无客观异常）
        assert report.downgrade_applied is False

        # 验证：认知档级应为3（最低档）
        assert report.cognition_tier == 3

    def test_guard_against_single_layer_override(self, analyzer: EvidenceStrengthLayer):
        """测试防护逻辑方法."""
        # 构建仅有客观异常的标签
        tags = [
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F001",
                # 初始化变量 matched_text
                matched_text="跨省取款",
                # 初始化变量 confidence
                confidence=0.85,
                # 初始化变量 source_span
                source_span=(0, 10),
                # 初始化变量 match_type
                match_type="keyword",
            ),
        ]

        # 初始化变量 report
        report = analyzer.layer_evidences(tags)
        # 初始化变量 initial_tier
        initial_tier = report.cognition_tier

        # 再次应用防护逻辑
        guarded_report = analyzer.guard_against_single_layer_override(report)

        # 验证：防护逻辑已应用
        assert guarded_report.downgrade_applied is True
        # 验证：档级应降低或保持不变（已降过则不变）
        assert guarded_report.cognition_tier >= initial_tier

    def test_layer_evidences_structure(self, analyzer: EvidenceStrengthLayer):
        """测试证据层级报告结构."""
        # 初始化变量 tags
        tags = [
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F003",
                # 初始化变量 matched_text
                matched_text="知道是洗黑钱",
                # 初始化变量 confidence
                confidence=0.90,
                # 初始化变量 source_span
                source_span=(0, 12),
                # 初始化变量 match_type
                match_type="keyword",
            ),
        ]

        # 初始化变量 report
        report = analyzer.layer_evidences(tags)

        # 验证：4个层级都存在
        assert len(report.layer_results) == 4
        assert EvidenceLayer.DIRECT_COGNITION in report.layer_results
        assert EvidenceLayer.OBJECTIVE_ANOMALY in report.layer_results
        assert EvidenceLayer.COGNITION_ENHANCER in report.layer_results
        assert EvidenceLayer.DEFENSE_VERIFICATION in report.layer_results

        # 验证：每个层级都有 strength_score
        # 循环遍历：处理业务逻辑
        for layer_evidence in report.layer_results.values():
            assert 0.0 <= layer_evidence.strength_score <= 10.0

    def test_to_dict_serialization(self, analyzer: EvidenceStrengthLayer):
        """测试报告序列化."""
        # 初始化变量 tags
        tags = [
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F003",
                # 初始化变量 matched_text
                matched_text="知道是洗黑钱",
                # 初始化变量 confidence
                confidence=0.90,
                # 初始化变量 source_span
                source_span=(0, 12),
                # 初始化变量 match_type
                match_type="keyword",
            ),
        ]

        # 初始化变量 report
        report = analyzer.layer_evidences(tags)
        # 初始化变量 report_dict
        report_dict = report.to_dict()

        # 验证：字典结构正确
        assert "layers" in report_dict
        assert "cognition_tier" in report_dict
        assert "has_direct_cognition" in report_dict
        assert "has_objective_anomaly" in report_dict
        assert "downgrade_applied" in report_dict

        # 验证：可以序列化为 JSON
        json_str = json.dumps(report_dict, ensure_ascii=False)
        assert isinstance(json_str, str)


# 定义 TestConvenienceFunctions 类
class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_analyze_evidence_layers(self):
        """测试 analyze_evidence_layers 便捷函数."""
        # 初始化变量 tags
        tags = [
            TagMatch(
                # 初始化变量 tag_id
                tag_id="F001",
                # 初始化变量 matched_text
                matched_text="跨省取款",
                # 初始化变量 confidence
                confidence=0.85,
                # 初始化变量 source_span
                source_span=(0, 10),
                # 初始化变量 match_type
                match_type="keyword",
            ),
        ]

        # 初始化变量 report
        report = analyze_evidence_layers(tags)

        assert report.has_objective_anomaly is True
        assert report.cognition_tier == 3
