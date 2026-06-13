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

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


# 确保 backend 在 sys.path 中
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

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
    return _CN_TIER_TO_RANK.get(cn_tier.strip(), 2)


def _tier_value_to_rank(tier_value: str) -> int:
    """将 TierEnum value（如 'T2'）转换为数值 rank (1-4)."""
    try:
        return int(tier_value.replace("T", ""))
    except (ValueError, AttributeError):
        return TierEnum.coerce(tier_value).rank


# ---------------------------------------------------------------------------
# Mock LLM 机制
# ---------------------------------------------------------------------------

class MockLLMConfig:
    """Mock LLM 配置，用于确保评测结果可重复."""

    def __init__(self, enabled: bool = True, seed: int = 42):
        self.enabled = enabled
        self.seed = seed


# ---------------------------------------------------------------------------
# 评估指标计算
# ---------------------------------------------------------------------------


def _tier_exact_match(pred_rank: int, truth_rank: int) -> bool:
    """精确匹配：预测档级与真实档级完全一致."""
    return pred_rank == truth_rank


def _tier_tolerance_match(pred_rank: int, truth_rank: int, tolerance: int = 1) -> bool:
    """容忍度匹配：预测档级与真实档级差距在 tolerance 以内."""
    return abs(pred_rank - truth_rank) <= tolerance


def _compute_tier_accuracy(
    predictions: list[int],
    truths: list[int],
) -> dict[str, float]:
    """计算维度档级准确率.

    Returns:
        包含 exact_match 和 tolerance_match 两种准确率的字典
    """
    n = len(predictions)
    if n == 0:
        return {"exact_match": 0.0, "tolerance_match": 0.0, "count": 0}

    exact = sum(1 for p, t in zip(predictions, truths) if _tier_exact_match(p, t))
    tol = sum(1 for p, t in zip(predictions, truths) if _tier_tolerance_match(p, t))

    return {
        "exact_match": round(exact / n, 4),
        "tolerance_match": round(tol / n, 4),
        "count": n,
    }


def _compute_verdict_accuracy(
    pred_verdicts: list[str],
    true_verdicts: list[str],
) -> dict[str, float]:
    """计算最终 verdict 判定准确率."""
    n = len(pred_verdicts)
    if n == 0:
        return {"accuracy": 0.0, "count": 0}

    correct = sum(1 for p, t in zip(pred_verdicts, true_verdicts) if p == t)
    return {
        "accuracy": round(correct / n, 4),
        "count": n,
    }


def _compute_sentence_band_accuracy(
    pred_bands: list[str],
    true_bands: list[str],
) -> dict[str, float]:
    """计算量刑区间预测准确率.

    由于量刑区间是档级的确定性映射，此处等价于档级精确匹配。
    """
    n = len(pred_bands)
    if n == 0:
        return {"accuracy": 0.0, "count": 0}

    correct = sum(1 for p, t in zip(pred_bands, true_bands) if p == t)
    return {
        "accuracy": round(correct / n, 4),
        "count": n,
    }


def _compute_f1(
    pred_sets: list[set[str]],
    truth_sets: list[set[str]],
) -> dict[str, float]:
    """计算标签抽取的 F1 分数（微平均）."""
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for pred, truth in zip(pred_sets, truth_sets):
        tp = len(pred & truth)
        fp = len(pred - truth)
        fn = len(truth - pred)
        total_tp += tp
        total_fp += fp
        total_fn += fn

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _compute_conflict_recall(
    pred_conflicts: list[bool],
    truth_conflicts: list[bool],
) -> dict[str, float]:
    """计算冲突检测召回率.

    以 gold standard 中 agreement_kappa < 0.75 的案例视为"存在冲突"。
    """
    true_positives = sum(
        1 for p, t in zip(pred_conflicts, truth_conflicts) if p and t
    )
    actual_positives = sum(truth_conflicts)

    if actual_positives == 0:
        return {"recall": 1.0 if not any(pred_conflicts) else 0.0, "count": 0}

    return {
        "recall": round(true_positives / actual_positives, 4),
        "count": actual_positives,
    }


