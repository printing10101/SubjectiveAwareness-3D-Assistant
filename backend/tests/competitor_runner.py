"""竞品对标框架 — 阶段 6 评测体系核心组件.

实现 3 种基线模型并与目标系统进行对比：
- baseline_random: 随机预测基线
- baseline_keywords: 纯关键词匹配基线
- baseline_general_llm: 通用 LLM 基线（无 prompt 工程优化）

在同一测试集上运行所有模型，生成对标表格。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
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
_COMPETITOR_REPORT_PATH = _REPORTS_DIR / "competitor_v1.0.json"


# ---------------------------------------------------------------------------
# 档级映射工具
# ---------------------------------------------------------------------------

_CN_TIER_TO_RANK: dict[str, int] = {
    "一档": 1,
    "二档": 2,
    "三档": 3,
    "四档": 4,
}


def _cn_tier_to_rank(cn_tier: str) -> int:
    """将中文档级转换为数值 rank (1-4)."""
    return _CN_TIER_TO_RANK.get(cn_tier.strip(), 2)


def _rank_to_cn_tier(rank: int) -> str:
    """将数值 rank 转换为中文档级."""
    rank_to_cn = {1: "一档", 2: "二档", 3: "三档", 4: "四档"}
    return rank_to_cn.get(rank, "二档")


def _tier_value_to_rank(tier_value: str) -> int:
    """将 TierEnum value 转换为数值 rank."""
    try:
        return int(tier_value.replace("T", ""))
    except (ValueError, AttributeError):
        return TierEnum.coerce(tier_value).rank


# ---------------------------------------------------------------------------
# 基线模型 1: 随机预测
# ---------------------------------------------------------------------------


class BaselineRandom:
    """随机预测基线模型."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)

    async def predict(self, case_text: str) -> dict[str, Any]:
        """对案例进行随机预测."""
        # 随机生成三个维度的档级 (T1-T4)
        d1_rank = random.randint(1, 4)
        d2_rank = random.randint(1, 4)
        d3_rank = random.randint(1, 4)

        # 根据档级推断 verdict
        final_rank = (d1_rank + d2_rank + d3_rank) // 3
        verdict = "认定帮信" if final_rank >= 2 else "不构成帮信"

        # 量刑区间
        sentence_band = TierEnum(f"T{final_rank}").sentence_band

        return {
            "d1_tier": f"T{d1_rank}",
            "d2_tier": f"T{d2_rank}",
            "d3_tier": f"T{d3_rank}",
            "final_tier": f"T{final_rank}",
            "sentence_band": sentence_band,
            "verdict": verdict,
            "matched_tag_ids": [],
            "has_conflicts": False,
            "fallback": True,
        }


# ---------------------------------------------------------------------------
# 基线模型 2: 关键词匹配
# ---------------------------------------------------------------------------


class BaselineKeywords:
    """关键词匹配基线模型."""

    # 严重程度关键词（权重高）
    SEVERE_KEYWORDS = {
        "情节特别严重", "数额特别巨大", "犯罪集团", "主犯",
        "累犯", "惯犯", "多次", "跨省", "境外",
    }

    # 中等严重程度关键词
    MODERATE_KEYWORDS = {
        "情节严重", "数额巨大", "共同犯罪", "从犯",
        "多次", "多人", "组织", "策划",
    }

    # 较轻情节关键词
    MINOR_KEYWORDS = {
        "情节较轻", "数额较小", "初犯", "偶犯",
        "自首", "立功", "坦白", "认罪认罚", "从犯",
    }

    def __init__(self):
        pass

    async def predict(self, case_text: str) -> dict[str, Any]:
        """基于关键词匹配进行预测."""
        severe_count = sum(1 for kw in self.SEVERE_KEYWORDS if kw in case_text)
        moderate_count = sum(1 for kw in self.MODERATE_KEYWORDS if kw in case_text)
        minor_count = sum(1 for kw in self.MINOR_KEYWORDS if kw in case_text)

        # 计算综合得分
        score = severe_count * 3 + moderate_count * 2 + minor_count * 1

        # 根据得分映射到档级
        if score >= 10:
            d1_rank = d2_rank = d3_rank = 4  # 四档
        elif score >= 6:
            d1_rank = d2_rank = d3_rank = 3  # 三档
        elif score >= 3:
            d1_rank = d2_rank = d3_rank = 2  # 二档
        else:
            d1_rank = d2_rank = d3_rank = 1  # 一档

        # 根据档级推断 verdict
        final_rank = (d1_rank + d2_rank + d3_rank) // 3
        verdict = "认定帮信" if final_rank >= 2 else "不构成帮信"

        sentence_band = TierEnum(f"T{final_rank}").sentence_band

        return {
            "d1_tier": f"T{d1_rank}",
            "d2_tier": f"T{d2_rank}",
            "d3_tier": f"T{d3_rank}",
            "final_tier": f"T{final_rank}",
            "sentence_band": sentence_band,
            "verdict": verdict,
            "matched_tag_ids": [],
            "has_conflicts": False,
            "fallback": False,
        }


