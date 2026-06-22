"""冲突检测器与证据强度分层器.

冲突检测
--------
负责在案件分析结果中检测以下 6 类冲突：

- C001 规则冲突
- C002 标签互斥冲突
- C003 维度间结论矛盾
- C004 证据不足
- C005 超量刑范围
- C006 适用法律版本冲突

证据强度分层
------------
根据 V1.2 法律引擎升级说明第二节第4条要求，将证据拆分为4个层级：
1. DIRECT_COGNITION（直接认知性证据）
2. OBJECTIVE_ANOMALY（客观异常事实）
3. COGNITION_ENHANCER（认知增强因素）
4. DEFENSE_VERIFICATION（辩解检验材料）

边界提醒
--------
检测案件是否超出帮信罪评价范围（原 boundary_reminder.py）。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from app.services.rule_engine import (
    ConflictCheck,
    Rule,
    Tag,
    load_conflicts,
    load_tags,
)
from app.services.tag_extractor import TagMatch
from app.types.evidence_layer import BoundaryAlert


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 严重程度
_SEVERITY_LOW: str = "low"
_SEVERITY_MEDIUM: str = "medium"
_SEVERITY_HIGH: str = "high"
_SEVERITY_CRITICAL: str = "critical"

# 标签互斥 ID 集合（与 data/tags/v1.0.json 的 mutually_exclusive_with 对应）
_OBJECTIVE_BEHAVIOR_TAGS: frozenset[str] = frozenset({"F001", "F002", "F009", "F010"})

# 量刑档位关键词，用于 C005
_TIER_KEYWORDS_PATTERN: re.Pattern[str] = re.compile(
    r"(一档|二档|三档|情节较轻|情节严重|情节特别严重|三年以下|三年以上|七年以下)",
)

# 法律版本标识
_LAW_VERSION_2019: str = "2019"
_LAW_VERSION_2025: str = "2025"

# C004 关键证据关键词
_CRITICAL_EVIDENCE_KEYWORDS: tuple[str, ...] = (
    "审计报告", "银行流水", "资金流水", "转账记录",
    "被害人陈述", "审计", "电子数据",
)

# C004 证据不足的最小关键词匹配数
_MIN_EVIDENCE_KEYWORD_HITS: int = 2

# 维度1（构成要件）、维度2（情节）、维度3（量刑参考）的默认名称
_DIM_CONSTITUTIVE: str = "dimension1"
_DIM_CIRCUMSTANCE: str = "dimension2"
_DIM_SENTENCING: str = "dimension3"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Conflict:
    """单条冲突检测结果.

    Attributes:
        check_id: 冲突 ID.
        name: 冲突名称.
        severity: 严重程度.
        involved: 涉及的规则/标签/维度 ID 列表.
        description: 冲突描述.
        resolution_strategy: 解决建议.
        raw_payload: 原始触发证据，便于审计.
    """

    check_id: str
    name: str
    severity: str
    involved: list[str]
    description: str
    resolution_strategy: str
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化字典."""
        return {"check_id": self.check_id,
            "name": self.name,
            "severity": self.severity,
            "involved": list(self.involved),
            "description": self.description,
            "resolution_strategy": self.resolution_strategy,
            "raw_payload": self.raw_payload,
        }


# ---------------------------------------------------------------------------
# 检测器
# ---------------------------------------------------------------------------


