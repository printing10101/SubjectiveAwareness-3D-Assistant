"""V2 协议分析模块.

提供 V2 协议下的三维度分析功能，包括：
- 标签抽取与规则匹配
- 三维度分析（事实审查、模式匹配、矛盾分析）
- 档级组合与冲突检测
- 结论生成
"""

import re
import time
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.services.conflict_detector import Conflict, detect_conflicts
from app.services.analysis_service import generate_conclusion
from app.services.ollama_client import _extract_think_content, call_ollama_with_retry
from app.services.prompt import (
    V2_DIMENSION1_PROMPT,
    V2_DIMENSION2_PROMPT,
    V2_DIMENSION3_PROMPT,
)
from app.services.rule_engine import Rule, load_rules
from app.services.tag_extractor import TagMatch, extract_tags
from app.services.analysis_helpers import combine_tiers
from app.types.analysis_v2 import (
    AnalysisResultV2,
    FinalVerdict,
    PipelineMeta,
    TierEnum,
)
from app.utils.common import sanitize_json_string

from app.services.pipeline.complexity import classify_complexity
from app.services.pipeline.json_utils import robust_json_parse
from app.services.pipeline.knowledge import _retrieve_legal_knowledge

# 规则注入时取的最大规则数
_V2_RULE_INJECTION_TOP_N: int = 10

# 标签注入时取的最大标签数
_V2_TAG_INJECTION_TOP_N: int = 12

# 维度间档级上下文最大字符数
_V2_PRIOR_CONTEXT_MAX: int = 600

# V2 维度 prompt 默认温度
_V2_DEFAULT_TEMPERATURE: float = 0.2

# 缺省 tier 字符串
_V2_DEFAULT_TIER: str = TierEnum.T2.value

# 缺省最终量刑
_V2_DEFAULT_SENTENCE: str = "待定"

# 缺省主观明知
_V2_DEFAULT_KNOWLEDGE: str = "未知"

# 阶段名常量（用于 pipeline_meta 与日志）
_STAGE_COMPLEXITY: str = "complexity_classification"
_STAGE_KNOWLEDGE: str = "knowledge_retrieval"
_STAGE_TAGS: str = "tag_extraction"
_STAGE_RULES: str = "rule_matching"
_STAGE_DIM1: str = "dimension1"
_STAGE_DIM2: str = "dimension2"
_STAGE_DIM3: str = "dimension3"
_STAGE_COMBINE: str = "tier_combination"
_STAGE_CONFLICTS: str = "conflict_detection"
_STAGE_CONCLUSION: str = "conclusion_generation"


def _build_default_v2_dimension(
    dim_name: str,
    fallback_reason: str = "",
) -> dict[str, Any]:
    """构造 V2 协议的默认维度结果.

    当某维度 LLM 调用失败或 JSON 解析失败时使用.
    """
    return {
        "tier": _V2_DEFAULT_TIER,
        "reasoning": (
            f"维度 {dim_name} 分析失败，使用默认档级 {_V2_DEFAULT_TIER}。"
            + (f"原因：{fallback_reason}" if fallback_reason else "")
        ),
        "key_indicators": [],
        "triggered_rules": [],
        "fallback": True,
    }


def _build_default_v2_analysis_result(
    case_text: str,
    failed_stage: str = "",
    error: str = "",
) -> AnalysisResultV2:
    """构造 V2 协议下的兜底分析结果.

    适用于整个管道在第一阶段就崩溃的极端情况.
    """
    default_dim: dict[str, Any] = _build_default_v2_dimension("全维度")
    verdict: FinalVerdict = combine_tiers(
        _V2_DEFAULT_TIER,
        _V2_DEFAULT_TIER,
        _V2_DEFAULT_TIER,
        rule_hits=[],
    )
    return {
        "version": "v2",
        "subjective_knowledge": _V2_DEFAULT_KNOWLEDGE,
        "sentence": _V2_DEFAULT_SENTENCE,
        "court": "基层人民法院",
        "dimension1": {**default_dim, "key_indicators": []},
        "dimension2": {**default_dim, "pattern_match": ""},
        "dimension3": {**default_dim, "contradictions": []},
        "final_verdict": verdict,
        "triggered_rule_ids": [],
        "matched_tag_ids": [],
        "conflicts": [],
        "fallback": True,
        "failed_stage": failed_stage or "pipeline",
        "timestamp": datetime.now(UTC).isoformat(),
        "pipeline_meta": {
            "stage_durations_ms": {},
            "stage_status": {},
            "failed_stage": failed_stage or "pipeline",
        },
        "disclaimer": (
            "本结论由系统兜底生成，LLM 调用失败，仅作辅助参考。"
        ),
    }