# ---------------------------------------------------------------------------
# 单案例评估
# ---------------------------------------------------------------------------


async def _evaluate_single_case(
    case: dict[str, Any],
    case_text: str,
) -> dict[str, Any]:
    """评估单个案例，返回预测结果与指标."""
    from app.services.pipeline import analyze_pipeline_v2

    case_id = case["case_id"]
    ground_truth = case["ground_truth"]

    start = time.perf_counter()
    try:
        result = await analyze_pipeline_v2(case_text, mode="auto")
        status = "success"
    except Exception as exc:
        result = None
        status = f"error: {exc}"

    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    # 提取预测结果
    pred = _extract_predictions(result)

    # 提取 ground truth
    gt_d1_rank = _cn_tier_to_rank(ground_truth["d1_tier"])
    gt_d2_rank = _cn_tier_to_rank(ground_truth["d2_tier"])
    gt_d3_rank = _cn_tier_to_rank(ground_truth["d3_tier"])
    gt_verdict = ground_truth["verdict"]

    # 量刑区间由档级确定映射
    gt_final_rank = _cn_tier_to_rank(
        _infer_final_tier_from_dims(gt_d1_rank, gt_d2_rank, gt_d3_rank)
    )
    gt_sentence_band = TierEnum(f"T{gt_final_rank}").sentence_band

    # 冲突标注：kappa < 0.75 视为存在冲突
    has_conflict = case.get("agreement_kappa", 1.0) < 0.75

    return {
        "case_id": case_id,
        "status": status,
        "duration_ms": duration_ms,
        "predictions": pred,
        "ground_truth": {
            "d1_rank": gt_d1_rank,
            "d2_rank": gt_d2_rank,
            "d3_rank": gt_d3_rank,
            "verdict": gt_verdict,
            "sentence_band": gt_sentence_band,
            "has_conflict": has_conflict,
        },
    }


def _infer_final_tier_from_dims(d1: int, d2: int, d3: int) -> str:
    """根据三维度 rank 推断最终档级（简化版组合逻辑）."""
    from app.services.tier_combiner import combine_tiers

    verdict = combine_tiers(f"T{d1}", f"T{d2}", f"T{d3}")
    return verdict["final_tier"]


def _extract_predictions(result: dict[str, Any] | None) -> dict[str, Any]:
    """从 AnalysisResultV2 中提取评估所需的预测字段."""
    if result is None:
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

    dim1 = result.get("dimension1", {})
    dim2 = result.get("dimension2", {})
    dim3 = result.get("dimension3", {})
    final_verdict = result.get("final_verdict", {})

    d1_tier = dim1.get("tier", "T2")
    d2_tier = dim2.get("tier", "T2")
    d3_tier = dim3.get("tier", "T2")

    final_tier = final_verdict.get("final_tier", "T2")
    sentence_band = final_verdict.get("sentence_band", TierEnum.T2.sentence_band)

    # 从 final_label 推断 verdict
    final_label = final_verdict.get("final_label", "")
    verdict = _infer_verdict_from_label(final_label, final_tier)

    matched_tag_ids = result.get("matched_tag_ids", [])
    conflicts = result.get("conflicts", [])

    return {
        "d1_tier": d1_tier,
        "d2_tier": d2_tier,
        "d3_tier": d3_tier,
        "final_tier": final_tier,
        "sentence_band": sentence_band,
        "verdict": verdict,
        "matched_tag_ids": matched_tag_ids,
        "has_conflicts": len(conflicts) > 0,
        "fallback": result.get("fallback", False),
    }


def _infer_verdict_from_label(final_label: str, final_tier: str) -> str:
    """从 final_label / final_tier 推断 verdict 文本.

    简化映射：
    - T1 → 不构成帮信
    - T2/T3 → 认定帮信
    - T4 → 认定帮信（情节特别严重）
    """
    rank = _tier_value_to_rank(final_tier)
    if rank <= 1:
        return "不构成帮信"
    return "认定帮信"


