#!/usr/bin/env python3
"""命令行标注工具.

功能：
1. 从 stdin 或指定文件读取 JSON Lines 格式的标注数据
2. 使用 Pydantic schema 验证每行数据
3. 批量写入 case_labels 表（覆盖式更新）
4. 同时生成结果文件 data/labels/v1.0.jsonl

输入格式（每行一个 JSON）:
    {"case_id": "CASE_0000", "d1_tier": "二档", "final_verdict": "认定帮信",
     "verdict_subtype": "供述明知", "judicial_era": "2025意见前"}

Usage:
    # 从 stdin 读
    cat labels.jsonl | python -m backend.scripts.label_via_cli

    # 从文件读
    python -m backend.scripts.label_via_cli --input labels.jsonl

    # 覆盖模式（默认 True）
    python -m backend.scripts.label_via_cli --input labels.jsonl --overwrite

    # 关闭覆盖模式（仅追加空白标签记录）
    python -m backend.scripts.label_via_cli --no-overwrite
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


# 将 backend 目录加入 sys.path
BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from typing import get_args  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.case import Case  # noqa: E402
from app.models.case_label import (  # noqa: E402
    CaseLabel,
    DimensionalTier,
    FinalVerdict,
    JudicialEra,
    VerdictSubtype,
)


# ---------------------------------------------------------------------------
# Pydantic 校验 schema
# ---------------------------------------------------------------------------


_LABEL_TYPE_TO_VALUES: dict[str, set[str]] = {
    "d1_tier": {tier.value for tier in DimensionalTier},
    "final_verdict": set(get_args(FinalVerdict)),
    "verdict_subtype": set(get_args(VerdictSubtype)),
    "judicial_era": set(get_args(JudicialEra)),
}

_ALLOWED_LABEL_TYPES: ClassVar[tuple[str, ...]] = tuple(_LABEL_TYPE_TO_VALUES.keys())


class CliLabelRow(BaseModel):
    """单行 JSON Lines 标注数据 schema.

    Attributes:
        case_id: 案件标识符。支持的格式：
            - 原始 case_id (例如 ``CASE_0000``)
            - 数据库 title (例如 ``帮信罪案例1``)
            - 数据库主键 (例如 ``1``)
        d1_tier: 维度分档 (可选)
        final_verdict: 最终定性 (可选)
        verdict_subtype: 认定子类 (可选)
        judicial_era: 司法时期 (可选)
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1, max_length=64, description="案件 ID")
    d1_tier: str | None = Field(default=None, description="维度分档")
    final_verdict: str | None = Field(default=None, description="最终定性")
    verdict_subtype: str | None = Field(default=None, description="认定子类")
    judicial_era: str | None = Field(default=None, description="司法时期")

    @field_validator("case_id")
    @classmethod
    def _trim_case_id(cls, v: str) -> str:
        """案件 ID 去空白."""
        v2 = v.strip()
        if not v2:
            msg = "case_id 不能为空"
            raise ValueError(msg)
        return v2

    @field_validator(*_ALLOWED_LABEL_TYPES, mode="after")
    @classmethod
    def _validate_label_value(cls, v: str | None, info) -> str | None:  # type: ignore[no-untyped-def]
        """根据 label_type 校验 label_value 是否在合法枚举中."""
        if v is None:
            return v
        v2 = v.strip()
        if not v2:
            return None
        allowed = _LABEL_TYPE_TO_VALUES[info.field_name]
        if v2 not in allowed:
            msg = (
                f"标签类型 '{info.field_name}' 的取值 '{v2}' 非法，"
                f"可选: {sorted(allowed)}"
            )
            raise ValueError(msg)
        return v2

    def iter_labels(self) -> list[tuple[str, str]]:
        """输出非空 (label_type, label_value) 列表."""
        out: list[tuple[str, str]] = []
        for lt in _ALLOWED_LABEL_TYPES:
            v = getattr(self, lt)
            if v:
                out.append((lt, v))
        return out


# ---------------------------------------------------------------------------
# 业务数据结构
# ---------------------------------------------------------------------------


@dataclass
class LineFailure:
    """单行解析/校验失败记录."""

    line_no: int
    raw: str
    error: str


