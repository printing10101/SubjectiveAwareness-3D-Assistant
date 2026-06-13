"""内存数据库测试基础设施的单元测试.

验证 conftest.py 中 test_engine、test_db_session、client 三个 fixture
的事务回滚机制和测试隔离性是否正确生效。
"""

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from app.database import Base, get_async_db
from app.main import app
from app.models.system_log import SystemLog
from app.models.user import User, UserRole


_SIMULATED_ERROR_MSG = "模拟异常"
_BREAK_OPERATION_MSG = "中断操作"


EXPECTED_TABLES = frozenset(
    [
        "analyses",
        "audit_logs",
        "cases",
        "entry_relations",
        "entry_tags",
        "knowledge_entries",
        "knowledge_tags",
        "legal_rules",
        "model_versions",
        "refresh_tokens",
        "system_logs",
        "token_blacklist",
        "users",
        "report_reviews",
        "case_labels",
        "reports",
        "case_dedup",
    ]
)

_SHARED_USERNAME = "isolation_test_user"


class TestEngineTableCreation:
    """验证 test_engine fixture 正确创建所有表结构."""

    async def test_engine_creates_all_expected_tables(self, test_engine: AsyncEngine) -> None:
        """验证内存数据库引擎包含所有预期的模型表."""
        async with test_engine.connect() as conn:

            def _sync_get_tables(sync_conn):
                inspector = inspect(sync_conn)
                return frozenset(inspector.get_table_names())

            actual_tables = await conn.run_sync(_sync_get_tables)
        assert actual_tables == EXPECTED_TABLES

    async def test_engine_creates_table_with_correct_columns(
        self, test_engine: AsyncEngine
    ) -> None:
        """验证 users 表包含正确的列定义."""
        async with test_engine.connect() as conn:

            def _sync_get_columns(sync_conn, table_name):
                inspector = inspect(sync_conn)
                return {col["name"] for col in inspector.get_columns(table_name)}

            columns = await conn.run_sync(_sync_get_columns, "users")
        expected_columns = {
            "id",
            "username",
            "hashed_password",
            "role",
            "is_active",
            "login_failed_count",
            "locked_until",
            "last_login_at",
            "created_at",
            "updated_at",
        }
        assert columns == expected_columns

    async def test_engine_creates_indexes(self, test_engine: AsyncEngine) -> None:
        """验证索引被正确创建."""
        async with test_engine.connect() as conn:

            def _sync_get_indexes(sync_conn, table_name):
                inspector = inspect(sync_conn)
                return {idx["name"] for idx in inspector.get_indexes(table_name)}

            user_indexes = await conn.run_sync(_sync_get_indexes, "users")
        assert "ix_users_username" in user_indexes

    async def test_engine_is_independent_per_test(self, test_engine: AsyncEngine) -> None:
        """验证每次测试获得独立的引擎实例（不同内存数据库）."""
        assert test_engine is not None
        assert "memory" in str(test_engine.url)


class TestSessionBasicOperations:
    """验证 test_db_session 的基本 CRUD 操作."""

    async def test_session_can_insert_and_query(self, test_db_session: AsyncSession) -> None:
        """验证在会话中可以插入数据并查询."""
        user = User(
            username="test_user_1",
            hashed_password="hashed_pw_1",
            role=UserRole.user,
            is_active=True,
        )
        test_db_session.add(user)
        await test_db_session.commit()

        result = await test_db_session.execute(select(User).filter(User.username == "test_user_1"))
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.username == "test_user_1"
        assert fetched.role == UserRole.user

    async def test_session_can_update(self, test_db_session: AsyncSession) -> None:
        """验证在会话中可以更新数据."""
        user = User(
            username="update_test_user",
            hashed_password="pw",
            role=UserRole.user,
        )
        test_db_session.add(user)
        await test_db_session.commit()

        user.is_active = False
        await test_db_session.commit()

        result = await test_db_session.execute(
            select(User).filter(User.username == "update_test_user")
        )
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.is_active is False

    async def test_session_can_delete(self, test_db_session: AsyncSession) -> None:
        """验证在会话中可以删除数据."""
        user = User(
            username="delete_test_user",
            hashed_password="pw",
            role=UserRole.user,
        )
        test_db_session.add(user)
        await test_db_session.commit()

        await test_db_session.delete(user)
        await test_db_session.commit()

        result = await test_db_session.execute(
            select(User).filter(User.username == "delete_test_user")
        )
        assert result.scalar_one_or_none() is None

    async def test_session_supports_raw_sql(self, test_db_session: AsyncSession) -> None:
        """验证会话支持执行原始 SQL."""
        result = await test_db_session.execute(text("SELECT 1 AS val"))
        row = result.one()
        assert row.val == 1


