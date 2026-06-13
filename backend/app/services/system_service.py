"""系统管理服务模块.

提供系统日志查询和统计信息的服务层实现。
将数据库操作从路由层分离，遵循分层架构原则。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.case import Case
from app.models.system_log import SystemLog
from app.models.user import User


async def get_system_logs_service(
    db: AsyncSession,
    level: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[SystemLog]:
    """获取系统日志列表.

    Args:
        db: 数据库会话
        level: 日志级别筛选（可选）
        skip: 分页偏移量
        limit: 每页数量

    Returns:
        list[SystemLog]: 日志记录列表
    """
    stmt = select(SystemLog)
    if level:
        stmt = stmt.where(SystemLog.log_level == level)
    stmt = stmt.order_by(SystemLog.created_at.desc())
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_system_stats_service(db: AsyncSession) -> dict[str, int]:
    """获取系统统计信息.

    通过一条 SQL 查询获取案件数、分析数和用户数。

    Args:
        db: 数据库会话

    Returns:
        dict[str, int]: 统计信息字典
    """
    result = await db.execute(
        select(
            func.count(Case.id).label("total_cases"),
            func.count(Analysis.id).label("total_analyses"),
            func.count(User.id).label("total_users"),
        )
    )
    row = result.first()
    if row is None:
        return {"total_cases": 0, "total_analyses": 0, "total_users": 0}
    return {
        "total_cases": row.total_cases,
        "total_analyses": row.total_analyses,
        "total_users": row.total_users,
    }
