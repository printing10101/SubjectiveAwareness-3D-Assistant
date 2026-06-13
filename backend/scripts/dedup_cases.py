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

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# 将 backend 目录加入 sys.path
BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.case import Case  # noqa: E402
from app.services.dedup_service import DedupService  # noqa: E402


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
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
        str: 桶名
    """
    if sim >= 0.99:
        return "0.99-1.00"
    if sim >= 0.98:
        return "0.98-0.99"
    if sim >= 0.97:
        return "0.97-0.98"
    if sim >= 0.96:
        return "0.96-0.97"
    return "0.95-0.96"


async def _load_all_cases(db: AsyncSession) -> list[Case]:
    """从数据库读取全部案件."""
    stmt = select(Case).order_by(Case.id)
    result = await db.execute(stmt)
    cases = list(result.scalars().all())
    return cases


def _case_short_title(case: Case, max_len: int = 50) -> str:
    """案件标题截断."""
    title = (case.title or "").strip()
    if len(title) > max_len:
        title = title[: max_len - 1] + "…"
    return title


def _build_pair_record(
    service: DedupService,
    c1: Case,
    c2: Case,
    similarity: float,
) -> dict[str, Any]:
    """构造一对重复记录."""
    return {
        "case_a_id": c1.id,
        "case_a_title": _case_short_title(c1),
        "case_b_id": c2.id,
        "case_b_title": _case_short_title(c2),
        "match_type": service.match_type((c1, c2, similarity)),
        "similarity": round(float(similarity), 6),
    }


def analyze_duplicates(
    cases: list[Case],
    service: DedupService,
) -> tuple[DedupReport, list[dict[str, Any]]]:
    """运行去重分析并组装报告对象.

    Args:
        cases: 案件列表
        service: 去重服务实例

    Returns:
        (DedupReport, 详细重复对记录列表)
    """
    report = DedupReport(
        generated_at=datetime.now(UTC).isoformat(),
        total_cases=len(cases),
        fuzzy_threshold=service.fuzzy_threshold,
        content_prefix_len=service.content_prefix_len,
    )

    start = time.perf_counter()
    pairs = service.find_duplicates(cases)
    elapsed = time.perf_counter() - start

    pair_records: list[dict[str, Any]] = []
    for c1, c2, sim in pairs:
        rec = _build_pair_record(service, c1, c2, sim)
        pair_records.append(rec)

        # 分类计数
        if rec["match_type"] == DedupService.MATCH_CASE_NUMBER:
            report.case_number_pair_count += 1
        elif rec["match_type"] == DedupService.MATCH_CONTENT_HASH:
            report.content_hash_pair_count += 1
        else:
            report.content_fuzzy_pair_count += 1
            # 模糊匹配的相似度才计入分布
            bucket = _similarity_bucket(sim)
            report.similarity_buckets[bucket] = (
                report.similarity_buckets.get(bucket, 0) + 1
            )

    report.duplicate_pair_count = len(pairs)
    report.elapsed_seconds = round(elapsed, 4)
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
    records: list[dict[str, Any]],
    output_dir: Path,
    stamp: str,
) -> Path:
    """写 CSV 报告."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"dedup_analysis_{stamp}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_HEADERS)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in _CSV_HEADERS})
    return csv_path


def write_text_report(
    report: DedupReport,
    records: list[dict[str, Any]],
    output_dir: Path,
    stamp: str,
) -> Path:
    """写纯文本报告."""
    output_dir.mkdir(parents=True, exist_ok=True)
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
    lines.append("-" * 60)
    lines.append("  区间       | 数量")
    for bucket in sorted(report.similarity_buckets.keys(), reverse=True):
        cnt = report.similarity_buckets[bucket]
        bar = "█" * min(cnt, 40)
        lines.append(f"  {bucket}  | {cnt:>4}  {bar}")
    lines.append("")

    # 重复对清单
    lines.append("-" * 60)
    lines.append("[3] 重复对清单")
    lines.append("-" * 60)
    if not records:
        lines.append("  (无)")
    else:
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
    return txt_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="分析数据库中的重复案件并生成报告（不写入数据库）",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("reports"),
        help="报告输出目录",
    )
    parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=0.95,
        help="模糊匹配相似度阈值（0,1]",
    )
    parser.add_argument(
        "--content-prefix-len",
        type=int,
        default=500,
        help="参与模糊匹配的内容前缀长度",
    )
    return parser.parse_args(argv)


async def _async_main(args: argparse.Namespace) -> int:
    service = DedupService(
        fuzzy_threshold=args.fuzzy_threshold,
        content_prefix_len=args.content_prefix_len,
    )

    async with AsyncSessionLocal() as db:
        cases = await _load_all_cases(db)
        logger.info("从数据库加载 {} 条案件", len(cases))

    if not cases:
        logger.warning("数据库无案件数据，分析终止")
        return 0

    report, records = analyze_duplicates(cases, service)
    logger.info(
        "去重完成: 共 {} 对, 耗时 {:.3f}s",
        report.duplicate_pair_count,
        report.elapsed_seconds,
    )

    stamp = datetime.now(UTC).strftime("%Y%m%d")
    csv_path = write_csv_report(records, args.report_dir, stamp)
    txt_path = write_text_report(report, records, args.report_dir, stamp)

    print("=" * 50)
    print(f"扫描案件:   {report.total_cases}")
    print(f"重复对:     {report.duplicate_pair_count}")
    print(f"  - 案号:   {report.case_number_pair_count}")
    print(f"  - 哈希:   {report.content_hash_pair_count}")
    print(f"  - 模糊:   {report.content_fuzzy_pair_count}")
    print(f"耗时(秒):   {report.elapsed_seconds}")
    print(f"CSV 报告:   {csv_path}")
    print(f"TXT 报告:   {txt_path}")
    print("=" * 50)

    return 0


def main() -> None:
    args = _parse_args()
    exit_code = asyncio.run(_async_main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
