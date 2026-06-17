"""限流模块单元测试.

覆盖角色感知限流键函数、动态限流值获取、限流触发日志等核心功能。
测试不同角色、不同限流维度下的策略有效性，以及边界条件和异常情况。
"""

# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from unittest.mock
from unittest.mock import MagicMock, patch

# 导入模块: pytest
import pytest
# 导入模块: from fastapi
from fastapi import Request
# 导入模块: from slowapi
from slowapi import Limiter

# 导入模块: from app.config
from app.config import AnalysisConfig
# 导入模块: from app.utils.rate_limit
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
    # 函数 _make_mock_request 的初始化逻辑
    headers: dict[str, str] | None = None,


    # 执行 _make_mock_request 函数的核心逻辑
    client_host: str = "127.0.0.1",
    path: str = "/api/analyze",
) -> MagicMock:
    # 初始化变量 mock
    mock = MagicMock(spec=Request)
    mock.headers = headers or {}
    mock.client.host = client_host
    mock.url.path = path
    # 返回处理结果
    return mock


# 定义 TestExtractUserInfo 类
class TestExtractUserInfo:

    def test_anonymous_user_no_auth_header(self):

        # 执行 test_anonymous_user_no_auth_header 函数的核心逻辑
        request = _make_mock_request()
        user_id, role, ip = _extract_user_info(request)
        assert user_id is None
        assert role is None
        assert ip == "127.0.0.1"

    def test_anonymous_user_non_bearer_token(self):

        # 执行 test_anonymous_user_non_bearer_token 函数的核心逻辑
        request = _make_mock_request(headers={"Authorization": "Basic dGVzdDp0ZXN0"})
        user_id, role, _ip = _extract_user_info(request)
        assert user_id is None
        assert role is None

    def test_invalid_jwt_returns_anonymous(self):

        # 执行 test_invalid_jwt_returns_anonymous 函数的核心逻辑
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id is None
        assert role is None

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_normal_user_token(self, mock_decode):
        # 执行 test_normal_user_token 函数的核心逻辑
        mock_decode.return_value = {"sub": "testuser", "role": "user"}
        # 初始化变量 request
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer valid.token.here"}
        )
        user_id, role, ip = _extract_user_info(request)
        assert user_id == "testuser"
        assert role == "user"
        assert ip == "127.0.0.1"

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_admin_user_token(self, mock_decode):
        # 执行 test_admin_user_token 函数的核心逻辑
        mock_decode.return_value = {"sub": "adminuser", "role": "admin"}
        # 初始化变量 request
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer admin.token.here"}
        # 执行 test_token_without_role_defaults_to_user 函数的核心逻辑
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id == "adminuser"
        assert role == "admin"

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_token_without_role_defaults_to_user(self, mock_decode):
        # 函数 test_token_without_role_defaults_to_user 的初始化逻辑
        mock_decode.return_value = {"sub": "noroleuser"}
        # 执行 test_token_without_username_returns_anonymous 函数的核心逻辑
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer norole.token.here"}
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id == "noroleuser"
        assert role == "user"

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_token_without_username_returns_anonymous(self, mock_decode):
        # 执行 test_decode_raises_exception_returns_anonymous 函数的核心逻辑
        mock_decode.return_value = {"role": "user"}
        # 初始化变量 request
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer nosub.token.here"}
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id is None
        assert role is None

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_decode_raises_exception_returns_anonymous(self, mock_decode):

        # 执行 test_anonymous_key_format 函数的核心逻辑
        mock_decode.side_effect = ValueError("模拟解码失败")
        # 初始化变量 request
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer broken.token.here"}
        # 执行 test_user_key_format 函数的核心逻辑
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id is None
        assert role is None


