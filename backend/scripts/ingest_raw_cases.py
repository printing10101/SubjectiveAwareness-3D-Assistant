#!/usr/bin/env python3
"""原始案件数据导入脚本.

功能：
1. 递归读取 data/raw/ 目录下所有 .json 文件
2. 解析 JSON 并写入 cases 表
3. 为每个导入案例在 case_labels 表中创建初始空记录（不创建任何具体标签值）
4. 错误处理：单文件失败不影响其他文件，记录失败原因
5. 生成导入报告（reports/ingest_report_YYYYMMDD_HHMMSS.{json,md}）

Usage:
    python -m backend.scripts.ingest_raw_cases
    python -m backend.scripts.ingest_raw_cases --raw-dir data/raw
    python -m backend.scripts.ingest_raw_cases --raw-dir data/raw --no-skip-existing
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


# 将 backend 目录加入 sys.path
BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import AnalysisConfig  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402
from app.models.case import Case, CaseStatus  # noqa: E402
from app.models.case_label import CaseLabel  # noqa: E402
from app.models.user import User  # noqa: E402


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class FileFailure:
    """单个文件导入失败记录."""

    file: str
    error: str


@dataclass
class ImportReport:
    """导入汇总报告."""

    started_at: str
    finished_at: str = ""
    total_files: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    cases_inserted: int = 0
    labels_inserted: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    by_case_type: dict[str, int] = field(default_factory=dict)
    failures: list[FileFailure] = field(default_factory=list)
    success_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典."""
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_files": self.total_files,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "cases_inserted": self.cases_inserted,
            "labels_inserted": self.labels_inserted,
            "by_status": self.by_status,
            "by_case_type": self.by_case_type,
            "failures": [
                {"file": f.file, "error": f.error} for f in self.failures
            ],
            "success_files": self.success_files,
            "skipped_files": self.skipped_files,
        }


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _default_admin_user_id(db: AsyncSession) -> int:
    """获取默认管理员用户的 ID.

    如果不存在管理员则使用 ID=1 作为创建者占位。
    """
    from sqlalchemy import select as sa_select

    async def _query() -> int | None:
        stmt = sa_select(User.id).where(User.role == "admin").limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # 此函数在同步上下文中不可用，调用方应在异步上下文中通过 await 处理
    raise NotImplementedError("请在异步上下文中调用 _get_admin_id")


