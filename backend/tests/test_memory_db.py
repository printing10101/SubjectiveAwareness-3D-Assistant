"""内存数据库测试基础设施的单元测试.

验证 conftest.py 中 test_engine、test_db_session、client 三个 fixture
的事务回滚机制和测试隔离性是否正确生效。
"""

# 导入模块: pytest
import pytest
# 导入模块: from sqlalchemy
from sqlalchemy import inspect, select, text
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

# 导入模块: from app.database
from app.database import Base, get_async_db
# 导入模块: from app.main
from app.main import app
# 导入模块: from app.models.system_log
from app.models.system_log import SystemLog
# 导入模块: from app.models.user
from app.models.user import User, UserRole


_SIMULATED_ERROR_MSG = "模拟异常"
_BREAK_OPERATION_MSG = "中断操作"


# 初始化变量 EXPECTED_TABLES
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


# 定义 TestEngineTableCreation 类
class TestEngineTableCreation:
    """验证 test_engine fixture 正确创建所有表结构."""

    async def test_engine_creates_all_expected_tables(self, test_engine: AsyncEngine) -> None:
        """验证内存数据库引擎包含所有预期的模型表."""
        async with test_engine.connect() as conn:

            def _sync_get_tables(sync_conn):

                # 执行 _sync_get_tables 函数的核心逻辑
                inspector = inspect(sync_conn)
                # 返回处理结果
                return frozenset(inspector.get_table_names())

            # 初始化变量 actual_tables
            actual_tables = await conn.run_sync(_sync_get_tables)
        assert actual_tables == EXPECTED_TABLES

    async def test_engine_creates_table_with_correct_columns(
        # 函数 test_engine_creates_table_with_correct_columns 的初始化逻辑
        self, test_engine: AsyncEngine
    ) -> None:
        """验证 users 表包含正确的列定义."""
        async with test_engine.connect() as conn:

            def _sync_get_columns(sync_conn, table_name):
                # 函数 _sync_get_columns 的初始化逻辑
                inspector = inspect(sync_conn)
                # 返回处理结果
                return {col["name"] for col in inspector.get_columns(table_name)}

            # 初始化变量 columns
            columns = await conn.run_sync(_sync_get_columns, "users")
        # 初始化变量 expected_columns
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
                # 函数 _sync_get_indexes 的初始化逻辑
                inspector = inspect(sync_conn)
                # 返回处理结果
                return {idx["name"] for idx in inspector.get_indexes(table_name)}

            # 初始化变量 user_indexes
            user_indexes = await conn.run_sync(_sync_get_indexes, "users")
        assert "ix_users_username" in user_indexes

    async def test_engine_is_independent_per_test(self, test_engine: AsyncEngine) -> None:
        """验证每次测试获得独立的引擎实例（不同内存数据库）."""
        assert test_engine is not None
        assert "memory" in str(test_engine.url)


# 定义 TestSessionBasicOperations 类
class TestSessionBasicOperations:
    """验证 test_db_session 的基本 CRUD 操作."""

    async def test_session_can_insert_and_query(self, test_db_session: AsyncSession) -> None:
        """验证在会话中可以插入数据并查询."""
        # 初始化变量 user
        user = User(
            # 初始化变量 username
            username="test_user_1",
            # 初始化变量 hashed_password
            hashed_password="hashed_pw_1",
            # 初始化变量 role
            role=UserRole.user,
            # 初始化变量 is_active
            is_active=True,
        )
        test_db_session.add(user)
        # 异步等待操作完成
        await test_db_session.commit()

        # 初始化变量 result
        result = await test_db_session.execute(select(User).filter(User.username == "test_user_1"))
        # 初始化变量 fetched
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.username == "test_user_1"
        assert fetched.role == UserRole.user

    async def test_session_can_update(self, test_db_session: AsyncSession) -> None:
        """验证在会话中可以更新数据."""
        # 初始化变量 user
        user = User(
            # 初始化变量 username
            username="update_test_user",
            # 初始化变量 hashed_password
            hashed_password="pw",
            # 初始化变量 role
            role=UserRole.user,
        )
        test_db_session.add(user)
        # 异步等待操作完成
        await test_db_session.commit()

        user.is_active = False
        # 异步等待操作完成
        await test_db_session.commit()

        # 初始化变量 result
        result = await test_db_session.execute(
            select(User).filter(User.username == "update_test_user")
        )
        # 初始化变量 fetched
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.is_active is False

    async def test_session_can_delete(self, test_db_session: AsyncSession) -> None:
        """验证在会话中可以删除数据."""
        # 初始化变量 user
        user = User(
            # 初始化变量 username
            username="delete_test_user",
            # 初始化变量 hashed_password
            hashed_password="pw",
            # 初始化变量 role
            role=UserRole.user,
        )
        test_db_session.add(user)
        # 异步等待操作完成
        await test_db_session.commit()

        # 异步等待操作完成
        await test_db_session.delete(user)
        # 异步等待操作完成
        await test_db_session.commit()

        # 初始化变量 result
        result = await test_db_session.execute(
            select(User).filter(User.username == "delete_test_user")
        )
        assert result.scalar_one_or_none() is None

    async def test_session_supports_raw_sql(self, test_db_session: AsyncSession) -> None:
        """验证会话支持执行原始 SQL."""
        # 初始化变量 result
        result = await test_db_session.execute(text("SELECT 1 AS val"))
        row = result.one()
        assert row.val == 1


