"""竞品对标框架 — 阶段 6 评测体系核心组件.

实现 3 种基线模型并与目标系统进行对比：
- baseline_random: 随机预测基线
- baseline_keywords: 纯关键词匹配基线
- baseline_general_llm: 通用 LLM 基线（无 prompt 工程优化）

在同一测试集上运行所有模型，生成对标表格。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: argparse
import argparse
# 导入模块: asyncio
import asyncio
# 导入模块: json
import json
# 导入模块: random
import random
# 导入模块: re
import re
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
    # 返回处理结果
    return _CN_TIER_TO_RANK.get(cn_tier.strip(), 2)


def _rank_to_cn_tier(rank: int) -> str:
    """将数值 rank 转换为中文档级."""
    # 初始化变量 rank_to_cn
    rank_to_cn = {1: "一档", 2: "二档", 3: "三档", 4: "四档"}
    # 返回处理结果
    return rank_to_cn.get(rank, "二档")


def _tier_value_to_rank(tier_value: str) -> int:
    """将 TierEnum value 转换为数值 rank."""
    # 异常处理：处理业务逻辑
    try:
        # 返回处理结果
        return int(tier_value.replace("T", ""))
    # 捕获异常：处理业务逻辑
    except (ValueError, AttributeError):
        # 返回处理结果
        return TierEnum.coerce(tier_value).rank


# ---------------------------------------------------------------------------
# 基线模型 1: 随机预测
# ---------------------------------------------------------------------------


# 定义 BaselineRandom 类
class BaselineRandom:
    """随机预测基线模型."""

    def __init__(self, seed: int = 42):

        # 执行 __init__ 函数的核心逻辑
        self.seed = seed
        random.seed(seed)

    async def predict(self, case_text: str) -> dict[str, Any]:
        """对案例进行随机预测."""
        # 随机生成三个维度的档级 (T1-T4)
        d1_rank = random.randint(1, 4)
        # 初始化变量 d2_rank
        d2_rank = random.randint(1, 4)
        # 初始化变量 d3_rank
        d3_rank = random.randint(1, 4)

        # 根据档级推断 verdict
        final_rank = (d1_rank + d2_rank + d3_rank) // 3
        # 初始化变量 verdict
        verdict = "认定帮信" if final_rank >= 2 else "不构成帮信"

        # 量刑区间
        sentence_band = TierEnum(f"T{final_rank}").sentence_band

        # 返回处理结果
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


# 定义 BaselineKeywords 类
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

        # 执行 __init__ 函数的核心逻辑
        pass

    async def predict(self, case_text: str) -> dict[str, Any]:
        """基于关键词匹配进行预测."""
        # 初始化变量 severe_count
        severe_count = sum(1 for kw in self.SEVERE_KEYWORDS if kw in case_text)
        # 初始化变量 moderate_count
        moderate_count = sum(1 for kw in self.MODERATE_KEYWORDS if kw in case_text)
        # 初始化变量 minor_count
        minor_count = sum(1 for kw in self.MINOR_KEYWORDS if kw in case_text)

        # 计算综合得分
        score = severe_count * 3 + moderate_count * 2 + minor_count * 1

        # 根据得分映射到档级
        if score >= 10:
            # 初始化变量 d1_rank
            d1_rank = d2_rank = d3_rank = 4  # 四档
        elif score >= 6:
            # 初始化变量 d1_rank
            d1_rank = d2_rank = d3_rank = 3  # 三档
        elif score >= 3:
            # 初始化变量 d1_rank
            d1_rank = d2_rank = d3_rank = 2  # 二档
        else:
            # 初始化变量 d1_rank
            d1_rank = d2_rank = d3_rank = 1  # 一档

        # 根据档级推断 verdict
        final_rank = (d1_rank + d2_rank + d3_rank) // 3
        # 初始化变量 verdict
        verdict = "认定帮信" if final_rank >= 2 else "不构成帮信"

        # 初始化变量 sentence_band
        sentence_band = TierEnum(f"T{final_rank}").sentence_band

        # 返回处理结果
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


# 定义 BaselineGeneralLLM 类
class BaselineGeneralLLM:
    """通用 LLM 基线模型（无 prompt 工程优化）."""

    def __init__(self, model: str = "qwen2.5:7b"):
        # 函数 __init__ 的初始化逻辑
        self.model = model

    async def predict(self, case_text: str) -> dict[str, Any]:
        """使用通用 LLM 进行预测（简单 prompt，无优化）."""
        # 导入模块: from app.services.ollama_client
        from app.services.ollama_client import call_ollama_with_retry

        # 简单的通用 prompt（无专业 prompt 工程）
        system_prompt = "你是一个法律助手，请分析以下案件并给出判断。"
        # 初始化变量 user_prompt
        user_prompt = f"""请分析以下帮信罪案件，判断其严重程度。

