"""分析管道编排器.

负责编排 V1 和 V2 协议的完整分析流程，包括：
- 复杂度评估
- 知识检索
- 标签抽取
- 规则匹配
- 三维度分析
- 档级组合
- 冲突检测
- 结论生成
"""

import time
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.config import AnalysisConfig
from app.services.conflict_detector import Conflict, detect_conflicts
from app.services.analysis_service import generate_conclusion
from app.services.rule_engine import Rule
from app.services.tag_extractor import TagMatch
from app.services.analysis_helpers import combine_tiers
from app.types.analysis import AnalysisResult
from app.types.analysis_v2 import (
    AnalysisResultV2,
    FinalVerdict,
    PipelineMeta,
)
from app.utils.monitoring import ANALYSIS_COUNTER, ANALYSIS_DURATION

from app.services.pipeline.complexity import ComplexityLevel, classify_complexity
from app.services.pipeline.json_utils import robust_json_parse
from app.services.pipeline.knowledge import _retrieve_legal_knowledge
from app.services.pipeline.v1_analysis import (
    multi_dimension_analysis,
    self_consistency_analysis,
    single_pass_analysis,
)
from app.services.pipeline.v2_protocol import (
    _STAGE_COMBINE,
    _STAGE_COMPLEXITY,
    _STAGE_CONFLICTS,
    _STAGE_CONCLUSION,
    _STAGE_DIM1,
    _STAGE_DIM2,
    _STAGE_DIM3,
    _STAGE_KNOWLEDGE,
    _STAGE_RULES,
    _STAGE_TAGS,
    _V2_DEFAULT_KNOWLEDGE,
    _V2_DEFAULT_SENTENCE,
    _V2_DEFAULT_TIER,
    _build_default_v2_analysis_result,
    _build_default_v2_dimension,
    _build_v2_prior_context,
    _extract_tags_v2,
    _format_matched_rules_for_prompt,
    _format_matched_tags_for_prompt,
    _format_v2_dimension1_prompt,
    _format_v2_dimension2_prompt,
    _format_v2_dimension3_prompt,
    _match_rules_v2,
    _v2_run_single_dimension,
)


def _record_stage(
    meta: PipelineMeta,
    name: str,
    duration_ms: float,
    status: str,
) -> None:
    """记录单个阶段的耗时与状态到 pipeline_meta."""
    meta["stage_durations_ms"][name] = duration_ms
    meta["stage_status"][name] = status


@ANALYSIS_DURATION.time()
async def analyze_pipeline(
    case_text: str,
    mode: str = "auto",
    version: str = "v2",
) -> Any:
    """主分析管道入口（同时支持 V1 / V2 协议）.

    Args:
        case_text: 案件事实文本
        mode: 分析模式（auto/single/multi）
        version: 协议版本 ``"v1"``（保留 0-10 评分）或 ``"v2"``（档级 + 规则/标签/冲突）
    """
    if version == "v1":
        return await _analyze_pipeline_v1(case_text, mode=mode)
    return await analyze_pipeline_v2(case_text, mode=mode)


async def _analyze_pipeline_v1(case_text: str, mode: str = "auto") -> AnalysisResult:
    """V1 协议下的主分析管道入口（保留 0-10 评分，向后兼容）."""
    try:
        legal_knowledge, knowledge_entries = await _retrieve_legal_knowledge(case_text)
        knowledge_used: bool = bool(legal_knowledge)

        if legal_knowledge:
            logger.info(f"知识注入启用: {len(knowledge_entries)} 条知识条目")

        if AnalysisConfig.SC_ENABLED and mode != "single":
            logger.info(
                f"启用 Self-Consistency 多次采样: "
                f"samples={AnalysisConfig.SC_NUM_SAMPLES}, "
                f"temperature={AnalysisConfig.SC_TEMPERATURE}"
            )
            result = await self_consistency_analysis(
                case_text, mode=mode,
                n_samples=AnalysisConfig.SC_NUM_SAMPLES,
                sample_temperature=AnalysisConfig.SC_TEMPERATURE,
                legal_knowledge=legal_knowledge,
            )
            result["fallback"] = False
            result["timestamp"] = datetime.now(UTC).isoformat()
            result["knowledge_used"] = knowledge_used
            result["knowledge_entries"] = knowledge_entries
            return result

        complexity: ComplexityLevel = classify_complexity(case_text)
        logger.info(f"自动模式: 复杂度='{complexity}'")

        if mode == "single" or (
            mode == "auto" and complexity == "simple"
        ):
            logger.info("推理模式: single")
            result: AnalysisResult = await single_pass_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )
        elif mode == "multi" or (
            mode == "auto" and complexity in ("medium", "complex")
        ):
            logger.info("推理模式: multi")
            result = await multi_dimension_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )
        else:
            result = await single_pass_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )

        if "ground_truth_analysis" not in result:
            from app.services.pipeline.v1_analysis import _build_default_dimension
            result["ground_truth_analysis"] = {
                "dimension1": _build_default_dimension(),
                "dimension2": _build_default_dimension(),
                "dimension3": _build_default_dimension(),
            }

        result["fallback"] = result.get("fallback", False)
        result["timestamp"] = datetime.now(UTC).isoformat()
        result["knowledge_used"] = knowledge_used
        result["knowledge_entries"] = knowledge_entries

        ANALYSIS_COUNTER.labels(mode=mode, status="success").inc()
        return result
    except Exception:
        ANALYSIS_COUNTER.labels(mode=mode, status="error").inc()
        raise


