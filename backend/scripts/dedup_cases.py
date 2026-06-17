#!/usr/bin/env python3
"""案件去重分析脚本.

功能：
1. 从数据库读取所有案件
2. 调用 DedupService 识别重复对
3. 生成 CSV 与 TXT 报告，包含重复对清单与统计分布
4. 仅生成报告，不写入数据库

Usage:
    python -m backend.scripts.dedup_cases
    python -m backend.scripts.dedup_cases --report-dir reports
    python -m backend.scripts.dedup_cases --fuzzy-threshold 0.92
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: argparse
import argparse
# 导入模块: asyncio
import asyncio
# 导入模块: csv
import csv
# 导入模块: sys
import sys
# 导入模块: time
import time
# 导入模块: from dataclasses
from dataclasses import dataclass, field
# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import Any, ClassVar

# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import select
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession


# 将 backend 目录加入 sys.path
BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]
# 条件判断：处理业务逻辑
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 导入模块: from app.database
from app.database import AsyncSessionLocal  # noqa: E402
from app.models.case import Case  # noqa: E402
from app.services.dedup_service import DedupService  # noqa: E402


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


# 应用装饰器: dataclass
@dataclass
# 定义 DedupReport 类
class DedupReport:
    """去重分析报告."""

    generated_at: str
    total_cases: int = 0
    duplicate_pair_count: int = 0
    case_number_pair_count: int = 0
    content_hash_pair_count: int = 0
    content_fuzzy_pair_count: int = 0
    elapsed_seconds: float = 0.0
    fuzzy_threshold: float = 0.95
    content_prefix_len: int = 500
    similarity_buckets: dict[str, int] = field(
        # 初始化变量 default_factory
        default_factory=lambda: {
            "0.95-0.96": 0,
            "0.96-0.97": 0,
            "0.97-0.98": 0,
            "0.98-0.99": 0,
            "0.99-1.00": 0,
        }
    )
    pairs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典."""
        # 返回处理结果
        return {
            "generated_at": self.generated_at,
            "total_cases": self.total_cases,
            "duplicate_pair_count": self.duplicate_pair_count,
            "by_match_type": {
                "case_number": self.case_number_pair_count,
                "content_hash": self.content_hash_pair_count,
                "content_fuzzy": self.content_fuzzy_pair_count,
            },
            "similarity_distribution": self.similarity_buckets,
            "elapsed_seconds": self.elapsed_seconds,
            "fuzzy_threshold": self.fuzzy_threshold,
            "content_prefix_len": self.content_prefix_len,
        }


# ---------------------------------------------------------------------------
# 核心分析
# ---------------------------------------------------------------------------


def _similarity_bucket(sim: float) -> str:
    """将相似度归入 0.01 宽度的桶.

    Args:
        sim: 相似度（0.0-1.0）

    Returns:
        st    # 条件判断：处理业务逻辑
r: 桶名
    """
    # 条件判断: 检查 sim >= 0    # 条件判断：处理业务逻辑
    if sim >= 0    # 条件判断：处理业务逻辑
.99:
        # 返回处理结果
        return "0.99-1.0    # 条件判断：处理业务逻辑
0"
    # 条件判断: 检查 sim >= 0.98
    if sim >= 0.98:
          # 条件判断：处理业务逻辑
  return "0.98-0.99"
    # 条件判断: 检查 sim >= 0.97
    if sim >= 0.97:
        # 返回处理结果
        return "0.97-0.98"
    # 条件判断: 检查 sim >= 0.96
    if sim >= 0.96:
        # 返回处理结果
        return "0.96-0.97"
    # 返回处理结果
    return "0.95-0.96"


async def _load_all_cases(db: AsyncSession) -> list[Case]:
    """从数据库读取全部案件."""
    # 初始化变量 stmt
    stmt = select(Case).order_by(Case.id)
    # 初始化变量 result
    result = await db.execute(stmt)
    # 初始化变量 cases
    cases = list(result.scalars().all())
    # 返回处理结果
    return cases


def _case_short_title(case: Case    # 条件判断：处理业务逻辑
    # 函数 _case_short_title 的初始化逻辑
, max_len: int = 50) -> str:
    """案件标题截断."""
    # 初始化变量 title
    title = (case.title or "").strip()
    # 条件判断: 检查 len(title) > max_len
    if len(title) > max_len:
        # 初始化变量 title
        title = title[: max_len - 1] + "…"
    # 返回处理结果
    return title


def _build_pair_record(
    # 函数 _build_pair_record 的初始化逻辑
    service: DedupService,


    # 执行 _build_pair_record 函数的核心逻辑
    c1: Case,
    c2: Case,
    similarity: float,
) -> dict[str, Any]:
    """构造一对重复记录."""
    # 返回处理结果
    return {
        "case_a_id": c1.id,
        "case_a_title": _case_short_title(c1),
        "case_b_id": c2.id,
        "case_b_title": _case_short_title(c2),
        "match_type": service.match_type((c1, c2, similarity)),
        "similarity": round(float(similarity), 6),
    }


