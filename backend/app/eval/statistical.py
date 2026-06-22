"""核心统计功能模块 — 纯 Python 实现.

提供 Cohen's Kappa、描述性统计、AI 一致率、混淆矩阵、时间性能分析等
5 个核心统计函数，不依赖 sklearn 等外部 ML 库。
"""

from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# 1. Cohen's Kappa 系数计算
# ---------------------------------------------------------------------------


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """计算两个评估者之间的 Cohen's Kappa 系数.

    Args:
        labels_a: 评估者 A 的标签列表。
        labels_b: 评估者 B 的标签列表（长度必须与 A 相同）。

    Returns:
        Cohen's Kappa 系数，范围 [-1, 1]。

    Raises:
        ValueError: 当两个列表长度不一致或为空时。
    """
    if len(labels_a) != len(labels_b):
        raise ValueError("两个标签列表长度必须相同")
    n = len(labels_a)
    if n == 0:
        raise ValueError("标签列表不能为空")

    # 收集所有唯一标签
    all_labels = sorted(set(labels_a) | set(labels_b))
    k = len(all_labels)
    label_idx = {lbl: i for i, lbl in enumerate(all_labels)}

    # 构建混淆计数矩阵
    matrix = [[0] * k for _ in range(k)]
    for a_lbl, b_lbl in zip(labels_a, labels_b):
        i = label_idx[a_lbl]
        j = label_idx[b_lbl]
        matrix[i][j] += 1

    # 观察一致率 P_o
    p_o = sum(matrix[i][i] for i in range(k)) / n

    # 期望一致率 P_e
    row_sums = [sum(matrix[i]) for i in range(k)]
    col_sums = [sum(matrix[r][i] for r in range(k)) for i in range(k)]
    p_e = sum((row_sums[i] / n) * (col_sums[i] / n) for i in range(k))
    if p_e >= 1.0:
        return 1.0 if p_o >= 1.0 else 0.0
    return (p_o - p_e) / (1.0 - p_e)


# ---------------------------------------------------------------------------
# 2. 描述性统计分析
# ---------------------------------------------------------------------------


def descriptive_statistics(values: list[float]) -> dict[str, Any]:
    """计算一组数值的描述性统计量.

    Args:
        values: 数值列表。

    Returns:
        包含 mean, std, median, min, max, q25, q75, count的字典。

    Raises:
        ValueError: 当列表为空时。
    """
    if not values:
        raise ValueError("数值列表不能为空")

    n = len(values)
    sorted_vals = sorted(values)
    total = sum(sorted_vals)
    mean = total / n

    # 标准差（样本标准差，ddof=1）
    if n > 1:
        variance = sum((x - mean) ** 2 for x in sorted_vals) / (n - 1)
        std = math.sqrt(variance)
    else:
        std = 0.0
    median = _percentile(sorted_vals, 50.0)
    q25 = _percentile(sorted_vals, 25.0)
    q75 = _percentile(sorted_vals, 75.0)
    return {"count": n,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "median": round(median, 4),
        "min": round(sorted_vals[0], 4),
        "max": round(sorted_vals[-1], 4),
        "q25": round(q25, 4),
        "q75": round(q75, 4),
    }


