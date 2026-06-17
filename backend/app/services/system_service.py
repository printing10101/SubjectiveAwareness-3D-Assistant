"""系统管理服务模块.

提供系统日志查询和统计信息的服务层实现。
将数据库操作从路由层分离，遵循分层架构原则。
"""

# 导入模块: from sqlalchemy
from sqlalchemy import func, select
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 导入模块: from app.models.analysis
from app.models.analysis import Analysis
# 导入模块: from app.models.case
from app.models.case import Case
# 导入模块: from app.models.system_log
from app.models.system_log import SystemLog
# 导入模块: from app.models.user
from app.models.user import User


async def get_system_logs_service(
    # 函数 get_system_logs_service 的初始化逻辑
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
    # 初始化变量 stmt
    stmt = select(SystemLog)
    # 条件判断：处理业务逻辑
    if level:
        # 初始化变量 stmt
        stmt = stmt.where(SystemLog.log_level == level)
    # 初始化变量 stmt
    stmt = stmt.order_by(SystemLog.created_at.desc())
    # 初始化变量 result
    result = await db.execute(stmt.offset(skip).limit(limit))
    # 返回处理结果
    return list(result.scalars().all())


async def get_system_stats_service(db: AsyncSession) -> dict[str, int]:
    """获取系统统计信息.

    通过一条 SQL 查询获取案件数、分析数和用户数。

    Args:
        db: 数据库会话

    Returns:
        dict[str, int]: 统计信息字典
    """
    # 初始化变量 result
    result = await db.execute(
        select(
            func.count(Case.id).label("total_cases"),
            func.count(Analysis.id).label("total_analyses"),
            func.count(User.id).label("total_users"),
        )
    )
    row    # 条件判断：处理业务逻辑
 = result.first()
    # 条件判断: 检查 row is None
    if row is None:
        # 返回处理结果
        return {"total_cases": 0, "total_analyses": 0, "total_users": 0}
    # 返回处理结果
    return {
        "total_cases": row.total_cases,
        "total_analyses": row.total_analyses,
        "total_users": row.total_users,
    }