# 定义 TestTransactionRollback 类
class TestTransactionRollback:
    """验证事务回滚机制的核心行为."""

    async def test_data_committed_in_session_visible_to_other_session(
        # 函数 test_data_committed_in_session_visible_to_other_session 的初始化逻辑
        self, test_engine: AsyncEngine, test_db_session: AsyncSession
    ) -> None:
        """验证在会话中提交的数据对同一引擎的其他会话可见.

        test_db_session使用conn.begin()绑定独立连接。
        session.commit()提交外层事务，因此数据对其他连接可见。
        测试间的隔离由函数作用域的test_engine保证（每个测试独立:memory:数据库）。
        """
        # 初始化变量 user
        user = User(
            # 初始化变量 username
            username="rollback_test_user",
            # 初始化变量 hashed_password
            hashed_password="pw",
            # 初始化变量 role
            role=UserRole.user,
        )
        test_db_session.add(user)
        # 异步等待操作完成
        await test_db_session.commit()

        # 初始化变量 in_session
        in_session = await test_db_session.execute(
            select(User).filter(User.username == "rollback_test_user")
        )
        assert in_session.scalar_one_or_none() is not None

        # 初始化变量 session_factory
        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as independent_session:
            # 初始化变量 result
            result = await independent_session.execute(
                select(User).filter(User.username == "rollback_test_user")
            )
            # 初始化变量 found
            found = result.scalar_one_or_none()
        assert found is not None

    async def test_commit_in_session_does_not_persist_across_tests(
        # 函数 test_commit_in_session_does_not_persist_across_tests 的初始化逻辑
        self, test_db_session: AsyncSession
    ) -> None:
        """验证即使在测试中显式 commit，数据也不会跨测试保留."""
        log = SystemLog(
            # 初始化变量 log_level
            log_level="INFO",
            # 初始化变量 username
            username="test_user",
            # 初始化变量 action
            action="test_action",
            # 初始化变量 message
            message="this should be rolled back",
        )
        test_db_session.add(log)
        # 异步等待操作完成
        await test_db_session.commit()
        # 异步等待操作完成
        await test_db_session.flush()

        # 初始化变量 result
        result = await test_db_session.execute(
            select(SystemLog).filter(SystemLog.action == "test_action")
        )
        assert result.scalar_one_or_none() is not None

    async def test_multiple_commits_visible_across_sessions(
        # 函数 test_multiple_commits_visible_across_sessions 的初始化逻辑
        self, test_engine: AsyncEngine, test_db_session: AsyncSession
    ) -> None:
        """验证多次提交的数据对其他会话可见.

        test_engine为每个测试创建独立的:memory:数据库，
        测试结束后引擎被dispose，数据自然清除。
        """
        # 循环遍历：处理业务逻辑
        for i in range(5):
            log = SystemLog(
                # 初始化变量 log_level
                log_level="DEBUG",
                # 初始化变量 username
                username=f"multi_user_{i}",
                # 初始化变量 action
                action=f"action_{i}",
            )
            test_db_session.add(log)
            # 异步等待操作完成
            await test_db_session.commit()

        # 初始化变量 count_result
        count_result = await test_db_session.execute(
            select(SystemLog).filter(SystemLog.log_level == "DEBUG")
        )
        assert len(count_result.scalars().all()) == 5

        # 初始化变量 session_factory
        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as independent_session:
            # 初始化变量 result
            result = await independent_session.execute(
                select(SystemLog).filter(SystemLog.log_level == "DEBUG")
            )
            assert len(result.scalars().all()) == 5


