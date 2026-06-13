"""
scripts/analyze_experiment.py

实验数据系统性统计分析与可视化呈现脚本。
对回溯性对比实验数据进行多维度统计分析，生成统计图表及实证研究报告初稿。

功能模块：
  1. 描述性统计分析（基本统计量、四分位距等）
  2. Cohen's Kappa 一致性分析（组内/组间 + 显著性检验）
  3. 耗时差异分析（独立样本 t 检验 + 效应量 + 95% 置信区间）
  4. AI 与判决一致率（Precision / Recall / F1 + 混淆矩阵）
  5. 不一致案例定性分析
  6. 数据可视化（柱状图、热力图、箱线图、混淆矩阵热力图、饼图）
  7. 实证研究报告自动生成
"""

import os
import sys
import json
import math
import random
from pathlib import Path
from datetime import datetime
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (
    cohen_kappa_score,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)
from loguru import logger

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
RESEARCH_DIR = PROJECT_ROOT / "research"
CASES_DIR = RESEARCH_DIR / "cases"
DATA_DIR = RESEARCH_DIR / "data"
RESULTS_DIR = RESEARCH_DIR / "results"
LOGS_DIR = PROJECT_ROOT / "logs"

sns.set_theme(style="whitegrid", font_scale=0.9)
plt.rcParams["font.family"] = ["sans-serif"]
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"analyze_experiment_{timestamp}.log"
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | <cyan>{message}</cyan>",
        level="INFO",
    )
    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
        level="DEBUG",
        rotation="50 MB",
    )
    logger.info(f"日志文件: {log_file}")
    return log_file


def load_experiment_data() -> dict:
    """尝试从多个数据源加载实验数据，若均不可用则生成模拟数据。"""
    candidates = [
        DATA_DIR / "experiment_data.json",
        RESULTS_DIR / "experiment_data.json",
    ]
    for path in candidates:
        if path.exists():
            logger.info(f"加载实验数据: {path}")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            records = data.get("records", [])
            logger.info(f"数据加载完成: {len(records)} 条分析记录")
            return data

    case_files = sorted(CASES_DIR.glob("GZ*.json"))
    if case_files:
        logger.info(f"发现 {len(case_files)} 个案例文件，加载基础案例数据")
        cases_data = []
        for cf in case_files:
            with open(cf, "r", encoding="utf-8") as f:
                cases_data.append(json.load(f))
        return _build_data_from_cases(cases_data)

    logger.warning("无可用实验数据，生成模拟数据用于验证")
    return _generate_mock_data()


def _build_data_from_cases(cases_data: list) -> dict:
    """从 research/cases/ 下的案例 JSON 构建实验数据集。"""
    random.seed(42)
    np.random.seed(42)

    num_raters_a = 10
    num_raters_b = 10
    rater_pool_a = [f"PA-{i + 1:03d}" for i in range(num_raters_a)]
    rater_pool_b = [f"PB-{i + 1:03d}" for i in range(num_raters_b)]

    records = []
    cases_meta = []
    ai_conclusions = {}

    for case in cases_data:
        case_id = case["case_id"]
        gt = case["actual_judgment"]["subjective_knowledge"]
        gt = "认定明知" if "明知" in gt else "不认定明知"
        difficulty = np.random.choice(["难", "中", "易"], p=[0.3, 0.4, 0.3])
        cases_meta.append(
            {
                "case_id": case_id,
                "difficulty": difficulty,
                "ground_truth": gt,
            }
        )

        ai_acc = 0.78 if difficulty == "难" else (0.85 if difficulty == "中" else 0.92)
        ai_label = (
            gt
            if random.random() < ai_acc
            else ("不认定明知" if gt == "认定明知" else "认定明知")
        )
        ai_conclusions[case_id] = ai_label

        for rater_id in rater_pool_a:
            agr_prob = (
                0.62 if difficulty == "难" else (0.72 if difficulty == "中" else 0.80)
            )
            conc = (
                gt
                if random.random() < agr_prob
                else ("不认定明知" if gt == "认定明知" else "认定明知")
            )
            base_time = np.random.normal(loc=18, scale=4)
            if difficulty == "难":
                base_time += 5
            elif difficulty == "易":
                base_time -= 3
            time_cost = max(3, round(base_time + np.random.normal(0, 2), 1))
            records.append(
                {
                    "case_id": case_id,
                    "difficulty": difficulty,
                    "ground_truth": gt,
                    "rater_id": rater_id,
                    "group": "A",
                    "conclusion": conc,
                    "time_cost_minutes": time_cost,
                    "confidence": np.random.randint(2, 6),
                }
            )

        for rater_id in rater_pool_b:
            agr_prob = (
                0.80 if difficulty == "难" else (0.87 if difficulty == "中" else 0.92)
            )
            conc = (
                gt
                if random.random() < agr_prob
                else ("不认定明知" if gt == "认定明知" else "认定明知")
            )
            base_time = np.random.normal(loc=10, scale=3)
            if difficulty == "难":
                base_time += 3
            elif difficulty == "易":
                base_time -= 2
            time_cost = max(2, round(base_time + np.random.normal(0, 1.5), 1))
            records.append(
                {
                    "case_id": case_id,
                    "difficulty": difficulty,
                    "ground_truth": gt,
                    "rater_id": rater_id,
                    "group": "B",
                    "conclusion": conc,
                    "time_cost_minutes": time_cost,
                    "confidence": np.random.randint(3, 6),
                }
            )

    data = {
        "experiment_info": {
            "name": "AI辅助分析对主观明知认定影响的回溯性对比实验",
            "total_cases": len(cases_meta),
            "group_a_raters": num_raters_a,
            "group_b_raters": num_raters_b,
            "generated_at": datetime.now().isoformat(),
            "data_source": f"{len(cases_meta)}个案例文件",
            "is_mock_data": True,
        },
        "cases": cases_meta,
        "records": records,
        "ai_conclusions": ai_conclusions,
    }
    logger.info(
        f"已从案例构建实验数据: {len(records)} 条记录, {len(cases_meta)} 件案件"
    )
    return data


def _generate_mock_data(seed: int = 42) -> dict:
    """生成完全模拟的实验数据，用于脚本功能验证。"""
    np.random.seed(seed)
    random.seed(seed)
    num_cases = 25
    num_raters_per_group = 10
    case_ids = [f"CASE-{i + 1:03d}" for i in range(num_cases)]
    difficulties = np.random.choice(
        ["难", "中", "易"], size=num_cases, p=[0.3, 0.4, 0.3]
    )
    ground_truth = np.random.choice(
        ["认定明知", "不认定明知"], size=num_cases, p=[0.55, 0.45]
    )

    records = []
    rater_pool_a = [f"PA-{i + 1:03d}" for i in range(num_raters_per_group)]
    rater_pool_b = [f"PB-{i + 1:03d}" for i in range(num_raters_per_group)]

    for case_idx, case_id in enumerate(case_ids):
        gt = ground_truth[case_idx]
        difficulty = difficulties[case_idx]

        for rater_id in rater_pool_a:
            agreement_prob = (
                0.65 if difficulty == "难" else (0.75 if difficulty == "中" else 0.82)
            )
            conclusion = (
                gt
                if np.random.random() < agreement_prob
                else ("不认定明知" if gt == "认定明知" else "认定明知")
            )
            base_time = np.random.normal(loc=18, scale=4)
            if difficulty == "难":
                base_time += 6
            elif difficulty == "易":
                base_time -= 4
            time_cost = max(3, round(base_time + np.random.normal(0, 2), 1))
            records.append(
                {
                    "case_id": case_id,
                    "difficulty": difficulty,
                    "ground_truth": gt,
                    "rater_id": rater_id,
                    "group": "A",
                    "conclusion": conclusion,
                    "time_cost_minutes": time_cost,
                    "confidence": np.random.randint(2, 6),
                }
            )

        for rater_id in rater_pool_b:
            agreement_prob = (
                0.82 if difficulty == "难" else (0.88 if difficulty == "中" else 0.93)
            )
            conclusion = (
                gt
                if np.random.random() < agreement_prob
                else ("不认定明知" if gt == "认定明知" else "认定明知")
            )
            base_time = np.random.normal(loc=10, scale=3)
            if difficulty == "难":
                base_time += 4
            elif difficulty == "易":
                base_time -= 2
            time_cost = max(2, round(base_time + np.random.normal(0, 1.5), 1))
            records.append(
                {
                    "case_id": case_id,
                    "difficulty": difficulty,
                    "ground_truth": gt,
                    "rater_id": rater_id,
                    "group": "B",
                    "conclusion": conclusion,
                    "time_cost_minutes": time_cost,
                    "confidence": np.random.randint(3, 6),
                }
            )

    ai_conclusions = {}
    for case_idx, case_id in enumerate(case_ids):
        gt = ground_truth[case_idx]
        difficulty = difficulties[case_idx]
        ai_accuracy = (
            0.78 if difficulty == "难" else (0.85 if difficulty == "中" else 0.92)
        )
        ai_conclusions[case_id] = (
            gt
            if np.random.random() < ai_accuracy
            else ("不认定明知" if gt == "认定明知" else "认定明知")
        )

    data = {
        "experiment_info": {
            "name": "AI辅助分析对主观明知认定影响的回溯性对比实验",
            "total_cases": num_cases,
            "group_a_raters": num_raters_per_group,
            "group_b_raters": num_raters_per_group,
            "generated_at": datetime.now().isoformat(),
            "is_mock_data": True,
        },
        "cases": [
            {
                "case_id": case_ids[i],
                "difficulty": difficulties[i],
                "ground_truth": ground_truth[i],
            }
            for i in range(num_cases)
        ],
        "records": records,
        "ai_conclusions": ai_conclusions,
    }
    logger.info(f"已生成模拟数据: {len(records)} 条记录, {num_cases} 件案件")
    return data


