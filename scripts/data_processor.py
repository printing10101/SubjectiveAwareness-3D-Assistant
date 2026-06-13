#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
法律领域训练数据处理器
功能：
1. 数据清洗：去除无关信息、标准化文本格式、处理特殊字符
2. 文本分段：合理划分案件事实文本，确保语义完整
3. 格式转换：将处理后的文本转换为JSONL格式
4. 质量过滤：自动质量评估机制，过滤低质量样本
"""

import sys
import re
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import unicodedata

from tqdm import tqdm

# 配置日志
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

date_str = datetime.now().strftime("%Y-%m-%d")
log_filename = LOG_DIR / f"data_processor_{date_str}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class TextCleaner:
    """文本清洗器"""

    # 隐私信息正则模式
    PRIVACY_PATTERNS = [
        (r"\b\d{17}[\dXx]\b", "[身份证号]"),  # 身份证号
        (r"\b1[3-9]\d{9}\b", "[手机号]"),  # 手机号
        (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "[邮箱]"),  # 邮箱
        (r"\b(?:\d{3,4}-)?\d{7,8}\b", "[电话号码]"),  # 座机号码
        (r"[\u4e00-\u9fa5]{2,4}(?:先生|女士|小姐|同志)", "[姓名]"),  # 带称呼的姓名
    ]

    # 特殊字符模式
    SPECIAL_CHARS = [
        (r"\n{3,}", "\n\n"),  # 多余换行
        (r"[ \t]+", " "),  # 多余空格
        (r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", ""),  # 控制字符
    ]

    @classmethod
    def clean(cls, text: str) -> str:
        """执行完整清洗流程"""
        if not text:
            return ""

        # 标准化Unicode
        text = unicodedata.normalize("NFC", text)

        # 去除隐私信息
        for pattern, replacement in cls.PRIVACY_PATTERNS:
            text = re.sub(pattern, replacement, text)

        # 处理特殊字符
        for pattern, replacement in cls.SPECIAL_CHARS:
            text = re.sub(pattern, replacement, text)

        # 去除首尾空白
        text = text.strip()

        return text

    @classmethod
    def desensitize_personal_info(cls, text: str) -> str:
        """
        脱敏处理：去除个人敏感信息
        保留案件分析必要的信息，去除可识别个人的信息
        """
        # 替换被告人/证人等姓名模式: "被告人XXX"、"证人XXX"
        name_pattern = (
            r"(被告人|证人|同案犯|被害人|上诉人|被上诉人)"
            r"([张王李赵刘陈杨黄周吴徐孙胡朱郭林何高马罗"
            r"梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕]{1,3})"
        )
        text = re.sub(name_pattern, r"\1[姓名]", text)

        # 替换常见姓名模式 (2-4个汉字，前无特定修饰)
        common_name_pattern = (
            r"(?<![\u4e00-\u9fa5])"
            r"([张王李赵刘陈杨黄][\u4e00-\u9fa5]{1,3})"
            r"(?=(?:系|被|于|在|与|将|向|从|对|称|说|供|述))"
        )
        text = re.sub(common_name_pattern, "[姓名]", text)

        # 替换具体地址
        address_pattern = (
            r"[\u4e00-\u9fa5]{2,}(?:省(?:份)?|市(?:县)?|县(?:区)?|区(?:镇)?|"
            r"镇(?:乡)?|乡(?:村)?|村|街道|路|巷|弄|号|栋|楼|室)"
        )
        text = re.sub(address_pattern, "[地址]", text)

        # 替换具体金额（保留数字）
        amount_pattern = r"(\d+(?:\.\d+)?)(?:万|亿|千|百|十)?元"
        text = re.sub(amount_pattern, lambda m: f"[金额{m.group(1)}元]", text)

        return text


class TextSegmenter:
    """文本分段器"""

    @classmethod
    def segment_by_structure(cls, content: str) -> Dict[str, str]:
        """
        按判决书结构分段
        返回各部分的文本内容
        """
        segments = {
            "header": "",  # 首部（法院、案号等）
            "facts": "",  # 案件事实
            "evidence": "",  # 证据部分
            "reasoning": "",  # 法院说理
            "judgment": "",  # 判决结果
        }

        # 关键词分割
        patterns = {
            "header": r"^(.*?)(?:经审理查明|事实如下)",
            "facts": r"(?:经审理查明|事实如下)(.*?)(?:上述|以上|本院认为)",
            "evidence": r"(?:证据|证明|证实)(.*?)(?:本院认为)",
            "reasoning": r"(?:本院认为|本院认为，?)(.*?)(?:判决如下|判决如下：)",
            "judgment": r"(?:判决如下|判决如下：)(.*)$",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.DOTALL)
            if match:
                segments[key] = match.group(1).strip()

        # 如果正则分割失败，尝试简单关键词分割
        if not any(segments.values()):
            segments = cls._simple_segment(content)

        return segments

    @classmethod
    def _simple_segment(cls, content: str) -> Dict[str, str]:
        """简单分段方法"""
        paragraphs = content.split("\n")
        segments = {
            "header": "",
            "facts": "",
            "evidence": "",
            "reasoning": "",
            "judgment": "",
        }

        current_section = "header"
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 检测段落类型
            if any(kw in para for kw in ["经审理查明", "事实如下", "查明"]):
                current_section = "facts"
            elif any(kw in para for kw in ["证据", "证明", "证实"]):
                current_section = "evidence"
            elif any(kw in para for kw in ["本院认为", "认为"]):
                current_section = "reasoning"
            elif any(kw in para for kw in ["判决", "裁定如下"]):
                current_section = "judgment"

            segments[current_section] += para + "\n"

        return segments

    @classmethod
    def extract_knowledge_content(cls, segments: Dict[str, str]) -> str:
        """提取与主观明知最相关的内容"""
        # 主要使用案件事实和法院说理部分
        facts = segments.get("facts", "")
        reasoning = segments.get("reasoning", "")

        combined = f"{facts}\n\n{reasoning}".strip()

        # 限制长度，避免过长
        if len(combined) > 5000:
            combined = combined[:5000]
            # 确保在句子边界截断
            last_period = combined.rfind("。")
            if last_period > 4000:
                combined = combined[: last_period + 1]

        return combined


class KnowledgeAnalyzer:
    """主观明知分析器"""

    @classmethod
    def analyze(cls, facts: str, reasoning: str, judgment: str) -> Dict:
        """
        三维度分析：
        1. 明知程度评估
        2. 认定依据
        3. 证据链完整性
        """
        return {
            "明知程度评估": cls._assess_knowledge_level(facts, reasoning, judgment),
            "认定依据": cls._extract_basis(reasoning),
            "证据链完整性": cls._assess_evidence_chain(facts, reasoning),
        }

    @classmethod
    def _assess_knowledge_level(cls, facts: str, reasoning: str, judgment: str) -> str:
        """评估明知程度"""
        combined = f"{facts} {reasoning} {judgment}"

        # 关键词判断
        positive_knowledge = ["明知", "明确知道", "清楚知道", "直接故意", "确知"]
        negative_knowledge = ["不明知", "不知道", "无法认定", "没有证据证明", "不明"]
        edge_knowledge = ["应当知道", "可能知道", "可以认定", "推定", "存疑"]

        positive_score = sum(1 for kw in positive_knowledge if kw in combined)
        negative_score = sum(1 for kw in negative_knowledge if kw in combined)
        edge_score = sum(1 for kw in edge_knowledge if kw in combined)

        # 判断结论
        if positive_score > negative_score and positive_score > edge_score:
            return "明确认定明知"
        elif negative_score > positive_score:
            return "明确认定不明知"
        else:
            return "边缘/存疑情形"

    @classmethod
    def _extract_basis(cls, reasoning: str) -> List[str]:
        """提取认定依据"""
        basis = []

        # 常见认定依据类型
        basis_patterns = [
            (r"交易方式(?:[^。]*?)(?:异常|不合常理)", "交易方式异常"),
            (r"价格(?:[^。]*?)(?:明显低于|明显高于|异常)", "价格异常"),
            (r"通讯记录|聊天记录|微信|QQ", "通讯记录证据"),
            (r"银行流水|转账|资金", "资金流向证据"),
            (r"同案犯|共犯|供述|指认", "同案犯供述"),
            (r"前科|劣迹|违法记录", "前科劣迹"),
            (r"专业知识|技术能力|从业经验", "专业知识背景"),
            (r"报酬|获利|高额收益|提成", "异常获利"),
        ]

        for pattern, basis_type in basis_patterns:
            if re.search(pattern, reasoning):
                basis.append(basis_type)

        return basis if basis else ["综合认定"]

    @classmethod
    def _assess_evidence_chain(cls, facts: str, reasoning: str) -> str:
        """评估证据链完整性"""
        combined = f"{facts} {reasoning}"

        evidence_types = [
            "书证",
            "物证",
            "证人证言",
            "被害人陈述",
            "被告人供述",
            "鉴定意见",
            "勘验笔录",
            "电子数据",
        ]

        found_evidence = [e for e in evidence_types if e in combined]

        if len(found_evidence) >= 5:
            return "完整（5种以上证据）"
        elif len(found_evidence) >= 3:
            return "较完整（3-4种证据）"
        elif len(found_evidence) >= 2:
            return "一般（2种证据）"
        else:
            return "薄弱（单一证据）"


class QualityFilter:
    """数据质量过滤器"""

    MIN_TEXT_LENGTH = 200  # 最小文本长度
    MAX_TEXT_LENGTH = 8000  # 最大文本长度
    MIN_KNOWLEDGE_KEYWORDS = 1  # 最少明知关键词数量

    @classmethod
    def filter(cls, record: Dict) -> Tuple[bool, str]:
        """
        过滤单条记录
        返回 (是否通过, 原因)
        """
        content = record.get("content", "")

        # 长度检查
        if len(content) < cls.MIN_TEXT_LENGTH:
            return False, f"文本过短({len(content)} < {cls.MIN_TEXT_LENGTH})"

        if len(content) > cls.MAX_TEXT_LENGTH:
            return False, f"文本过长({len(content)} > {cls.MAX_TEXT_LENGTH})"

        # 关键词检查
        knowledge_keywords = ["明知", "知道", "应当知道", "主观", "故意"]
        has_knowledge = any(kw in content for kw in knowledge_keywords)
        if not has_knowledge:
            return False, "不包含主观明知相关关键词"

        # 结构完整性检查
        segments = TextSegmenter.segment_by_structure(content)
        if not segments.get("facts") and not segments.get("reasoning"):
            return False, "缺少案件事实或法院说理部分"

        # 特殊字符检查
        if cls._has_too_many_special_chars(content):
            return False, "包含过多特殊字符或乱码"

        return True, "通过"

    @classmethod
    def _has_too_many_special_chars(cls, text: str, threshold: float = 0.1) -> bool:
        """检查特殊字符比例是否过高"""
        if not text:
            return False

        special_count = 0
        special_chars = set("\n\t")
        for char in text:
            cat_starts_c = unicodedata.category(char).startswith("C")
            if cat_starts_c and char not in special_chars:
                special_count += 1

        return (special_count / len(text)) > threshold


class DataProcessor:
    """数据处理器主类"""

    def __init__(self, raw_data_dir: Path, output_dir: Path):
        self.raw_data_dir = raw_data_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            "total_records": 0,
            "passed_filter": 0,
            "failed_filter": 0,
            "filter_reasons": {},
            "duplicate_removed": 0,
            "knowledge_distribution": {
                "明确认定明知": 0,
                "明确认定不明知": 0,
                "边缘/存疑情形": 0,
            },
        }

    def load_raw_data(self) -> List[Dict]:
        """加载所有原始数据"""
        records = []

        json_files = list(self.raw_data_dir.glob("*.json"))
        logger.info(f"找到 {len(json_files)} 个原始数据文件")

        for file_path in tqdm(json_files, desc="加载数据"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    record = json.load(f)
                    records.append(record)
            except Exception as e:
                logger.warning(f"加载文件失败: {file_path} - {str(e)}")

        self.stats["total_records"] = len(records)
        logger.info(f"成功加载 {len(records)} 条记录")
        return records

    def process(self, records: List[Dict]) -> List[Dict]:
        """
        完整处理流程

        Args:
            records: 原始记录列表

        Returns:
            处理后的训练样本列表
        """
        processed = []
        seen_hashes = set()

        for record in tqdm(records, desc="处理数据"):
            # 1. 质量过滤
            passed, reason = QualityFilter.filter(record)
            if not passed:
                self.stats["failed_filter"] += 1
                self.stats["filter_reasons"][reason] = (
                    self.stats["filter_reasons"].get(reason, 0) + 1
                )
                continue

            # 2. 去重
            content_hash = hashlib.md5(record.get("content", "").encode()).hexdigest()
            if content_hash in seen_hashes:
                self.stats["duplicate_removed"] += 1
                continue
            seen_hashes.add(content_hash)

            # 3. 数据清洗
            cleaned_content = TextCleaner.clean(record.get("content", ""))
            cleaned_content = TextCleaner.desensitize_personal_info(cleaned_content)

            # 4. 文本分段
            segments = TextSegmenter.segment_by_structure(cleaned_content)
            knowledge_content = TextSegmenter.extract_knowledge_content(segments)

            if not knowledge_content:
                self.stats["failed_filter"] += 1
                self.stats["filter_reasons"]["无有效主观明知内容"] = (
                    self.stats["filter_reasons"].get("无有效主观明知内容", 0) + 1
                )
                continue

            # 5. 三维度分析
            analysis = KnowledgeAnalyzer.analyze(
                segments.get("facts", ""),
                segments.get("reasoning", ""),
                segments.get("judgment", ""),
            )

            # 6. 构建训练样本
            sample = {
                "instruction": "分析以下案件的主观明知",
                "input": knowledge_content,
                "output": json.dumps(analysis, ensure_ascii=False),
            }

            # 统计分布
            knowledge_level = analysis["明知程度评估"]
            self.stats["knowledge_distribution"][knowledge_level] += 1

            processed.append(sample)
            self.stats["passed_filter"] += 1

        return processed

    def save_jsonl(self, samples: List[Dict], output_file: Path):
        """保存为JSONL格式"""
        with open(output_file, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        logger.info(f"已保存 {len(samples)} 条样本至 {output_file}")

    def save_stats(self):
        """保存处理统计"""
        stats_file = self.output_dir / "processing_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

        logger.info(f"处理统计已保存至 {stats_file}")

    def run(self):
        """执行完整处理流程"""
        logger.info("开始数据处理流程")

        # 1. 加载数据
        records = self.load_raw_data()
        if not records:
            logger.error("无原始数据，请先运行爬虫脚本")
            return None

        # 2. 处理数据
        processed = self.process(records)
        logger.info(f"处理完成，获得 {len(processed)} 条有效样本")

        # 3. 保存结果
        if processed:
            output_file = self.output_dir / "processed.jsonl"
            self.save_jsonl(processed, output_file)

        # 4. 保存统计
        self.save_stats()

        # 5. 输出统计摘要
        self._print_stats()

        return processed

    def _print_stats(self):
        """打印处理统计"""
        logger.info("=" * 60)
        logger.info("数据处理统计:")
        logger.info(f"  总记录数: {self.stats['total_records']}")
        logger.info(f"  通过过滤: {self.stats['passed_filter']}")
        logger.info(f"  未通过过滤: {self.stats['failed_filter']}")
        logger.info(f"  去重移除: {self.stats['duplicate_removed']}")
        logger.info("  明知分布:")
        for level, count in self.stats["knowledge_distribution"].items():
            logger.info(f"    - {level}: {count}")
        logger.info("  过滤原因:")
        for reason, count in self.stats["filter_reasons"].items():
            logger.info(f"    - {reason}: {count}")
        logger.info("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="法律领域训练数据处理器")
    parser.add_argument(
        "--raw-dir", type=str, default=None, help="原始数据目录 (default: data/raw)"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None, help="输出目录 (default: data/training)"
    )
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent

    raw_dir = Path(args.raw_dir) if args.raw_dir else project_root / "data" / "raw"
    output_dir = (
        Path(args.output_dir) if args.output_dir else project_root / "data" / "training"
    )

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 检查原始数据是否存在
    if not raw_dir.exists():
        logger.error(f"原始数据目录不存在: {raw_dir}")
        logger.error("请先运行爬虫脚本: python scripts/crawl_judgments.py")
        sys.exit(1)

    # 执行处理
    processor = DataProcessor(raw_dir, output_dir)
    processor.run()


if __name__ == "__main__":
    main()