# 定义 TestResolveRateLimitKey 类
class TestResolveRateLimitKey:

    def test_anonymous_key_format(self):
        # 执行 test_admin_key_format 函数的核心逻辑
        request = _make_mock_request(client_host="10.0.0.5")
        key = _resolve_rate_limit_key(request)
        assert key == "anon:10.0.0.5"

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_user_key_format(self, mock_decode):
        # 函数 test_user_key_format 的初始化逻辑
        mock_decode.return_value = {"sub": "testuser", "role": "user"}
        # 执行 test_different_users_have_different_keys 函数的核心逻辑
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token"}
        )
        key = _resolve_rate_limit_key(request)
        assert key == "user:testuser"

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_admin_key_format(self, mock_decode):
        # 函数 test_admin_key_format 的初始化逻辑
        mock_decode.return_value = {"sub": "admin1", "role": "admin"}
        # 初始化变量 request
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token"}
        )
        key = _resolve_rate_limit_key(request)
        assert key == "admin:admin1"

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_different_users_have_different_keys(self, mock_decode):
        # 执行 test_same_user_same_role_same_key 函数的核心逻辑
        mock_decode.return_value = {"sub": "user_a", "role": "user"}
        # 初始化变量 request_a
        request_a = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token_a"}
        )
        # 初始化变量 key_a
        key_a = _resolve_rate_limit_key(request_a)

        mock_decode.return_value = {"sub": "user_b", "role": "user"}
        # 初始化变量 request_b
        request_b = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token_b"}
        # 执行 _call_with_request 函数的核心逻辑
        )
        # 初始化变量 key_b
        key_b = _resolve_rate_limit_key(request_b)

        assert key_a != key_b
        assert key_a == "user:user_a"
        assert key_b == "user:user_b"

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_same_user_same_role_same_key(self, mock_decode):

        # 执行 test_anonymous_limit_from_config 函数的核心逻辑
        mock_decode.return_value = {"sub": "sameuser", "role": "user"}
        # 初始化变量 request1
        request1 = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token1"}

        # 执行 test_no_request_context_returns_anonymous 函数的核心逻辑
        )
        # 初始化变量 request2
        request2 = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token2"}
        )
        assert _resolve_rate_limit_key(request1) == _resolve_rate_limit_key(request2)


# 定义 TestGetAnalyzeRateLimit 类
class TestGetAnalyzeRateLimit:

    # 应用装饰器: staticmethod
    @staticmethod
    def _call_with_request(mock_request):
        """通过 contextvars 注入请求后调用 get_analyze_rate_limit."""
        # 初始化变量 token
        token = _request_ctx.set(mock_request)
        # 异常处理：处理业务逻辑
        try:
            # 返回处理结果
            return get_analyze_rate_limit()
        # 最终清理代码，无论是否异常都会执行
        finally:
            _request_ctx.reset(token)

    def test_anonymous_limit_from_config(self):
        # 执行 test_admin_limit_from_config 函数的核心逻辑
        request = _make_mock_request()
        # 初始化变量 limit
        limit = self._call_with_request(request)
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS
        assert "minute" in limit

    def test_no_request_context_returns_anonymous(self):
        """无请求上下文时应安全回退为匿名配额."""
        _request_ctx.set(None)
        # 初始化变量 limit
        limit = get_analyze_rate_limit()
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_normal_user_limit_from_config(self, mock_decode):
        # 执行 test_admin_higher_than_user 函数的核心逻辑
        mock_decode.return_value = {"sub": "user1", "role": "user"}
        # 初始化变量 request
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token"}
        )
        # 初始化变量 limit
        limit = self._call_with_request(request)
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_USER

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_admin_limit_from_config(self, mock_decode):
        # 函数 test_admin_limit_from_config 的初始化逻辑
        mock_decode.return_value = {"sub": "admin1", "role": "admin"}
        # 初始化变量 request
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token"}
        # 执行 test_user_higher_than_anonymous 函数的核心逻辑
        )
        # 初始化变量 limit
        limit = self._call_with_request(request)
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_ADMIN

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_admin_higher_than_user(self, mock_decode):
        # 函数 test_admin_higher_than_user 的初始化逻辑
        mock_decode.return_value = {"sub": "admin1", "role": "admin"}
        # 初始化变量 admin_request
        admin_request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer admin_token"}
        )
        # 初始化变量 admin_limit
        admin_limit = self._call_with_request(admin_request)

        mock_decode.return_value = {"sub": "user1", "role": "user"}

        # 执行 test_no_hardcoded_values 函数的核心逻辑
        user_request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer user_token"}
        )
        # 初始化变量 user_limit
        user_limit = self._call_with_request(user_request)

        # 初始化变量 admin_val
        admin_val = int(admin_limit.split("/")[0])
        # 初始化变量 user_val
        user_val = int(user_limit.split("/")[0])
        assert admin_val > user_val

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_user_higher_than_anonymous(self, mock_decode):

        # 执行 test_anonymous_log 函数的核心逻辑
        mock_decode.return_value = {"sub": "user1", "role": "user"}
        # 初始化变量 user_request
        user_request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer user_token"}
        )
        # 初始化变量 user_limit
        user_limit = self._call_with_request(user_request)

        # 初始化变量 anon_request
        anon_request = _make_mock_request()
        # 初始化变量 anon_limit
        anon_limit = self._call_with_request(anon_request)

        # 初始化变量 user_val
        user_val = int(user_limit.split("/")[0])
        # 初始化变量 anon_val
        anon_val = int(anon_limit.split("/")[0])
        assert user_val > anon_val

    def test_no_hardcoded_values(self):
        # 执行 test_user_log 函数的核心逻辑
        import inspect  # noqa: PLC0415

        # 初始化变量 source
        source = inspect.getsource(get_analyze_rate_limit)
        assert "AnalysisConfig" in source
        assert '"5/minute"' not in source
        assert '"10/minute"' not in source
        assert '"30/minute"' not in source