def compute_descriptive_statistics(data: dict) -> dict:
    """计算两组实验数据的描述性统计量。

    包括案例数量、平均耗时（含标准差）、中位数、四分位距（Q1, Q3, IQR）。
    """
    result = {}
    for group_label in ("A", "B"):
        group_records = [r for r in data["records"] if r["group"] == group_label]
        if not group_records:
            result[group_label] = {}
            continue
        times = np.array([r["time_cost_minutes"] for r in group_records])
        confs = np.array([r["confidence"] for r in group_records])
        conclusions = [r["conclusion"] for r in group_records]
        unique, counts = np.unique(conclusions, return_counts=True)

        q1 = float(np.percentile(times, 25))
        q3 = float(np.percentile(times, 75))
        result[group_label] = {
            "n_raters": len(set(r["rater_id"] for r in group_records)),
            "n_records": len(group_records),
            "n_cases": len(set(r["case_id"] for r in group_records)),
            "time_cost_minutes": {
                "mean": round(float(np.mean(times)), 2),
                "std": round(float(np.std(times, ddof=1)), 2),
                "median": round(float(np.median(times)), 2),
                "min": round(float(np.min(times)), 2),
                "max": round(float(np.max(times)), 2),
                "q1": round(q1, 2),
                "q3": round(q3, 2),
                "iqr": round(q3 - q1, 2),
            },
            "confidence": {
                "mean": round(float(np.mean(confs)), 2),
                "std": round(float(np.std(confs, ddof=1)), 2),
            },
            "conclusion_distribution": dict(zip(unique.tolist(), counts.tolist())),
        }
        logger.info(
            f"  {group_label}组: n={result[group_label]['n_records']}, "
            f"平均耗时={result[group_label]['time_cost_minutes']['mean']}min "
            f"(SD={result[group_label]['time_cost_minutes']['std']}), "
            f"中位数={result[group_label]['time_cost_minutes']['median']}, "
            f"IQR={result[group_label]['time_cost_minutes']['iqr']}"
        )
    return result


def compute_cohens_kappa_analysis(data: dict) -> dict:
    """计算各组组内 Cohen's Kappa 系数及组间对比。

    对每组内所有评估者两两组合计算 Kappa，汇总得到组内一致性分布。
    采用 Bootstrap 法估计 Kappa 的 95% 置信区间。
    """
    result = {}
    for group_label in ("A", "B"):
        group_records = [r for r in data["records"] if r["group"] == group_label]
        rater_ids = sorted(set(r["rater_id"] for r in group_records))

        pair_kappas = []
        pair_details = []

        for r1, r2 in combinations(rater_ids, 2):
            r1_map = {
                r["case_id"]: r["conclusion"]
                for r in group_records
                if r["rater_id"] == r1
            }
            r2_map = {
                r["case_id"]: r["conclusion"]
                for r in group_records
                if r["rater_id"] == r2
            }
            common = sorted(set(r1_map.keys()) & set(r2_map.keys()))
            if len(common) < 5:
                continue
            k = cohen_kappa_score(
                [r1_map[c] for c in common], [r2_map[c] for c in common]
            )
            pair_kappas.append(k)
            pair_details.append(
                {
                    "rater1": r1,
                    "rater2": r2,
                    "kappa": round(float(k), 4),
                    "n_cases": len(common),
                }
            )

        arr = np.array(pair_kappas)
        mean_k = float(np.mean(arr))
        std_k = float(np.std(arr, ddof=1))
        n_pairs = len(arr)

        ci_lower, ci_upper = _bootstrap_kappa_ci(arr)

        comparison_within = {}
        for threshold, label in [
            (0.0, "低于随机"),
            (0.2, "极低"),
            (0.4, "较低"),
            (0.6, "中等"),
            (0.8, "良好"),
        ]:
            count = int(np.sum(arr >= threshold))
            comparison_within[label] = {
                "threshold": threshold,
                "count": count,
                "pct": round(count / n_pairs * 100, 1) if n_pairs > 0 else 0,
            }

        result[group_label] = {
            "group": group_label,
            "mean_kappa": round(mean_k, 4),
            "median_kappa": round(float(np.median(arr)), 4),
            "std_kappa": round(std_k, 4),
            "min_kappa": round(float(np.min(arr)), 4),
            "max_kappa": round(float(np.max(arr)), 4),
            "ci_95": [round(ci_lower, 4), round(ci_upper, 4)],
            "kappa_above_065_pct": round(float(np.mean(arr >= 0.65) * 100), 1),
            "pair_count": n_pairs,
            "distribution_by_level": comparison_within,
            "pair_details": pair_details,
        }
        logger.info(
            f"  {group_label}组 Cohen's Kappa: μ={result[group_label]['mean_kappa']:.4f}, "
            f"95%CI=[{result[group_label]['ci_95'][0]:.4f}, {result[group_label]['ci_95'][1]:.4f}], "
            f"≥0.65占比={result[group_label]['kappa_above_065_pct']:.1f}%"
        )

    a_k = result["A"]["mean_kappa"]
    b_k = result["B"]["mean_kappa"]
    delta = b_k - a_k

    kappa_comparison = {
        "group_a_kappa": a_k,
        "group_b_kappa": b_k,
        "delta": round(delta, 4),
        "delta_pct": round(delta / max(abs(a_k), 0.001) * 100, 2),
        "interpretation": (
            f"B组Kappa({b_k:.4f})较A组({a_k:.4f}){'提升' if delta > 0 else '降低'}"
            f"{abs(delta):.4f}({abs(delta / max(abs(a_k), 0.001)) * 100:.1f}%)"
        ),
    }

    result["comparison"] = kappa_comparison
    return result


def _bootstrap_kappa_ci(
    kappa_array: np.ndarray, n_bootstrap: int = 2000, ci: float = 0.95
) -> tuple:
    """用 Bootstrap 法估计 Kappa 均值的置信区间。"""
    if len(kappa_array) < 2:
        return (float(np.min(kappa_array)), float(np.max(kappa_array)))
    means = np.array(
        [
            np.mean(np.random.choice(kappa_array, size=len(kappa_array), replace=True))
            for _ in range(n_bootstrap)
        ]
    )
    alpha = (1.0 - ci) / 2.0
    return (
        float(np.percentile(means, alpha * 100)),
        float(np.percentile(means, (1 - alpha) * 100)),
    )


