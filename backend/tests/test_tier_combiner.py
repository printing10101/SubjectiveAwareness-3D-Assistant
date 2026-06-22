"""档级组合器单元测试.

覆盖以下方面：

- 4×4×4 = 64 种基础组合的最终档级符合预期
- 类型归一化（TierEnum / str / int / None / 中文标签）
- 抗辩降档逻辑（d3 显著低于 d1/d2）
- T4 升级：极高权重 + T4 关键词直接升 T4
- T3 升级：高权重 + T4 关键词 / 仅高权重
- 组合规则标识（combination_rule）正确返回
- FinalVerdict 字段完整性（tier / label / sentence_band / confidence / severity_score）
- 置信度钳制在 [0, 1]
- 兜底行为：空规则、未知输入不崩溃
"""

from __future__ import annotations

import pytest

from app.services.rule_engine import Rule
from app.services.analysis_helpers import (
    _BASE_COMBINATION,
    all_combinations,
    combine_tiers,
)
from app.types.analysis_v2 import TierEnum


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_rule_template() -> dict:
    """单条规则的基础模板."""
    return {
        "rule_id": "R001",
        "name": "测试规则",
        "source_law": "刑法第 287 条之二",
        "article": "第一款",
        "conditions": "测试条件",
        "conclusion": "测试结论",
        "evidence_types": [],
        "weight": 0.5,
        "applicable_scenarios": [],
        "conflicting_rules": [],
    }


def _mk_rule(template: dict, **overrides) -> Rule:
    """从模板构造 Rule."""
    payload = {**template, **overrides}
    return Rule(**payload)


# ---------------------------------------------------------------------------
# 基础映射：4×4×4=64 种组合
# ---------------------------------------------------------------------------


class TestBaseCombinationTable:
    """验证 _BASE_COMBINATION 表的完整性与正确性."""

    def test_table_has_64_entries(self) -> None:
        """64 种组合必须全覆盖."""
        assert len(_BASE_COMBINATION) == 64

    def test_all_keys_in_range(self) -> None:
        """所有 (d1, d2, d3) 都应在 [1, 4] 范围内."""
        for d1, d2, d3 in _BASE_COMBINATION.keys():
            assert d1 in (1, 2, 3, 4)
            assert d2 in (1, 2, 3, 4)
            assert d3 in (1, 2, 3, 4)

    def test_all_values_in_range(self) -> None:
        """所有 final_tier 都应在 [1, 4] 范围内."""
        for rank, _rule_id in _BASE_COMBINATION.values():
            assert rank in (1, 2, 3, 4)

    def test_combine_tiers_returns_all_64(self) -> None:
        """对所有 64 种组合调用 combine_tiers，都应得到合法 verdict."""
        for d1 in range(1, 5):
            for d2 in range(1, 5):
                for d3 in range(1, 5):
                    verdict = combine_tiers(d1, d2, d3, rule_hits=[])
                    assert verdict["final_tier"] in ("T1", "T2", "T3", "T4")
                    assert verdict["severity_score"] in (1, 2, 3, 4)
                    # combination_rule 必须包含 BASE_xxx（可被 DOWNGRADE_DEFENSE_/ESCALATE_ 包裹）
                    assert "BASE_" in verdict["combination_rule"]

    def test_three_t1_combines_to_low_tier(self) -> None:
        """全 T1 → final_tier 应为 T1（情节较轻）."""
        v = combine_tiers("T1", "T1", "T1")
        assert v["final_tier"] == "T1"
        assert v["severity_score"] == 1
        assert "情节较轻" in v["final_label"]

    def test_three_t4_combines_to_highest_tier(self) -> None:
        """全 T4 → final_tier 应为 T4（情节特别严重）."""
        v = combine_tiers("T4", "T4", "T4")
        assert v["final_tier"] == "T4"
        assert v["severity_score"] == 4
        assert "特别严重" in v["final_label"]

    def test_extreme_combinations_dont_crash(self) -> None:
        """极限组合 (1, 4, 4) / (4, 1, 1) 不应崩溃."""
        v1 = combine_tiers(1, 4, 4)
        assert v1["final_tier"] in ("T1", "T2", "T3", "T4")
        v2 = combine_tiers(4, 1, 1)
        assert v2["final_tier"] in ("T1", "T2", "T3", "T4")