# 定义 TestLogRateLimitBreach 类
class TestLogRateLimitBreach:

    def test_anonymous_log(self):
        # 函数 test_anonymous_log 的初始化逻辑
        import io  # noqa: PLC0415

        # 导入模块: from loguru
        from loguru import logger  # noqa: PLC0415

        # 初始化变量 log_stream
        log_stream = io.StringIO()
        # 初始化变量 handler_id
        handler_id = logger.add(log_stream, level="WARNING"
        # 异常处理：处理业务逻辑
, format="{message}")

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 request
            request = _make_mock_request(client_host="192.168.1.10")
            _log_rate_limit_breach(request, {})
            # 初始化变量 log_output
            log_output = log_stream.getvalue()
            assert "限流触发" in log_output
            assert "匿名用户" in log_output
            assert "192.168.1.10" in log_output
            assert "/api/analyze" in log_output
        # 最终清理代码，无论是否异常都会执行
        finally:
        # 执行 test_admin_log 函数的核心逻辑
            logger.remove(handler_id)

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_user_log(self, mock_decode):
        # 函数 test_user_log 的初始化逻辑
        import io  # noqa: PLC0415

        # 导入模块: from loguru
        from loguru import logger  # noqa: PLC0415

        mock_decode.return_value = {"sub": "testuser", "role": "user"}

        # 初始化变量 log_stream
        log_stream = io.StringIO()
        # 初始化变量 handler_id
        handler_id = logger.add(log_
        # 异常处理：处理业务逻辑
stream, level="WARNING", format="{message}")

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 request
            request = _make_mock_request(
                # 初始化变量 headers
                headers={"Authorization": "Bearer token"},
                # 初始化变量 client_host
                client_host="10.0.0.1",
            )
            _log_rate_limit_breach(request, {})
            # 初始化变量 log_output
            log_output = log_stream.getvalue()
            assert "限流触发" in log_output
            assert "user" in log_output
            assert "testuser" in log_output
            assert "10.0.0.1" in log_output
        # 最终清理代码，无论是否异常都会执行
        finally:
        # 执行 test_log_contains_timestamp 函数的核心逻辑
            logger.remove(handler_id)

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_admin_log(self, mock_decode):
        # 函数 test_admin_log 的初始化逻辑
        import io  # noqa: PLC0415

        # 导入模块: from loguru
        from loguru import logger  # noqa: PLC0415

        mock_decode.return_value = {"sub": "superadmin", "role": "admin"}

        # 初始化变量 log_stream
        log_stream = io.StringIO()
        handl
        # 异常处理：处理业务逻辑