案件内容：
{case_text}

请从以下四个档位中选择一个：
- T1: 情节较轻
- T2: 情节一般
- T3: 情节严重
- T4: 情节特别严重

请以 JSON 格式返回：
{{"tier": "T1/T2/T3/T4", "reason
        # 异常处理：处理业务逻辑
ing": "你的理由"}}"""

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 response
            response = await call_ollama_with_retry(
                user_prompt,
                # 初始化变量 system_prompt
                system_prompt=system_prompt,
                # 初始化变量 temperature
                temperature=0.3,
            )

            # 解析响应
            tier = self._extract_tier_from_response(response)
            # 初始化变量 rank
            rank = _tier_value_to_rank(tier)

            # 初始化变量 d1_rank
            d1_rank = d2_rank = d3_rank = rank
            # 初始化变量 final_rank
            final_rank = rank
            # 初始化变量 verdict
            verdict = "认定帮信" if final_rank >= 2 else "不构成帮信"
            # 初始化变量 sentence_band
            sentence_band = TierEnum(f"T{final_rank}").sentence_band

            # 返回处理结果
            return {
                "d1_tier": f"T{d1_rank}",
                "d2_tier": f"T{d2_rank}",
                "d3_tier": f"T{d3_rank}",
                "final_tier": f"T{final_rank}",
                "sentence_band": sentence_band,
                "verdict": verdict,
                "matched_tag_ids": [],
                "has_conflicts": False,
                "fallback": Fal
        # 捕获异常：处理业务逻辑
se,
            }

        # 捕获并处理异常
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

        # 执行 _extract_tier_from_response 函数的核心逻辑
            }

    def _extract_tier_from_response(self, response: str) -> str:
        """从 LLM 响应中提取档级."""
        # 尝试匹配 JSON 格式
        json_match = re.search(r'"tier"\s*:\s*"(T[1-4])        # 条件判断：处理业务逻辑
"', response)
        # 条件判断: 检查 json_match
        if json_match:
            # 返回处理结果
            return json_match.group(1)

        # 尝试直接匹配 T1-T4
        tier_match = r        # 条件判断：处理业务逻辑
e.search(r"\b(T[1-4])\b", response)
        # 条件判断: 检查 tier_match
        if tier_match:
            # 返回处理结果
            return tier_match.group(1)

        # 默认返回 T2
        return "T2"


# ---------------------------------------------------------------------------
# 目标系统（完整 pipeline）
# ---------------------------------------------------------------------------


# 定义 TargetSystem 类
class TargetSystem:
    """目标系统（完整 pipeline）."""

    async def predict(self, case_text: str) -> dict[str, Any]:
        """使用完整 pipeline 进行预测."""
        # 导入模块: from eval_runner
        from eval_runner import _extract_predictions

        from app.serv
        # 异常处理：处理业务逻辑
ices.pipeline import analyze_pipeline_v2

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 result
            result = await analyze_pipeline_v2(case_text, mode="auto")
               # 捕获异常：处理业务逻辑
     return _extract_predictions(result)
        # 捕获并处理异常
        except Exception as e:
            print(f"  [target_system] Pipeline 执行失败: {e}")
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


# ---------------------------------------------------------------------------
# 评估指标计算（复用 eval_runner 中的函数）
# ---------------------------------------------------------------------------


def _compute_tier_accuracy(
    # 函数 _compute_tier_accuracy 的初始化逻辑
    predictions: list[int],


    # 执行 _compute_tier_accuracy 函数的核心逻辑
    truths: list[int],
) -> dict[s    # 条件判断：处理业务逻辑
tr, float]:
    """计算维度档级准确率."""
    n = len(predictions)
    # 条件判断: 检查 n == 0
    if n == 0:
        # 返回处理结果
        return {"exact_match": 0.0, "tolerance_match": 0.0, "count": 0}

    # 初始化变量 exact
    exact = sum(1 for p, t in zip(predictions, truths) if p == t)
    tol = sum(1 for p, t in zip(predictions, truths) if abs(p - t) <= 1)

    # 返回处理结果
    return {
        "exact_match": round(exact / n, 4),


    # 执行 _compute_verdict_accuracy 函数的核心逻辑
        "tolerance_match": round(tol / n, 4),
        "count": n,
    }


def _compute_verdict_accuracy(
    # 函数 _compute_verdict_accuracy 的初始化逻辑
    pred_verdicts: list[str],
    true_verdicts: list[str],
) ->    # 条件判断：处理业务逻辑
 dict[str, float]:
    """计算最终 verdict 判定准确率."""
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
       # 条件判断：处理业务逻辑
 true_bands: list[str],
) -> dict[str, float]:
    """计算量刑区间预测准确率."""
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
        "count": n,
    }


