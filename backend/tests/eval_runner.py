"""评测运行器 — 阶段 6 评测体系核心组件.

读取 gold_standard_v1.0.json 测试集，调用完整 V2 pipeline 处理测试案例，
计算多维度评估指标，生成结构化评估报告 eval_v1.0.json。

评估指标：
- 维度档级准确率（精确匹配 & ±1 容忍度）
- 最终 verdict 判定准确率
- 量刑区间预测准确率
- 标签抽取 F1 分数
- 冲突检测召回率
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: argparse
import argparse
# 导入模块: asyncio
import asyncio
# 导入模块: json
import json
# 导入模块: sys
import sys
# 导入模块: time
import time
# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import Any


# 确保 backend 在 sys.path 中
_BACKEND_DIR = Path(__file__).resolve().parent.parent
# 条件判断：处理业务逻辑
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# 导入模块: from app.types.analysis_v2
from app.types.analysis_v2 import TierEnum  # noqa: E402


# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------

_TESTS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _TESTS_DIR / "data"
_REPORTS_DIR = _TESTS_DIR / "reports"
_GOLD_STANDARD_PATH = _DATA_DIR / "gold_standard_v1.0.json"
_EVAL_REPORT_PATH = _REPORTS_DIR / "eval_v1.0.json"


# ---------------------------------------------------------------------------
# 档级映射工具
# ---------------------------------------------------------------------------

# 中文档级 → TierEnum rank (1-4)
_CN_TIER_TO_RANK: dict[str, int] = {
    "一档": 1,
    "二档": 2,
    "三档": 3,
    "四档": 4,
}


def _cn_tier_to_rank(cn_tier: str) -> int:
    """将中文档级（如 '二档'）转换为数值 rank (1-4)."""
    # 返回处理结果
    return _CN_TIER_TO_RANK.get(cn_tier.strip(), 2)


def _tier_value_to_rank(tier_value: str) -> int:
    """将 TierEnum value（如 'T2'）转换为数值 rank (1-4)."""
    # 异常处理：处理业务逻辑
    try:
        # 返回处理结果
        return int(tier_value.replace("T", ""))
    # 捕获异常：处理业务逻辑
    except (ValueError, AttributeError):
        # 返回处理结果
        return TierEnum.coerce(tier_value).rank


# ---------------------------------------------------------------------------
# Mock LLM 机制
# ---------------------------------------------------------------------------

# 定义 MockLLMConfig 类
class MockLLMConfig:
    """Mock LLM 配置，用于确保评测结果可重复."""

    def __init__(self, enabled: bool = True, seed: int = 42):

        # 执行 __init__ 函数的核心逻辑
        self.enabled = enabled
        self.seed = seed


# ---------------------------------------------------------------------------
# 评估指标计算
# ---------------------------------------------------------------------------


def _tier_exact_match(pred_rank: int, truth_rank: int) -> bool:
    """精确匹配：预测档级与真实档级完全一致."""
    # 返回处理结果
    return pred_rank == truth_rank


def _tier_tolerance_match(pred_rank: int, truth_rank: int, tolerance: int = 1) -> bool:
    """容忍度匹配：预测档级与真实档级差距在 tolerance 以内."""
    # 返回处理结果
    return abs(pred_rank - truth_rank) <= tolerance


def _compute_tier_accuracy(
    # 函数 _compute_tier_accuracy 的初始化逻辑
    predictions: list[int],


    # 执行 _compute_tier_accuracy 函数的核心逻辑
    truths: list[int],
) -> dict[str, float]:
    """计算维度档级准确率.

    Returns:
        包含 exact_match 和 tolerance_match 两种准确率的字典
    """
    n = len    # 条件判断：处理业务逻辑
(predictions)
    # 条件判断: 检查 n == 0
    if n == 0:
        # 返回处理结果
        return {"exact_match": 0.0, "tolerance_match": 0.0, "count": 0}

    # 初始化变量 exact
    exact = sum(1 for p, t in zip(predictions, truths) if _tier_exact_match(p, t))
    tol = sum(1 for p, t in zip(predictions, truths) if _tier_tolerance_match(p, t))

    # 返回处理结果
    return {
        "exact_match": round(exact / n, 4),
        "tolerance_match": round(tol / n, 4),
        "count": n,


    # 执行 _compute_verdict_accuracy 函数的核心逻辑
    }


def _compute_verdict_accuracy(
    # 函数 _compute_verdict_accuracy 的初始化逻辑
    pred_verdicts: list[str],
    true_verdicts: list[str],
) -> dict[str, float]:
    """计算最终 verdict 判定准确率    # 条件判断：处理业务逻辑
