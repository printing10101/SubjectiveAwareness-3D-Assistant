"""案例数据迁移脚本.

将 status 为 'completed' 的案件数据迁移至知识库（KnowledgeEntry），
支持批量处理、预览模式、事务管理、LLM 元数据提取和迁移报告生成。

运行方式:
    python scripts/migrate_cases_to_knowledge.py
    python scripts/migrate_cases_to_knowledge.py --batch-size 10
    python scripts/migrate_cases_to_knowledge.py --dry-run
    python scripts/migrate_cases_to_knowledge.py --log-level DEBUG
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_BACKEND_DIR = str(Path(__file__).resolve().parent.parent / "backend")
sys.path.insert(0, _BACKEND_DIR)

_old_cwd = os.getcwd()
os.chdir(_BACKEND_DIR)

from loguru import logger  # noqa: E402
from sqlalchemy import select, func  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.config import AnalysisConfig, settings  # noqa: E402
from app.database import AsyncSessionLocal, async_engine  # noqa: E402
from app.models.analysis import Analysis  # noqa: E402
from app.models.case import Case, CaseStatus  # noqa: E402
from app.models.knowledge_entry import (  # noqa: E402
    EntryStatus, KnowledgeEntry, SourceType,
)
from app.services.knowledge_import_service import (  # noqa: E402
    _associate_tags,
    _resolve_category,
)
from app.services.ollama_client import get_client  # noqa: E402
from app.utils.logger import setup_logging  # noqa: E402

_METADATA_EXTRACTION_PROMPT: str = """请从以下法律案件文本中提取结构化元数据，以JSON格式返回。

必须包含以下字段：
- title: 简洁准确的标题（不超过30字，反映案件核心内容）
- summary: 内容摘要（150-300字之间，准确概括案件事实和关键要点）
- suggested_tags: 建议标签列表（3-5个，用于分类和检索，如罪名、犯罪类型等法律相关标签）
- suggested_category: 建议分类，必须是以下之一：
  law（法律法规）、methodology（方法论）、case（案例）、other（其他）

质量要求：
- summary 必须控制在150-300字之间
- suggested_tags 必须包含3-5个标签
- 标签要具有检索价值，包含法律专业术语

只返回JSON，不要包含任何其他文字：

