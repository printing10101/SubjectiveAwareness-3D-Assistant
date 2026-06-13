from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.ollama_client import (
    OllamaClient,
    RateLimitedOllamaClient,
    _build_dynamic_timeout,
    call_ollama,
    call_ollama_with_retry,
    get_client,
    get_rate_limited_client,
)


class TestBuildDynamicTimeout:
    def test_short_prompt(self):
        timeout = _build_dynamic_timeout("short prompt")
        assert timeout.connect == 5.0

    def test_long_prompt(self):
        timeout = _build_dynamic_timeout("x" * 5000)
        assert timeout.read > 120.0

    def test_connect_timeout_set(self):
        timeout = _build_dynamic_timeout("test")
        assert timeout.connect == 5.0

    def test_very_long_prompt_capped(self):
        timeout = _build_dynamic_timeout("x" * 100000)
        assert timeout.read <= 300.0


class TestOllamaClient:
    @pytest.fixture
    def client(self):
        return OllamaClient()

    async def test_generate_builds_request(self, client):
        with patch.object(client.client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "test response"}
            mock_post.return_value = mock_response

            result = await client.generate("test prompt")
            assert result == "test response"

    async def test_generate_with_system_prompt(self, client):
        with patch.object(client.client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "response"}
            mock_post.return_value = mock_response

            await client.generate("prompt", system_prompt="system")
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["json"]["system"] == "system"

    async def test_generate_with_custom_model(self, client):
        with patch.object(client.client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "ok"}
            mock_post.return_value = mock_response

            await client.generate("prompt", model="custom-model")
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["json"]["model"] == "custom-model"

    async def test_generate_http_error(self, client):
        with patch.object(client.client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=httpx.Request("POST", "http://test.com"),
                response=httpx.Response(500),
            )
            mock_post.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                await client.generate("test prompt")

    async def test_generate_timeout(self, client):
        with patch.object(client.client, "post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException(
                "timeout",
                request=httpx.Request("POST", "http://test.com"),
            )

            with pytest.raises(httpx.TimeoutException):
                await client.generate("test prompt")

    async def test_generate_json_success(self, client):
        with patch.object(client, "generate") as mock_generate:
            mock_generate.return_value = '{"key": "value"}'
            result = await client.generate_json("prompt")
            assert result == {"key": "value"}

    async def test_generate_json_list_response(self, client):
        with patch.object(client, "generate") as mock_generate:
            mock_generate.return_value = '[{"id": 1}, {"id": 2}]'
            result = await client.generate_json("prompt")
            assert result == [{"id": 1}, {"id": 2}]

    async def test_generate_json_with_field(self, client):
        with patch.object(client, "generate") as mock_generate:
            mock_generate.return_value = (
                '{"data": {"score": 8}, "extra": "info"}'
            )
            result = await client.generate_json("prompt", field="data")
            assert result == {"score": 8}

    async def test_generate_json_invalid_response(self, client):
        with patch.object(client, "generate") as mock_generate:
            mock_generate.return_value = "just plain text"
            result = await client.generate_json("prompt")
            assert result == {}

    async def test_list_models_success(self, client):
        with patch.object(client.client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [{"name": "model1"}, {"name": "model2"}]
            }
            mock_get.return_value = mock_response

            models = await client.list_models()
            assert len(models) == 2
            assert models[0]["name"] == "model1"

    async def test_list_models_empty(self, client):
        with patch.object(client.client, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("connection failed")
            models = await client.list_models()
            assert models == []

    async def test_check_health_available(self, client):
        with patch.object(client.client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            assert await client.check_health() is True

    async def test_check_health_unavailable(self, client):
        with patch.object(client.client, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("connection failed")
            assert await client.check_health() is False

    async def test_check_model_available(self, client):
        with patch.object(client, "list_models") as mock_list:
            mock_list.return_value = [
                {"name": "deepseek-r1:7b"}, {"name": "llama2"}
            ]
            result = await client.check_model_available("deepseek-r1:7b")
            assert result is True

    async def test_check_model_unavailable(self, client):
        with patch.object(client, "list_models") as mock_list:
            mock_list.return_value = [{"name": "llama2"}]
            result = await client.check_model_available("deepseek-r1:7b")
            assert result is False

    async def test_close(self, client):
        with patch.object(client.client, "aclose") as mock_aclose:
            await client.close()
            mock_aclose.assert_called_once()


class TestRateLimitedOllamaClient:
    @pytest.fixture
    def client(self):
        return RateLimitedOllamaClient()

    def test_initial_queue_size_zero(self, client):
        assert client.queue_size == 0

    def test_average_queue_size_zero(self, client):
        assert client.average_queue_size == 0.0

    async def test_start_stop_worker(self, client):
        client.start_worker()
        assert client._is_running is True
        assert client._worker_task is not None

        await client.stop_worker()
        assert client._is_running is False
        assert client._worker_task is None


class TestModuleFunctions:
    async def test_call_ollama(self):
        with patch("app.services.ollama_client.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(return_value="response")
            mock_get.return_value = mock_client

            result = await call_ollama("test")
            assert result == "response"

    async def test_call_ollama_with_retry_success(self):
        with patch(
            "app.services.ollama_client.call_ollama",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = '{"result": "ok"}'
            result = await call_ollama_with_retry("prompt")
            assert '{"result": "ok"}' in result

    async def test_get_client_singleton(self):
        c1 = get_client()
        c2 = get_client()
        assert c1 is c2

    async def test_get_rate_limited_client_singleton(self):
        c1 = get_rate_limited_client()
        c2 = get_rate_limited_client()
        assert c1 is c2
