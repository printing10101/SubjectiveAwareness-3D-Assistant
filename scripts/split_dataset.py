#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据集划分脚本
功能：
1. 将处理后的数据划分为训练集和验证集
2. 验证集占比10%
3. 验证集包含不低于20%的否定类（不明知）样本
4. 确保三类样本均衡分布
"""

import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter

import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KnowledgeLevelExtractor:
    """从样本output字段提取明知程度"""

    @staticmethod
    def extract_knowledge_level(sample: Dict) -> str:
        """
        从样本的output字段提取明知程度分类

        Returns:
            "positive" (明知), "negative" (不明知), "edge" (边缘)
        """
        output_str = sample.get("output", "")
        try:
            output_json = json.loads(output_str)
            level = output_json.get("明知程度评估", "")
        except json.JSONDecodeError:
            level = ""

        # 分类映射
        if "明确认定明知" in level:
            return "positive"
        elif "明确认定不明知" in level:
            return "negative"
        elif "边缘" in level or "存疑" in level:
            return "edge"
        else:
            # 默认归类为边缘
            return "edge"


class DatasetSplitter:
    """数据集划分器"""

    def __init__(
        self, val_ratio: float = 0.1, min_negative_ratio: float = 0.2, seed: int = 42
    ):
        self.val_ratio = val_ratio
        self.min_negative_ratio = min_negative_ratio
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def load_jsonl(self, file_path: Path) -> List[Dict]:
        """加载JSONL文件"""
        samples = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        samples.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning(f"跳过无效行: {line[:50]}...")
        return samples

    def split(self, samples: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        划分数据集

        Args:
            samples: 所有样本列表

        Returns:
            (train_samples, val_samples)
        """
        # 1. 按明知程度分类
        positive_samples = []
        negative_samples = []
        edge_samples = []

        for sample in samples:
            level = KnowledgeLevelExtractor.extract_knowledge_level(sample)
            if level == "positive":
                positive_samples.append(sample)
            elif level == "negative":
                negative_samples.append(sample)
            else:
                edge_samples.append(sample)

        logger.info(
            f"样本分布: 明知={len(positive_samples)}, "
            f"不明知={len(negative_samples)}, 边缘={len(edge_samples)}"
        )

        total = len(samples)
        val_size = max(1, int(total * self.val_ratio))

        # 2. 确保验证集中否定类样本比例不低于20%
        min_negative_in_val = max(1, int(val_size * self.min_negative_ratio))

        # 3. 按比例从各类别中抽取验证集样本
        val_samples = []

        # 首先确保验证集有足够的否定类样本
        available_negative = len(negative_samples)
        negative_for_val = min(min_negative_in_val, available_negative)

        if negative_for_val < min_negative_in_val:
            logger.warning(
                f"否定类样本不足，验证集中将包含 {negative_for_val} 条"
                f"（要求最低 {min_negative_in_val} 条）"
            )

        # 从各类别中按比例抽取
        val_negative = (
            random.sample(negative_samples, negative_for_val)
            if negative_for_val > 0
            else []
        )
        remaining_negative = [s for s in negative_samples if s not in val_negative]

        # 计算剩余验证集名额
        remaining_val_size = val_size - len(val_negative)

        # 从正类和边缘类中按比例分配
        remaining_positive = len(positive_samples)
        remaining_edge = len(edge_samples)
        total_remaining = remaining_positive + remaining_edge

        if total_remaining > 0:
            positive_ratio = remaining_positive / total_remaining
            val_positive_count = min(
                remaining_positive, int(remaining_val_size * positive_ratio)
            )
            val_edge_count = min(
                remaining_edge, remaining_val_size - val_positive_count
            )
        else:
            val_positive_count = 0
            val_edge_count = 0

        # 抽取正类和边缘类样本
        val_positive = (
            random.sample(positive_samples, val_positive_count)
            if val_positive_count > 0
            else []
        )
        val_edge = (
            random.sample(edge_samples, val_edge_count) if val_edge_count > 0 else []
        )

        # 剩余的进入训练集
        remaining_positive = [s for s in positive_samples if s not in val_positive]
        remaining_edge = [s for s in edge_samples if s not in val_edge]

        # 合并验证集和训练集
        val_samples = val_negative + val_positive + val_edge
        train_samples = remaining_negative + remaining_positive + remaining_edge

        # 打乱顺序
        random.shuffle(val_samples)
        random.shuffle(train_samples)

        # 验证分布
        val_negative_count = sum(
            1
            for s in val_samples
            if KnowledgeLevelExtractor.extract_knowledge_level(s) == "negative"
        )
        actual_negative_ratio = (
            val_negative_count / len(val_samples) if val_samples else 0
        )

        logger.info(
            f"验证集分布: 总计={len(val_samples)}, "
            f"否定类={val_negative_count} ({actual_negative_ratio:.1%})"
        )

        if actual_negative_ratio < self.min_negative_ratio:
            logger.warning(
                f"验证集否定类比例 ({actual_negative_ratio:.1%}) "
                f"低于要求 ({self.min_negative_ratio:.1%})"
            )

        return train_samples, val_samples

    def save_jsonl(self, samples: List[Dict], file_path: Path):
        """保存为JSONL格式"""
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        logger.info(f"已保存 {len(samples)} 条样本至 {file_path}")

    def print_distribution(self, samples: List[Dict], name: str):
        """打印样本分布"""
        levels = [KnowledgeLevelExtractor.extract_knowledge_level(s) for s in samples]
        counter = Counter(levels)

        logger.info(f"{name} 分布:")
        for level, count in counter.most_common():
            level_name = {"positive": "明知", "negative": "不明知", "edge": "边缘"}.get(
                level, level
            )
            logger.info(f"  {level_name}: {count} ({count / len(samples):.1%})")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据集划分脚本")
    parser.add_argument(
        "--input",
        type=str,
        default="data/training/processed.jsonl",
        help="输入JSONL文件路径 (default: data/training/processed.jsonl)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/training",
        help="输出目录 (default: data/training)",
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.1, help="验证集比例 (default: 0.1)"
    )
    parser.add_argument(
        "--min-negative-ratio",
        type=float,
        default=0.2,
        help="验证集最小否定类比例 (default: 0.2)",
    )
    parser.add_argument("--seed", type=int, default=42, help="随机种子 (default: 42)")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    input_file = project_root / args.input
    output_dir = project_root / args.output_dir

    # 检查输入文件
    if not input_file.exists():
        logger.error(f"输入文件不存在: {input_file}")
        logger.error("请先运行数据处理脚本: python scripts/data_processor.py")
        return

    # 加载数据
    logger.info(f"加载数据: {input_file}")
    samples = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    logger.info(f"加载 {len(samples)} 条样本")

    if len(samples) < 10:
        logger.warning(f"样本量过少 ({len(samples)})，建议至少收集100条样本")

    # 划分数据集
    splitter = DatasetSplitter(
        val_ratio=args.val_ratio,
        min_negative_ratio=args.min_negative_ratio,
        seed=args.seed,
    )

    train_samples, val_samples = splitter.split(samples)

    # 保存结果
    train_file = output_dir / "train.jsonl"
    val_file = output_dir / "val.jsonl"

    splitter.save_jsonl(train_samples, train_file)
    splitter.save_jsonl(val_samples, val_file)

    # 打印分布
    print("\n" + "=" * 60)
    print("数据集划分完成")
    print(f"训练集: {len(train_samples)} 条 -> {train_file}")
    splitter.print_distribution(train_samples, "训练集")
    print(f"\n验证集: {len(val_samples)} 条 -> {val_file}")
    splitter.print_distribution(val_samples, "验证集")
    print("=" * 60)


if __name__ == "__main__":
    main()