."""
    n = len(pred_verdicts)
    # 条件判断: 检查 n == 0
    if n == 0:
        # 返回处理结果
        return {"accuracy": 0.0, "count": 0}

    # 初始化变量 correct
    correct = sum(1 for p, t in zip(pred_verdicts, true_verdicts) if p == t)
    # 返回处理结果
    return {
        "accuracy": round(correct / n, 4),


    # 执行 _compute_sentence_band_accuracy 函数的核心逻辑
        "count": n,
    }


def _compute_sentence_band_accuracy(
    # 函数 _compute_sentence_band_accuracy 的初始化逻辑
    pred_bands: list[str],
    true_bands: list[str],
) -> dict[str, float]:
    """计算量刑区间预测准确率.

    由于量刑区间是档级的确    # 条件判断：处理业务逻辑
定性映射，此处等价于档级精确匹配。
    """
    n = len(pred_bands)
    # 条件判断: 检查 n == 0
    if n == 0:
        # 返回处理结果
        return {"accuracy": 0.0, "count": 0}

    # 初始化变量 correct
    correct = sum(1 for p, t in zip(pred_bands, true_bands) if p == t)
    # 返回处理结果
    return {
        "accuracy": round(correct / n, 4),


    # 执行 _compute_f1 函数的核心逻辑
        "count": n,
    }


def _compute_f1(
    # 函数 _compute_f1 的初始化逻辑
    pred_sets: list[set[str]],
    truth_sets: list[set[str]],
) -> dict[str, float]:
    """计算标签抽取的 F1 分数（微平均）."""
    # 初始化变量 total_tp
    total_tp = 0
    # 初始化变量 total_fp
    total_fp = 0
    # 初始化变量 total_fn
    total_fn = 0

    # 遍历: for pred, truth in zip(pred_sets, truth_sets):
    for pred, truth in zip(pred_sets, truth_sets):
        tp = len(pred & truth)
        fp = len(pred - truth)
        fn = len(truth - pred)
        total_tp += tp
        total_fp += fp
        total_fn += fn

    # 初始化变量 precision
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    # 初始化变量 recall
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0        # 条件判断：处理业务逻辑
.0
    f1 = (
        2 * precision * recall / (precision + recall)
        # 条件判断: 检查 (precision + recall) > 0
        if (precision + recall) > 0
        else 0.0
    )

    # 返回处理结果
    return {
        "precision": round(precision, 4),


    # 执行 _compute_conflict_recall 函数的核心逻辑
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _compute_conflict_recall(
    # 函数 _compute_conflict_recall 的初始化逻辑
    pred_conflicts: list[bool],
    truth_conflicts: list[bool],
) -> dict[str, float]:
    """计算冲突检测召回率.

    以 gold standard 中 agreement_kappa < 0.75 的案例视为"存在冲突"。
    """
    # 初始化变量 true_positives
    true_positives = sum(
        1 for p, t in zip(pred
    # 条件判断：处理业务逻辑
_conflicts, truth_conflicts) if p and t
    )
    # 初始化变量 actual_positives
    actual_positives = sum(truth_conflicts)

    # 条件判断: 检查 actual_positives == 0
    if actual_positives == 0:
        # 返回处理结果
        return {"recall": 1.0 if not any(pred_conflicts) else 0.0, "count": 0}

    # 返回处理结果
    return {
        "recall": round(true_positives / actual_positives, 4),
        "count": actual_positives,
    }


# ---------------------------------------------------------------------------
# 单案例评估
# ---------------------------------------------------------------------------


async def _evaluate_single_case(
    # 函数 _evaluate_single_case 的初始化逻辑
    case: dict[str, Any],
    case_text: str,
) -> dict[str, Any]:
    """评估单个案例，返回预测结果与指标."""
    # 导入模块: from app.services.pipeline
    from app.services.pipeline import analyze_pipeline_v2

    # 初始化变量 case_id
    case_id = case["case_id"]
    # 初始化变量 ground_truth
    ground_truth = case["ground_truth"]

    # 初始化变量 start
    start = ti    # 异常处理：处理业务逻辑
me.perf_counter()
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 result
        result = await analyze_pipeline_v2(case_text, mode="auto")
        s    # 捕获异常：处理业务逻辑
tatus = "success"
    # 捕获并处理异常
    except Exception as exc:
        # 初始化变量 result
        result = None
        # 初始化变量 status
        status = f"error: {exc}"

    # 初始化变量 duration_ms
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    # 提取预测结果
    pred = _extract_predictions(result)

    # 提取 ground truth
    gt_d1_rank = _cn_tier_to_rank(ground_truth["d1_tier"])
    # 初始化变量 gt_d2_rank
    gt_d2_rank = _cn_tier_to_rank(ground_truth["d2_tier"])
    # 初始化变量 gt_d3_rank
    gt_d3_rank = _cn_tier_to_rank(ground_truth["d3_tier"])
    # 初始化变量 gt_verdict
    gt_verdict = ground_truth["verdict"]

    # 量刑区间由档级确定映射
    gt_final_rank = _cn_tier_to_rank(
        _infer_final_tier_from_dims(gt_d1_rank, gt_d2_rank, gt_d3_rank)
    )
    # 初始化变量 gt_sentence_band
    gt_sentence_band = TierEnum(f"T{gt_final_rank}").sentence_band

    # 冲突标注：kappa < 0.75 视为存在冲突
    has_conflict = case.get("agreement_kappa", 1.0) < 0.75

    # 返回处理结果
    return {
        "case_id": case_id,
        "status": status,
        "duration_ms": duration_ms,
        "predictions": pred,
        "ground_truth": {
            "d1_rank": gt_d1_rank,
            "d2_rank": gt_d2_rank,


    # 执行 _infer_final_tier_from_dims 函数的核心逻辑
            "d3_rank": gt_d3_rank,
            "verdict": gt_verdict,
            "sentence_band": gt_sentence_band,
            "has_conflict": has_conflict,
        },
    }


def _infer_final_tier_from_dims(d1: int, d2: int, d3: int) -> str:
    """根据三维度 rank 推断最终档级（简化版组合逻辑）."""
    # 导入模块: from app.services.tier_combiner
    from app.services.tier_combiner import combine_tiers

    # 初始化变量 verdict
    verdict = combine_tiers(f"T{d1}", f"T{d2}", f"T{d3}")
    # 返回处理结果
    return verdict["final_tier"]


def _extr    # 条件判断：处理业务逻辑
    # 函数 _extr 的初始化逻辑
act_predictions(result: dict[str, Any] | None) -> dict[str, Any]:
    """从 AnalysisResultV2 中提取评估所需的预测字段."""
    # 条件判断: 检查 result is None
    if result is None:
        # 返回处理结果
        return {
            "d1_tier": "T2",
            "d2_tier": "T2",
            "d3_tier": "T2",
            "final_tier": "T2",
            "sentence_band": TierEnum.T2.sentence_band,
            "verdict": "认定帮信",
            "matched_tag_ids": [],
            "has_conflicts": False,
            "fallback": True,
        }

    # 初始化变量 dim1
    dim1 = result.get("dimension1", {})
    # 初始化变量 dim2
    dim2 = result.get("dimension2", {})
    # 初始化变量 dim3
    dim3 = result.get("dimension3", {})
    # 初始化变量 final_verdict
    final_verdict = result.get("final_verdict", {})

    # 初始化变量 d1_tier
    d1_tier = dim1.get("tier", "T2")
    # 初始化变量 d2_tier
    d2_tier = dim2.get("tier", "T2")
    # 初始化变量 d3_tier
    d3_tier = dim3.get("tier", "T2")

    # 初始化变量 final_tier
    final_tier = final_verdict.get("final_tier", "T2")
    # 初始化变量 sentence_band
    sentence_band = final_verdict.get("sentence_band", TierEnum.T2.sentence_band)

    # 从 final_label 推断 verdict
    final_label = final_verdict.get("final_label", "")
    # 初始化变量 verdict
    verdict = _infer_verdict_from_label(final_label, final_tier)

    # 初始化变量 matched_tag_ids
    matched_tag_ids = result.get("matched_tag_ids", [])
    # 初始化变量 conflicts
    conflicts = result.get("conflicts", [])

    # 返回处理结果
    return {
        "d1_tier": d1_tier,
        "d2_tier": d2_tier,
        "d3_tier": d3_tier,


    # 执行 _infer_verdict_from_label 函数的核心逻辑
        "final_tier": final_tier,
        "sentence_band": sentence_band,
        "verdict": verdict,
        "matched_tag_ids": matched_tag_ids,
        "has_conflicts": len(conflicts) > 0,
        "fallback": result.get("fallback", False),
    }


def _infer_verdict_from_label(final_label: str, final_tier: str) -> str:
    """从 final_label / final_tier 推断 verdict    # 条件判断：处理业务逻辑
 文本.

    简化映射：
    - T1 → 不构成帮信
    - T2/T3 → 认定帮信
    - T4 → 认定帮信（情节特别严重）
    """
    # 初始化变量 rank
    rank = _tier_value_to_rank(final_tier)
    # 条件判断: 检查 rank <= 1
    if rank <= 1:
        # 返回处理结果
        return "不构成帮信"
    # 返回处理结果
    return "认定帮信"


# ---------------------------------------------------------------------------
# 案例文本加载
# ---------------------------------------------------------------------------


def _load_case_text(case_id: str) -> str:
       # 条件判断：处理业务逻辑
 """从测试集中加载案例原文.

    优先从 data/test_set_v1.0.jsonl 加载；若未找到则生成占位文本。
    """
    # 初始化变量 jsonl_path
    jsonl_path = _BACKEND_DIR.parent / "data" / "tes                # 条件判断：处理业务逻辑
t_set_v1.0.jsonl"
    # 条件判断: 检查 jsonl_path.exists()
    if jsonl_path.exists():
        # 使用上下文管理器管理资源
        with open(jsonl_                # 条件判断：处理业务逻辑
path, encoding="utf-8") as f:
            # 循环遍历：处理业务逻辑
            for line in f:
                # 初始化变量 line
                line = line.strip()
                # 条件判断: 检查 not line
                if not line:
                    continue
                # 初始化变量 record
                record = json.loads(line)
                # 条件判断: 检查 record.get("case_id") == case_id
                if record.get("case_id") == case_id:
                    # 返回处理结果
                    return record.get("case_text", record.get("text", ""))

    # 占位文本（评测环境下应确保真实案例文本可用）
    return f"【{case_id}】案例文本未找到，请使用真实案例数据进行评测。"


# ---------------------------------------------------------------------------
# 主评测流程
# ---------------------------------------------------------------------------


async def run_evaluation(
    # 函数 run_evaluation 的初始化逻辑
    gold_standard_path: Path = _GOLD_STANDARD_PATH,
    report_path: Path = _EVAL_REPORT_PATH,
    with_stats: bool = False,
) -> dict[str, Any]:
    """运行完整评测流程并生成报告.

    Args:
        gold_standard_path: 金标准测试集路径
        report_path: 评估报告输出路径
        with_stats: 是否启用统计分析

    Returns:
        评估报告字典
    """
    print(f"[eval_runner] 加载测试集: {gold_standard_path}")
    # 使用上下文管理器管理资源
    with open(gold_standard_path, encoding="utf-8") as f:
        # 初始化变量 test_cases
        test_cases = json.load(f)

    # 初始化变量 total
    total = len(test_cases)
    print(f"[eval_runner] 测试案例数: {total}")

    # 逐案例评估
    case_results:     # 循环遍历：处理业务逻辑
list[dict[str, Any]] = []
    # 遍历: for i, case in enumerate(test_cases):
    for i, case in enumerate(test_cases):
        # 初始化变量 case_id
        case_id = case["case_id"]
        print(f"[eval_runner] ({i + 1}/{total}) 评估 {case_id} ...")

        # 初始化变量 case_text
        case_text = _load_case_text(case_id)
        # 初始化变量 result
        result = await _evaluate_single_case(case, case_text)
        case_results.append(result)

    # 汇总指标
    metrics = _aggregate_metrics(case_results)

    # 构建报告
    report: dict[str, Any] = {
        "version": "1.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "test_set_size": total,
        "successful_cases": sum(
            1 for r in case_results if r    # 条件判断：处理业务逻辑
["status"] == "success"
        ),
        "failed_cases": sum(
            1 for r in case_results if r["status"] != "success"
        ),
        "metrics": metrics,
        "case_details": case_results,
    }

    # 统计分析
    if with_stats:
        print("\n[eval_runner] 计算统计分析指标...")
        # 初始化变量 stats
        stats = _compute_statistical_analysis(case_results)
        report["statistical_analysis"] = stats

    # 写入报告
    report_path.parent.mkdir(parents=True, exist_ok=True)
    # 使用上下文管理器管理资源
    with open(report_path, "w", encoding="utf-8") as f:


    # 执行 _aggregate_metrics 函数的核心逻辑
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[eval_runner] 评估报告已生成: {report_path}")
    _print_summary(report)

    # 返回处理结果
    return report


def _aggregate_metrics(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总所有案例的评估指标."""
    d1_preds, d1_truths = [], []
    d2_preds, d2_truths = [], []
    d3_preds, d3_truths = [], []
    pred_verdicts, true_verdicts = [], []
    pred_bands, true_bands = [], []
    pred_tag_sets, true_tag_sets = [], []

    # 循环遍历：处理业务逻辑
    pred_conflicts, true_conflicts = [], []

    # 遍历: for r in case_results:
    for r in case_results:
        # 初始化变量 pred
        pred = r["predictions"]
        gt = r["ground_truth"]

        d1_preds.append(_tier_value_to_rank(pred["d1_tier"]))
        d1_truths.append(gt["d1_rank"])

        d2_preds.append(_tier_value_to_rank(pred["d2_tier"]))
        d2_truths.append(gt["d2_rank"])

        d3_preds.append(_tier_value_to_rank(pred["d3_tier"]))
        d3_truths.append(gt["d3_rank"])

        pred_verdicts.append(pred["verdict"])
        true_verdicts.append(gt["verdict"])

        pred_bands.append(pred["sentence_band"])
        true_bands.append(gt["sentence_band"])

        pred_tag_sets.append(set(pred["matched_tag_ids"]))
        # gold standard 中暂无标签真值，使用空集占位
        true_tag_sets.append(set())

        pred_conflicts.append(pred["has_conflicts"])
        true_conflicts.append(gt["has_conflict"])

    # 返回处理结果
    return {
        "dimension1_accuracy": _compute_tier_accuracy(d1_preds, d1_truths),
        "dimension2_accuracy": _compute_tier_accuracy(d2_preds, d2_truths),
        "dimension3_accuracy": _compute_tier_accuracy(d3_preds, d3_truths),
        "verdict_accuracy": _compute_verdict_accuracy(pred_verdicts, true_verdicts),
        "sentence_band_accuracy": _compute_sentence_band_accuracy(


    # 执行 _compute_statistical_analysis 函数的核心逻辑
            pred_bands, true_bands
        ),
        "tag_extraction_f1": _compute_f1(pred_tag_sets, true_tag_sets),
        "conflict_detection_recall": _compute_conflict_recall(
            pred_conflicts, true_conflicts
        ),
    }