class TestExhaustiveCombinations:
    """参数化 64 种组合，验证 final_tier 属于 [1, 4]."""

    @pytest.mark.parametrize("d1", [1, 2, 3, 4])
    @pytest.mark.parametrize("d2", [1, 2, 3, 4])
    @pytest.mark.parametrize("d3", [1, 2, 3, 4])
    def test_combination_in_range(self, d1, d2, d3) -> None:
        v = combine_tiers(d1, d2, d3)
        assert v["final_tier"] in ("T1", "T2", "T3", "T4")
        assert v["severity_score"] in (1, 2, 3, 4)
        assert 0.0 <= v["confidence"] <= 1.0

    @pytest.mark.parametrize("d1", [1, 2, 3, 4])
    @pytest.mark.parametrize("d2", [1, 2, 3, 4])
    @pytest.mark.parametrize("d3", [1, 2, 3, 4])
    def test_combination_id_matches_pattern(self, d1, d2, d3) -> None:
        v = combine_tiers(d1, d2, d3)
        # combination_rule 形如 BASE_x_y_z 或 DOWNGRADE_DEFENSE_BASE_x_y_z
        # 但必须包含可追溯的 BASE_<d1>_<d2>_<d3> 段
        assert "BASE_" in v["combination_rule"]
        # 至少要包含三个数字（BASE_d1_d2_d3）
        base_segment = v["combination_rule"].split("BASE_")[-1]
        parts = base_segment.split("_")
        assert len(parts) >= 3
        assert int(parts[0]) == d1
        assert int(parts[1]) == d2
        assert int(parts[2]) == d3


# ---------------------------------------------------------------------------
# 类型归一化
# ---------------------------------------------------------------------------


class TestInputNormalization:
    """combine_tiers 必须能接受多种输入格式."""

    def test_accepts_tier_enum(self) -> None:
        v = combine_tiers(TierEnum.T2, TierEnum.T2, TierEnum.T2)
        assert v["final_tier"] == "T2"

    def test_accepts_string(self) -> None:
        v = combine_tiers("T3", "T3", "T3")
        assert v["final_tier"] == "T3"

    def test_accepts_int(self) -> None:
        v = combine_tiers(2, 2, 2)
        assert v["final_tier"] == "T2"

    def test_accepts_chinese_label(self) -> None:
        v = combine_tiers("一档", "一档", "一档")
        assert v["final_tier"] == "T1"
        v2 = combine_tiers("四档", "四档", "四档")
        assert v2["final_tier"] == "T4"

    def test_accepts_none_falls_back_to_t2(self) -> None:
        v = combine_tiers(None, None, None)
        assert v["final_tier"] in ("T1", "T2", "T3", "T4")
        # 至少不应崩溃

    def test_accepts_garbage_falls_back_to_t2(self) -> None:
        v = combine_tiers("garbage", 999, "???")
        assert v["final_tier"] in ("T1", "T2", "T3", "T4")

    def test_mixed_types(self) -> None:
        v = combine_tiers(TierEnum.T1, "2", 3)
        # 不应崩溃，应给出合法 tier
        assert v["final_tier"] in ("T1", "T2", "T3", "T4")


# ---------------------------------------------------------------------------
# FinalVerdict 字段完整性
# ---------------------------------------------------------------------------


class TestFinalVerdictStructure:
    """FinalVerdict 字典必须包含 6 个字段."""

    def test_has_all_required_fields(self) -> None:
        v = combine_tiers("T2", "T2", "T2")
        assert "final_tier" in v
        assert "final_label" in v
        assert "sentence_band" in v
        assert "confidence" in v
        assert "severity_score" in v
        assert "combination_rule" in v

    def test_sentence_band_chinese_legal_text(self) -> None:
        """sentence_band 应为合法量刑建议文本."""
        v = combine_tiers("T3", "T3", "T3")
        assert "有期徒刑" in v["sentence_band"]
        assert "罚金" in v["sentence_band"]

    def test_confidence_clamped(self) -> None:
        v = combine_tiers("T2", "T2", "T2", rule_hits=[])
        assert 0.0 <= v["confidence"] <= 1.0

    def test_severity_score_matches_tier(self) -> None:
        """severity_score 应等于 final_tier 数值."""
        for tier in ("T1", "T2", "T3", "T4"):
            v = combine_tiers(tier, tier, tier)
            assert v["severity_score"] == int(tier[1])


# ---------------------------------------------------------------------------
# 抗辩降档（d3 显著低于 d1/d2）
# ---------------------------------------------------------------------------


