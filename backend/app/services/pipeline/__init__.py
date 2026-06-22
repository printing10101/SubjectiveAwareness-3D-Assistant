"""分析管道包.

V2 协议（阶段 4）：负责按"复杂度分类 → 标签抽取 → 规则匹配 →
维度1 → 维度2 → 维度3（带前置上下文）→ 档级组合 → 冲突检测
→ 结论生成"的顺序编排 LLM 调用，输出 AnalysisResultV2。

V1 协议（向后兼容）：保留原 0-10 分评分管道，旧调用方仍可使用。
"""

from app.services.pipeline.complexity import (
    ComplexityLevel,
    classify_complexity,
)
from app.services.pipeline.json_utils import robust_json_parse
from app.services.pipeline.knowledge import (
    _retrieve_legal_knowledge,
)
from app.services.pipeline.orchestrator import (
    analyze_pipeline,
    analyze_pipeline_v2,
)
from app.services.pipeline.v1_analysis import (
    multi_dimension_analysis,
    self_consistency_analysis,
    single_pass_analysis,
)
from app.services.pipeline.v2_protocol import (
    _build_default_v2_analysis_result,
    _build_default_v2_dimension,
    _extract_tags_v2,
    _format_matched_rules_for_prompt,
    _format_matched_tags_for_prompt,
    _format_rule_candidates,
    _format_tag_candidates,
    _format_v2_dimension1_prompt,
    _format_v2_dimension2_prompt,
    _format_v2_dimension3_prompt,
    _match_rules_v2,
    _v2_run_single_dimension,
)

__all__ = [
    "analyze_pipeline",
    "analyze_pipeline_v2",
    "classify_complexity",
    "multi_dimension_analysis",
    "self_consistency_analysis",
    "single_pass_analysis",
    "robust_json_parse",
    "_retrieve_legal_knowledge",
    "_build_default_v2_dimension",
    "_build_default_v2_analysis_result",
    "_extract_tags_v2",
    "_match_rules_v2",
    "_format_tag_candidates",
    "_format_rule_candidates",
    "_format_matched_tags_for_prompt",
    "_format_matched_rules_for_prompt",
    "_format_v2_dimension1_prompt",
    "_format_v2_dimension2_prompt",
    "_format_v2_dimension3_prompt",
    "_v2_run_single_dimension",
]