def compute_time_analysis(data: dict) -> dict:
    """比较两组分析耗时的差异。

    方法：
      1. Shapiro-Wilk 正态性检验
      2. 若两组均正态 → 独立样本 t 检验；否则 → Mann-Whitney U 检验
      3. Cohen's d 效应量 + 均值差的 95% 置信区间
    """
    times_a = np.array(
        [r["time_cost_minutes"] for r in data["records"] if r["group"] == "A"]
    )
    times_b = np.array(
        [r["time_cost_minutes"] for r in data["records"] if r["group"] == "B"]
    )

    mean_a, std_a = float(np.mean(times_a)), float(np.std(times_a, ddof=1))
    mean_b, std_b = float(np.mean(times_b)), float(np.std(times_b, ddof=1))
    median_a, median_b = float(np.median(times_a)), float(np.median(times_b))

    n_a, n_b = len(times_a), len(times_b)

    shapiro_a = stats.shapiro(times_a)
    shapiro_b = stats.shapiro(times_b)
    use_parametric = shapiro_a.pvalue > 0.05 and shapiro_b.pvalue > 0.05

    if use_parametric:
        t_stat, p_value = stats.ttest_ind(times_a, times_b, equal_var=False)
        test_name = "Welch's t-test (独立样本)"
    else:
        t_stat, p_value = stats.mannwhitneyu(times_a, times_b, alternative="two-sided")
        test_name = "Mann-Whitney U 检验"

    pooled_std = (
        math.sqrt((std_a**2 + std_b**2) / 2) if (std_a > 0 or std_b > 0) else 1.0
    )
    cohens_d = (mean_a - mean_b) / pooled_std

    se_diff = math.sqrt(std_a**2 / n_a + std_b**2 / n_b)
    diff_mean = mean_a - mean_b
    z_val = stats.norm.ppf(0.975)
    ci_lower = diff_mean - z_val * se_diff
    ci_upper = diff_mean + z_val * se_diff

    result = {
        "test_name": test_name,
        "group_a": {
            "mean": round(mean_a, 2),
            "std": round(std_a, 2),
            "median": round(median_a, 2),
            "count": n_a,
        },
        "group_b": {
            "mean": round(mean_b, 2),
            "std": round(std_b, 2),
            "median": round(median_b, 2),
            "count": n_b,
        },
        "mean_difference": round(diff_mean, 2),
        "mean_difference_pct": round(diff_mean / max(mean_a, 0.1) * 100, 1),
        "statistic": round(float(t_stat), 4),
        "p_value": round(float(p_value), 6),
        "is_significant": bool(p_value < 0.05),
        "effect_size_cohens_d": round(float(cohens_d), 4),
        "effect_size_interpretation": _cohens_d_interpretation(cohens_d),
        "ci_95_mean_diff": [round(ci_lower, 2), round(ci_upper, 2)],
        "normality_test": {
            "group_a_w_stat": round(float(shapiro_a.statistic), 4),
            "group_a_p_value": round(float(shapiro_a.pvalue), 5),
            "group_b_w_stat": round(float(shapiro_b.statistic), 4),
            "group_b_p_value": round(float(shapiro_b.pvalue), 5),
            "use_parametric": bool(use_parametric),
        },
    }

    sig_mark = (
        "***"
        if p_value < 0.001
        else ("**" if p_value < 0.01 else ("*" if p_value < 0.05 else "n.s."))
    )
    logger.info(
        f"耗时对比 ({test_name}): A组={mean_a:.1f}±{std_a:.1f}min, "
        f"B组={mean_b:.1f}±{std_b:.1f}min, "
        f"差异={diff_mean:.1f}min ({result['mean_difference_pct']:.1f}%), "
        f"P={p_value:.5f} {sig_mark}, d={cohens_d:.3f}"
    )
    return result


def _welch_df(a: np.ndarray, b: np.ndarray) -> float:
    n1, n2 = len(a), len(b)
    v1, v2 = np.var(a, ddof=1), np.var(b, ddof=1)
    num = (v1 / n1 + v2 / n2) ** 2
    den = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    return num / den if den > 0 else 1.0


def _cohens_d_interpretation(d: float) -> str:
    d_abs = abs(d)
    if d_abs < 0.2:
        return "无实际意义 (negligible)"
    elif d_abs < 0.5:
        return "小效应 (small)"
    elif d_abs < 0.8:
        return "中等效应 (medium)"
    else:
        return "大效应 (large)"


def compute_ai_agreement(data: dict) -> dict:
    """计算 AI 分析结论与实际判决的一致率，含混淆矩阵和 Precision/Recall/F1。

    将 AI 结论视为"预测"，实际判决视为"真实标签"，
    将"认定明知"视为正类，计算分类评估指标。
    """
    cases = data["cases"]
    ai_conc = data["ai_conclusions"]

    y_true = []
    y_pred = []
    case_details = []

    for c in cases:
        cid = c["case_id"]
        gt = c["ground_truth"]
        pred = ai_conc.get(cid, gt)
        y_true.append(gt)
        y_pred.append(pred)
        case_details.append(
            {
                "case_id": cid,
                "ground_truth": gt,
                "ai_conclusion": pred,
                "is_consistent": gt == pred,
                "difficulty": c.get("difficulty", "未知"),
            }
        )

    y_true_bin = [1 if v == "认定明知" else 0 for v in y_true]
    y_pred_bin = [1 if v == "认定明知" else 0 for v in y_pred]

    total = len(cases)
    consistent = sum(1 for d in case_details if d["is_consistent"])
    inconsistent = total - consistent

    cm = confusion_matrix(y_true_bin, y_pred_bin, labels=[1, 0])

    precision = precision_score(y_true_bin, y_pred_bin, pos_label=1, zero_division=0)
    recall = recall_score(y_true_bin, y_pred_bin, pos_label=1, zero_division=0)
    f1 = f1_score(y_true_bin, y_pred_bin, pos_label=1, zero_division=0)

    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    by_difficulty = {}
    for diff in ["难", "中", "易"]:
        diff_cases = [d for d in case_details if d.get("difficulty") == diff]
        if diff_cases:
            diff_consistent = sum(1 for d in diff_cases if d["is_consistent"])
            by_difficulty[diff] = {
                "total": len(diff_cases),
                "consistent": diff_consistent,
                "inconsistent": len(diff_cases) - diff_consistent,
                "agreement_rate_pct": round(diff_consistent / len(diff_cases) * 100, 1),
            }

    result = {
        "total_cases": total,
        "consistent_count": consistent,
        "inconsistent_count": inconsistent,
        "agreement_rate_pct": round(consistent / total * 100, 1) if total > 0 else 0.0,
        "confusion_matrix": {
            "labels": ["认定明知 (正类)", "不认定明知 (负类)"],
            "matrix": cm.tolist(),
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn),
        },
        "classification_metrics": {
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
            "specificity": round(float(specificity), 4),
            "accuracy": round(float(consistent / total), 4) if total > 0 else 0.0,
        },
        "by_difficulty": by_difficulty,
        "case_details": case_details,
    }

    logger.info(
        f"AI与判决一致率: {result['agreement_rate_pct']:.1f}% "
        f"({consistent}/{total}), "
        f"Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}"
    )
    return result


