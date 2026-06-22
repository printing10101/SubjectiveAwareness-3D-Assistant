"""混淆矩阵计算与可视化模块.

提供纯Python实现的混淆矩阵算法，不依赖sklearn库。
支持JSON格式输出、PNG可视化生成，以及matplotlib不可用时的文本降级输出。
"""
import io
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 尝试导入matplotlib，失败时设置降级标志
_MATPLOTLIB_AVAILABLE = False
try:
    import matplotlib
    matplotlib.use("Agg")  # 非交互式后端
    import matplotlib.pyplot as plt
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    logger.warning("matplotlib库不可用，混淆矩阵可视化将降级为文本格式输出")


def compute_confusion_matrix(y_true: list[int],
    y_pred: list[int],
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """计算混淆矩阵.

    Args:
        y_true: 真实标签列表，整数编码
        y_pred: 预测标签列表，整数编码
        labels: 类别名称列表，可选

    Returns:
        包含混淆矩阵数据的字典，格式如下:
        {
            "matrix": [[int, ...], ...],  # 混淆矩阵二维数组
            "labels": [str, ...],          # 类别名称列表
            "classes": int,                # 类别数量
            "total_samples": int,          # 总样本数
            "correct_predictions": int,    # 正确预测数
            "accuracy": float,             # 准确率
        }

    Raises:
        ValueError: 当输入数据长度不匹配或为空时
    """
    if len(y_true) != len(y_pred):
        raise ValueError(f"真实标签和预测标签长度不匹配: {len(y_true)} != {len(y_pred)}")
    if not y_true:
        raise ValueError("输入数据不能为空")

    # 确定类别数量
    all_labels = set(y_true) | set(y_pred)
    n_classes = max(all_labels) + 1 if all_labels else 0

    # 生成默认类别名称
    if labels is None:
        labels = [f"class_{i}" for i in range(n_classes)]
    elif len(labels) < n_classes:
        # 扩展标签列表
        labels.extend([f"class_{i}" for i in range(len(labels), n_classes)])

    # 初始化混淆矩阵
    matrix = [[0] * n_classes for _ in range(n_classes)]

    # 填充混淆矩阵
    for true_label, pred_label in zip(y_true, y_pred, strict=True):
        matrix[true_label][pred_label] += 1

    # 计算统计信息
    total_samples = len(y_true)
    correct_predictions = sum(matrix[i][i] for i in range(n_classes))
    accuracy = correct_predictions / total_samples if total_samples > 0 else 0.0
    return {"matrix": matrix,
        "labels": labels[:n_classes],
        "classes": n_classes,
        "total_samples": total_samples,
        "correct_predictions": correct_predictions,
        "accuracy": accuracy,
    }


def compute_per_class_metrics(confusion_data: dict[str, Any],
) -> dict[str, dict[str, float]]:
    """计算每个类别的详细指标.

    Args:
        confusion_data: compute_confusion_matrix返回的混淆矩阵数据

    Returns:
        每个类别的precision、recall、f1_score字典
    """
    matrix = confusion_data["matrix"]
    labels = confusion_data["labels"]
    n_classes = confusion_data["classes"]
    metrics = {}

    for i in range(n_classes):
        # True Positives
        tp = matrix[i][i]

        # False Positives (列和 - TP)
        fp = sum(matrix[r][i] for r in range(n_classes)) - tp

        # False Negatives (行和 - TP)
        fn = sum(matrix[i][c] for c in range(n_classes)) - tp

        # Precision
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

        # Recall
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        # F1 Score
        f1_score = (
            2 * precision * recall / (precision + recall) if (precision + recall) > 0
            else 0.0
        )

        metrics[labels[i]] = {"precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "support": tp + fn,  # 该类别的实际样本数
        }
    return metrics


def format_confusion_json(confusion_data: dict[str, Any]) -> str:
    """将混淆矩阵数据格式化为JSON字符串.

    Args:
        confusion_data: compute_confusion_matrix返回的混淆矩阵数据

    Returns:
        JSON格式的字符串
    """
    return json.dumps(confusion_data, ensure_ascii=False, indent=2)


def save_confusion_json(confusion_data: dict[str, Any],
    output_path: str | Path,
) -> None:
    """保存混淆矩阵数据到JSON文件.

    Args:
        confusion_data: compute_confusion_matrix返回的混淆矩阵数据
        output_path: 输出文件路径
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(confusion_data, f, ensure_ascii=False, indent=2)

    logger.info(f"混淆矩阵数据已保存至: {output_path}")


def render_confusion_text(confusion_data: dict[str, Any]) -> str:
    """渲染混淆矩阵为文本格式.

    当matplotlib不可用时的降级输出方案。

    Args:
        confusion_data: compute_confusion_matrix返回的混淆矩阵数据

    Returns:
        文本格式的混淆矩阵表示
    """
    matrix = confusion_data["matrix"]
    labels = confusion_data["labels"]
    n_classes = confusion_data["classes"]
    accuracy = confusion_data["accuracy"]
    lines = []
    lines.append("=" * 60)
    lines.append("混淆矩阵 (Confusion Matrix)")
    lines.append("=" * 60)
    lines.append(f"总样本数: {confusion_data['total_samples']}")
    lines.append(f"正确预测: {confusion_data['correct_predictions']}")
    lines.append(f"准确率: {accuracy:.4f} ({accuracy * 100:.2f}%)")
    lines.append("")

    # 计算列宽
    max_val = max(max(row) for row in matrix) if matrix else 0
    cell_width = max(4, len(str(max_val)) + 1)

    # 表头
    header = " " * cell_width + " | "
    header += " ".join(f"{label[:cell_width]:^{cell_width}}" for label in labels)
    lines.append(header)
    lines.append("-" * len(header))

    # 矩阵内容
    for i, row in enumerate(matrix):
        row_str = f"{labels[i][:cell_width]:<{cell_width}} | "
        row_str += " ".join(f"{val:^{cell_width}}" for val in row)
        lines.append(row_str)

    lines.append("=" * 60)
    return "\n".join(lines)


def render_confusion_png(confusion_data: dict[str, Any],
    output_path: str | Path,
    title: str = "混淆矩阵",
    cmap: str = "Blues",
) -> bool:
    """渲染混淆矩阵为PNG图像.

    Args:
        confusion_data: compute_confusion_matrix返回的混淆矩阵数据
        output_path: 输出图像文件路径
        title: 图像标题
        cmap: 颜色映射方案

    Returns:
        True表示成功生成图像，False表示降级为文本输出
    """
    if not _MATPLOTLIB_AVAILABLE:
        logger.warning("matplotlib不可用，无法生成PNG图像")
        return False

    try:
        matrix = confusion_data["matrix"]
        labels = confusion_data["labels"]
        n_classes = confusion_data["classes"]

        fig, ax = plt.subplots(figsize=(max(8, n_classes * 1.5), max(6, n_classes * 1.2)))

        # 绘制热力图
        im = ax.imshow(matrix, interpolation="nearest", cmap=cmap)
        ax.figure.colorbar(im, ax=ax)

        # 设置坐标轴
        ax.set(
            xticks=range(n_classes),
            yticks=range(n_classes),
            xticklabels=labels,
            yticklabels=labels,
            title=title,
            ylabel="真实标签",
            xlabel="预测标签",
        )

        # 旋转x轴标签
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        # 在每个单元格中显示数值
        fmt = "d"
        thresh = max(max(row) for row in matrix) / 2.0
        for i in range(n_classes):
            for j in range(n_classes):
                ax.text(
                    j,
                    i,
                    format(matrix[i][j], fmt),
                    ha="center",
                    va="center",
                    color="white" if matrix[i][j] > thresh else "black",
                )

        fig.tight_layout()

        # 保存图像
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        logger.info(f"混淆矩阵图像已保存至: {output_path}")
        return True
    except Exception as e:
        logger.error(f"生成混淆矩阵PNG图像失败: {e}")
        return False


def save_confusion_matrix(y_true: list[int],
    y_pred: list[int],
    output_dir: str | Path,
    labels: list[str] | None = None,
    prefix: str = "confusion_matrix",
) -> dict[str, Any]:
    """计算并保存混淆矩阵的完整流程.

    自动生成JSON数据文件、PNG图像（或文本降级输出）。

    Args:
        y_true: 真实标签列表
        y_pred: 预测标签列表
        output_dir: 输出目录路径
        labels: 类别名称列表，可选
        prefix: 输出文件名前缀

    Returns:
        包含所有输出文件路径和混淆矩阵数据的字典
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 计算混淆矩阵
    confusion_data = compute_confusion_matrix(y_true, y_pred, labels)

    # 保存JSON数据
    json_path = output_dir / f"{prefix}.json"
    save_confusion_json(confusion_data, json_path)

    # 尝试生成PNG图像，失败时保存文本输出
    png_path = output_dir / f"{prefix}.png"
    png_success = render_confusion_png(confusion_data, png_path)
    result = {"confusion_data": confusion_data, "json_path": str(json_path),
        "png_generated": png_success,
    }
    if png_success:
        result["png_path"] = str(png_path)
    else:
        # 降级为文本输出
        text_path = output_dir / f"{prefix}.txt"
        text_content = render_confusion_text(confusion_data)
        with text_path.open("w", encoding="utf-8") as f:
            f.write(text_content)
        result["text_path"] = str(text_path)
        logger.info(f"混淆矩阵文本输出已保存至: {text_path}")
    return result