文本内容：
{text}"""

_DEFAULT_METADATA: dict[str, Any] = {
    "summary": "",
    "suggested_tags": ["案件"],
    "suggested_category": "case",
}

_REQUIRED_CONTENT_MIN_LENGTH: int = 10
_LLM_TIMEOUT_BASE: float = 60.0
_LLM_TIMEOUT_PER_CHAR: float = 0.01
_LLM_TIMEOUT_MAX: float = 300.0
_LLM_RETRY_MAX_ATTEMPTS: int = 2
_LLM_RETRY_DELAY_BASE: float = 1.0
_CONTENT_PREVIEW_CHARS: int = 8000


@dataclass
class CaseMigrationRecord:
    """单个案件迁移记录."""
    case_id: int
    case_title: str
    status: str
    entry_id: int | None = None
    error: str | None = None
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationReport:
    """迁移报告."""
    total_eligible: int = 0
    success_count: int = 0
    failure_count: int = 0
    skip_count: int = 0
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    records: list[CaseMigrationRecord] = field(default_factory=list)
    batch_size: int = 10
    dry_run: bool = False

    def generate_text_report(self) -> str:
        processed_count = (
            self.success_count + self.failure_count + self.skip_count
        )
        eligible = max(self.total_eligible, 1)
        lines: list[str] = [
            "=" * 70,
            "          案例数据迁移报告",
            "=" * 70,
            f"  开始时间: {self.start_time}",
            f"  结束时间: {self.end_time}",
            f"  总耗时: {self.duration_seconds:.2f} 秒",
            f"  运行模式: {'预览模式 (DRY-RUN)' if self.dry_run else '正式迁移'}",
            f"  每批数量: {self.batch_size}",
            "",
            "-" * 70,
            "  总体统计",
            "-" * 70,
            f"  符合条件的案件总数: {self.total_eligible}",
            f"  [成功] 成功迁移: {self.success_count}",
            f"  [失败] 失败数量: {self.failure_count}",
            f"  [跳过] 跳过数量: {self.skip_count}",
            f"处理完成率: "
            f"{processed_count / eligible * 100:.1f}%",
            f"  成功率: "
            f"{self.success_count / eligible * 100:.1f}%",
            "",
        ]

        if self.failure_count > 0:
            lines.extend(["-" * 70, "  失败案例详情", "-" * 70])
            for r in self.records:
                if r.status == "failed":
                    lines.append(f"  [案件ID: {r.case_id}]")
                    lines.append(f"     标题: {r.case_title}")
                    lines.append(f"     原因: {r.error}")
                    lines.append("")

        if self.skip_count > 0:
            lines.extend(["-" * 70, "  跳过案例详情", "-" * 70])
            for r in self.records:
                if r.status == "skipped":
                    lines.append(f"  [案件ID: {r.case_id}]")
                    lines.append(f"     标题: {r.case_title}")
                    lines.append(f"     原因: {r.error}")
                    lines.append("")

        lines.extend(["-" * 70, "  详细迁移日志", "-" * 70])
        for r in self.records:
            icon = (
                "[OK]" if r.status == "success"
                else ("[FAIL]" if r.status == "failed" else "[SKIP]")
            )
            entry_info = f", 知识条目ID: {r.entry_id}" if r.entry_id else ""
            lines.append(f"  {icon} 案件ID: {r.case_id}{entry_info}")
            lines.append(f"     标题: {r.case_title}")
            lines.append(f"     耗时: {r.duration_seconds:.2f}s")
            if r.error:
                lines.append(f"     状态: {r.status}, 错误: {r.error}")
            else:
                lines.append(f"     状态: {r.status}")
            lines.append("")

        lines.append("=" * 70)
        lines.append("报告结束")
        lines.append("=" * 70)
        return "\n".join(lines)

    def generate_json_report(self) -> dict[str, Any]:
        return {
            "report_metadata": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": self.duration_seconds,
                "dry_run": self.dry_run,
                "batch_size": self.batch_size,
            },
            "statistics": {
                "total_eligible": self.total_eligible,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "skip_count": self.skip_count,
                "completion_rate": round(
                    (self.success_count + self.failure_count + self.skip_count)
                    / max(self.total_eligible, 1) * 100, 1
                ),
                "success_rate": round(
                    self.success_count / max(self.total_eligible, 1) * 100, 1
                ),
            },
            "records": [
                {
                    "case_id": r.case_id,
                    "case_title": r.case_title,
                    "status": r.status,
                    "entry_id": r.entry_id,
                    "error": r.error,
                    "duration_seconds": round(r.duration_seconds, 2),
                }
                for r in self.records
            ],
        }


def _format_timestamp(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(UTC)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="案例数据迁移脚本 — 将 completed 状态的案件迁移至知识库",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="每批处理的案件数量（默认: 10）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：仅查询和统计，不实际写入数据库",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别（默认: INFO）",
    )
    return parser.parse_args()


async def count_eligible_cases(db: AsyncSession) -> int:
    """统计符合条件的案件数量."""
    result = await db.execute(
        select(func.count(Case.id)).where(Case.status == CaseStatus.completed)
    )
    return result.scalar_one()


async def fetch_completed_cases(
    db: AsyncSession,
    offset: int = 0,
    limit: int = 10,
) -> list[Case]:
    """分页查询 completed 状态的案件.

    Args:
        db: 数据库会话
        offset: 偏移量
        limit: 每页数量

    Returns:
        案件列表，按 id 升序排列
    """
    result = await db.execute(
        select(Case)
        .where(Case.status == CaseStatus.completed)
        .order_by(Case.id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def fetch_latest_analysis(
    db: AsyncSession, case_id: int
) -> Analysis | None:
    """查询指定案件的最新分析结果."""
    result = await db.execute(
        select(Analysis)
        .where(
            Analysis.case_id == case_id
        )
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def validate_case_data(case: Case) -> str | None:
    """验证案件数据完整性.

    Args:
        case: 案件实例

    Returns:
        如果数据有效返回 None，否则返回错误描述
    """
    if not case.title or not case.title.strip():
        return "案件标题为空"

    if not case.case_text or not case.case_text.strip():
        return "案件事实文本为空"

    if len(case.case_text.strip()) < _REQUIRED_CONTENT_MIN_LENGTH:
        return (
            f"案件事实文本长度不足（{len(case.case_text.strip())} "
            f"字符，最少需要 {_REQUIRED_CONTENT_MIN_LENGTH}）"
        )

    return None


def build_merged_content(case: Case, analysis: Analysis | None) -> str:
    """将案件事实与分析结果合并为知识条目正文.

    格式：案件事实在前，分析结果在后，使用明确分隔符。

    Args:
        case: 案件实例
        analysis: 分析结果实例（可选）

    Returns:
        合并后的完整正文
    """
    parts: list[str] = [case.case_text.strip()]

    if analysis and analysis.result_json:
        try:
            analysis_data = json.loads(analysis.result_json)
            analysis_text = json.dumps(
                analysis_data, ensure_ascii=False, indent=2
            )
            parts.append("\n\n--- 案件分析结果 ---\n")
            parts.append(analysis_text)
        except (json.JSONDecodeError, TypeError):
            parts.append("\n\n--- 案件分析结果 ---\n")
            parts.append(str(analysis.result_json))

    return "".join(parts)


async def extract_case_metadata_with_llm(content: str) -> dict[str, Any]:
    """调用 LLM 从案件内容中提取元数据（摘要和标签）.

    实现请求超时处理和重试机制。

    Args:
        content: 合并后的案件正文

    Returns:
        包含 title/summary/suggested_tags/suggested_category 的字典

    Raises:
        ValueError: 重试耗尽后仍未获取有效元数据
    """
    client = get_client()
    prompt = _METADATA_EXTRACTION_PROMPT.format(
        text=content[:_CONTENT_PREVIEW_CHARS]
    )

    last_error: str | None = None

    for attempt in range(_LLM_RETRY_MAX_ATTEMPTS + 1):
        try:
            raw_result: dict[str, Any] | list[Any] = (
                await client.generate_json(
                    prompt=prompt,
                    system_prompt="你是一个专业的法律知识管理助手，"
                    "擅长从案件文本中提取结构化元数据。",
                    temperature=0.2,
                )
            )

            if isinstance(raw_result, list):
                last_error = "LLM 返回了列表格式而非字典"
                logger.warning(f"元数据提取尝试 {attempt + 1}: {last_error}")
                continue

            validated = _validate_case_metadata(raw_result, content)
            logger.info(
                f"元数据提取成功: title={validated.get('title', '')[:50]}, "
                f"category={validated.get('suggested_category', 'N/A')}, "
                f"tags={len(validated.get('suggested_tags', []))}"
            )
            return validated

        except (ValueError, json.JSONDecodeError) as e:
            last_error = str(e)
            logger.warning(
                f"元数据验证失败 (尝试 {attempt + 1}/"
                f"{_LLM_RETRY_MAX_ATTEMPTS + 1}): {e}"
            )
            if attempt < _LLM_RETRY_MAX_ATTEMPTS:
                await asyncio.sleep(_LLM_RETRY_DELAY_BASE * (attempt + 1))

        except Exception as e:
            last_error = str(e)
            logger.error(f"LLM 调用异常 (尝试 {attempt + 1}): {e}")
            if attempt < _LLM_RETRY_MAX_ATTEMPTS:
                await asyncio.sleep(_LLM_RETRY_DELAY_BASE * (attempt + 1))

    raise ValueError(f"元数据提取失败，已重试 {_LLM_RETRY_MAX_ATTEMPTS} 次: {last_error}")


def _validate_case_metadata(
    data: dict[str, Any], original_content: str
) -> dict[str, Any]:
    """验证 LLM 返回的案件元数据，填充缺失字段.

    Args:
        data: LLM 返回的原始元数据
        original_content: 原始案件内容（用于回退）

    Returns:
        验证并格式化后的元数据

    Raises:
        ValueError: 必需字段 title 缺失
    """
    title = data.get("title", "")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title 必须是非空字符串")

    result: dict[str, Any] = {
        "title": title.strip()[:AnalysisConfig.MAX_ENTRY_TITLE_LENGTH],
        "summary": "",
        "suggested_tags": ["案件"],
        "suggested_category": "case",
    }

    summary = data.get("summary", "")
    if isinstance(summary, str) and summary.strip():
        if len(summary) > 500:
            summary = summary[:500]
        result["summary"] = summary

    tags = data.get("suggested_tags", [])
    if isinstance(tags, list):
        clean_tags = [
            str(t).strip()
            for t in tags
            if isinstance(t, (str, int, float)) and str(t).strip()
        ]
        if clean_tags:
            result["suggested_tags"] = clean_tags[:10]

    if "案件" not in result["suggested_tags"]:
        result["suggested_tags"].append("案件")

    category = str(data.get("suggested_category", "case")).strip().lower()
    valid_categories = {"law", "methodology", "case", "other"}
    if category not in valid_categories:
        category = "case"
    result["suggested_category"] = category

    return result


def validate_entry_content(
    title: str,
    content: str,
    case_id: int,
) -> str | None:
    """创建 KnowledgeEntry 前验证内容质量.

    Args:
        title: 知识条目标题
        content: 知识条目正文
        case_id: 案件 ID（仅用于日志）

    Returns:
        内容有效返回 None，否则返回错误描述
    """
    if not title or not title.strip():
        return "标题为空"

    if len(title) > AnalysisConfig.MAX_ENTRY_TITLE_LENGTH:
        return f"标题过长（{len(title)}/{AnalysisConfig.MAX_ENTRY_TITLE_LENGTH}）"

    if not content or not content.strip():
        return "正文内容为空"

    if len(content) > AnalysisConfig.MAX_ENTRY_CONTENT_LENGTH:
        return (
            f"正文过长（{len(content)}/"
            f"{AnalysisConfig.MAX_ENTRY_CONTENT_LENGTH}）"
        )

    return None


async def process_single_case(
    db: AsyncSession,
    case: Case,
    dry_run: bool,
) -> CaseMigrationRecord:
    """处理单个案件迁移.

    Args:
        db: 数据库会话
        case: 案件实例
        dry_run: 是否为预览模式

    Returns:
        迁移记录
    """
    start_ts = time.monotonic()
    record = CaseMigrationRecord(
        case_id=case.id,
        case_title=case.title,
        status="pending",
    )

    try:
        validation_error = validate_case_data(case)
        if validation_error:
            record.status = "skipped"
            record.error = validation_error
            record.duration_seconds = time.monotonic() - start_ts
            logger.warning(f"案件数据验证失败 [ID={case.id}]: {validation_error}")
            return record

        case_text = case.case_text.strip()
        analysis = await fetch_latest_analysis(db, case.id)
        merged_content = build_merged_content(case, analysis)
        content_length = len(merged_content)
        logger.info(f"内容合并完成 [案件ID={case.id}]: 长度={content_length}")

        metadata: dict[str, Any]
        try:
            metadata = await extract_case_metadata_with_llm(merged_content)
        except Exception as e:
            logger.warning(
                f"LLM 元数据提取失败，使用默认值 [案件ID={case.id}]: {e}"
            )
            metadata = {
                "title": case.title[:AnalysisConfig.MAX_ENTRY_TITLE_LENGTH],
                "summary": (case.description or case_text)[:200].strip(),
                "suggested_tags": ["案件"],
                "suggested_category": "case",
            }

        record.metadata = metadata

        content_error = validate_entry_content(
            metadata["title"], merged_content, case.id
        )
        if content_error:
            record.status = "skipped"
            record.error = f"知识条目内容验证失败: {content_error}"
            record.duration_seconds = time.monotonic() - start_ts
            logger.warning(f"内容验证失败 [案件ID={case.id}]: {content_error}")
            return record

        if dry_run:
            record.status = "success"
            record.entry_id = -1
            record.duration_seconds = time.monotonic() - start_ts
            logger.info(
                f"[DRY-RUN] 将创建知识条目 "
                f"[案件ID={case.id}]: {metadata['title']}"
            )
            return record

        db_entry = KnowledgeEntry(
            title=metadata["title"],
            content=merged_content,
            summary=metadata.get("summary", ""),
            category=await _resolve_category(
                metadata.get("suggested_category", "case")
            ),
            status=EntryStatus.draft,
            source_type=SourceType.case_conversion,
            source_id=case.id,
            created_by=case.created_by or 1,
        )

        db.add(db_entry)
        await db.flush()
        logger.info(f"知识条目创建成功 [entry_id={db_entry.id}, case_id={case.id}]")

        tag_names = metadata.get("suggested_tags", ["案件"])
        if "案件" not in tag_names:
            tag_names.append("案件")
        await _associate_tags(db, db_entry.id, tag_names)
        logger.info(f"标签关联完成 [entry_id={db_entry.id}]: {tag_names}")

        record.status = "success"
        record.entry_id = db_entry.id
        record.duration_seconds = time.monotonic() - start_ts
        logger.info(
            f"案件迁移成功 [案件ID={case.id}]: "
            f"知识条目ID={db_entry.id}, "
            f"标题={metadata['title'][:50]}, "
            f"耗时={record.duration_seconds:.2f}s"
        )
        return record

    except Exception as e:
        record.status = "failed"
        record.error = f"{type(e).__name__}: {e!s}"
        record.duration_seconds = time.monotonic() - start_ts
        logger.error(
            f"案件迁移失败 [案件ID={case.id}]: {record.error}, "
            f"耗时={record.duration_seconds:.2f}s"
        )
        return record


async def run_migration(
    batch_size: int,
    dry_run: bool,
) -> MigrationReport:
    """执行迁移主流程.

    Args:
        batch_size: 每批处理数量
        dry_run: 是否预览模式

    Returns:
        迁移报告
    """
    report = MigrationReport(
        start_time=_format_timestamp(),
        batch_size=batch_size,
        dry_run=dry_run,
    )

    async with AsyncSessionLocal() as db:
        try:
            total = await count_eligible_cases(db)
            report.total_eligible = total
            logger.info(f"符合条件的案件总数: {total}")

            if total == 0:
                report.end_time = _format_timestamp()
                report.duration_seconds = 0.0
                logger.warning("没有找到符合条件的案件，迁移结束")
                return report

            if dry_run:
                logger.info("=" * 50)
                logger.info("预览模式 (DRY-RUN)：仅查询和统计，不写入数据库")
                logger.info("=" * 50)

            processed = 0
            while processed < total:
                cases = await fetch_completed_cases(db, processed, batch_size)
                if not cases:
                    break

                batch_start = time.monotonic()
                logger.info(
                    f"开始处理批次: 偏移量={processed}, "
                    f"本批数量={len(cases)}, "
                    f"进度={processed}/{total}"
                )

                async with db.begin_nested():
                    for case in cases:
                        record = await process_single_case(db, case, dry_run)
                        report.records.append(record)

                        if record.status == "success":
                            report.success_count += 1
                        elif record.status == "failed":
                            report.failure_count += 1
                        else:
                            report.skip_count += 1

                batch_duration = time.monotonic() - batch_start
                processed += len(cases)
                logger.info(
                    f"批次完成: 处理={len(cases)}, "
                    f"批次耗时={batch_duration:.2f}s, "
                    f"累计进度={processed}/{total}"
                )

        except Exception as e:
            logger.critical(f"迁移过程发生严重错误: {e}")
            raise
        finally:
            report.end_time = _format_timestamp()

    duration = 0.0
    if report.start_time and report.end_time:
        try:
            start_dt = datetime.strptime(
                report.start_time.replace(" UTC", ""),
                "%Y-%m-%d %H:%M:%S",
            )
            end_dt = datetime.strptime(
                report.end_time.replace(" UTC", ""),
                "%Y-%m-%d %H:%M:%S",
            )
            duration = (end_dt - start_dt).total_seconds()
        except (ValueError, AttributeError):
            pass
    report.duration_seconds = duration

    return report


async def main() -> int:
    args = parse_args()

    setup_logging(log_level=args.log_level, log_dir=settings.LOG_DIR)

    logger.info("=" * 50)
    logger.info("案例数据迁移脚本启动")
    logger.info(f"  批处理大小: {args.batch_size}")
    logger.info(f"  运行模式: {'预览 (DRY-RUN)' if args.dry_run else '正式迁移'}")
    logger.info(f"  日志级别: {args.log_level}")
    logger.info("=" * 50)

    try:
        report = await run_migration(
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
    except Exception as e:
        logger.critical(f"迁移失败: {e}")
        return 1
    finally:
        await async_engine.dispose()
        os.chdir(_old_cwd)
        logger.info("数据库引擎资源已释放")

    report_text = report.generate_text_report()
    print("\n" + report_text)

    logger.info("迁移报告生成完成")
    logger.info(f"总计: {report.total_eligible}, "
                f"成功: {report.success_count}, "
                f"失败: {report.failure_count}, "
                f"跳过: {report.skip_count}")

    report_dir = Path(settings.LOG_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    mode_suffix = "_dryrun" if args.dry_run else ""
    txt_path = report_dir / f"migration_report_{timestamp}{mode_suffix}.txt"
    txt_path.write_text(report_text, encoding="utf-8")
    logger.info(f"文本报告已保存: {txt_path}")

    json_report = report.generate_json_report()
    json_path = report_dir / f"migration_report_{timestamp}{mode_suffix}.json"
    json_path.write_text(
        json.dumps(json_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"JSON 报告已保存: {json_path}")

    if args.dry_run:
        logger.info("预览模式完成，未写入任何数据。移除 --dry-run 参数执行正式迁移。")
    else:
        logger.info("迁移完成！")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