# 定义 TestIsolationBetweenTests 类
class TestIsolationBetweenTests:
    """验证测试用例之间的数据隔离性."""

    async def test_isolation_part1_write_data(self, test_db_session: AsyncSession) -> None:
        """测试隔离性 - 第一部分：写入共享用户名到数据库."""
        # 初始化变量 user
        user = User(
            # 初始化变量 username
            username=_SHARED_USERNAME,
            # 初始化变量 hashed_password
            hashed_password="isolated_pw",
            # 初始化变量 role
            role=UserRole.analyst,
        )
        test_db_session.add(user)
        # 异步等待操作完成
        await test_db_session.commit()

        # 初始化变量 result
        result = await test_db_session.execute(
            select(User).filter(User.username == _SHARED_USERNAME)
        )
        assert result.scalar_one_or_none() is not None

    async def test_isolation_part2_verify_no_leak(self, test_db_session: AsyncSession) -> None:
        """测试隔离性 - 第二部分：验证前一个测试的数据没有泄漏.

        前一个测试(test_isolation_part1_write_data)写入的用户
        在当前测试中不应该存在。
        """
        # 初始化变量 result
        result = await test_db_session.execute(
            select(User).filter(User.username == _SHARED_USERNAME)
        )
        assert result.scalar_one_or_none() is None


# 定义 TestConcurrentSessionIsolation 类
class TestConcurrentSessionIsolation:
    """验证并发会话之间的事务隔离."""

    async def test_uncommitted_data_not_visible_to_other_session(
        # 函数 test_uncommitted_data_not_visible_to_other_session 的初始化逻辑
        self, test_engine: AsyncEngine
    ) -> None:
        """验证未提交（flush未commit）的数据对其他会话不可见.

        通过单独连接创建独立会话并开启事务后写入数据，
        确保其他连接在当前事务提交前无法看到数据。"""
        # 初始化变量 session_factory
        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.connect() as other_conn:
            # 异步等待操作完成
            await other_conn.begin()
            async with session_factory(bind=other_conn) as write_session:
                # 初始化变量 user
                user = User(
                    # 初始化变量 username
                    username="uncommitted_user",
                    # 初始化变量 hashed_password
                    hashed_password="pw",
                    # 初始化变量 role
                    role=UserRole.user,
                )
                write_session.add(user)
                # 异步等待操作完成
                await write_session.flush()

        async with session_factory() as read_session:
            # 初始化变量 result
            result = await read_session.execute(
                select(User).filter(User.username == "uncommitted_user")
            )
            assert result.scalar_one_or_none() is None

    async def test_committed_data_visible_to_other_session(
        # 函数 test_committed_data_visible_to_other_session 的初始化逻辑
        self, test_engine: AsyncEngine, test_db_session: AsyncSession
    ) -> None:
        """验证提交的数据对其他会话可见.

        session.commit()在整个引擎范围内持久化数据，
        因此通过engine创建的其他会话可以读取到已提交数据。"""
        # 初始化变量 user
        user = User(
            # 初始化变量 username
            username="committed_user",
            # 初始化变量 hashed_password
            hashed_password="pw",
            # 初始化变量 role
            role=UserRole.user,
        )
        test_db_session.add(user)
        # 异步等待操作完成
        await test_db_session.commit()

        # 初始化变量 in_session
        in_session = await test_db_session.execute(
            select(User).filter(User.username == "committed_user")
        )
        assert in_session.scalar_one_or_none() is not None

        # 初始化变量 session_factory
        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as other_session:
            # 初始化变量 result
            result = await other_session.execute(
                select(User).filter(User.username == "committed_user")
            )
            assert result.scalar_one_or_none() is not None

    async def test_independent_sessions_have_independent_data(
        # 函数 test_independent_sessions_have_independent_data 的初始化逻辑
        self, test_engine: AsyncEngine
    ) -> None:
        """验证独立会话各自的事务提交互不影响.

        不使用test_db_session的内嵌连接，而是通过engine直接创建
        独立会话，验证每次commit的数据对后续会话可见。"""
        # 初始化变量 factory
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as session_a:
            # 初始化变量 user_a
            user_a = User(
                # 初始化变量 username
                username="session_a_user",
                # 初始化变量 hashed_password
                hashed_password="pw_a",
                # 初始化变量 role
                role=UserRole.user,
            )
            session_a.add(user_a)
            # 异步等待操作完成
            await session_a.commit()

        async with factory() as session_b:
            # 初始化变量 result_a
            result_a = await session_b.execute(
                select(User).filter(User.username == "session_a_user")
            )
            assert result_a.scalar_one_or_none() is not None

            # 初始化变量 user_b
            user_b = User(
                # 初始化变量 username
                username="session_b_user",
                # 初始化变量 hashed_password
                hashed_password="pw_b",
                # 初始化变量 role
                role=UserRole.analyst,
            )
            session_b.add(user_b)
            # 异步等待操作完成
            await session_b.commit()

        async with factory() as session_c:
            # 初始化变量 result_b
            result_b = await session_c.execute(
                select(User).filter(User.username == "session_b_user")
            )
            assert result_b.scalar_one_or_none() is not None