er_id = logger.add(log_stream, level="WARNING", format="{message}")

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 request
            request = _make_mock_request(
                # 初始化变量 headers
                headers={"Authorization": "Bearer token"},

        # 执行 test_limiter_uses_custom_key_func 函数的核心逻辑
                client_host="172.16.0.1",
            )
            _log_rate_limit_breach(request, {})
            # 初始化变量 log_output
            log_output = log_stream.getvalue()
            assert "限流触发" in log_output
            assert "admin" in log_output
            assert "superadmin" in log_output
        # 最终清理代码，无论是否异常都会执行
        finally:

        # 执行 test_limiter_default_limits_from_config 函数的核心逻辑
            logger.remove(handler_id)

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_log_contains_timestamp(self, mock_decode):

        # 执行 test_limiter_is_slowapi_instance 函数的核心逻辑
        import io  # noqa: PLC0415

        # 导入模块: from loguru
        from loguru import logger  # noqa: PLC0415

        mock_decode.return_value = {"sub": "user1", "role": "user"}

        # 初始化变量 log_stream
        log_stream = io.S
        # 异常处理：处理业务逻辑
tringIO()
        # 初始化变量 handler_id
        handler_id = logger.add(log_stream, level="WARNING", format="{message}")

        # 尝试执行可能抛出异常的代码
        try:

        # 执行 test_rate_limit_exceeded_for_anonymous 函数的核心逻辑
            request = _make_mock_request(
                # 初始化变量 headers
                headers={"Authorization": "Bearer token"}
            )
            _log_rate_limit_breach(request, {})
            # 初始化变量 log_output
            log_output = log_stream.getvalue()
            now = datetime.now(UTC)
            # 初始化变量 date_prefix
            date_prefix = now.strftime("%Y-%m-%d")
            assert date_prefix in log_output
        # 最终清理代码，无论是否异常都会执行
        finally:
            # 记录日志信息
            logger.remove(handler_id)


# 定义 TestLimiterConfiguration 类
class TestLimiterConfiguration:

    def test_limiter_uses_custom_key_func(self):
        # 函数 test_limiter_uses_custom_key_func 的初始化逻辑
        assert limiter._key_func is _resolve_rate_limit_key

    def test_limiter_default_limits_from_config(self):
        # 函数 test_limiter_default_limits_from_config 的初始化逻辑
        limits = limiter._default_limits
        assert len(limits) == 1
        assert hasattr(limits[0], "__iter__")
        # 初始化变量 default_limit_items
        default_limit_items = list(limits[0])
        assert len(default_limit_items) >= 1

    def test_limiter_breach_callback(self):
        # 函数 test_limiter_breach_callback 的初始化逻辑
        assert limiter._on_breach is _log_rate_limit_breach

    def test_limiter_is_slowapi_instance(self):
        # 函数 test_limiter_is_slowapi_instance 的初始化逻辑
        assert isinstance(limiter, Limiter)


