"""数据库连接与会话管理模块.

提供异步引擎（含连接池）和异步会话管理：
- 异步引擎：基于 create_async_engine，适用于高并发场景
- 连接池参数仅对 PostgreSQL 生效，SQLite 自动跳过（NullPool 不适用）
- 所有数据库操作统一使用异步会话，确保非阻塞事件循环
"""

# 导入模块: os
import os
# 导入模块: from collections.abc
from collections.abc import AsyncGenerator
# 导入模块: from contextlib
from contextlib import asynccontextmanager

# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
# 导入模块: from sqlalchemy.orm
from sqlalchemy.orm import declarative_base

# 导入模块: from app.config
from app.config import settings


_CPU_COUNT: int = os.cpu_count() or 4


def _is_postgresql(url: str) -> bool:
    """判断数据库 URL 是否为 PostgreSQL."""
    # 返回处理结果
    return "postgresql" in url


def _pool_kwargs() -> dict:
    """构建连接池参数，SQLite 的 NullPool 不支持 pool_size/max_overflow."""
    # 返回处理结果
    return {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
        "pool_recycle": settings.DB_POOL_RECYCLE,
    }


def _engine_kwargs(url: str) -> dict:
    """根据数据库类型构建 create_engine 通用参数."""
    kwargs: dict = {"echo": settings.DB_ECHO}
    # 条件判断：处理业务逻辑
    if _is_postgresql(url):
        kwargs.update(_pool_kwargs())
        kwargs["connect_args"] = {"timeout": settings.DB_CONNECT_TIMEOUT}
    # 其他情况的默认处理
    else:
        kwargs["connect_args"] = {"check_same_thread": False}
    # 返回处理结果
    return kwargs


async_engine: AsyncEngine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    **_engine_kwargs(settings.ASYNC_DATABASE_URL),
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    async_engine,
    # 初始化变量 class_
    class_=AsyncSession,
    # 初始化变量 expire_on_commit
    expire_on_commit=False,
    # 初始化变量 autoflush
    autoflush=False,
)

# 初始化变量 Base
Base = declarative_base()


# 应用装饰器: asynccontextmanager
@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """异步数据库会话上下文管理器.

    使用异步引擎的连接池获取会话，自动处理事务提交和回滚。

    适用于：
    - 通用数据库操作（路由层、服务层、工具层）
    - FastAPI 依赖注入（可通过别名 ``get_async_db`` 引用）

    Yields:
        AsyncSession: SQLAlchemy 异步数据库会话实例

    Raises:
        Exception: 发生异常时自动回滚后重新抛出

    Example:
        >>> # 上下文管理器用法
        >>> async with get_async_db_session() as db:
        # 异步等待操作完成
        ...     result = await db.execute(select(User))
        >>> # FastAPI 依赖注入用法
        >>> @app.get("/items")
        ... async def list_items(db: AsyncSession = Depends(get_async_db)):
        ...     ...
    """
    async with AsyncSessionLocal() as db:
        # 异常处理：处理业务逻辑
        try:
            # 生成器产出值
            yield db
            # 异步等待操作完成
            await db.commit()
        # 捕获异常：处理业务逻辑
        except Exception:
            # 异步等待操作完成
            await db.rollback()
            raise


# 初始化变量 get_async_db
get_async_db = get_async_db_session


async def dispose_engines() -> None:
    """释放所有数据库引擎资源，用于应用关闭时清理."""
    # 异步等待操作完成
    await async_engine.dispose()
