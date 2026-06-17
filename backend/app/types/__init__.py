"""类型定义包.

提供项目中所有复杂数据结构的 TypedDict 类型定义，
确保类型注解的完整性和准确性。

V1 协议：0-10 评分，定义在 :mod:`app.types.analysis`（默认，向后兼容）。
V2 协议：三维度 × 四档 + 规则/标签/冲突，定义在 :mod:`app.types.analysis_v2`。
"""

# 导入模块: from app.types.analysis
from app.types.analysis import (
    AnalysisReport,
    AnalysisResult,
    CacheSnapshot,
    Dimension1Result,
    Dimension2Result,
    Dimension3Result,
    DimensionResult,
    ExperimentResult,
    GroundTruthAnalysis,
    ReportList,
    SentencingSuggestion,
    SimilarCase,
)
# 导入模块: from app.types.analysis_v2
from app.types.analysis_v2 import (
    AnalysisResultV2,
    AnalysisVersion,
    Dimension1ResultV2,
    Dimension2ResultV2,
    Dimension3ResultV2,
    FinalVerdict,
    PipelineMeta,
    TierEnum,
    is_v2_result,
)


__all__ = [
    # v1
    "AnalysisReport",
    "AnalysisResult",
    "CacheSnapshot",
    "Dimension1Result",
    "Dimension2Result",
    "Dimension3Result",
    "DimensionResult",
    "ExperimentResult",
    "GroundTruthAnalysis",
    "ReportList",
    "SentencingSuggestion",
    "SimilarCase",
    # v2
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