def _format_tag_candidates(tags: list[Any] | None) -> str:
    """把 tag 元数据格式化为 prompt 注入片段（候选列表）."""
    if not tags:
        return "（无候选标签）"
    lines: list[str] = []
    for t in tags:
        if isinstance(t, dict):
            tag_id = t.get("tag_id", "?")
            name = t.get("name", "")
            category = t.get("category", "")
            extraction_hints = t.get("extraction_hints", [])
        else:
            tag_id = getattr(t, "tag_id", "?")
            name = getattr(t, "name", "")
            category = getattr(t, "category", "")
            extraction_hints = getattr(t, "extraction_hints", [])
        hints_str = "、".join(extraction_hints or []) or "—"
        lines.append(f"- {tag_id} {name}（{category}）| 提示词：{hints_str}")
    return "\n".join(lines)


def _format_rule_candidates(rules: list[Rule] | None) -> str:
    """把 Rule 列表格式化为 prompt 注入片段（候选列表）."""
    if not rules:
        return "（无候选规则）"
    lines: list[str] = []
    for r in rules:
        weight = f"{r.weight:.2f}" if isinstance(r.weight, (int, float)) else "n/a"
        conclusion = (r.conclusion or "").strip()[:80]
        conditions = (r.conditions or "").strip()[:120]
        lines.append(
            f"- {r.rule_id} {r.name} (weight={weight})\n"
            f"   条件：{conditions}\n"
            f"   结论：{conclusion}"
        )
    return "\n".join(lines)


def _format_matched_tags_for_prompt(matches: list[TagMatch]) -> str:
    """把已抽取的 TagMatch 列表格式化为 prompt 注入片段."""
    if not matches:
        return "（未抽取到任何事实标签）"
    lines: list[str] = []
    for m in matches[:_V2_TAG_INJECTION_TOP_N]:
        conf = f"{m.confidence:.2f}" if isinstance(m.confidence, (int, float)) else "n/a"
        text = (m.matched_text or "").strip()[:60]
        lines.append(f"- {m.tag_id}（{m.match_type}，conf={conf}）：{text}")
    return "\n".join(lines)


def _format_matched_rules_for_prompt(rules: list[Rule]) -> str:
    """把命中的 Rule 列表格式化为 prompt 注入片段."""
    if not rules:
        return "（未命中任何具体规则）"
    lines: list[str] = []
    for r in rules[:_V2_RULE_INJECTION_TOP_N]:
        weight = f"{r.weight:.2f}" if isinstance(r.weight, (int, float)) else "n/a"
        conclusion = (r.conclusion or "").strip()[:80]
        article = (r.article or "").strip()
        suffix = f" | {article}" if article else ""
        lines.append(f"- {r.rule_id} {r.name} (weight={weight}): {conclusion}{suffix}")
    return "\n".join(lines)


def _extract_tier_from_v2_response(result: dict[str, Any]) -> str:
    """从 V2 维度 LLM 响应中抽取档级.

    支持 ``tier`` 字段、``final_tier`` 字段或嵌套字段; 失败时返回 T2.
    """
    if not isinstance(result, dict):
        return _V2_DEFAULT_TIER

    # 常见字段名
    for key in ("tier", "final_tier", "档级", "tier_value"):
        if key in result:
            return TierEnum.coerce(result[key]).value

    # 嵌套字段
    gta = result.get("ground_truth_analysis")
    if isinstance(gta, dict):
        for dim in ("dimension1", "dimension2", "dimension3"):
            d = gta.get(dim)
            if isinstance(d, dict) and "tier" in d:
                return TierEnum.coerce(d["tier"]).value

    return _V2_DEFAULT_TIER


