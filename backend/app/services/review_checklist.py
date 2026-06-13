"""人工审查清单服务模块.

定义11项标准化审查项模板，提供审查记录的创建、更新和查询功能。

@file: review_checklist.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import ReportReview


# ---------------------------------------------------------------------------
# 11项标准化审查项模板
# ---------------------------------------------------------------------------


REVIEW_ITEMS_TEMPLATE: dict[str, dict[str, Any]] = {
    "item_01": {
        "id": "item_01",
        "title": "事实认定审查",
        "description": "审查案件事实是否清楚，证据是否确实、充分",
        "default_checked": False,
        "category": "事实审查",
    },
    "item_02": {
        "id": "item_02",
        "title": "证据合法性审查",
        "description": "审查证据收集程序是否合法，是否存在非法证据排除情形",
        "default_checked": False,
        "category": "证据审查",
    },
    "item_03": {
        "id": "item_03",
        "title": "证据关联性审查",
        "description": "审查证据与案件事实之间是否存在关联性",
        "default_checked": False,
        "category": "证据审查",
    },
    "item_04": {
        "id": "item_04",
        "title": "主观明知认定审查",
        "description": "审查嫌疑人主观明知程度的认定是否合理",
        "default_checked": False,
        "category": "要件审查",
    },
    "item_05": {
        "id": "item_05",
        "title": "构成要件齐备性审查",
        "description": "审查帮信罪构成要件是否齐备",
        "default_checked": False,
        "category": "要件审查",
    },
    "item_06": {
        "id": "item_06",
        "title": "情节严重程度审查",
        "description": "审查情节档级（T1-T4）认定是否适当",
        "default_checked": False,
        "category": "量刑审查",
    },
    "item_07": {
        "id": "item_07",
        "title": "法律适用审查",
        "description": "审查法律条文引用是否准确，法律适用是否正确",
        "default_checked": False,
        "category": "法律审查",
    },
    "item_08": {
        "id": "item_08",
        "title": "量刑建议适当性审查",
        "description": "审查量刑建议是否在法定幅度内，是否适当",
        "default_checked": False,
        "category": "量刑审查",
    },
    "item_09": {
        "id": "item_09",
        "title": "程序合法性审查",
        "description": "审查办案程序是否符合法律规定",
        "default_checked": False,
        "category": "程序审查",
    },
    "item_10": {
        "id": "item_10",
        "title": "权利保障审查",
        "description": "审查嫌疑人诉讼权利是否得到保障",
        "default_checked": False,
        "category": "程序审查",
    },
    "item_11": {
        "id": "item_11",
        "title": "综合结论审查",
        "description": "审查综合分析结论是否合理，是否有遗漏或矛盾",
        "default_checked": False,
        "category": "综合审查",
    },
}


# ---------------------------------------------------------------------------
# 审查清单服务函数
# ---------------------------------------------------------------------------


def get_review_items_template() -> dict[str, dict[str, Any]]:
    """获取审查项模板.

    Returns:
        dict: 11项审查项模板
    """
    return REVIEW_ITEMS_TEMPLATE.copy()


def create_default_review_items() -> dict[str, bool]:
    """创建默认审查项状态.

    Returns:
        dict: 所有审查项默认未勾选状态
    """
    return {
        item_id: item["default_checked"]
        for item_id, item in REVIEW_ITEMS_TEMPLATE.items()
    }


async def create_review(
    db: AsyncSession,
    report_id: int,
    reviewer_id: int | None = None,
) -> ReportReview:
    """创建审查记录.

    Args:
        db: 数据库会话
        report_id: 报告ID
        reviewer_id: 审查人ID

    Returns:
        ReportReview: 创建的审查记录
    """
    logger.info(f"创建审查记录 - 报告ID={report_id}, 审查人ID={reviewer_id}")

    review = ReportReview(
        report_id=report_id,
        reviewer_id=reviewer_id,
        items=create_default_review_items(),
        comments=None,
        completed_at=None,
    )

    db.add(review)
    await db.commit()
    await db.refresh(review)

    logger.info(f"审查记录创建成功 - 审查ID={review.id}")

    return review


async def get_review_by_report_id(
    db: AsyncSession,
    report_id: int,
) -> ReportReview | None:
    """根据报告ID获取审查记录.

    Args:
        db: 数据库会话
        report_id: 报告ID

    Returns:
        ReportReview | None: 审查记录或None
    """
    result = await db.execute(
        select(ReportReview).where(ReportReview.report_id == report_id)
    )
    return result.scalar_one_or_none()


async def update_review_items(
    db: AsyncSession,
    review_id: int,
    items: dict[str, bool],
) -> ReportReview | None:
    """更新审查项状态.

    Args:
        db: 数据库会话
        review_id: 审查记录ID
        items: 审查项状态字典

    Returns:
        ReportReview | None: 更新后的审查记录或None
    """
    logger.info(f"更新审查项状态 - 审查ID={review_id}")

    result = await db.execute(
        select(ReportReview).where(ReportReview.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        logger.warning(f"审查记录不存在 - 审查ID={review_id}")
        return None

    # 更新审查项状态
    review.items = items
    await db.commit()
    await db.refresh(review)

    logger.info(f"审查项状态更新成功 - 审查ID={review_id}")

    return review


async def update_review_comments(
    db: AsyncSession,
    review_id: int,
    comments: str,
) -> ReportReview | None:
    """更新审查意见.

    Args:
        db: 数据库会话
        review_id: 审查记录ID
        comments: 审查意见

    Returns:
        ReportReview | None: 更新后的审查记录或None
    """
    logger.info(f"更新审查意见 - 审查ID={review_id}")

    result = await db.execute(
        select(ReportReview).where(ReportReview.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        logger.warning(f"审查记录不存在 - 审查ID={review_id}")
        return None

    review.comments = comments
    await db.commit()
    await db.refresh(review)

    logger.info(f"审查意见更新成功 - 审查ID={review_id}")

    return review


async def complete_review(
    db: AsyncSession,
    review_id: int,
    items: dict[str, bool] | None = None,
    comments: str | None = None,
) -> ReportReview | None:
    """完成审查.

    更新审查项状态、审查意见，并设置审查完成时间。

    Args:
        db: 数据库会话
        review_id: 审查记录ID
        items: 审查项状态字典（可选）
        comments: 审查意见（可选）

    Returns:
        ReportReview | None: 更新后的审查记录或None
    """
    logger.info(f"完成审查 - 审查ID={review_id}")

    result = await db.execute(
        select(ReportReview).where(ReportReview.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        logger.warning(f"审查记录不存在 - 审查ID={review_id}")
        return None

    # 更新审查项状态
    if items is not None:
        review.items = items

    # 更新审查意见
    if comments is not None:
        review.comments = comments

    # 设置审查完成时间
    review.completed_at = datetime.now()

    await db.commit()
    await db.refresh(review)

    logger.info(f"审查完成 - 审查ID={review_id}")

    return review


async def get_review_statistics(
    db: AsyncSession,
    report_id: int,
) -> dict[str, Any]:
    """获取审查统计信息.

    Args:
        db: 数据库会话
        report_id: 报告ID

    Returns:
        dict: 审查统计信息
    """
    review = await get_review_by_report_id(db, report_id)

    if not review:
        return {
            "total_items": len(REVIEW_ITEMS_TEMPLATE),
            "checked_items": 0,
            "unchecked_items": len(REVIEW_ITEMS_TEMPLATE),
            "completion_rate": 0.0,
            "is_completed": False,
        }

    items = review.items or {}
    checked_count = sum(1 for v in items.values() if v)
    total_count = len(REVIEW_ITEMS_TEMPLATE)

    return {
        "total_items": total_count,
        "checked_items": checked_count,
        "unchecked_items": total_count - checked_count,
        "completion_rate": checked_count / total_count if total_count > 0 else 0.0,
        "is_completed": review.completed_at is not None,
        "completed_at": review.completed_at.isoformat() if review.completed_at else None,
    }


__all__ = [
    "REVIEW_ITEMS_TEMPLATE",
    "complete_review",
    "create_default_review_items",
    "create_review",
    "get_review_by_report_id",
    "get_review_items_template",
    "get_review_statistics",
    "update_review_comments",
    "update_review_items",
]