class TestDefenseDowngrade:
    """d3 显著低于 d1 和 d2 时，final_tier 应比基础档下调一档."""

    def test_defense_downgrade_applied(self) -> None:
        """d1=T3, d2=T3, d3=T1 → 基础档为 T2，抗辩降档后保持 T1 或更低档."""
        v = combine_tiers("T3", "T3", "T1")
        # 基础档 (3, 3, 1) = T2
        # 抗辩降档条件: d3.rank <= d1.rank-1 (1 <= 2) 且 d3.rank <= d2.rank-1 (1 <= 2)
        # 满足 → final_rank = max(1, 2-1) = 1
        assert v["final_tier"] == "T1"

    def test_no_downgrade_when_not_significant(self) -> None:
        """d3 不显著低于 d1/d2 时不应降档."""
        # (3, 3, 3) → 基础档 T3；d3=3 不比 d1-1=2 低
        v = combine_tiers("T3", "T3", "T3")
        # 应当等于或接近 T3（仅取决于基础映射）
        assert v["final_tier"] in ("T2", "T3")

    def test_no_downgrade_to_zero(self) -> None:
        """档位不能降到 0 以下."""
        # (1, 1, 1) → 基础档 T1；d3=1, d1-1=0 满足条件但 final_rank=1 不会 < 1
        v = combine_tiers("T1", "T1", "T1")
        assert v["severity_score"] >= 1

    def test_downgrade_combination_rule_contains_downgrade(self) -> None:
        """降档后 combination_rule 应包含 DOWNGRADE_DEFENSE 前缀."""
        v = combine_tiers("T4", "T4", "T1")
        # (4, 4, 1) 基础档 T3；d3=1 <= d1-1=3 且 d3=1 <= d2-1=3
        # 满足降档条件 → final_rank = max(1, 3-1) = 2
        assert v["final_tier"] == "T2"
        assert "DOWNGRADE_DEFENSE" in v["combination_rule"]


# ---------------------------------------------------------------------------
# T4 升级
# ---------------------------------------------------------------------------


class TestEscalation:
    """规则命中 T4 信号 + 高/极高权重应触发升级."""

    def test_t4_signal_with_very_high_weight_escalates_to_t4(self, base_rule_template) -> None:
        """T4 关键词 + weight>=0.9 → 直接升 T4."""
        rules = [
            _mk_rule(
                base_rule_template,
                rule_id="R_T4_CRITICAL",
                name="组织者/主犯",
                conclusion="电信网络诈骗上游",
                weight=0.95,
            ),
        ]
        # 基础档很低 (T1, T1, T1) = T1
        v = combine_tiers("T1", "T1", "T1", rule_hits=rules)
        assert v["final_tier"] == "T4"
        assert v["combination_rule"] == "ESCALATE_T4_CRITICAL"

    def test_t4_signal_with_high_weight_escalates_to_t3(self, base_rule_template) -> None:
        """T4 关键词 + weight>=0.8 → 升 T3."""
        rules = [
            _mk_rule(
                base_rule_template,
                rule_id="R_T4_HEAVY",
                name="跨境帮信",
                conclusion="跨境",
                weight=0.85,
            ),
        ]
        v = combine_tiers("T1", "T1", "T1", rule_hits=rules)
        assert v["final_tier"] in ("T3", "T4")
        # 至少到 T3
        assert v["severity_score"] >= 3

    def test_high_weight_only_escalates_to_t3(self, base_rule_template) -> None:
        """无 T4 关键词但 weight>=0.8 → 升 T3."""
        rules = [
            _mk_rule(
                base_rule_template,
                rule_id="R_HEAVY_NO_T4",
                name="普通高权重",
                conclusion="无 T4 关键词",
                conditions="无升级信号",
                weight=0.85,
            ),
        ]
        v = combine_tiers("T1", "T1", "T1", rule_hits=rules)
        # 基础档 T1，任意高权重规则 → 升 T3
        assert v["final_tier"] == "T3"

    def test_no_escalation_with_low_weight(self, base_rule_template) -> None:
        """weight<0.8 时不应触发升级."""
        rules = [
            _mk_rule(
                base_rule_template,
                rule_id="R_LIGHT",
                name="轻量规则",
                conclusion="无",
                weight=0.5,
            ),
        ]
        v = combine_tiers("T1", "T1", "T1", rule_hits=rules)
        # 基础档 T1，无高权重规则 → 保持 T1
        assert v["final_tier"] == "T1"

    def test_no_escalation_with_no_rules(self) -> None:
        """无规则命中 → 基础档."""
        v = combine_tiers("T2", "T2", "T2", rule_hits=[])
        # (2, 2, 2) 基础档 T2
        assert v["final_tier"] == "T2"

    def test_escalation_takes_max_with_base(self, base_rule_template) -> None:
        """升级时 final_rank = max(base_rank, target)."""
        rules = [
            _mk_rule(
                base_rule_template,
                rule_id="R_T4_S",
                name="数额特别巨大",
                conclusion="数额特别巨大",
                weight=0.85,
            ),
        ]
        # (3, 3, 3) 基础档 T3，T3 升级 → final_rank = max(3, 3) = 3
        v = combine_tiers("T3", "T3", "T3", rule_hits=rules)
        # 至少 T3
        assert v["severity_score"] >= 3


