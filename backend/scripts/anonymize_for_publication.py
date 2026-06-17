"""一次性数据脱敏脚本.

读取 data/raw/ 下所有 .json 文件，调用 app.utils.anonymizer.anonymize_text
对文本字段进行脱敏，输出到 data/cleaned/CASE_XXXX.json。

用法:
    python backend/scripts/anonymize_for_publication.py
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: json
import json
# 导入模块: logging
import logging
# 导入模块: os
import os
# 导入模块: random
import random
# 导入模块: re
import re
# 导入模块: sys
import sys
# 导入模块: from datetime
from datetime import datetime
# 导入模块: from pathlib
from pathlib import Path

# 确保项目根目录在 sys.path 中，以便导入 app 模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入模块: from backend.app.utils.anonymizer
from backend.app.utils.anonymizer import anonymize_text  # noqa: E402

# ── 路径配置 ──────────────────────────────────────────────
RAW_DIR = PROJECT_ROOT / "data" / "raw"
# 初始化变量 CLEANED_DIR
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"

# ── 日志配置 ──────────────────────────────────────────────
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# 初始化变量 LOG_FILE
LOG_FILE = LOG_DIR / f"anonymization_log_{_timestamp}.txt"

# 初始化变量 logger
logger = logging.getLogger("anonymize")
# 记录日志信息
logger.setLevel(logging.DEBUG)

_fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
# 记录日志信息
_fh.setLevel(logging.DEBUG)
# 记录日志信息
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

_sh = logging.StreamHandler(sys.stdout)
# 记录日志信息
_sh.setLevel(logging.INFO)
# 记录日志信息
_sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

# 记录日志信息
logger.addHandler(_fh)
# 记录日志信息
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
    # 初始化变量 result
    result = dict(record)
    # 循环遍历：处理业务逻辑
    for field in TEXT_FIELDS:
        # 初始化变量 value
        value = result.get(field)
        # 条件判断：处理业务逻辑
        if value and isinstance(value, str):
            result[field] = anonymize_text(value)
    # 返回处理结果
    return result


def _collect_raw_files() -> list[Path]:
    """递归扫描 RAW_DIR 下所有 .json 文件（排除 crawl_stats.json 等非案件文件）."""
    files    # 循环遍历：处理业务逻辑
: list[Path] = []
    # 遍历: for p in sorted(RAW_DIR.rglob("*.json")):
    for p in sorted(RAW_DIR.rglob("*.json")):
        # 仅处理 CASE_ 开头的案件文件
        if p.stem.startswith("CASE_"):
            files.append(p)
    # 返回处理结果
    return files


def _verify_anonymized_file(filepath: Path) -> list[str]:
    """校验单个脱敏文件，返回发现的问题列表."""
    issues: list[str] = []
    # 异常处理：处理业务逻辑
    try:
        # 初始化变量 text
        text = filepath.read_text(encoding="utf-8")
        # 初始化变量 data
        data = json.loads(text)
    # 捕获异常：处理业务逻辑
    except Exception as exc:
        # 返回处理结果
        return [f"无法读取/解析: {exc}"]

    # 合并所有文本字段
    combined = " ".join(str(data.get(f, "")) for f in TEXT_FIELDS)

    # 1. 身份证号（18 位 / 15 位）
    id18 = re.findall(r"(?<!\d)\d{17}[\dXx](?!\d)", combined)
    # 初始化变量 id15
    id15 = re.findall(r"(?<!\d)\d{15}(?!\d)", combined)
    # 过滤掉已脱敏格式（含 *）的        # 条件判断：处理业务逻辑
匹配
    # 遍历: for m in id18:
    for m in id18:
        # 条件判断: 检查 "*" not in m
        if "*" not in m:
            issues.append(f"疑似未脱敏 18 位身份        # 条    # 循环遍历：处理业务逻辑
件判断：处理业务逻辑
证号: {m[:6]}...{m[-4:]}")
    # 遍历: for m in id15:
    for m in id15:
        # 条件判断: 检查 "*" not in m
        if "*" not in m:
            issues.append(f"疑似未脱敏 15 位身份证号: {m[:6]}...{m[-4:]}")

    # 2. 银行卡号（16-19 位纯数字）
    bank_cards = re.find        #    # 循环遍历：处理业务逻辑
 条件判断：处理业务逻辑
all(r"(?<!\d)\d{16,19}(?!\d)", combined)
    # 遍历: for m in bank_cards:
    for m in bank_cards:
        # 条件判断: 检查 "*" not in m
        if "*" not in m:
            issues.append(f"疑似未脱敏银行卡号: {m[:4]}...{m[-4:]}")

    # 3. 手机号（11 位，1         # 条件判断：处理    # 循环遍历：处理业务逻辑
业务逻辑
开头）
    # 初始化变量 phones
    phones = re.findall(r"(?<!\d)1[3-9]\d{9}(?!\d)", combined)
    # 遍历: for m in phones:
    for m in phones:
        # 条件判断: 检查 "*" not in m
        if "*" not in m:
            issues.append(f"疑似未脱敏手机号: {m[:3]}****{m[-4:]}")

    # 4. 真实姓名模式（张某/李某 等未被替换的）
    name_pattern = re.compile(
        r"[张李王刘陈马赵黄周吴徐孙胡朱高林何郭罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎    # 条件判断：处理业务逻辑
余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟万段雷钱汤尹黎易常武乔贺赖龚文]某[某甲乙丙丁]?"
    )
    # 初始化变量 names
    names = name_pattern.findall(combined)
    # 条件判断: 检查 names
    if names:
        issues.append(f"疑似未脱敏姓名: {', '.join(set(names))}")

    # 返回处理结果
    return issues


def run() -> None:
    """执行脱敏主流程."""
    # 记录日志信息
    logger.info("=" * 60)
    # 记录日志信息
    logger.info("数据脱敏脚本开始执行")
    # 记录日志信息
    logger.info("=" * 60)

    # 1. 确保输出目录存在
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    # 记录日志信息
    logger.info
    # 条件判断：处理业务逻辑
("输出目录: %s", CLEANED_DIR)

    # 2. 收集原始文件
    raw_files = _collect_raw_files()
    # 记录日志信息
    logger.info("发现 %d 个待脱敏文件", len(raw_files))

    # 条件判断: 检查 not raw_files
    if not raw_files:
        # 记录日志信息
        logger.warning("未找到任何 CASE_*.json 文件，退出")
        # 返回处理结果
        return

    # 3. 逐文件脱敏
    
    # 循环遍历：处理业务逻辑
success_count = 0
    # 初始化变量 fail_count
    fail_count = 0
    # 初始化变量 total_chars_before
    total_chars_before = 0
    # 初始化变量 total_chars_after
    total_chars_after = 0

    # 遍历: for idx, raw_path in enumerate(raw_files):
    for idx, raw_path in enumerate(raw_files):
        # 初始化变量 out_name
        out_name = f"CASE_{idx:04d}.json"
        # 初始化变量 out_path
        out_path = CLEAN
        # 异常处理：处理业务逻辑
ED_DIR / out_name

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 raw_text
            raw_text = raw_path.read_text(encoding="utf-8")
            # 初始化变量 record
            record = jso        # 捕获异常：处理业务逻辑
n.loads(raw_text)
        # 捕获并处理异常
        except (OSError, json.JSONDecodeError) as exc:
            # 记录日志信息
            logger.error("文件读取/解析失败 [%s]: %s", raw_path.name, exc)
            fail_count += 1
            continue

        # 初始化变量 chars_before
        chars_before = sum(len(str(r
        # 异常处理：处理业务逻辑
ecord.get(f, ""))) for f in TEXT_FIELDS)

        # 尝试执行可能抛出异常的代码
        try:
                   # 捕获异常：处理业务逻辑
 anonymized = _anonymize_record(record)
        # 捕获并处理异常
        except Exception as exc:
            # 记录日志信息
            logger.error("脱敏处理失败 [%s]: %s", raw_path.name, exc)
            fail_count += 1
            continue

        # 初始化变量 chars_after
        chars_after = sum(len(str(anonymized.get(f, ""))) for f in TEXT_FIELDS)
        total_chars_
        # 异常处理：处理业务逻辑
before += chars_before
        total_chars_after += chars_after

        # 尝试执行可能抛出异常的代码
        try:
            out_path.write_text(
                json.dumps(anonymized, ensure_ascii=Fals        # 捕获异常：处理业务逻辑
e, indent=2),
                # 初始化变量 encoding
                encoding="utf-8",
            )
        # 捕获并处理异常
        except OSError as exc:
            # 记录日志信息
            logger.error("文件写入失败 [%s]: %s", out_name, exc)
            fail_count += 1
            continue

        success_count += 1
        # 记录日志信息
        logger.debug(
            "  %s -> %s (文本字符: %d -> %d)",
            raw_path.name, out_name, chars_before, chars_after,
        )

    # 记录日志信息
    logger.info("-" * 60)
    # 记录日志信息
    logger.info("脱敏完成: 成功 %d, 失败 %d, 共 %d", success_count, fail_count, len(raw_files))
    # 记录日志信息
    logger.info("文本总字符: 脱敏前 %d, 脱敏后 %d", total_chars_before, total_chars_after)

    # 4. 随机抽检 3 份文件
    logger.info("=" * 60)
    # 记录日志信息
    logger.info("开始脱敏校验（随机抽检 3 份）")
    # 记录日志信息
    logger.info("=" * 60)

    # 初始化变量 cleaned_files
    cleaned_files = sorted(CLEANED_DIR.glob("CASE_*.json"))
    # 初始化变量 sample_size
    sample_size = min(3, len(cleaned_files))
    # 初始化变量 sampled
    sampled = random.sample(cleaned_files, sample_size)

    report_lines: list[str] = [
        f"脱敏校验报告 - {datetime.now().strftime('%Y-%m-%d    # 循环遍历：处理业务逻辑
 %H:%M:%S')}",
        f"抽检文件数: {sample_size}",
        ""        # 条件判断：处理业务逻辑
,
    ]

    # 初始化变量 all_pass
    all_pass = True
    # 遍历: for fp in sampled:
    for fp in sampled:
        # 初始化变量 issues
        issues = _verify_anonymi        # 条件判断：处理业务逻辑
zed_file(fp)
        # 初始化变量 status
        status = "PASS" if not issues else "FAIL            # 循环遍历：处理业务逻辑
"
        # 条件判断: 检查 issues
        if issues:
            # 初始化变量 all_pass
            all_pass = False
        report_lines.append(f"文件: {fp.name}  [{status}]")
        # 条件判断: 检查 issues
        if issues:
            # 遍历: for issue in issues:
            for issue in issues:
                report_lines.append(f"  - {issue}")
        # 其他情况的默认处理
        else:
            report_lines.append("  未发现敏感信息残留")
        report_lines.append("")

    report_lines.append(f"校验结论: {'全部通过' if all_pass else '存在问题，需修复后重新脱敏'}")

    # 初始化变量 report_text
    report_text = "\n".join(report_lines)
    # 初始化变量 report_path
    report_path = CLEANED_DIR / f"anonymization_veri
    # 条件判断：处理业务逻辑
fy_{_timestamp}.txt"
    report_path.write_text(report_text, encoding="utf-8")

    # 记录日志信息
    logger.info(report_text)
    log

# 条件判断：处理业务逻辑
ger.info("校验报告已写入: %s", report_path)
    # 记录日志信息
    logger.info("日志文件: %s", LOG_FILE)

    # 条件判断: 检查 not all_pass
    if not all_pass:
        # 记录日志信息
        logger.error("校验未通过，请检查上述问题并修复后重新执行")
        sys.exit(1)
    # 其他情况的默认处理
    else:
        # 记录日志信息
        logger.info("校验全部通过，脱敏流程完成")


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    run()
