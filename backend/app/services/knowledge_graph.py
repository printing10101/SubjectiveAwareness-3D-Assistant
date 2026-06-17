"""知识图谱服务模块.

提供法律规则的 CRUD 操作，包含数据净化和事务管理。
所有数据库操作均使用异步 API。
"""

# 导入模块: from typing
from typing import Any

# 导入模块: from fastapi
from fastapi import HTTPException
# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import select
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 导入模块: from app.models.legal_rule
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
    # 返回处理结果
    return {k: v for k, v in rule_data.items() if k in ALLOWED_RULE_FIELDS}


async def get_legal_rules(
    # 函数 get_legal_rules 的初始化逻辑
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
    # 初始化变量 result
    result = await db.execute(
        select(LegalRule).offset(skip).limit(limit)
    )
    # 返回处理结果
    return list(result.scalars().all())


async def get_legal_rule(db: AsyncSession, rule_id: int) -> LegalRule | None:
    """根据 ID 查询单个法律规则.

    Args:
        db: 异步数据库会话
        rule_id: 规则 ID

    Returns:
        LegalRule | None: 规则记录，不存在返回 None
    """
    # 初始化变量 result
    result = await db.execute(
        select(LegalRule).where(LegalRule.id == rule_id)
    )
    # 返回处理结果
    return result.scalar_one_or_none()


async def create_legal_rule(
    # 函数 create_legal_rule 的初始化逻辑
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
    # 初始化变量 db_rule
    db_rule = LegalRule(**safe_data)
    # 异常处理：处理业务逻辑
    try:
        db.add(db_rule)
        # 异步等待操作完成
        await db.commit()
        # 异步等待操作完成
        await db.refresh(db_rule)
        # 返回处理结果
        return db_rule
    # 捕获异常：处理业务逻辑
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"创建法律规则失败: {e}")
        # 抛出异常，处理错误情况
        raise HTTPException(status_code=500, detail="创建法律规则失败") from e


async def update_legal_rule(
    # 函数 update_legal_rule 的初始化逻辑
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
    # 异步等待操作完成
    db_rule: LegalRule | None = await get_legal_rule(db, rule_id)
    # 条件判断：处理业务逻辑
    if not db_rule:
        # 抛出异常，处理错误情况
        raise HTTPException(status_code=404, detail="Rule not found")
    safe_data: dict[str, Any] = _sanitize_rul    # 异常处理：处理业务逻辑
e_data(rule_data)
    # 尝试执行可能抛出异常的代码
    try:
        # 循环遍历：处理业务逻辑
        for key, value in safe_data.items():
            setattr(db_rule, key, value)
        # 异步等待操作完成
        await db.commit()
        # 异步等待操作完成
        await db.refresh(db_rule)
         # 捕获异常：处理业务逻辑
   return db_rule
    # 捕获并处理异常
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"更新法律规则失败: rule_id={rule_id}, error={e}")
        # 抛出异常，处理错误情况
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
    # 异步等待操作完成
    db_rule: LegalRule | None = await get_legal_    # 条件判断：处理业务逻辑
rule(db, rule_id)
    # 条件判断: 检查 not db_rule
    if not db_rule:
        # 抛出异常，处理错误情况
        raise HTTPException(status    # 异常处理：处理业务逻辑
_code=404, detail="Rule not found")
    # 尝试执行可能抛出异常的代码
    try:
        # 异步等待操作完成
        await db.delete(db_rule)
        aw    # 捕获异常：处理业务逻辑
ait db.commit()
        # 返回处理结果
        return True
    # 捕获并处理异常
    except Exception as e:
        # 异步等待操作完成
        await db.rollback()
        # 记录日志信息
        logger.error(f"删除法律规则失败: rule_id={rule_id}, error={e}")
        # 抛出异常，处理错误情况
        raise HTTPException(status_code=500, detail="删除法律规则失败") from e
