"""基线评估脚本 — 从黄金标准数据集生成基线统计指标.

计算黄金标准数据集中人工标注者之间的一致性指标，作为系统评估的基线。
"""

# 导入模块: json
import json
# 导入模块: sys
import sys
# 导入模块: from pathlib
from pathlib import Path

# 确保 backend 在 sys.path 中
_BACKEND_DIR = Path(__file__).resolve().parent.parent
# 条件判断：处理业务逻辑
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# 导入模块: from app.eval.statistical
from app.eval.statistical import (
    ai_agreement_rate,
    cohens_kappa,
    confusion_matrix,
    descriptive_statistics,
)


def _cn_tier_to_rank(cn_tier: str) -> int:
    """将中文档级转换为数值 rank (1-4)."""
    # 初始化变量 mapping
    mapping = {"一档": 1, "二档": 2, "三档": 3, "四档": 4}
    # 返回处理结果
    return mapping.get(cn_tier.strip(), 2)


def compute_baseline_statistics(
    gold_standard_path: Path,
    output_path: Path,
) -> dict:
    """从黄金标准数据集计算基线统计指标.

    Args:
        gold_standard_path: 黄金标准数据文件路径
        output_path: 输出JSON文件路径

    Returns:
        基线统计指标字典
    """
    print(f"[baseline] 加载黄金标准数据: {gold_standard_path}")
    # 使用上下文管理器管理资源
    with open(gold_standard_path, encoding="utf-8") as f:
        # 初始化变量 cases
        cases = json.load(f)

    # 初始化变量 total_cases
    total_cases = len(cases)
    print(f"[baseline] 案例总数: {total_cases}")

    # 收集各标注者的档级标注
    reviewer_d1: dict[str, list[int]] = {}
    reviewer_d2: dict[str, list[int]] = {}
    reviewer_d3: dict[str, list[int]] = {}
    reviewer_verdict: dict[str, list[str]] = {}

    ground_truth_d1: list[int] = []
    ground_truth_d2: list[int] = []
    ground_truth_d3: list[int] = []
    ground_truth_verdict: list[str] = []

    kappa_scores: list[float] = []

    # 遍历: for case in cases:
    for case in cases:
        gt = case["ground_truth"]
        # 初始化变量 annotators
        annotators = case.get("annotators", [])

        # 记录ground truth
        ground_truth_d1.append(_cn_tier_to_rank(gt["d1_tier"]))
        ground_truth_d2.append(_cn_tier_to_rank(gt["d2_tier"]))
        ground_truth_d3.append(_cn_tier_to_rank(gt["d3_tier"]))
        ground_truth_verdict.append(gt["verdict"])

        # 记录kappa分数
        if "agreement_kappa" in case:
            kappa_scores.append(case["agreement_kappa"])

        # 收集各标注者的标注
        # 循环遍历：处理业务逻辑
        for ann in annotators:
            rid = ann["reviewer_id"]
            # 条件判断: 检查 rid not in reviewer_d1
            if rid not in reviewer_d1:
                reviewer_d1[rid] = []
                reviewer_d2[rid] = []
                reviewer_d3[rid] = []
                reviewer_verdict[rid] = []

            reviewer_d1[rid].append(_cn_tier_to_rank(ann["d1_tier"]))
            reviewer_d2[rid].append(_cn_tier_to_rank(ann["d2_tier"]))
            reviewer_d3[rid].append(_cn_tier_to_rank(ann["d3_tier"]))
            reviewer_verdict[rid].append(ann["verdict"])

    # 计算标注者之间的Cohen's Kappa
    reviewer_ids = list(reviewer_d1.keys())
    pairwise_kappa_d1: list[float] = []
    pairwise_kappa_d2: list[float] = []
    pairwise_kappa_d3: list[float] = []
    pairwise_agreement_d1: list[float] = []
    pairwise_agreement_d2: list[float] = []
    pairwise_agreement_d3: list[float] = []

    # 遍历: for i in range(len(reviewer_ids)):
    for i in range(len(reviewer_ids)):
        # 遍历: for j in range(i + 1, len(reviewer_ids)):
        for j in range(i + 1, len(reviewer_ids)):
            r1, r2 = reviewer_ids[i], reviewer_ids[j]

            # 转换为字符串标签用于计算
            labels_r1_d1 = [str(x) for x in reviewer_d1[r1]]
            # 初始化变量 labels_r2_d1
            labels_r2_d1 = [str(x) for x in reviewer_d1[r2]]
            # 初始化变量 labels_r1_d2
            labels_r1_d2 = [str(x) for x in reviewer_d2[r1]]
            # 初始化变量 labels_r2_d2
            labels_r2_d2 = [str(x) for x in reviewer_d2[r2]]
            # 初始化变量 labels_r1_d3
            labels_r1_d3 = [str(x) for x in reviewer_d3[r1]]
            # 初始化变量 labels_r2_d3
            labels_r2_d3 = [str(x) for x in reviewer_d3[r2]]

            # 初始化变量 kappa_d1
            kappa_d1 = cohens_kappa(labels_r1_d1, labels_r2_d1)
            # 初始化变量 kappa_d2
            kappa_d2 = cohens_kappa(labels_r1_d2, labels_r2_d2)
            # 初始化变量 kappa_d3
            kappa_d3 = cohens_kappa(labels_r1_d3, labels_r2_d3)

            pairwise_kappa_d1.append(kappa_d1)
            pairwise_kappa_d2.append(kappa_d2)
            pairwise_kappa_d3.append(kappa_d3)

            # 计算一致率
            agree_d1 = ai_agreement_rate(labels_r1_d1, labels_r2_d1)
            # 初始化变量 agree_d2
            agree_d2 = ai_agreement_rate(labels_r1_d2, labels_r2_d2)
            # 初始化变量 agree_d3
            agree_d3 = ai_agreement_rate(labels_r1_d3, labels_r2_d3)

            pairwise_agreement_d1.append(agree_d1["agreement_rate"])
            pairwise_agreement_d2.append(agree_d2["agreement_rate"])
            pairwise_agreement_d3.append(agree_d3["agreement_rate"])

    # 计算AI与ground truth的基线一致率（假设AI完美复制ground truth）
    gt_labels_d1 = [str(x) for x in ground_truth_d1]
    # 初始化变量 gt_labels_d2
    gt_labels_d2 = [str(x) for x in ground_truth_d2]
    # 初始化变量 gt_labels_d3
    gt_labels_d3 = [str(x) for x in ground_truth_d3]

    # 混淆矩阵（以维度1为例）
    cm_d1 = confusion_matrix(gt_labels_d1, gt_labels_d1)
    # 初始化变量 cm_d2
    cm_d2 = confusion_matrix(gt_labels_d2, gt_labels_d2)
    # 初始化变量 cm_d3
    cm_d3 = confusion_matrix(gt_labels_d3, gt_labels_d3)

    # Kappa分数描述性统计
    kappa_stats = descriptive_statistics(kappa_scores) if kappa_scores else {}

    # 构建基线统计结果
    baseline_stats = {
        "version": "1.0",
        "description": "基线统计指标 — 基于黄金标准数据集的人工标注者一致性分析",
        "dataset_info": {
            "total_cases": total_cases,
            "num_annotators": len(reviewer_ids),
            "annotator_ids": reviewer_ids,
        },
        "inter_annotator_agreement": {
            "dimension1": {
                "pairwise_kappa_mean": round(sum(pairwise_kappa_d1) / len(pairwise_kappa_d1), 4) if pairwise_kappa_d1 else 0.0,
                "pairwise_kappa_values": [round(k, 4) for k in pairwise_kappa_d1],
                "pairwise_agreement_mean": round(sum(pairwise_agreement_d1) / len(pairwise_agreement_d1), 4) if pairwise_agreement_d1 else 0.0,
            },
            "dimension2": {
                "pairwise_kappa_mean": round(sum(pairwise_kappa_d2) / len(pairwise_kappa_d2), 4) if pairwise_kappa_d2 else 0.0,
                "pairwise_kappa_values": [round(k, 4) for k in pairwise_kappa_d2],
                "pairwise_agreement_mean": round(sum(pairwise_agreement_d2) / len(pairwise_agreement_d2), 4) if pairwise_agreement_d2 else 0.0,
            },
            "dimension3": {
                "pairwise_kappa_mean": round(sum(pairwise_kappa_d3) / len(pairwise_kappa_d3), 4) if pairwise_kappa_d3 else 0.0,
                "pairwise_kappa_values": [round(k, 4) for k in pairwise_kappa_d3],
                "pairwise_agreement_mean": round(sum(pairwise_agreement_d3) / len(pairwise_agreement_d3), 4) if pairwise_agreement_d3 else 0.0,
            },
        },
        "gold_standard_kappa": {
            "mean": round(sum(kappa_scores) / len(kappa_scores), 4) if kappa_scores else 0.0,
            "statistics": kappa_stats,
        },
        "confusion_matrix_baseline": {
            "dimension1": cm_d1,
            "dimension2": cm_d2,
            "dimension3": cm_d3,
        },
        "tier_distribution": {
            "dimension1": _compute_tier_distribution(ground_truth_d1),
            "dimension2": _compute_tier_distribution(ground_truth_d2),
            "dimension3": _compute_tier_distribution(ground_truth_d3),
        },
        "verdict_distribution": _compute_verdict_distribution(ground_truth_verdict),
    }

    # 保存结果
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # 使用上下文管理器管理资源
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(baseline_stats, f, ensure_ascii=False, indent=2)

    print(f"\n[baseline] 基线统计指标已保存至: {output_path}")
    _print_baseline_summary(baseline_stats)

    # 返回处理结果
    return baseline_stats