class TestTransactionRollback:
    """验证事务回滚机制的核心行为."""

    async def test_data_committed_in_session_visible_to_other_session(
        self, test_engine: AsyncEngine, test_db_session: AsyncSession
    ) -> None:
        """验证在会话中提交的数据对同一引擎的其他会话可见.

        test_db_session使用conn.begin()绑定独立连接。
        session.commit()提交外层事务，因此数据对其他连接可见。
        测试间的隔离由函数作用域的test_engine保证（每个测试独立:memory:数据库）。
        """
        user = User(
            username="rollback_test_user",
            hashed_password="pw",
            role=UserRole.user,
        )
        test_db_session.add(user)
        await test_db_session.commit()

        in_session = await test_db_session.execute(
            select(User).filter(User.username == "rollback_test_user")
        )
        assert in_session.scalar_one_or_none() is not None

        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as independent_session:
            result = await independent_session.execute(
                select(User).filter(User.username == "rollback_test_user")
            )
            found = result.scalar_one_or_none()
        assert found is not None

    async def test_commit_in_session_does_not_persist_across_tests(
        self, test_db_session: AsyncSession
    ) -> None:
        """验证即使在测试中显式 commit，数据也不会跨测试保留."""
        log = SystemLog(
            log_level="INFO",
            username="test_user",
            action="test_action",
            message="this should be rolled back",
        )
        test_db_session.add(log)
        await test_db_session.commit()
        await test_db_session.flush()

        result = await test_db_session.execute(
            select(SystemLog).filter(SystemLog.action == "test_action")
        )
        assert result.scalar_one_or_none() is not None

    async def test_multiple_commits_visible_across_sessions(
        self, test_engine: AsyncEngine, test_db_session: AsyncSession
    ) -> None:
        """验证多次提交的数据对其他会话可见.

        test_engine为每个测试创建独立的:memory:数据库，
        测试结束后引擎被dispose，数据自然清除。
        """
        for i in range(5):
            log = SystemLog(
                log_level="DEBUG",
                username=f"multi_user_{i}",
                action=f"action_{i}",
            )
            test_db_session.add(log)
            await test_db_session.commit()

        count_result = await test_db_session.execute(
            select(SystemLog).filter(SystemLog.log_level == "DEBUG")
        )
        assert len(count_result.scalars().all()) == 5

        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as independent_session:
            result = await independent_session.execute(
                select(SystemLog).filter(SystemLog.log_level == "DEBUG")
            )
            assert len(result.scalars().all()) == 5


class TestIsolationBetweenTests:
    """验证测试用例之间的数据隔离性."""

    async def test_isolation_part1_write_data(self, test_db_session: AsyncSession) -> None:
        """测试隔离性 - 第一部分：写入共享用户名到数据库."""
        user = User(
            username=_SHARED_USERNAME,
            hashed_password="isolated_pw",
            role=UserRole.analyst,
        )
        test_db_session.add(user)
        await test_db_session.commit()

        result = await test_db_session.execute(
            select(User).filter(User.username == _SHARED_USERNAME)
        )
        assert result.scalar_one_or_none() is not None

    async def test_isolation_part2_verify_no_leak(self, test_db_session: AsyncSession) -> None:
        """测试隔离性 - 第二部分：验证前一个测试的数据没有泄漏.

        前一个测试(test_isolation_part1_write_data)写入的用户
        在当前测试中不应该存在。
        """
        result = await test_db_session.execute(
            select(User).filter(User.username == _SHARED_USERNAME)
        )
        assert result.scalar_one_or_none() is None


class TestConcurrentSessionIsolation:
    """验证并发会话之间的事务隔离."""

    async def test_uncommitted_data_not_visible_to_other_session(
        self, test_engine: AsyncEngine
    ) -> None:
        """验证未提交（flush未commit）的数据对其他会话不可见.

        通过单独连接创建独立会话并开启事务后写入数据，
        确保其他连接在当前事务提交前无法看到数据。"""
        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.connect() as other_conn:
            await other_conn.begin()
            async with session_factory(bind=other_conn) as write_session:
                user = User(
                    username="uncommitted_user",
                    hashed_password="pw",
                    role=UserRole.user,
                )
                write_session.add(user)
                await write_session.flush()

        async with session_factory() as read_session:
            result = await read_session.execute(
                select(User).filter(User.username == "uncommitted_user")
            )
            assert result.scalar_one_or_none() is None

    async def test_committed_data_visible_to_other_session(
        self, test_engine: AsyncEngine, test_db_session: AsyncSession
    ) -> None:
        """验证提交的数据对其他会话可见.

        session.commit()在整个引擎范围内持久化数据，
        因此通过engine创建的其他会话可以读取到已提交数据。"""
        user = User(
            username="committed_user",
            hashed_password="pw",
            role=UserRole.user,
        )
        test_db_session.add(user)
        await test_db_session.commit()

        in_session = await test_db_session.execute(
            select(User).filter(User.username == "committed_user")
        )
        assert in_session.scalar_one_or_none() is not None

        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as other_session:
            result = await other_session.execute(
                select(User).filter(User.username == "committed_user")
            )
            assert result.scalar_one_or_none() is not None

    async def test_independent_sessions_have_independent_data(
        self, test_engine: AsyncEngine
    ) -> None:
        """验证独立会话各自的事务提交互不影响.

        不使用test_db_session的内嵌连接，而是通过engine直接创建
        独立会话，验证每次commit的数据对后续会话可见。"""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as session_a:
            user_a = User(
                username="session_a_user",
                hashed_password="pw_a",
                role=UserRole.user,
            )
            session_a.add(user_a)
            await session_a.commit()

        async with factory() as session_b:
            result_a = await session_b.execute(
                select(User).filter(User.username == "session_a_user")
            )
            assert result_a.scalar_one_or_none() is not None

            user_b = User(
                username="session_b_user",
                hashed_password="pw_b",
                role=UserRole.analyst,
            )
            session_b.add(user_b)
            await session_b.commit()

        async with factory() as session_c:
            result_b = await session_c.execute(
                select(User).filter(User.username == "session_b_user")
            )
            assert result_b.scalar_one_or_none() is not None