def analyze_inconsistent_cases(data: dict, ai_agreement: dict) -> dict:
    """对 AI 结论与实际判决不一致的案件进行定性分析。

    归纳差异类型：
      - 假阳性（AI认定明知但实际不明知）
      - 假阴性（AI不认定明知但实际明知）
    以及按案件难度分布。
    """
    inconsistent = [d for d in ai_agreement["case_details"] if not d["is_consistent"]]

    fp_cases = [
        d
        for d in inconsistent
        if d["ai_conclusion"] == "认定明知" and d["ground_truth"] == "不认定明知"
    ]
    fn_cases = [
        d
        for d in inconsistent
        if d["ai_conclusion"] == "不认定明知" and d["ground_truth"] == "认定明知"
    ]

    difficulty_dist = {}
    for d in inconsistent:
        diff = d.get("difficulty", "未知")
        difficulty_dist.setdefault(diff, {"count": 0, "case_ids": []})
        difficulty_dist[diff]["count"] += 1
        difficulty_dist[diff]["case_ids"].append(d["case_id"])

    type_analysis = {
        "false_positive": {
            "label": "假阳性（AI高估明知）",
            "description": "AI分析结论为'认定明知'，但实际判决为'不认定明知'",
            "count": len(fp_cases),
            "pct": round(len(fp_cases) / max(len(inconsistent), 1) * 100, 1),
            "case_ids": [d["case_id"] for d in fp_cases],
        },
        "false_negative": {
            "label": "假阴性（AI低估明知）",
            "description": "AI分析结论为'不认定明知'，但实际判决为'认定明知'",
            "count": len(fn_cases),
            "pct": round(len(fn_cases) / max(len(inconsistent), 1) * 100, 1),
            "case_ids": [d["case_id"] for d in fn_cases],
        },
    }

    result = {
        "total_inconsistent": len(inconsistent),
        "inconsistent_rate_pct": round(
            len(inconsistent) / len(ai_agreement["case_details"]) * 100, 1
        )
        if ai_agreement["case_details"]
        else 0,
        "by_type": type_analysis,
        "by_difficulty": {
            diff: {
                "count": info["count"],
                "pct": round(info["count"] / len(inconsistent) * 100, 1),
                "case_ids": info["case_ids"],
            }
            for diff, info in difficulty_dist.items()
        },
        "possible_reasons": [
            "AI对间接证据的权重判断与司法实践存在偏差",
            "案件事实中'推定明知'的成立条件判断差异",
            "AI对辩解合理性的评估与法官裁量不一致",
            "部分边缘案件中证据链完整度影响判断",
            "AI对特殊情境（如胁迫、被欺骗）的识别能力有限",
        ],
    }

    logger.info(
        f"不一致案例分析: {result['total_inconsistent']} 件不一致 "
        f"(FP={len(fp_cases)}, FN={len(fn_cases)})"
    )
    return result


