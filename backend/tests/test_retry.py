"""重试机制单元测试.

覆盖以下场景:
  - API 调用成功场景
  - API 临时失败后重试成功场景
  - API 持续失败至重试次数耗尽场景
  - 返回无效 JSON 格式响应场景
"""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.ollama_client import call_ollama_with_retry


@pytest.fixture
def mock_call_ollama():
    with patch("app.services.ollama_client.call_ollama", new_callable=AsyncMock) as mock:
        yield mock


class TestCallOllamaWithRetry:
    """call_ollama_with_retry 函数测试."""

    async def test_successful_call(self, mock_call_ollama: AsyncMock):
        mock_call_ollama.return_value = json.dumps(
            {"result": "success", "data": "test"}
        )
        result = await call_ollama_with_retry("test prompt")
        assert json.loads(result) == {"result": "success", "data": "test"}
        assert mock_call_ollama.call_count == 1

    async def test_http_error_then_success(self, mock_call_ollama: AsyncMock):
        mock_call_ollama.side_effect = [
            httpx.HTTPStatusError(
                "Server Error",
                request=httpx.Request("POST", "http://test.com"),
                response=httpx.Response(503),
            ),
            json.dumps({"result": "success"}),
        ]
        result = await call_ollama_with_retry("test prompt")
        assert json.loads(result) == {"result": "success"}
        assert mock_call_ollama.call_count == 2

    async def test_http_error_exhausted(self, mock_call_ollama: AsyncMock):
        mock_call_ollama.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=httpx.Request("POST", "http://test.com"),
            response=httpx.Response(503),
        )
        with pytest.raises(httpx.HTTPStatusError):
            await call_ollama_with_retry("test prompt")
        assert mock_call_ollama.call_count == 3

    async def test_connection_error_then_success(self, mock_call_ollama: AsyncMock):
        mock_call_ollama.side_effect = [
            httpx.ConnectError("Connection refused"),
            json.dumps({"result": "success"}),
        ]
        result = await call_ollama_with_retry("test prompt")
        assert json.loads(result) == {"result": "success"}
        assert mock_call_ollama.call_count == 2

    async def test_connection_error_exhausted(self, mock_call_ollama: AsyncMock):
        mock_call_ollama.side_effect = httpx.ConnectError("Connection refused")
        with pytest.raises(httpx.ConnectError):
            await call_ollama_with_retry("test prompt")
        assert mock_call_ollama.call_count == 3

    async def test_invalid_json_response(self, mock_call_ollama: AsyncMock):
        mock_call_ollama.return_value = "invalid json response"
        with pytest.raises(json.JSONDecodeError):
            await call_ollama_with_retry("test prompt")
        assert mock_call_ollama.call_count == 3

    async def test_invalid_json_then_valid(self, mock_call_ollama: AsyncMock):
        mock_call_ollama.side_effect = [
            "not json",
            json.dumps({"result": "success"}),
        ]
        result = await call_ollama_with_retry("test prompt")
        assert json.loads(result) == {"result": "success"}
        assert mock_call_ollama.call_count == 2

    async def test_preserves_kwargs(self, mock_call_ollama: AsyncMock):
        mock_call_ollama.return_value = json.dumps({"result": "ok"})
        await call_ollama_with_retry(
            "test prompt",
            system_prompt="system",
            temperature=0.5,
        )
        mock_call_ollama.assert_called_once_with(
            "test prompt",
            system_prompt="system",
            temperature=0.5,
        )

    async def test_without_retry(self, mock_call_ollama: AsyncMock):
        # local import required for mock patching to work correctly
        from app.services.ollama_client import call_ollama  # noqa: PLC0415

        mock_call_ollama.return_value = "plain text response"
        result = await call_ollama("test prompt")
        assert result == "plain text response"
        assert mock_call_ollama.call_count == 1