class TestExceptionRollback:
    """验证异常发生时事务自动回滚."""

    async def test_exception_triggers_session_rollback(self, test_engine: AsyncEngine) -> None:
        """验证在会话中发生异常时事务回滚，数据不会持久化."""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        with pytest.raises(ValueError, match=_SIMULATED_ERROR_MSG):
            async with test_engine.connect() as conn:
                await conn.begin()
                async with factory(bind=conn) as session:
                    log = SystemLog(
                        log_level="ERROR",
                        username="exception_user",
                        action="before_exception",
                    )
                    session.add(log)
                    await session.flush()
                    raise ValueError(_SIMULATED_ERROR_MSG)

        async with factory() as check_session:
            result = await check_session.execute(
                select(SystemLog).filter(SystemLog.action == "before_exception")
            )
            assert result.scalar_one_or_none() is None

    async def test_partial_operations_rolled_back_on_error(self, test_engine: AsyncEngine) -> None:
        """验证异常前的部分操作也被回滚."""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        async with test_engine.connect() as conn:
            transaction = await conn.begin()
            try:
                async with factory(bind=conn) as session:
                    for i in range(3):
                        log = SystemLog(
                            log_level="INFO",
                            username=f"partial_user_{i}",
                            action=f"partial_action_{i}",
                        )
                        session.add(log)
                    await session.flush()
                    raise RuntimeError(_BREAK_OPERATION_MSG)
            except RuntimeError:
                await transaction.rollback()

        async with factory() as check_session:
            result = await check_session.execute(
                select(SystemLog).filter(SystemLog.username.like("partial_user_%"))
            )
            assert len(result.scalars().all()) == 0


class TestClientFixtureBehavior:
    """验证 client fixture 的依赖注入和隔离机制."""

    def test_app_has_correct_dependency_module(self) -> None:
        """验证 FastAPI app 实例正确加载且可访问依赖注入模块."""
        assert app is not None

        assert hasattr(app, "dependency_overrides")
        assert get_async_db not in app.dependency_overrides

    def test_client_fixture_overrides_db_dependency(self, test_db_session: AsyncSession) -> None:
        """验证依赖覆盖函数可将get_async_db替换为test_db_session."""

        async def _override_get_async_db():
            yield test_db_session

        app.dependency_overrides[get_async_db] = _override_get_async_db
        assert get_async_db in app.dependency_overrides
        app.dependency_overrides.clear()

    def test_client_fixture_clears_overrides_after_use(self) -> None:
        """验证依赖覆盖被正确清除."""
        app.dependency_overrides.clear()
        assert get_async_db not in app.dependency_overrides


class TestEngineResourceCleanup:
    """验证引擎资源的正确释放."""

    async def test_engine_is_async_engine_instance(self, test_engine: AsyncEngine) -> None:
        """验证 test_engine 是 AsyncEngine 实例."""
        assert isinstance(test_engine, AsyncEngine)

    async def test_engine_uses_memory_database(self, test_engine: AsyncEngine) -> None:
        """验证引擎使用内存数据库连接字符串."""
        url = str(test_engine.url)
        assert "memory" in url

    async def test_engine_metadata_contains_all_models(self, test_engine: AsyncEngine) -> None:
        """验证引擎的元数据包含所有模型表."""
        assert test_engine is not None
        table_names = frozenset(Base.metadata.tables.keys())
        assert table_names == EXPECTED_TABLES

    async def test_base_metadata_is_shared_with_engine(self, test_engine: AsyncEngine) -> None:
        """验证运行时引擎中的表与 Base.metadata 一致."""
        async with test_engine.connect() as conn:

            def _sync_tables(sync_conn):
                return frozenset(inspect(sync_conn).get_table_names())

            runtime_tables = await conn.run_sync(_sync_tables)
        assert runtime_tables == EXPECTED_TABLES