@dataclass
class IngestResult:
    """CLI 标注导入汇总."""

    started_at: str
    finished_at: str = ""
    total_lines: int = 0
    success_lines: int = 0
    failed_lines: int = 0
    inserted_labels: int = 0
    updated_labels: int = 0
    cases_not_found: list[str] = field(default_factory=list)
    failures: list[LineFailure] = field(default_factory=list)
    output_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典."""
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_lines": self.total_lines,
            "success_lines": self.success_lines,
            "failed_lines": self.failed_lines,
            "inserted_labels": self.inserted_labels,
            "updated_labels": self.updated_labels,
            "cases_not_found": self.cases_not_found,
            "failures": [
                {"line": f.line_no, "error": f.error, "raw_preview": f.raw[:80]}
                for f in self.failures
            ],
            "output_file": self.output_file,
        }


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------


def load_lines(input_path: Path | None) -> list[tuple[int, str]]:
    """从文件或 stdin 读取所有行.

    Args:
        input_path: 文件路径，None 表示从 stdin 读取

    Returns:
        list[tuple[int, str]]: (行号, 原始行内容)
    """
    if input_path is None:
        raw = sys.stdin.read()
        lines = raw.splitlines()
    else:
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        lines = input_path.read_text(encoding="utf-8").splitlines()

    # 过滤空行
    out: list[tuple[int, str]] = []
    for idx, line in enumerate(lines, start=1):
        s = line.strip()
        if not s:
            continue
        out.append((idx, s))
    return out


# ---------------------------------------------------------------------------
# 数据库写入
# ---------------------------------------------------------------------------


_CASE_ID_RE = re.compile(r"^CASE_(\d{4,})$")


def _case_id_to_display_title(case_id: str) -> str | None:
    """将原始 case_id (例如 ``CASE_0000``) 映射为存储时的 title 文本.

    原始 JSON 的 ``case_id`` 是 ``CASE_0000``、``CASE_0001`` ... ``CASE_0099``，
    而 ingest_raw_cases.py 写入数据库时 title 取自 JSON ``title`` 字段
    (如 ``帮信罪案例1``)，索引号 +1 与 case_id 数值一致。

    Args:
        case_id: 原始 case_id

    Returns:
        str | None: 推断得到的 title 字符串；若不匹配则返回 None
    """
    m = _CASE_ID_RE.match(case_id.strip())
    if not m:
        return None
    try:
        n = int(m.group(1))
    except ValueError:
        return None
    return f"帮信罪案例{n + 1}"


async def _resolve_case_id_to_pk(
    db: AsyncSession, raw_case_id: str
) -> int | None:
    """根据案件原始 ID 找到数据库主键.

    支持的输入格式（按优先级）:
        1. ``CASE_0000`` 形式: 根据 ingest_raw_cases 的命名规则换算为
           ``帮信罪案例{N+1}`` 后按 title 匹配
        2. 原始 title (例如 ``帮信罪案例1``): 直接按 title 匹配
        3. 数据库主键 (数字字符串): 直接返回

    Args:
        db: 异步数据库会话
        raw_case_id: 原始 case_id / title / 主键字符串

    Returns:
        int | None: 数据库主键；不存在则返回 None
    """
    raw = raw_case_id.strip()
    if not raw:
        return None

    # 1. 数字主键直查
    if raw.isdigit():
        stmt = select(Case.id).where(Case.id == int(raw)).limit(1)
        result = await db.execute(stmt)
        pk = result.scalar_one_or_none()
        if pk is not None:
            return pk

    # 2. CASE_XXXX -> 帮信罪案例(N+1)
    mapped_title = _case_id_to_display_title(raw)

    candidate_titles: list[str] = []
    if mapped_title:
        candidate_titles.append(mapped_title)
    if mapped_title != raw:
        candidate_titles.append(raw)

    for title in candidate_titles:
        stmt = select(Case.id).where(Case.title == title).limit(1)
        result = await db.execute(stmt)
        pk = result.scalar_one_or_none()
        if pk is not None:
            return pk

    return None


async def _apply_labels(
    db: AsyncSession,
    case_pk: int,
    labels: list[tuple[str, str]],
    source: str,
    overwrite: bool,
) -> tuple[int, int]:
    """将一组 (label_type, label_value) 写入 case_labels.

    Args:
        db: 异步会话
        case_pk: 案件主键
        labels: (label_type, label_value) 列表
        source: 标注来源
        overwrite: 是否覆盖已有同 label_type

    Returns:
        tuple[int, int]: (inserted_count, updated_count)
    """
    if not labels:
        return 0, 0

    # 读取已有标签
    stmt = select(CaseLabel).where(CaseLabel.case_id == case_pk)
    result = await db.execute(stmt)
    existing = {lab.label_type: lab for lab in result.scalars().all()}

    inserted = 0
    updated = 0
    for label_type, label_value in labels:
        if label_type in existing:
            if not overwrite:
                continue
            row = existing[label_type]
            if row.label_value != label_value or row.source != source:
                row.label_value = label_value
                row.source = source
                updated += 1
        else:
            db.add(
                CaseLabel(
                    case_id=case_pk,
                    label_type=label_type,
                    label_value=label_value,
                    source=source,
                )
            )
            inserted += 1
    return inserted, updated


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


async def ingest_labels(
    lines: list[tuple[int, str]],
    *,
    source: str,
    overwrite: bool,
    output_path: Path,
) -> IngestResult:
    """解析 + 校验 + 写入 + 输出结果文件.

    Args:
        lines: (行号, 原始行) 列表
        source: 标注来源
        overwrite: 是否覆盖已有标签
        output_path: 结果文件输出路径 (data/labels/v1.0.jsonl)

    Returns:
        IngestResult: 汇总结果
    """
    result = IngestResult(
        started_at=datetime.now(UTC).isoformat(),
        total_lines=len(lines),
    )

    # 1. 解析 + 校验
    parsed: list[tuple[int, CliLabelRow]] = []
    for line_no, raw in lines:
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("JSON 顶层必须是对象")
            row = CliLabelRow.model_validate(payload)
            parsed.append((line_no, row))
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            result.failed_lines += 1
            result.failures.append(LineFailure(line_no=line_no, raw=raw, error=str(e)))
            logger.error("[line {}] 解析/校验失败: {}", line_no, e)

    if not parsed:
        result.finished_at = datetime.now(UTC).isoformat()
        return result

    # 2. 写入数据库
    output_records: list[dict[str, Any]] = []
    async with AsyncSessionLocal() as db:
        for idx, (line_no, row) in enumerate(parsed, start=1):
            try:
                pk = await _resolve_case_id_to_pk(db, row.case_id)
                if pk is None:
                    result.cases_not_found.append(row.case_id)
                    result.failed_lines += 1
                    result.failures.append(
                        LineFailure(
                            line_no=line_no,
                            raw=row.case_id,
                            error=f"案件 {row.case_id} 在数据库中不存在",
                        )
                    )
                    logger.warning("[line {}] 案件 {} 不存在", line_no, row.case_id)
                    continue

                labels = row.iter_labels()
                if not labels:
                    result.failed_lines += 1
                    result.failures.append(
                        LineFailure(
                            line_no=line_no,
                            raw=row.case_id,
                            error="至少需要一个非空标签 (d1_tier/final_verdict/...)",
                        )
                    )
                    continue

                inserted, updated = await _apply_labels(
                    db, pk, labels, source=source, overwrite=overwrite
                )
                result.inserted_labels += inserted
                result.updated_labels += updated
                result.success_lines += 1

                output_record: dict[str, Any] = {"case_id": row.case_id}
                for lt, lv in labels:
                    output_record[lt] = lv
                output_records.append(output_record)

                logger.info(
                    "[{}/{}] 写入: case_id={} inserted={} updated={}",
                    idx,
                    len(parsed),
                    row.case_id,
                    inserted,
                    updated,
                )
            except IntegrityError as e:
                await db.rollback()
                result.failed_lines += 1
                result.failures.append(
                    LineFailure(
                        line_no=line_no,
                        raw=row.case_id,
                        error=f"数据库完整性错误: {e.orig}",
                    )
                )
                logger.error("[line {}] 写入失败 (IntegrityError): {}", line_no, e)
            except SQLAlchemyError as e:
                await db.rollback()
                result.failed_lines += 1
                result.failures.append(
                    LineFailure(line_no=line_no, raw=row.case_id, error=f"数据库错误: {e}")
                )
                logger.error("[line {}] 写入失败 (SQLAlchemyError): {}", line_no, e)

        # 循环结束后显式 commit，避免在异常分支已 rollback 时仍尝试 commit
        try:
            await db.commit()
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error("最终提交失败: {}", e)
            result.failed_lines += result.success_lines
            result.success_lines = 0
            result.inserted_labels = 0
            result.updated_labels = 0
            output_records.clear()

    # 3. 写出 data/labels/v1.0.jsonl
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for rec in output_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    result.output_file = str(output_path)
    result.finished_at = datetime.now(UTC).isoformat()
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 stdin / JSONL 文件读取标注数据，写入数据库与结果文件",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=None,
        help="输入 JSONL 文件路径；缺省时从 stdin 读取",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/labels/v1.0.jsonl"),
        help="结果输出文件路径 (默认: data/labels/v1.0.jsonl)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="cli",
        help="标注来源 (默认 cli)",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="不覆盖已有标签 (默认覆盖)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认 INFO)",
    )
    return parser.parse_args(argv)


async def _async_main(args: argparse.Namespace) -> int:
    logger.remove()
    logger.add(sys.stderr, level=args.log_level)

    try:
        lines = load_lines(args.input)
    except FileNotFoundError as e:
        logger.error("输入加载失败: {}", e)
        return 2

    if not lines:
        logger.warning("输入为空，无标注可处理")
        return 0

    logger.info("从 {} 加载 {} 行非空数据", args.input or "stdin", len(lines))

    result = await ingest_labels(
        lines=lines,
        source=args.source,
        overwrite=not args.no_overwrite,
        output_path=args.output,
    )

    logger.success(
        "完成: 成功={} 失败={} 插入标签={} 更新标签={} 案件未找到={} 输出={}",
        result.success_lines,
        result.failed_lines,
        result.inserted_labels,
        result.updated_labels,
        len(result.cases_not_found),
        result.output_file,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.failed_lines == 0 else 1


def main() -> None:
    args = _parse_args()
    exit_code = asyncio.run(_async_main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
