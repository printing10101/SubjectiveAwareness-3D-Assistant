"""证据强度4层分级器.

根据 V1.2 法律引擎升级说明第二节第4条要求，将证据拆分为4个层级：
1. DIRECT_COGNITION（直接认知性证据）：自述"知道是洗黑钱"等
2. OBJECTIVE_ANOMALY（客观异常事实）：跨省取款、夜间大额、虚拟币折现等
3. COGNITION_ENHANCER（认知增强因素）：异常报酬比例、规避监管行为等
4. DEFENSE_VERIFICATION（辩解检验材料）：与客观事实是否冲突

核心功能：
- 为每个层级生成独立证据列表，计算0-10分的强度评分（仅用于内部计算）
- 实现防护逻辑：当仅有OBJECTIVE_ANOMALY而无DIRECT_COGNITION时，必须将认知匹配度档级降低一档
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: from collections.abc
from collections.abc import Sequence
# 导入模块: from dataclasses
from dataclasses import dataclass, field
# 导入模块: from enum
from enum import Enum
# 导入模块: from typing
from typing import Any

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.services.tag_extractor
from app.services.tag_extractor import TagMatch


# ---------------------------------------------------------------------------
# 证据层级枚举
# ---------------------------------------------------------------------------


# 定义 EvidenceLayer 类
class EvidenceLayer(str, Enum):
    """证据强度4层分级.

    层级定义基于 V1.2 法律引擎升级说明第二节第4条。
    """

    # 初始化变量 DIRECT_COGNITION
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
# 数据结构
# ---------------------------------------------------------------------------


# 应用装饰器: dataclass
@dataclass(slots=True)
# 定义 LayerEvidence 类
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
        # 返回处理结果
        return {
            "layer": self.layer.value,
            "layer_name": self._get_layer_name(),
            "evidence_count": len(self.evidences),
            "strength_score": round(self.strength_score, 2),
            "evidences": [e.to_dict() for e in self.evidences],
        }

    def _get_layer_name(self) -> str:
        """获取层级的中文名称."""
        # 初始化变量 names
        names = {
            EvidenceLayer.DIRECT_COGNITION: "直接认知性证据",
            EvidenceLayer.OBJECTIVE_ANOMALY: "客观异常事实",
            EvidenceLayer.COGNITION_ENHANCER: "认知增强因素",
            EvidenceLayer.DEFENSE_VERIFICATION: "辩解检验材料",
        }
        # 返回处理结果
        return names.get(self.layer, "未知层级")


# 应用装饰器: dataclass
@dataclass(slots=True)
# 定义 EvidenceLayerReport 类
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
        # 返回处理结果
        return {
            "layers": {
                layer.value: result.to_dict()
                # 循环遍历：处理业务逻辑
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


# 定义 EvidenceStrengthLayer 类
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
          # 循环遍历：处理业务逻辑
      }

        # 将标签分类到对应层级
        for tag_match in tags:
            # 初始化变量 layer
            layer = self._tag_to_layer.get(tag_match.tag_id)
            # 条件判断：处理业务逻辑
            if layer is not None:
                layer_results[layer]        # 循环遍历：处理业务逻辑
.evidences.append(tag_match)

        # 计算每个层级的强度评分
        for layer_evidence in layer_results.values():
            layer_evidence.strength_score = self._calculate_layer_score(
                layer_evidence.evidences,
                layer_evidence.layer,
            )

        # 判断是否存在直接认知和客观异常
        has_direct = len(layer_results[EvidenceLayer.DIRECT_COGNITION].evidences) > 0
        # 初始化变量 has_objective
        has_objective = len(layer_results[EvidenceLayer.OBJECTIVE_ANOMALY].evidences) > 0

        # 计算初始认知档级
        cognition_tier = self._calculate_cognition_tier(layer_results)

        # 应用防护逻辑
                # 条件判断：处理业务逻辑
downgrade_applied = False
        # 条件判断: 检查 has_objective and not has_direct
        if has_objective and not has_direct:
            # 仅有客观异常而无直接认知时，降一档
            cognition_tier = min(cognition_tier + 1, 3)
            # 初始化变量 downgrade_applied
            downgrade_applied = True
            # 记录日志信息
            logger.info(
                "应用降档防护：仅有客观异常而无直接认知，认知档级降为第{}档",
                cognition_tier,
            )

        # 返回处理结果
        return EvidenceLayerReport(
            # 初始化变量 layer_results
            layer_results=layer_results,
            # 初始化变量 cognition_tier
            cognition_tier=cognition_tier,
            # 初始化变量 has_direct_cognition
            has_direct_cognition=has_direct,
            # 初始化变量 has_objective_anomaly
            has_objective_anomaly=has_objective,
            # 初始化变量 downgrade_applied
            downgrade_applied=downgrade_applied,
        )

    def guard_against_single_layer_override(
        # 函数 guard_against_single_layer_override 的初始化逻辑
        self,
        report: EvidenceLayerReport,

        # 执行 guard_against_single_layer_override 函数的核心逻辑
    ) -> EvidenceLayerReport:
        """防护逻辑：防止单一客观事实替代主观明知证明.

        当仅有OBJECTIVE_ANOMALY而无DIRECT_COGNITION时，
        必须将认知匹配度档级降低一档。

        Args:
            report: 初始评估报告.

        Returns:
            应用防护逻辑后的报告（若需要降档则修改 c        # 条件判断：处理业务逻辑
