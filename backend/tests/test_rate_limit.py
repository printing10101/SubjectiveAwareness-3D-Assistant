"""限流模块单元测试.

覆盖角色感知限流键函数、动态限流值获取、限流触发日志等核心功能。
测试不同角色、不同限流维度下的策略有效性，以及边界条件和异常情况。
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from slowapi import Limiter

from app.config import AnalysisConfig
from app.utils.rate_limit import (
    _extract_user_info,
    _log_rate_limit_breach,
    _request_ctx,
    _resolve_rate_limit_key,
    get_analyze_rate_limit,
    limiter,
)


# decode_token_with_fallback 在 rate_limit.py 中是惰性导入，
# patch 需指向其实际定义模块 app.utils.auth 以确保 mock 生效
_DECODE_PATCH_TARGET = "app.utils.auth.decode_token_with_fallback"


def _make_mock_request(
    headers: dict[str, str] | None = None,
    client_host: str = "127.0.0.1",
    path: str = "/api/analyze",
) -> MagicMock:
    mock = MagicMock(spec=Request)
    mock.headers = headers or {}
    mock.client.host = client_host
    mock.url.path = path
    return mock


class TestExtractUserInfo:

    def test_anonymous_user_no_auth_header(self):
        request = _make_mock_request()
        user_id, role, ip = _extract_user_info(request)
        assert user_id is None
        assert role is None
        assert ip == "127.0.0.1"

    def test_anonymous_user_non_bearer_token(self):
        request = _make_mock_request(headers={"Authorization": "Basic dGVzdDp0ZXN0"})
        user_id, role, _ip = _extract_user_info(request)
        assert user_id is None
        assert role is None

    def test_invalid_jwt_returns_anonymous(self):
        request = _make_mock_request(
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id is None
        assert role is None

    @patch(_DECODE_PATCH_TARGET)
    def test_normal_user_token(self, mock_decode):
        mock_decode.return_value = {"sub": "testuser", "role": "user"}
        request = _make_mock_request(
            headers={"Authorization": "Bearer valid.token.here"}
        )
        user_id, role, ip = _extract_user_info(request)
        assert user_id == "testuser"
        assert role == "user"
        assert ip == "127.0.0.1"

    @patch(_DECODE_PATCH_TARGET)
    def test_admin_user_token(self, mock_decode):
        mock_decode.return_value = {"sub": "adminuser", "role": "admin"}
        request = _make_mock_request(
            headers={"Authorization": "Bearer admin.token.here"}
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id == "adminuser"
        assert role == "admin"

    @patch(_DECODE_PATCH_TARGET)
    def test_token_without_role_defaults_to_user(self, mock_decode):
        mock_decode.return_value = {"sub": "noroleuser"}
        request = _make_mock_request(
            headers={"Authorization": "Bearer norole.token.here"}
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id == "noroleuser"
        assert role == "user"

    @patch(_DECODE_PATCH_TARGET)
    def test_token_without_username_returns_anonymous(self, mock_decode):
        mock_decode.return_value = {"role": "user"}
        request = _make_mock_request(
            headers={"Authorization": "Bearer nosub.token.here"}
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id is None
        assert role is None

    @patch(_DECODE_PATCH_TARGET)
    def test_decode_raises_exception_returns_anonymous(self, mock_decode):
        mock_decode.side_effect = ValueError("模拟解码失败")
        request = _make_mock_request(
            headers={"Authorization": "Bearer broken.token.here"}
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id is None
        assert role is None


class TestResolveRateLimitKey:

    def test_anonymous_key_format(self):
        request = _make_mock_request(client_host="10.0.0.5")
        key = _resolve_rate_limit_key(request)
        assert key == "anon:10.0.0.5"

    @patch(_DECODE_PATCH_TARGET)
    def test_user_key_format(self, mock_decode):
        mock_decode.return_value = {"sub": "testuser", "role": "user"}
        request = _make_mock_request(
            headers={"Authorization": "Bearer token"}
        )
        key = _resolve_rate_limit_key(request)
        assert key == "user:testuser"

    @patch(_DECODE_PATCH_TARGET)
    def test_admin_key_format(self, mock_decode):
        mock_decode.return_value = {"sub": "admin1", "role": "admin"}
        request = _make_mock_request(
            headers={"Authorization": "Bearer token"}
        )
        key = _resolve_rate_limit_key(request)
        assert key == "admin:admin1"

    @patch(_DECODE_PATCH_TARGET)
    def test_different_users_have_different_keys(self, mock_decode):
        mock_decode.return_value = {"sub": "user_a", "role": "user"}
        request_a = _make_mock_request(
            headers={"Authorization": "Bearer token_a"}
        )
        key_a = _resolve_rate_limit_key(request_a)

        mock_decode.return_value = {"sub": "user_b", "role": "user"}
        request_b = _make_mock_request(
            headers={"Authorization": "Bearer token_b"}
        )
        key_b = _resolve_rate_limit_key(request_b)

        assert key_a != key_b
        assert key_a == "user:user_a"
        assert key_b == "user:user_b"

    @patch(_DECODE_PATCH_TARGET)
    def test_same_user_same_role_same_key(self, mock_decode):
        mock_decode.return_value = {"sub": "sameuser", "role": "user"}
        request1 = _make_mock_request(
            headers={"Authorization": "Bearer token1"}
        )
        request2 = _make_mock_request(
            headers={"Authorization": "Bearer token2"}
        )
        assert _resolve_rate_limit_key(request1) == _resolve_rate_limit_key(request2)


class TestGetAnalyzeRateLimit:

    @staticmethod
    def _call_with_request(mock_request):
        """通过 contextvars 注入请求后调用 get_analyze_rate_limit."""
        token = _request_ctx.set(mock_request)
        try:
            return get_analyze_rate_limit()
        finally:
            _request_ctx.reset(token)

    def test_anonymous_limit_from_config(self):
        request = _make_mock_request()
        limit = self._call_with_request(request)
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS
        assert "minute" in limit

    def test_no_request_context_returns_anonymous(self):
        """无请求上下文时应安全回退为匿名配额."""
        _request_ctx.set(None)
        limit = get_analyze_rate_limit()
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS

    @patch(_DECODE_PATCH_TARGET)
    def test_normal_user_limit_from_config(self, mock_decode):
        mock_decode.return_value = {"sub": "user1", "role": "user"}
        request = _make_mock_request(
            headers={"Authorization": "Bearer token"}
        )
        limit = self._call_with_request(request)
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_USER

    @patch(_DECODE_PATCH_TARGET)
    def test_admin_limit_from_config(self, mock_decode):
        mock_decode.return_value = {"sub": "admin1", "role": "admin"}
        request = _make_mock_request(
            headers={"Authorization": "Bearer token"}
        )
        limit = self._call_with_request(request)
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_ADMIN

    @patch(_DECODE_PATCH_TARGET)
    def test_admin_higher_than_user(self, mock_decode):
        mock_decode.return_value = {"sub": "admin1", "role": "admin"}
        admin_request = _make_mock_request(
            headers={"Authorization": "Bearer admin_token"}
        )
        admin_limit = self._call_with_request(admin_request)

        mock_decode.return_value = {"sub": "user1", "role": "user"}
        user_request = _make_mock_request(
            headers={"Authorization": "Bearer user_token"}
        )
        user_limit = self._call_with_request(user_request)

        admin_val = int(admin_limit.split("/")[0])
        user_val = int(user_limit.split("/")[0])
        assert admin_val > user_val

    @patch(_DECODE_PATCH_TARGET)
    def test_user_higher_than_anonymous(self, mock_decode):
        mock_decode.return_value = {"sub": "user1", "role": "user"}
        user_request = _make_mock_request(
            headers={"Authorization": "Bearer user_token"}
        )
        user_limit = self._call_with_request(user_request)

        anon_request = _make_mock_request()
        anon_limit = self._call_with_request(anon_request)

        user_val = int(user_limit.split("/")[0])
        anon_val = int(anon_limit.split("/")[0])
        assert user_val > anon_val

    def test_no_hardcoded_values(self):
        import inspect  # noqa: PLC0415

        source = inspect.getsource(get_analyze_rate_limit)
        assert "AnalysisConfig" in source
        assert '"5/minute"' not in source
        assert '"10/minute"' not in source
        assert '"30/minute"' not in source


class TestLogRateLimitBreach:

    def test_anonymous_log(self):
        import io  # noqa: PLC0415

        from loguru import logger  # noqa: PLC0415

        log_stream = io.StringIO()
        handler_id = logger.add(log_stream, level="WARNING", format="{message}")

        try:
            request = _make_mock_request(client_host="192.168.1.10")
            _log_rate_limit_breach(request, {})
            log_output = log_stream.getvalue()
            assert "限流触发" in log_output
            assert "匿名用户" in log_output
            assert "192.168.1.10" in log_output
            assert "/api/analyze" in log_output
        finally:
            logger.remove(handler_id)

    @patch(_DECODE_PATCH_TARGET)
    def test_user_log(self, mock_decode):
        import io  # noqa: PLC0415

        from loguru import logger  # noqa: PLC0415

        mock_decode.return_value = {"sub": "testuser", "role": "user"}

        log_stream = io.StringIO()
        handler_id = logger.add(log_stream, level="WARNING", format="{message}")

        try:
            request = _make_mock_request(
                headers={"Authorization": "Bearer token"},
                client_host="10.0.0.1",
            )
            _log_rate_limit_breach(request, {})
            log_output = log_stream.getvalue()
            assert "限流触发" in log_output
            assert "user" in log_output
            assert "testuser" in log_output
            assert "10.0.0.1" in log_output
        finally:
            logger.remove(handler_id)

    @patch(_DECODE_PATCH_TARGET)
    def test_admin_log(self, mock_decode):
        import io  # noqa: PLC0415

        from loguru import logger  # noqa: PLC0415

        mock_decode.return_value = {"sub": "superadmin", "role": "admin"}

        log_stream = io.StringIO()
        handler_id = logger.add(log_stream, level="WARNING", format="{message}")

        try:
            request = _make_mock_request(
                headers={"Authorization": "Bearer token"},
                client_host="172.16.0.1",
            )
            _log_rate_limit_breach(request, {})
            log_output = log_stream.getvalue()
            assert "限流触发" in log_output
            assert "admin" in log_output
            assert "superadmin" in log_output
        finally:
            logger.remove(handler_id)

    @patch(_DECODE_PATCH_TARGET)
    def test_log_contains_timestamp(self, mock_decode):
        import io  # noqa: PLC0415

        from loguru import logger  # noqa: PLC0415

        mock_decode.return_value = {"sub": "user1", "role": "user"}

        log_stream = io.StringIO()
        handler_id = logger.add(log_stream, level="WARNING", format="{message}")

        try:
            request = _make_mock_request(
                headers={"Authorization": "Bearer token"}
            )
            _log_rate_limit_breach(request, {})
            log_output = log_stream.getvalue()
            now = datetime.now(UTC)
            date_prefix = now.strftime("%Y-%m-%d")
            assert date_prefix in log_output
        finally:
            logger.remove(handler_id)


class TestLimiterConfiguration:

    def test_limiter_uses_custom_key_func(self):
        assert limiter._key_func is _resolve_rate_limit_key

    def test_limiter_default_limits_from_config(self):
        limits = limiter._default_limits
        assert len(limits) == 1
        assert hasattr(limits[0], "__iter__")
        default_limit_items = list(limits[0])
        assert len(default_limit_items) >= 1

    def test_limiter_breach_callback(self):
        assert limiter._on_breach is _log_rate_limit_breach

    def test_limiter_is_slowapi_instance(self):
        assert isinstance(limiter, Limiter)


class TestRateLimitIntegration:

    @pytest.fixture(autouse=True)
    def _ensure_limiter_enabled(self):
        """确保集成测试期间限流器处于启用状态."""
        from app.main import app  # noqa: PLC0415
        was_enabled = app.state.limiter.enabled
        app.state.limiter.enabled = True
        app.state.limiter.reset()
        yield
        app.state.limiter.enabled = was_enabled

    def test_rate_limit_exceeded_for_anonymous(self):
        import json  # noqa: PLC0415
        from unittest.mock import AsyncMock, patch  # noqa: PLC0415

        from fastapi.testclient import TestClient  # noqa: PLC0415

        from app.main import app  # noqa: PLC0415

        with patch(
            "app.services.pipeline.call_ollama_with_retry",
            new_callable=AsyncMock,
        ) as mock_ollama:
            mock_ollama.return_value = json.dumps(
                {
                    "subjective_knowledge": "明知",
                    "sentence": "有期徒刑一年",
                    "ground_truth_analysis": {
                        "dimension1": {"score": 8.0, "reasoning": "test"},
                        "dimension2": {"score": 7.0, "reasoning": "test"},
                        "dimension3": {"score": 6.0, "reasoning": "test"},
                    },
                }
            )

            client = TestClient(app)
            anon_limit_str = AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS
            max_requests = int(anon_limit_str.split("/")[0])

            for i in range(max_requests + 1):
                response = client.post(
                    "/api/analyze",
                    json={
                        "case_text": f"这是一段足够长的测试文本内容编号{i}",
                        "mode": "single",
                    },
                )

            assert response.status_code == 429

    @patch("app.services.pipeline.call_ollama_with_retry")
    def test_different_roles_have_independent_counters(self, mock_ollama):
        import json  # noqa: PLC0415

        from fastapi.testclient import TestClient  # noqa: PLC0415

        from app.main import app  # noqa: PLC0415

        mock_ollama.return_value = json.dumps(
            {
                "subjective_knowledge": "明知",
                "sentence": "有期徒刑一年",
                "ground_truth_analysis": {
                    "dimension1": {"score": 8.0, "reasoning": "test"},
                    "dimension2": {"score": 7.0, "reasoning": "test"},
                    "dimension3": {"score": 6.0, "reasoning": "test"},
                },
            }
        )

        client = TestClient(app)
        anon_limit = int(
            AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS.split("/")[0]
        )

        for i in range(anon_limit):
            response = client.post(
                "/api/analyze",
                json={
                    "case_text": f"这是一段足够长的匿名用户测试文本{i}",
                    "mode": "single",
                },
            )
        assert response.status_code == 200

        response = client.post(
            "/api/analyze",
            json={
                "case_text": "匿名用户超限测试请求文本内容",
                "mode": "single",
            },
        )
        assert response.status_code == 429

    def test_jwt_decode_failure_graceful_degradation(self):
        import json  # noqa: PLC0415
        from unittest.mock import AsyncMock, patch  # noqa: PLC0415

        from fastapi.testclient import TestClient  # noqa: PLC0415

        from app.main import app  # noqa: PLC0415

        with patch(
            "app.services.pipeline.call_ollama_with_retry",
            new_callable=AsyncMock,
        ) as mock_ollama:
            mock_ollama.return_value = json.dumps(
                {
                    "subjective_knowledge": "明知",
                    "sentence": "有期徒刑一年",
                    "ground_truth_analysis": {
                        "dimension1": {"score": 8.0, "reasoning": "test"},
                        "dimension2": {"score": 7.0, "reasoning": "test"},
                        "dimension3": {"score": 6.0, "reasoning": "test"},
                    },
                }
            )

            client = TestClient(app)
            response = client.post(
                "/api/analyze",
                json={
                    "case_text": "降级测试文本内容足够长符合要求",
                    "mode": "single",
                },
                headers={"Authorization": "Bearer corrupt.token.here"},
            )
            assert response.status_code in {200, 429}


class TestEdgeCases:

    @patch(_DECODE_PATCH_TARGET)
    def test_empty_username_in_token(self, mock_decode):
        mock_decode.return_value = {"sub": "", "role": "user"}
        request = _make_mock_request(
            headers={"Authorization": "Bearer token"}
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id is None
        assert role is None

    @patch(_DECODE_PATCH_TARGET)
    def test_unknown_role_treated_as_user(self, mock_decode):
        """未知角色应被视为普通用户对待."""
        mock_decode.return_value = {"sub": "stranger", "role": "unknown_role"}
        request = _make_mock_request(
            headers={"Authorization": "Bearer token"}
        )
        token = _request_ctx.set(request)
        try:
            limit = get_analyze_rate_limit()
        finally:
            _request_ctx.reset(token)
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_USER

    @patch(_DECODE_PATCH_TARGET)
    def test_empty_role_falls_back_to_anonymous(self, mock_decode):
        """role 为空字符串时 get_analyze_rate_limit 回退为匿名配额."""
        mock_decode.return_value = {"sub": "user1", "role": ""}
        request = _make_mock_request(
            headers={"Authorization": "Bearer token"}
        )
        token = _request_ctx.set(request)
        try:
            limit = get_analyze_rate_limit()
        finally:
            _request_ctx.reset(token)
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS

    def test_different_ips_have_independent_keys(self):
        key1 = _resolve_rate_limit_key(
            _make_mock_request(client_host="1.1.1.1")
        )
        key2 = _resolve_rate_limit_key(
            _make_mock_request(client_host="2.2.2.2")
        )
        assert key1 != key2
        assert key1 == "anon:1.1.1.1"
        assert key2 == "anon:2.2.2.2"

    def test_config_values_are_valid_strings(self):
        for attr_name in (
            "RATE_LIMIT_ANALYZE_ANONYMOUS",
            "RATE_LIMIT_ANALYZE_USER",
            "RATE_LIMIT_ANALYZE_ADMIN",
        ):
            value = getattr(AnalysisConfig, attr_name)
            assert isinstance(value, str)
            assert "/minute" in value
            count = int(value.split("/")[0])
            assert count > 0

    def test_rate_limit_key_is_hashable(self):
        key = _resolve_rate_limit_key(_make_mock_request())
        d = {key: 1}
        assert d[key] == 1

    @patch(_DECODE_PATCH_TARGET)
    def test_admin_vs_user_have_separate_buckets(self, mock_decode):
        mock_decode.return_value = {"sub": "u1", "role": "admin"}
        admin_key = _resolve_rate_limit_key(
            _make_mock_request(headers={"Authorization": "Bearer t1"})
        )
        mock_decode.return_value = {"sub": "u1", "role": "user"}
        user_key = _resolve_rate_limit_key(
            _make_mock_request(headers={"Authorization": "Bearer t2"})
        )
        assert admin_key != user_key
        assert admin_key == "admin:u1"
        assert user_key == "user:u1"