# ---------------------------------------------------------------------------
# 基线模型 3: 通用 LLM（无 prompt 工程优化）
# ---------------------------------------------------------------------------


class BaselineGeneralLLM:
    """通用 LLM 基线模型（无 prompt 工程优化）."""

    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model

    async def predict(self, case_text: str) -> dict[str, Any]:
        """使用通用 LLM 进行预测（简单 prompt，无优化）."""
        from app.services.ollama_client import call_ollama_with_retry

        # 简单的通用 prompt（无专业 prompt 工程）
        system_prompt = "你是一个法律助手，请分析以下案件并给出判断。"
        user_prompt = f"""请分析以下帮信罪案件，判断其严重程度。

案件内容：
{case_text}

请从以下四个档位中选择一个：
- T1: 情节较轻
- T2: 情节一般
- T3: 情节严重
- T4: 情节特别严重

请以 JSON 格式返回：
{{"tier": "T1/T2/T3/T4", "reasoning": "你的理由"}}"""

        try:
            response = await call_ollama_with_retry(
                user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
            )

            # 解析响应
            tier = self._extract_tier_from_response(response)
            rank = _tier_value_to_rank(tier)

            d1_rank = d2_rank = d3_rank = rank
            final_rank = rank
            verdict = "认定帮信" if final_rank >= 2 else "不构成帮信"
            sentence_band = TierEnum(f"T{final_rank}").sentence_band

            return {
                "d1_tier": f"T{d1_rank}",
                "d2_tier": f"T{d2_rank}",
                "d3_tier": f"T{d3_rank}",
                "final_tier": f"T{final_rank}",
                "sentence_band": sentence_band,
                "verdict": verdict,
                "matched_tag_ids": [],
                "has_conflicts": False,
                "fallback": False,
            }

        except Exception as e:
            print(f"  [baseline_general_llm] LLM 调用失败: {e}")
            # 失败时返回默认值
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

    def _extract_tier_from_response(self, response: str) -> str:
        """从 LLM 响应中提取档级."""
        # 尝试匹配 JSON 格式
        json_match = re.search(r'"tier"\s*:\s*"(T[1-4])"', response)
        if json_match:
            return json_match.group(1)

        # 尝试直接匹配 T1-T4
        tier_match = re.search(r"\b(T[1-4])\b", response)
        if tier_match:
            return tier_match.group(1)

        # 默认返回 T2
        return "T2"


# ---------------------------------------------------------------------------
# 目标系统（完整 pipeline）
# ---------------------------------------------------------------------------


class TargetSystem:
    """目标系统（完整 pipeline）."""

    async def predict(self, case_text: str) -> dict[str, Any]:
        """使用完整 pipeline 进行预测."""
        from eval_runner import _extract_predictions

        from app.services.pipeline import analyze_pipeline_v2

        try:
            result = await analyze_pipeline_v2(case_text, mode="auto")
            return _extract_predictions(result)
        except Exception as e:
            print(f"  [target_system] Pipeline 执行失败: {e}")
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


# ---------------------------------------------------------------------------
# 评估指标计算（复用 eval_runner 中的函数）
# ---------------------------------------------------------------------------