def _compute_f1(
    # 函数 _compute_f1 的初始化逻辑
    pred_sets: list[set[str]],
    truth_sets: list[set[str]],
) -> dict[str, float]:
    """计算标签抽取的 F1 分数."""
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
    recall = total_tp / (total_tp + t        # 条件判断：处理业务逻辑
otal_fn) if (total_tp + total_fn) > 0 else 0.0
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
    """计算冲突检测召回率."""
    true_pos
    # 条件判断：处理业务逻辑
itives = sum(
        1 for p, t in zip(pred_conflicts, truth_conflicts) if p and t
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


def _aggregate_metrics(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总所有案例的评估指标."""
    d1_preds, d1_truths = [], []
    d2_preds, d2_truths = [], []
    d3_preds, d3_truths = [], []
    pred_verdicts, true_verdicts = [], []
    pred_bands, true_bands = [], []
    pred_tag_sets, true_tag_sets = [], []
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
        true_tag_sets.append(set())  # gold standard 中暂无标签真值

        pred_conflicts.append(pred["has_conflicts"])
        true_conflicts.append(gt["has_conflict"])

    # 返回处理结果
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


    # 执行 _load_case_text 函数的核心逻辑
            pred_conflicts, true_conflicts
        ),
    }


# ---------------------------------------------------------------------------
# 案例文本加载
# ------------------------------------------------------------    # 条件判断：处理业务逻辑
---------------


def _load_case_text(case_id: str) -> str:
    """从测试集中加载案例原文."""
    # 初始化变量 jsonl_path
    jsonl_path = _BACKEND_DIR.parent / "data                # 条件判断：处理业务逻辑
" / "test_set_v1.0.jsonl"
    # 条件判断: 检查 jsonl_path.exists()
    if jsonl_path.exists():
        # 使用上下文管理器管理资源
        with ope                # 条件判断：处理业务逻辑
n(jsonl_path, encoding="utf-8") as f:
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

    # 返回处理结果
    return f"【{case_id}】案例文本未找到，请使用真实案例数据进行评测。"


# ---------------------------------------------------------------------------
# 竞品对标主流程
# ---------------------------------------------------------------------------


async def run_competitor_evaluation(
    # 函数 run_competitor_evaluation 的初始化逻辑
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
    # 使用上下文管理器管理资源
    with open(gold_standard_path, encoding="utf-8") as f:
        # 初始化变量 test_cases
        test_cases = json.load(f)

    # 初始化变量 total
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
    model_results: 
    # 循环遍历：处理业务逻辑
list[dict[str, Any]] = []

    # 遍历: for model_name, model in models.items():
    for model_name, model in models.items():
        print(f"\n[competitor_runner] 评测模型: {model_name}")

        # 运行所有测试案例
           # 循环遍历：处理业务逻辑
     case_results: list[dict[str, Any]] = []
        # 遍历: for i, case in enumerate(test_cases):
        for i, case in enumerate(test_cases):
            # 初始化变量 case_id
            case_id = case["case_id"]
            print(f"  ({i + 1}/{total}) 评估 {case_id} ...")

            # 初始化变量 case_text
            case_text = _load_case_text(case_id)

            # 使用模型进行预测
            start = time.perf_counter()
            # 尝试执行可能抛出异常的代码
            try:
                # 初始化变量 predictions
                predictions = awa            # 捕获异常：处理业务逻辑
it model.predict(case_text)
                # 初始化变量 status
                status = "success"
            # 捕获并处理异常
            except Exception as exc:
                # 初始化变量 predictions
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
                # 初始化变量 status
                status = f"error: {exc}"

            # 初始化变量 duration_ms
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            # 构建案例结果
            ground_truth = case["ground_truth"]
            # 初始化变量 gt_d1_rank
            gt_d1_rank = _cn_tier_to_rank(ground_truth["d1_tier"])
            # 初始化变量 gt_d2_rank
            gt_d2_rank = _cn_tier_to_rank(ground_truth["d2_tier"])
            # 初始化变量 gt_d3_rank
            gt_d3_rank = _cn_tier_to_rank(ground_truth["d3_tier"])
            # 初始化变量 gt_verdict
            gt_verdict = ground_truth["verdict"]

            # 推断最终档级和量刑区间
            from eval_runner import _infer_final_tier_from_dims
            # 初始化变量 gt_final_rank
            gt_final_rank = _cn_tier_to_rank(
                _infer_final_tier_from_dims(gt_d1_rank, gt_d2_rank, gt_d3_rank)
            )
            # 初始化变量 gt_sentence_band
            gt_sentence_band = TierEnum(f"T{gt_final_rank}").sentence_band

            # 初始化变量 has_conflict
            has_conflict = case.get("agreement_kappa", 1.0) < 0.75

            # 初始化变量 case_result
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
    # 使用上下文管理器管理资源
    with open(report_path, "w", encoding="utf-8") as f:


    # 执行 _print_competitor_summary 函数的核心逻辑
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[competitor_runner] 竞品对标报告已生成: {report_path}")
    _print_competitor_summary(report)

    # 返回处理结果
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
        f"{'量刑准确率':<12} {'标签F1':<10} {'冲突召回':<
    # 循环遍历：处理业务逻辑
10} {'平均耗时(ms)':<12}"
    )
    print(header)
    print("-" * 100)

    # 遍历: for model in report["models"]:
    for model in report["models"]:
        # 初始化变量 name
        name = model["model_name"]
        # 初始化变量 metrics
        metrics = model["metrics"]
        # 初始化变量 avg_duration
        avg_duration = model["avg_duration_ms"]

        # 初始化变量 verdict_acc
        verdict_acc = metrics.get("verdict_accuracy", {}).get("accuracy", 0.0)
        # 初始化变量 d1_exact
        d1_exact = metrics.get("dimension1_accuracy", {}).get("exact_match", 0.0)
        # 初始化变量 d1_tol
        d1_tol = metrics.get("dimension1_accuracy", {}).get("tolerance_match", 0.0)
        # 初始化变量 sentence_acc
        sentence_acc = metrics.get("sentence_band_accuracy", {}).get("accuracy", 0.0)
        # 初始化变量 tag_f1
        tag_f1 = metrics.get("tag_extraction_f1", {}).get("f1", 0.0)
        # 初始化变量 conflict_recall
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
    # 初始化变量 best_verdict
    best_verdict = max(
        report["models"],
        key=lambda m: m["metrics"].get("verdict_accuracy", {}).get("accuracy", 0.0),
    )
    # 初始化变量 best_d1
    best_d1 = max(
        report["models"],
        key=lambda m: m["metrics"].get("dimension1_accuracy", {}).get("exact_match", 0.0),
    )
    # 初始化变量 fastest
    fastest = min(report["models"], key=lambda m: m["avg_duration_ms"])

    print(f"  - verdict 准确率最高: {best_verdict['model_name']} "
          f"({best_verdict['metrics']['verdict_accuracy']['accuracy']:.2%})")
    print(f"  - D1 精确匹配最高: {best_d1['model_name']} "
          f"({best_d1['metrics']['dimension1_accuracy']['exact_match']:.2%})")


    # 执行 main 函数的核心逻辑
    print(f"  - 平均耗时最短: {fastest['model_name']} ({fastest['avg_duration_ms']:.2f}ms)")
    print("=" * 100)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------


def main() -> None:
    """命令行入口."""
    # 初始化变量 parser
    parser = argparse.ArgumentParser(description="竞品对标运行器")
    parser.add_argument(
        "--gold-standard",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=_GOLD_STANDARD_PATH,
        # 初始化变量 help
        help="金标准测试集路径",
    )
    parser.add_

# 条件判断：处理业务逻辑
argument(
        "--report",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=_COMPETITOR_REPORT_PATH,
        # 初始化变量 help
        help="竞品对标报告输出路径",
    )
    # 初始化变量 args
    args = parser.parse_args()

    asyncio.run(run_competitor_evaluation(args.gold_standard, args.report))


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()
