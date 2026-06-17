import os
import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from itertools import combinations

import scipy.stats as stats
from sklearn.metrics import cohen_kappa_score
from loguru import logger


_project_root = Path(__file__).resolve().parent.parent
_data_dir = _project_root / "research" / "data"
_output_dir = _project_root / "research" / "results"


def setup_logging():
    _output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = _output_dir / f"statistical_analysis_{timestamp}.log"
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


def load_experiment_data(data_path: str = None) -> dict:
    if data_path is None:
        data_path = str(_data_dir / "experiment_data.json")
    logger.info(f"加载实验数据: {data_path}")
    if not os.path.exists(data_path):
        logger.warning(f"数据文件不存在，使用模拟数据: {data_path}")
        return _generate_mock_data()
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"数据加载完成: {len(data.get('records', []))} 条分析记录")
    return data


def _generate_mock_data(seed: int = 42) -> dict:
    np.random.seed(seed)
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
            if np.random.random() < agreement_prob:
                conclusion = gt
            else:
                conclusion = "不认定明知" if gt == "认定明知" else "认定明知"
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
            if np.random.random() < agreement_prob:
                conclusion = gt
            else:
                conclusion = "不认定明知" if gt == "认定明知" else "认定明知"
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


def compute_cohens_kappa_for_group(data: dict, group: str) -> dict:
    records = [r for r in data["records"] if r["group"] == group]
    rater_ids = sorted(set(r["rater_id"] for r in records))

    all_kappas = []
    pair_results = []

    for r1, r2 in combinations(rater_ids, 2):
        r1_records = {
            r["case_id"]: r["conclusion"] for r in records if r["rater_id"] == r1
        }
        r2_records = {
            r["case_id"]: r["conclusion"] for r in records if r["rater_id"] == r2
        }
        common_cases = sorted(set(r1_records.keys()) & set(r2_records.keys()))
        if len(common_cases) < 5:
            continue
        ratings1 = [r1_records[c] for c in common_cases]
        ratings2 = [r2_records[c] for c in common_cases]

        kappa = cohen_kappa_score(ratings1, ratings2)
        all_kappas.append(kappa)
        pair_results.append(
            {
                "rater1": r1,
                "rater2": r2,
                "kappa": round(kappa, 4),
                "n_cases": len(common_cases),
            }
        )

    result = {
        "group": group,
        "mean_kappa": round(float(np.mean(all_kappas)), 4),
        "median_kappa": round(float(np.median(all_kappas)), 4),
        "std_kappa": round(float(np.std(all_kappas)), 4),
        "min_kappa": round(float(np.min(all_kappas)), 4),
        "max_kappa": round(float(np.max(all_kappas)), 4),
        "kappa_above_threshold_pct": round(
            float(np.mean(np.array(all_kappas) >= 0.65) * 100), 1
        ),
        "pair_count": len(all_kappas),
        "pair_details": pair_results,
    }
    logger.info(
        f"  {group}组 Cohen's Kappa: μ={result['mean_kappa']:.4f}, SD={result['std_kappa']:.4f}, ≥0.65占比={result['kappa_above_threshold_pct']:.1f}%"
    )
    return result


def compute_fleiss_kappa(data: dict, group: str) -> float:
    records = [r for r in data["records"] if r["group"] == group]
    case_ids = sorted(set(r["case_id"] for r in records))
    categories = sorted(set(r["conclusion"] for r in records))
    cat_to_idx = {cat: i for i, cat in enumerate(categories)}
    n_cases = len(case_ids)
    n_raters = len(set(r["rater_id"] for r in records))

    matrix = np.zeros((n_cases, len(categories)), dtype=int)
    case_list = sorted(set(r["case_id"] for r in records))
    case_to_idx = {c: i for i, c in enumerate(case_list)}

    for r in records:
        i = case_to_idx[r["case_id"]]
        j = cat_to_idx[r["conclusion"]]
        matrix[i, j] += 1

    p_j = matrix.sum(axis=0) / (n_cases * n_raters)
    P_i = (np.sum(matrix**2, axis=1) - n_raters) / (n_raters * (n_raters - 1))
    P_bar = np.mean(P_i)
    P_e = np.sum(p_j**2)
    kappa = (P_bar - P_e) / (1 - P_e) if (1 - P_e) > 0 else 0.0

    logger.info(f"  {group}组 Fleiss' Kappa: {kappa:.4f}")
    return round(float(kappa), 4)


