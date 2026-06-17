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

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: argparse
import argparse
# 导入模块: asyncio
import asyncio
# 导入模块: json
import json
# 导入模块: re
import re
# 导入模块: sys
import sys
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
# 导入模块: from pydantic
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
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

# 导入模块: from typing
from typing import get_args  # noqa: E402

# 导入模块: from app.database
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


# 定义 CliLabelRow 类
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

    # 初始化变量 model_config
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1, max_length=64, description="案件 ID")
    d1_tier: str | None = Field(default=None, description="维度分档")
    final_verdict: str | None = Field(default=None, description="最终定性")
    verdict_subtype: str | None = Field(default=None, description="认定子类")
    judicial_era: str | None = Field(default=None, description="司法时期")

    # 应用装饰器: field_validator
    @field_validator("case_id")
    # 应用装饰器: classmethod
    @classmethod
    def _trim_case_id(cls, v: str) -> str:
        """案件 ID 去空白."""
        v        # 条件判断：处理业务逻辑
2 = v.strip()
        # 条件判断: 检查 not v2
        if not v2:
            msg = "case_id 不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return v2

    # 应用装饰器: field_validator
    @field_validator(*_ALLOWED_LABEL_TYPES, mode="after")
    # 应用装饰器: classmethod
    @classmethod
    def _validate_label_value(cls, v: str | None, info) -> str | None:  # type: ignore[no-untyped-def]
        """根据 lab        # 条件判断：处理业务逻辑
el_type 校验 label_value 是否在合法枚举中."""
                # 条件判断：处理业务逻辑
if v is None:
            # 返回处理结果
            return v
        v2 = v.strip()
        # 条件判断: 检查 not v2
        if not v2:
         # 条件判断：处理业务逻辑
           return None
        # 初始化变量 allowed
        allowed = _LABEL_TYPE_TO_VALUES[info.field_name]
        # 条件判断: 检查 v2 not in allowed
        if v2 not in allowed:
            msg = (
                f"标签类型 '{info.field_name}' 的取值 '{v2}' 非法，"
                f"可选: {sorted(allowed)}"
            )
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return v2

    def iter_labels(self) -> list[tuple[str, str]]:
        """输出非空 (label_type, label_value) 列表."""
        out:            # 条件判断：处理业务逻辑
 list[tuple[str, str]] = []
        # 循环遍历：处理业务逻辑
        for lt in _ALLOWED_LABEL_TYPES:
            v = getattr(self, lt)
            # 条件判断: 检查 v
            if v:
                out.append((lt, v))
        # 返回处理结果
        return out


# ---------------------------------------------------------------------------
# 业务数据结构
# ---------------------------------------------------------------------------


# 应用装饰器: dataclass
@dataclass
# 定义 LineFailure 类
class LineFailure:
    """单行解析/校验失败记录."""

    line_no: int
    raw: str
    error: str


# 应用装饰器: dataclass
@dataclass
# 定义 IngestResult 类
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
        # 返回处理结果
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
                {"line": f.line_no, "error": f.error, "raw_                # 循环遍历：处理业务逻辑
preview": f.raw[:80]}
                # 遍历: for f in self.failures
                for f in self.failures
            ],
            "output_file": self.output_file,
        }


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------


def load_lines(input_path: Path | None) -> list[tuple[int, str]]:
    """从文件或 stdi    # 条件判断：处理业务逻辑
n 读取所有行.

    Args:
        input_path: 文件路径，None 表示从 stdin 读取

    Returns:
              # 条件判断：处理业务逻辑
  list[tuple[int, str]]: (行号, 原始行内容)
    """
    # 条件判断: 检查 input_path is None
    if input_path is None:
        raw = sys.stdin.read()
        # 初始化变量 lines
        lines = raw.splitlines()
    # 其他情况的默认处理
    else:
        # 条件判断: 检查 not input_path.exists()
        if not input_path.exists():
            # 抛出异常，处理错误情况
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        # 初始化变量 lines
        lines = input        # 条件判断：处理业务逻辑
_path.read_text(encoding="utf-8").splitline    # 循环遍历：处理业务逻辑
s()

    # 过滤空行
    out: list[tuple[int, str]] = []
    # 遍历: for idx, line in enumerate(lines, start=1):
    for idx, line in enumerate(lines, start=1):
        s = line.strip()
        # 条件判断: 检查 not s
        if not s:
            continue
        out.append((idx, s))
    # 返回处理结果
    return out


# ---------------------------------------------------------------------------
# 数据库写入
# ---------------------------------------------------------------------------


_CASE_ID_RE = re.compile(r"^CASE_(\d{4,})$")