def _build_v2_dimension_result(
    dim_name: str,
    raw_result: dict[str, Any],
    fallback_used: bool = False,
) -> dict[str, Any]:
    """把 LLM 返回的 dict 转换为 V2 维度结果结构.

    适配 LLM 偶尔输出 ``{tier, reasoning, key_indicators, triggered_rules}``
    或带其他多余字段的情况.
    """
    tier = _extract_tier_from_v2_response(raw_result)
    reasoning = raw_result.get("reasoning") or raw_result.get("analysis") or ""
    if not isinstance(reasoning, str):
        reasoning = str(reasoning)

    # 触发规则
    triggered_raw = raw_result.get("triggered_rules", [])
    if not isinstance(triggered_raw, list):
        triggered_raw = []
    triggered_rules: list[str] = [
        str(x).strip() for x in triggered_raw if str(x).strip()
    ]

    base: dict[str, Any] = {
        "tier": tier,
        "reasoning": reasoning,
        "triggered_rules": triggered_rules,
        "fallback": fallback_used,
    }

    if dim_name == "dimension1":
        indicators = raw_result.get("key_indicators", [])
        if not isinstance(indicators, list):
            indicators = []
        base["key_indicators"] = [str(x) for x in indicators][:10]
    elif dim_name == "dimension2":
        pattern = raw_result.get("pattern_match", "")
        base["pattern_match"] = str(pattern) if pattern else ""
    elif dim_name == "dimension3":
        contradictions = raw_result.get("contradictions", [])
        if not isinstance(contradictions, list):
            contradictions = []
        base["contradictions"] = [str(x) for x in contradictions][:10]

    return base


def _format_v2_dimension1_prompt(
    *,
    case_text: str,
    matched_tags_text: str,
    triggered_rules_text: str,
    legal_knowledge: str,
) -> str:
    """格式化维度1的 prompt."""
    return V2_DIMENSION1_PROMPT.format(
        matched_tags=matched_tags_text,
        triggered_rules=triggered_rules_text,
        legal_knowledge=legal_knowledge or "（无相关检索知识）",
        case_text=case_text,
    )


def _format_v2_dimension2_prompt(
    *,
    case_text: str,
    matched_tags_text: str,
    triggered_rules_text: str,
    legal_knowledge: str,
) -> str:
    """格式化维度2的 prompt."""
    return V2_DIMENSION2_PROMPT.format(
        matched_tags=matched_tags_text,
        triggered_rules=triggered_rules_text,
        legal_knowledge=legal_knowledge or "（无相关检索知识）",
        case_text=case_text,
    )


def _format_v2_dimension3_prompt(
    *,
    case_text: str,
    matched_tags_text: str,
    triggered_rules_text: str,
    legal_knowledge: str,
    prior_dim1_text: str,
    prior_dim2_text: str,
) -> str:
    """格式化维度3的 prompt."""
    return V2_DIMENSION3_PROMPT.format(
        prior_dim1=prior_dim1_text,
        prior_dim2=prior_dim2_text,
        matched_tags=matched_tags_text,
        triggered_rules=triggered_rules_text,
        legal_knowledge=legal_knowledge or "（无相关检索知识）",
        case_text=case_text,
    )


async def _extract_tags_v2(
    case_text: str,
    rules: list[Rule] | None = None,
) -> list[TagMatch]:
    """V2 协议的标签抽取（先走关键词，必要时 LLM 兜底）.

    复用 :func:`extract_tags` 的实现；失败时返回空列表，确保不阻断后续流程.
    """
    try:
        return extract_tags(case_text, rules=rules or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"V2 标签抽取异常: {exc}")
        return []


