"""数据库会话管理器单元测试.

覆盖异步会话创建、提交、回滚和资源释放等核心功能。
"""

# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, patch

# 导入模块: pytest
import pytest

# 导入模块: from app.database
from app.database import get_async_db_session


_error_msg = "test error"
_unexpected_msg = "unexpected error"
_custom_msg = "custom error message"


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_async_db_session_normal_flow() -> None:
    """测试正常流程：异步会话创建、提交和关闭."""
    # 初始化变量 mock_session
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(return_value=None)

    # 使用上下文管理器管理资源
    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ):
        async with get_async_db_session() as db:
            # 异步等待操作完成
            await db.execute("SELECT 1")

    mock_session.commit.assert_awaited_once()


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_async_db_session_rollback_on_exception() -> None:
    """测试异常流程：发生异常时自动回滚并重新抛出."""
    # 初始化变量 mock_session
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock(return_value=None)

    # 使用上下文管理器管理资源
    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ), pytest.raises(ValueError, match=_error_msg):
        async with get_async_db_session() as db:
            # 异步等待操作完成
            await db.execute("SELECT 1")
            # 抛出异常，处理错误情况
            raise ValueError(_error_msg)

    mock_session.rollback.assert_awaited_once()


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_async_db_session_commit_success() -> None:
    """测试正常流程中 commit 被正确调用."""
    # 初始化变量 mock_session
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(return_value=None)

    # 使用上下文管理器管理资源
    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ):
        async with get_async_db_session() as db:
            db.add("test_object")

    mock_session.commit.assert_awaited_once()


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_async_db_session_custom_model_operations() -> None:
    """测试在异步会话中执行模型操作后提交事务."""
    # 初始化变量 mock_session
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(return_value=None)

    # 使用上下文管理器管理资源
    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ):
        async with get_async_db_session() as db:
            db.add("model_instance")
            # 异步等待操作完成
            await db.execute("INSERT INTO test VALUES (1)")

    mock_session.commit.assert_awaited_once()


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_async_db_session_exception_message_preserved() -> None:
    """测试原始异常信息被保留并重新抛出."""
    # 初始化变量 mock_session
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock(return_value=None)

    # 使用上下文管理器管理资源
    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ), pytest.raises(ValueError) as exc_info:
        async with get_async_db_session():
            # 抛出异常，处理错误情况
            raise ValueError(_custom_msg)

    assert str(exc_info.value) == _custom_msg


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_async_db_session_rollback_called_before_close() -> None:
    """测试异常时 rollback 在会话退出前被调用."""
    # 初始化变量 mock_session
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock(return_value=None)

    # 使用上下文管理器管理资源
    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ), pytest.raises(RuntimeError, match=_error_msg):
        async with get_async_db_session():
            # 抛出异常，处理错误情况
            raise RuntimeError(_error_msg)

    mock_session.rollback.assert_awaited_once()


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_async_db_session_yields_session_instance() -> None:
    """测试上下文管理器正确 yield 出异步会话实例."""
    # 初始化变量 mock_session
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(return_value=None)

    # 使用上下文管理器管理资源
    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ):
        async with get_async_db_session() as db:
            assert db is mock_session


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_async_db_session_commit_not_called_on_error() -> None:
    """测试异常时 commit 不被调用."""
    # 初始化变量 mock_session
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock(return_value=None)

    # 使用上下文管理器管理资源
    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ), pytest.raises(RuntimeError, match=_unexpected_msg):
        async with get_async_db_session():
            # 抛出异常，处理错误情况
            raise RuntimeError(_unexpected_msg)

    mock_session.commit.assert_not_called()