def _compute_tier_accuracy(
    predictions: list[int],
    truths: list[int],
) -> dict[str, float]:
    """计算维度档级准确率."""
    n = len(predictions)
    if n == 0:
        return {"exact_match": 0.0, "tolerance_match": 0.0, "count": 0}

    exact = sum(1 for p, t in zip(predictions, truths) if p == t)
    tol = sum(1 for p, t in zip(predictions, truths) if abs(p - t) <= 1)

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
    """计算量刑区间预测准确率."""
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
    """计算标签抽取的 F1 分数."""
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
    """计算冲突检测召回率."""
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
        true_tag_sets.append(set())  # gold standard 中暂无标签真值

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


# ---------------------------------------------------------------------------
# 案例文本加载
# ---------------------------------------------------------------------------


def _load_case_text(case_id: str) -> str:
    """从测试集中加载案例原文."""
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

    return f"【{case_id}】案例文本未找到，请使用真实案例数据进行评测。"


# ---------------------------------------------------------------------------
# 竞品对标主流程
# ---------------------------------------------------------------------------


async def run_competitor_evaluation(
    gold_standard_path: Path = _GOLD_STANDARD_PATH,
    report_path: Path = _COMPETITOR_REPORT_PATH,
) -> dict[str, Any]:
    """运行竞品对标评测并生成报告.

    Args:
        gold_standard_path: 金标准测试集路径
        report_path: 竞品对标报告输出路径

    Returns:
        竞品对标报告字典
    """
    print(f"[competitor_runner] 加载测试集: {gold_standard_path}")
    with open(gold_standard_path, encoding="utf-8") as f:
        test_cases = json.load(f)

    total = len(test_cases)
    print(f"[competitor_runner] 测试案例数: {total}")

    # 初始化模型
    models = {
        "baseline_random": BaselineRandom(seed=42),
        "baseline_keywords": BaselineKeywords(),
        "baseline_general_llm": BaselineGeneralLLM(model="qwen2.5:7b"),
        "target_system": TargetSystem(),
    }

    print(f"[competitor_runner] 评测模型数: {len(models)}")

    # 存储每个模型的结果
    model_results: list[dict[str, Any]] = []

    for model_name, model in models.items():
        print(f"\n[competitor_runner] 评测模型: {model_name}")

        # 运行所有测试案例
        case_results: list[dict[str, Any]] = []
        for i, case in enumerate(test_cases):
            case_id = case["case_id"]
            print(f"  ({i + 1}/{total}) 评估 {case_id} ...")

            case_text = _load_case_text(case_id)

            # 使用模型进行预测
            start = time.perf_counter()
            try:
                predictions = await model.predict(case_text)
                status = "success"
            except Exception as exc:
                predictions = {
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
                status = f"error: {exc}"

            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            # 构建案例结果
            ground_truth = case["ground_truth"]
            gt_d1_rank = _cn_tier_to_rank(ground_truth["d1_tier"])
            gt_d2_rank = _cn_tier_to_rank(ground_truth["d2_tier"])
            gt_d3_rank = _cn_tier_to_rank(ground_truth["d3_tier"])
            gt_verdict = ground_truth["verdict"]

            # 推断最终档级和量刑区间
            from eval_runner import _infer_final_tier_from_dims
            gt_final_rank = _cn_tier_to_rank(
                _infer_final_tier_from_dims(gt_d1_rank, gt_d2_rank, gt_d3_rank)
            )
            gt_sentence_band = TierEnum(f"T{gt_final_rank}").sentence_band

            has_conflict = case.get("agreement_kappa", 1.0) < 0.75

            case_result = {
                "case_id": case_id,
                "status": status,
                "duration_ms": duration_ms,
                "predictions": predictions,
                "ground_truth": {
                    "d1_rank": gt_d1_rank,
                    "d2_rank": gt_d2_rank,
                    "d3_rank": gt_d3_rank,
                    "verdict": gt_verdict,
                    "sentence_band": gt_sentence_band,
                    "has_conflict": has_conflict,
                },
            }
            case_results.append(case_result)

        # 汇总该模型的指标
        metrics = _aggregate_metrics(case_results)

        model_results.append({
            "model_name": model_name,
            "metrics": metrics,
            "successful_cases": sum(
                1 for r in case_results if r["status"] == "success"
            ),
            "failed_cases": sum(
                1 for r in case_results if r["status"] != "success"
            ),
            "avg_duration_ms": round(
                sum(r["duration_ms"] for r in case_results) / len(case_results), 2
            ),
        })

    # 构建报告
    report: dict[str, Any] = {
        "version": "1.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "test_set_size": total,
        "model_count": len(models),
        "models": model_results,
    }

    # 写入报告
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[competitor_runner] 竞品对标报告已生成: {report_path}")
    _print_competitor_summary(report)

    return report


def _print_competitor_summary(report: dict[str, Any]) -> None:
    """打印竞品对标结果摘要."""
    print("\n" + "=" * 100)
    print("竞品对标结果摘要")
    print("=" * 100)
    print(f"测试集大小: {report['test_set_size']}")
    print(f"模型数量: {report['model_count']}")
    print("-" * 100)

    # 表头
    header = (
        f"{'模型名称':<25} {'verdict准确率':<12} {'D1精确':<10} {'D1容忍':<10} "
        f"{'量刑准确率':<12} {'标签F1':<10} {'冲突召回':<10} {'平均耗时(ms)':<12}"
    )
    print(header)
    print("-" * 100)

    for model in report["models"]:
        name = model["model_name"]
        metrics = model["metrics"]
        avg_duration = model["avg_duration_ms"]

        verdict_acc = metrics.get("verdict_accuracy", {}).get("accuracy", 0.0)
        d1_exact = metrics.get("dimension1_accuracy", {}).get("exact_match", 0.0)
        d1_tol = metrics.get("dimension1_accuracy", {}).get("tolerance_match", 0.0)
        sentence_acc = metrics.get("sentence_band_accuracy", {}).get("accuracy", 0.0)
        tag_f1 = metrics.get("tag_extraction_f1", {}).get("f1", 0.0)
        conflict_recall = metrics.get("conflict_detection_recall", {}).get("recall", 0.0)

        row = (
            f"{name:<25} "
            f"{verdict_acc:<12.2%} "
            f"{d1_exact:<10.2%} "
            f"{d1_tol:<10.2%} "
            f"{sentence_acc:<12.2%} "
            f"{tag_f1:<10.2%} "
            f"{conflict_recall:<10.2%} "
            f"{avg_duration:<12.2f}"
        )
        print(row)

    print("=" * 100)

    # 找出最佳模型
    print("\n最佳模型分析:")
    best_verdict = max(
        report["models"],
        key=lambda m: m["metrics"].get("verdict_accuracy", {}).get("accuracy", 0.0),
    )
    best_d1 = max(
        report["models"],
        key=lambda m: m["metrics"].get("dimension1_accuracy", {}).get("exact_match", 0.0),
    )
    fastest = min(report["models"], key=lambda m: m["avg_duration_ms"])

    print(f"  - verdict 准确率最高: {best_verdict['model_name']} "
          f"({best_verdict['metrics']['verdict_accuracy']['accuracy']:.2%})")
    print(f"  - D1 精确匹配最高: {best_d1['model_name']} "
          f"({best_d1['metrics']['dimension1_accuracy']['exact_match']:.2%})")
    print(f"  - 平均耗时最短: {fastest['model_name']} ({fastest['avg_duration_ms']:.2f}ms)")
    print("=" * 100)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------


def main() -> None:
    """命令行入口."""
    parser = argparse.ArgumentParser(description="竞品对标运行器")
    parser.add_argument(
        "--gold-standard",
        type=Path,
        default=_GOLD_STANDARD_PATH,
        help="金标准测试集路径",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=_COMPETITOR_REPORT_PATH,
        help="竞品对标报告输出路径",
    )
    args = parser.parse_args()

    asyncio.run(run_competitor_evaluation(args.gold_standard, args.report))


if __name__ == "__main__":
    main()
