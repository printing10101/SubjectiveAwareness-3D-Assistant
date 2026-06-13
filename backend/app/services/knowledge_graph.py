"""知识图谱服务模块.

提供法律规则的 CRUD 操作，包含数据净化和事务管理。
所有数据库操作均使用异步 API。
"""

from typing import Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_rule import LegalRule


# 允许更新的规则字段白名单
ALLOWED_RULE_FIELDS: set[str] = {
    "rule_id",
    "name",
    "description",
    "source_law",
    "article",
    "conditions",
    "conclusion",
    "evidence_types",
    "weight",
}


def _sanitize_rule_data(rule_data: dict[str, Any]) -> dict[str, Any]:
    """净化规则数据，仅保留白名单中的字段.

    Args:
        rule_data: 原始规则数据字典

    Returns:
        dict[str, Any]: 净化后的规则数据
    """
    return {k: v for k, v in rule_data.items() if k in ALLOWED_RULE_FIELDS}


async def get_legal_rules(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> list[LegalRule]:
    """分页查询法律规则列表.

    Args:
        db: 异步数据库会话
        skip: 跳过的记录数
        limit: 返回的最大记录数

    Returns:
        list[LegalRule]: 法律规则列表
    """
    result = await db.execute(
        select(LegalRule).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_legal_rule(db: AsyncSession, rule_id: int) -> LegalRule | None:
    """根据 ID 查询单个法律规则.

    Args:
        db: 异步数据库会话
        rule_id: 规则 ID

    Returns:
        LegalRule | None: 规则记录，不存在返回 None
    """
    result = await db.execute(
        select(LegalRule).where(LegalRule.id == rule_id)
    )
    return result.scalar_one_or_none()


async def create_legal_rule(
    db: AsyncSession, rule_data: dict[str, Any]
) -> LegalRule:
    """创建新的法律规则.

    包含数据净化和事务回滚机制。

    Args:
        db: 异步数据库会话
        rule_data: 规则数据字典

    Returns:
        LegalRule: 新创建的规则记录

    Raises:
        HTTPException 500: 数据库操作失败
    """
    safe_data: dict[str, Any] = _sanitize_rule_data(rule_data)
    db_rule = LegalRule(**safe_data)
    try:
        db.add(db_rule)
        await db.commit()
        await db.refresh(db_rule)
        return db_rule
    except Exception as e:
        await db.rollback()
        logger.error(f"创建法律规则失败: {e}")
        raise HTTPException(status_code=500, detail="创建法律规则失败") from e


async def update_legal_rule(
    db: AsyncSession,
    rule_id: int,
    rule_data: dict[str, Any],
) -> LegalRule:
    """更新法律规则.

    包含数据净化和事务回滚机制。

    Args:
        db: 异步数据库会话
        rule_id: 规则 ID
        rule_data: 要更新的字段数据

    Returns:
        LegalRule: 更新后的规则记录

    Raises:
        HTTPException 404: 规则不存在
        HTTPException 500: 数据库操作失败
    """
    db_rule: LegalRule | None = await get_legal_rule(db, rule_id)
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    safe_data: dict[str, Any] = _sanitize_rule_data(rule_data)
    try:
        for key, value in safe_data.items():
            setattr(db_rule, key, value)
        await db.commit()
        await db.refresh(db_rule)
        return db_rule
    except Exception as e:
        await db.rollback()
        logger.error(f"更新法律规则失败: rule_id={rule_id}, error={e}")
        raise HTTPException(status_code=500, detail="更新法律规则失败") from e


async def delete_legal_rule(db: AsyncSession, rule_id: int) -> bool:
    """删除法律规则.

    包含事务回滚机制。

    Args:
        db: 异步数据库会话
        rule_id: 规则 ID

    Returns:
        bool: 删除成功返回 True

    Raises:
        HTTPException 404: 规则不存在
        HTTPException 500: 数据库操作失败
    """
    db_rule: LegalRule | None = await get_legal_rule(db, rule_id)
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    try:
        await db.delete(db_rule)
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"删除法律规则失败: rule_id={rule_id}, error={e}")
        raise HTTPException(status_code=500, detail="删除法律规则失败") from e