def compare_kappa_between_groups(group_a_kappa: dict, group_b_kappa: dict) -> dict:
    result = {
        "group_a_kappa": group_a_kappa["mean_kappa"],
        "group_b_kappa": group_b_kappa["mean_kappa"],
        "delta": round(group_b_kappa["mean_kappa"] - group_a_kappa["mean_kappa"], 4),
        "delta_pct": round(
            (group_b_kappa["mean_kappa"] - group_a_kappa["mean_kappa"])
            / max(abs(group_a_kappa["mean_kappa"]), 0.001)
            * 100,
            2,
        ),
    }
    logger.info(
        f"组间Kappa对比: A组={result['group_a_kappa']:.4f}, B组={result['group_b_kappa']:.4f}, 差异={result['delta']:+.4f} ({result['delta_pct']:+.2f}%)"
    )
    return result


def compare_time_efficiency(data: dict) -> dict:
    group_a_times = [
        r["time_cost_minutes"] for r in data["records"] if r["group"] == "A"
    ]
    group_b_times = [
        r["time_cost_minutes"] for r in data["records"] if r["group"] == "B"
    ]

    mean_a = round(float(np.mean(group_a_times)), 1)
    mean_b = round(float(np.mean(group_b_times)), 1)
    std_a = round(float(np.std(group_a_times, ddof=1)), 1)
    std_b = round(float(np.std(group_b_times, ddof=1)), 1)
    median_a = round(float(np.median(group_a_times)), 1)
    median_b = round(float(np.median(group_b_times)), 1)

    normality_a = stats.shapiro(group_a_times)
    normality_b = stats.shapiro(group_b_times)
    use_param = normality_a.pvalue > 0.05 and normality_b.pvalue > 0.05

    if use_param:
        t_stat, p_value = stats.ttest_ind(
            group_a_times, group_b_times, alternative="greater"
        )
        test_name = "独立样本t检验"
    else:
        t_stat, p_value = stats.mannwhitneyu(
            group_a_times, group_b_times, alternative="greater"
        )
        test_name = "Mann-Whitney U检验"

    effect_size = (
        (mean_a - mean_b) / np.sqrt((std_a**2 + std_b**2) / 2)
        if (std_a > 0 or std_b > 0)
        else 0
    )

    result = {
        "test_name": test_name,
        "group_a": {
            "mean": mean_a,
            "std": std_a,
            "median": median_a,
            "count": len(group_a_times),
        },
        "group_b": {
            "mean": mean_b,
            "std": std_b,
            "median": median_b,
            "count": len(group_b_times),
        },
        "time_reduction": round(mean_a - mean_b, 1),
        "time_reduction_pct": round((mean_a - mean_b) / max(mean_a, 0.1) * 100, 1),
        "statistic": round(float(t_stat), 4),
        "p_value": round(float(p_value), 5),
        "is_significant": bool(p_value < 0.05),
        "effect_size_cohens_d": round(float(effect_size), 4),
        "normality_test": {
            "group_a_shapiro_p": round(float(normality_a.pvalue), 5),
            "group_b_shapiro_p": round(float(normality_b.pvalue), 5),
            "use_parametric": use_param,
        },
    }

    significance_mark = (
        "***"
        if p_value < 0.001
        else ("**" if p_value < 0.01 else ("*" if p_value < 0.05 else "n.s."))
    )
    logger.info(
        f"耗时对比 ({test_name}): A组={mean_a}±{std_a}min, B组={mean_b}±{std_b}min, 降低={result['time_reduction']}min ({result['time_reduction_pct']}%), P={p_value:.5f} {significance_mark}"
    )
    return result


def compute_ai_agreement_rate(data: dict) -> dict:
    cases = data["cases"]
    ai_conc = data["ai_conclusions"]
    total = len(cases)
    consistent = sum(1 for c in cases if ai_conc.get(c["case_id"]) == c["ground_truth"])
    rate = round(consistent / total * 100) if total > 0 else 0

    by_difficulty = {}
    for diff in ["难", "中", "易"]:
        diff_cases = [c for c in cases if c["difficulty"] == diff]
        diff_total = len(diff_cases)
        diff_consistent = sum(
            1 for c in diff_cases if ai_conc.get(c["case_id"]) == c["ground_truth"]
        )
        by_difficulty[diff] = {
            "total": diff_total,
            "consistent": diff_consistent,
            "agreement_rate_pct": round(diff_consistent / diff_total * 100)
            if diff_total > 0
            else 0,
        }

    result = {
        "total_cases": total,
        "ai_judgment_consistent": consistent,
        "ai_judgment_inconsistent": total - consistent,
        "agreement_rate_pct": rate,
        "by_difficulty": by_difficulty,
    }
    logger.info(f"AI与判决一致率: {rate}% ({consistent}/{total})")
    return result


