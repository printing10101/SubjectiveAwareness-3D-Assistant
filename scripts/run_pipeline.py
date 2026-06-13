#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整数据集构建流水线
一键执行：爬取 → 处理 → 划分 → 报告生成
"""

import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_script(script_name: str, args: list = None) -> bool:
    """执行脚本"""
    cmd = [sys.executable, str(script_name)]
    if args:
        cmd.extend(args)

    logger.info(f"执行: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    """主流水线"""
    import argparse

    parser = argparse.ArgumentParser(description="数据集构建一键流水线")
    parser.add_argument("--skip-crawl", action="store_true", help="跳过爬取步骤")
    parser.add_argument("--max-pages", type=int, default=50, help="爬取最大页数")
    parser.add_argument("--interval", type=float, default=2.0, help="请求间隔")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行")

    args = parser.parse_args()

    scripts_dir = Path(__file__).parent

    logger.info("=" * 60)
    logger.info("法律领域指令微调数据集构建流水线")
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 步骤1: 爬取数据
    if not args.skip_crawl:
        logger.info("\n[步骤 1/4] 爬取裁判文书数据")
        success = run_script(
            scripts_dir / "crawl_judgments.py",
            ["--max-pages", str(args.max_pages), "--interval", str(args.interval)],
        )
        if not success:
            logger.error("爬取步骤失败")
            return
    else:
        logger.info("\n[步骤 1/4] 跳过爬取（使用已有数据）")

    # 步骤2: 数据处理
    logger.info("\n[步骤 2/4] 数据处理与清洗")
    success = run_script(scripts_dir / "data_processor.py")
    if not success:
        logger.error("数据处理步骤失败")
        return

    # 步骤3: 数据集划分
    logger.info("\n[步骤 3/4] 划分训练集和验证集")
    success = run_script(scripts_dir / "split_dataset.py")
    if not success:
        logger.error("数据集划分步骤失败")
        return

    # 步骤4: 生成报告
    logger.info("\n[步骤 4/4] 生成数据集构建报告")
    success = run_script(scripts_dir / "generate_report.py")
    if not success:
        logger.error("报告生成步骤失败")
        return

    logger.info("\n" + "=" * 60)
    logger.info("数据集构建流水线完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