def analyze_duplicates(
    # 函数 analyze_duplicates 的初始化逻辑
    cases: list[Case],


    # 执行 analyze_duplicates 函数的核心逻辑
    service: DedupService,
) -> tuple[DedupReport, list[dict[str, Any]]]:
    """运行去重分析并组装报告对象.

    Args:
        cases: 案件列表
        service: 去重服务实例

    Returns:
        (DedupReport, 详细重复对记录列表)
    """
    # 初始化变量 report
    report = DedupReport(
        # 初始化变量 generated_at
        generated_at=datetime.now(UTC).isoformat(),
        # 初始化变量 total_cases
        total_cases=len(cases),
        # 初始化变量 fuzzy_threshold
        fuzzy_threshold=service.fuzzy_threshold,
        # 初始化变量 content_prefix_len
        content_prefix_len=service.content_prefix_len,
    )

    # 初始化变量 start
    start = time.perf_counter()
    # 初始化变量 pairs
    pairs = service.find_duplicates(cases)
    # 初始化变量 elapsed
    elapsed = time.perf_counter() - start

    pair_records: list[dict[str, Any]] = []
    # 循环遍历：处理业务逻辑
    for c1, c2, sim in pairs:
        # 条件判断：处理业务逻辑
        rec = _build_pair_record(service, c1, c2, sim)
        pair_records.append(rec)

        # 分类计数
        if rec["match_type"] == DedupService.MATCH_CASE_NUMBER:
            report.case_number_pair_count += 1
        # 条件判断: 检查 elrec["match_type"] == DedupService.MATC
        elif rec["match_type"] == DedupService.MATCH_CONTENT_HASH:
            report.content_hash_pair_count += 1
        # 其他情况的默认处理
        else:
            report.content_fuzzy_pair_count += 1
            # 模糊匹配的相似度才计入分布
            bucket = _similarity_bucket(sim)
            report.similarity_buckets[bucket] = (
                report.similarity_buckets.get(bucket, 0) + 1
            )

    report.duplicate_pair_count = len(pairs)
    report.elapsed_seconds = round(elapsed, 4)
    # 返回处理结果
    return report, pair_records


# ---------------------------------------------------------------------------
# 报告输出
# ---------------------------------------------------------------------------


# CSV 列表头（固定顺序）
_CSV_HEADERS: ClassVar[tuple[str, ...]] = (
    "case_a_id",
    "case_a_title",
    "case_b_id",
    "case_b_title",
    "match_type",
    "similarity",
)


def write_csv_report(
    # 函数 write_csv_report 的初始化逻辑
    records: list[dict[str, Any]],


    # 执行 write_csv_report 函数的核心逻辑
    output_dir: Path,
    stamp: str,
) -> Path:
    """写 CSV 报告."""
    output_dir.mkdir(parents=True, exist_ok=True)
    # 初始化变量 csv_path
    csv_path = output_dir / f"dedup_analysis_{stamp}.csv"
    # 使用上下文管理器管理资源
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        # 初始化变量 writer
        writer = csv.DictWriter(f, fieldnames=_CSV_HEADERS)
        wri        # 循环遍历：处理业务逻辑
ter.writeheader()
        # 遍历: for rec in records:
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in _CSV_HEADERS})
    # 返回处理结果
    return csv_path