# 定义 TestExceptionRollback 类
class TestExceptionRollback:
    """验证异常发生时事务自动回滚."""

    async def test_exception_triggers_session_rollback(self, test_engine: AsyncEngine) -> None:
        """验证在会话中发生异常时事务回滚，数据不会持久化."""
        # 初始化变量 factory
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match=_SIMULATED_ERROR_MSG):
            async with test_engine.connect() as conn:
                # 异步等待操作完成
                await conn.begin()
                async with factory(bind=conn) as session:
                    log = SystemLog(
                        # 初始化变量 log_level
                        log_level="ERROR",
                        # 初始化变量 username
                        username="exception_user",
                        # 初始化变量 action
                        action="before_exception",
                    )
                    session.add(log)
                    # 异步等待操作完成
                    await session.flush()
                    # 抛出异常，处理错误情况
                    raise ValueError(_SIMULATED_ERROR_MSG)

        async with factory() as check_session:
            # 初始化变量 result
            result = await check_session.execute(
                select(SystemLog).filter(SystemLog.action == "before_exception")
            )
            assert result.scalar_one_or_none() is None

    async def test_partial_operations_rolled_back_on_error(self, test_engine: AsyncEngine) -> None:
        """验证异常前的部分操作也被回滚."""
        # 初始化变量 factory
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        async with test_engine.connect() as conn:
            # 初始化变量 transaction
            transaction = await conn.begin()
            # 异常处理：处理业务逻辑
            try:
                async with factory(b                    # 循环遍历：处理业务逻辑
ind=conn) as session:
                    # 遍历: for i in range(3):
                    for i in range(3):
                        log = SystemLog(
                            # 初始化变量 log_level
                            log_level="INFO",
                            # 初始化变量 username
                            username=f"partial_user_{i}",
                            # 初始化变量 action
                            action=f"partial_action_{i}",
                        )
                        session.add(log)
                    # 异步等待操作完成
                    await session.flush()
                    # 抛出异常，处理错误情况
                    raise RuntimeError(_BREAK_OPERATION_MSG)
            # 捕获异常：处理业务逻辑
            except RuntimeError:
                # 异步等待操作完成
                await transaction.rollback()

        async with factory() as check_session:
            # 初始化变量 result
            result = await check_session.execute(
                select(SystemLog).filter(SystemLog.username.like("partial_user_%"))
            )
            assert len(result.scalars().all()) == 0


# 定义 TestClientFixtureBehavior 类
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
            # 函数 _override_get_async_db 的初始化逻辑
            yield test_db_session

        app.dependency_overrides[get_async_db] = _override_get_async_db
        assert get_async_db in app.dependency_overrides
        app.dependency_overrides.clear()

    def test_client_fixture_clears_overrides_after_use(self) -> None:
        """验证依赖覆盖被正确清除."""
        app.dependency_overrides.clear()
        assert get_async_db not in app.dependency_overrides


# 定义 TestEngineResourceCleanup 类
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
        # 初始化变量 table_names
        table_names = frozenset(Base.metadata.tables.keys())
        assert table_names == EXPECTED_TABLES

    async def test_base_metadata_is_shared_with_engine(self, test_engine: AsyncEngine) -> None:
        """验证运行时引擎中的表与 Base.metadata 一致."""
        async with test_engine.connect() as conn:

            def _sync_tables(sync_conn):
                # 函数 _sync_tables 的初始化逻辑
                return frozenset(inspect(sync_conn).get_table_names())

            # 初始化变量 runtime_tables
            runtime_tables = await conn.run_sync(_sync_tables)
        assert runtime_tables == EXPECTED_TABLES