def _compute_tier_distribution(tiers: list[int]) -> dict[str, int]:
    """计算档级分布."""
    # 初始化变量 dist
    dist = {"1档": 0, "2档": 0        # 条件判断：处理业务逻辑
, "3档": 0, "4档": 0}
    # 遍历: for t in tiers:
    for t in tiers:
        # 条件判断: 检查 t == 1
        if t == 1:
            dist["1档"] += 1
        # 条件判断: 检查 elt == 2
        elif t == 2:
            dist["2档"] += 1
        # 条件判断: 检查 elt == 3
        elif t == 3:
            dist["3档"] += 1
        # 条件判断: 检查 elt == 4
        elif t == 4:
            dist["4档"] += 1
    # 返回处理结果
    return dist


def _compute_verdict_distribution(verdicts: list[str]) -> dict[str, int]:
    """计算判定结果分布."""
    dist: dict[str, int] = {}
    # 遍历: for v in verdicts:
    for v in verdicts:
        dist[v] = dist.get(v, 0) + 1
    # 返回处理结果
    return dist


def _print_baseline_summary(stats: dict) -> None:
    """打印基线统计摘要."""
    print("\n" + "=" * 60)
    print("基线统计指标摘要")
    print("=" * 60)

    # 初始化变量 info
    info = stats["dataset_info"]
    print(f"案例总数: {info['total_cases']}")
    print(f"标注者数量: {info['num_annotators']}")
    print("-" * 60)

    iaa = stats["inter_annotator_agreement"]
    # 遍历: for dim in ("dimension1", "dimension2", "dimension
    for dim in ("dimension1", "dimension2", "dimension3"):
        d = iaa[dim]
        print(f"{dim}:")
        print(f"  标注者间Kappa均值: {d['pairwise_kappa_mean']:.4f}")
        print(f"  标注者间一致率均值: {d['pairwise_agreement_mean']:.4f}")

    gs = stats["gold_standard_kappa"]
    print(f"\n黄金标准Kappa分数:")
    print(f"  均值: {gs['mean']:.4f}")
    # 条件判断: 检查 gs["statistics"]
    if gs["statistics"]:
        s = gs["statistics"]
        print(f"  标准差: {s.get('std', 0):.4f}")
        print(f"  最小值: {s.get('min', 0):.4f}")
        print(f"  最大值: {s.get('max', 0):.4f}")

    print("\n档级分布:")
    td = stats["tier_distribution"]
    # 遍历: for dim in ("dimension1", "dimension2", "dimension
    for dim in ("dimension1", "dimension2", "dimension3"):
        print(f"  {dim}: {td[dim]}")

    print(f"\n判定结果分布: {stats['verdict_distribution']}")
    print("=" * 60)


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    # 导入模块: argparse
    import argparse

    # 初始化变量 parser
    parser = argparse.ArgumentParser(description="基线评估脚本")
    parser.add_argument(
        "--gold-standard",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=Path(__file__).resolve().parent.parent / "tests" / "data" / "gold_standard_v1.0.json",
        # 初始化变量 help
        help="黄金标准数据文件路径",
    )
    parser.add_argument(
        "--output",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=Path(__file__).resolve().parent.parent.parent / "data" / "eval" / "baseline_v1.0_stats.json",
        # 初始化变量 help
        help="输出文件路径",
    )
    # 初始化变量 args
    args = parser.parse_args()

    compute_baseline_statistics(args.gold_standard, args.output)