def _percentile(sorted_data: list[float], pct: float) -> float:
    """使用线性插值计算百分位数.

    Args:
        sorted_data: 已排序的数据列表。
        pct: 百分位（0-100）。

    Returns:
        对应的百分位数值。
    """
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]
    rank = (pct / 100.0) * (n - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return sorted_data[lower]
    frac = rank - lower
    return sorted_data[lower] * (1.0 - frac) + sorted_data[upper] * frac


# ---------------------------------------------------------------------------
# 3. AI agreement 一致率计算
# ---------------------------------------------------------------------------


def ai_agreement_rate(ground_truths: list[str],
    ai_predictions: list[str],
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """计算 AI 预测与黄金标准的一致率.

    Args:
        ground_truths: 黄金标准标签列表。
        ai_predictions: AI 预测标签列表。
        categories: 可选的分类标签列表，用于按类别统计。

    Returns:
        包含总体一致率和按类别一致率的字典。

    Raises:
        ValueError: 当两个列表长度不一致或为空时。
    """
    if len(ground_truths) != len(ai_predictions):
        raise ValueError("标签列表长度必须相同")
    n = len(ground_truths)
    if n == 0:
        raise ValueError("标签列表不能为空")
    consistent = sum(1 for g, p in zip(ground_truths, ai_predictions) if g == p)
    rate = consistent / n

    result: dict[str, Any] = {"total": n,
        "consistent": consistent,
        "inconsistent": n - consistent,
        "agreement_rate": round(rate, 4),
        "agreement_rate_pct": round(rate * 100, 2),
    }

    # 按类别统计
    if categories is not None:
        by_category: dict[str, dict[str, int | float]] = {}
        for cat in categories:
            cat_indices = [i for i, g in enumerate(ground_truths) if g == cat]
            cat_total = len(cat_indices)
            if cat_total == 0:
                by_category[cat] = {"total": 0, "consistent": 0, "agreement_rate_pct": 0.0}
                continue
            cat_consistent = sum(
                1 for i in cat_indices if ai_predictions[i] == cat
            )
            by_category[cat] = {"total": cat_total,
                "consistent": cat_consistent,
                "agreement_rate_pct": round(cat_consistent / cat_total * 100, 2),
            }
        result["by_category"] = by_category
    return result


# ---------------------------------------------------------------------------
# 4. 混淆矩阵生成
# ---------------------------------------------------------------------------


def confusion_matrix(ground_truths: list[str],
    predictions: list[str],
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """生成混淆矩阵.

    Args:
        ground_truths: 真实标签列表。
        predictions: 预测标签列表。
        labels: 可选的标签列表（定义矩阵行列顺序）。

    Returns:
        包含 labels、matrix、以及每个类别的 precision/recall/f1 的字典。

    Raises:
        ValueError: 当两个列表长度不一致或为空时。
    """
    if len(ground_truths) != len(predictions):
        raise ValueError("标签列表长度必须相同")
    if not ground_truths:
        raise ValueError("标签列表不能为空")
    if labels is None:
        labels = sorted(set(ground_truths) | set(predictions))

    k = len(labels)
    label_idx = {lbl: i for i, lbl in enumerate(labels)}

    # 构建 k×k 矩阵
    matrix = [[0] * k for _ in range(k)]
    for gt, pred in zip(ground_truths, predictions):
        if gt in label_idx and pred in label_idx:
            matrix[label_idx[gt]][label_idx[pred]] += 1

    # 计算每类的 precision / recall / f1
    per_class: dict[str, dict[str, float]] = {}
    for i, lbl in enumerate(labels):
        tp = matrix[i][i]
        fp = sum(matrix[r][i] for r in range(k)) - tp
        fn = sum(matrix[i]) - tp
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall) if (precision + recall) > 0
            else 0.0
        )
        per_class[lbl] = {"precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(matrix[i]),
        }

    # 总体准确率
    total = sum(sum(row) for row in matrix)
    correct = sum(matrix[i][i] for i in range(k))
    accuracy = correct / total if total > 0 else 0.0
    return {"labels": labels,
        "matrix": matrix,
        "accuracy": round(accuracy, 4),
        "per_class": per_class,
        "total_samples": total,
    }


# ---------------------------------------------------------------------------
# 5. 时间性能分析
# ---------------------------------------------------------------------------


def time_performance_analysis(
    times_a: list[float],
    times_b: list[float],
) -> dict[str, Any]:
    """对比两组的时间性能.

    使用 Welch's t 检验近似（不依赖 scipy），计算效应量 Cohen's d。

    Args:
        times_a: A 组耗时列表。
        times_b: B 组耗时列表。

    Returns:
        包含各组统计量、均值差异、t 统计量、p 值近似、效应量的字典。

    Raises:
        ValueError: 当任一组为空时。
    """
    if not times_a or not times_b:
        raise ValueError("时间列表不能为空")
    stats_a = descriptive_statistics(times_a)
    stats_b = descriptive_statistics(times_b)
    mean_a = stats_a["mean"]
    mean_b = stats_b["mean"]
    std_a = stats_a["std"]
    std_b = stats_b["std"]
    n_a = stats_a["count"]
    n_b = stats_b["count"]
    mean_diff = mean_a - mean_b
    mean_diff_pct = (mean_diff / mean_a * 100) if mean_a != 0 else 0.0

    # Welch's t-test 统计量
    se_a = (std_a ** 2) / n_a if n_a > 0 else 0.0
    se_b = (std_b ** 2) / n_b if n_b > 0 else 0.0
    se = math.sqrt(se_a + se_b) if (se_a + se_b) > 0 else 1e-10
    t_stat = mean_diff / se

    # Welch-Satterthwaite 自由度
    if se_a + se_b > 0:
        df_num = (se_a + se_b) ** 2
        df_den = (se_a ** 2) / (n_a - 1) + (se_b ** 2) / (n_b - 1) if n_a > 1 and n_b > 1 else 1e-10
        df = df_num / df_den if df_den > 0 else 1.0
    else:
        df = 1.0

    # p 值近似（使用 t 分布的近似公式）
    p_value = _t_distribution_p_value(abs(t_stat), df)

    # Cohen's d 效应量
    pooled_std = math.sqrt(((n_a - 1) * std_a ** 2 + (n_b - 1) * std_b ** 2) / max(n_a + n_b - 2, 1))
    cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0.0
    return {"group_a": stats_a,
        "group_b": stats_b,
        "mean_difference": round(mean_diff, 4),
        "mean_difference_pct": round(mean_diff_pct, 2),
        "t_statistic": round(t_stat, 4),
        "degrees_of_freedom": round(df, 2),
        "p_value": round(p_value, 6),
        "is_significant": p_value < 0.05,
        "cohens_d": round(cohens_d, 4),
        "time_reduction_pct": round(mean_diff_pct, 2),
    }


def _t_distribution_p_value(t: float, df: float) -> float:
    """使用近似公式计算 t 分布的双尾 p 值.

    采用 Abramowitz & Stegun 近似，精度足够用于显著性检验。

    Args:
        t: t 统计量的绝对值。
        df: 自由度。

    Returns:
        双尾 p 值。
    """
    if df <= 0:
        return 1.0
    # 使用正态近似（当 df 较大时）或 Beta 不完全函数近似
    x = df / (df + t * t)
    p = _regularized_incomplete_beta(df / 2.0, 0.5, x)
    return min(max(p, 0.0), 1.0)


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    """正则化不完全 Beta 函数的连分数近似.

    Args:
        a: 参数 a。
        b: 参数 b。
        x: 积分上限（0 到 1）。

    Returns:
        正则化不完全 Beta 函数值。
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    # 使用连分数展开
    ln_beta = _ln_gamma(a) + _ln_gamma(b) - _ln_gamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1.0 - x) - ln_beta) / a

    # Lentz 连分数算法
    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    f = d
    for m in range(1, 200):
        # 偶数步
        numerator = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        d = 1.0 + numerator * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + numerator / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = c * d
        f *= delta

        # 奇数步
        numerator = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + numerator * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + numerator / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = c * d
        f *= delta
        if abs(delta - 1.0) < 1e-10:
            break
    return front * f


def _ln_gamma(z: float) -> float:
    """使用 Stirling 近似计算 ln(Gamma(z)).

    Args:
        z: 正实数参数。

    Returns:
        ln(Gamma(z)) 的近似值。
    """
    if z <= 0:
        return 0.0
    # Lanczos 近似
    g = 7
    c = [
        0.99999999999980993,
        676.5203681218851,
        -1259.1392167224028,
        771.32342877765313,
        -176.61502916214059,
        12.507343278686905,
        -0.13857109526572012,
        9.9843695780195716e-6,
        1.5056327351493116e-7,
    ]
    if z < 0.5:
        return math.log(math.pi / math.sin(math.pi * z)) - _ln_gamma(1.0 - z)
    z -= 1
    x = c[0]
    for i in range(1, g + 2):
        x += c[i] / (z + i)
    t = z + g + 0.5
    return 0.5 * math.log(2 * math.pi) + (z + 0.5) * math.log(t) - t + math.log(x)