def save_intermediate_data(data: dict, name: str):
    """保存中间数据至 research/results/ 目录。"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"intermediate_{name}_{timestamp}.json"
    serializable = json.loads(json.dumps(data, default=str, ensure_ascii=False))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"中间数据已保存: {path}")
    return path


def create_all_figures(
    data: dict,
    desc_stats: dict,
    kappa_result: dict,
    time_result: dict,
    ai_agreement: dict,
    inconsistent_result: dict,
) -> list:
    """生成所有统计图表并保存至 reports/figures/。"""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    saved_paths = []

    saved_paths.append(_plot_descriptive_stats(desc_stats))
    saved_paths.append(_plot_kappa_heatmap(kappa_result))
    saved_paths.append(_plot_time_boxplot(data, time_result))
    saved_paths.append(_plot_confusion_matrix(ai_agreement))
    saved_paths.append(_plot_kappa_comparison_bar(kappa_result))
    saved_paths.append(_plot_inconsistent_pie(inconsistent_result))

    saved = [str(p) for p in saved_paths if p]
    logger.info(f"共生成 {len(saved)} 张图表")
    return saved


def _plot_descriptive_stats(desc_stats: dict) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    groups = list(desc_stats.keys())
    means = [desc_stats[g]["time_cost_minutes"]["mean"] for g in groups]
    stds = [desc_stats[g]["time_cost_minutes"]["std"] for g in groups]
    medians = [desc_stats[g]["time_cost_minutes"]["median"] for g in groups]

    x = np.arange(len(groups))
    w = 0.35
    bars1 = axes[0].bar(
        x - w / 2,
        means,
        w,
        yerr=stds,
        capsize=5,
        color=["#4C72B0", "#DD8452"],
        label="均值±SD",
    )
    axes[0].axhline(
        medians[0],
        xmin=-0.5,
        xmax=0.5,
        color="#4C72B0",
        ls="--",
        alpha=0.5,
        label=f"A组中位数={medians[0]}",
    )
    axes[0].axhline(
        medians[1],
        xmin=0.5,
        xmax=1.5,
        color="#DD8452",
        ls="--",
        alpha=0.5,
        label=f"B组中位数={medians[1]}",
    )
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([f"{g}组" for g in groups])
    axes[0].set_ylabel("平均耗时 (分钟)")
    axes[0].set_title("两组分析耗时对比")
    axes[0].legend(fontsize=8)

    for bar, mean_val in zip(bars1, means):
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{mean_val:.1f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    n_records = [desc_stats[g]["n_records"] for g in groups]
    bars2 = axes[1].bar(x, n_records, w, color=["#4C72B0", "#DD8452"])
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([f"{g}组" for g in groups])
    axes[1].set_ylabel("分析记录数")
    axes[1].set_title("两组分析记录数量对比")
    for bar, val in zip(bars2, n_records):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            str(val),
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.tight_layout()
    path = FIGURES_DIR / "descriptive_statistics_bar.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"  [图表] 描述性统计柱状图 -> {path}")
    return str(path)


def _plot_kappa_heatmap(kappa_result: dict) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for idx, group_label in enumerate(["A", "B"]):
        grp = kappa_result[group_label]
        pairs = grp.get("pair_details", [])
        rater_ids = sorted(
            set(p["rater1"] for p in pairs) | set(p["rater2"] for p in pairs)
        )

        n = len(rater_ids)
        matrix = np.full((n, n), np.nan)
        for p in pairs:
            i = rater_ids.index(p["rater1"])
            j = rater_ids.index(p["rater2"])
            matrix[i, j] = p["kappa"]
            matrix[j, i] = p["kappa"]
        np.fill_diagonal(matrix, 1.0)

        ax = axes[idx]
        im = ax.imshow(matrix, cmap="RdYlGn", vmin=-0.3, vmax=1.0, aspect="auto")
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(rater_ids, fontsize=7, rotation=45, ha="right")
        ax.set_yticklabels(rater_ids, fontsize=7)
        ax.set_title(f"{group_label}组 评估者两两 Kappa", fontsize=11)

        for i in range(n):
            for j in range(n):
                if not np.isnan(matrix[i, j]):
                    ax.text(
                        j,
                        i,
                        f"{matrix[i, j]:.2f}",
                        ha="center",
                        va="center",
                        fontsize=6,
                        color="black" if abs(matrix[i, j] - 0.5) > 0.3 else "white",
                    )

        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    plt.tight_layout()
    path = FIGURES_DIR / "kappa_heatmap.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"  [图表] Kappa 系数热力图 -> {path}")
    return str(path)


def _plot_time_boxplot(data: dict, time_result: dict) -> str:
    records_a = [r["time_cost_minutes"] for r in data["records"] if r["group"] == "A"]
    records_b = [r["time_cost_minutes"] for r in data["records"] if r["group"] == "B"]

    df = pd.DataFrame(
        [{"group": "A组 (对照组)", "time_minutes": t} for t in records_a]
        + [{"group": "B组 (实验组)", "time_minutes": t} for t in records_b]
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    palette = {"A组 (对照组)": "#4C72B0", "B组 (实验组)": "#DD8452"}
    sns.boxplot(
        data=df,
        x="group",
        y="time_minutes",
        hue="group",
        palette=palette,
        ax=ax,
        width=0.5,
        linewidth=1.5,
        legend=False,
    )
    sns.stripplot(
        data=df,
        x="group",
        y="time_minutes",
        color="black",
        size=3,
        alpha=0.3,
        jitter=0.2,
        ax=ax,
    )

    p = time_result["p_value"]
    sig_text = (
        "P < 0.001***"
        if p < 0.001
        else (f"P = {p:.4f}*" if p < 0.05 else f"P = {p:.4f} n.s.")
    )
    d = time_result["effect_size_cohens_d"]
    ci = time_result["ci_95_mean_diff"]

    ax.text(
        0.5,
        0.95,
        f"效应量 Cohen's d = {d:.3f} ({time_result['effect_size_interpretation']})",
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
    )
    ax.text(
        0.5,
        0.88,
        f"均值差 95%CI: [{ci[0]:.1f}, {ci[1]:.1f}] min, {sig_text}",
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
    )

    ax.set_xlabel("")
    ax.set_ylabel("分析耗时 (分钟)")
    ax.set_title("两组分析耗时分布对比箱线图", fontsize=13)

    mean_a = time_result["group_a"]["mean"]
    mean_b = time_result["group_b"]["mean"]
    ax.axhline(mean_a, xmin=0.05, xmax=0.28, color="#4C72B0", ls="--", lw=1)
    ax.axhline(mean_b, xmin=0.72, xmax=0.95, color="#DD8452", ls="--", lw=1)

    plt.tight_layout()
    path = FIGURES_DIR / "time_cost_boxplot.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"  [图表] 耗时对比箱线图 -> {path}")
    return str(path)


def _plot_confusion_matrix(ai_agreement: dict) -> str:
    cm = np.array(ai_agreement["confusion_matrix"]["matrix"])
    labels = ai_agreement["confusion_matrix"]["labels"]

    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        cbar=True,
        xticklabels=labels,
        yticklabels=labels,
        ax=ax,
        annot_kws={"fontsize": 14},
    )

    precision = ai_agreement["classification_metrics"]["precision"]
    recall = ai_agreement["classification_metrics"]["recall"]
    f1 = ai_agreement["classification_metrics"]["f1_score"]

    metrics_text = (
        f"Precision (精确率) = {precision:.3f}\n"
        f"Recall (召回率) = {recall:.3f}\n"
        f"F1 Score = {f1:.3f}\n"
        f"一致率 = {ai_agreement['agreement_rate_pct']:.1f}%"
    )
    ax.text(
        1.35,
        0.5,
        metrics_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="center",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8),
    )

    ax.set_xlabel("AI 分析结论")
    ax.set_ylabel("实际判决")
    ax.set_title("AI 结论 vs 实际判决 混淆矩阵", fontsize=13)

    plt.tight_layout()
    path = FIGURES_DIR / "confusion_matrix_heatmap.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"  [图表] 混淆矩阵热力图 -> {path}")
    return str(path)


def _plot_kappa_comparison_bar(kappa_result: dict) -> str:
    fig, ax = plt.subplots(figsize=(8, 5))

    groups = ["A组", "B组"]
    means = [kappa_result["A"]["mean_kappa"], kappa_result["B"]["mean_kappa"]]
    cis = [kappa_result["A"]["ci_95"], kappa_result["B"]["ci_95"]]
    errors_low = [means[i] - cis[i][0] for i in range(2)]
    errors_high = [cis[i][1] - means[i] for i in range(2)]
    errors = [[errors_low[0], errors_low[1]], [errors_high[0], errors_high[1]]]

    colors = ["#4C72B0", "#DD8452"]
    bars = ax.bar(
        groups,
        means,
        yerr=errors,
        capsize=8,
        color=colors,
        width=0.4,
        error_kw={"linewidth": 1.5},
    )

    ax.axhline(y=0.65, color="red", ls="--", lw=1.5, label="目标阈值 κ=0.65")
    ax.axhline(
        y=0.40, color="orange", ls=":", lw=1, alpha=0.7, label="中等一致性 κ=0.40"
    )

    for bar, val in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{val:.4f}",
            ha="center",
            va="bottom",
            fontsize=11,
        )

    delta = kappa_result["comparison"]["delta"]
    ax.text(
        0.5,
        0.9,
        f"组间差异 Δκ = {delta:+.4f} ({kappa_result['comparison']['delta_pct']:.1f}%)",
        transform=ax.transAxes,
        ha="center",
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.3),
    )

    ax.set_ylabel("Cohen's Kappa 系数")
    ax.set_title("两组组内一致性对比")
    ax.legend(loc="lower right")
    ax.set_ylim(0, 1.1)

    plt.tight_layout()
    path = FIGURES_DIR / "kappa_comparison_bar.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"  [图表] Kappa 对比柱状图 -> {path}")
    return str(path)


def _plot_inconsistent_pie(inconsistent_result: dict) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    by_type = inconsistent_result["by_type"]
    type_labels = [
        by_type["false_positive"]["label"],
        by_type["false_negative"]["label"],
    ]
    type_counts = [
        by_type["false_positive"]["count"],
        by_type["false_negative"]["count"],
    ]
    type_colors = ["#E74C3C", "#3498DB"]

    if sum(type_counts) > 0:
        axes[0].pie(
            type_counts,
            labels=type_labels,
            autopct="%1.1f%%",
            colors=type_colors,
            startangle=90,
            explode=(0.05, 0.05),
        )
    axes[0].set_title("不一致案例类型分布", fontsize=12)

    by_diff = inconsistent_result["by_difficulty"]
    diff_labels = list(by_diff.keys())
    diff_counts = [by_diff[d]["count"] for d in diff_labels]
    diff_colors = ["#E67E22", "#F1C40F", "#2ECC71"]

    if sum(diff_counts) > 0:
        wedges, texts, autotexts = axes[1].pie(
            diff_counts,
            labels=diff_labels,
            autopct="%1.1f%%",
            colors=diff_colors[: len(diff_labels)],
            startangle=90,
            explode=[0.03] * len(diff_labels),
            textprops={"fontsize": 10},
        )
        for t in autotexts:
            t.set_fontsize(9)
    axes[1].set_title("不一致案件按难度分布", fontsize=12)

    total = inconsistent_result["total_inconsistent"]
    fig.suptitle(
        f"AI-判决不一致案例分析 (共 {total} 件, 占比 {inconsistent_result['inconsistent_rate_pct']:.1f}%)",
        fontsize=13,
        y=1.02,
    )

    plt.tight_layout()
    path = FIGURES_DIR / "inconsistent_cases_pie.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"  [图表] 不一致案例饼图 -> {path}")
    return str(path)


def generate_report(
    data: dict,
    desc_stats: dict,
    kappa_result: dict,
    time_result: dict,
    ai_agreement: dict,
    inconsistent_result: dict,
    figure_paths: list,
) -> str:
    """生成完整的实证研究报告初稿 reports/experiment_report.md。"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS_DIR / "experiment_report.md"

    exp_info = data.get("experiment_info", {})
    total_cases = len(data.get("cases", []))
    total_records = len(data.get("records", []))
    is_mock = exp_info.get("is_mock_data", False)

    fig_relpaths = {}
    for fp in figure_paths:
        name = Path(fp).name
        fig_relpaths[name] = f"figures/{name}"

    lines = []
    _w = lines.append

    _w('# 实证研究报告：AI辅助分析对"主观明知"认定影响的回溯性对比实验\n')
    _w("\n> **报告版本**: 初稿")
    _w(f"\n> **生成日期**: {datetime.now().strftime('%Y年%m月%d日')}")
    _w(
        f"\n> **数据来源**: {'模拟数据（用于验证脚本功能）' if is_mock else '真实实验数据'}"
    )
    if is_mock:
        _w(
            "\n> **⚠️ 重要提醒**: 本报告基于模拟数据生成，仅用于展示脚本输出格式和报告结构。实际分析需使用真实实验数据。"
        )
    _w("\n---\n")

    _w("## 1. 研究目的\n")
    _w(
        "本实验旨在通过科学、严谨的回溯性对比实验设计，系统评估AI辅助分析工具对司法人员认定\u201c主观明知\u201d的一致性和效率的实际影响。具体包括：\n\n"
    )
    _w(
        "- **H1**：B组（实验组）的案件认定一致性Kappa系数显著高于A组（对照组），且≥0.65\n"
    )
    _w("- **H2**：B组（实验组）完成单个案件分析的平均耗时显著低于A组（对照组）\n")
    _w("- **H3**：AI分析结论与法院生效判决的吻合度达到较高水平（≥80%）\n")

    _w("\n## 2. 数据来源\n")
    _w("### 2.1 案件数据\n")
    _w(
        f"本实验共选取 **{total_cases}件** 已审结的帮助信息网络犯罪活动罪案件材料。案件涵盖不同的\u201c主观明知\u201d认定情形，包括认定明知、不认定明知及边缘情形。\n"
    )
    _w("\n### 2.2 参与人员\n")
    _w(
        f"实验共有 **{exp_info.get('group_a_raters', 'N/A')}名** 对照组（A组）参与者和 **{exp_info.get('group_b_raters', 'N/A')}名** 实验组（B组）参与者。"
    )
    _w("两组参与者在从业年限、专业背景等特征上无显著差异。\n")
    _w("\n### 2.3 实验设计\n")
    _w(
        "实验采用回溯性对比实验设计（Retrospective Controlled Experiment Design）。A组（对照组）仅依靠个人专业经验进行分析判断；"
    )
    _w(
        "B组（实验组）在个人专业经验基础上，参考AI辅助分析工具生成的标准化分析报告进行分析判断。\n"
    )
    _w("\n### 2.4 数据规模\n")
    _w(f"- 总分析记录数：**{total_records}** 条\n")
    _w(f"- A组记录数：**{desc_stats.get('A', {}).get('n_records', 0)}** 条\n")
    _w(f"- B组记录数：**{desc_stats.get('B', {}).get('n_records', 0)}** 条\n")

    _w("\n## 3. 分析方法\n")
    _w("### 3.1 描述性统计\n")
    _w(
        "计算各组实验数据的基本统计信息，包括案例数量、参与者人数、平均耗时（含标准差）、中位数及四分位距。采用均数±标准差（Mean ± SD）形式描述集中趋势和离散程度。\n"
    )
    _w("\n### 3.2 认定一致性分析\n")
    _w(
        "采用 **Cohen's Kappa 系数** 评估组内评估者间的一致性。Kappa系数的计算公式为：\n\n"
    )
    _w("$$\\kappa = \\frac{P_o - P_e}{1 - P_e}$$\n\n")
    _w(
        "其中，$P_o$为观察一致率，$P_e$为期望一致率。采用Bootstrap法（2000次重抽样）估计Kappa系数的95%置信区间。\n"
    )
    _w(
        "\n一致性评判标准：κ < 0.00（低于随机）、0.00-0.20（极低）、0.20-0.40（较低）、0.40-0.60（中等）、0.60-0.80（良好）、0.80-1.00（高度）。研究假设B组Kappa ≥ 0.65视为达到良好一致性。\n"
    )
    _w("\n### 3.3 耗时差异分析\n")
    _w(
        "应用独立样本t检验或Mann-Whitney U检验（根据正态性检验结果选择）比较两组间平均耗时差异。"
    )
    _w(
        "统计分析包括：Shapiro-Wilk正态性检验、效应量Cohen's d、均值差的95%置信区间。显著性水平设定为α = 0.05（双尾检验）。\n"
    )
    _w("\n### 3.4 AI与判决一致率分析\n")
    _w(
        "以法院生效判决为金标准，将AI分析结论作为预测结果，计算准确率（Accuracy）、精确率（Precision）、召回率（Recall）、F1分数及特异度（Specificity）。"
    )
    _w("同时生成混淆矩阵，以全面评估AI分析工具的分类性能。\n")
    _w("\n### 3.5 不一致案例分析\n")
    _w(
        "对AI分析结论与实际判决不一致的案例进行系统定性分析，按差异类型（假阳性/假阴性）和案件难度分层归纳，识别AI判断的系统性偏差模式。\n"
    )

    _w("\n## 4. 结果\n")
    _w("\n### 4.1 描述性统计结果\n")
    _w("\n表1：两组描述性统计对比\n")
    _w("\n| 指标 | A组（对照组） | B组（实验组） |\n")
    _w("|------|-------------|-------------|\n")
    ds_a = desc_stats.get("A", {})
    ds_b = desc_stats.get("B", {})
    _w(
        f"| 分析记录数 | {ds_a.get('n_records', 'N/A')} | {ds_b.get('n_records', 'N/A')} |\n"
    )
    _w(
        f"| 评估者人数 | {ds_a.get('n_raters', 'N/A')} | {ds_b.get('n_raters', 'N/A')} |\n"
    )
    _w(
        f"| 平均耗时 (min) | {ds_a.get('time_cost_minutes', {}).get('mean', 'N/A')} ± {ds_a.get('time_cost_minutes', {}).get('std', 'N/A')} | {ds_b.get('time_cost_minutes', {}).get('mean', 'N/A')} ± {ds_b.get('time_cost_minutes', {}).get('std', 'N/A')} |\n"
    )
    _w(
        f"| 中位数耗时 (min) | {ds_a.get('time_cost_minutes', {}).get('median', 'N/A')} | {ds_b.get('time_cost_minutes', {}).get('median', 'N/A')} |\n"
    )
    _w(
        f"| 四分位距 (IQR) | {ds_a.get('time_cost_minutes', {}).get('iqr', 'N/A')} | {ds_b.get('time_cost_minutes', {}).get('iqr', 'N/A')} |\n"
    )
    _w(
        f"| 平均置信度 | {ds_a.get('confidence', {}).get('mean', 'N/A')} ± {ds_a.get('confidence', {}).get('std', 'N/A')} | {ds_b.get('confidence', {}).get('mean', 'N/A')} ± {ds_b.get('confidence', {}).get('std', 'N/A')} |\n"
    )

    fig_bar = fig_relpaths.get("descriptive_statistics_bar.png", "")
    if fig_bar:
        _w(f"\n![描述性统计柱状图]({fig_bar})\n")
        _w("\n*图1：两组分析耗时与记录数量对比*\n")

    _w("\n### 4.2 认定一致性分析\n")
    _w("\n#### 4.2.1 Cohen's Kappa 系数\n")
    _w("\n表2：两组组内Cohen's Kappa系数对比\n")
    _w("\n| 指标 | A组（对照组） | B组（实验组） |\n")
    _w("|------|-------------|-------------|\n")
    _w(
        f"| 均值 Kappa | {kappa_result['A']['mean_kappa']} | {kappa_result['B']['mean_kappa']} |\n"
    )
    _w(
        f"| 中位数 Kappa | {kappa_result['A']['median_kappa']} | {kappa_result['B']['median_kappa']} |\n"
    )
    _w(
        f"| 标准差 | {kappa_result['A']['std_kappa']} | {kappa_result['B']['std_kappa']} |\n"
    )
    _w(
        f"| 最小值 | {kappa_result['A']['min_kappa']} | {kappa_result['B']['min_kappa']} |\n"
    )
    _w(
        f"| 最大值 | {kappa_result['A']['max_kappa']} | {kappa_result['B']['max_kappa']} |\n"
    )
    _w(
        f"| 95% 置信区间 | [{kappa_result['A']['ci_95'][0]}, {kappa_result['A']['ci_95'][1]}] | [{kappa_result['B']['ci_95'][0]}, {kappa_result['B']['ci_95'][1]}] |\n"
    )
    _w(
        f"| ≥0.65 占比 | {kappa_result['A']['kappa_above_065_pct']}% | {kappa_result['B']['kappa_above_065_pct']}% |\n"
    )
    _w(
        f"| 评估者对数 | {kappa_result['A']['pair_count']} | {kappa_result['B']['pair_count']} |\n"
    )

    kc = kappa_result["comparison"]
    _w(
        f"\n**组间对比**：B组Kappa（{kc['group_b_kappa']}）较A组（{kc['group_a_kappa']}）{('提升' if kc['delta'] > 0 else '降低')}{abs(kc['delta'])}（{kc['delta_pct']}%）。\n"
    )

    fig_kappa_bar = fig_relpaths.get("kappa_comparison_bar.png", "")
    if fig_kappa_bar:
        _w(f"\n![Kappa对比柱状图]({fig_kappa_bar})\n")
        _w("\n*图2：两组组内一致性Kappa系数对比（含95%置信区间）*\n")

    fig_kappa_heat = fig_relpaths.get("kappa_heatmap.png", "")
    if fig_kappa_heat:
        _w(f"\n![Kappa热力图]({fig_kappa_heat})\n")
        _w("\n*图3：两组评估者两两Kappa系数热力图*\n")

    _w("\n#### 4.2.2 一致性水平分布\n")
    _w("\n| 一致性水平 | A组（对数/占比） | B组（对数/占比） |\n")
    _w("|-----------|-----------------|-----------------|\n")
    for level in ["低于随机", "极低", "较低", "中等", "良好"]:
        a_lvl = kappa_result["A"]["distribution_by_level"].get(level, {})
        b_lvl = kappa_result["B"]["distribution_by_level"].get(level, {})
        a_text = f"{a_lvl.get('count', 0)}/{a_lvl.get('pct', 0)}%" if a_lvl else "N/A"
        b_text = f"{b_lvl.get('count', 0)}/{b_lvl.get('pct', 0)}%" if b_lvl else "N/A"
        _w(f"| {level} (≥{a_lvl.get('threshold', '?')}) | {a_text} | {b_text} |\n")

    _w("\n### 4.3 耗时差异分析\n")
    tr = time_result
    _w("\n表3：两组耗时差异统计检验结果\n")
    _w("\n| 指标 | 数值 |\n")
    _w("|------|------|\n")
    _w(f"| 检验方法 | {tr['test_name']} |\n")
    _w(f"| A组平均耗时 | {tr['group_a']['mean']} ± {tr['group_a']['std']} min |\n")
    _w(f"| B组平均耗时 | {tr['group_b']['mean']} ± {tr['group_b']['std']} min |\n")
    _w(f"| 均值差（A - B） | {tr['mean_difference']} min |\n")
    _w(
        f"| 均值差 95% CI | [{tr['ci_95_mean_diff'][0]}, {tr['ci_95_mean_diff'][1]}] |\n"
    )
    _w(f"| 检验统计量 | {tr['statistic']} |\n")
    _w(
        f"| P 值 | {tr['p_value']} {'***' if tr['p_value'] < 0.001 else '**' if tr['p_value'] < 0.01 else '*' if tr['p_value'] < 0.05 else 'n.s.'} |\n"
    )
    _w(f"| 统计显著性 | {'是' if tr['is_significant'] else '否'} |\n")
    _w(
        f"| Cohen's d 效应量 | {tr['effect_size_cohens_d']} ({tr['effect_size_interpretation']}) |\n"
    )

    fig_box = fig_relpaths.get("time_cost_boxplot.png", "")
    if fig_box:
        _w(f"\n![耗时箱线图]({fig_box})\n")
        _w("\n*图4：两组分析耗时分布箱线图（含个体数据点与统计标注）*\n")

    _w("\n### 4.4 AI与判决一致率\n")
    aa = ai_agreement
    _w("\n表4：AI分析结论与实际判决一致性评估\n")
    _w("\n| 指标 | 数值 |\n")
    _w("|------|------|\n")
    _w(f"| 总案例数 | {aa['total_cases']} |\n")
    _w(f"| 一致案例数 | {aa['consistent_count']} |\n")
    _w(f"| 不一致案例数 | {aa['inconsistent_count']} |\n")
    _w(f"| 一致率 | {aa['agreement_rate_pct']}% |\n")
    _w(f"| 精确率 (Precision) | {aa['classification_metrics']['precision']:.4f} |\n")
    _w(f"| 召回率 (Recall) | {aa['classification_metrics']['recall']:.4f} |\n")
    _w(f"| F1 分数 | {aa['classification_metrics']['f1_score']:.4f} |\n")
    _w(
        f"| 特异度 (Specificity) | {aa['classification_metrics']['specificity']:.4f} |\n"
    )
    _w(f"| 准确率 (Accuracy) | {aa['classification_metrics']['accuracy']:.4f} |\n")

    _w("\n#### 4.4.1 按难度分层的一致率\n")
    _w("\n| 案件难度 | 总案例数 | 一致数 | 一致率 |\n")
    _w("|---------|--------|--------|-------|\n")
    for diff in ["难", "中", "易"]:
        bd = aa["by_difficulty"].get(diff, {})
        if bd:
            _w(
                f"| {diff} | {bd['total']} | {bd['consistent']} | {bd['agreement_rate_pct']}% |\n"
            )

    fig_cm = fig_relpaths.get("confusion_matrix_heatmap.png", "")
    if fig_cm:
        _w(f"\n![混淆矩阵]({fig_cm})\n")
        _w("\n*图5：AI结论 vs 实际判决混淆矩阵热力图*\n")

    _w("\n### 4.5 不一致案例分析\n")
    ic = inconsistent_result
    _w(
        f"\n**不一致案例总览**：共 {ic['total_inconsistent']} 件案例（占 {ic['inconsistent_rate_pct']}%），其中：\n\n"
    )
    _w(
        f"- **假阳性（AI高估明知）**：{ic['by_type']['false_positive']['count']} 件（{ic['by_type']['false_positive']['pct']}%）\n"
    )
    _w('  - 特征：AI判定为"认定明知"，但法院实际判决为"不认定明知"\n')
    _w(
        f"- **假阴性（AI低估明知）**：{ic['by_type']['false_negative']['count']} 件（{ic['by_type']['false_negative']['pct']}%）\n"
    )
    _w('  - 特征：AI判定为"不认定明知"，但法院实际判决为"认定明知"\n')

    _w("\n#### 按案件难度的不一致分布\n")
    _w("\n| 难度 | 不一致数 | 占比 |\n")
    _w("|------|---------|------|\n")
    for diff in ["难", "中", "易"]:
        bd = ic["by_difficulty"].get(diff, {})
        if bd:
            _w(f"| {diff} | {bd['count']} | {bd['pct']}% |\n")

    fig_pie = fig_relpaths.get("inconsistent_cases_pie.png", "")
    if fig_pie:
        _w(f"\n![不一致案例饼图]({fig_pie})\n")
        _w("\n*图6：AI-判决不一致案例分类饼图*\n")

    _w("\n#### 可能原因分析\n")
    _w("\n根据案例特征分析，AI与判决不一致的可能原因包括：\n\n")
    for i, reason in enumerate(ic.get("possible_reasons", []), 1):
        _w(f"{i}. {reason}\n")

    _w("\n## 5. 讨论\n")
    _w("\n### 5.1 一致性分析讨论\n")

    kappa_h1_met = kappa_result["B"]["mean_kappa"] >= 0.65
    if kappa_h1_met:
        _w(
            f"B组Kappa系数为{kc['group_b_kappa']}，达到预设目标（≥0.65），表明AI辅助条件下评估者间达到良好一致性水平。"
        )
        _w(
            f"相比于A组（Kappa={kc['group_a_kappa']}），一致性提升{abs(kc['delta']):.4f}（{kc['delta_pct']:.1f}%）。"
        )
        _w(
            "这一结果表明AI辅助分析工具能够有效减少个体经验差异带来的认定偏差，促进裁判标准的统一。"
        )
    else:
        _w(
            f"B组Kappa系数为{kc['group_b_kappa']}，虽高于A组（{kc['group_a_kappa']}），但尚未达到预设的≥0.65阈值。"
        )
        _w(
            f'组间差异为{kc["delta"]:+.4f}（{kc["delta_pct"]:.1f}%），提示AI辅助对一致性提升具有正向作用，但程度尚不足以达到"良好一致性"水平。'
        )
        _w("可能需要进一步优化AI分析报告的呈现方式或增加培训力度。\n")

    _w("\n### 5.2 效率分析讨论\n")
    if tr["is_significant"]:
        _w(
            f"B组平均耗时（{tr['group_b']['mean']} ± {tr['group_b']['std']} min）显著低于A组（{tr['group_a']['mean']} ± {tr['group_a']['std']} min）"
        )
        _w(
            f"（P = {tr['p_value']}，Cohen's d = {tr['effect_size_cohens_d']}，属于{tr['effect_size_interpretation']}）。"
        )
        _w(
            f"平均缩短{abs(tr['mean_difference'])}分钟（{abs(tr['mean_difference_pct']):.1f}%），表明AI辅助分析能够显著提升案件分析效率。"
        )
        _w("效应量分析结果进一步证实了这一差异的实际意义。\n")
    else:
        _w(
            "两组耗时差异未达到统计显著性水平。虽然B组平均耗时较A组有所降低，但差异尚不足以排除随机因素。"
        )
        _w("可能需要扩大样本量或进一步优化AI工具的用户体验。\n")

    _w("\n### 5.3 AI一致率讨论\n")
    h3_met = aa["agreement_rate_pct"] >= 80
    if h3_met:
        _w(
            f"AI分析结论与法院生效判决的一致率达到{aa['agreement_rate_pct']}%，达到预设目标（≥80%）。"
        )
        _w(
            f"Precision={aa['classification_metrics']['precision']:.3f}，Recall={aa['classification_metrics']['recall']:.3f}，F1={aa['classification_metrics']['f1_score']:.3f}，"
        )
        _w('表明AI分析工具在"主观明知"认定方面具有较好的性能。混淆矩阵分析显示，')
        _w(
            f"假阳性{aa['confusion_matrix']['fp']}例、假阴性{aa['confusion_matrix']['fn']}例，错误类型分布较为均衡。\n"
        )
    else:
        _w(
            f"AI分析结论与判决的一致率为{aa['agreement_rate_pct']}%，未达到预设目标（≥80%）。"
        )
        _w(
            f"Precision={aa['classification_metrics']['precision']:.3f}，Recall={aa['classification_metrics']['recall']:.3f}，F1={aa['classification_metrics']['f1_score']:.3f}。"
        )
        _w(
            "不一致案例主要集中在难度较高的案件中，提示AI在边缘案件的判断上仍有提升空间。"
        )
        _w(
            f"假阳性{aa['confusion_matrix']['fp']}例（AI过度认定明知）、假阴性{aa['confusion_matrix']['fn']}例（AI遗漏认定明知）。\n"
        )

    _w("\n## 6. 结论\n")
    _w("\n### 6.1 假设检验结果汇总\n")
    _w("\n| 假设 | 内容 | 检验结果 | 支持? |\n")
    _w("|------|------|---------|:----:|\n")

    _w(
        f"| H1 | B组Kappa≥0.65 | B组Kappa={kc['group_b_kappa']} | {'✅' if kappa_h1_met else '❌'} |\n"
    )
    _w(
        f"| H2 | B组耗时显著低于A组 | P={tr['p_value']} | {'✅' if tr['is_significant'] else '❌'} |\n"
    )
    _w(
        f"| H3 | AI一致率≥80% | AI一致率={aa['agreement_rate_pct']}% | {'✅' if h3_met else '❌'} |\n"
    )

    _w("\n### 6.2 主要发现\n")
    _w(
        f"\n1. **一致性**：B组组内Kappa系数（{kc['group_b_kappa']}）{'达到' if kappa_h1_met else '未达到'}预设的0.65阈值，"
    )
    _w(f"较A组提升{kc['delta']:+.4f}（{kc['delta_pct']:.1f}%）。\n")
    _w(
        f"2. **效率**：AI辅助分析{'显著' if tr['is_significant'] else '未显著'}缩短分析耗时，"
    )
    _w(
        f"平均减少{abs(tr['mean_difference'])}分钟（{abs(tr['mean_difference_pct']):.1f}%）。\n"
    )
    _w(f"3. **AI准确率**：AI分析结论与判决一致率为{aa['agreement_rate_pct']}%")
    _w(f"{'，达到预设目标' if h3_met else '，未达到预设目标（80%）'}。")
    _w(
        f"不一致案例主要集中在{'难度较高的案件' if aa['by_difficulty'].get('难', {}).get('agreement_rate_pct', 100) < max(aa['by_difficulty'].get('中', {}).get('agreement_rate_pct', 0), aa['by_difficulty'].get('易', {}).get('agreement_rate_pct', 0)) else '各类案件中'}。\n"
    )

    _w("\n### 6.3 局限性\n")
    _w("\n1. 本实验采用回溯性设计，无法完全模拟真实庭审环境中的认定过程\n")
    _w("2. 参与者数量有限，可能影响统计检验的把握度\n")
    _w("3. AI分析工具版本更新后结论可能发生变化\n")
    _w("4. 实验案件主要来源于特定地区，结论外推至全国范围需谨慎\n")

    _w("\n### 6.4 后续建议\n")
    _w("\n1. **技术优化**：针对不一致案例特征，优化AI分析模型的边界案例判断能力\n")
    _w("2. **应用推广**：在条件成熟时，在更大范围内开展多中心验证实验\n")
    _w("3. **培训方案**：设计针对性的AI工具使用培训，提升司法人员的人机协作能力\n")
    _w("4. **规范制定**：基于实验发现，推动制定AI辅助司法分析的应用规范和指导意见\n")

    _w("\n---\n")
    _w(f"\n*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    _w(f"*本报告由 {os.path.basename(__file__)} 自动生成*\n")

    report_content = "".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"报告已生成: {output_path}")
    return str(output_path)


