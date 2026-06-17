"""知识生命周期管理服务模块.

提供知识条目的信心评分动态调整、遗忘曲线衰减、知识库质量扫描
以及条目版本更替等完整的知识生命周期管理功能。

所有操作均使用异步数据库 API，支持事务回滚和分批处理。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: asyncio
import asyncio
# 导入模块: contextlib
import contextlib
# 导入模块: re
import re
# 导入模块: from dataclasses
from dataclasses import dataclass, field
# 导入模块: from datetime
from datetime import UTC, datetime, timedelta
# 导入模块: from typing
from typing import Any, Literal

# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import func, select
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 导入模块: from app.config
from app.config import AnalysisConfig
# 导入模块: from app.database
from app.database import get_async_db_session
# 导入模块: from app.models.entry_relation
from app.models.entry_relation import EntryRelation, RelationType
# 导入模块: from app.models.knowledge_entry
from app.models.knowledge_entry import EntryStatus, KnowledgeEntry


_WIKILINK_PATTERN: re.Pattern = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# 初始化变量 FeedbackType
FeedbackType = Literal["positive", "negative"]


# 应用装饰器: dataclass
@dataclass
# 定义 DecayStatistics 类
class DecayStatistics:
    """遗忘曲线衰减操作的统计结果.

    Attributes:
        total_decayed: 被衰减的总条目数
        newly_stale: 新标记为stale的条目数
        avg_decay_magnitude: 平均衰减幅度
        min_decay: 最小衰减值
        max_decay: 最大衰减值
    """

    total_decayed: int = 0
    newly_stale: int = 0
    avg_decay_magnitude: float = 0.0
    min_decay: float = 0.0
    max_decay: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        # 返回处理结果
        return {
            "total_decayed": self.total_decayed,
            "newly_stale": self.newly_stale,
            "avg_decay_magnitude": round(self.avg_decay_magnitude, 6),
            "min_decay": round(self.min_decay, 6),
            "max_decay": round(self.max_decay, 6),
        }


# 应用装饰器: dataclass
@dataclass
# 定义 LintIssue 类
class LintIssue:
    """知识库扫描发现的问题.

    Attributes:
        issue_type: 问题类型标识
        affected_entry_ids: 受影响的条目ID列表
        description: 问题描述
        suggestion: 修复建议
    """

    issue_type: str
    affected_entry_ids: list[int]
    description: str
    suggestion: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        # 返回处理结果
        return {
            "issue_type": self.issue_type,
            "affected_entry_ids": self.affected_entry_ids,
            "description": self.description,
            "suggestion": self.suggestion,
        }


# 应用装饰器: dataclass
@dataclass
# 定义 LintReport 类
class LintReport:
    """知识库质量扫描报告.

    Attributes:
        total_issues: 问题总数
        issues: 问题列表
        scanned_entries: 已扫描的条目总数
        timestamp: 扫描时间戳
    """

    total_issues: int = 0
    issues: list[LintIssue] = field(default_factory=list)
    scanned_entries: int = 0
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        # 返回处理结果
        return {
            "total_issues": self.total_issues,
            "issues": [issue.to_dict() for issue in self.issues],
            "scanned_entries": self.scanned_entries,
            "timestamp": self.timestamp,
        }


def _validate_entry_id(entry_id: int, param_name: str = "entry_id") -> None:
    """验证知识条目ID的有效性.

    Args:
        entry_id: 条目ID
        param_name: 参数名称（用于错误信息）

    Raises:
        ValueError: ID无效
    """
    # 条件判断：处理业务逻辑
    if not isinstance(entry_id, int) or entry_id <= 0:
        msg = f"无效的参数'{param_name}': {entry_id}，必须为正整数"
        # 抛出异常，处理错误情况
        raise ValueError(msg)


def _validate_feedback(feedback: str) -> FeedbackType:
    """验证用户反馈类型.

    Args:
        feedback: 反馈类型字符串

    Returns:
        FeedbackType: 验证后的反馈类型

    Raises:
        ValueError: 反馈类型无效
    """
    valid_feedback: tuple[str, ...] = ("posit    # 条件判断：处理业务逻辑
ive", "negative")
    # 条件判断: 检查 feedback not in valid_feedback
    if feedback not in valid_feedback:
        msg = (
            f"无效的反馈类型'{feedback}'，"
            f"仅支持: {', '.join(valid_feedback)}"
        )
        # 抛出异常，处理错误情况
        raise ValueError(msg)
    # 返回处理结果
    return feedback  # type: ignore[return-value]


def _extract_wikilinks(content: str) -> set[str]:
    """从Markdown内容中提取所有wikilinks引用的标题.

    Args:
        content: Markdown格式的正文内容

    Returns:
        # 条件判断：处理业务逻辑
    set[str]: 引用的条目标题集合（去重）
    """
    # 条件判断: 检查 not content
    if not content:
        # 返回处理结果
        return set()
    # 返回处理结果
    return {match.group(1).strip() for match in _WIKILINK_PATTERN.finditer(content)}


# =========================================================================
# 1. update_confidence — 根据用户反馈动态调整信心评分
# =========================================================================


async def update_confidence(
    # 函数 update_confidence 的初始化逻辑
    db: AsyncSession,
    entry_id: int,
    feedback: FeedbackType,
) -> KnowledgeEntry:
    """根据用户反馈动态调整知识条目的信心评分.

    正反馈(positive): confidence += 0.05，上限 1.0
    负反馈(negative): confidence -= 0.10，下限 0.0

    Args:
        db: 异步数据库会话
        entry_id: 知识条目唯一标识符
        feedback: 用户反馈类型，"positive" 或 "negative"

    Returns:
        KnowledgeEntry: 更新后的知识条目

    Raises:
        ValueError: 参数无效
        LookupError: 知识条目不存在
        RuntimeError: 数据库操作失败
    """
    _validate_entry_id(entry_id, "entry_id")
    # 初始化变量 feedback
    feedback = _validate_feedback(feedback)

    # 初始化变量 result
    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry
    # 条件判断：处理业务逻辑
: KnowledgeEntry | None = result.scalar_one_or_none()

    # 条件判断: 检查 entry is None
    if entry is None:
        msg = f"知识条目不    # 条件判断：处理业务逻辑
存在: entry_id={entry_id}"
        # 抛出异常，处理错误情况
        raise LookupError(msg)

    step: float
    # 条件判断: 检查 feedback == "positive"
    if feedback == "positive":
        # 初始化变量 step
        step = AnalysisConfig.KNOWLEDGE_POSITIVE_FEEDBACK_STEP
    # 其他情况的默认处理
    else:
        # 初始化变量 step
        step = -AnalysisConfig.KNOWLEDGE_NEGATIVE_FEEDBACK_STEP

    current_confidence: float = entry.confidence or 0.5
    new_confidence: float = max(0.0, min(1.0, current_confidence + step))

    # 记录日志信息
    logger.info(
        "信心评分调整: entry_id={}, feedback={}, "
        "old_confidence={:.4f}, new_confidence={:.4f}",
        entry_id,
        feedback,
        current_confidence,
        new_confidence,
    )

    # 尝试执行可能抛出异常的代码
    try:
        entry.confidence = new_confidence
        # 异步等待操作完成
        await db.flush()
        # 返回处理结果
        return entry
    # 捕获异常：处理业务逻辑
    except Exception as e:
        # 记录日志信息
        logger.error(f"更新信心评分失败: entry_id={entry_id}, error={e}")
        msg = f"更新信心评分失败: {e}"
        # 抛出异常，处理错误情况
        raise RuntimeError(msg) from e


# =========================================================================
# 2. apply_decay — 遗忘曲线衰减算法
# =========================================================================


async def apply_decay(db: AsyncSession) -> dict[str, Any]:
    """对知识库中所有条目应用遗忘曲线衰减算法.

    衰减机制：
    - 基于decay_coefficient参数逐条目计算衰减量
    - new_confidence = current_confidence * (1 - decay_coefficient)
    - 当confidence低于0.3时，自动将条目标记为"stale"状态

    支持大数据量分批处理（BATCH_SIZE = 500）。

    Returns:
        dict: 包含以下统计信息的字典：
            - total_decayed: 被衰减的总条目数
            - newly_stale: 新标记为stale的条目数
            - avg_decay_magnitude: 平均衰减幅度
            - min_decay: 最小衰减值
            - max_decay: 最大衰减值

    Raises:
        RuntimeError: 数据库操作失败，已自动回滚
    """
    # 初始化变量 decay_coefficient
    decay_coefficient = AnalysisConfig.KNOWLEDGE_DECAY_COEFFICIENT
    # 初始化变量 stale_threshold
    stale_threshold = AnalysisConfig.KNOWLEDGE_STALE_CONFIDENCE_THRESHOLD
    # 初始化变量 batch_size
    batch_size = AnalysisConfig.KNOWLEDGE_BATCH_SIZE

    # 初始化变量 stats
    stats = DecayStatistics()

    # 初始化变量 count_result
    count_result = await db.execute(
        select(func.count(KnowledgeEntry.id)).where(
            KnowledgeEntry.confidence.isnot(None),
            KnowledgeE    # 条件判断：处理业务逻辑
ntry.confidence > 0.0,
        )
    )
    total_eligible: int = count_result.scalar_one()
    # 条件判断: 检查 total_eligible == 0
    if total_eligible == 0:
        # 记录日志信息
        logger.info("apply_decay: 无需衰减的条目（所有条目confidence为空或已为0）")
        # 返回处理结果
        return stats.to_dict()

    # 记录日志信息
    logger.info(
        "开始应用遗忘曲线衰减: 系数={}, 待处理条目={}",
        decay_coefficient,
        total_eligible,
    )

    decay_magnitudes: list[float] = []
    # 初始化变量 offset
    offset = 0

    # 尝试执行可能抛出异常的代码
    try:
        # 循环条件：处理业务逻辑
        while offset < total_eligible:
            # 初始化变量 batch_result
            batch_result = await db.execute(
                select(KnowledgeEntry)
                .where(
                    KnowledgeEntry.confidence.isnot(None),
                    KnowledgeEntry.confidence > 0.0,
                )
                .order_by(KnowledgeEntry.id)
                .offset(offset)
                .limit(batch_size)
            )
            batch: list[KnowledgeEntry] = list(batch_result.scalars().all())

            # 遍历: for entry in batch:
            for entry in batch:
                old_confidence: float = entry.confidence or 0.0
                new_confidence: float = old_confidence * (1.0 - decay_coefficient)
                # 初始化变量 new_confidence
                new_confidence = max(0.0, new_confidence)
                decay_amount: float = old_confidence - new_confidence

                entry.confidence = ne
                # 条件判断：处理业务逻辑
w_confidence

                stats.total_decayed += 1
                decay_magnitudes.append(decay_amount)

                # 条件判断: 检查 new_confidence < stale_threshold
                if new_confidence < stale_threshold:
                    was_ac                    # 条件判断：处理业务逻辑
tive: bool = entry.status in (
                        EntryStatus.active,
                        EntryStatus.draft,
                    )
                    # 条件判断: 检查 was_active
                    if was_active:
                        entry.status = EntryStatus.stale
                        stats.newly_stale += 1
                        # 记录日志信息
                        logger.info(
                            "条目标记为stale: entry_id={}, "
                            "confidence={:.4f}",
                            entry.id,
                            new_confidence,
                        )

            # 异步等待操作完成
            await db.flus
        # 条件判断：处理业务逻辑
h()
            offset += len(batch)
            # 记录日志信息
            logger.debug(
                "衰减批次完成: offset={} / total={}", offset, total_eligible
            )

        # 异步等待操作完成
        await db.flush()

        # 条件判断: 检查 decay_magnitudes
        if decay_magnitudes:
            stats.avg_decay_magnitude = sum(decay_magnitudes) / len(decay_magnitudes)
            stats.min_decay = min(decay_magnitudes)
            stats.max_decay = max(decay_magnitudes)

        # 记录日志信息
        logger.info(
            "遗忘曲线衰减完成: total={}, stale={}, avg={:.6f}, "
            "min={:.6f}, max={:.6f}",
            stats.total_decayed,
            stats.newly_stale,
            stats.avg_decay_magnitude,
            stats.min_decay,
            stats.max_decay,
        )

        retur
    # 捕获异常：处理业务逻辑
n stats.to_dict()

    # 捕获并处理异常
    except Exception as e:
        # 记录日志信息
        logger.error(f"apply_decay 执行失败: {e}")
        msg = f"遗忘曲线衰减执行失败: {e}"
        # 抛出异常，处理错误情况
        raise RuntimeError(msg) from e


# =========================================================================
# 3. lint_knowledge_base — 知识库质量扫描
# =========================================================================


async def lint_knowledge_base(db: AsyncSession) -> dict[str, Any]:
    """全面扫描知识库并检测各类质量问题.

    检测以下问题类型：
    - blank_wikilinks: 内容中wikilinks引用但不存在的条目
    - contradiction: confidence > 0.7 但存在contradicts关系的条目组
    - outdated_content: last_verified_at 超过90天的条目
    - orphan_entry: 没有任何入站或出站关联关系的条目

    Returns:
        dict: 包含问题列表和修复建议的结构化数据：
            - total_issues: 问题总数
            - issues: 问题列表，每个问题包含 issue_type, affected_entry_ids,
              description, suggestion
            - scanned_entries: 已扫描的条目总数
            - timestamp: 扫描时间戳（ISO 8601）

    Raises:
        RuntimeError: 扫描过程发生数据库错误
    """
    # 初始化变量 batch_size
    batch_size = AnalysisConfig.KNOWLEDGE_BATCH_SIZE
    # 初始化变量 outdated_days
    outdated_days = AnalysisConfig.KNOWLEDGE_OUTDATED_DAYS_THRESHOLD
    # 初始化变量 contradiction_min_conf
    contradiction_min_conf = AnalysisConfig.KNOWLEDGE_CONTRADICTION_MIN_CONFIDENCE

    # 初始化变量 report
    report = LintReport()
    report.timestamp = datetime.now(UTC).isoformat()

    # 初始化变量 count_result
    count_result = await db.execute(
   
    # 条件判断：处理业务逻辑
     select(func.count(KnowledgeEntry.id))
    )
    total_entries: int = count_result.scalar_one()
    report.scanned_entries = total_entries

    # 记录日志信息
    logger.info("开始知识库质量扫描: 条目总数={}", total_entries)

    # 条件判断: 检查 total_entries == 0
    if total_entries == 0:
        # 记录日志信息
        logger.info("知识库为空，扫描完成")
        # 返回处理结果
        return report.to_dict()

    # 尝试执行可能抛出异常的代码
    try:
        # ---------------------------------------------------------------
        # 3a. 空白链接检测 — wikilinks引用但不存在的条目
        # ---------------------------------------------------------------
        blank_wikilinks_issues = await _detect_blank_wikilinks(
            db, total_entries, batch_size
        )
        report.issues.extend(blank_wikilinks_issues)

        # ---------------------------------------------------------------
        # 3b. 矛盾信息检测 — 高信心条目间的contradicts关系
        # ---------------------------------------------------------------
        contradiction_issues = await _detect_contradictions(
            db, contradiction_min_conf
        )
        report.issues.extend(contradiction_issues)

        # ---------------------------------------------------------------
        # 3c. 过时内容检测 — last_verified_at 超期
        # ---------------------------------------------------------------
        outdated_issues = await _detect_outdated_entries(db, outdated_days)
        report.issues.extend(outdated_issues)

        # ---------------------------------------------------------------
        # 3d. 孤立条目检测 — 无入站/出站关联
        # ---------------------------------------------------------------
        orphan_issues = await _detect_orphan_entries(db, total_entries, batch_size)
        report.issues.extend(orphan_issues)

        report.total_issues = len(report.issues)

        # 记录日志信息
        logger.info(
            "知识库质量扫描完成: issues={}, "
            "blank_wikilinks={}, contradictions={}, "
            "outdated={}, orphan={}",
            report.total_issues,
            len(blank_wikilinks_issues),
            len(contradiction_issues),
            len(outdated_issues),
            len(orphan_issues),
      
    # 捕获异常：处理业务逻辑
  )

        # 返回处理结果
        return report.to_dict()

    # 捕获并处理异常
    except Exception as e:
        # 记录日志信息
        logger.error(f"lint_knowledge_base 扫描失败: {e}")
        msg = f"知识库质量扫描失败: {e}"
        # 抛出异常，处理错误情况
        raise RuntimeError(msg) from e


async def _detect_blank_wikilinks(
    # 函数 _detect_blank_wikilinks 的初始化逻辑
    db: AsyncSession,
    total_entries: int,
    batch_size: int,
) -> list[LintIssue]:
    """检测内容中wikilinks引用但不存在的条目.

    Args:
        db: 异步数据库会话
        total_entries: 条目总数
        batch_size: 批处理大小

    Returns:
        list[LintIssue]: 空白链接问题列表
    """
    # 初始化变量 all_titles_result
    all_titles_result = await db.execute(select(KnowledgeEntry.title))
    existing_titles: set[str] = {
        row[0] for row in all_titles_result.all() if row[0]
    }

    issues: list[LintIssue] = []
    scanned_ids_with_issues: set[int] =
    # 循环条件：处理业务逻辑
 set()
    # 初始化变量 offset
    offset = 0

    # 循环条件: while offset < total_entries:
    while offset < total_entries:
        # 初始化变量 batch_result
        batch_result = await db.execute(
            select(KnowledgeEntry.id, KnowledgeEntry.content)
            .order_by(KnowledgeEntry.id)
            .offset(offset)
            .limit(bat
            # 条件判断：处理业务逻辑
ch_size)
        )
        # 初始化变量 batch
        batch = batch_result.all()

        # 遍历: for row in batch:
        for row in batch:
            entry_id: int = r            # 条件判断：处理业务逻辑
ow[0]
            content: str = row[1] or ""
            # 初始化变量 referenced_titles
            referenced_titles = _extract_wikilinks(content)

            # 条件判断: 检查 not referenced_titles
            if not referenced_titles:
                continue

            # 初始化变量 missing_titles
            missing_titles = referenced_titles - existing_titles - {""}
            # 条件判断: 检查 missing_titles
            if missing_titles:
                scanned_ids_with_issues.add(entry_id)
                issues.append(
                    LintIssue(
                        # 初始化变量 issue_type
                        issue_type="blank_wikilinks",
                        # 初始化变量 affected_entry_ids
                        affected_entry_ids=[entry_id],
                        # 初始化变量 description
                        description=(
                            f"知识条目(id={entry_id})内容中存在"
                            f"指向不存在条目的wikilinks: "
                            f"{', '.join(sorted(m
    # 条件判断：处理业务逻辑
issing_titles))}"
                        ),
                        # 初始化变量 suggestion
                        suggestion=(
                            "请检查引用的条目标题是否正确拼写，"
                            "或创建对应的知识条目。"
                        ),
                    )
                )

        offset += len(batch)

    # 条件判断: 检查 scanned_ids_with_issues
    if scanned_ids_with_issues:
        # 记录日志信息
        logger.info(
            "发现 {} 个条目存在 {} 个空白wikilinks问题",
            len(scanned_ids_with_issues),
            len(issues),
        )

    # 返回处理结果
    return issues


async def _detect_contradictions(
    # 函数 _detect_contradictions 的初始化逻辑
    db: AsyncSession,
    min_confidence: float,
) -> list[LintIssue]:
    """检测高信心条目间存在contradicts关系的矛盾信息.

    Args:
        db: 异步数据库会话
        min_confidence: 最低信心阈值

    Returns:
      
    # 条件判断：处理业务逻辑
  list[LintIssue]: 矛盾信息问题列表
    """
    # 初始化变量 result
    result = await db.execute(
        select(
            EntryRelation.source_entry_id,
            EntryRelation.target_entry_id,
        ).where(EntryRelation.relation_type == RelationType.contradicts)
    )
    # 初始化变量 contradict_relations
    contradict_relations = result.all()

    # 条件判断: 检查 not contradict_relations
    if not contradict_relations:
        # 返回处理结果
        return []

    all_contradiction_ids: set[int] = set()
    # 循环遍历：处理业务逻辑
    for rel in contradict_relations:
        all_contradiction_ids.add(rel[0])
        all_contradiction_ids.add(rel[1])

    # 初始化变量 confidence_result
    confidence_result = await db.execute(
        select(KnowledgeEntry.id, KnowledgeEntry.confidence)        # 条件判断：处理业务逻辑
.where(
            KnowledgeEntry.id.in_(list(all_contradiction_ids)),
            KnowledgeEntry.confidence >= min_confidence,
        )
    )
    high_conf_ids: set[int] = {row[0] for row in confidence_result.all()}

    issues: lis    # 循环遍历：处理业务逻辑
t[LintIssue] = []
    # 遍历: for source_id, target_id in contradict_relations:
    for source_id, target_id in contradict_relations:
        # 条件判断: 检查 source_id in high_conf_ids and target_id
        if source_id in high_conf_ids and target_id in high_conf_ids:
            issues.append(
                LintIssue(
                    # 初始化变量 issue_type
                    issue_type="contradiction",
                    # 初始化变量 affected_entry_ids
                    affected_entry_ids=[source_id, target_id],
                    # 初始化变量 description
                    description=(
                        f"知识条目(id={source_id})与条目(id={target_id})"
                        f"存在矛盾关系(contradicts)，且双方信心评分均 >= "
                 
    # 条件判断：处理业务逻辑
       f"{min_confidence}，内容可能存在冲突。"
                    ),
                    # 初始化变量 suggestion
                    suggestion=(
                        "请人工审查这两个条目的内容，"
                        "确认矛盾是否真实存在。"
                        "若一方正确，请更新错误方的内容并降低其信心评分；"
                        "若矛盾已解决，请移除contradicts关系。"
                    ),
                )
            )

    # 条件判断: 检查 issues
    if issues:
        # 记录日志信息
        logger.info("发现 {} 个高信心矛盾条目组", len(issues))

    # 返回处理结果
    return issues


async def _detect_outdated_entries(
    # 函数 _detect_outdated_entries 的初始化逻辑
    db: AsyncSession,
    outdated_days: int,
) -> list[LintIssue]:
    """检测last_verified_at超过指定天数的过时条目.

    Args:
        db: 异步数据库会话
        outdated_days: 过时阈值（天数）

    Returns:
        list[LintIssue]: 过时内容问题列表
    """
    cutoff_date: datetime = datetime.now(UTC) - time
    # 条件判断：处理业务逻辑
delta(days=outdated_days)

    # 初始化变量 result
    result = await db.execute(
        select(KnowledgeEntry.id, KnowledgeEntry.title).where(
            KnowledgeEntry.last_verified_at.isnot(None),
            KnowledgeEntry.last_verified_at < cutoff_date,
            KnowledgeEntry.status != EntryStatus.archived,
        )
    )
    # 初始化变量 outdated_entries
    outdated_entries = result.all()

    # 条件判断: 检查 not outdated_entries
    if not outdated_entries:
        # 返回处理结果
        return []

    outdated_ids: list[int] = [row[0] for row in outdated_entries]
    # 初始化变量 issues
    issues = [
        LintIssue(
            # 初始化变量 issue_type
            issue_type="outdated_content",
            # 初始化变量 affected_entry_ids
            affected_entry_ids=outdated_ids,
            # 初始化变量 description
            description=(
                f"发现 {len(outdated_ids)} 个知识条目的最后验证时间"
                f"超过 {outdated_days} 天，内容可能已过时。"
                f"受影响条目ID: {outdated_ids}"
            ),
            # 初始化变量 suggestion
            suggestion=(
                "请逐一审查这些条目的内容是否仍然准确有效，"
                "更新内容后设置新的 last_verified_at 时间戳。"
                "若确认不再使用，请将其状态设为 archived。"
            ),
        )
    ]

    # 记录日志信息
    logger.info("发现 {} 个过时条目（>{}天）", len(outdated_ids), outdated_days)
    # 返回处理结果
    return issues


async def _detect_orphan_entries(
    # 函数 _detect_orphan_entries 的初始化逻辑
    db: AsyncSession,
    total_entries: int,
    batch_size: int,
) -> list[LintIssue]:
    """检测没有任何入站或出站关联关系的孤立条目.

    Args:
        db: 异步数据库会话
        total_entries: 条目总数
        batch_size: 批处理大小

    Returns:
        list[LintIssue]: 孤立条目问题列表
    """
    # 初始化变量 outgoing_result
    outgoing_result = await db.execute(
        select(EntryRelation.source_entry_id).distinct()
    )
    outgoing_ids: set[int] = {row[0] for row in outgoing_result.all()}

    # 初始化变量 incoming_result
    incoming_result = await db.execute(
        select(EntryRelation.target_entry_id).distinct()
    )
    incoming_ids: set[int] = {row[0] for row in incoming_result.all()}

    connected_ids: set[int] = outgoing_ids | incoming_ids

    o
    # 循环条件：处理业务逻辑
rphan_ids: list[int] = []
    # 初始化变量 offset
    offset = 0

    # 循环条件: while offset < total_            # 条件判断：处理业务逻辑
    while offset < total_            # 条件判断：处理业务逻辑
entries:
        # 初始化变量 batch_result
        batch_result = await db.execute(
            select(KnowledgeEntry.id)
            .where(Know
    # 条件判断：处理业务逻辑
ledgeEntry.status != EntryStatus.archived)
            .order_by(KnowledgeEntry.id)
            .offset(offset)
            .limit(batch_size)
        )
        # 初始化变量 batch_ids
        batch_ids = {ro
        # 循环遍历：处理业务逻辑
w[0] for row in batch_result.all()}

        # 遍历: for entry_id in sorted(batch_ids):
        for entry_id in sorted(batch_ids):
            # 条件判断: 检查 entry_id not in connected_ids
            if entry_id not in connected_ids:
                orphan_ids.append(entry_id)  # noqa: PERF401

        offset += batch_size

    # 条件判断: 检查 not orphan_ids
    if not orphan_ids:
        # 返回处理结果
        return []

    # 初始化变量 issues
    issues = [
        LintIssue(
            # 初始化变量 issue_type
            issue_type="orphan_entry",
            # 初始化变量 affected_entry_ids
            affected_entry_ids=orphan_ids,
            # 初始化变量 description
            description=(
                f"发现 {len(orphan_ids)} 个孤立知识条目，"
                f"它们没有任何入站或出站的关联关系。"
                f"受影响条目ID: {orphan_ids}"
            ),
            # 初始化变量 suggestion
            suggestion=(
                "请审查这些条目是否需要与其他条目建立关联关系。"
                "可使用自动关联功能(find_related_entries / auto_link_entries)"
                "为孤立条目建立语义关系。如果条目确实独立且不需要关联，"
                "可忽略此提示。"
            ),
        )
    ]

    # 记录日志信息
    logger.info("发现 {} 个孤立条目", len(orphan_ids))
    # 返回处理结果
    return issues


# =========================================================================
# 4. supersede_entry — 知识条目版本更替
# =========================================================================


async def supersede_entry(
    # 函数 supersede_entry 的初始化逻辑
    db: AsyncSession,
    old_entry_id: int,
    new_entry_id: int,
    operated_by: int,
    reason: str | None = None,
) -> dict[str, Any]:
    """管理知识条目的版本更替，用新条目取代旧条目.

    执行以下核心操作：
    1. 在新旧条目间创建"supersedes"关联关系
    2. 将旧条目状态更新为"archived"
    3. 保留旧条目的完整历史数据供追溯
    4. 将指向旧条目的引用关系自动重定向到新条目
    5. 记录完整的操作日志

    Args:
        db: 异步数据库会话
        old_entry_id: 旧知识条目ID（被取代方）
        new_entry_id: 新知识条目ID（取代方）
        operated_by: 操作人用户ID
        reason: 更替原因（可选）

    Returns:
        dict: 包含操作摘要的字典：
            - old_entry_id: 旧条目ID
            - new_
    # 条件判断：处理业务逻辑