class ConflictDetector:
    """帮信罪案件冲突检测器.

    复用 :func:`app.services.rule_engine.load_conflicts` 提供的元规则。
    """

    def __init__(self, checks: Sequence[ConflictCheck] | None = None) -> None:
        self._checks: list[ConflictCheck] = (
            list(checks) if checks is not None else list(load_conflicts())
        )
        self._tag_index: dict[str, Tag] = {t.tag_id: t for t in load_tags()}

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def detect_conflicts(
        self,
        tags: Sequence[TagMatch],
        rule_hits: Sequence[Rule],
        dimension_results: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> list[Conflict]:
        """运行所有冲突检查.

        Args:
            tags: 标签抽取结果.
            rule_hits: 命中的规则.
            dimension_results: 多维度分析结果，键为 ``dimension1/2/3``.

        Returns:
            :class:`Conflict` 列表.
        """
        results: list[Conflict] = []
        for check in self._checks:
            try:
                if check.check_id == "C001":
                    conflict = self._check_rule_conflict(rule_hits)
                elif check.check_id == "C002":
                    conflict = self._check_tag_mutex(tags)
                elif check.check_id == "C003":
                    conflict = self._check_dimension_contradiction(dimension_results)
                elif check.check_id == "C004":
                    conflict = self._check_evidence_shortage(tags, rule_hits, dimension_results)
                elif check.check_id == "C005":
                    conflict = self._check_sentence_out_of_range(dimension_results)
                elif check.check_id == "C006":
                    conflict = self._check_law_version_conflict(rule_hits)
                else:
                    logger.warning(f"未知的冲突检查 ID: {check.check_id}")
                    continue
            except Exception:  # noqa: BLE001
                logger.exception(f"冲突检测失败: {check.check_id}")
                continue
            if conflict is not None:
                results.append(conflict)
        return results

    # ------------------------------------------------------------------
    # C001 规则冲突
    # ------------------------------------------------------------------

    def _check_rule_conflict(self, rule_hits: Sequence[Rule]) -> Conflict | None:
        rule_ids = {r.rule_id for r in rule_hits}
        conflicting: list[str] = []
        for r in rule_hits:
            for other in r.conflicting_rules:
                if other in rule_ids:
                    pair = tuple(sorted({r.rule_id, other}))
                    if pair not in conflicting:
                        conflicting.append(pair)
        if not conflicting:
            return None
        check = self._get_check("C001")
        return Conflict(
            check_id=check.check_id,
            name=check.name,
            severity=_SEVERITY_HIGH,
            involved=conflicting,
            description=check.description,
            resolution_strategy=check.resolution_strategy,
            raw_payload={"conflicting_pairs": conflicting},
        )

    # ------------------------------------------------------------------
    # C002 标签互斥冲突
    # ------------------------------------------------------------------

    def _check_tag_mutex(self, tags: Sequence[TagMatch]) -> Conflict | None:
        tag_ids = {t.tag_id for t in tags}
        violations: list[tuple[str, str]] = []
        for tag in tags:
            meta = self._tag_index.get(tag.tag_id)
            if not meta:
                continue
            for other in meta.mutually_exclusive_with:
                if other in tag_ids:
                    pair = tuple(sorted({tag.tag_id, other}))
                    if pair not in violations:
                        violations.append(pair)
        if not violations:
            return None
        check = self._get_check("C002")
        return Conflict(
            check_id=check.check_id,
            name=check.name,
            severity=_SEVERITY_MEDIUM,
            involved=[tid for pair in violations for tid in pair],
            description=check.description,
            resolution_strategy=check.resolution_strategy,
            raw_payload={"mutex_pairs": [list(p) for p in violations]},
        )

    # ------------------------------------------------------------------
    # C003 维度间结论矛盾
    # ------------------------------------------------------------------

    def _check_dimension_contradiction(
        self,
        dimension_results: Mapping[str, Mapping[str, Any]] | None,
    ) -> Conflict | None:
        if not dimension_results:
            return None
        constitutive = dimension_results.get(_DIM_CONSTITUTIVE) or {}
        circumstance = dimension_results.get(_DIM_CIRCUMSTANCE) or {}
        constitutive_text = _safe_text(constitutive.get("reasoning", ""))
        circumstance_text = _safe_text(circumstance.get("reasoning", ""))

        # 情形 1: 文本层面互相矛盾
        constitutive_text_hit = "情节严重" in constitutive_text
        circumstance_text_hit = (
            "情节较轻" in circumstance_text
            or "情节显著轻微" in circumstance_text
            or "情节轻微" in circumstance_text
        )
        text_contradiction = constitutive_text_hit and circumstance_text_hit

        # 情形 2: 分数层面互相矛盾
        # 构成要件维度分高、情节维度文字明确说"较轻/轻微"
        try:
            constitutive_score = float(constitutive.get("score", 0))
        except (TypeError, ValueError):
            constitutive_score = 0.0
        score_contradiction = (
            constitutive_score >= 7.0 and circumstance_text_hit
        )
        if not (text_contradiction or score_contradiction):
            return None
        check = self._get_check("C003")
        return Conflict(
            check_id=check.check_id,
            name=check.name,
            severity=_SEVERITY_HIGH,
            involved=[_DIM_CONSTITUTIVE, _DIM_CIRCUMSTANCE],
            description=check.description,
            resolution_strategy=check.resolution_strategy,
            raw_payload={"constitutive_reasoning": constitutive_text,
                "constitutive_score": constitutive_score,
                "circumstance_reasoning": circumstance_text,
                "trigger": (
                    "text" if text_contradiction else "score"),
            },
        )

    # ------------------------------------------------------------------
    # C004 证据不足
    # ------------------------------------------------------------------

    def _check_evidence_shortage(
        self,
        tags: Sequence[TagMatch],
        rule_hits: Sequence[Rule],
        dimension_results: Mapping[str, Mapping[str, Any]] | None,
    ) -> Conflict | None:
        if not rule_hits:
            return None
        heavy_rules = [r for r in rule_hits if r.weight >= 0.8]
        if not heavy_rules:
            return None

        evidence_text_parts: list[str] = []
        if dimension_results:
            for v in dimension_results.values():
                if isinstance(v, Mapping):
                    evidence_text_parts.append(_safe_text(v.get("reasoning", "")))
        evidence_text_parts.extend(t.matched_text for t in tags)
        evidence_text = "\n".join(evidence_text_parts)

        hit = sum(1 for kw in _CRITICAL_EVIDENCE_KEYWORDS if kw in evidence_text)
        if hit >= _MIN_EVIDENCE_KEYWORD_HITS:
            return None
        check = self._get_check("C004")
        return Conflict(
            check_id=check.check_id,
            name=check.name,
            severity=_SEVERITY_MEDIUM,
            involved=[r.rule_id for r in heavy_rules],
            description=check.description,
            resolution_strategy=check.resolution_strategy,
            raw_payload={
                "evidence_hits": hit,
                "missing_evidence": [
                    kw for kw in _CRITICAL_EVIDENCE_KEYWORDS if kw not in evidence_text
                ],
            },
        )

    # ------------------------------------------------------------------
    # C005 超量刑范围
    # ------------------------------------------------------------------

    def _check_sentence_out_of_range(
        self,
        dimension_results: Mapping[str, Mapping[str, Any]] | None,
    ) -> Conflict | None:
        if not dimension_results:
            return None
        sentencing = dimension_results.get(_DIM_SENTENCING) or {}
        circumstance = dimension_results.get(_DIM_CIRCUMSTANCE) or {}
        sent_text = _safe_text(sentencing.get("reasoning", ""))
        circum_text = _safe_text(circumstance.get("reasoning", ""))
        sent_tier = _match_highest_tier(sent_text)
        circum_tier = _match_highest_tier(circum_text)
        if sent_tier is None or circum_tier is None:
            return None
        if sent_tier <= circum_tier:
            return None
        check = self._get_check("C005")
        return Conflict(
            check_id=check.check_id,
            name=check.name,
            severity=_SEVERITY_HIGH,
            involved=[_DIM_SENTENCING, _DIM_CIRCUMSTANCE],
            description=check.description,
            resolution_strategy=check.resolution_strategy,
            raw_payload={
                "sentencing_tier": sent_tier,
                "circumstance_tier": circum_tier,
            },
        )

    # ------------------------------------------------------------------
    # C006 适用法律版本冲突
    # ------------------------------------------------------------------

    def _check_law_version_conflict(self, rule_hits: Sequence[Rule]) -> Conflict | None:
        versions: set[str] = set()
        for r in rule_hits:
            if _LAW_VERSION_2025 in r.source_law:
                versions.add(_LAW_VERSION_2025)
            if _LAW_VERSION_2019 in r.source_law:
                versions.add(_LAW_VERSION_2019)
        if len(versions) < 2:
            return None
        check = self._get_check("C006")
        return Conflict(
            check_id=check.check_id,
            name=check.name,
            severity=_SEVERITY_CRITICAL,
            involved=sorted(versions),
            description=check.description,
            resolution_strategy=check.resolution_strategy,
            raw_payload={"versions": sorted(versions)},
        )

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def _get_check(self, check_id: str) -> ConflictCheck:
        for c in self._checks:
            if c.check_id == check_id:
                return c
        # 兜底：返回占位符对象，避免 None 引发 AttributeError
        return ConflictCheck(
            check_id=check_id,
            name="未注册",
            rule_a="",
            rule_b="",
            description="",
            resolution_strategy="",
        )


# ---------------------------------------------------------------------------
# 模块级便捷函数
# ---------------------------------------------------------------------------


def detect_conflicts(
    tags: Sequence[TagMatch],
    rule_hits: Sequence[Rule],
    dimension_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[Conflict]:
    """便捷函数：执行 6 类冲突检查.

    Args:
        tags: 标签抽取结果.
        rule_hits: 命中的规则.
        dimension_results: 多维度分析结果.

    Returns:
        :class:`Conflict` 列表.
    """
    detector = ConflictDetector()
    return detector.detect_conflicts(tags, rule_hits, dimension_results)


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _safe_text(value: Any) -> str:
    """将任意输入安全地转为字符串."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _match_highest_tier(text: str) -> int | None:
    """从文本中匹配最高档位（数字越大档位越高）.

    Returns:
        1（情节较轻/一档）、2（情节严重/二档）、3（情节特别严重/三档），
        文本中无任何档位关键词则返回 ``None``。
    """
    if not text:
        return None
    highest: int | None = None
    for match in _TIER_KEYWORDS_PATTERN.finditer(text):
        keyword = match.group(1)
        if keyword in ("一档", "情节较轻", "三年以下"):
            tier = 1
        elif keyword in ("二档", "情节严重"):
            tier = 2
        elif keyword in ("三档", "情节特别严重", "三年以上", "七年以下"):
            tier = 3
        else:
            continue
        if highest is None or tier > highest:
            highest = tier
    return highest


# ===========================================================================
# 证据强度分层功能 (原 evidence_strength_layer.py)
# ===========================================================================


# ---------------------------------------------------------------------------
# 证据层级枚举
# ---------------------------------------------------------------------------


class EvidenceLayer(str, Enum):
    """证据强度4层分级.

    层级定义基于 V1.2 法律引擎升级说明第二节第4条。
    """
    DIRECT_COGNITION = "direct_cognition"  # 直接认知性证据
    OBJECTIVE_ANOMALY = "objective_anomaly"  # 客观异常事实
    COGNITION_ENHANCER = "cognition_enhancer"  # 认知增强因素
    DEFENSE_VERIFICATION = "defense_verification"  # 辩解检验材料


# ---------------------------------------------------------------------------
# 标签到证据层级的映射
# ---------------------------------------------------------------------------

# 标签ID到证据层级的映射关系
# 基于 tag_extractor.py 中的标签定义，将标签分类到4个证据层级
_TAG_TO_LAYER_MAP: dict[str, EvidenceLayer] = {
    # 直接认知性证据（自述明知）
    "F003": EvidenceLayer.DIRECT_COGNITION,  # 自述知道是洗黑钱
    "F004": EvidenceLayer.DIRECT_COGNITION,  # 承认知道资金异常
    "F005": EvidenceLayer.DIRECT_COGNITION,  # 明知他人从事违法活动

    # 客观异常事实
    "F001": EvidenceLayer.OBJECTIVE_ANOMALY,  # 跨省取款
    "F002": EvidenceLayer.OBJECTIVE_ANOMALY,  # 夜间大额交易
    "F009": EvidenceLayer.OBJECTIVE_ANOMALY,  # 虚拟币折现
    "F010": EvidenceLayer.OBJECTIVE_ANOMALY,  # 频繁转账

    # 认知增强因素
    "F006": EvidenceLayer.COGNITION_ENHANCER,  # 异常报酬比例
    "F007": EvidenceLayer.COGNITION_ENHANCER,  # 规避监管行为
    "F008": EvidenceLayer.COGNITION_ENHANCER,  # 规避身份验证

    # 辩解检验材料
    "F011": EvidenceLayer.DEFENSE_VERIFICATION,  # 辩解与客观事实冲突
    "F012": EvidenceLayer.DEFENSE_VERIFICATION,  # 辩解无法验证
}


# ---------------------------------------------------------------------------
# 证据层级数据结构
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LayerEvidence:
    """单个证据层级的评估结果.

    Attributes:
        layer: 证据层级.
        evidences: 该层级的证据列表（TagMatch对象）.
        strength_score: 强度评分（0-10分，仅用于内部计算）.
    """

    layer: EvidenceLayer
    evidences: list[TagMatch] = field(default_factory=list)
    strength_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典."""
        return {"layer": self.layer.value,
            "layer_name": self._get_layer_name(),
            "evidence_count": len(self.evidences),
            "strength_score": round(self.strength_score, 2),
            "evidences": [e.to_dict() for e in self.evidences],
        }

    def _get_layer_name(self) -> str:
        """获取层级的中文名称."""
        names = {
            EvidenceLayer.DIRECT_COGNITION: "直接认知性证据",
            EvidenceLayer.OBJECTIVE_ANOMALY: "客观异常事实",
            EvidenceLayer.COGNITION_ENHANCER: "认知增强因素",
            EvidenceLayer.DEFENSE_VERIFICATION: "辩解检验材料",
        }
        return names.get(self.layer, "未知层级")


@dataclass(slots=True)
class EvidenceLayerReport:
    """证据层级评估报告.

    Attributes:
        layer_results: 4个层级的评估结果.
        cognition_tier: 认知匹配度档级（1-3档，1为最高）.
        has_direct_cognition: 是否存在直接认知性证据.
        has_objective_anomaly: 是否存在客观异常事实.
        downgrade_applied: 是否应用了降档防护.
    """

    layer_results: dict[EvidenceLayer, LayerEvidence] = field(default_factory=dict)
    cognition_tier: int = 3  # 默认最低档
    has_direct_cognition: bool = False
    has_objective_anomaly: bool = False
    downgrade_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典."""
        return {"layers": {
                layer.value: result.to_dict()
                for layer, result in self.layer_results.items()
            },
            "cognition_tier": self.cognition_tier,
            "has_direct_cognition": self.has_direct_cognition,
            "has_objective_anomaly": self.has_objective_anomaly,
            "downgrade_applied": self.downgrade_applied,
        }


# ---------------------------------------------------------------------------
# 证据强度分级器
# ---------------------------------------------------------------------------


class EvidenceStrengthLayer:
    """证据强度4层分级器.

    实现证据分层评估与防护逻辑。
    """

    def __init__(self) -> None:
        """初始化分级器."""
        self._tag_to_layer = _TAG_TO_LAYER_MAP

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def layer_evidences(self, tags: Sequence[TagMatch]) -> EvidenceLayerReport:
        """为每个层级生成独立证据列表并计算强度评分.

        Args:
            tags: 标签抽取结果（来自 TagExtractor）.

        Returns:
            EvidenceLayerReport: 包含4个层级评估结果的报告.
        """
        # 初始化4个层级
        layer_results: dict[EvidenceLayer, LayerEvidence] = {
            layer: LayerEvidence(layer=layer) for layer in EvidenceLayer
        }

        # 将标签分类到对应层级
        for tag_match in tags:
            layer = self._tag_to_layer.get(tag_match.tag_id)
            if layer is not None:
                layer_results[layer].evidences.append(tag_match)

        # 计算每个层级的强度评分
        for layer_evidence in layer_results.values():
            layer_evidence.strength_score = self._calculate_layer_score(
                layer_evidence.evidences,
                layer_evidence.layer,
            )

        # 判断是否存在直接认知和客观异常
        has_direct = len(layer_results[EvidenceLayer.DIRECT_COGNITION].evidences) > 0
        has_objective = len(layer_results[EvidenceLayer.OBJECTIVE_ANOMALY].evidences) > 0

        # 计算初始认知档级
        cognition_tier = self._calculate_cognition_tier(layer_results)

        # 应用防护逻辑
        downgrade_applied = False
        if has_objective and not has_direct:
            # 仅有客观异常而无直接认知时，降一档
            cognition_tier = min(cognition_tier + 1, 3)
            downgrade_applied = True
            logger.info("应用降档防护：仅有客观异常而无直接认知，认知档级降为第{}档",
                cognition_tier,
            )
        return EvidenceLayerReport(
            layer_results=layer_results,
            cognition_tier=cognition_tier,
            has_direct_cognition=has_direct,
            has_objective_anomaly=has_objective,
            downgrade_applied=downgrade_applied,
        )

    def guard_against_single_layer_override(self,
        report: EvidenceLayerReport,
    ) -> EvidenceLayerReport:
        """防护逻辑：防止单一客观事实替代主观明知证明.

        当仅有OBJECTIVE_ANOMALY而无DIRECT_COGNITION时，
        必须将认知匹配度档级降低一档。

        Args:
            report: 初始评估报告.

        Returns:
            应用防护逻辑后的报告（若需要降档则修改 cognition_tier 和 downgrade_applied）.
        """
        if report.has_objective_anomaly and not report.has_direct_cognition:
            # 已经应用过降档则不重复处理
            if not report.downgrade_applied:
                report.cognition_tier = min(report.cognition_tier + 1, 3)
                report.downgrade_applied = True
                logger.info("防护逻辑触发：认知档级降为第{}档",
                    report.cognition_tier,
                )
        return report

    # ------------------------------------------------------------------
    # 内部：计算层级强度评分
    # ------------------------------------------------------------------

    def _calculate_layer_score(self,
        evidences: list[TagMatch],
        layer: EvidenceLayer,
    ) -> float:
        """计算单个层级的强度评分（0-10分）.

        评分规则：
        - 基础分：每个证据贡献其 confidence * 10
        - 层级权重：不同层级的权重不同
        - 最终分数限制在 0-10 范围内

        Args:
            evidences: 该层级的证据列表.
            layer: 证据层级.

        Returns:
            强度评分（0-10分）.
        """
        if not evidences:
            return 0.0

        # 层级权重
        layer_weights = {
            EvidenceLayer.DIRECT_COGNITION: 1.0,  # 直接认知权重最高
            EvidenceLayer.OBJECTIVE_ANOMALY: 0.8,  # 客观异常次之
            EvidenceLayer.COGNITION_ENHANCER: 0.7,  # 认知增强再次之
            EvidenceLayer.DEFENSE_VERIFICATION: 0.6,  # 辩解检验最低
        }
        weight = layer_weights.get(layer, 0.5)

        # 计算基础分：所有证据的 confidence 之和 * 权重
        base_score = sum(e.confidence for e in evidences) * 10 * weight

        # 限制在 0-10 范围内
        return min(max(base_score, 0.0), 10.0)

    # ------------------------------------------------------------------
    # 内部：计算认知档级
    # ------------------------------------------------------------------

    def _calculate_cognition_tier(self,
        layer_results: dict[EvidenceLayer, LayerEvidence],
    ) -> int:
        """计算认知档级（1-3档，1为最高）.

        档级判定规则：
        - 第1档（最高）：DIRECT_COGNITION 评分 >= 6 且 OBJECTIVE_ANOMALY 评分 >= 5
        - 第2档（中等）：DIRECT_COGNITION 评分 >= 4 或 OBJECTIVE_ANOMALY 评分 >= 6
        - 第3档（最低）：其他情况

        Args:
            layer_results: 4个层级的评估结果.

        Returns:
            认知档级（1-3）.
        """
        direct_score = layer_results[EvidenceLayer.DIRECT_COGNITION].strength_score
        objective_score = layer_results[EvidenceLayer.OBJECTIVE_ANOMALY].strength_score
        enhancer_score = layer_results[EvidenceLayer.COGNITION_ENHANCER].strength_score

        # 第1档：直接认知强且客观异常强
        if direct_score >= 6.0 and objective_score >= 5.0:
            return 1

        # 第2档：直接认知中等或客观异常强
        if direct_score >= 4.0 or objective_score >= 6.0 or enhancer_score >= 5.0:
            return 2

        # 第3档：其他情况
        return 3


# ---------------------------------------------------------------------------
# 证据分层便捷函数
# ---------------------------------------------------------------------------


def analyze_evidence_layers(tags: Sequence[TagMatch]) -> EvidenceLayerReport:
    """便捷函数：分析证据层级并生成报告.

    Args:
        tags: 标签抽取结果.

    Returns:
        EvidenceLayerReport: 证据层级评估报告.
    """
    analyzer = EvidenceStrengthLayer()
    return analyzer.layer_evidences(tags)


def apply_single_layer_guard(report: EvidenceLayerReport) -> EvidenceLayerReport:
    """便捷函数：应用单一层级防护逻辑.

    Args:
        report: 初始评估报告.

    Returns:
        应用防护逻辑后的报告.
    """
    analyzer = EvidenceStrengthLayer()
    return analyzer.guard_against_single_layer_override(report)


# ---------------------------------------------------------------------------
# 边界提醒功能 (原 boundary_reminder.py)
# ---------------------------------------------------------------------------

# 边界提醒规则
_BOUNDARY_RULES = [
    {
        "keywords": ["明确知道系诈骗钱款", "事先知道诈骗"],
        "alert_type": "超出帮信罪范围",
        "description": "案件事实显示被告人明确知道系诈骗钱款，可能构成诈骗罪共同犯罪",
        "severity": "high",
    },
    {
        "keywords": ["长期取现分工", "上线安排"],
        "alert_type": "分工合作特征",
        "description": "案件事实显示存在长期取现分工或上线安排，可能构成诈骗罪共同犯罪",
        "severity": "high",
    },
    {
        "keywords": ["每日验卡", "防止冻结"],
        "alert_type": "规避监管行为",
        "description": "案件事实显示存在每日验卡、防止冻结等规避监管行为，可能构成掩饰隐瞒犯罪所得",
        "severity": "medium",
    },
    {
        "keywords": ["分开装袋", "掩饰隐瞒"],
        "alert_type": "掩饰隐瞒行为",
        "description": "案件事实显示存在分开装袋等掩饰隐瞒行为，可能构成掩饰隐瞒犯罪所得罪",
        "severity": "high",
    },
]


def check_boundary_alerts(case_text: str) -> list[BoundaryAlert]:
    """检查案件是否超出帮信罪评价范围.

    当出现以下事实时触发提醒：
    - 明确知道系诈骗钱款
    - 长期取现分工
    - 上线安排
    - 每日验卡、防止冻结
    - 分开装袋等掩饰隐瞒行为

    Args:
        case_text: 案件事实文本

    Returns:
        list[BoundaryAlert]: 边界提醒列表
    """
    logger.info("开始边界提醒检查 (B4)")
    alerts = []
    for rule in _BOUNDARY_RULES:
        for keyword in rule["keywords"]:
            if keyword in case_text:
                alert = BoundaryAlert(
                    alert_type=rule["alert_type"],
                    description=rule["description"],
                    severity=rule["severity"],
                )
                alerts.append(alert)
                logger.warning(f"触发边界提醒: {alert.alert_type} - {keyword}")
                break  # 每个规则只触发一次
    if not alerts:
        logger.info("未触发边界提醒")
    return alerts


# ---------------------------------------------------------------------------
# 导出符号
# ---------------------------------------------------------------------------

__all__ = [
    # 冲突检测
    "Conflict",
    "ConflictDetector",
    "detect_conflicts",
    # 证据分层
    "EvidenceLayer",
    "LayerEvidence",
    "EvidenceLayerReport",
    "EvidenceStrengthLayer",
    "analyze_evidence_layers",
    "apply_single_layer_guard",
    # 边界提醒
    "BoundaryAlert",
    "check_boundary_alerts",
]
