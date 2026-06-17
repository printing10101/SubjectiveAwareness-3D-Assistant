#!/usr/bin/env python3
"""真实判决书批量入库脚本.

功能：
1. 批量读取 data/real_judgments/ 目录下的 25 个 GZ 系列判决书文件
2. 使用 RealJudgmentLoader 解析并标准化数据
3. 将数据路由至 cases 数据库表
4. 为每条记录设置 source="real_gz2023" 和 judgment_no 字段
5. 实现数据去重机制（按 judgment_no 判重）
6. 生成入库报告

Usage:
    python -m backend.scripts.ingest_real_judgments
    python -m backend.scripts.ingest_real_judgments --no-skip-existing
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
from app.services.real_judgment_loader import RealJudgmentLoader  # noqa: E402


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


async def _get_admin_id(db: AsyncSession) -> int | None:
    """异步获取管理员用户 ID."""
    # 初始化变量 stmt
    stmt = select(User.id).where(User.role == "admin").limit(1)
    # 初始化变量 result
    result = await db.execute(stmt)
    # 返回处理结果
    return result.scalar_one_or_none()


async def _case_exists_by_judgment_no(
    # 函数 _case_exists_by_judgment_no 的初始化逻辑
    db: AsyncSession, judgment_no: str
) -> bool:
    """检查判决书编号是否已存在（按 judgment_no 判重，避免重复导入)."""
    # 初始化变量 stmt
    stmt = select(Case.id).where(Case.judgment_no == judgment_no).limit(1)
    # 初始化变量 result
    result = await db.execute(stmt)
    # 返回处理结果
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


async def ingest_real_judgments(
    # 函数 ingest_real_judgments 的初始化逻辑
    judgments_dir: Path,
    skip_existing: bool = True,
) -> ImportReport:
    """主流程：批量导入真实判决书数据.

    Args:
        judgments_dir: 真实判决书 JSON 所在目录
        skip_existing: 已存在的判决书是否跳过

    Returns:
        ImportReport:    # 条件判断：处理业务逻辑
 导入汇总
    """
    # 条件判断: 检查 not judgments_dir.exists() or not judgme
    if not judgments_dir.exists() or not judgments_dir.is_dir():
        msg = f"判决书目录不存在: {judgments_dir}"
        # 抛出异常，处理错误情况
        raise FileNotFoundError(msg)

    # 初始化加载器
    loader = RealJudgmentLoader(judgments_dir)
    # 初始化变量 judgments
    judgments = loader.load_all_judgments()

    # 初始化变量 report
    report = ImportReport(
        # 初始化变量 started_at
        started_at=datetime.now(UTC).isoformat(),
        # 初始化变量 total_files
        total_files=len(judgments),
    )
    # 记录日志信息
    logger.info("准备导入 {} 个判决书", len(judgments))

    async with AsyncSessionLocal() as db:
        # 初始化变量 admin_id
        admin_id = await _get_admin_id(db)

        # 遍历: for idx, judgment in enumerate(judgments, start=1)
        for idx, judgment in enumerate(judgments, start=1):
            rel = f"{judgment.case_id}.json"
            # 异常处理：处理业务逻辑
            try:
                # 1. 构建 Case
                case, status_value, case_type = loader.build_case_from_judgment(
                    judgment, admin_id
                              # 条件判断：处理业务逻辑
  )

                # 2. 跳过已存在
                if skip_existing and await _case_exists_by_judgment_no(
                    db, judgment.case_id
                ):
                    report.skipped_count += 1
                    report.skipped_files.append(rel)
                    # 记录日志信息
                    logger.info(
                        "[{}/{}] 跳过已存在判决书: {}",
                        idx,
                        report.total_files,
                        judgment.case_id,
                    )
                    continue

                # 3. 持久化
                db.add(case)
                # 异步等待操作完成
                await db.flush()  # 获取 case.id

                # 4. 写入初始空标签记录（占位 4 种 label_type）
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
                            source="ingest_real",
                        )
                    )

                # 异步等待操作完成
                await db.commit()

                # 5. 累加统计
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
                    "[{}/{}] 导入成功: judgment_no={} title={}",
                    idx,
                    report.total_files,
                    judgment.case_id,
                    case.title,
                )
            # 捕获异常：处理业务逻辑
            except IntegrityError as e:
                # 异步等待操作完成
                await db.rollback()
                report.failed_count += 1
                report.failures.append(
                    FileFailure(file=rel, error=f"数据库完整性错误: {e.orig}")
                )
                # 记录日志信息
                logger.error(
                    "[{}/{}] 导入失败(IntegrityError): {}", idx, report.total_f            # 捕获异常：处理业务逻辑
iles, e
                )
            # 捕获并处理异常
            except SQLAlchemyError as e:
                # 异步等待操作完成
                await db.rollback()
                report.failed_count += 1
                report.failures.append(
                    FileFailure(file=rel, error=f"数据库错误: {e}")
                )
                # 记录日志信息
                logger.error(
                    "[{}/{}] 导入失败(SQLAlchemyError)            # 捕获异常：处理业务逻辑
: {}", idx, report.total_files, e
                )
            # 捕获并处理异常
            except (ValueError, KeyError) as e:
                # 异步等待操作完成
                await db.rollback()
                report.failed_count += 1
                report.failures.append(FileFailure(file=rel, error=str(e)))
                # 记录日志信息
                logger.error(
                         # 捕获异常：处理业务逻辑
       "[{}/{}] 导入失败(数据错误): {}", idx, report.total_files, e
                )
            # 捕获并处理异常
            except OSError as e:
                # 异步等待操作完成
                await db.rollback()
                report.failed_count += 1
                report.failures.append(
                    FileFailure(file=rel, error=f"文件读取错误: {e}")
                )
                logg            # 捕获异常：处理业务逻辑
er.error(
                    "[{}/{}] 导入失败(OSError): {}", idx, report.total_files, e
                )
            # 捕获并处理异常
            except Exception as e:  # noqa: BLE001
                await db.rollback()
                report.failed_count += 1
                report.failures.append(FileFailure(file=rel, error=f"未预期错误: {e}"))
                # 记录日志信息
                logger.exception(
                    "[{}/{}] 导入失败(未预期): {}", idx, report.total_files, e
                )

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
    json_path = output_dir / f"ingest_real_report_{stamp}.json"
    # 初始化变量 md_path
    md_path = output_dir / f"ingest_real_report_{stamp}.md"

    # JSON 报告
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        # 初始化变量 encoding
        encoding="utf-8",
    )

    # Markdown 报告
    lines: list[str] = [
        "# 真实判决书数据导入报告",
        "",
        f"- 开始时间: {report.started_at}",
        f"- 结束时间: {report.finished_at}",
        f"- 扫描文件总数: {report.total_files}",
        f"- 成功: {report.success_count}",
        f"- 失败: {report.failed_count}",
        f"- 跳过(已存在): {report.skipped_count}",
        f"- 新增案件数: {report.cases_inserted}",
        f"- 新增占位标签数: {report.labels_i    # 条件判断：处理业务逻辑
nserted}",
        "",
        "## 案件状态分布",
        "",
    ]
    # 条件判断: 检查 report.by_status
    if report.by_status:
        lines.append("| status | count |")
        lines        # 循环遍历：处理业务逻辑
.append("|--------|------:|")
        # 遍历: for k, v in sorted(report.by_status.items()):
        for k, v in sorted(report.by_status.items()):
            lines.append(f"| {k} | {v} |    # 条件判断：处理业务逻辑
")
        lines.append("")

    lines.append("## 案件类型分布")
    lines.append("")
    # 条件判断: 检查 report.by_case_type
    if report.by_case_type:
        lines.append("| case_type | coun        # 循环遍历：处理业务逻辑
t |")
        lines.append("|-----------|------:|")
        # 遍历: for k, v in sorted(
        for k, v in sorted(
    # 条件判断：处理业务逻辑
report.by_case_type.items()):
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
        description="批量导入 data/real_judgments/ 下的真实判决书数据到数据库",
    )
    parser.add_argument(
        "--judgments-dir",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=Path("data/real_judgments"),
        # 初始化变量 help
        help="真实判决书 JSON 所在目录",
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
        help="不跳过已存在的判决书（按 judgment_no 判重）",
    )
    # 返回处理结果
    return parser.parse_args(argv)


async def _async_main(args: ar    # 异常处理：处理业务逻辑
    # 函数 _async_main 的初始化逻辑
gparse.Namespace) -> int:
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 report
        report = await in    # 捕获异常：处理业务逻辑
gest_real_judgments(
            # 初始化变量 judgments_dir
            judgments_dir=args.judgments_dir,
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
    print(f"JSON 报告: {json_path}")
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
