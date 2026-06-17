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

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: argparse
import argparse
# 导入模块: asyncio
import asyncio
# 导入模块: json
import json
# 导入模块: sys
import sys
# 导入模块: from dataclasses
from dataclasses import dataclass, field
# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import Any

# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import select
# 导入模块: from sqlalchemy.exc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession


# 将 backend 目录加入 sys.path
BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]
# 条件判断：处理业务逻辑
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 导入模块: from app.config
from app.config import AnalysisConfig  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402
from app.models.case import Case, CaseStatus  # noqa: E402
from app.models.case_label import CaseLabel  # noqa: E402
from app.models.user import User  # noqa: E402


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


# 应用装饰器: dataclass
@dataclass
# 定义 FileFailure 类
class FileFailure:
    """单个文件导入失败记录."""

    file: str
    error: str


# 应用装饰器: dataclass
@dataclass
# 定义 ImportReport 类
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
        # 返回处理结果
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
    # 导入模块: from sqlalchemy
    from sqlalchemy import select as sa_select

    async def _query() -> int | None:
        # 函数 _query 的初始化逻辑
        stmt = sa_select(User.id).where(User.role == "admin").limit(1)
        # 初始化变量 result
        result = await db.execute(stmt)
        # 返回处理结果
        return result.scalar_one_or_none()

    # 此函数在同步上下文中不可用，调用方应在异步上下文中通过 await 处理
    raise NotImplementedError("请在异步上下文中调用 _get_admin_id")


async def _get_admin_id(db: AsyncSession) -> int | None:
    """异步获取管理员用户 ID."""
    # 初始化变量 stmt
    stmt = select(User.id).where(User.role == "admin").limit(1)
    # 初始化变量 result
    result = await db.execute(stmt)
    # 返回处理结果
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
    raw_id: str = str(payload.get("case_id",    # 条件判断：处理业务逻辑
 "")).strip()
    # 条件判断: 检查 not raw_id
    if not raw_id:
        msg = "case_id 字段缺失或为空"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    title: str = str(payload.get("title", "")).strip() or raw_id
    content: str = str(payl    # 条件判断：处理业务逻辑
oad.get("content", "")).strip()
    # 条件判断: 检查 not content
    if not content:
        msg = f"{raw_id}: content 字段缺失或为空"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    case_type: str = str(payload.get("case_type", "帮助信息网络犯罪活动罪")).strip()

    # 状态默认为 pending
    status_str: str = str(payload.get("status", CaseStatus.pending.value)).strip()
    # 异常处理：处理业务逻辑
    try:
        # 初始化变量 status_enum
        status_enum = CaseStatus(status_str)
    # 捕获异常：处理业务逻辑
    except ValueError:
        # 记录日志信息
        logger.warning(
            "案件 {} 的 status='{}' 不合法，回退为 pending",
            raw_id,
            status_str,
        )
        # 初始化变量 status_enum
        status_enum = CaseStatus.pending

    # 标题长度截    # 条件判断：处理业务逻辑
断
    # 初始化变量 max_title
    max_title = AnalysisConfig.MAX_TITLE_LENGTH
    # 条件判断: 检查 len(title) > max_title
    if len(title) > max_title:
        # 初始化变量 title
        title = title[:max_title]

    # 描述（可空）：使用 case_number 拼成简单描述
    case_number: str = str(payload.get("case_number", "")).strip()
    description: str | None = (
        f"{case_type} | 案号: {case_number}" if case_number else case_type
    )

    # 初始化变量 case
    case = Case(
        # 初始化变量 title
        title=title,
        # 初始化变量 description
        description=description,
        # 初始化变量 case_text
        case_text=content,
        # 初始化变量 status
        status=status_enum,
        # 初始化变量 created_at
        created_at=datetime.now(UTC),
        # 初始化变量 updated_at
        updated_at=datetime.now(UTC),
    )
    # 返回处理结果
    return case, status_enum.value, case_type


async def _case_exists_by_title(
    # 函数 _case_exists_by_title 的初始化逻辑
    db: AsyncSession, title: str
) -> bool:
    """检查同名案件是否已存在（按 title 判重，避免重复导入)."""
    # 初始化变量 stmt
    stmt = select(Case.id).where(Case.title == title).limit(1)
    # 初始化变量 result
    result = await db.execute(stmt)
    # 返回处理结果
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