# ---------------------------------------------------------------------------
# 案例文本加载
# ---------------------------------------------------------------------------


def _load_case_text(case_id: str) -> str:
    """从测试集中加载案例原文.

    优先从 data/test_set_v1.0.jsonl 加载；若未找到则生成占位文本。
    """
    jsonl_path = _BACKEND_DIR.parent / "data" / "test_set_v1.0.jsonl"
    if jsonl_path.exists():
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("case_id") == case_id:
                    return record.get("case_text", record.get("text", ""))

    # 占位文本（评测环境下应确保真实案例文本可用）
    return f"【{case_id}】案例文本未找到，请使用真实案例数据进行评测。"


# ---------------------------------------------------------------------------
# 主评测流程
# ---------------------------------------------------------------------------


async def run_evaluation(
    gold_standard_path: Path = _GOLD_STANDARD_PATH,
    report_path: Path = _EVAL_REPORT_PATH,
) -> dict[str, Any]:
    """运行完整评测流程并生成报告.

    Args:
        gold_standard_path: 金标准测试集路径
        report_path: 评估报告输出路径

    Returns:
        评估报告字典
    """
    print(f"[eval_runner] 加载测试集: {gold_standard_path}")
    with open(gold_standard_path, encoding="utf-8") as f:
        test_cases = json.load(f)

    total = len(test_cases)
    print(f"[eval_runner] 测试案例数: {total}")

    # 逐案例评估
    case_results: list[dict[str, Any]] = []
    for i, case in enumerate(test_cases):
        case_id = case["case_id"]
        print(f"[eval_runner] ({i + 1}/{total}) 评估 {case_id} ...")

        case_text = _load_case_text(case_id)
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
            1 for r in case_results if r["status"] == "success"
        ),
        "failed_cases": sum(
            1 for r in case_results if r["status"] != "success"
        ),
        "metrics": metrics,
        "case_details": case_results,
    }

    # 写入报告
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[eval_runner] 评估报告已生成: {report_path}")
    _print_summary(report)

    return report


def _aggregate_metrics(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总所有案例的评估指标."""
    d1_preds, d1_truths = [], []
    d2_preds, d2_truths = [], []
    d3_preds, d3_truths = [], []
    pred_verdicts, true_verdicts = [], []
    pred_bands, true_bands = [], []
    pred_tag_sets, true_tag_sets = [], []
    pred_conflicts, true_conflicts = [], []

    for r in case_results:
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

    return {
        "dimension1_accuracy": _compute_tier_accuracy(d1_preds, d1_truths),
        "dimension2_accuracy": _compute_tier_accuracy(d2_preds, d2_truths),
        "dimension3_accuracy": _compute_tier_accuracy(d3_preds, d3_truths),
        "verdict_accuracy": _compute_verdict_accuracy(pred_verdicts, true_verdicts),
        "sentence_band_accuracy": _compute_sentence_band_accuracy(
            pred_bands, true_bands
        ),
        "tag_extraction_f1": _compute_f1(pred_tag_sets, true_tag_sets),
        "conflict_detection_recall": _compute_conflict_recall(
            pred_conflicts, true_conflicts
        ),
    }


def _print_summary(report: dict[str, Any]) -> None:
    """打印评估结果摘要."""
    metrics = report["metrics"]
    print("\n" + "=" * 60)
    print("评估结果摘要")
    print("=" * 60)
    print(f"测试集大小: {report['test_set_size']}")
    print(f"成功案例: {report['successful_cases']}")
    print(f"失败案例: {report['failed_cases']}")
    print("-" * 60)

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
    parser = argparse.ArgumentParser(description="评测运行器")
    parser.add_argument(
        "--gold-standard",
        type=Path,
        default=_GOLD_STANDARD_PATH,
        help="金标准测试集路径",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=_EVAL_REPORT_PATH,
        help="评估报告输出路径",
    )
    args = parser.parse_args()

    asyncio.run(run_evaluation(args.gold_standard, args.report))


if __name__ == "__main__":
    main()