def _case_id_to_display_title(case_id: str) -> str | None:
    """将原始 case_id (例如 ``CASE_0000``) 映射为存储时的 title 文本.

    原始 JSON 的 ``case_id`` 是 ``CASE_0000``、``CASE_0001`` ... ``CASE_0099``，
    而 ingest_raw_cases.py 写入数据库时 title 取自 JSON ``title`` 字段
    (    # 条件判断：处理业务逻辑
如 ``帮信罪案例1``)，索引号 +1 与 case_id 数值一致。

    Args:
        case_id: 原始 case_id

    Returns:
        str | None: 推断得到的 title 字符串；若不匹配则返回 None
    """
    m = _CASE_ID_RE.match(case_id.strip())
    # 条件判断: 检查 not m
    if not m:
        # 返回处理结果
        return None
    # 异常处理：处理业务逻辑
    try:
        n = int(m.group(1))
    # 捕获异常：处理业务逻辑
    except ValueError:
        # 返回处理结果
        return None
    # 返回处理结果
    return f"帮信罪案例{n + 1}"


async def _resolve_case_id_to_pk(
    # 函数 _resolve_case_id_to_pk 的初始化逻辑
    db: AsyncSession, raw_case_id: str
) -> int | None:
    """根据案件原始 ID 找到数据库主键.

    支持的输入格式（按优先级）:
        1. ``CASE_0000`` 形式: 根据 ingest_raw_cases 的命名规则换算为
           ``帮信罪案例{N+1}`` 后按 title 匹配
        2. 原始 title (例如 ``帮信罪案例1``): 直接按 t    # 条件判断：处理业务逻辑
itle 匹配
        3. 数据库主键 (数字字符串): 直    # 条件判断：处理业务逻辑
接返回

    Args:
        db: 异步数据库会话
        raw_case_id: 原始 case_id / title / 主键字符串

    Returns:
        int | None: 数据库主键；不存在则返回 None
    """
    raw =        # 条件判断：处理业务逻辑
 raw_case_id.strip()
    # 条件判断: 检查 not raw
    if not raw:
        # 返回处理结果
        return None

    # 1. 数字主键直查
    if raw.isdigit():
        # 初始化变量 stmt
        stmt = select(Case.id).where(Case.id == int(r    # 条件判断：处理业务逻辑
aw)).limit(1)
        # 初始化变量 result
        result = await db.execute(s    # 条件判断：处理业务逻辑
tmt)
        pk = result.scalar_one_or_none()
        # 条件判断: 检查 pk is not None
        if pk is not None:
            # 返回处理结果
            return pk

    # 2. CASE_XXXX -> 帮信罪案例(N+1)
    mapped_title = _case_id_to_display_title(raw)

    candidate_titles: list[str] = []
    # 条件判断: 检查 mapped_        # 条件判断：处理业务逻辑
    if mapped_        # 条件判断：处理业务逻辑
title:
        candidate_titles.append(mapped_ti
    # 循环遍历：处理业务逻辑
tle)
    # 条件判断: 检查 mapped_title != raw
    if mapped_title != raw:
        candidate_titles.append(raw)

    # 遍历: for title in candidate_titles:
    for title in candidate_titles:
        # 初始化变量 stmt
        stmt = select(Case.id).where(Case.title == title).limit(1)
        # 初始化变量 result
        result = await db.execute(stmt)
        pk = result.scalar_one_or_none()
        # 条件判断: 检查 pk is not None
        if pk is not None:
            # 返回处理结果
            return pk

    # 返回处理结果
    return None


async def _apply_labels(
    # 函数 _apply_labels 的初始化逻辑
    db: AsyncSession,
    case_pk: int,
    labels: list[tuple[str, str]],
    source: str,
    o    # 条件判断：处理业务逻辑
verwrite: bool,
) -> tuple[int, int]:
    """将一组 (label_type, label_value) 写入 case_labels.

    Args:
        db: 异步会话
        case_pk: 案件主键
        labels: (label_type, label_value) 列表
        source: 标注来源
        overwrite: 是否覆盖已有同 label_type

    Returns:
        tuple[int, int]:         # 条件判断：处理业务逻辑
(inserted_cou            # 条件判断：处理业务逻辑
nt, updated_count)
    """
    # 条件判断: 检查 not labels
    if not labels:
        # 返回处理结果
        return 0, 0

    # 读取已有标签
    stmt = select(CaseLabel).where(CaseLabel.case_id == case_pk)
    # 初始化变量 result
    result = await db.execute(stmt)
    # 初始化变量 existing
    existing = {    # 循环遍历：处理业务逻辑
lab.label_type: lab for lab in result.scalars().all()}

    # 初始化变量 inserted
    inserted = 0
    # 初始化变量 updated
    updated = 0
    # 遍历: for label_type, label_value in labels:
    for label_type, label_value in labels:
        # 条件判断: 检查 label_type in existing
        if label_type in existing:
            # 条件判断: 检查 not overwrite
            if not overwrite:
                continue
            row = existing[label_type]
            # 条件判断: 检查 row.label_value != label_value or row.so
            if row.label_value != label_value or row.source != source:
                row.label_value = label_value
                row.source = source
                updated += 1
        # 其他情况的默认处理
        else:
            db.add(
                CaseLabel(
                    # 初始化变量 case_id
                    case_id=case_pk,
                    # 初始化变量 label_type
                    label_type=label_type,
                    # 初始化变量 label_value
                    label_value=label_value,
                    # 初始化变量 source
                    source=source,
                )
            )
            inserted += 1
    # 返回处理结果
    return inserted, updated


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


