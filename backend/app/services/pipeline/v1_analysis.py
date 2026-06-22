"""V1 协议分析模块.

提供 V1 协议下的三种分析模式：
- 单通道分析（simple 案件）
- 多维度分析（medium/complex 案件）
- Self-Consistency 多次采样验证分析
"""

import asyncio
import statistics
import time
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.config import AnalysisConfig
from app.services.ollama_client import _extract_think_content, call_ollama_with_retry
from app.services.prompt import (
    ANALYSIS_SYSTEM_PROMPT,
    DIMENSION1_PROMPT,
    DIMENSION2_PROMPT,
    DIMENSION3_PROMPT,
)
from app.types.analysis import AnalysisResult
from app.utils.common import sanitize_json_string

from app.services.pipeline.complexity import ComplexityLevel, classify_complexity
from app.services.pipeline.json_utils import robust_json_parse

_DEFAULT_SCORE = 5.0
_MAX_CONTEXT_LENGTH = 500
_MIN_SAMPLES_FOR_STDEV = 2


def _build_default_dimension() -> dict[str, Any]:
    """构建默认维度分析结果."""
    return {
        "score": AnalysisConfig.DEFAULT_DIMENSION_SCORE,
        "reasoning": AnalysisConfig.DEFAULT_REASONING,
    }