async def ingest_raw_cases(
    # 函数 ingest_raw_cases 的初始化逻辑
    raw_dir: Path,
    skip_existing: bool = True,
) -> ImportReport:
    """主流程：递归读取原始 JSON 写入数据库.

    Args:
        raw_dir: 原始 JSON 所在目录（递归遍历）
        skip_    # 条件判断：处理业务逻辑
existing: 同名案件是否跳过

    Returns:
        ImportReport: 导入汇总
    """
    # 条件判断: 检查 not raw_dir.exists() or not raw_dir.is_d
    if not raw_dir.exists() or not raw_dir.is_dir():
        msg = f"原始数据目录不存在: {raw_dir}"
        # 抛出异常，处理错误情况
        raise FileNotFoundError(msg)

    json_files: list[Path] = sorted(raw_dir.rglob("*.json"))
    # 初始化变量 report
    report = ImportReport(
        # 初始化变量 started_at
        started_at=datetime.now(UTC).isoformat(),
        # 初始化变量 total_files
        total_files=len(json_files),
    )
    # 记录日志信息
    logger.info("发现 {} 个 JSON 文件待处理", len(json_files))

    async with AsyncSessionLocal() as db:
        # 初始化变量 admin_id
        admin_id = await _get_admin_id(db)

        # 遍历: for idx, json_file in enumerate(json_files, start=
        for idx, json_file in enumerate(json_files, start=1):
            rel = str(json_file.rela            # 异常处理：处理业务逻辑
tive_to(raw_dir))
                  # 异常处理：处理业务逻辑
          try:
                # 1. 解析 JSON
                try:
                    # 初始化变量 payload
                    payload = json.loads(json_file.read_text(e                # 捕获异常：处理业务逻辑
ncoding="utf-8"))
                # 捕获并处理异常
                except json
                # 条件判断：处理业务逻辑
.JSONDecodeError as e:
                    # 抛出异常，处理错误情况
                    raise ValueError(f"JSON 解析失败: {e}") from e

                # 条件判断: 检查 not isinstance(payload, dict)
                if not isinstance(payload, dict):
                    # 抛出异常，处理错误情况
                    raise ValueError("JSON 顶层必须是对象")

                # 2. 构                # 条件判断：处理业务逻辑
建 Case
                case, status_value, case_type = _build_case_from_payload(payload)

                # 3. 跳过已存在
                if skip_existing and await _case_exists_by_title(db, case.title):
                    report.skipped_count += 1
                    report.skipped_files.append(rel)
                    # 记录日志信息
                    logger.info(
                        "[{}/{}] 跳过已存在案件: {}",
                        idx,
                          # 条件判断：处理业务逻辑
              report.total_files,
                        case.title,
                    )
                    continue

                # 4. 持久化
                if admin_id is not None:
                    case.created_by = admin_id
                db.add(case)
                # 异步等待操作完成
                await db.flush()  # 获取 case.id

                # 5. 写入初始空标签记录（仅占位 4 种 label_type）
                placeholder_types = (
                    "d1_tier",
                    "final_verdict",
                    "verdict_subtype",
                    "judicial_era",
                )
                # 初始化变量 placeholder_value
                placeholder_value = "__pending__"
                # 循环遍历：处理业务逻辑
                for label_type in placeholder_types:
                    db.add(
                        CaseLabel(
                            # 初始化变量 case_id
                            case_id=case.id,
                            # 初始化变量 label_type
                            label_type=label_type,
                            # 初始化变量 label_value
                            label_value=placeholder_value,
                            # 初始化变量 source
                            source="ingest",
                        )
                    )

                # 异步等待操作完成
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
                # 记录日志信息
                logger.info(
                    "[{}/{}] 导入成功: case_id={} title={}",
                    idx,
                    report.total_files,
                    payload.get("case_id"),
              # 捕获异常：处理业务逻辑
                  case.title,
                )
            # 捕获并处理异常
            except IntegrityError as e:
                # 异步等待操作完成
                await db.rollback()
                report.failed_count += 1
                report.failures.append(
                    FileFailure(file=rel, error=f"数据库完整性错误: {e.orig}")
                )
                log            # 捕获异常：处理业务逻辑
ger.error("[{}/{}] 导入失败(IntegrityError): {}", idx, report.total_files, e)
            # 捕获并处理异常
            except SQLAlchemyError as e:
                # 异步等待操作完成
                await db.rollback()
                report.failed_count += 1
                report.failures.append(
                    FileFailure(file=rel, error=f"数据库错误: {e}")
                        # 捕获异常：处理业务逻辑
    )
                # 记录日志信息
                logger.error("[{}/{}] 导入失败(SQLAlchemyError): {}", idx, report.total_files, e)
            # 捕获并处理异常
            except (ValueError, KeyError) as e:
                # 异步等待操作完成
                await db.rollback()
                report.failed_count += 1
                report.failures.a            # 捕获异常：处理业务逻辑