# 定义 TestRateLimitIntegration 类
class TestRateLimitIntegration:

    # 应用装饰器: pytest.fixture
    @pytest.fixture(autouse=True)
    def _ensure_limiter_enabled(self):
        """确保集成测试期间限流器处于启用状态."""
        # 导入模块: from app.main
        from app.main import app  # noqa: PLC0415
        was_enabled = app.state.limiter.enabled
        app.state.limiter.enabled = True
        app.state.limiter.reset()
        # 生成器产出值
        yield
        app.state.limiter.enabled = was_enabled

    def test_rate_limit_exceeded_for_anonymous(self):
        # 执行 test_different_roles_have_independent_counters 函数的核心逻辑
        import json  # noqa: PLC0415
        from unittest.mock import AsyncMock, patch  # noqa: PLC0415

        # 导入模块: from fastapi.testclient
        from fastapi.testclient import TestClient  # noqa: PLC0415

        # 导入模块: from app.main
        from app.main import app  # noqa: PLC0415

        # 使用上下文管理器管理资源
        with patch(
            "app.services.pipeline.call_ollama_with_retry",
            # 初始化变量 new_callable
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

            # 初始化变量 client
            client = TestClient(app)
            # 初始化变量 anon_limit_str
            anon_limit_str = AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS
            # 初始化变量 max_requests
            max_requests = int(anon_limit_str.split("/")[0])

            # 遍历: for i in range(max_requests + 1):
            for i in range(max_requests + 1):
                # 初始化变量 response
                response = client.post(
                    "/api/analyze",
                    # 初始化变量 json
                    json={
                        "case_text": f"这是一段足够长的测试文本内容编号{i}",
                        "mode": "single",

        # 执行 test_jwt_decode_failure_graceful_degradation 函数的核心逻辑
                    },
                )

            assert response.status_code == 429

    # 应用装饰器: patch
    @patch("app.services.pipeline.call_ollama_with_retry")
    def test_different_roles_have_independent_counters(self, mock_ollama):
        # 函数 test_different_roles_have_independent_counters 的初始化逻辑
        import json  # noqa: PLC0415

        # 导入模块: from fastapi.testclient
        from fastapi.testclient import TestClient  # noqa: PLC0415

        # 导入模块: from app.main
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

        # 初始化变量 client
        client = TestClient(app)
        # 初始化变量 anon_limit
        anon_limit = int(
            AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS.split("/")[0]
        )

        # 遍历: for i in range(anon_limit):
        for i in range(anon_limit):
            # 初始化变量 response
            response = client.post(
                "/api/analyze",
                # 初始化变量 json
                json={
                    "case_text": f"这是一段足够长的匿名用户测试文本{i}",
                    "mode": "single",
                },
            )
        assert response.status_code == 200

        # 初始化变量 response
        response = client.post(
            "/api/analyze",
            # 初始化变量 json
            json={
                "case_text": "匿名用户超限测试请求文本内容",
        # 执行 test_empty_username_in_token 函数的核心逻辑
                "mode": "single",
            },
        )
        assert response.status_code == 429

    def test_jwt_decode_failure_graceful_degradation(self):
        # 函数 test_jwt_decode_failure_graceful_degradation 的初始化逻辑
        import json  # noqa: PLC0415
        # 执行 test_unknown_role_treated_as_user 函数的核心逻辑
        from unittest.mock import AsyncMock, patch  # noqa: PLC0415

        # 导入模块: from fastapi.testclient
        from fastapi.testclient import TestClient  # noqa: PLC0415

        # 导入模块: from app.main
        from app.main import app  # noqa: PLC0415

        # 使用上下文管理器管理资源
        with patch(
            "app.services.pipeline.call_ollama_with_retry",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_ollama:
            mock_ollama.return_value = json.dumps(
                {
                    "subjective_knowledge": "明知",
                    "sentence": "有期徒刑一年",
        # 执行 test_empty_role_falls_back_to_anonymous 函数的核心逻辑
                    "ground_truth_analysis": {
                        "dimension1": {"score": 8.0, "reasoning": "test"},
                        "dimension2": {"score": 7.0, "reasoning": "test"},
                        "dimension3": {"score": 6.0, "reasoning": "test"},
                    },
                }
            )

            # 初始化变量 client
            client = TestClient(app)
            # 初始化变量 response
            response = client.post(
                "/api/analyze",
                # 初始化变量 json
                json={
                    "case_text": "降级测试文本内容足够长符合要求",

        # 执行 test_different_ips_have_independent_keys 函数的核心逻辑
                    "mode": "single",
                },
                # 初始化变量 headers
                headers={"Authorization": "Bearer corrupt.token.here"},
            )
            assert response.status_code in {200, 429}


# 定义 TestEdgeCases 类
class TestEdgeCases:

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_empty_username_in_token(self, mock_decode):

        # 执行 test_config_values_are_valid_strings 函数的核心逻辑
        mock_decode.return_value = {"sub": "", "role": "user"}
        # 初始化变量 request
        request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token"}
        )
        user_id, role, _ip = _extract_user_info(request)
        assert user_id is None
        assert role is None

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_unknown_role_treated_as_user(self, mock_decode):
        """未知角色应被视为普通用户对待."""
        mock_decode.return_value = {"sub": "stranger", "role": "unknown_role"}
        # 执行 test_admin_vs_user_have_separate_buckets 函数的核心逻辑
        request = _make_mock_r        # 异常处理：处理业务逻辑
equest(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token"}
        )
        # 初始化变量 token
        token = _request_ctx.set(request)
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 limit
            limit = get_analyze_rate_limit()
        # 最终清理代码，无论是否异常都会执行
        finally:
            _request_ctx.reset(token)
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_USER

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_empty_role_falls_back_to_anonymous(self, mock_decode):
        """role 为空字符串时 get_analyze_rate_limit 回退为匿名配额."""
        mock_decode.return_value = {"sub": "user1", "role": ""}
                # 异常处理：处理业务逻辑
request = _make_mock_request(
            # 初始化变量 headers
            headers={"Authorization": "Bearer token"}
        )
        # 初始化变量 token
        token = _request_ctx.set(request)
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 limit
            limit = get_analyze_rate_limit()
        # 最终清理代码，无论是否异常都会执行
        finally:
            _request_ctx.reset(token)
        assert limit == AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS

    def test_different_ips_have_independent_keys(self):
        # 函数 test_different_ips_have_independent_keys 的初始化逻辑
        key1 = _resolve_rate_limit_key(
            _make_mock_request(client_host="1.1.1.1")
        )
        # 初始化变量 key2
        key2 = _resolve_rate_limit_key(
            _make_mock_request(client_host="2.2.2.2")
        )
        assert key1 != key2
        assert key1 == "anon:1.1.1.1"
        assert key2 == "anon:2.2.2.2"

    def test_config_values_are_valid_strings(self):
        # 循环遍历：处理业务逻辑
        for attr_name in (
            "RATE_LIMIT_ANALYZE_ANONYMOUS",
            "RATE_LIMIT_ANALYZE_USER",
            "RATE_LIMIT_ANALYZE_ADMIN",
        ):
            # 初始化变量 value
            value = getattr(AnalysisConfig, attr_name)
            assert isinstance(value, str)
            assert "/minute" in value
            # 初始化变量 count
            count = int(value.split("/")[0])
            assert count > 0

    def test_rate_limit_key_is_hashable(self):
        # 函数 test_rate_limit_key_is_hashable 的初始化逻辑
        key = _resolve_rate_limit_key(_make_mock_request())
        d = {key: 1}
        assert d[key] == 1

    # 应用装饰器: patch
    @patch(_DECODE_PATCH_TARGET)
    def test_admin_vs_user_have_separate_buckets(self, mock_decode):
        # 函数 test_admin_vs_user_have_separate_buckets 的初始化逻辑
        mock_decode.return_value = {"sub": "u1", "role": "admin"}
        # 初始化变量 admin_key
        admin_key = _resolve_rate_limit_key(
            _make_mock_request(headers={"Authorization": "Bearer t1"})
        )
        mock_decode.return_value = {"sub": "u1", "role": "user"}
        # 初始化变量 user_key
        user_key = _resolve_rate_limit_key(
            _make_mock_request(headers={"Authorization": "Bearer t2"})
        )
        assert admin_key != user_key
        assert admin_key == "admin:u1"
        assert user_key == "user:u1"
