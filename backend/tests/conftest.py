"""conftest - 单元测试模块.

本模块包含帮信罪主观明知智能分析系统的测试用例，
用于验证相关功能的正确性和稳定性。

测试范围：
    - 功能验证：确保核心功能按预期工作
    - 边界测试：验证边界条件下的行为
    - 异常处理：确保异常情况的正确处理
    - 性能测试：验证系统性能指标

测试框架：pytest
依赖服务：FastAPI TestClient, 数据库测试环境

# 应用装饰器: author 帮信罪智能分析系统开发团队
@author 帮信罪智能分析系统开发团队
# 应用装饰器: version 1.0.0
@version 1.0.0
"""

# 导入模块: json
import json
# 导入模块: from collections.abc
from collections.abc import AsyncGenerator
# 导入模块: from contextlib
from contextlib import asynccontextmanager
# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, patch

# 导入模块: pytest
import pytest
# 导入模块: from fastapi.testclient
from fastapi.testclient import TestClient
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# 导入模块: from app.database
from app.database import Base, get_async_db
# 导入模块: from app.main
from app.main import app


# 初始化变量 TEST_DATABASE_URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# 应用装饰器: pytest.fixture
@pytest.fixture(scope="function")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """创建内存数据库引擎并初始化所有表结构.

    使用SQLite内存数据库(:memory:)，确保测试环境与开发/生产环境完全隔离。
    每个测试函数获得独立的数据库引擎实例，引擎在测试结束后自动释放资源。

    Args:
        无

    Yields:
        AsyncEngine: 已初始化所有表结构的异步数据库引擎

    Raises:
        SQLAlchemyError: 表结构创建失败时抛出
    """
    # 初始化变量 engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        # 初始化变量 echo
        echo=False,
        # 初始化变量 connect_args
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        # 异步等待操作完成
        await conn.run_sync(Base.metadata.create_all)

    # 尝试执行可能抛出异常的代码
    try:
        # 生成器产出值
        yield engine
    # 最终清理代码，无论是否异常都会执行
    finally:
        # 异步等待操作完成
        await engine.dispose()