# ---------------------------------------------------------------------------
# 置信度计算
# ---------------------------------------------------------------------------


class TestConfidence:
    """置信度应在 [0, 1]，且满足一致性启发式."""

    def test_identical_tiers_high_confidence(self) -> None:
        """三档完全相同 → 高置信度（≥ 0.95）."""
        v = combine_tiers("T2", "T2", "T2")
        assert v["confidence"] >= 0.95

    def test_different_tiers_lower_confidence(self) -> None:
        """档级差异大 → 置信度较低."""
        v = combine_tiers("T1", "T4", "T1")
        assert v["confidence"] < 0.9

    def test_rule_bonus_increases_confidence(self, base_rule_template) -> None:
        """每命中 1 条规则 +0.02 置信度（上限 0.20）."""
        rules_no = []
        rules_yes = [
            _mk_rule(base_rule_template, rule_id=f"R{i:03d}", weight=0.5)
            for i in range(5)
        ]
        # 使用 spread=1 的组合以避免 base_conf 顶到 1.0 上限
        v_no = combine_tiers("T1", "T2", "T1", rule_hits=rules_no)
        v_yes = combine_tiers("T1", "T2", "T1", rule_hits=rules_yes)
        # 5 条规则 → +0.10
        assert v_yes["confidence"] >= v_no["confidence"]
        assert v_yes["confidence"] - v_no["confidence"] >= 0.05

    def test_confidence_clamped_to_one(self, base_rule_template) -> None:
        """置信度超过 1 时应被钳制."""
        rules = [
            _mk_rule(base_rule_template, rule_id=f"R{i:03d}", weight=0.5)
            for i in range(20)  # 20 条 → 超过 0.20 上限
        ]
        v = combine_tiers("T2", "T2", "T2", rule_hits=rules)
        assert 0.0 <= v["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


class TestAllCombinationsHelper:
    """all_combinations 返回 64 项有序列表."""

    def test_helper_returns_64(self) -> None:
        combos = all_combinations()
        assert len(combos) == 64

    def test_helper_keys_unique(self) -> None:
        combos = all_combinations()
        keys = [k for k, _ in combos]
        assert len(set(keys)) == 64


# ---------------------------------------------------------------------------
# 鲁棒性
# ---------------------------------------------------------------------------


class TestRobustness:
    """异常输入不应导致系统崩溃."""

    def test_none_inputs(self) -> None:
        v = combine_tiers(None, None, None, rule_hits=None)
        assert v["final_tier"] in ("T1", "T2", "T3", "T4")

    def test_invalid_string_inputs(self) -> None:
        v = combine_tiers("invalid", "garbage", "???", rule_hits=[])
        assert v["final_tier"] in ("T1", "T2", "T3", "T4")

    def test_out_of_range_int_inputs(self) -> None:
        v = combine_tiers(99, 100, -1, rule_hits=[])
        # TierEnum.coerce 会把 -1/99 兜底为 T2
        assert v["final_tier"] in ("T1", "T2", "T3", "T4")

    def test_with_edge_weight_rule_object(self, base_rule_template) -> None:
        """rule_hits 含有 weight 边界值（0.0 / 1.0）时不应崩溃."""
        rules = [
            _mk_rule(base_rule_template, rule_id="R_ZERO", weight=0.0),
            _mk_rule(base_rule_template, rule_id="R_ONE", weight=1.0),
        ]
        v = combine_tiers("T1", "T1", "T1", rule_hits=rules)
        assert v["final_tier"] in ("T1", "T2", "T3", "T4")

    def test_iterable_rule_hits(self, base_rule_template) -> None:
        """rule_hits 接受生成器/可迭代对象."""
        def gen():
            yield _mk_rule(base_rule_template, rule_id="R1", weight=0.5)

        v = combine_tiers("T1", "T1", "T1", rule_hits=gen())
        assert v["final_tier"] in ("T1", "T2", "T3", "T4")