ognition_tier 和 downgrade_applied）.
        """
        # 条件判断: 检查 report.has_objective_ano            # 条件
        if report.has_objective_ano            # 条件判断：处理业务逻辑
maly and not report.has_direct_cognition:
            # 已经应用过降档则不重复处理
            if not report.downgrade_applied:
                report.cognition_tier = min(report.cognition_tier + 1, 3)
                report.downgrade_applied = True
                # 记录日志信息
                logger.info(
                    "防护逻辑触发：认知档级降为第{}档",
                    report.cognition_tier,
                )
        # 返回处理结果
        return report

    # ------------------------------------------------------------------
    # 内部：计算层级强度评分
    # ------------------------------------------------------------------

    def _calculate_layer_score(
        # 函数 _calculate_layer_score 的初始化逻辑
        self,
        evidences: list[TagMatch],

        # 执行 _calculate_layer_score 函数的核心逻辑
        layer: EvidenceLayer,
    ) -> float:
        """计算单个层级的强度评分（0-10分）.

        评分规则：
        - 基础分：每个证据贡献其 confidence * 10
        - 层级权重：不同层级的权重不同
        - 最终分数限制在 0-10 范围内

        Args:
            evide        # 条件判断：处理业务逻辑
nces: 该层级的证据列表.
            layer: 证据层级.

        Returns:
            强度评分（0-10分）.
        """
        # 条件判断: 检查 not evidences
        if not evidences:
            # 返回处理结果
            return 0.0

        # 层级权重
        layer_weights = {
            EvidenceLayer.DIRECT_COGNITION: 1.0,  # 直接认知权重最高
            EvidenceLayer.OBJECTIVE_ANOMALY: 0.8,  # 客观异常次之
            EvidenceLayer.COGNITION_ENHANCER: 0.7,  # 认知增强再次之
            EvidenceLayer.DEFENSE_VERIFICATION: 0.6,  # 辩解检验最低
        }

        # 初始化变量 weight
        weight = layer_weights.get(layer, 0.5)

        # 计算基础分：所有证据的 confidence 之和 * 权重
        base_score = sum(e.confidence for e in evidences) * 10 * weight

        # 限制在 0-10 范围内
        return min(max(base_score, 0.0), 10.0)

    # ------------------------------------------------------------------
    # 内部：计算认知档级
    # ------------------------------------------------------------------

    def _calculate_cognition_tier(
        # 函数 _calculate_cognition_tier 的初始化逻辑
        self,
        layer_results: dict[EvidenceLayer, LayerEvidence],

        # 执行 _calculate_cognition_tier 函数的核心逻辑
    ) -> int:
        """计算认知匹配度档级（1-3档，1为最高）.

        档级判定规则：
        - 第1档（最高）：DIRECT_COGNITION 评分 >= 6 且 OBJECTIVE_ANOMALY 评分 >= 5
        - 第2档（中等）：DIRECT_COGNITION 评分 >= 4 或 OBJECTIVE_ANOMALY 评分 >= 6
        - 第3档（最低）：其他情况

        Args:
            layer_results: 4个层级的评估结果.

        Returns:
            认知档级（1-3）.
        """
        # 初始化变量 direct_score
        direct_score = layer_results[EvidenceLayer.DIRECT_COGNITION].strength_score
        # 初始化变量 objective_score
        objective_score = layer_results[EvidenceLayer.OBJECTIVE_ANOMALY].strength_sco        # 条件判断：处理业务逻辑
re
        # 初始化变量 enhancer_score
        enhancer_score = layer_results[EvidenceLayer.COGNITION_ENHANCER].strength_s        # 条件判断：处理业务逻辑
core

        # 第1档：直接认知强且客观异常强
        if direct_score >= 6.0 and objective_score >= 5.0:
            # 返回处理结果
            return 1

        # 第2档：直接认知中等或客观异常强
        if direct_score >= 4.0 or objective_score >= 6.0 or enhancer_score >= 5.0:
            # 返回处理结果
            return 2

        # 第3档：其他情况
        return 3


# ---------------------------------------------------------------------------
# 模块级便捷函数
# ---------------------------------------------------------------------------


def analyze_evidence_layers(tags: Sequence[TagMatch]) -> EvidenceLayerReport:
    """便捷函数：分析证据层级并生成报告.

    Args:
        tags: 标签抽取结果.

    Returns:
        EvidenceLayerReport: 证据层级评估报告.
    """
    # 初始化变量 analyzer
    analyzer = EvidenceStrengthLayer()
    # 返回处理结果
    return analyzer.layer_evidences(tags)


def apply_single_layer_guard(report: EvidenceLayerReport) -> EvidenceLayerReport:
    """便捷函数：应用单一层级防护逻辑.

    Args:
        report: 初始评估报告.

    Returns:
        应用防护逻辑后的报告.
    """
    # 初始化变量 analyzer
    analyzer = EvidenceStrengthLayer()
    # 返回处理结果
    return analyzer.guard_against_single_layer_override(report)