def _build_default_analysis_result() -> AnalysisResult:
    """构建预设的默认分析结果，用于 JSON 解析失败时的降级返回."""
    default_dim = _build_default_dimension()
    return {
        "ground_truth_analysis": {
            "dimension1": default_dim,
            "dimension2": default_dim,
            "dimension3": default_dim,
        },
        "subjective_knowledge": "未知",
        "sentence": "待定",
        "fallback": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def single_pass_analysis(
    case_text: str,
    mode: str = "auto",
    temperature: float = AnalysisConfig.OLLAMA_DEFAULT_TEMPERATURE,
    legal_knowledge: str = "",
) -> AnalysisResult:
    """单通道分析（适用于简单案件）.

    在单次 LLM 调用中完成所有维度分析。

    Args:
        case_text: 案件事实文本
        mode: 分析模式
        temperature: 生成温度
        legal_knowledge: 注入的检索知识（可选）

    Returns:
        AnalysisResult: 包含三维度分析结果的字典
    """
    logger.info(f"使用单通道分析模式 ({mode}), temperature={temperature}")
    system_prompt: str = ANALYSIS_SYSTEM_PROMPT.replace("{legal_knowledge}", legal_knowledge)
    user_prompt: str = f"请对以下案件进行三维度分析：\n\n{case_text}"

    response: str = await call_ollama_with_retry(
        user_prompt, system_prompt=system_prompt, temperature=temperature
    )
    reasoning_text, _ = _extract_think_content(response)
    result: AnalysisResult = robust_json_parse(sanitize_json_string(response))
    if reasoning_text:
        result["reasoning_process"] = reasoning_text
    return result


async def _single_dimension_analysis(
    case_text: str,
    system_prompt: str,
    _dimension_name: str,
    user_prompt: str | None = None,
    temperature: float = AnalysisConfig.OLLAMA_DEFAULT_TEMPERATURE,
) -> dict[str, Any]:
    """单个维度的独立分析.

    对单个维度调用 LLM，并使用 robust_json_parse 处理响应。
    异常会向上传播，由调用方（_timed_dimension_analysis）统一捕获并记录。

    Args:
        case_text: 案件事实文本（当 user_prompt 为 None 时作为用户消息）
        system_prompt: 当前维度的系统提示词
        dimension_name: 维度名称（用于日志记录）
        user_prompt: 自定义用户消息，为 None 时使用 case_text
        temperature: 生成温度

    Returns:
        dict: 该维度的分析结果字典

    Raises:
        Exception: LLM 调用失败时向上传播异常
    """
    prompt: str = user_prompt if user_prompt is not None else case_text
    response = await call_ollama_with_retry(
        prompt, system_prompt=system_prompt, temperature=temperature
    )
    reasoning_text, _ = _extract_think_content(response)
    cleaned = sanitize_json_string(response)
    result = robust_json_parse(
        cleaned,
        default=_build_default_dimension(),
    )
    if reasoning_text:
        result["reasoning_process"] = reasoning_text
    return result


async def _timed_dimension_analysis(
    case_text: str,
    system_prompt: str,
    dimension_name: str,
    user_prompt: str | None = None,
    temperature: float = AnalysisConfig.OLLAMA_DEFAULT_TEMPERATURE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """带性能计时的单维度分析包装器.

    在 _single_dimension_analysis 基础上增加精确的性能计时
    和详细的异常信息记录。

    Args:
        case_text: 案件事实文本（当 user_prompt 为 None 时作为用户消息）
        system_prompt: 当前维度的系统提示词
        dimension_name: 维度名称
        user_prompt: 自定义用户消息，为 None 时使用 case_text
        temperature: 生成温度

    Returns:
        tuple: (维度分析结果字典, 执行元数据字典)
    """
    start_time: float = time.perf_counter()
    start_ts: str = datetime.now(UTC).isoformat()
    status: str = "success"
    error_info: dict[str, str] = {}

    try:
        result: dict[str, Any] = await _single_dimension_analysis(
            case_text, system_prompt, dimension_name,
            user_prompt=user_prompt, temperature=temperature,
        )
    except Exception as exc:  # noqa: BLE001
        result = _build_default_dimension()
        status = "failed"
        error_info = {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "error_time": datetime.now(UTC).isoformat(),
        }
        logger.error(
            f"{dimension_name} 分析异常: "
            f"类型={type(exc).__name__}, "
            f"错误={exc}, "
            f"时间={error_info['error_time']}"
        )

    end_time: float = time.perf_counter()
    duration_ms: float = round((end_time - start_time) * 1000, 2)

    timing: dict[str, Any] = {
        "status": status,
        "duration_ms": duration_ms,
        "start_time": start_ts,
        "end_time": datetime.now(UTC).isoformat(),
        **error_info,
    }
    logger.info(
        f"{dimension_name} 执行完成: 状态={status}, 耗时={duration_ms}ms"
    )
    return result, timing


def _build_prior_analysis_context(
    dim1_result: dict[str, Any],
    dim2_result: dict[str, Any],
) -> str:
    """将维度1（事实审查）和维度2（模式匹配）的结果摘要为维度3可用的上下文.

    Args:
        dim1_result: 维度1的事实审查分析结果
        dim2_result: 维度2的模式匹配分析结果

    Returns:
        str: 格式化的前置分析文本摘要（不超过500字）
    """
    parts: list[str] = []

    dim1_score: float = dim1_result.get("score", _DEFAULT_SCORE)
    dim1_reasoning: str = dim1_result.get("reasoning", "无分析结果")
    dim1_indicators: list[str] = dim1_result.get("key_indicators", [])

    if dim1_reasoning == "自动分析结果" and dim1_score == _DEFAULT_SCORE:
        parts.append("【事实审查维度分析失败，该维度无法提供有效分析，请独立判断】")
    else:
        parts.append("【事实审查维度结论】")
        parts.append(f"评分：{dim1_score}/10")
        if dim1_indicators:
            parts.append(f"关键指标：{'、'.join(dim1_indicators[:5])}")
        parts.append(f"分析摘要：{dim1_reasoning[:200]}")

    dim2_score: float = dim2_result.get("score", _DEFAULT_SCORE)
    dim2_reasoning: str = dim2_result.get("reasoning", "无分析结果")
    dim2_pattern: str = dim2_result.get("pattern_match", "无匹配结果")

    if dim2_reasoning == "自动分析结果" and dim2_score == _DEFAULT_SCORE:
        parts.append("【模式匹配维度分析失败，该维度无法提供有效分析，请独立判断】")
    else:
        parts.append("")
        parts.append("【模式匹配维度结论】")
        parts.append(f"评分：{dim2_score}/10")
        parts.append(f"模式匹配：{dim2_pattern}")
        parts.append(f"分析摘要：{dim2_reasoning[:200]}")

    context: str = "\n".join(parts)

    if len(context) > _MAX_CONTEXT_LENGTH:
        context = context[:_MAX_CONTEXT_LENGTH - 3] + "..."

    return context


async def multi_dimension_analysis(
    case_text: str,
    mode: str = "auto",  # noqa: ARG001
    temperature: float = AnalysisConfig.OLLAMA_DEFAULT_TEMPERATURE,
    legal_knowledge: str = "",
) -> AnalysisResult:
    """多维度分析（适用于复杂案件）.

    采用两阶段推理策略：
    第一阶段：并行执行维度1（事实审查）和维度2（模式匹配）
    第二阶段：将维度1和维度2的结果摘要注入维度3（矛盾分析），
              使其能基于前置分析结果进行更有依据的矛盾识别。

    各维度异常隔离，互不干扰。任一维度失败时自动使用默认值降级。
    同时记录各维度的执行状态、耗时和异常详情。

    Args:
        case_text: 案件事实文本
        mode: 分析模式
        temperature: 生成温度
        legal_knowledge: 注入的检索知识（可选）

    Returns:
        AnalysisResult: 包含三维度分析结果、量刑建议和各维度执行元数据的字典
    """
    logger.info(f"使用多维度两阶段分析模式, temperature={temperature}")

    dim1_prompt: str = DIMENSION1_PROMPT.replace("{legal_knowledge}", legal_knowledge)
    dim2_prompt: str = DIMENSION2_PROMPT.replace("{legal_knowledge}", "")

    # ------------------------------------------------------------------
    # 第一阶段：并行执行维度1（事实审查）和维度2（模式匹配）
    # ------------------------------------------------------------------
    phase1_dim_names: list[str] = ["dimension1", "dimension2"]
    phase1_results = await asyncio.gather(
        _timed_dimension_analysis(case_text, dim1_prompt, "维度1", temperature=temperature),
        _timed_dimension_analysis(case_text, dim2_prompt, "维度2", temperature=temperature),
        return_exceptions=True,
    )

    dimension_results: dict[str, dict[str, Any]] = {}
    dimension_meta: dict[str, dict[str, Any]] = {}

    for dim_name, gather_result in zip(
        phase1_dim_names, phase1_results, strict=True
    ):
        if isinstance(gather_result, BaseException):
            error_time: str = datetime.now(UTC).isoformat()
            dimension_results[dim_name] = _build_default_dimension()
            dimension_meta[dim_name] = {
                "status": "failed",
                "duration_ms": 0.0,
                "start_time": "",
                "end_time": error_time,
                "error": str(gather_result),
                "error_type": type(gather_result).__name__,
                "error_time": error_time,
            }
            logger.error(
                f"{dim_name} 分析异常: "
                f"类型={type(gather_result).__name__}, "
                f"错误={gather_result}, "
                f"时间={error_time}"
            )
        else:
            dim_result, timing = gather_result
            dimension_results[dim_name] = dim_result
            dimension_meta[dim_name] = timing

    # ------------------------------------------------------------------
    # 构建前置分析上下文（供维度3使用）
    # ------------------------------------------------------------------
    context: str = _build_prior_analysis_context(
        dimension_results.get("dimension1", _build_default_dimension()),
        dimension_results.get("dimension2", _build_default_dimension()),
    )

    # ------------------------------------------------------------------
    # 第二阶段：串行执行维度3（矛盾分析），注入前置分析结果
    # ------------------------------------------------------------------
    enriched_prompt: str = DIMENSION3_PROMPT.replace("{legal_knowledge}", "").format(
        prior_analysis=context,
        case_text=case_text,
    )
    dim3_result: dict[str, Any]
    dim3_timing: dict[str, Any]
    dim3_result, dim3_timing = await _timed_dimension_analysis(
        case_text, enriched_prompt, "维度3", temperature=temperature,
    )
    dimension_results["dimension3"] = dim3_result
    dimension_meta["dimension3"] = dim3_timing

    ground_truth: dict[str, Any] = {
        "dimension1": dimension_results["dimension1"],
        "dimension2": dimension_results["dimension2"],
        "dimension3": dimension_results["dimension3"],
    }
    dim1: dict[str, Any] = dimension_results["dimension1"]
    key_indicators: list[str] = dim1.get("key_indicators", ["未知"])
    subjective_knowledge: str = key_indicators[0] if key_indicators else "未知"
    sentence_suggestion: str = dim1.get("sentence_suggestion", "待定")

    return {
        "ground_truth_analysis": ground_truth,
        "subjective_knowledge": subjective_knowledge,
        "sentence": sentence_suggestion,
        "fallback": False,
        "timestamp": datetime.now(UTC).isoformat(),
        "dimension_meta": dimension_meta,
    }


async def self_consistency_analysis(  # noqa: PLR0912, PLR0915
    case_text: str,
    mode: str = "auto",
    n_samples: int = 3,
    sample_temperature: float = 0.5,
    legal_knowledge: str = "",
) -> AnalysisResult:
    """Self-Consistency 多次采样验证分析.

    通过多次独立采样 LLM 分析结果，计算评分中位数和一致性指标，
    有效降低单次推理的随机偏差，尤其适用于边界案例。

    流程：
    1. 循环调用 n_samples 次分析（根据 mode 选择单通道或多维度）
       - 每次使用 sample_temperature 而非默认温度以引入多样性
    2. 收集所有采样结果
    3. 对每个维度的 score 取中位数作为最终分数
    4. 计算每个维度的评分一致性（标准差）
    5. 合并 reasoning 文本（选取最接近中位数的采样结果）
    6. 计算整体置信度（基于三个维度的一致性综合评估）

    Args:
        case_text: 案件事实文本
        mode: 分析模式
        n_samples: 采样次数
        sample_temperature: 采样温度（高于默认值以引入多样性）
        legal_knowledge: 注入的检索知识（可选）

    Returns:
        AnalysisResult: 包含 SC 置信度指标的分析结果
    """
    logger.info(
        f"Self-Consistency 分析: samples={n_samples}, "
        f"temperature={sample_temperature}, mode={mode}"
    )

    dim_names: list[str] = ["dimension1", "dimension2", "dimension3"]
    all_results: list[AnalysisResult] = []
    sample_scores_list: list[dict[str, Any]] = []

    for i in range(n_samples):
        logger.info(f"Self-Consistency 采样 {i + 1}/{n_samples}")
        try:
            if mode == "single":
                result = await single_pass_analysis(
                    case_text, mode=mode, temperature=sample_temperature,
                    legal_knowledge=legal_knowledge,
                )
            elif mode == "multi":
                result = await multi_dimension_analysis(
                    case_text, mode=mode, temperature=sample_temperature,
                    legal_knowledge=legal_knowledge,
                )
            else:
                complexity: ComplexityLevel = classify_complexity(case_text)
                if complexity == "simple":
                    result = await single_pass_analysis(
                        case_text, mode=mode, temperature=sample_temperature,
                        legal_knowledge=legal_knowledge,
                    )
                else:
                    result = await multi_dimension_analysis(
                        case_text, mode=mode, temperature=sample_temperature,
                        legal_knowledge=legal_knowledge,
                    )

            all_results.append(result)

            gta = result.get("ground_truth_analysis", {}) or {}
            sample_scores = {}
            for dim in dim_names:
                dim_data = gta.get(dim, {}) or {}
                sample_scores[dim] = dim_data.get("score", 5.0)
            sample_scores_list.append(sample_scores)

        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"Self-Consistency 采样 {i + 1} 失败: {exc}"
            )
            continue

    if not all_results:
        logger.warning("Self-Consistency 所有采样均失败，使用默认降级结果")
        result = _build_default_analysis_result()
        result["confidence"] = 0.0
        result["confidence_details"] = {}
        result["num_samples"] = 0
        result["sample_scores"] = []
        return result

    actual_samples = len(all_results)

    dim_scores: dict[str, list[float]] = {d: [] for d in dim_names}
    dim_reasonings: dict[str, list[str]] = {d: [] for d in dim_names}

    for sample in sample_scores_list:
        for dim in dim_names:
            score = sample.get(dim, 5.0)
            dim_scores[dim].append(score)

    for result in all_results:
        gta = result.get("ground_truth_analysis", {}) or {}
        for dim in dim_names:
            dim_data = gta.get(dim, {}) or {}
            reasoning = dim_data.get("reasoning", "")
            dim_reasonings[dim].append(reasoning)

    final_scores: dict[str, float] = {}
    dim_std: dict[str, float] = {}
    dim_confidence: dict[str, float] = {}
    confidence_details: dict[str, Any] = {}

    for dim in dim_names:
        scores = dim_scores[dim]
        if scores:
            final_scores[dim] = statistics.median(scores)
        else:
            final_scores[dim] = 5.0

        if len(scores) >= _MIN_SAMPLES_FOR_STDEV:
            dim_std[dim] = statistics.stdev(scores)
        else:
            dim_std[dim] = 0.0

        max_possible_std = 5.0
        conf = max(0.0, 1.0 - dim_std[dim] / max_possible_std)
        dim_confidence[dim] = round(conf, 4)

        confidence_details[dim] = {
            "scores": scores,
            "median": round(final_scores[dim], 2),
            "mean": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "std_dev": round(dim_std[dim], 4),
            "min": round(min(scores), 2) if scores else 0.0,
            "max": round(max(scores), 2) if scores else 0.0,
            "confidence": dim_confidence[dim],
        }

    overall_confidence = round(
        sum(dim_confidence.values()) / len(dim_confidence), 4
    )

    best_result = all_results[0]
    best_deviation = float("inf")
    for result in all_results:
        gta = result.get("ground_truth_analysis", {}) or {}
        deviation = 0.0
        for dim in dim_names:
            dim_data = gta.get(dim, {}) or {}
            score = dim_data.get("score", 5.0)
            deviation += abs(score - final_scores[dim])
        if deviation < best_deviation:
            best_deviation = deviation
            best_result = result

    final_result: AnalysisResult = dict(best_result)
    gta = final_result.get("ground_truth_analysis")
    if gta:
        for dim in dim_names:
            if dim in gta:
                dim_copy = dict(gta[dim])
                dim_copy["score"] = final_scores[dim]
                gta[dim] = dim_copy

    final_result["confidence"] = overall_confidence
    final_result["confidence_details"] = confidence_details
    final_result["num_samples"] = actual_samples
    final_result["sample_scores"] = sample_scores_list

    logger.info(
        f"Self-Consistency 完成: samples={actual_samples}, "
        f"confidence={overall_confidence}"
    )

    return final_result