def compute_descriptive_stats(data: dict) -> dict:
    group_a = [r for r in data["records"] if r["group"] == "A"]
    group_b = [r for r in data["records"] if r["group"] == "B"]

    def _stats(records):
        times = [r["time_cost_minutes"] for r in records]
        confs = [r["confidence"] for r in records]
        conclusions = [r["conclusion"] for r in records]
        return {
            "n": len(records),
            "time": {
                "mean": round(float(np.mean(times)), 1),
                "std": round(float(np.std(times, ddof=1)), 1),
                "median": round(float(np.median(times)), 1),
                "min": round(float(np.min(times)), 1),
                "max": round(float(np.max(times)), 1),
                "q25": round(float(np.percentile(times, 25)), 1),
                "q75": round(float(np.percentile(times, 75)), 1),
            },
            "confidence": {
                "mean": round(float(np.mean(confs)), 2),
                "std": round(float(np.std(confs, ddof=1)), 2),
            },
            "conclusion_distribution": {
                str(k): int(v)
                for k, v in zip(*np.unique(conclusions, return_counts=True))
            },
        }

    return {"group_a": _stats(group_a), "group_b": _stats(group_b)}


def compute_confidence_comparison(data: dict) -> dict:
    group_a_conf = [r["confidence"] for r in data["records"] if r["group"] == "A"]
    group_b_conf = [r["confidence"] for r in data["records"] if r["group"] == "B"]
    u_stat, p_value = stats.mannwhitneyu(
        group_a_conf, group_b_conf, alternative="two-sided"
    )
    result = {
        "group_a_mean": round(float(np.mean(group_a_conf)), 2),
        "group_b_mean": round(float(np.mean(group_b_conf)), 2),
        "mannwhitney_u": round(float(u_stat), 2),
        "p_value": round(float(p_value), 5),
        "is_significant": bool(p_value < 0.05),
    }
    logger.info(
        f"置信度对比: A组={result['group_a_mean']:.2f}, B组={result['group_b_mean']:.2f}, P={result['p_value']:.5f}"
    )
    return result


def compute_accuracy_by_difficulty(data: dict) -> dict:
    result = {}
    for group in ["A", "B"]:
        group_results = {}
        for diff in ["难", "中", "易"]:
            records = [
                r
                for r in data["records"]
                if r["group"] == group and r["difficulty"] == diff
            ]
            if not records:
                continue
            correct = sum(1 for r in records if r["conclusion"] == r["ground_truth"])
            total = len(records)
            group_results[diff] = {
                "total": total,
                "correct": correct,
                "accuracy_pct": round(correct / total * 100, 1),
            }
        result[group] = group_results
    logger.info("按案件难度分组的准确率:")
    for group in ["A", "B"]:
        for diff in ["难", "中", "易"]:
            if diff in result[group]:
                v = result[group][diff]
                logger.info(
                    f"  {group}组-{diff}: {v['accuracy_pct']:.1f}% ({v['correct']}/{v['total']})"
                )
    return result


def generate_output_filename(prefix: str = "statistical_analysis") -> str:
    _output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(_output_dir / f"{prefix}_{timestamp}.json")


def save_results(results: dict, output_path: str = None):
    if output_path is None:
        output_path = generate_output_filename()
    serializable = json.loads(json.dumps(results, default=str, ensure_ascii=False))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    logger.info(f"结果已保存至: {output_path}")
    return output_path