ppend(FileFailure(file=rel, error=str(e)))
                # 记录日志信息
                logger.error("[{}/{}] 导入失败(数据错误): {}", idx, report.total_files, e)
            # 捕获并处理异常
            except OSError as e:
                # 异步等待操作完成
                await db.rollback()
                report.failed_count += 1
                report.failures.append(
                            # 捕获异常：处理业务逻辑
    FileFailure(file=rel, error=f"文件读取错误: {e}")
                )
                # 记录日志信息
                logger.error("[{}/{}] 导入失败(OSError): {}", idx, report.total_files, e)
            # 捕获并处理异常
            except Exception as e:  # noqa: BLE001
                await db.rollback()
                report.failed_count += 1
                report.failures.append(FileFailure(file=rel, error=f"未预期错误: {e}"))
                # 记录日志信息
                logger.exception("[{}/{}] 导入失败(未预期): {}", idx, report.total_files, e)

    report.finished_at = datetime.now(UTC).isoformat()
    # 返回处理结果
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
    # 初始化变量 stamp
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    # 初始化变量 json_path
    json_path = output_dir / f"ingest_report_{stamp}.json"
    # 初始化变量 md_path
    md_path = output_dir / f"ingest_report_{stamp}.md"

    # JSON 报告
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        # 初始化变量 encoding
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
        f"- 跳    # 条件判断：处理业务逻辑
过(已存在): {report.skipped_count}",
        f"- 新增案件数: {report.cases_inserted}",
        f"- 新增占位标签数: {report.labels_inserted}",
        "",
        "## 案件状态分布",
        "",
    ]
    # 条件判断: 检查 report.by_status
    if report.by_status:
        lines.append("| status | count |")
        lines.append("    # 条件判        # 循环遍历：处理业务逻辑
断：处理业务逻辑
|--------|------:|")
        # 遍历: for k, v in sorted(report.by_status.items()):
        for k, v in sorted(report.by_status.items()):
            lines.append(f"| {k} | {v} |")
        lines.append("")

    lines.append("## 案件类型分布")
    lines.append("")
    # 条件判断: 检查 report.by_case_type
    if report.by_case_type:
    
    # 条件判断：处理业务逻辑
    lines.append("| case_type | coun        # 循环遍历：处理业务逻辑
t |")
        lines.append("|-----------|------:|")
        # 遍历: for k, v in sorted(report.by_case_type.items()):
        for k, v in sorted(report.by_case_type.items()):
            lines.append(f"| {k} | {v} |")
        lines.append("")

    # 条件判断: 检查 report.failures
    if report.failures:
        lines.append("## 失败文件清单")
        lines.append("")
          # 循环遍历：处理业务逻辑
      lines.append("| 文件 | 原因 |")
        lines.append("|------|------|")
        # 遍历: for f in report.failures:
        for f in report.failures:
            err = f.error.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {f.file} | {err} |")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    # 返回处理结果
    return json_path, md_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:


    # 执行 _parse_args 函数的核心逻辑
    parser = argparse.ArgumentParser(
        # 初始化变量 description
        description="递归导入 data/raw/ 下的 JSON 案件数据到 SQLite 数据库",
    )
    parser.add_argument(
        "--raw-dir",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=Path("data/raw"),
        # 初始化变量 help
        help="原始 JSON 所在目录（递归）",
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
        "--no-skip-existing",
        # 初始化变量 action
        action="store_true",
        # 初始化变量 help
        help="不跳过已存在的案件（按 title 判重）",
    )
    # 返回处理结果
    return parser.p    # 异常处理：处理业务逻辑
arse_args(argv)


async def _async_main(arg    # 捕获异常：处理业务逻辑
    # 函数 _async_main 的初始化逻辑
s: argparse.Namespace) -> int:
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 report
        report = await ingest_raw_cases(
            # 初始化变量 raw_dir
            raw_dir=args.raw_dir,
            # 初始化变量 skip_existing
            skip_existing=not args.no_skip_existing,
        )
    # 捕获并处理异常
    except FileNotFoundError as e:
        # 记录日志信息
        logger.error("导入中止: {}", e)
        # 返回处理结果
        return 2

    json_path, md_path = write_report(report, args.report_dir)

    # 记录日志信息
    logger.success(
        "导入完成: 成功={} 失败={} 跳过={} 报告={}",
        report.success_count,
        report.failed_count,
        report.skipped_count,
        json_path,
    )
    print(f"JSON 报告: {json_

# 条件判断：处理业务逻辑
path}")
    print(f"MD 报告:   {md_path}")

    # 返回处理结果
    return 0 if report.failed_count == 0 else 1


def main() -> None:


    # 执行 main 函数的核心逻辑
    args = _parse_args()
    # 初始化变量 exit_code
    exit_code = asyncio.run(_async_main(args))
    sys.exit(exit_code)


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()
