"""档级（V2）分析结果类型定义.

V2 协议使用"三维度 × 四档"代替 V1 协议的"0-10 分"，并把规则、标签、
冲突检查结果统一整合进分析结果。

四档（TierEnum）:
- T1  情节较轻   （一档 / 三年以下 / 罚金）
- T2  情节一般   （二档 / 三年以上七年以下）
- T3  情节严重   （三档 / 三年以上）
- T4  情节特别严重（最高档 / 七年以下或更高）

保留向后兼容：v1 的 ``AnalysisResult`` 与 v2 的 ``AnalysisResultV2``
共存于 ``app.types``，使用 ``version: Literal["v1", "v2"]`` 区分。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, NotRequired

from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# 档级枚举
# ---------------------------------------------------------------------------


class TierEnum(str, Enum):
    """帮信罪四档分类.

    数值顺序 = 严重程度（数字越大越严重），便于排序与组合规则计算。
    """

    T1 = "T1"  # 情节较轻
    T2 = "T2"  # 情节一般
    T3 = "T3"  # 情节严重
    T4 = "T4"  # 情节特别严重

    @classmethod
    def coerce(cls, value: Any) -> TierEnum:
        """将任意输入安全地归一化为 ``TierEnum``.

        接受: ``"T1"``/``"T2"``/``"T3"``/``"T4"``、中文"一档"/"二档" 等、
        ``"高"/"中"/"低"``、数字 1-4，以及 ``TierEnum`` 自身。
        任何无法识别的输入都降级为 :attr:`T2`（情节一般），确保调用方不会
        因缺少 tier 字段而崩溃。
        """
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.T2
        s = str(value).strip()
        if not s:
            return cls.T2
        # 直接匹配
        for tier in cls:
            if s.upper() == tier.value or s == tier.name:
                return tier
        # 中文/同义词映射
        aliases: dict[str, TierEnum] = {
            "一档": cls.T1,
            "1档": cls.T1,
            "第一档": cls.T1,
            "情节较轻": cls.T1,
            "情节轻微": cls.T1,
            "情节显著轻微": cls.T1,
            "低": cls.T1,
            "低档": cls.T1,
            "轻微": cls.T1,
            "二档": cls.T2,
            "2档": cls.T2,
            "第二档": cls.T2,
            "情节一般": cls.T2,
            "中": cls.T2,
            "中档": cls.T2,
            "三档": cls.T3,
            "3档": cls.T3,
            "第三档": cls.T3,
            "情节严重": cls.T3,
            "高": cls.T3,
            "高档": cls.T3,
            "四档": cls.T4,
            "4档": cls.T4,
            "第四档": cls.T4,
            "情节特别严重": cls.T4,
            "特别严重": cls.T4,
            "极高": cls.T4,
            "最高档": cls.T4,
        }
        if s in aliases:
            return aliases[s]
        # 数字 1-4
        try:
            n = int(s)
            if n in (1, 2, 3, 4):
                return cls(f"T{n}")
        except (TypeError, ValueError):
            pass
        # 包含关系回退
        for k, v in aliases.items():
            if k in s:
                return v
        return cls.T2

    @property
    def rank(self) -> int:
        """数值等级，1-4，数字越大越严重."""
        return int(self.value[1])

    def __lt__(self, other: TierEnum) -> bool:  # type: ignore[override]
        if not isinstance(other, TierEnum):
            return NotImplemented
        return self.rank < other.rank

    def __le__(self, other: TierEnum) -> bool:
        if not isinstance(other, TierEnum):
            return NotImplemented
        return self.rank <= other.rank

    def __gt__(self, other: TierEnum) -> bool:
        if not isinstance(other, TierEnum):
            return NotImplemented
        return self.rank > other.rank

    def __ge__(self, other: TierEnum) -> bool:
        if not isinstance(other, TierEnum):
            return NotImplemented
        return self.rank >= other.rank

    @property
    def chinese_label(self) -> str:
        """中文标签（用于报告展示）."""
        mapping = {
            TierEnum.T1: "一档（情节较轻）",
            TierEnum.T2: "二档（情节一般）",
            TierEnum.T3: "三档（情节严重）",
            TierEnum.T4: "四档（情节特别严重）",
        }
        return mapping[self]

    @property
    def sentence_band(self) -> str:
        """量刑区间（与刑法第 287 条之二对应）."""
        mapping = {
            TierEnum.T1: "三年以下有期徒刑、拘役或者管制，并处或者单处罚金",
            TierEnum.T2: "三年以下有期徒刑，并处罚金",
            TierEnum.T3: "三年以上七年以下有期徒刑，并处罚金",
            TierEnum.T4: "七年以上有期徒刑，并处罚金或者没收财产",
        }
        return mapping[self]


# ---------------------------------------------------------------------------
# 维度结果 V2
# ---------------------------------------------------------------------------


class _DimensionBaseV2(TypedDict):
    """维度 V2 公共字段.

    Attributes:
        tier: 档级判定结果
        reasoning: 完整推理过程（中文）
        confidence: 维度内的局部置信度（0-1），可由 self-consistency 提供
    """

    tier: str  # TierEnum 的 value (T1/T2/T3/T4)
    reasoning: str
    confidence: NotRequired[float]


class Dimension1ResultV2(_DimensionBaseV2):
    """维度 1 V2（事实知识审查 / 构成要件）.

    Attributes:
        tier: 事实要件齐备程度对应的档级
        reasoning: 推理过程
        key_indicators: 关键事实/要件指标
        triggered_rules: 命中且影响档级的规则 ID 列表（如 R005/R009 等）
        confidence: 局部置信度
    """

    key_indicators: list[str]
    triggered_rules: list[str]


class Dimension2ResultV2(_DimensionBaseV2):
    """维度 2 V2（模式匹配 / 情节评估）.

    Attributes:
        tier: 行为模式对应的情节档级
        reasoning: 推理过程
        pattern_match: 与典型模式的对比结果
        triggered_rules: 影响档级的规则 ID
        confidence: 局部置信度
    """

    pattern_match: str
    triggered_rules: list[str]


class Dimension3ResultV2(_DimensionBaseV2):
    """维度 3 V2（矛盾分析 / 抗辩可信度）.

    Attributes:
        tier: 嫌疑人辩解对档级的影响档级（越低代表抗辩越有效）
        reasoning: 推理过程
        contradictions: 矛盾点列表
        triggered_rules: 影响档级的规则 ID
        confidence: 局部置信度
    """

    contradictions: list[str]
    triggered_rules: list[str]


# ---------------------------------------------------------------------------
# 顶层分析结果 V2
# ---------------------------------------------------------------------------


class FinalVerdict(TypedDict):
    """档级组合器产出的最终结论.

    Attributes:
        final_tier: 综合档级（T1-T4）
        final_label: 人类可读的中文标签
        sentence_band: 建议量刑区间
        confidence: 综合置信度（0-1）
        severity_score: 数值化的严重程度（1-4），便于排序与报表
        combination_rule: 命中的组合规则标识（来自 tier_combiner）
    """

    final_tier: str
    final_label: str
    sentence_band: str
    confidence: float
    severity_score: int
    combination_rule: str


class PipelineMeta(TypedDict):
    """管道编排元数据.

    记录每阶段耗时、状态、失败信息，用于监控、审计与重试。
    Attributes:
        stage_durations_ms: 阶段名 -> 耗时（毫秒）
        stage_status: 阶段名 -> "success" | "failed" | "skipped"
        failed_stage: 失败阶段名（顶层 fallback 字段已使用 failed_stage）
    """

    stage_durations_ms: dict[str, float]
    stage_status: dict[str, str]
    failed_stage: NotRequired[str]


class AnalysisResultV2(TypedDict):
    """V2 主分析结果.

    Attributes:
        version: 协议版本，固定为 ``"v2"``
        subjective_knowledge: 主观明知程度判定（兼容字段）
        sentence: 量刑建议文本
        court: 建议管辖法院
        dimension1: 维度 1（构成要件）结果
        dimension2: 维度 2（情节模式）结果
        dimension3: 维度 3（矛盾分析）结果
        final_verdict: 档级组合后的最终结论
        triggered_rule_ids: 触发的规则 ID 列表
        matched_tag_ids: 命中的标签 ID 列表
        conflicts: 冲突检测结果（结构同 :class:`Conflict`）
        confidence: 整体置信度（0-1）
        confidence_details: 各阶段置信度明细
        pipeline_meta: 各阶段耗时与状态
        fallback: 是否使用降级结果
        failed_stage: 失败阶段名（fallback 时存在）
        reasoning_process: LLM 原始推理（<think> 标签内容）
        timestamp: ISO 时间戳
        knowledge_used: 是否使用知识图谱
        knowledge_entries: 知识条目摘要
        disclaimer: 免责声明
    """

    version: Literal["v2"]
    subjective_knowledge: NotRequired[str]
    sentence: NotRequired[str]
    court: NotRequired[str]
    dimension1: Dimension1ResultV2
    dimension2: Dimension2ResultV2
    dimension3: Dimension3ResultV2
    final_verdict: FinalVerdict
    triggered_rule_ids: list[str]
    matched_tag_ids: list[str]
    conflicts: list[dict[str, Any]]  # Conflict.to_dict() 序列化
    confidence: NotRequired[float]
    confidence_details: NotRequired[dict[str, Any]]
    pipeline_meta: NotRequired[PipelineMeta]
    fallback: bool
    failed_stage: NotRequired[str]
    reasoning_process: NotRequired[str]
    timestamp: str
    knowledge_used: NotRequired[bool]
    knowledge_entries: NotRequired[list[dict[str, str]]]
    disclaimer: NotRequired[str]


# ---------------------------------------------------------------------------
# 联合类型 / 便捷类型
# ---------------------------------------------------------------------------


AnalysisVersion = Literal["v1", "v2"]


def is_v2_result(payload: dict[str, Any] | None) -> bool:
    """判断一个反序列化的结果字典是否属于 V2 协议."""
    if not isinstance(payload, dict):
        return False
    return payload.get("version") == "v2"


__all__ = [
    "AnalysisResultV2",
    "AnalysisVersion",
    "Dimension1ResultV2",
    "Dimension2ResultV2",
    "Dimension3ResultV2",
    "FinalVerdict",
    "PipelineMeta",
    "TierEnum",
    "is_v2_result",
]
