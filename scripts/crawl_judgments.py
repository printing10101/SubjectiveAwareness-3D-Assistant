#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
裁判文书数据爬取脚本
目标：贵州地区帮助信息网络犯罪活动罪（帮信罪）判决书

注意：中国裁判文书网使用动态加密(ciphertext)和验证码机制，直接爬取需要破解加密算法。
本脚本提供多种数据获取方式：
1. 通过裁判文书网API（需处理ciphertext加密）
2. 从公开的法律数据源获取
3. 导入本地已有的判决书数据

建议：对于学术研究，优先考虑通过正规渠道获取数据或使用已有的公开数据集。
"""

import sys
import time
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# 配置日志
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / f"crawler_{datetime.now().strftime('%Y-%m-%d')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class JudgmentRecord:
    """判决书数据记录"""

    case_id: str
    title: str
    court: str
    case_number: str
    judgment_date: str
    case_type: str
    content: str
    source_url: str
    crawl_time: str
    content_hash: str


class CrawlerConfig:
    """爬虫配置"""

    BASE_URL = "https://wenshu.court.gov.cn"
    SEARCH_URL = "https://wenshu.court.gov.cn/website/parse/rest.q4w"

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    REQUEST_INTERVAL = 3.0
    MAX_REQUEST_INTERVAL = 15.0
    TIMEOUT = 30

    PROVINCE = "贵州省"
    CASE_CAUSE = "帮助信息网络犯罪活动罪"

    RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
    MAX_RETRIES = 3


class JudgmentCrawler:
    """裁判文书爬虫 - 支持多数据源"""

    def __init__(self, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.config.USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": self.config.BASE_URL,
            }
        )

        self.stats = {
            "total_fetched": 0,
            "success_count": 0,
            "fail_count": 0,
            "duplicate_count": 0,
            "errors": [],
        }

        self.seen_ids = set()
        self.config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 存储有效的session cookie
        self._session_valid = False

    def _calculate_hash(self, content: str) -> str:
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _wait(self, base_interval: float = None):
        interval = base_interval or self.config.REQUEST_INTERVAL
        import random

        jitter = random.uniform(0.8, 1.5)
        time.sleep(interval * jitter)

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        data: Dict = None,
        headers: Dict = None,
        retries: int = None,
    ) -> Optional[requests.Response]:
        retries = retries if retries is not None else self.config.MAX_RETRIES

        for attempt in range(retries):
            try:
                self._wait()

                req_headers = headers or {}

                if method.upper() == "GET":
                    response = self.session.get(
                        url, headers=req_headers, timeout=self.config.TIMEOUT
                    )
                else:
                    req_headers["Content-Type"] = "application/x-www-form-urlencoded"
                    response = self.session.post(
                        url, data=data, headers=req_headers, timeout=self.config.TIMEOUT
                    )

                response.raise_for_status()
                response.encoding = response.apparent_encoding
                return response

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"请求失败 (尝试 {attempt + 1}/{retries}): {url} - {str(e)}"
                )
                if attempt < retries - 1:
                    wait_time = min(
                        self.config.REQUEST_INTERVAL * (2**attempt),
                        self.config.MAX_REQUEST_INTERVAL,
                    )
                    self._wait(wait_time)
                else:
                    error_msg = f"请求最终失败: {url} - {str(e)}"
                    logger.error(error_msg)
                    self.stats["errors"].append(error_msg)
                    return None

    def _get_ciphertext(self) -> Optional[str]:
        """
        获取裁判文书网API所需的ciphertext参数
        需要访问首页获取加密参数

        注意：这里需要逆向工程的加密逻辑，以下为占位实现
        """
        try:
            # 访问首页获取session和加密参数
            self.session.get(self.config.BASE_URL, timeout=10)

            # 尝试从页面中提取加密参数
            # 实际需要根据页面JavaScript逻辑解密
            # 这里仅做占位
            return None

        except Exception as e:
            logger.warning(f"获取ciphertext失败: {str(e)}")
            return None

    def search_judgments(
        self, page: int = 1, page_size: int = 15
    ) -> Optional[List[Dict]]:
        """搜索判决书"""
        # 尝试获取ciphertext
        ciphertext = self._get_ciphertext()

        if not ciphertext:
            logger.warning("无法获取ciphertext，裁判文书网可能需要验证码")
            self.stats["errors"].append("ciphertext获取失败，可能需要人工验证码")
            return None

        form_data = {
            "pageId": "",
            "pageSize": str(page_size),
            "sortFields": "s50:desc",
            "ciphertext": ciphertext,
            "pageNum": str(page),
            "queryCondition": json.dumps(
                [
                    {"key": "法院省份", "value": self.config.PROVINCE},
                    {"key": "案由", "value": self.config.CASE_CAUSE},
                ]
            ),
        }

        url = self.config.SEARCH_URL
        response = self._make_request(url, method="POST", data=form_data)

        if not response:
            return None

        try:
            data = response.json()
            if not data.get("success"):
                logger.warning(f"API返回失败: {data}")
                return None

            if "relDocInfos" in data:
                return data.get("relDocInfos", [])
            elif "result" in data and data["result"]:
                return data["result"]
            else:
                logger.warning(f"API响应格式未知: {list(data.keys())}")
                return []
        except json.JSONDecodeError:
            logger.warning("API响应非JSON格式")
            return None

    def fetch_judgment_detail(self, doc_id: str) -> Optional[str]:
        """获取判决书详情"""
        url = f"{self.config.BASE_URL}/website/paperinfo/paperdetail"

        ciphertext = self._get_ciphertext()
        form_data = {
            "docId": doc_id,
            "ciphertext": ciphertext or "",
        }

        response = self._make_request(url, method="POST", data=form_data)
        if not response:
            return None

        try:
            soup = BeautifulSoup(response.text, "html.parser")

            for selector in [
                ".article_content",
                ".content",
                "#content",
                ".paper_content",
                ".fulltext",
            ]:
                content_div = soup.select_one(selector)
                if content_div:
                    text = content_div.get_text(separator="\n", strip=True)
                    if len(text) > 100:
                        return text

            body = soup.find("body")
            if body:
                text = body.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return text

            return None

        except Exception as e:
            logger.error(f"解析详情页失败: {doc_id} - {str(e)}")
            return None

    def extract_subjective_knowledge(self, content: str) -> Dict:
        """提取主观明知相关段落"""
        result = {
            "case_facts": "",
            "evidence_description": "",
            "court_reasoning": "",
            "knowledge_conclusion": "",
        }

        knowledge_keywords = [
            "主观明知",
            "明知",
            "应当知道",
            "知道或者应当知道",
            "清楚",
            "认识到",
            "意识到",
            "主观方面",
        ]

        paragraphs = content.split("\n")

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if any(kw in para for kw in ["经审理查明", "案件事实", "事实如下"]):
                result["case_facts"] += para + "\n"

            if any(kw in para for kw in ["证据", "证明", "证实"]):
                result["evidence_description"] += para + "\n"

            if any(kw in para.lower() for kw in knowledge_keywords):
                result["court_reasoning"] += para + "\n"

            if any(kw in para for kw in ["本院认为", "认定", "判决如下"]):
                result["knowledge_conclusion"] += para + "\n"

        return result

    def save_raw_data(self, record: JudgmentRecord):
        file_path = self.config.RAW_DATA_DIR / f"{record.case_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(record), f, ensure_ascii=False, indent=2)

    def load_existing_ids(self) -> set:
        existing_ids = set()
        for file_path in self.config.RAW_DATA_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    existing_ids.add(data.get("case_id"))
            except Exception:
                continue
        return existing_ids

    def run(self, max_pages: int = 50, page_size: int = 15):
        """执行爬取任务"""
        logger.info(f"开始爬取 {self.config.PROVINCE} {self.config.CASE_CAUSE} 判决书")
        logger.info(f"目标页数: {max_pages}, 每页数量: {page_size}")

        self.seen_ids = self.load_existing_ids()
        logger.info(f"已存在 {len(self.seen_ids)} 条记录，将跳过")

        consecutive_failures = 0
        max_consecutive_failures = 3

        for page in tqdm(range(1, max_pages + 1), desc="爬取进度"):
            logger.info(f"正在爬取第 {page} 页")

            results = self.search_judgments(page=page, page_size=page_size)

            if results is None:
                logger.warning(f"第 {page} 页获取失败（可能需要验证码或ciphertext）")
                self.stats["fail_count"] += 1
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"连续失败 {max_consecutive_failures} 次")
                    logger.info("裁判文书网反爬机制较严格，建议：")
                    logger.info("1. 手动获取数据后放入 data/raw/ 目录")
                    logger.info("2. 使用已公开的法律数据集")
                    logger.info("3. 通过正规渠道申请数据访问权限")
                    self.stats["errors"].append(
                        "连续失败，裁判文书网可能需要验证码或人工交互"
                    )
                    break
                continue

            consecutive_failures = 0

            if not results:
                logger.info(f"第 {page} 页无数据，可能已到达末页")
                break

            self.stats["total_fetched"] += len(results)

            for item in results:
                doc_id = item.get("docId") or item.get("id") or item.get("文书ID")
                if not doc_id:
                    continue

                if doc_id in self.seen_ids:
                    self.stats["duplicate_count"] += 1
                    continue

                content = self.fetch_judgment_detail(doc_id)
                if not content:
                    self.stats["fail_count"] += 1
                    continue

                if not any(
                    kw in content for kw in ["明知", "知道", "应当知道", "主观"]
                ):
                    self.stats["fail_count"] += 1
                    continue

                record = JudgmentRecord(
                    case_id=doc_id,
                    title=item.get("title", item.get("文书名称", "")),
                    court=item.get("court", item.get("法院名称", "")),
                    case_number=item.get("caseNo", item.get("案号", "")),
                    judgment_date=item.get("judgeDate", item.get("裁判日期", "")),
                    case_type=self.config.CASE_CAUSE,
                    content=content,
                    source_url=(f"{self.config.BASE_URL}/detail/{doc_id}"),
                    crawl_time=datetime.now().isoformat(),
                    content_hash=self._calculate_hash(content),
                )

                self.save_raw_data(record)
                self.seen_ids.add(doc_id)
                self.stats["success_count"] += 1

                logger.info(f"成功保存: {record.case_number}")

        self._print_stats()

        stats_file = self.config.RAW_DATA_DIR / "crawl_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

        logger.info(f"爬取完成，统计信息已保存至 {stats_file}")
        return self.stats

    def _print_stats(self):
        logger.info("=" * 50)
        logger.info("爬取统计:")
        logger.info(f"  获取总数: {self.stats['total_fetched']}")
        logger.info(f"  成功数量: {self.stats['success_count']}")
        logger.info(f"  失败数量: {self.stats['fail_count']}")
        logger.info(f"  去重数量: {self.stats['duplicate_count']}")
        logger.info(f"  错误数量: {len(self.stats['errors'])}")
        if self.stats["errors"]:
            logger.info("  错误详情:")
            for error in self.stats["errors"][:10]:
                logger.info(f"    - {error}")
        logger.info("=" * 50)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="裁判文书数据爬取脚本")
    parser.add_argument("--max-pages", type=int, default=50, help="最大爬取页数")
    parser.add_argument("--page-size", type=int, default=15, help="每页文书数量")
    parser.add_argument("--province", type=str, default="贵州省", help="目标省份")
    parser.add_argument(
        "--case-cause", type=str, default="帮助信息网络犯罪活动罪", help="案由"
    )
    parser.add_argument("--interval", type=float, default=3.0, help="请求间隔秒数")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行")

    args = parser.parse_args()

    if args.dry_run:
        logger.info("模拟运行模式")
        logger.info("实际运行: python scripts/crawl_judgments.py --max-pages 50")
        return

    config = CrawlerConfig()
    config.PROVINCE = args.province
    config.CASE_CAUSE = args.case_cause
    config.REQUEST_INTERVAL = args.interval

    crawler = JudgmentCrawler(config)
    stats = crawler.run(max_pages=args.max_pages, page_size=args.page_size)

    print("\n" + "=" * 60)
    print("爬取任务完成")
    print(f"成功获取: {stats['success_count']} 条")
    print(f"失败: {stats['fail_count']} 条")
    print(f"数据保存位置: {config.RAW_DATA_DIR}")

    if stats["success_count"] == 0:
        print("\n提示：裁判文书网反爬机制严格，建议：")
        print("1. 使用已公开的法律数据集")
        print("2. 从 data/raw/ 目录导入已有的判决书数据")
        print("3. 运行 python scripts/generate_sample_data.py 生成示例数据用于测试")

    print("=" * 60)


if __name__ == "__main__":
    main()