def run_analysis(data_path: str = None) -> dict:
    data = load_experiment_data(data_path)
    is_mock = data.get("experiment_info", {}).get("is_mock_data", False)
    if is_mock:
        logger.warning("=" * 50)
        logger.warning("当前使用模拟数据运行，仅用于验证脚本功能")
        logger.warning("请将真实实验数据放置于 research/data/experiment_data.json")
        logger.warning("=" * 50)

    logger.info("=" * 60)
    logger.info("步骤 1/6: 描述性统计分析")
    logger.info("=" * 60)
    desc_stats = compute_descriptive_stats(data)
    logger.info(
        f"  A组: {desc_stats['group_a']['n']}条记录, 平均耗时={desc_stats['group_a']['time']['mean']}min"
    )
    logger.info(
        f"  B组: {desc_stats['group_b']['n']}条记录, 平均耗时={desc_stats['group_b']['time']['mean']}min"
    )

    logger.info("=" * 60)
    logger.info("步骤 2/6: Cohen's Kappa 一致性分析")
    logger.info("=" * 60)
    kappa_a = compute_cohens_kappa_for_group(data, "A")
    kappa_b = compute_cohens_kappa_for_group(data, "B")
    kappa_comparison = compare_kappa_between_groups(kappa_a, kappa_b)

    logger.info("=" * 60)
    logger.info("步骤 3/6: Fleiss' Kappa 多评估者一致性")
    logger.info("=" * 60)
    fleiss_a = compute_fleiss_kappa(data, "A")
    fleiss_b = compute_fleiss_kappa(data, "B")

    logger.info("=" * 60)
    logger.info("步骤 4/6: 分析耗时对比 (显著性检验)")
    logger.info("=" * 60)
    time_result = compare_time_efficiency(data)

    logger.info("=" * 60)
    logger.info("步骤 5/6: AI与判决一致率")
    logger.info("=" * 60)
    ai_result = compute_ai_agreement_rate(data)

    logger.info("=" * 60)
    logger.info("步骤 6/6: 辅助分析")
    logger.info("=" * 60)
    conf_result = compute_confidence_comparison(data)
    acc_by_diff = compute_accuracy_by_difficulty(data)

    results = {
        "analysis_info": {
            "title": "回溯性对比实验统计分析结果",
            "generated_at": datetime.now().isoformat(),
            "data_source": "模拟数据" if is_mock else "真实实验数据",
            "total_cases": len(data.get("cases", [])),
            "total_records": len(data.get("records", [])),
        },
        "descriptive_statistics": desc_stats,
        "cohens_kappa": {
            "group_a": kappa_a,
            "group_b": kappa_b,
            "comparison": kappa_comparison,
        },
        "fleiss_kappa": {
            "group_a": fleiss_a,
            "group_b": fleiss_b,
            "delta": round(fleiss_b - fleiss_a, 4),
        },
        "time_efficiency": time_result,
        "ai_agreement": ai_result,
        "confidence_comparison": conf_result,
        "accuracy_by_difficulty": acc_by_diff,
    }

    summary = _build_summary(results)
    results["summary"] = summary

    output_path = save_results(results)
    results["output_path"] = output_path

    _print_summary(results)
    return results


def _build_summary(results: dict) -> dict:
    kappa_comp = results["cohens_kappa"]["comparison"]
    time_eff = results["time_efficiency"]
    ai_agree = results["ai_agreement"]
    ai_threshold = ai_agree["agreement_rate_pct"] >= 80

    return {
        "假设检验结果": {
            "H1 (一致性提升)": f"B组Kappa={results['cohens_kappa']['group_b']['mean_kappa']:.4f}, A组Kappa={results['cohens_kappa']['group_a']['mean_kappa']:.4f}, 提升={kappa_comp['delta']:+.4f}, 达成目标(≥0.65): {'✓' if results['cohens_kappa']['group_b']['mean_kappa'] >= 0.65 else '✗'}",
            "H2 (效率提升)": f"B组平均耗时={results['descriptive_statistics']['group_b']['time']['mean']}min, A组={results['descriptive_statistics']['group_a']['time']['mean']}min, P={time_eff['p_value']}, 统计显著: {'✓' if time_eff['is_significant'] else '✗'}",
            "H3 (AI一致性)": f"AI与判决一致率={ai_agree['agreement_rate_pct']}%, 达成目标(≥80%): {'✓' if ai_threshold else '✗'}",
        },
        "kappa_threshold_met": results["cohens_kappa"]["group_b"]["mean_kappa"] >= 0.65,
        "time_efficiency_significant": time_eff["is_significant"],
        "ai_agreement_threshold_met": ai_threshold,
    }


def _print_summary(results: dict):
    summary = results["summary"]
    logger.info("")
    logger.info("=" * 70)
    logger.info("实 验 结 果 摘 要")
    logger.info("=" * 70)
    logger.info("")

    logger.info("【假设检验结果】")
    for hypothesis, detail in summary["假设检验结果"].items():
        logger.info(f"  {hypothesis}: {detail}")
    logger.info("")

    kappa_b = results["cohens_kappa"]["group_b"]
    logger.info(
        f"一致性指标: B组 Cohen's Kappa = {kappa_b['mean_kappa']:.4f} (目标≥0.65), 达标: {'✓ 通过' if summary['kappa_threshold_met'] else '✗ 未通过'}"
    )
    logger.info(
        f"效率指标:   {'✓ 统计显著' if summary['time_efficiency_significant'] else '✗ 未达统计显著'} (P={results['time_efficiency']['p_value']})"
    )
    logger.info(
        f"AI一致率:   {results['ai_agreement']['agreement_rate_pct']}% (目标≥80%), 达标: {'✓ 通过' if summary['ai_agreement_threshold_met'] else '✗ 未通过'}"
    )

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"完整报告已保存至: {results.get('output_path', 'N/A')}")
    logger.info("=" * 70)


if __name__ == "__main__":
    data_path = sys.argv[1] if len(sys.argv) > 1 else None
    setup_logging()
    run_analysis(data_path)