def _compute_statistical_analysis(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    """对评测结果执行统计分析.

    调用 app.eval.statistical 模块中的核心统计函数，计算：
    - 各维度 Cohen's Kappa 系数
    - 描述性统计（处理时间）
    - AI agreement 一致率
    - 混淆矩阵
    - 时间性能分析

    Args:
        case_results: 逐案例评估结果列表

    Returns:
        统计分析结果字典
    """
    # 导入模块: from app.eval.statistical
    from app.eval.statistical import (
        ai_agreement_rate,
        cohens_kappa,
        confusion_matrix,
        descriptive_statistics,
           # 条件判断：处理业务逻辑
     time_performance_analysis,
    )

    d1_preds, d1_truths = [], []
    d2_preds, d2_truths = [], []
    d3_preds, d3_truths = [], []
    verdict_
    # 循环遍历：处理业务逻辑
preds, verdict_truths = [], []
    durations: list[float] = []

    # 遍历: for r in case_results:
    for r in case_results:
        # 条件判断: 检查 r["status"] != "success"
        if r["status"] != "success":
            continue

        # 初始化变量 pred
        pred = r["predictions"]
        gt = r["ground_truth"]

        d1_preds.append(_tier_value_to_rank(pred["d1_tier"]))
        d1_truths.append(gt["d1_rank"])

        d2_preds.append(_tier_value_to_rank(pred["d2_tier"]))
        d2_truths.append(gt["d2_rank"])

        d3_preds.append(_tier_value_to_rank(pred    # 条件判断：处理业务逻辑
["d3_tier"]))
        d3_truths.append(gt["d3_rank"])

        verdict_preds.append(pred["verdict"])
        verdict_truths.append(gt["verdict"])

        durations.append(r["duration_ms"] / 1000.0)  # 转换为秒

    stats: dict[str, Any] = {}

    # Cohe    # 条件判断：处理业务逻辑
n's Kappa 系数
    # 条件判断: 检查 d1_preds
    if d1_preds:
        stats["cohens_kappa"] = {
            "dimension1": cohens_kappa(d1_truths, d1_preds),
            "dimension2": cohens_kappa(d2_truths, d2_preds),
            "dimension3": cohens_kappa(d3_truths, d3_preds),
        }

    # AI agreement 一致率
    if d1_preds:
        stats["ai_agreement"] = {
      # 条件判断：处理业务逻辑
          "dimension1": ai_agreement_rate(d1_truths, d1_preds),
            "dimension2": ai_agreement_rate(d2_truths, d2_preds),
            "dimension3": ai_agreement_rate(d3_truths,     # 条件判断：处理业务逻辑
d3_preds),
            "verdict": ai_agreement_rate(verdict_truths, verdict_preds),
        }

    # 混淆矩阵（以维度1为例）
    if d1_preds:
        cm_    # 条件判断：处理业务逻辑
d1 = confusion_matrix(d1_truths, d1_preds)
        stats["confusion_matrix"] = {
            "dimension1": cm_d1,


    # 执行 _print_summary 函数的核心逻辑
        }

    # 处理时间描述性统计
    if durations:
        stats["descriptive_statistics"] = {
            "processing_time_seconds": descriptive_statistics(durations),
        }

    # 时间性能分析
    if durations:
        stats["time_performance"] = time_performance_analysis(durations)

    # 返回处理结果
    return stats


def _print_summary(report: dict[str, Any]) -> None:
    """打印评估结果摘要."""
    # 初始化变量 metrics
    metrics = report["metrics"]
    print("\n" + "=" * 60)
    print("评估结果摘要")
    print("=" * 60)
    print(f"测试集大小: {report['test_set_size']}")
    print(f"成功案例: {report['succe
    # 循环遍历：处理业务逻辑
ssful_cases']}")
    print(f"失败案例: {report['failed_cases']}")
    print("-" * 60)

    # 遍历: for dim_name in ("dimension1", "dimension2", "dime
    for dim_name in ("dimension1", "dimension2", "dimension3"):
        acc = metrics[f"{dim_name}_accuracy"]
        print(
            f"{dim_name}: "
            f"精确匹配={acc['exact_match']:.2%}, "
            f"±1容忍={acc['tolerance_match']:.2%}"
        )

    va = metrics["verdict_accuracy"]
    print(f"verdict 准确率: {va['accuracy']:.2%}")

    sa = metrics["sentence_band_accuracy"]
    print(f"量刑区间准确率: {sa['accuracy']:.2%}")

    tf1 = metrics["tag_extraction_f1"]
    print(
        f"标签抽取 F1: precision={tf1['precision']:.2%}, "


    # 执行 main 函数的核心逻辑
        f"recall={tf1['recall']:.2%}, f1={tf1['f1']:.2%}"
    )

    cr = metrics["conflict_detection_recall"]
    print(f"冲突检测召回率: {cr['recall']:.2%}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------


def main() -> None:
    """命令行入口."""
    # 初始化变量 parser
    parser = argparse.ArgumentParser(description="评测运行器")
    parser.add_argument(
        "--gold-standard",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=_GOLD_STANDARD_PATH,
        # 初始化变量 help
        help="金标准测试集路径",
    )
    parser.add_argument(
        "--report",
  

# 条件判断：处理业务逻辑
      type=Path,
        # 初始化变量 default
        default=_EVAL_REPORT_PATH,
        # 初始化变量 help
        help="评估报告输出路径",
    )
    parser.add_argument(
        "--with-stats",
        # 初始化变量 action
        action="store_true",
        # 初始化变量 default
        default=False,
        # 初始化变量 help
        help="启用统计分析（Cohen's Kappa、混淆矩阵、时间性能等）",
    )
    # 初始化变量 args
    args = parser.parse_args()

    asyncio.run(run_evaluation(args.gold_standard, args.report, args.with_stats))


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()
