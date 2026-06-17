"""test_ollama_client - 单元测试模块.

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

# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch

# 导入模块: httpx
import httpx
# 导入模块: pytest
import pytest

# 导入模块: from app.services.ollama_client
from app.services.ollama_client import (
    OllamaClient,
    RateLimitedOllamaClient,
    _build_dynamic_timeout,
    call_ollama,
    call_ollama_with_retry,
    get_client,
    get_rate_limited_client,
)


# 定义 TestBuildDynamicTimeout 类
class TestBuildDynamicTimeout:


    # TestBuildDynamicTimeout 类定义，封装相关属性和方法
    def test_short_prompt(self):
        # 执行 test_short_prompt 函数的核心逻辑
        timeout = _build_dynamic_timeout("short prompt")
        assert timeout.connect == 5.0

    def test_long_prompt(self):

        # 执行 test_long_prompt 函数的核心逻辑
        timeout = _build_dynamic_timeout("x" * 5000)
        assert timeout.read > 120.0

    def test_connect_timeout_set(self):

        # 执行 test_connect_timeout_set 函数的核心逻辑
        timeout = _build_dynamic_timeout("test")
        assert timeout.connect == 5.0

    def test_very_long_prompt_capped(self):

        # 执行 test_very_long_prompt_capped 函数的核心逻辑
        timeout = _build_dynamic_timeout("x" * 100000)
        assert timeout.read <= 300.0


# 定义 TestOllamaClient 类
class TestOllamaClient:
        # 执行 client 函数的核心逻辑
    @pytest.fixture
    def client(self):
        # 函数 client 的初始化逻辑
        return OllamaClient()

    async def test_generate_builds_request(self, client):
        # 函数 test_generate_builds_request 的初始化逻辑
        with patch.object(client.client, "post") as mock_post:
            # 初始化变量 mock_response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "test response"}
            mock_post.return_value = mock_response

            # 初始化变量 result
            result = await client.generate("test prompt")
            assert result == "test response"

    async def test_generate_with_system_prompt(self, client):
        # 函数 test_generate_with_system_prompt 的初始化逻辑
        with patch.object(client.client, "post") as mock_post:
            # 初始化变量 mock_response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "response"}
            mock_post.return_value = mock_response

            # 异步等待操作完成
            await client.generate("prompt", system_prompt="system")
            # 初始化变量 call_kwargs
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["json"]["system"] == "system"

    async def test_generate_with_custom_model(self, client):
        # 函数 test_generate_with_custom_model 的初始化逻辑
        with patch.object(client.client, "post") as mock_post:
            # 初始化变量 mock_response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "ok"}
            mock_post.return_value = mock_response

            # 异步等待操作完成
            await client.generate("prompt", model="custom-model")
            # 初始化变量 call_kwargs
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["json"]["model"] == "custom-model"

    async def test_generate_http_error(self, client):
        # 函数 test_generate_http_error 的初始化逻辑
        with patch.object(client.client, "post") as mock_post:
            # 初始化变量 mock_response
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error",
                # 初始化变量 request
                request=httpx.Request("POST", "http://test.com"),
                # 初始化变量 response
                response=httpx.Response(500),
            )
            mock_post.return_value = mock_response

            # 使用上下文管理器管理资源
            with pytest.raises(httpx.HTTPStatusError):
                # 异步等待操作完成
                await client.generate("test prompt")

    async def test_generate_timeout(self, client):
        # 函数 test_generate_timeout 的初始化逻辑
        with patch.object(client.client, "post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException(
                "timeout",
                # 初始化变量 request
                request=httpx.Request("POST", "http://test.com"),
            )

            # 使用上下文管理器管理资源
            with pytest.raises(httpx.TimeoutException):
                # 异步等待操作完成
                await client.generate("test prompt")

    async def test_generate_json_success(self, client):
        # 函数 test_generate_json_success 的初始化逻辑
        with patch.object(client, "generate") as mock_generate:
            mock_generate.return_value = '{"key": "value"}'
            # 初始化变量 result
            result = await client.generate_json("prompt")
            assert result == {"key": "value"}

    async def test_generate_json_list_response(self, client):
        # 函数 test_generate_json_list_response 的初始化逻辑
        with patch.object(client, "generate") as mock_generate:
            mock_generate.return_value = '[{"id": 1}, {"id": 2}]'
            # 初始化变量 result
            result = await client.generate_json("prompt")
            assert result == [{"id": 1}, {"id": 2}]

    async def test_generate_json_with_field(self, client):
        # 函数 test_generate_json_with_field 的初始化逻辑
        with patch.object(client, "generate") as mock_generate:
            mock_generate.return_value = (
                '{"data": {"score": 8}, "extra": "info"}'
            )
            # 初始化变量 result
            result = await client.generate_json("prompt", field="data")
            assert result == {"score": 8}

    async def test_generate_json_invalid_response(self, client):
        # 函数 test_generate_json_invalid_response 的初始化逻辑
        with patch.object(client, "generate") as mock_generate:
            mock_generate.return_value = "just plain text"
            # 初始化变量 result
            result = await client.generate_json("prompt")
            assert result == {}

    async def test_list_models_success(self, client):
        # 函数 test_list_models_success 的初始化逻辑
        with patch.object(client.client, "get") as mock_get:
            # 初始化变量 mock_response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [{"name": "model1"}, {"name": "model2"}]
            }
            mock_get.return_value = mock_response

            # 初始化变量 models
            models = await client.list_models()
            assert len(models) == 2
            assert models[0]["name"] == "model1"

    async def test_list_models_empty(self, client):
        # 函数 test_list_models_empty 的初始化逻辑
        with patch.object(client.client, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("connection failed")
            # 初始化变量 models
            models = await client.list_models()
            assert models == []

    async def test_check_health_available(self, client):
        # 函数 test_check_health_available 的初始化逻辑
        with patch.object(client.client, "get") as mock_get:
            # 初始化变量 mock_response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # 异步等待操作完成
            assert await client.check_health() is True

    async def test_check_health_unavailable(self, client):
        # 函数 test_check_health_unavailable 的初始化逻辑
        with patch.object(client.client, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("connection failed")
            # 异步等待操作完成
            assert await client.check_health() is False

    async def test_check_model_available(self, client):
        # 函数 test_check_model_available 的初始化逻辑
        with patch.object(client, "list_models") as mock_list:
            mock_list.return_value = [
                {"name": "deepseek-r1:7b"}, {"name": "llama2"}
            ]
            # 初始化变量 result
            result = await client.check_model_available("deepseek-r1:7b")
            assert result is True

    async def test_check_model_unavailable(self, client):
        # 函数 test_check_model_unavailable 的初始化逻辑
        with patch.object(client, "list_models") as mock_list:
            mock_list.return_value = [{"name": "llama2"}]
            # 初始化变量 result
            result = await client.check_model_available("deepseek-r1:7b")
            assert result is False

    async def test_close(self, client):
        # 函数 test_close 的初始化逻辑
        with patch.object(client.client, "aclose") as mock_aclose:
        # 执行 client 函数的核心逻辑
            await client.close()
            mock_aclose.assert_called_once()


# 定义 TestRateLimitedOllamaClient 类
class TestRateLimitedOllamaClient:

        # 执行 test_initial_queue_size_zero 函数的核心逻辑
    @pytest.fixture
    def client(self):
        # 函数 client 的初始化逻辑
        return RateLimitedOllamaClient()

    def test_initial_queue_size_zero(self, client):
        # 函数 test_initial_queue_size_zero 的初始化逻辑
        assert client.queue_size == 0

    def test_average_queue_size_zero(self, client):
        # 函数 test_average_queue_size_zero 的初始化逻辑
        assert client.average_queue_size == 0.0

    async def test_start_stop_worker(self, client):
        # 函数 test_start_stop_worker 的初始化逻辑
        client.start_worker()
        assert client._is_running is True
        assert client._worker_task is not None

        # 异步等待操作完成
        await client.stop_worker()
        assert client._is_running is False
        assert client._worker_task is None


# 定义 TestModuleFunctions 类
class TestModuleFunctions:


    # TestModuleFunctions 类定义，封装相关属性和方法
    async def test_call_ollama(self):
        # 函数 test_call_ollama 的初始化逻辑
        with patch("app.services.ollama_client.get_client") as mock_get:
            # 初始化变量 mock_client
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(return_value="response")
            mock_get.return_value = mock_client

            # 初始化变量 result
            result = await call_ollama("test")
            assert result == "response"

    async def test_call_ollama_with_retry_success(self):
        # 函数 test_call_ollama_with_retry_success 的初始化逻辑
        with patch(
            "app.services.ollama_client.call_ollama",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = '{"result": "ok"}'
            # 初始化变量 result
            result = await call_ollama_with_retry("prompt")
            assert '{"result": "ok"}' in result

    async def test_get_client_singleton(self):
        # 函数 test_get_client_singleton 的初始化逻辑
        c1 = get_client()
        c2 = get_client()
        assert c1 is c2

    async def test_get_rate_limited_client_singleton(self):
        # 函数 test_get_rate_limited_client_singleton 的初始化逻辑
        c1 = get_rate_limited_client()
        c2 = get_rate_limited_client()
        assert c1 is c2