def _match_rules_v2(
    case_text: str,
    tag_matches: list[TagMatch],
) -> list[Rule]:
    """V2 协议的规则匹配.

    实现策略（启发式，避免 LLM 不可用时无规则命中）：

    1. 加载所有规则；
    2. 遍历规则，统计其 ``conditions`` / ``conclusion`` / ``applicable_scenarios``
       文本与案件文本的关键词命中数；
    3. 命中数 ≥ 1 即视为命中；
    4. 至少返回 1 条 fallback 规则，避免下游无规则可参与档级组合。
    """
    rules = load_rules()
    if not rules:
        return []

    # 收集案件文本里的关键词（来自 tag_matches + 案件文本）
    case_keywords: set[str] = set()
    for m in tag_matches:
        for token in (m.tag_id, m.matched_text):
            if token:
                case_keywords.add(str(token).strip())

    # 简单分词：使用案件文本中出现的中文双字以上片段
    if case_text:
        for ch in re.findall(r"[\u4e00-\u9fff]{2,}", case_text):
            case_keywords.add(ch)

    scored: list[tuple[int, Rule]] = []
    for r in rules:
        haystack = " ".join(
            [
                r.name or "",
                r.conclusion or "",
                r.conditions or "",
                " ".join(r.applicable_scenarios or []),
            ]
        )
        hits = sum(1 for kw in case_keywords if kw and kw in haystack)
        # 至少 1 个命中且权重 > 0
        if hits > 0 and (r.weight or 0) > 0:
            scored.append((hits, r))

    # 按命中数 * 权重排序
    scored.sort(key=lambda x: x[0] * (x[1].weight or 0.0), reverse=True)
    matched = [r for _, r in scored[:_V2_RULE_INJECTION_TOP_N]]

    if not matched:
        # 兜底：返回权重最高的 1 条规则
        sorted_rules = sorted(
            rules, key=lambda r: r.weight or 0.0, reverse=True
        )
        if sorted_rules:
            matched = [sorted_rules[0]]

    return matched


async def _v2_run_single_dimension(
    case_text: str,
    system_prompt: str,
    dim_name: str,
    user_prompt: str,
    temperature: float = _V2_DEFAULT_TEMPERATURE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """V2 协议下单个维度的 LLM 调用.

    返回 ``(dimension_result, timing_meta)``. 失败时使用默认档级.
    """
    start = time.perf_counter()
    start_ts = datetime.now(UTC).isoformat()
    status = "success"
    error_info: dict[str, str] = {}

    dim_result: dict[str, Any] = _build_default_v2_dimension(dim_name)
    try:
        response = await call_ollama_with_retry(
            user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )
        reasoning_text, _ = _extract_think_content(response)
        cleaned = sanitize_json_string(response)
        parsed = robust_json_parse(cleaned, default=dim_result)
        # 兼容 LLM 返回的嵌套结构
        if "ground_truth_analysis" in parsed and dim_name in parsed["ground_truth_analysis"]:
            parsed = parsed["ground_truth_analysis"][dim_name]
        dim_result = _build_v2_dimension_result(dim_name, parsed, fallback_used=False)
        if reasoning_text:
            dim_result["reasoning_process"] = reasoning_text
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        error_info = {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "error_time": datetime.now(UTC).isoformat(),
        }
        logger.error(f"V2 {dim_name} 异常: {exc}")
        dim_result = _build_default_v2_dimension(
            dim_name, fallback_reason=str(exc)
        )

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    timing: dict[str, Any] = {
        "status": status,
        "duration_ms": duration_ms,
        "start_time": start_ts,
        "end_time": datetime.now(UTC).isoformat(),
        **error_info,
    }
    return dim_result, timing


def _build_v2_prior_context(
    dim1: dict[str, Any],
    dim2: dict[str, Any],
) -> tuple[str, str]:
    """构建维度 3 用的前置上下文（事实审查 + 模式匹配摘要）.

    返回 ``(prior_dim1_text, prior_dim2_text)`` 各自最长 300 字.
    """
    def _shorten(d: dict[str, Any]) -> str:
        tier = d.get("tier", _V2_DEFAULT_TIER)
        reasoning = d.get("reasoning", "无")
        if d.get("fallback"):
            return f"[默认档级] {tier}（该维度分析失败）"
        text = f"档级：{tier}\n推理摘要：{reasoning[:300]}"
        return text

    return _shorten(dim1), _shorten(dim2)