entry_id: 新条目ID
            - old_entry_status: 旧条目更新后的状态
            - redirected_relations: 重定向的关联关系数量
    
    # 条件判断：处理业务逻辑
        - operated_by: 操作人ID
            - reason: 更替原因
            - timestamp: 操作时间戳

    Raises:
        ValueError: 参数无效
        LookupError: 条目不存在
        RuntimeError: 数据库操作失败（已自动回滚）
    """
    _validate_entry_id(old_entry_id, "old_entry_id")
    _validate_entry_id(new_entry_id, "new_entry_id")

    
    # 条件判断：处理业务逻辑
if old_entry_id == new_entry_id:
        msg = "新旧条目ID不能相同，old_entry_id 与 new_entry_id 必须不同"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    # 条件判断: 检查 not isinstance(operated_by, int) or oper
    if not isinstance(operated_by, int) or operated_by <= 0:
        msg = f"无效的operated_by: {operated_by}，必须为正整数"
        # 抛出异常，处理错误情况
        raise ValueError(m
    # 条件判断：处理业务逻辑
sg)

    old_entry: KnowledgeEntry | None = (
        # 异步等待操作完成
        await db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.id == old_entry_id)
        )
    ).scalar_one_or_none()

    # 条件判断: 检查 old_entry is None
    if old_entry is None:
        msg = f"旧知识条目不存在: id={old_entry_id}"
        # 抛出异常，处理错误情况
        raise LookupError(msg)

    new_entry: KnowledgeEntry | None = (
        # 异步等待操作完成
        await db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.id == new_entry_id)
        )
    ).scalar_one_or_none()

    # 条件判断: 检查 new_entry is None
    if new_entry is None:
        msg = f"新知识条目不存在: id={new_entry_id}"
        # 抛出异常，处理错误情况
        raise LookupError(msg)

    # 记录日志信息
    logger.info(
        "开始版本更替: old_entry_id={}, new_entry_id={}, operated_by={}, reason={}",
        old_entry_id,
        new_entry_id,
        operated_by,
   
        # 条件判断：处理业务逻辑
     reason or "未指定",
    )

    # 初始化变量 redirected_count
    redirected_count = 0
    # 初始化变量 timestamp
    timestamp = datetime.now(UTC).isoformat()

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 existing_relation
        existing_relation = (
            # 异步等待操作完成
            await db.execute(
                select(EntryRelation).where(
                    EntryRelation.source_entry_id == new_entry_id,
                    EntryRelation.target_entry_id == old_entry_id,
                    EntryRelation.relation_type == RelationType.supersedes,
                )
            )
        ).scalar_one_or_none()

        # 条件判断: 检查 existing_relation is not None
        if existing_relation is not None:
            # 记录日志信息
            logger.info(
                "supersedes关系已存在: source={}, target={}",
                new_entry_id,
                old_entry_id,
            )
        # 其他情况的默认处理
        else:
            # 初始化变量 supersedes_relation
            supersedes_relation = EntryRelation(
                # 初始化变量 source_entry_id
                source_entry_id=new_entry_id,
                # 初始化变量 target_entry_id
                target_entry_id=old_entry_id,
                # 初始化变量 relation_type
                relation_type=RelationType.supersedes,
            )
            db.add(supersedes_relation)
            # 异步等待操作完成
            await db.flush()
            # 记录日志信息
            logger.info(
                "已创建supersedes关系: source={}, target={}",
                new_entry_id,
                old_entry_id,
            )

        # ---------------------------------------------------------------
        # 将旧条目标记为 archived
        # ---------------------------------------------------------------
        old_entry.status = EntryStatus.archived
        # 异步等待操作完成
        await db.flush()
        # 记录日志信息
        logger.info("旧条目标记为archived: entry_id={}", old_entry_id)

        # ---------------------------------------------------------------
        # 重定向引用：将所有指向旧条目的EntryRelation重定向到新条目
        # ----------------------------
        # 条件判断：处理业务逻辑
-----------------------------------
        # 初始化变量 incoming_result
        incoming_result = await db.execute(
            select(EntryRelation).where(
                EntryRelation.target_entry_id == old_entry_id,
                EntryRelation.relation_type != RelationType.supersedes,
            )
        )
        incoming_relations: list[EntryRelation] = l
        # 循环遍历：处理业务逻辑
ist(
            incoming_result.scalars().all()
        )

        # 遍历: for rel in incoming_relations:
        for rel in incoming_relations:
            rel.target_entry_id = new_entry_id
            redirected_count += 1

        # 条件判断: 检查 redirected_count > 0
        if redirected_count > 0:
            # 异步等待操作完成
            await db.flush()
            # 记录日志信息
            logger.info(
                "已重定向 {} 条关联关系到新条目: new_entry_id={}",
                redirected_count,
                new_entry_id,
            )

        # ---------------------------------------------------------------
        # 操作日志
        # ---------------------------------------------------------------
        log_message = (
            f"[版本更替] old_entry_id={old_entry_id} -> new_entry_id={new_entry_id}, "
            f"operated_by={operated_by}, reason='{reason or '未指定'}', "
            f"redirected_relations={redirected_count}, timestamp={timestamp}"
        )
        # 记录日志信息
        logger.info(log_message)

        # 返回处理结果
        return {
            "old_entry_id": old_entry_id,
            "new_entry_id": new_entry_id,
            "old_entry_status": old_entry.status.value,
            "redirected_relations": redirected_count,
            "operated_by": operated_by,
            "reason": reason 
    # 捕获异常：处理业务逻辑
or "未指定",
            "timestamp": timestamp,
        }

    # 捕获并处理异常
    except Exception as e:
        # 记录日志信息
        logger.error(f"版本更替失败: old={old_entry_id}, new={new_entry_id}, error={e}")
        msg = f"知识条目版本更替失败: {e}"
        # 抛出异常，处理错误情况
        raise RuntimeError(msg) from e


# =========================================================================
# 5. 定时任务调度器
# =========================================================================


# 应用装饰器: dataclass
@dataclass
# 定义 ScheduleConfig 类
class ScheduleConfig:
    """定时任务调度配置.

    Attributes:
        decay_interval: apply_decay 执行间隔（秒），默认 86400（24小时）
        lint_interval: lint_knowledge_base 执行间隔（秒），默认 604800（7天）
        decay_enabled: 是否启用衰减定时任务
        lint_enabled: 是否启用扫描定时任务
    """

    decay_interval: int = AnalysisConfig.KNOWLEDGE_DECAY_SCHEDULE_INTERVAL
    lint_interval: int = AnalysisConfig.KNOWLEDGE_LINT_SCHEDULE_INTERVAL
    decay_enabled: bool = True
    lint_enabled: bool = True


# 定义 KnowledgeLifecycleScheduler 类
class KnowledgeLifecycleScheduler:
    """知识生命周期定时任务调度器.

    基于 asyncio 实现轻量级定时调度，支持：
    - 可配置的执行间隔和时间窗口
    - 独立的启动/停止控制
    - 手动触发和自动定时两种模式
    - 任务状态查询

    Usage:
        # 初始化变量 scheduler
        scheduler = KnowledgeLifecycleScheduler()
        # 异步等待操作完成
        await scheduler.start()
        # ... 应用运行中 ...
        await scheduler.stop()
    """

    def __init__(self, config: ScheduleConfig | None = None) -> None:

        # 执行 __init__ 函数的核心逻辑
        self._config = config or ScheduleConfig()
        self._decay_task: asyncio.Task[Any] | None = None
        self._lint_task: asyncio.Task[Any] | None = None
        self._running = False
        self._last_decay_run: str | None = None
        self._last_lint_run: str | None = None

    # 应用装饰器: property
    @property
    def is_running(self) -> bool:
        """是否正在运行."""
        # 返回处理结果
        return self._running

    # 应用装饰器: property
    @property
    def status(self) -> dict[str, Any]:
           # 条件判断：处理业务逻辑
     """运行状态信息."""
        # 返回处理结果
        return {
            "running": self._running,
            "decay_enabled": self._config.decay_enabled,
            "lint_enabled": self._config.lint_enabled,
            "decay_interval_seconds": self._config.decay_interval,
            "lint_interv
        # 条件判断：处理业务逻辑
al_seconds": self._config.lint_interval,
            "last_decay_run": self._last_decay_
        # 条件判断：处理业务逻辑
run,
            "last_lint_run": self._last_lint_run,
        }

    async def start(self) -> None:
        """启动定时任务调度器.

        分别启动decay和lint两个独立的循环任务。
        """
        # 条件判断: 检查 self._running
        if self._running:
            # 记录日志信息
            logger.warning("调度器已在运行中，忽略重复启动")
               # 条件判断：处理业务逻辑
         return

        self._running = True
        # 记录日志信息
        logger.info(
            "知识生命周期调度器启动: decay_interval={}s, lint_interval={}s",
            self._config.decay_interval,
            self._config.lint_interval,
        )

        # 条件判断: 检查 self._config.decay_enabled
        if self._config.decay_enabled:
            self._decay_task = asyncio.create_task(self._decay_loop())

        # 条件判断: 检查 self._config.lint_enabled
        if self._config.lint_enabled:
            self._lint_task = asyncio.create_task(self._lint_loop())

    async def stop
        # 循环遍历：处理业务逻辑
(self) -> None:
        """停止定时任务调度器，取消所有运行中的任务."""
        self._running = False

        # 遍历: for task in (self._decay_task, self._lint_task):
        for task in (self._decay_task, self._lint_task):
            # 条件判断: 检查 task and not task.done()
            if task and not task.done():
                task.cancel()
                # 使用上下文管理器管理资源
                with contextlib.suppress(asyncio.CancelledError):
                    # 异步等待操作完成
                    await task

        self._decay_task = None
        self._lint_task = None
        # 记录日志信息
        logger.info("知识生命周期调度器已停止")

    async def trigger_decay(self) -> dict[str, Any]:
        """手动触发一次遗忘曲线衰减.

        Returns:
            dict: apply_decay 的统计结果

        Raises:
            RuntimeError: 数据库操作失败
        """
        # 记录日志信息
        logger.info("手动触发遗忘曲线衰减...")
        # 异常处理：处理业务逻辑
        try:
            async with get_async_db_session() as db:
                # 初始化变量 result
                result = await apply_decay(db)
            self._last_decay_run = datetime.no        # 捕获异常：处理业务逻辑
w(UTC).isoformat()
            # 返回处理结果
            return result  # type: ignore[return-value]
        except Exception as e:
            # 记录日志信息
            logger.error(f"手动触发decay失败: {e}")
            raise

    async def trigger_lint(self) -> dict[str, Any]:
        """手动触发一次知识库质量扫描.

        Returns:
            dict: lint_knowledge_base 的扫描报告

        Raises:
            RuntimeError: 数据库操作失败
        """
        # 记录日志信息
        logger.i        # 异常处理：处理业务逻辑
nfo("手动触发知识库质量扫描...")
        # 尝试执行可能抛出异常的代码
        try:
            async with get_async_db_session() as db:
                # 初始化变量 result
                result = await lint_knowledge_base(db)
            self._last_        # 捕获异常：处理业务逻辑
lint_run = datetime.now(UTC).isoformat()
            # 返回处理结果
            return result  # type: ignore[return-value]
        except Exception as e:
            # 记录日志信息
            logger.error(f"手动触发lint失败: {e}")
            raise

    a        # 循环条件：处理业务逻辑
sync def _decay_loop(self) -> None:
        "            # 异常处理：处理业务逻辑
""衰减定时循环任务."""
        # 循环条件: while self._running:
        while self._running:
            # 尝试执行可能抛出异常的代码
            try:
                # 记录日志信息
                logger.info("定时任务: 开始执行遗忘曲线衰减...")
                async with get_async_db_session() as db:
                    # 初始化变量 result
                    result = await apply_decay(db)
               # 捕获异常：处理业务逻辑
             self._last_decay_run = datetime.now(UTC).isoformat()
                          # 捕获异常：处理业务逻辑
  logger.info("定时decay完成: {}", result)
            # 捕获并处理异常
            except asyncio.CancelledError:
                # 记录日志信息
                logger.info("衰减定时任务被取消")
                break
            # 捕获并处理异常
            except Exception as e:  # noqa: BLE001
                logger.error(f"定时decay执行异常: {e}")

            # 异步等待操作完成
            await asyncio.sleep(self._config        # 循环条件：处理业务逻辑
.decay_interval)

    async def _lint_loo            # 异常处理：处理业务逻辑
        # 函数 _lint_loo 的初始化逻辑
