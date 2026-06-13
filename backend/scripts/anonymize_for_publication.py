"""一次性数据脱敏脚本.

读取 data/raw/ 下所有 .json 文件，调用 app.utils.anonymizer.anonymize_text
对文本字段进行脱敏，输出到 data/cleaned/CASE_XXXX.json。

用法:
    python backend/scripts/anonymize_for_publication.py
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

# 确保项目根目录在 sys.path 中，以便导入 app 模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.utils.anonymizer import anonymize_text  # noqa: E402

# ── 路径配置 ──────────────────────────────────────────────
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"

# ── 日志配置 ──────────────────────────────────────────────
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f"anonymization_log_{_timestamp}.txt"

logger = logging.getLogger("anonymize")
logger.setLevel(logging.DEBUG)

_fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

_sh = logging.StreamHandler(sys.stdout)
_sh.setLevel(logging.INFO)
_sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

logger.addHandler(_fh)
logger.addHandler(_sh)

# ── 需要脱敏的文本字段 ────────────────────────────────────
TEXT_FIELDS = [
    "title",
    "content",
    "court",
    "case_number",
    "source_url",
]


def _anonymize_record(record: dict) -> dict:
    """对单条案件记录执行脱敏，返回新 dict."""
    result = dict(record)
    for field in TEXT_FIELDS:
        value = result.get(field)
        if value and isinstance(value, str):
            result[field] = anonymize_text(value)
    return result


def _collect_raw_files() -> list[Path]:
    """递归扫描 RAW_DIR 下所有 .json 文件（排除 crawl_stats.json 等非案件文件）."""
    files: list[Path] = []
    for p in sorted(RAW_DIR.rglob("*.json")):
        # 仅处理 CASE_ 开头的案件文件
        if p.stem.startswith("CASE_"):
            files.append(p)
    return files


def _verify_anonymized_file(filepath: Path) -> list[str]:
    """校验单个脱敏文件，返回发现的问题列表."""
    issues: list[str] = []
    try:
        text = filepath.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception as exc:
        return [f"无法读取/解析: {exc}"]

    # 合并所有文本字段
    combined = " ".join(str(data.get(f, "")) for f in TEXT_FIELDS)

    # 1. 身份证号（18 位 / 15 位）
    id18 = re.findall(r"(?<!\d)\d{17}[\dXx](?!\d)", combined)
    id15 = re.findall(r"(?<!\d)\d{15}(?!\d)", combined)
    # 过滤掉已脱敏格式（含 *）的匹配
    for m in id18:
        if "*" not in m:
            issues.append(f"疑似未脱敏 18 位身份证号: {m[:6]}...{m[-4:]}")
    for m in id15:
        if "*" not in m:
            issues.append(f"疑似未脱敏 15 位身份证号: {m[:6]}...{m[-4:]}")

    # 2. 银行卡号（16-19 位纯数字）
    bank_cards = re.findall(r"(?<!\d)\d{16,19}(?!\d)", combined)
    for m in bank_cards:
        if "*" not in m:
            issues.append(f"疑似未脱敏银行卡号: {m[:4]}...{m[-4:]}")

    # 3. 手机号（11 位，1 开头）
    phones = re.findall(r"(?<!\d)1[3-9]\d{9}(?!\d)", combined)
    for m in phones:
        if "*" not in m:
            issues.append(f"疑似未脱敏手机号: {m[:3]}****{m[-4:]}")

    # 4. 真实姓名模式（张某/李某 等未被替换的）
    name_pattern = re.compile(
        r"[张李王刘陈马赵黄周吴徐孙胡朱高林何郭罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟万段雷钱汤尹黎易常武乔贺赖龚文]某[某甲乙丙丁]?"
    )
    names = name_pattern.findall(combined)
    if names:
        issues.append(f"疑似未脱敏姓名: {', '.join(set(names))}")

    return issues


def run() -> None:
    """执行脱敏主流程."""
    logger.info("=" * 60)
    logger.info("数据脱敏脚本开始执行")
    logger.info("=" * 60)

    # 1. 确保输出目录存在
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("输出目录: %s", CLEANED_DIR)

    # 2. 收集原始文件
    raw_files = _collect_raw_files()
    logger.info("发现 %d 个待脱敏文件", len(raw_files))

    if not raw_files:
        logger.warning("未找到任何 CASE_*.json 文件，退出")
        return

    # 3. 逐文件脱敏
    success_count = 0
    fail_count = 0
    total_chars_before = 0
    total_chars_after = 0

    for idx, raw_path in enumerate(raw_files):
        out_name = f"CASE_{idx:04d}.json"
        out_path = CLEANED_DIR / out_name

        try:
            raw_text = raw_path.read_text(encoding="utf-8")
            record = json.loads(raw_text)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("文件读取/解析失败 [%s]: %s", raw_path.name, exc)
            fail_count += 1
            continue

        chars_before = sum(len(str(record.get(f, ""))) for f in TEXT_FIELDS)

        try:
            anonymized = _anonymize_record(record)
        except Exception as exc:
            logger.error("脱敏处理失败 [%s]: %s", raw_path.name, exc)
            fail_count += 1
            continue

        chars_after = sum(len(str(anonymized.get(f, ""))) for f in TEXT_FIELDS)
        total_chars_before += chars_before
        total_chars_after += chars_after

        try:
            out_path.write_text(
                json.dumps(anonymized, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("文件写入失败 [%s]: %s", out_name, exc)
            fail_count += 1
            continue

        success_count += 1
        logger.debug(
            "  %s -> %s (文本字符: %d -> %d)",
            raw_path.name, out_name, chars_before, chars_after,
        )

    logger.info("-" * 60)
    logger.info("脱敏完成: 成功 %d, 失败 %d, 共 %d", success_count, fail_count, len(raw_files))
    logger.info("文本总字符: 脱敏前 %d, 脱敏后 %d", total_chars_before, total_chars_after)

    # 4. 随机抽检 3 份文件
    logger.info("=" * 60)
    logger.info("开始脱敏校验（随机抽检 3 份）")
    logger.info("=" * 60)

    cleaned_files = sorted(CLEANED_DIR.glob("CASE_*.json"))
    sample_size = min(3, len(cleaned_files))
    sampled = random.sample(cleaned_files, sample_size)

    report_lines: list[str] = [
        f"脱敏校验报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"抽检文件数: {sample_size}",
        "",
    ]

    all_pass = True
    for fp in sampled:
        issues = _verify_anonymized_file(fp)
        status = "PASS" if not issues else "FAIL"
        if issues:
            all_pass = False
        report_lines.append(f"文件: {fp.name}  [{status}]")
        if issues:
            for issue in issues:
                report_lines.append(f"  - {issue}")
        else:
            report_lines.append("  未发现敏感信息残留")
        report_lines.append("")

    report_lines.append(f"校验结论: {'全部通过' if all_pass else '存在问题，需修复后重新脱敏'}")

    report_text = "\n".join(report_lines)
    report_path = CLEANED_DIR / f"anonymization_verify_{_timestamp}.txt"
    report_path.write_text(report_text, encoding="utf-8")

    logger.info(report_text)
    logger.info("校验报告已写入: %s", report_path)
    logger.info("日志文件: %s", LOG_FILE)

    if not all_pass:
        logger.error("校验未通过，请检查上述问题并修复后重新执行")
        sys.exit(1)
    else:
        logger.info("校验全部通过，脱敏流程完成")


if __name__ == "__main__":
    run()
