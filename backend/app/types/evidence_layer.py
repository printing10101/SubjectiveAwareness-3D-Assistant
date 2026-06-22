"""证据层报告类型定义.

V1.2 法律引擎升级引入的证据强度分层报告结构。
"""
from dataclasses import dataclass, field
from typing import Literal

LegalPath = Literal["帮信罪主路径",
    "诈骗罪共同犯罪路径",
    "掩饰隐瞒犯罪所得路径",
    "规范路径待核实"]

EvidenceStrength = Literal["直接认知性证据",
    "客观异常事实",
    "认知增强因素",
    "辩解检验材料"
]


# 应用装饰器: dataclass
@dataclass
# 定义 SubjectInfo 类
class SubjectInfo:
    """单个主体信息."""

    name: str
    role: str
    objective_behavior: str
    cognitive_evidence: list[str] = field(default_factory=list)
    defense: str = ""
    disputes: list[str] = field(default_factory=list)


# 应用装饰器: dataclass
@dataclass
# 定义 EvidenceLayer 类
class EvidenceLayer:
    """证据强度分层.

    Attributes:
        strength: 证据强度级别
        facts: 事实列表
        legal_basis: 法律依据
    """

    strength: EvidenceStrength
    facts: list[str]
    legal_basis: str = ""


# 应用装饰器: dataclass
@dataclass
# 定义 BoundaryAlert 类
class BoundaryAlert:
    """边界提醒.

    Attributes:
        alert_type: 提醒类型
        description: 描述
        severity: 严重程度 (low/medium/high)
    """

    alert_type: str
    description: str
    severity: Literal["low", "medium", "high"] = "medium"


# 应用装饰器: dataclass
@dataclass
# 定义 EvidenceLayerReport 类
class EvidenceLayerReport:
    """证据层报告.

    V1.2 核心数据结构，包含：
    - 识别的法律路径
    - 多主体信息
    - 证据强度分层
    - 边界提醒
    """

    identified_path: LegalPath
    subjects: list[SubjectInfo] = field(default_factory=list)
    evidence_layers: list[EvidenceLayer] = field(default_factory=list)
    boundary_alerts: list[BoundaryAlert] = field(default_factory=list)
    is_primary_path_bangxin: bool = True

    def should_cite_article_287_2(self) -> bool:
        """判断是否应引用《刑法》第287-2条.

        仅当识别路径为帮信罪主路径时返回True。
        """
        return self.identified_path == "帮信罪主路径"

    def get_scoring_mode(self) -> Literal["definitive", "reference_only"]:
        """获取打分模式.

        帮信罪主路径：definitive（决定性）
        其他路径：reference_only（仅参照）
        """
        if self.identified_path == "帮信罪主路径":
            return "definitive"
        return "reference_only"