async def ingest_labels(
    # 函数 ingest_labels 的初始化逻辑
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
                # 条件判断：处理业务逻辑
    overwrite: 是否覆盖已有标签
        output_path: 结果文件输出路径 (data/labels/v1.0.jsonl)

    Returns:
        IngestResult: 汇总结果
    """
    # 初始化变量 result
    result = IngestResult(
        # 初始化变量 started_at
        started_at=datetime.now(UTC).isoformat    # 循环遍历：处理业务逻辑
(),
        # 初始化变量 total_lines
        total_lines=len(lines),
    )

    # 1. 解析 + 校验
    parsed: list[tuple[int, CliLabelRow]] = []
    # 遍历: for line_        # 异常处理：处理业务逻辑
    for line_        # 异常处理：处理业务逻辑
no, raw in lines:
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 payload
            payload = json.loads(raw)
            # 条件判断: 检查 not isinstance(paylo
            if not isinstance(paylo
    # 条件判断：处理业务逻辑
ad, dict):
                # 抛出异常，处理错误情况
                raise ValueError("JSON 顶层必须是对象")
            row = CliLabelRow.model_validate(payload)
            parsed.appen        # 捕获异常：处理业务逻辑
d((line_no, row))
        # 捕获并处理异常
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            result.failed_lines += 1
            result.failures.append(LineFailure(line_no=line_no, raw                # 条件判断：处理业务逻辑
=raw, error=str(e)))
            # 记录日志信息
            logger.error("[line {}] 解析/校验失败: {}", line_no, e)

    # 条件判断: 检查 not parsed
    if not parsed:
        result.finished_at = datetime.now(UTC).isoformat()
         # 循环遍历：处理业务逻辑
       return result

    # 2. 写入数据库
    output_records: list[dict[str, Any]] = []
    async with AsyncSessionLocal() as db:
        # 遍历: for idx, (line_            # 异常处理：处理业务逻辑
        for idx, (line_            # 异常处理：处理业务逻辑
no, row) in enumerate(parsed, start=1):
            # 尝试执行可能抛出异常的代码
            try:
                pk = await _resolve_case_id_to_pk(db, row.case_id)
                # 条件判断: 检查 pk is None
                if pk is None:
                    result.cases_not_found.append(row.case_id)
                                # 条件判断：处理业务逻辑
    result.failed_lines += 1
                    result.failures.append(
                        LineFailure(
                            # 初始化变量 line_no
                            line_no=line_no,
                            raw=row.case_id,
                            # 初始化变量 error
                            error=f"案件 {row.case_id} 在数据库中不存在",
                        )
                    )
                    # 记录日志信息
                    logger.warning("[line {}] 案件 {} 不存在", line_no, row.case_id)
                    continue

                # 初始化变量 labels
                labels = row.iter_labels()
                # 条件判断: 检查 not labels
                if not labels:
                    result.failed_lines += 1
                    result.failures.append(
                        LineFailure(
                            # 初始化变量 line_no
                            line_no=line_no,
                            raw=row.case_id,
                            # 初始化变量 error
                            error="至少需要一个非空标签 (d1_tier/final_verdict/...)",
                        )
                    )
                    continue

                # 异步等待操作完成
                inserted, updated = await _apply_labels(
                    db, pk, labels, source=source, overwrite=overwrite
                )
                result.inserted_labels += inserted
                re                # 循环遍历：处理业务逻辑
sult.updated_labels += updated
                result.success_lines += 1

                output_record: dict[str, Any] = {"case_id": row.case_id}
                # 遍历: for lt, lv in labels:
                for lt, lv in labels:
                    output_record[lt] = lv
                output_records.append(output_record)

                # 记录日志信息
                logger.info(
                    "[{}/{}] 写入: case_id={} inserted={} updated={}",
                    idx,
                    len(parsed),
                    row.case_id,
                    inserted,
                   # 捕获异常：处理业务逻辑
             updated,
                )
            # 捕获并处理异常
            except IntegrityError as e:
                # 异步等待操作完成
                await db.rollback()
                result.failed_lines += 1
                result.failures.append(
                    LineFailure(
                        # 初始化变量 line_no
                        line_no=line_no,
                        raw=row.case_id,
                        # 初始化变量 error
                        error=f"数据库完整性错误: {e.orig}",
                    )
                )
                          # 捕获异常：处理业务逻辑
  logger.error("[line {}] 写入失败 (IntegrityError): {}", line_no, e)
            # 捕获并处理异常
            except SQLAlchemyError as e:
                # 异步等待操作完成
                await db.rollback()
                result.failed_lines += 1
                result.failures.append(
                    LineFailure(line_no=line_no, raw=row.case_id, error=f"数据库错误: {e}")
                )
                # 记录日志信息
                logger.error("[line {}] 写入失败 (SQLAlchemyError): {}", li        # 异常处理：处理业务逻辑
ne_no, e)

        # 循环结束后显式 commit，避免在异常分支已 rollback 时仍尝试 commit
        try:
            # 异步等待操作完成
            await db.commit()
        # 捕获并处理异常
        except SQLAlchemyError as e:
            # 异步等待操作完成
            await db.rollback()
            # 记录日志信息
            logger.error("最终提交失败: {}", e)
            result.failed_lines += result.success_lines
            result.success_lines = 0
            result.inserted_labels = 0
            result.updated_labels = 0
               # 循环遍历：处理业务逻辑
     output_records.clear()

    # 3. 写出 data/labels/v1.0.jsonl
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # 使用上下文管理器管理资源
    with output_path.open("w", encoding="utf-8") as f:
        # 遍历: for rec in output_records:
        for rec in output_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    result.output_file = str(output_path)
    result.finished_at = datetime.now(UTC).isoformat()
    # 返回处理结果
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:


    # 执行 _parse_args 函数的核心逻辑
    parser = argparse.ArgumentParser(
        # 初始化变量 description
        description="从 stdin / JSONL 文件读取标注数据，写入数据库与结果文件",
    )
    parser.add_argument(
        "--input",
        "-i",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=None,
        # 初始化变量 help
        help="输入 JSONL 文件路径；缺省时从 stdin 读取",
    )
    parser.add_argument(
        "--output",
        "-o",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=Path("data/labels/v1.0.jsonl"),
        # 初始化变量 help
        help="结果输出文件路径 (默认: data/labels/v1.0.jsonl)",
    )
    parser.add_argument(
        "--source",
        # 初始化变量 type
        type=str,
        # 初始化变量 default
        default="cli",
        # 初始化变量 help
        help="标注来源 (默认 cli)",
    )
    parser.add_argument(
        "--no-overwrite",
        # 初始化变量 action
        action="store_true",
        # 初始化变量 help
        help="不覆盖已有标签 (默认
    # 条件判断：处理业务逻辑
覆盖)",
    )
    parser.add_argument(
        "--log-level",
        # 初始化变量 type
        type=str,
        # 初始化变量 default
        default="INFO",
        # 初始化变量 choices
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        # 初始化变量 help
        help="日志级别 (默认 INFO)",
    )
    # 返回处理结果
    return parser.parse_args(argv)


async def _async_main(args: argparse.
    # 异常处理：处理业务逻辑
Namespace) -> int:
    # 记录日志信息
    logger.remove()
    lo    # 捕获异常：处理业务逻辑
gger.add(sys.stderr, level=args.log_level)

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 lines
        lines = load_lines(args.input)
    # 捕获并处理异常
    except FileNotFoundError as e:
        # 记录日志信息
        logger.error("输入加载失败: {}", e)
        # 返回处理结果
        return 2

    # 条件判断: 检查 not lines
    if not lines:
        # 记录日志信息
        logger.warning("输入为空，无标注可处理")
        # 返回处理结果
        return 0

    # 记录日志信息
    logger.info("从 {} 加载 {} 行非空数据", args.input or "stdin", len(lines))

    # 初始化变量 result
    result = await ingest_labels(
        # 初始化变量 lines
        lines=lines,
        # 初始化变量 source
        source=args.source,
        # 初始化变量 overwrite
        overwrite=not args.no_overwrite,
        # 初始化变量 output_path
        output_path=args.output,
    )

    # 记录日志信息
    logger.succes

# 条件判断：处理业务逻辑
s(
        "完成: 成功={} 失败={} 插入标签={} 更新标签={} 案件未找到={} 输出={}",
        result.success_lines,
        result.failed_lines,
        result.inserted_labels,
        result.updated_labels,
        len(result.cases_not_found),
        result.output_file,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    # 返回处理结果
    return 0 if result.failed_lines == 0 else 1


def main() -> None:


    # 执行 main 函数的核心逻辑
    args = _parse_args()
    # 初始化变量 exit_code
    exit_code = asyncio.run(_async_main(args))
    sys.exit(exit_code)


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()
