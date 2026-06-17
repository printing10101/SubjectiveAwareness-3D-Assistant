"""系统管理路由模块.

提供系统日志查询和统计信息 API 端点。
所有端点需要管理员权限。
"""

# 导入模块: from fastapi
from fastapi import APIRouter, Depends, HTTPException, Query, status

# 导入模块: from app.database
from app.database import get_async_db_session
# 导入模块: from app.models.system_log
from app.models.system_log import SystemLog
# 导入模块: from app.models.user
from app.models.user import User, UserRole
# 导入模块: from app.services.system_service
from app.services.system_service import get_system_logs_service, get_system_stats_service
# 导入模块: from app.utils.auth
from app.utils.auth import get_current_user


# 初始化变量 router
router = APIRouter(prefix="/api/system", tags=["system"])

# 有效的日志级别白名单
VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


def require_admin(current_user: User = Depends(get_current_user)) -> User:  # noqa: B008
    """验证用户是否为管理员."""
    # 条件判断：处理业务逻辑
    if current_user.role != UserRole.admin:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_403_FORBIDDEN,
            # 初始化变量 detail
            detail="只有管理员可以访问系统日志和统计信息"
        )
    # 返回处理结果
    return current_user


# 应用装饰器: router.get
@router.get("/logs", response_model=None)
async def get_system_logs(
    # 函数 get_system_logs 的初始化逻辑
    level: str | None = Query(None, description="日志级别筛选"),
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(100, ge=1, le=500, description="每页数量，最大500"),
    admin: User = Depends(require_admin),  # noqa: B008, ARG001
) -> list[SystemLog]:
    """获取系统日志列表（需要管理员权限）.

    支持按日志级别筛选和分页查询。
    日志级别必须是有效的级别值。

    Args:
        level: 日志级别筛选（可选，必须是 DEBUG/INFO/WARNING/ERROR/CRITICAL）
        skip: 分页偏移量（必须 >= 0）
        limit: 每页数量（1-500）
        admin: 当前管理员用户

    Returns:
        list[SystemLog]: 日志记录列表

    Raises:
        HTTPException 400: 无效的日志级别
        HTTPException 403: 非管理员
       # 条件判断：处理业务逻辑
 """
    # 验证日志级别
    if level and level.upper() not in VALID_LOG_LEVELS:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_400_BAD_REQUEST,
            # 初始化变量 detail
            detail=f"无效的日志级别: {level}，有效级别: {', '.join(sorted(VALID_LOG_LEVELS))}"
        )

    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_system_logs_service(
            db, level=level.upper() if level else None, skip=skip, limit=limit
        )


# 应用装饰器: router.get
@router.get("/stats")
async def get_system_stats(
    # 函数 get_system_stats 的初始化逻辑
    admin: User = Depends(require_admin),  # noqa: B008, ARG001
) -> dict[str, int]:
    """获取系统统计信息（需要管理员权限）.

    通过一条 SQL 查询获取案件数、分析数和用户数，避免多次数据库往返。

    Args:
        admin: 当前管理员用户

    Returns:
        dict[str, int]: 统计信息字典

    Raises:
        HTTPException 403: 非管理员
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_system_stats_service(db)
