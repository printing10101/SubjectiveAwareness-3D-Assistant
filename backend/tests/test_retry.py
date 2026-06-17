"""重试机制单元测试.

覆盖以下场景:
  - API 调用成功场景
  - API 临时失败后重试成功场景
  - API 持续失败至重试次数耗尽场景
  - 返回无效 JSON 格式响应场景
"""

# 导入模块: json
import json
# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, patch

# 导入模块: httpx
import httpx
# 导入模块: pytest
import pytest

# 导入模块: from app.services.ollama_client
from app.services.ollama_client import call_ollama_with_retry


# 应用装饰器: pytest.fixture
@pytest.fixture
def mock_call_ollama():
    # 执行 mock_call_ollama 函数的核心逻辑
    with patch("app.services.ollama_client.call_ollama", new_callable=AsyncMock) as mock:
        # 生成器产出值
        yield mock


# 定义 TestCallOllamaWithRetry 类
class TestCallOllamaWithRetry:
    """call_ollama_with_retry 函数测试."""

    async def test_successful_call(self, mock_call_ollama: AsyncMock):
        # 函数 test_successful_call 的初始化逻辑
        mock_call_ollama.return_value = json.dumps(
            {"result": "success", "data": "test"}
        )
        # 初始化变量 result
        result = await call_ollama_with_retry("test prompt")
        assert json.loads(result) == {"result": "success", "data": "test"}
        assert mock_call_ollama.call_count == 1

    async def test_http_error_then_success(self, mock_call_ollama: AsyncMock):
        # 函数 test_http_error_then_success 的初始化逻辑
        mock_call_ollama.side_effect = [
            httpx.HTTPStatusError(
                "Server Error",
                # 初始化变量 request
                request=httpx.Request("POST", "http://test.com"),
                # 初始化变量 response
                response=httpx.Response(503),
            ),
            json.dumps({"result": "success"}),
        ]
        # 初始化变量 result
        result = await call_ollama_with_retry("test prompt")
        assert json.loads(result) == {"result": "success"}
        assert mock_call_ollama.call_count == 2

    async def test_http_error_exhausted(self, mock_call_ollama: AsyncMock):
        # 函数 test_http_error_exhausted 的初始化逻辑
        mock_call_ollama.side_effect = httpx.HTTPStatusError(
            "Server Error",
            # 初始化变量 request
            request=httpx.Request("POST", "http://test.com"),
            # 初始化变量 response
            response=httpx.Response(503),
        )
        # 使用上下文管理器管理资源
        with pytest.raises(httpx.HTTPStatusError):
            # 异步等待操作完成
            await call_ollama_with_retry("test prompt")
        assert mock_call_ollama.call_count == 3

    async def test_connection_error_then_success(self, mock_call_ollama: AsyncMock):
        # 函数 test_connection_error_then_success 的初始化逻辑
        mock_call_ollama.side_effect = [
            httpx.ConnectError("Connection refused"),
            json.dumps({"result": "success"}),
        ]
        # 初始化变量 result
        result = await call_ollama_with_retry("test prompt")
        assert json.loads(result) == {"result": "success"}
        assert mock_call_ollama.call_count == 2

    async def test_connection_error_exhausted(self, mock_call_ollama: AsyncMock):
        # 函数 test_connection_error_exhausted 的初始化逻辑
        mock_call_ollama.side_effect = httpx.ConnectError("Connection refused")
        # 使用上下文管理器管理资源
        with pytest.raises(httpx.ConnectError):
            # 异步等待操作完成
            await call_ollama_with_retry("test prompt")
        assert mock_call_ollama.call_count == 3

    async def test_invalid_json_response(self, mock_call_ollama: AsyncMock):
        # 函数 test_invalid_json_response 的初始化逻辑
        mock_call_ollama.return_value = "invalid json response"
        # 使用上下文管理器管理资源
        with pytest.raises(json.JSONDecodeError):
            # 异步等待操作完成
            await call_ollama_with_retry("test prompt")
        assert mock_call_ollama.call_count == 3

    async def test_invalid_json_then_valid(self, mock_call_ollama: AsyncMock):
        # 函数 test_invalid_json_then_valid 的初始化逻辑
        mock_call_ollama.side_effect = [
            "not json",
            json.dumps({"result": "success"}),
        ]
        # 初始化变量 result
        result = await call_ollama_with_retry("test prompt")
        assert json.loads(result) == {"result": "success"}
        assert mock_call_ollama.call_count == 2

    async def test_preserves_kwargs(self, mock_call_ollama: AsyncMock):
        # 函数 test_preserves_kwargs 的初始化逻辑
        mock_call_ollama.return_value = json.dumps({"result": "ok"})
        # 异步等待操作完成
        await call_ollama_with_retry(
            "test prompt",
            # 初始化变量 system_prompt
            system_prompt="system",
            # 初始化变量 temperature
            temperature=0.5,
        )
        mock_call_ollama.assert_called_once_with(
            "test prompt",
            # 初始化变量 system_prompt
            system_prompt="system",
            # 初始化变量 temperature
            temperature=0.5,
        )

    async def test_without_retry(self, mock_call_ollama: AsyncMock):
        # local import required for mock patching to work correctly
        from app.services.ollama_client import call_ollama  # noqa: PLC0415

        mock_call_ollama.return_value = "plain text response"
        # 初始化变量 result
        result = await call_ollama("test prompt")
        assert result == "plain text response"
        assert mock_call_ollama.call_count == 1