async def _get_admin_id(db: AsyncSession) -> int | None:
    """异步获取管理员用户 ID."""
    stmt = select(User.id).where(User.role == "admin").limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _build_case_from_payload(payload: dict[str, Any]) -> tuple[Case, str, str]:
    """从 JSON 字典构造 Case ORM 对象.

    Args:
        payload: 原始 JSON 解析结果

    Returns:
        tuple: (Case 对象, 处理后状态枚举字符串, 处理后案件类型字符串)

    Raises:
        KeyError: 缺少必填字段
        ValueError: 字段值非法
    """
    raw_id: str = str(payload.get("case_id", "")).strip()
    if not raw_id:
        msg = "case_id 字段缺失或为空"
        raise ValueError(msg)

    title: str = str(payload.get("title", "")).strip() or raw_id
    content: str = str(payload.get("content", "")).strip()
    if not content:
        msg = f"{raw_id}: content 字段缺失或为空"
        raise ValueError(msg)

    case_type: str = str(payload.get("case_type", "帮助信息网络犯罪活动罪")).strip()

    # 状态默认为 pending
    status_str: str = str(payload.get("status", CaseStatus.pending.value)).strip()
    try:
        status_enum = CaseStatus(status_str)
    except ValueError:
        logger.warning(
            "案件 {} 的 status='{}' 不合法，回退为 pending",
            raw_id,
            status_str,
        )
        status_enum = CaseStatus.pending

    # 标题长度截断
    max_title = AnalysisConfig.MAX_TITLE_LENGTH
    if len(title) > max_title:
        title = title[:max_title]

    # 描述（可空）：使用 case_number 拼成简单描述
    case_number: str = str(payload.get("case_number", "")).strip()
    description: str | None = (
        f"{case_type} | 案号: {case_number}" if case_number else case_type
    )

    case = Case(
        title=title,
        description=description,
        case_text=content,
        status=status_enum,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    return case, status_enum.value, case_type


async def _case_exists_by_title(
    db: AsyncSession, title: str
) -> bool:
    """检查同名案件是否已存在（按 title 判重，避免重复导入)."""
    stmt = select(Case.id).where(Case.title == title).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


async def ingest_raw_cases(
    raw_dir: Path,
    skip_existing: bool = True,
) -> ImportReport:
    """主流程：递归读取原始 JSON 写入数据库.

    Args:
        raw_dir: 原始 JSON 所在目录（递归遍历）
        skip_existing: 同名案件是否跳过

    Returns:
        ImportReport: 导入汇总
    """
    if not raw_dir.exists() or not raw_dir.is_dir():
        msg = f"原始数据目录不存在: {raw_dir}"
        raise FileNotFoundError(msg)

    json_files: list[Path] = sorted(raw_dir.rglob("*.json"))
    report = ImportReport(
        started_at=datetime.now(UTC).isoformat(),
        total_files=len(json_files),
    )
    logger.info("发现 {} 个 JSON 文件待处理", len(json_files))

    async with AsyncSessionLocal() as db:
        admin_id = await _get_admin_id(db)

        for idx, json_file in enumerate(json_files, start=1):
            rel = str(json_file.relative_to(raw_dir))
            try:
                # 1. 解析 JSON
                try:
                    payload = json.loads(json_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError as e:
                    raise ValueError(f"JSON 解析失败: {e}") from e

                if not isinstance(payload, dict):
                    raise ValueError("JSON 顶层必须是对象")

                # 2. 构建 Case
                case, status_value, case_type = _build_case_from_payload(payload)

                # 3. 跳过已存在
                if skip_existing and await _case_exists_by_title(db, case.title):
                    report.skipped_count += 1
                    report.skipped_files.append(rel)
                    logger.info(
                        "[{}/{}] 跳过已存在案件: {}",
                        idx,
                        report.total_files,
                        case.title,
                    )
                    continue

                # 4. 持久化
                if admin_id is not None:
                    case.created_by = admin_id
                db.add(case)
                await db.flush()  # 获取 case.id

                # 5. 写入初始空标签记录（仅占位 4 种 label_type）
                placeholder_types = (
                    "d1_tier",
                    "final_verdict",
                    "verdict_subtype",
                    "judicial_era",
                )
                placeholder_value = "__pending__"
                for label_type in placeholder_types:
                    db.add(
                        CaseLabel(
                            case_id=case.id,
                            label_type=label_type,
                            label_value=placeholder_value,
                            source="ingest",
                        )
                    )

                await db.commit()

                # 6. 累加统计
                report.success_count += 1
                report.cases_inserted += 1
                report.labels_inserted += len(placeholder_types)
                report.success_files.append(rel)
                report.by_status[status_value] = (
                    report.by_status.get(status_value, 0) + 1
                )
                report.by_case_type[case_type] = (
                    report.by_case_type.get(case_type, 0) + 1
                )
                logger.info(
                    "[{}/{}] 导入成功: case_id={} title={}",
                    idx,
                    report.total_files,
                    payload.get("case_id"),
                    case.title,
                )
            except IntegrityError as e:
                await db.rollback()
                report.failed_count += 1
                report.failures.append(
                    FileFailure(file=rel, error=f"数据库完整性错误: {e.orig}")
                )
                logger.error("[{}/{}] 导入失败(IntegrityError): {}", idx, report.total_files, e)
            except SQLAlchemyError as e:
                await db.rollback()
                report.failed_count += 1
                report.failures.append(
                    FileFailure(file=rel, error=f"数据库错误: {e}")
                )
                logger.error("[{}/{}] 导入失败(SQLAlchemyError): {}", idx, report.total_files, e)
            except (ValueError, KeyError) as e:
                await db.rollback()
                report.failed_count += 1
                report.failures.append(FileFailure(file=rel, error=str(e)))
                logger.error("[{}/{}] 导入失败(数据错误): {}", idx, report.total_files, e)
            except OSError as e:
                await db.rollback()
                report.failed_count += 1
                report.failures.append(
                    FileFailure(file=rel, error=f"文件读取错误: {e}")
                )
                logger.error("[{}/{}] 导入失败(OSError): {}", idx, report.total_files, e)
            except Exception as e:  # noqa: BLE001
                await db.rollback()
                report.failed_count += 1
                report.failures.append(FileFailure(file=rel, error=f"未预期错误: {e}"))
                logger.exception("[{}/{}] 导入失败(未预期): {}", idx, report.total_files, e)

    report.finished_at = datetime.now(UTC).isoformat()
    return report


# ---------------------------------------------------------------------------
# 报告输出
# ---------------------------------------------------------------------------


def write_report(report: ImportReport, output_dir: Path) -> tuple[Path, Path]:
    """将报告写入磁盘.

    Args:
        report: 导入报告对象
        output_dir: 输出目录

    Returns:
        tuple: (json 报告路径, md 报告路径)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"ingest_report_{stamp}.json"
    md_path = output_dir / f"ingest_report_{stamp}.md"

    # JSON 报告
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Markdown 报告
    lines: list[str] = [
        "# 原始案件数据导入报告",
        "",
        f"- 开始时间: {report.started_at}",
        f"- 结束时间: {report.finished_at}",
        f"- 扫描文件总数: {report.total_files}",
        f"- 成功: {report.success_count}",
        f"- 失败: {report.failed_count}",
        f"- 跳过(已存在): {report.skipped_count}",
        f"- 新增案件数: {report.cases_inserted}",
        f"- 新增占位标签数: {report.labels_inserted}",
        "",
        "## 案件状态分布",
        "",
    ]
    if report.by_status:
        lines.append("| status | count |")
        lines.append("|--------|------:|")
        for k, v in sorted(report.by_status.items()):
            lines.append(f"| {k} | {v} |")
        lines.append("")

    lines.append("## 案件类型分布")
    lines.append("")
    if report.by_case_type:
        lines.append("| case_type | count |")
        lines.append("|-----------|------:|")
        for k, v in sorted(report.by_case_type.items()):
            lines.append(f"| {k} | {v} |")
        lines.append("")

    if report.failures:
        lines.append("## 失败文件清单")
        lines.append("")
        lines.append("| 文件 | 原因 |")
        lines.append("|------|------|")
        for f in report.failures:
            err = f.error.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {f.file} | {err} |")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="递归导入 data/raw/ 下的 JSON 案件数据到 SQLite 数据库",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="原始 JSON 所在目录（递归）",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("reports"),
        help="报告输出目录",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="不跳过已存在的案件（按 title 判重）",
    )
    return parser.parse_args(argv)


async def _async_main(args: argparse.Namespace) -> int:
    try:
        report = await ingest_raw_cases(
            raw_dir=args.raw_dir,
            skip_existing=not args.no_skip_existing,
        )
    except FileNotFoundError as e:
        logger.error("导入中止: {}", e)
        return 2

    json_path, md_path = write_report(report, args.report_dir)

    logger.success(
        "导入完成: 成功={} 失败={} 跳过={} 报告={}",
        report.success_count,
        report.failed_count,
        report.skipped_count,
        json_path,
    )
    print(f"JSON 报告: {json_path}")
    print(f"MD 报告:   {md_path}")

    return 0 if report.failed_count == 0 else 1


def main() -> None:
    args = _parse_args()
    exit_code = asyncio.run(_async_main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
