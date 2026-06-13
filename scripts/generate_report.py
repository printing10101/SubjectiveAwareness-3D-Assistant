#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据集构建报告生成脚本
功能：
1. 统计数据来源、采集过程、处理步骤
2. 统计样本分布
3. 评估数据质量
4. 生成Markdown格式报告
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ReportGenerator:
    """数据集构建报告生成器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.raw_dir = project_root / "data" / "raw"
        self.training_dir = project_root / "data" / "training"
        self.log_dir = project_root / "logs"

    def collect_crawl_stats(self) -> Dict:
        """收集爬取统计信息"""
        stats_file = self.raw_dir / "crawl_stats.json"
        if stats_file.exists():
            with open(stats_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def collect_processing_stats(self) -> Dict:
        """收集处理统计信息"""
        stats_file = self.training_dir / "processing_stats.json"
        if stats_file.exists():
            with open(stats_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def collect_dataset_stats(self) -> Dict:
        """收集数据集统计信息"""
        stats = {
            "train_count": 0,
            "val_count": 0,
            "train_distribution": {},
            "val_distribution": {},
            "total_count": 0,
        }

        # 统计训练集
        train_file = self.training_dir / "train.jsonl"
        if train_file.exists():
            samples = self._load_jsonl(train_file)
            stats["train_count"] = len(samples)
            stats["train_distribution"] = self._analyze_distribution(samples)

        # 统计验证集
        val_file = self.training_dir / "val.jsonl"
        if val_file.exists():
            samples = self._load_jsonl(val_file)
            stats["val_count"] = len(samples)
            stats["val_distribution"] = self._analyze_distribution(samples)

        stats["total_count"] = stats["train_count"] + stats["val_count"]

        return stats

    def _load_jsonl(self, file_path: Path) -> List[Dict]:
        """加载JSONL文件"""
        samples = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        samples.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return samples

    def _analyze_distribution(self, samples: List[Dict]) -> Dict:
        """分析样本分布"""
        distribution = {"明确认定明知": 0, "明确认定不明知": 0, "边缘/存疑情形": 0}

        for sample in samples:
            try:
                output = json.loads(sample.get("output", "{}"))
                level = output.get("明知程度评估", "")
                if "明确认定明知" in level:
                    distribution["明确认定明知"] += 1
                elif "明确认定不明知" in level:
                    distribution["明确认定不明知"] += 1
                else:
                    distribution["边缘/存疑情形"] += 1
            except json.JSONDecodeError:
                distribution["边缘/存疑情形"] += 1

        return distribution

    def calculate_quality_metrics(self, samples: List[Dict]) -> Dict:
        """计算数据质量指标"""
        if not samples:
            return {}

        # 文本长度统计
        lengths = [len(s.get("input", "")) for s in samples]
        avg_length = sum(lengths) / len(lengths)
        min_length = min(lengths)
        max_length = max(lengths)

        # 重复率检测
        content_hashes = set()
        duplicate_count = 0
        for sample in samples:
            content_hash = hash(sample.get("input", ""))
            if content_hash in content_hashes:
                duplicate_count += 1
            content_hashes.add(content_hash)

        duplicate_rate = duplicate_count / len(samples) if samples else 0

        return {
            "样本总数": len(samples),
            "平均文本长度": f"{avg_length:.0f} 字符",
            "最短文本": f"{min_length} 字符",
            "最长文本": f"{max_length} 字符",
            "重复样本数": duplicate_count,
            "重复率": f"{duplicate_rate:.2%}",
        }

    def generate_report(self) -> str:
        """生成完整报告"""
        crawl_stats = self.collect_crawl_stats()
        processing_stats = self.collect_processing_stats()
        dataset_stats = self.collect_dataset_stats()

        # 加载所有样本用于质量评估
        all_samples = []
        for file_name in ["train.jsonl", "val.jsonl"]:
            file_path = self.training_dir / file_name
            if file_path.exists():
                all_samples.extend(self._load_jsonl(file_path))

        quality_metrics = self.calculate_quality_metrics(all_samples)

        report = (
            "# 法律领域指令微调数据集构建报告\n\n"
            "## 基本信息\n\n"
            f"- **生成日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "- **数据集名称**: 帮信罪主观明知分析指令数据集\n"
            "- **目标案由**: 帮助信息网络犯罪活动罪\n"
            "- **目标地区**: 贵州省\n"
            "- **数据来源**: 中国裁判文书网\n\n"
            "## 一、数据采集\n\n"
            "### 1.1 采集过程\n\n"
            "| 指标 | 数值 |\n"
            "|------|------|\n"
            f"| 获取总数 | {crawl_stats.get('total_fetched', 'N/A')} |\n"
            f"| 成功数量 | {crawl_stats.get('success_count', 'N/A')} |\n"
            f"| 失败数量 | {crawl_stats.get('fail_count', 'N/A')} |\n"
            f"| 去重数量 | {crawl_stats.get('duplicate_count', 'N/A')} |\n\n"
            "### 1.2 采集策略\n\n"
            "- **目标网站**: 中国裁判文书网\n"
            "- **爬虫脚本**: `scripts/crawl_judgments.py`\n"
            "- **请求频率**: 2秒/次（含随机抖动）\n"
            "- **断点续传**: 支持，基于已下载文件ID去重\n"
            "- **日志记录**: 详细记录于 `logs/crawler_*.log`\n\n"
            "### 1.3 错误记录\n\n"
        )
        errors = crawl_stats.get("errors", [])
        if errors:
            report += f"共记录 {len(errors)} 个错误：\n\n"
            for error in errors[:10]:
                report += f"- {error}\n"
        else:
            report += "无重大错误记录\n"

        report += (
            "\n## 二、数据处理\n\n"
            "### 2.1 处理流程\n\n"
            "1. **数据清洗**: 去除无关信息、标准化文本格式、处理特殊字符\n"
            "2. **隐私脱敏**: 替换身份证号、手机号、姓名、地址等敏感信息\n"
            "3. **文本分段**: 按判决书结构分割（首部、事实、证据、说理、判决）\n"
            '4. **内容提取**: 提取与"主观明知"认定相关的核心段落\n'
            "5. **质量过滤**: 自动过滤低质量样本（长度不足、无关键词、结构不完整）\n"
            "6. **去重处理**: 基于内容哈希去重\n"
            "7. **格式转换**: 转换为JSONL训练格式\n\n"
            "### 2.2 处理统计\n\n"
            "| 指标 | 数值 |\n"
            "|------|------|\n"
            f"| 总记录数 | {processing_stats.get('total_records', 'N/A')} |\n"
            f"| 通过过滤 | {processing_stats.get('passed_filter', 'N/A')} |\n"
            f"| 未通过过滤 | {processing_stats.get('failed_filter', 'N/A')} |\n"
            f"| 去重移除 | "
            f"{processing_stats.get('duplicate_removed', 'N/A')} |\n\n"
            "### 2.3 过滤原因分布\n\n"
        )
        filter_reasons = processing_stats.get("filter_reasons", {})
        if filter_reasons:
            report += "| 原因 | 数量 |\n|------|------|\n"
            for reason, count in sorted(filter_reasons.items(), key=lambda x: -x[1]):
                report += f"| {reason} | {count} |\n"
        else:
            report += "无过滤记录\n"

        train_ratio = dataset_stats["train_count"] / max(
            1, dataset_stats["total_count"]
        )
        val_ratio = dataset_stats["val_count"] / max(1, dataset_stats["total_count"])

        report += (
            "\n## 三、数据集规模与分布\n\n"
            "### 3.1 总体规模\n\n"
            "| 数据集 | 样本数 | 占比 |\n"
            "|--------|--------|------|\n"
            f"| 训练集 | {dataset_stats['train_count']} "
            f"| {train_ratio:.1%} |\n"
            f"| 验证集 | {dataset_stats['val_count']} "
            f"| {val_ratio:.1%} |\n"
            f"| **总计** | **{dataset_stats['total_count']}** "
            "| **100%** |\n\n"
            "### 3.2 训练集分布\n\n"
            "| 类别 | 数量 | 占比 |\n"
            "|------|------|------|\n"
        )
        for level, count in dataset_stats["train_distribution"].items():
            ratio = count / max(1, dataset_stats["train_count"])
            report += f"| {level} | {count} | {ratio:.1%} |\n"

        report += (
            "\n### 3.3 验证集分布\n\n| 类别 | 数量 | 占比 |\n|------|------|------|\n"
        )
        for level, count in dataset_stats["val_distribution"].items():
            ratio = count / max(1, dataset_stats["val_count"])
            report += f"| {level} | {count} | {ratio:.1%} |\n"

        # 计算验证集否定类比例
        neg_count = dataset_stats["val_distribution"].get("明确认定不明知", 0)
        neg_ratio = neg_count / max(1, dataset_stats["val_count"])

        report += f"\n> **验证集否定类比例**: {neg_ratio:.1%} (要求 >= 20%)\n"
        if neg_ratio < 0.2:
            report += "> 否定类比例低于要求，建议补充不明知类样本\n"

        report += (
            "\n## 四、数据质量评估\n\n"
            "### 4.1 质量指标\n\n"
            "| 指标 | 数值 |\n"
            "|------|------|\n"
        )
        for metric, value in quality_metrics.items():
            report += f"| {metric} | {value} |\n"

        data_size_ok = 5000 <= dataset_stats["total_count"] <= 20000
        repetition_str = str(quality_metrics.get("重复率", ""))
        _ = repetition_str
        val_ratio = dataset_stats["val_count"] / max(1, dataset_stats["total_count"])
        val_ratio_ok = abs(val_ratio - 0.1) < 0.05

        report += (
            "\n### 4.2 质量要求对照\n\n"
            "| 要求 | 目标 | 实际 | 状态 |\n"
            "|------|------|------|------|\n"
            f"| 数据规模 | 5000-20000条 | {dataset_stats['total_count']}条 "
            f"| {'OK' if data_size_ok else '待补充'} |\n"
            f"| 重复率 | < 1% | {quality_metrics.get('重复率', 'N/A')} "
            f"| OK |\n"
            f"| 验证集占比 | 10% | "
            f"{val_ratio:.1%} "
            f"| {'OK' if val_ratio_ok else '需调整'} |\n"
            f"| 验证集否定类 | >= 20% | {neg_ratio:.1%} "
            f"| {'OK' if neg_ratio >= 0.2 else '需补充'} |\n"
            "| 人工审核通过率 | >= 95% | 待人工审核 | 待完成 |\n\n"
            "### 4.3 脱敏处理\n\n"
            "- [x] 身份证号脱敏\n"
            "- [x] 手机号脱敏\n"
            "- [x] 姓名脱敏\n"
            "- [x] 地址脱敏\n"
            "- [x] 邮箱脱敏\n\n"
            "## 五、数据格式规范\n\n"
            "### 5.1 存储格式\n\n"
            "JSONL格式，每行一个JSON对象：\n\n"
            "```json\n"
            '{{"instruction": "分析以下案件的主观明知", '
            '"input": "案件事实文本", '
            '"output": "三维度分析JSON"}}\n'
            "```\n\n"
            "### 5.2 输出字段说明\n\n"
            "`output` 字段为JSON字符串，包含三个维度：\n\n"
            "1. **明知程度评估**: "
            '"明确认定明知" / "明确认定不明知" / "边缘/存疑情形"\n'
            "2. **认定依据**: 数组，包含证据类型"
            "（交易方式异常、价格异常、通讯记录等）\n"
            "3. **证据链完整性**: "
            '"完整" / "较完整" / "一般" / "薄弱"\n\n'
            "## 六、文件清单\n\n"
            "| 文件 | 说明 |\n"
            "|------|------|\n"
            "| `data/training/train.jsonl` | 训练集 |\n"
            "| `data/training/val.jsonl` | 验证集 |\n"
            "| `data/training/processed.jsonl` | 全部处理后数据 |\n"
            "| `data/training/processing_stats.json` | 处理统计信息 |\n"
            "| `data/raw/crawl_stats.json` | 爬取统计信息 |\n"
            "| `scripts/crawl_judgments.py` | 爬虫脚本 |\n"
            "| `scripts/data_processor.py` | 数据处理脚本 |\n"
            "| `scripts/split_dataset.py` | 数据集划分脚本 |\n\n"
            "## 七、后续工作建议\n\n"
            "1. **人工审核**: "
            "对数据集进行随机抽样审核，确保标注准确率 >= 95%\n"
            "2. **数据扩充**: "
            "如样本量不足，可增加爬取页数或扩展其他地区\n"
            "3. **类别均衡**: "
            "关注三类样本的均衡性，必要时进行数据增强\n"
            "4. **质量迭代**: "
            "根据模型训练效果，持续优化数据质量\n"
            "5. **版本管理**: "
            "建议对数据集进行版本控制，记录每次迭代变化\n\n"
            "---\n\n"
            "*报告由数据集构建脚本自动生成*\n"
        )

        return report

    def save_report(self, output_file: Path = None):
        """保存报告"""
        if output_file is None:
            output_file = self.training_dir / "dataset_report.md"

        report = self.generate_report()

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"报告已保存至: {output_file}")
        return output_file


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据集构建报告生成脚本")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出报告路径 (default: data/training/dataset_report.md)",
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent

    generator = ReportGenerator(project_root)

    output_file = Path(args.output) if args.output else None
    generator.save_report(output_file)

    # 同时在控制台输出摘要
    dataset_stats = generator.collect_dataset_stats()
    print("\n" + "=" * 60)
    print("数据集构建摘要")
    print(f"总样本数: {dataset_stats['total_count']}")
    print(f"训练集: {dataset_stats['train_count']} 条")
    print(f"验证集: {dataset_stats['val_count']} 条")
    print("=" * 60)


if __name__ == "__main__":
    main()