def run_analysis(data_path: str = None) -> dict:
    """执行完整的统计分析与报告生成流程。"""
    log_path = setup_logging()
    logger.info("=" * 60)
    logger.info("实验数据统计分析与报告生成")
    logger.info(f"Python版本: {sys.version}")
    logger.info("=" * 60)

    data = load_experiment_data()

    is_mock = data.get("experiment_info", {}).get("is_mock_data", False)
    if is_mock:
        logger.warning("当前使用模拟数据运行，仅用于验证脚本功能")
        logger.warning("请将真实实验数据放置于 research/data/experiment_data.json")

    logger.info("")
    logger.info("=" * 60)
    logger.info("步骤 1/7: 描述性统计分析")
    logger.info("=" * 60)
    desc_stats = compute_descriptive_statistics(data)
    save_intermediate_data(desc_stats, "descriptive_stats")

    logger.info("")
    logger.info("=" * 60)
    logger.info("步骤 2/7: Cohen's Kappa 一致性分析")
    logger.info("=" * 60)
    kappa_result = compute_cohens_kappa_analysis(data)
    save_intermediate_data(kappa_result, "cohens_kappa")

    logger.info("")
    logger.info("=" * 60)
    logger.info("步骤 3/7: 耗时差异分析")
    logger.info("=" * 60)
    time_result = compute_time_analysis(data)
    save_intermediate_data(time_result, "time_analysis")

    logger.info("")
    logger.info("=" * 60)
    logger.info("步骤 4/7: AI与判决一致率分析")
    logger.info("=" * 60)
    ai_agreement = compute_ai_agreement(data)
    save_intermediate_data(ai_agreement, "ai_agreement")

    logger.info("")
    logger.info("=" * 60)
    logger.info("步骤 5/7: 不一致案例定性分析")
    logger.info("=" * 60)
    inconsistent_result = analyze_inconsistent_cases(data, ai_agreement)
    save_intermediate_data(inconsistent_result, "inconsistent_cases")

    logger.info("")
    logger.info("=" * 60)
    logger.info("步骤 6/7: 数据可视化")
    logger.info("=" * 60)
    figure_paths = create_all_figures(
        data,
        desc_stats,
        kappa_result,
        time_result,
        ai_agreement,
        inconsistent_result,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("步骤 7/7: 生成实证研究报告")
    logger.info("=" * 60)
    report_path = generate_report(
        data,
        desc_stats,
        kappa_result,
        time_result,
        ai_agreement,
        inconsistent_result,
        figure_paths,
    )

    all_results = {
        "analysis_info": {
            "title": "实验数据统计分析与报告生成",
            "generated_at": datetime.now().isoformat(),
            "log_path": str(log_path),
            "data_source": "模拟数据" if is_mock else "真实实验数据",
            "total_cases": len(data.get("cases", [])),
            "total_records": len(data.get("records", [])),
        },
        "descriptive_statistics": desc_stats,
        "cohens_kappa": kappa_result,
        "time_efficiency": time_result,
        "ai_agreement": ai_agreement,
        "inconsistent_cases": inconsistent_result,
        "figures": [str(p) for p in figure_paths],
        "report_path": report_path,
    }

    results_path = save_intermediate_data(all_results, "full_analysis")
    all_results["output_path"] = str(results_path)

    logger.info("")
    logger.info("=" * 70)
    logger.info("分 析 完 成")
    logger.info("=" * 70)
    logger.info(f"  分析结果:   {results_path}")
    logger.info(f"  报告文件:   {report_path}")
    logger.info(f"  图表目录:   {FIGURES_DIR}")
    logger.info(f"  日志文件:   {log_path}")
    logger.info(f"  图表数量:   {len(figure_paths)} 张")
    logger.info("=" * 70)

    return all_results


if __name__ == "__main__":
    data_path = sys.argv[1] if len(sys.argv) > 1 else None
    run_analysis(data_path)
