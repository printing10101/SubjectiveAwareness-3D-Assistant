"""数据库会话管理器单元测试.

覆盖异步会话创建、提交、回滚和资源释放等核心功能。
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.database import get_async_db_session


_error_msg = "test error"
_unexpected_msg = "unexpected error"
_custom_msg = "custom error message"


@pytest.mark.asyncio
async def test_get_async_db_session_normal_flow() -> None:
    """测试正常流程：异步会话创建、提交和关闭."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(return_value=None)

    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ):
        async with get_async_db_session() as db:
            await db.execute("SELECT 1")

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_async_db_session_rollback_on_exception() -> None:
    """测试异常流程：发生异常时自动回滚并重新抛出."""
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock(return_value=None)

    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ), pytest.raises(ValueError, match=_error_msg):
        async with get_async_db_session() as db:
            await db.execute("SELECT 1")
            raise ValueError(_error_msg)

    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_async_db_session_commit_success() -> None:
    """测试正常流程中 commit 被正确调用."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(return_value=None)

    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ):
        async with get_async_db_session() as db:
            db.add("test_object")

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_async_db_session_custom_model_operations() -> None:
    """测试在异步会话中执行模型操作后提交事务."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(return_value=None)

    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ):
        async with get_async_db_session() as db:
            db.add("model_instance")
            await db.execute("INSERT INTO test VALUES (1)")

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_async_db_session_exception_message_preserved() -> None:
    """测试原始异常信息被保留并重新抛出."""
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock(return_value=None)

    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ), pytest.raises(ValueError) as exc_info:
        async with get_async_db_session():
            raise ValueError(_custom_msg)

    assert str(exc_info.value) == _custom_msg


@pytest.mark.asyncio
async def test_get_async_db_session_rollback_called_before_close() -> None:
    """测试异常时 rollback 在会话退出前被调用."""
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock(return_value=None)

    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ), pytest.raises(RuntimeError, match=_error_msg):
        async with get_async_db_session():
            raise RuntimeError(_error_msg)

    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_async_db_session_yields_session_instance() -> None:
    """测试上下文管理器正确 yield 出异步会话实例."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(return_value=None)

    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ):
        async with get_async_db_session() as db:
            assert db is mock_session


@pytest.mark.asyncio
async def test_get_async_db_session_commit_not_called_on_error() -> None:
    """测试异常时 commit 不被调用."""
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock(return_value=None)

    with patch(
        "app.database.AsyncSessionLocal",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
    ), pytest.raises(RuntimeError, match=_unexpected_msg):
        async with get_async_db_session():
            raise RuntimeError(_unexpected_msg)

    mock_session.commit.assert_not_called()