# 应用装饰器: pytest.fixture
@pytest.fixture(scope="function")
async def test_db_session(
    # 函数 test_db_session 的初始化逻辑
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """提供隔离的异步数据库会话，测试结束后自动回滚事务.

    每个测试用例获得绑定到独立连接的数据库会话。
    测试间隔离性由函数作用域的test_engine保证（每个测试独立的:memory:数据库），
    测试内通过conn.begin()包装事务，确保测试结束时未提交的数据被回滚。

    # 初始化变量 会话配置为expire_on_commit
    会话配置为expire_on_commit=False和autoflush=False，
    以匹配生产环境的会话行为。

    Args:
        test_engine: 内存数据库引擎fixture

    Yields:
        AsyncSession: 绑定到独立连接的异步数据库会话
    """
    # 初始化变量 session_factory
    session_factory = async_sessionmaker(
        test_engine,
        # 初始化变量 class_
        class_=AsyncSession,
        # 初始化变量 expire_on_commit
        expire_on_commit=False,
        # 初始化变量 autoflush
        autoflush=False,
    )

    async with test_engine.connect() as conn:
        # 异步等待操作完成
        await conn.begin()
        async with session_factory(bind=conn) as session:
            # 异常处理：处理业务逻辑
            try:
                # 生成器产出值
                yield session
            # 最终清理代码，无论是否异常都会执行
            finally:
                # 异步等待操作完成
                await conn.rollback()


# 应用装饰器: pytest.fixture
@pytest.fixture(scope="function")
def client(
    # 函数 client 的初始化逻辑
    test_db_session: AsyncSession,
    # 执行 client 函数的核心逻辑
) -> AsyncGenerator[TestClient, None]:
    """创建FastAPI测试客户端，注入内存数据库会话.

    通过FastAPI的dependency_overrides机制和模块级patch，
    将所有API端点和内部函数中的数据库依赖替换为test_db_session：
    - get_async_db: 用于FastAPI Depends()的端点
    - get_async_db_session: 用于路由中直接调用的上下文管理器

    测试结束后自动清除依赖覆盖，避免影响后续测试。

    Args:
        test_db_session: 隔离的内存数据库会话fixture

    Yields:
        TestClient: 已配置内存数据库依赖注入的FastAPI测试客户端
    """

    async def _override_get_async_db() -> AsyncGenerator[AsyncSession, None]:
        # 函数 _override_get_async_db 的初始化逻辑
        yield test_db_session

    # 应用装饰器: asynccontextmanager
    @asynccontextmanager
    async def _patched_get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
        # 函数 _patched_get_async_db_session 的初始化逻辑
        yield test_db_session

    app.dependency_overrides[get_async_db] = _override_get_async_db

    async def _noop_async() -> None:
        # 函数 _noop_async 的初始化逻辑
        return None

    # 使用上下文管理器管理资源
    with (
        patch("app.database.get_async_db_session", return_value=_patched_get_async_db_session()),
        patch(
            "app.routers.cases.get_async_db_session", return_value=_patched_get_async_db_session()
        ),
        patch("app.main.ollama_startup", new_callable=AsyncMock, side_effect=_noop_async),
        patch("app.main.ollama_shutdown", new_callable=AsyncMock, side_effect=_noop_async),
        patch("app.main.pre_cache_demo_cases", new_callable=AsyncMock, side_effect=_noop_async),
        patch("app.main.create_default_admin_async", new_callable=AsyncMock, side_effect=_noop_async),
        patch("app.main.init_knowledge_base_defaults", new_callable=AsyncMock, side_effect=_noop_async),
        patch("app.main.start_lifecycle_scheduler", new_callable=AsyncMock, side_effect=_noop_async),
        patch("app.main.stop_lifecycle_scheduler", new_callable=AsyncMock, side_effect=_noop_async),
        TestClient(app) as tc,
    ):
        # 生成器产出值
        yield tc

    app.dependency_overrides.clear()


# 应用装饰器: pytest.fixture
@pytest.fixture
def mock_ollama_response() -> AsyncGenerator[AsyncMock, None]:
    """模拟 Ollama 管道分析响应（兼容 V1 和 V2 协议）.

    V1 函数（single_pass_analysis 等）期望包含 ``ground_truth_analysis``/``score`` 的 JSON；
    V2 函数（analyze_pipeline_v2 等）期望包含 ``tier`` 字段的 JSON。
    使用 side_effect 根据 prompt 内容智能返回对应格式。
    """
    # 使用上下文管理器管理资源
    with (
        patch(
            "app.services.pipeline.call_ollama_with_retry",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock,
        patch("app.routers.analysis.cache_manager") as cache_mock,
    ):
        # Mock 缓存管理器，避免返回旧缓存数据
        cache_mock.get.return_value = None
        cache_mock.set.return_value = None

        # V1 格式：包含 ground_truth_analysis + score
        v1_response = json.dumps(
            {
                "subjective_knowledge": "明知",
                "sentence": "有期徒刑一年",
                "ground_truth_analysis": {
                    "dimension1": {"score": 8.0, "reasoning": "事实清楚"},
                    "dimension2": {"score": 7.0, "reasoning": "模式匹配"},
                    "dimension3": {"score": 6.0, "reasoning": "矛盾分析"},
                },
                "fallback": False,
                "timestamp": "2024-01-01T00:00:00Z",
            }
        )
        # V2 格式：包含 tier 字段
        v2_response = json.dumps(
            {
                "tier": "T2",
                "reasoning": "事实审查维度推理过程。嫌疑人行为符合帮信罪构成要件。",
                "key_indicators": ["提供银行卡", "明知他人犯罪"],
                "triggered_rules": ["R001"],
                "pattern_match": "典型帮信罪行为模式",
                "contradictions": [],
            }
        )

        # V2 维度 prompt 关键词列表（更精确的匹配）
        v2_keywords = ("档级", "tier", "事实审查维度", "模式匹配维度", "矛盾分析维度")

        def _smart_response(*args, **kwargs):
            """根据 prompt 内容返回 V1 或 V2 格式."""
            # 初始化变量 user_prompt
            user_prompt = args[0] if args else kwargs.get("user_prompt", "")
            # 初始化变量 system_prompt
            system_prompt = args[1] if len(args) > 1 else kwargs.get("system_prompt", "")
            # 初始化变量 combined
            combined = str(user_prompt) + str(system_prompt)
            # 条件判断：处理业务逻辑
            if any(kw in combined for kw in v2_keywords):
                # 返回处理结果
                return v2_response
            # 返回处理结果
            return v1_response

        mock.side_effect = _smart_response
        # 生成器产出值
        yield mock


# 应用装饰器: pytest.fixture
@pytest.fixture
def mock_ollama_client() -> AsyncGenerator[AsyncMock, None]:
    """模拟Ollama客户端."""
    # 使用上下文管理器管理资源
    with patch("app.services.ollama_client.get_client", new_callable=AsyncMock) as mock:
        # 初始化变量 client
        client = AsyncMock()
        client.generate = AsyncMock(return_value="test response")
        client.generate_json = AsyncMock(return_value={"result": "success", "data": "test"})
        client.list_models = AsyncMock(return_value=[{"name": "test-model"}])
        client.check_health = AsyncMock(return_value=True)
        client.check_model_available = AsyncMock(return_value=True)
        mock.return_value = client
        # 生成器产出值
        yield mock


# 应用装饰器: pytest.fixture
@pytest.fixture
def sample_case_text() -> str:
    """提供示例案件文本."""
    # 返回处理结果
    return (
        "被告人张某，男，1995年出生，初中文化程度。2023年3月至5月期间，"
        "张某明知他人利用信息网络实施犯罪，仍将自己的三张银行卡提供给对方使用，"
        "帮助对方进行支付结算，流水金额共计人民币50余万元。"
        "张某从中获利人民币3000元。案发后，张某主动到公安机关投案自首。"
    )


# 应用装饰器: pytest.fixture
@pytest.fixture
def sample_analysis_result() -> dict:
    """提供示例分析结果."""
    # 返回处理结果
    return {
        "subjective_knowledge": "明知",
        "sentence": "有期徒刑一年",
        "ground_truth_analysis": {
            "dimension1": {"score": 8.0, "reasoning": "事实清楚"},
            "dimension2": {"score": 7.0, "reasoning": "模式匹配"},
            "dimension3": {"score": 6.0, "reasoning": "矛盾分析"},
        },
        "fallback": False,
        "timestamp": "2024-01-01T00:00:00Z",
    }