p(self) -> None:
        """扫描定时循环任务."""
        # 循环条件: while self._running:
        while self._running:
            # 尝试执行可能抛出异常的代码
            try:
                # 记录日志信息
                logger.info("定时任务: 开始执行知识库质量扫描...")
                async with get_async_db_session() as db:
                    # 初始化变量 result
                    result = await lint_knowledge_base(db)
                self._last_lint_run = dateti            # 捕获异常：处理业务逻辑
me.now(UTC).isoformat()
                # 记录日志信息
                logger.info(
                    "定时lint            # 捕获异常：处理业务逻辑
完成: total_issues={}",
                    result.get("total_issues", 0),
                )
            # 捕获并处理异常
            except asyncio.CancelledError:
                # 记录日志信息
                logger.info("扫描定时任务被取消")
                break
            # 捕获并处理异常
            except Exception as e:  # noqa: BLE001
                logger.error(f"定时lint执行异常: {e}")

            # 异步等待操作完成
            await asyncio.sleep(self._config.lint_interval)


async def run_decay_sync() -> dict[str, Any]:
    """便捷函数 — 同步执行一次衰减（在事务内完成）.

    Returns:
        dict: 衰减统计结果
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await apply_decay(db)  # type: ignore[return-value]


async def run_lint_sync() -> dict[str, Any]:
    """便捷函数 — 同步执行一次质量扫描（在事务内完成）.

    Returns:
        dict: 扫描报告
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await lint_knowledge_base(db)  # type: ignore[return-value]