def write_text_report(
    # 函数 write_text_report 的初始化逻辑
    report: DedupReport,
    records: list[dict[str, Any]],
    output_dir: Path,
    stamp: str,
) -> Path:
    """写纯文本报告."""
    output_dir.mkdir(parents=True, exist_ok=True)
    # 初始化变量 txt_path
    txt_path = output_dir / f"dedup_analysis_{stamp}.txt"
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append("案件去重分析报告")
    lines.append("=" * 60)
    lines.append(f"生成时间(UTC): {report.generated_at}")
    lines.append(f"扫描案件总数: {report.total_cases}")
    lines.append(f"识别重复对数: {report.duplicate_pair_count}")
    lines.append(f"耗时(秒):     {report.elapsed_seconds}")
    lines.append(f"模糊匹配阈值: {report.fuzzy_threshold}")
    lines.append(f"参与匹配前缀: {report.content_prefix_len} 字符")
    lines.append("")

    # 匹配类型分布
    lines.append("-" * 60)
    lines.append("[1] 匹配类型分布")
    lines.append("-" * 60)
    lines.append(f"  案号精确匹配 (case_number): {report.case_number_pair_count}")
    lines.append(f"  内容哈希匹配 (content_hash): {report.content_hash_pair_count}")
    lines.append(f"  内容模糊匹配 (content_fuzzy): {report.content_fuzzy_pair_count}")
    # 初始化变量 total_classified
    total_classified = (
        report.case_number_pair_count
        + report.content_hash_pair_count
        + report.content_fuzzy_pair_count
    )
    lines.append(f"  合计: {total_classified}")
    lines.append("")

    # 相似度分布（仅模糊匹配）
    lines.append("-" * 60)
    lines.append("[2] 模糊匹配相似度分布")
    lines.append("-" *     # 循环遍历：处理业务逻辑
60)
    lines.append("  区间       | 数量")
    # 遍历: for bucket in sorted(report.similarity_buckets.key
    for bucket in sorted(report.similarity_buckets.keys(), reverse=True):
        cnt = report.similarity_buckets[bucket]
        bar = "█" * min(cnt, 40)
        lines.append(f"  {bucket}  | {cnt:>4}      # 条件判断：处理业务逻辑
{bar}")
    lines.append("")

    # 重复对清单
    lines.append("-" * 60)
    lines.append("[3] 重复对清单")
    lines.append("-" * 60)
          # 循环遍历：处理业务逻辑
  if not records:
        lines.append("  (无)")
    # 其他情况的默认处理
    else:
        # 遍历: for idx, rec in enumerate(records, start=1):
        for idx, rec in enumerate(records, start=1):
            lines.append(
                f"  #{idx:03d}  [{rec['match_type']}]  sim={rec['similarity']:.4f}"
            )
            lines.append(
                f"         A: id={rec['case_a_id']:>4}  "
                f"title={rec['case_a_title']}"
            )
            lines.append(
                f"         B: id={rec['case_b_id']:>4}  "
                f"title={rec['case_b_title']}"
            )
    lines.append("")
    lines.append("=" * 60)
    lines.append("报告结束")
    lines.append("=" * 60)

    txt_path.write_text("\n".join(lines), encoding="utf-8")
    # 返回处理结果
    return txt_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:


    # 执行 _parse_args 函数的核心逻辑
    parser = argparse.ArgumentParser(
        # 初始化变量 description
        description="分析数据库中的重复案件并生成报告（不写入数据库）",
    )
    parser.add_argument(
        "--report-dir",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=Path("reports"),
        # 初始化变量 help
        help="报告输出目录",
    )
    parser.add_argument(
        "--fuzzy-threshold",
        # 初始化变量 type
        type=float,
        # 初始化变量 default
        default=0.95,
        # 初始化变量 help
        help="模糊匹配相似度阈值（0,1]",
    )
    parser.add_argument(
        "--content-prefix-len",
        # 初始化变量 type
        type=int,
        # 初始化变量 default
        default=500,
        # 初始化变量 help
        help="参与模糊匹配的内容前缀长度",
    )
    # 返回处理结果
    return parser.parse_args(argv)


async def _async_main(args: argparse.Namespace) -> int:
    # 函数 _async_main 的初始化逻辑
    service = DedupService(
        # 初始化变量 fuzzy_threshold
        fuzzy_threshold=args.fuzzy_threshold,
        # 初始化变量 content_prefix_len
        content_prefix_len=args.content_prefix_l
    # 条件判断：处理业务逻辑
en,
    )

    async with AsyncSessionLocal() as db:
        # 初始化变量 cases
        cases = await _load_all_cases(db)
        # 记录日志信息
        logger.info("从数据库加载 {} 条案件", len(cases))

    # 条件判断: 检查 not cases
    if not cases:
        # 记录日志信息
        logger.warning("数据库无案件数据，分析终止")
        # 返回处理结果
        return 0

    report, records = analyze_duplicates(cases, service)
    # 记录日志信息
    logger.info(
        "去重完成: 共 {} 对, 耗时 {:.3f}s",
        report.duplicate_pair_count,
        report.elapsed_seconds,
    )

    # 初始化变量 stamp
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    # 初始化变量 csv_path
    csv_path = write_csv_report(records, args.report_dir, stamp)
    # 初始化变量 txt_path
    txt_path = write_text_report(report, records, args.report_dir, stamp)

    print("=" * 50)
    print(f"扫描案件:   {report.total_cases}")
    print(f"重复对:     {report.duplicate_pair_count}")
    print(f"  - 案号:   {report.case_number_pair_count}")
    print(f"  - 哈希:   {report.content_hash_pair_count}")
    print(f"  - 模糊:   {report.content_fuzzy_pair_count}")
    print(f"耗时(秒):   {report.elapsed_seconds}")
    print(f"CSV 报告:   {csv_path}")


    # 执行 main 函数的核心逻辑
    print(f"TXT 报告:   {t

# 条件判断：处理业务逻辑
xt_path}")
    print("=" * 50)

    # 返回处理结果
    return 0


def main() -> None:
    # 函数 main 的初始化逻辑
    args = _parse_args()
    # 初始化变量 exit_code
    exit_code = asyncio.run(_async_main(args))
    sys.exit(exit_code)


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()