@ANALYSIS_DURATION.time()
async def analyze_pipeline_v2(
    case_text: str,
    mode: str = "auto",
) -> AnalysisResultV2:
    """V2 协议下的主分析管道入口.

    顺序：

    1. 复杂度分类
    2. 知识检索（Neo4j / SQLite FTS / 内存兜底）
    3. 标签抽取
    4. 规则匹配
    5. 维度 1（事实审查）
    6. 维度 2（模式匹配）
    7. 维度 3（矛盾分析，带前置上下文）
    8. 档级组合
    9. 冲突检测
    10. 结论生成

    任一阶段失败不阻断，标记 ``fallback=True`` 并记录 ``failed_stage``.
    """
    meta: PipelineMeta = {
        "stage_durations_ms": {},
        "stage_status": {},
    }
    failed_stage: str = ""
    overall_start = time.perf_counter()

    # 阶段 1：复杂度分类
    stage_start = time.perf_counter()
    try:
        complexity: ComplexityLevel = classify_complexity(case_text)
        _record_stage(
            meta, _STAGE_COMPLEXITY,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success",
        )
    except Exception as exc:  # noqa: BLE001
        complexity = "medium"
        _record_stage(
            meta, _STAGE_COMPLEXITY,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_COMPLEXITY
        logger.warning(f"复杂度分类失败: {exc}")

    # 阶段 2：知识检索
    stage_start = time.perf_counter()
    knowledge_text: str = ""
    knowledge_entries: list[dict[str, str]] = []
    knowledge_used: bool = False
    try:
        knowledge_text, knowledge_entries = await _retrieve_legal_knowledge(case_text)
        knowledge_used = bool(knowledge_text)
        _record_stage(
            meta, _STAGE_KNOWLEDGE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if knowledge_text else "skipped",
        )
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_KNOWLEDGE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_KNOWLEDGE
        logger.warning(f"知识检索失败: {exc}")

    # 阶段 3：标签抽取
    stage_start = time.perf_counter()
    tag_matches: list[TagMatch] = []
    try:
        tag_matches = await _extract_tags_v2(case_text, rules=None)
        _record_stage(
            meta, _STAGE_TAGS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if tag_matches else "skipped",
        )
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_TAGS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_TAGS
        logger.warning(f"标签抽取失败: {exc}")

    matched_tag_ids: list[str] = list({m.tag_id for m in tag_matches})

    # 阶段 4：规则匹配
    stage_start = time.perf_counter()
    rule_hits: list[Rule] = []
    try:
        rule_hits = _match_rules_v2(case_text, tag_matches)
        _record_stage(
            meta, _STAGE_RULES,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if rule_hits else "skipped",
        )
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_RULES,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_RULES
        logger.warning(f"规则匹配失败: {exc}")

    triggered_rule_ids: list[str] = [r.rule_id for r in rule_hits]

    matched_tags_text = _format_matched_tags_for_prompt(tag_matches)
    triggered_rules_text = _format_matched_rules_for_prompt(rule_hits)

    # 阶段 5：维度 1
    stage_start = time.perf_counter()
    try:
        dim1_prompt = _format_v2_dimension1_prompt(
            case_text=case_text,
            matched_tags_text=matched_tags_text,
            triggered_rules_text=triggered_rules_text,
            legal_knowledge=knowledge_text,
        )
        dim1_result, dim1_meta = await _v2_run_single_dimension(
            case_text,
            "你是帮信罪事实审查维度的专业分析助手，按 5 步推理并输出 tier。",
            "dimension1",
            dim1_prompt,
        )
        _record_stage(
            meta, _STAGE_DIM1, dim1_meta.get("duration_ms", 0.0),
            dim1_meta.get("status", "unknown"),
        )
        if dim1_meta.get("status") == "failed":
            failed_stage = failed_stage or _STAGE_DIM1
    except Exception as exc:  # noqa: BLE001
        dim1_result = _build_default_v2_dimension("dimension1", fallback_reason=str(exc))
        _record_stage(
            meta, _STAGE_DIM1,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_DIM1
        logger.warning(f"维度1执行失败: {exc}")

    # 阶段 6：维度 2
    stage_start = time.perf_counter()
    try:
        dim2_prompt = _format_v2_dimension2_prompt(
            case_text=case_text,
            matched_tags_text=matched_tags_text,
            triggered_rules_text=triggered_rules_text,
            legal_knowledge=knowledge_text,
        )
        dim2_result, dim2_meta = await _v2_run_single_dimension(
            case_text,
            "你是帮信罪模式匹配维度的专业分析助手，按 5 步推理并输出 tier。",
            "dimension2",
            dim2_prompt,
        )
        _record_stage(
            meta, _STAGE_DIM2, dim2_meta.get("duration_ms", 0.0),
            dim2_meta.get("status", "unknown"),
        )
        if dim2_meta.get("status") == "failed":
            failed_stage = failed_stage or _STAGE_DIM2
    except Exception as exc:  # noqa: BLE001
        dim2_result = _build_default_v2_dimension("dimension2", fallback_reason=str(exc))
        _record_stage(
            meta, _STAGE_DIM2,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_DIM2
        logger.warning(f"维度2执行失败: {exc}")

    # 阶段 7：维度 3（带前置上下文）
    stage_start = time.perf_counter()
    prior_dim1_text, prior_dim2_text = _build_v2_prior_context(dim1_result, dim2_result)
    try:
        dim3_prompt = _format_v2_dimension3_prompt(
            case_text=case_text,
            matched_tags_text=matched_tags_text,
            triggered_rules_text=triggered_rules_text,
            legal_knowledge=knowledge_text,
            prior_dim1_text=prior_dim1_text,
            prior_dim2_text=prior_dim2_text,
        )
        dim3_result, dim3_meta = await _v2_run_single_dimension(
            case_text,
            "你是帮信罪矛盾分析维度的专业分析助手，按 5 步推理并输出 tier。",
            "dimension3",
            dim3_prompt,
        )
        _record_stage(
            meta, _STAGE_DIM3, dim3_meta.get("duration_ms", 0.0),
            dim3_meta.get("status", "unknown"),
        )
        if dim3_meta.get("status") == "failed":
            failed_stage = failed_stage or _STAGE_DIM3
    except Exception as exc:  # noqa: BLE001
        dim3_result = _build_default_v2_dimension("dimension3", fallback_reason=str(exc))
        _record_stage(
            meta, _STAGE_DIM3,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_DIM3
        logger.warning(f"维度3执行失败: {exc}")

    # 阶段 8：档级组合
    stage_start = time.perf_counter()
    try:
        verdict: FinalVerdict = combine_tiers(
            dim1_result.get("tier", _V2_DEFAULT_TIER),
            dim2_result.get("tier", _V2_DEFAULT_TIER),
            dim3_result.get("tier", _V2_DEFAULT_TIER),
            rule_hits=rule_hits,
        )
        _record_stage(
            meta, _STAGE_COMBINE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success",
        )
    except Exception as exc:  # noqa: BLE001
        verdict = combine_tiers(
            _V2_DEFAULT_TIER, _V2_DEFAULT_TIER, _V2_DEFAULT_TIER, rule_hits=[]
        )
        _record_stage(
            meta, _STAGE_COMBINE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_COMBINE
        logger.warning(f"档级组合失败: {exc}")

    # 阶段 9：冲突检测
    stage_start = time.perf_counter()
    conflicts: list[Conflict] = []
    try:
        dim_results_for_conflict: dict[str, dict[str, Any]] = {
            "dimension1": {
                "tier": dim1_result.get("tier", _V2_DEFAULT_TIER),
                "reasoning": dim1_result.get("reasoning", ""),
            },
            "dimension2": {
                "tier": dim2_result.get("tier", _V2_DEFAULT_TIER),
                "reasoning": dim2_result.get("reasoning", ""),
            },
            "dimension3": {
                "tier": dim3_result.get("tier", _V2_DEFAULT_TIER),
                "reasoning": dim3_result.get("reasoning", ""),
            },
        }
        conflicts = detect_conflicts(
            tag_matches, rule_hits, dim_results_for_conflict
        )
        _record_stage(
            meta, _STAGE_CONFLICTS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success",
        )
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_CONFLICTS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_CONFLICTS
        logger.warning(f"冲突检测失败: {exc}")

    # 阶段 10：结论生成
    stage_start = time.perf_counter()
    conclusion_text: str = ""
    try:
        conclusion_text = await generate_conclusion(
            verdict=verdict,
            rule_hits=rule_hits,
            tags=tag_matches,
            case_text=case_text,
            dimension_tiers={
                "dimension1": dim1_result.get("tier", _V2_DEFAULT_TIER),
                "dimension2": dim2_result.get("tier", _V2_DEFAULT_TIER),
                "dimension3": dim3_result.get("tier", _V2_DEFAULT_TIER),
            },
            conflicts=conflicts,
        )
        _record_stage(
            meta, _STAGE_CONCLUSION,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if conclusion_text else "skipped",
        )
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_CONCLUSION,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_CONCLUSION
        logger.warning(f"结论生成失败: {exc}")

    # 整体置信度：维度的均值（0-1）
    confidences: list[float] = []
    for d in (dim1_result, dim2_result, dim3_result):
        c = d.get("confidence")
        if isinstance(c, (int, float)):
            confidences.append(max(0.0, min(1.0, float(c))))
    overall_confidence: float = (
        round(sum(confidences) / len(confidences), 4) if confidences else 0.5
    )

    # 冲突序列化为 dict
    conflicts_payload: list[dict[str, Any]] = [c.to_dict() for c in conflicts]

    result: AnalysisResultV2 = {
        "version": "v2",
        "subjective_knowledge": (
            dim1_result.get("key_indicators", [None])[0]
            if dim1_result.get("key_indicators")
            else _V2_DEFAULT_KNOWLEDGE
        ),
        "sentence": verdict.get("sentence_band", _V2_DEFAULT_SENTENCE),
        "court": "基层人民法院",
        "dimension1": {  # type: ignore[typeddict-item]
            "tier": dim1_result.get("tier", _V2_DEFAULT_TIER),
            "reasoning": dim1_result.get("reasoning", ""),
            "key_indicators": dim1_result.get("key_indicators", []),
            "triggered_rules": dim1_result.get("triggered_rules", []),
        },
        "dimension2": {  # type: ignore[typeddict-item]
            "tier": dim2_result.get("tier", _V2_DEFAULT_TIER),
            "reasoning": dim2_result.get("reasoning", ""),
            "pattern_match": dim2_result.get("pattern_match", ""),
            "triggered_rules": dim2_result.get("triggered_rules", []),
        },
        "dimension3": {  # type: ignore[typeddict-item]
            "tier": dim3_result.get("tier", _V2_DEFAULT_TIER),
            "reasoning": dim3_result.get("reasoning", ""),
            "contradictions": dim3_result.get("contradictions", []),
            "triggered_rules": dim3_result.get("triggered_rules", []),
        },
        "final_verdict": verdict,
        "triggered_rule_ids": triggered_rule_ids,
        "matched_tag_ids": matched_tag_ids,
        "conflicts": conflicts_payload,
        "confidence": overall_confidence,
        "pipeline_meta": meta,
        "fallback": bool(failed_stage) or any(
            meta["stage_status"].get(s) == "failed"
            for s in (_STAGE_DIM1, _STAGE_DIM2, _STAGE_DIM3, _STAGE_COMBINE)
        ),
        "timestamp": datetime.now(UTC).isoformat(),
        "knowledge_used": knowledge_used,
        "knowledge_entries": knowledge_entries,
        "disclaimer": (
            "本结论由 V2 协议（三维度 × 四档）生成，"
            "并集成了规则、标签、冲突检测结果，仅供办案人员参考。"
        ),
    }

    if failed_stage:
        result["failed_stage"] = failed_stage
        meta["failed_stage"] = failed_stage

    # 把 LLM 原始推理（仅维度 1）放在顶层，方便阅读
    if dim1_result.get("reasoning_process"):
        result["reasoning_process"] = dim1_result["reasoning_process"]

    # 把结论文本附加在 result.conclusion_text 字段上（不破坏 TypedDict）
    result["conclusion_text"] = conclusion_text  # type: ignore[typeddict-unknown-key]

    # 整体耗时
    meta["stage_durations_ms"]["_total"] = round(
        (time.perf_counter() - overall_start) * 1000, 2
    )

    try:
        ANALYSIS_COUNTER.labels(mode=mode, status="success").inc()
    except Exception:  # noqa: BLE001
        pass

    logger.info(
        f"V2 管道完成: complexity={complexity}, "
        f"final_tier={verdict.get('final_tier')}, "
        f"fallback={result['fallback']}, "
        f"total_ms={meta['stage_durations_ms'].get('_total')}"
    )

    return result
