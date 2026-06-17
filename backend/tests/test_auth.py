"""test_auth - 单元测试模块.

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

# 导入模块: from datetime
from datetime import UTC, datetime, timedelta
# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch

# 导入模块: jwt
import jwt
# 导入模块: pytest
import pytest
# 导入模块: from fastapi
from fastapi import HTTPException, Request

# 导入模块: from app.config
from app.config import AnalysisConfig, settings
# 导入模块: from app.utils.auth
from app.utils.auth import (
    RefreshRequest,
    TokenPair,
    _generate_jti,
    _get_allowed_keys,
    _hash_token,
    clear_all_user_cache,
    clear_token_blacklist,
    create_access_token,
    create_refresh_token,
    create_tokens,
    decode_token,
    decode_token_with_fallback,
    get_current_user,
    get_optional_current_user,
    get_password_hash,
    refresh_token,
    verify_password,
    verify_token_not_blacklisted,
)


# 应用装饰器: pytest.fixture
@pytest.fixture(autouse=True)
async def clear_auth_caches():
    """每个测试前清除认证缓存，避免跨测试污染."""
    # 异步等待操作完成
    await clear_all_user_cache()
    # 异步等待操作完成
    await clear_token_blacklist()
    # 生成器产出值
    yield


# 应用装饰器: pytest.fixture
@pytest.fixture(autouse=True)
def ensure_jwt_key():
    # 执行 ensure_jwt_key 函数的核心逻辑
    original = settings.JWT_SECRET_KEY
    # 初始化变量 default_key
    default_key = "change-this-to-a-secure-random-secret-key-in-production"
    # 条件判断：处理业务逻辑
    if not original or original == default_key:
        settings.JWT_SECRET_KEY = (
            "test-secret-key-that-is-at-least-32-chars-long!!"
        )
    # 生成器产出值
    yield
    settings.JWT_SECRET_KEY = original


# 定义 TestPasswordUtils 类
class TestPasswordUtils:


    # TestPasswordUtils 类定义，封装相关属性和方法
    def test_verify_password_correct(self):
        # 执行 test_verify_password_correct 函数的核心逻辑
        hashed = get_password_hash("test_password")
        assert verify_password("test_password", hashed) is True

    def test_verify_password_incorrect(self):

        # 执行 test_verify_password_incorrect 函数的核心逻辑
        hashed = get_password_hash("test_password")
        assert verify_password("wrong_password", hashed) is False

    def test_password_hash_changes(self):

        # 执行 test_password_hash_changes 函数的核心逻辑
        h1 = get_password_hash("same_password")
        h2 = get_password_hash("same_password")
        assert h1 != h2

    def test_verify_empty_password(self):

        # 执行 test_verify_empty_password 函数的核心逻辑
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True
        assert verify_password("x", hashed) is False


# 定义 TestTokenUtils 类
class TestTokenUtils:
        # 执行 test_generate_jti_length 函数的核心逻辑
    def test_generate_jti_length(self):

        # 执行 test_hash_token 函数的核心逻辑
        jti = _generate_jti()
        assert len(jti) == 64

    def test_generate_jti_uniqueness(self):
        # 函数 test_generate_jti_uniqueness 的初始化逻辑
        jtis = {_generate_jti() for _ in range(100)}
        assert len(jtis) == 100

    def test_hash_token(self):

        # 执行 test_get_allowed_keys_with_primary 函数的核心逻辑
        token = "test_token_string"
        # 初始化变量 hashed
        hashed = _hash_token(token)
        assert isinstance(hashed, str)
        assert len(hashed) == 64
        assert _hash_token(token) == _hash_token(token)

    def test_get_allowed_keys_with_primary(self):

        # 执行 test_get_allowed_keys_with_previous 函数的核心逻辑
        keys = _get_allowed_keys()
        assert len(keys) >= 1

    def test_get_allowed_keys_with_previous(self):
        # 函数 test_get_allowed_keys_with_previous 的初始化逻辑
        with patch.object(settings, "JWT_SECRET_KEY_PREVIOUS", "previous-key"):
            # 初始化变量 keys
            keys = _get_allowed_keys()
            assert len(keys) >= 2


# 定义 TestCreateAccessToken 类
class TestCreateAccessToken:


    # TestCreateAccessToken 类定义，封装相关属性和方法
    def test_create_valid_token(self):

        # 执行 test_token_expiry 函数的核心逻辑
        token = create_access_token(data={"sub": "testuser"})
        assert isinstance(token, str)
        # 初始化变量 payload
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            # 初始化变量 algorithms
            algorithms=[AnalysisConfig.JWT_ALGORITHM],
        )
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_token_expiry(self):
        # 函数 test_token_expiry 的初始化逻辑
        token = create_access_token(
            # 初始化变量 data
            data={"sub": "user"},

        # 执行 test_token_with_custom_jti 函数的核心逻辑
            expires_delta=timedelta(seconds=-1),
        )
        # 初始化变量 payload
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            # 初始化变量 algorithms
            algorithms=[AnalysisConfig.JWT_ALGORITHM],
            # 初始化变量 options
            options={"verify_exp": False},
        )
        assert payload["sub"] == "user"
        # 初始化变量 expired
        expired = datetime.fromtimestamp(payload["exp"], tz=UTC)
        assert expired < datetime.now(UTC)

    def test_token_with_custom_jti(self):
        # 执行 test_create_valid_refresh_token 函数的核心逻辑
        custom_jti = "custom-jti-value"
        # 初始化变量 token
        token = create_access_token(data={"sub": "user"}, jti=custom_jti)
        # 初始化变量 payload
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            # 初始化变量 algorithms
            algorithms=[AnalysisConfig.JWT_ALGORITHM],
        )
        assert payload["jti"] == custom_jti


# 定义 TestCreateRefreshToken 类
class TestCreateRefreshToken:
        # 执行 test_decode_valid_token 函数的核心逻辑
    def test_create_valid_refresh_token(self):
        # 函数 test_create_valid_refresh_token 的初始化逻辑
        token_str, jti = create_refresh_token(data={"sub": "testuser"})
        assert isinstance(token_str, str)
        assert isinstance(jti, str)
        # 初始化变量 payload
        payload = jwt.decode(
            token_str,
            settings.JWT_SECRET_KEY,
            # 初始化变量 algorithms
            algorithms=[AnalysisConfig.JWT_ALGORITHM],
        )
        assert payload["sub"] == "testuser"
        assert payload["type"] == "refresh"
        assert payload["jti"] == jti


# 定义 TestDecodeTokenWithFallback 类
class TestDecodeTokenWithFallback:

        # 执行 test_decode_invalid_token 函数的核心逻辑
    def test_decode_valid_token(self):

        # 执行 test_fallback_to_previous_key 函数的核心逻辑
        token = create_access_token(data={"sub": "testuser"})
        # 初始化变量 payload
        payload = decode_token_with_fallback(token)
        assert payload["sub"] == "testuser"

    def test_decode_invalid_token(self):
        # 函数 test_decode_invalid_token 的初始化逻辑
        with pytest.raises(jwt.InvalidTokenError):
            decode_token_with_fallback("invalid_token_string")

    def test_decode_expired_token(self):
        # 执行 test_decode_valid_token 函数的核心逻辑
        token = create_access_token(
            # 初始化变量 data
            data={"sub": "user"},
            # 初始化变量 expires_delta
            expires_delta=timedelta(seconds=-1),
        )
        # 使用上下文管理器管理资源
        with pytest.raises(jwt.InvalidTokenError):

        # 执行 test_decode_with_explicit_key 函数的核心逻辑
            decode_token_with_fallback(token)

    def test_fallback_to_previous_key(self):
        # 函数 test_fallback_to_previous_key 的初始化逻辑
        token = create_access_token(data={"sub": "user"})
        # 使用上下文管理器管理资源
        with (
            patch.object(
                settings, "JWT_SECRET_KEY", "new-different-key"
            ),
            pytest.raises(jwt.InvalidTokenError),
        ):

        # 执行 test_decode_invalid_token_raises_invalid_token_error 函数的核心逻辑
            decode_token_with_fallback(token)


# 定义 TestDecodeToken 类
class TestDecodeToken:

        # 执行 test_decode_expired_token_raises_expired_signature_error 函数的核心逻辑
    def test_decode_valid_token(self):
        # 函数 test_decode_valid_token 的初始化逻辑
        token = create_access_token(data={"sub": "testuser"})

        # 执行 test_decode_wrong_key_raises_invalid_token_error 函数的核心逻辑
        payload = decode_token(token)
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_decode_with_explicit_key(self):

        # 执行 test_decode_token_preserves_original_claims 函数的核心逻辑
        token = create_access_token(data={"sub": "testuser"})
        # 初始化变量 payload
        payload = decode_token(token, key=settings.JWT_SECRET_KEY)
        assert payload["sub"] == "testuser"

    def test_decode_invalid_token_raises_invalid_token_error(self):
        # 函数 test_decode_invalid_token_raises_invalid_token_error 的初始化逻辑
        with pytest.raises(jwt.InvalidTokenError):
            decode_token("invalid_token_string")

    def test_decode_expired_token_raises_expired_signature_error(self):
        # 函数 test_decode_expired_token_raises_expired_signature_error 的初始化逻辑
        token = create_access_token(
            # 初始化变量 data
            data={"sub": "user"},
            # 初始化变量 expires_delta
            expires_delta=timedelta(seconds=-1),
        )
        # 使用上下文管理器管理资源
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token)

    def test_decode_wrong_key_raises_invalid_token_error(self):
        # 函数 test_decode_wrong_key_raises_invalid_token_error 的初始化逻辑
        token = create_access_token(data={"sub": "user"})
        # 使用上下文管理器管理资源
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(token, key="wrong-secret-key-that-does-not-match")

    def test_decode_token_preserves_original_claims(self):
        # 函数 test_decode_token_preserves_original_claims 的初始化逻辑
        token_data = {"sub": "testuser", "role": "admin", "user_id": "42"}
        # 初始化变量 token
        token = create_access_token(data=token_data)
        # 初始化变量 payload
        payload = decode_token(token)
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"
        assert payload["user_id"] == "42"


# 定义 TestCreateTokens 类
class TestCreateTokens:


    # TestCreateTokens 类定义，封装相关属性和方法
    async def test_create_tokens_pair(self):
        # 函数 test_create_tokens_pair 的初始化逻辑
        with patch("app.utils.auth.get_async_db_session") as mock_session_ctx:
            # 初始化变量 mock_db
            mock_db = AsyncMock()
            # 初始化变量 mock_result
            mock_result = MagicMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_result.scalar_one_or_none.return_value = MagicMock(
                id=1, role=MagicMock(value="user")
            )
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 初始化变量 result
            result = await create_tokens("testuser")
            assert isinstance(result, TokenPair)
            assert result.access_token is not None
            assert result.refresh_token is not None
            assert result.token_type == "bearer"

    async def test_create_tokens_unknown_user(self):
        # 函数 test_create_tokens_unknown_user 的初始化逻辑
        with patch("app.utils.auth.get_async_db_session") as mock_session_ctx:
            # 初始化变量 mock_db
            mock_db = AsyncMock()
            # 初始化变量 mock_result
            mock_result = MagicMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_result.scalar_one_or_none.return_value = None
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 初始化变量 result
            result = await create_tokens("unknown_user")
            assert isinstance(result, TokenPair)


# 定义 TestVerifyTokenNotBlacklisted 类
class TestVerifyTokenNotBlacklisted:


    # TestVerifyTokenNotBlacklisted 类定义，封装相关属性和方法
    async def test_not_blacklisted(self):
        # 函数 test_not_blacklisted 的初始化逻辑
        with patch("app.utils.auth.get_async_db_session") as mock_session_ctx:
            # 初始化变量 mock_db
            mock_db = AsyncMock()
            # 初始化变量 mock_result
            mock_result = MagicMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_result.scalar_one_or_none.return_value = None
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 异步等待操作完成
            await verify_token_not_blacklisted("some_jti")

    async def test_is_blacklisted(self):
        # 函数 test_is_blacklisted 的初始化逻辑
        with patch("app.utils.auth.get_async_db_session") as mock_session_ctx:
            # 初始化变量 mock_db
            mock_db = AsyncMock()
            # 初始化变量 mock_result
            mock_result = MagicMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_result.scalar_one_or_none.return_value = MagicMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 使用上下文管理器管理资源
            with pytest.raises(HTTPException) as exc:


    # TestGetCurrentUser 类定义，封装相关属性和方法
                await verify_token_not_blacklisted("blacklisted_jti")
            assert exc.value.status_code == 401


# 定义 TestGetCurrentUser 类
class TestGetCurrentUser:
    async def test_valid_token(self):
        # 函数 test_valid_token 的初始化逻辑
        token = create_access_token(data={"sub": "testuser"})
        # 使用上下文管理器管理资源
        with (
            patch(
                "app.utils.auth.verify_token_not_blacklisted",
                # 初始化变量 new_callable
                new_callable=AsyncMock,
            ),
            patch("app.utils.auth.get_async_db_session") as mock_session_ctx,
        ):
        # 执行 _mock_request 函数的核心逻辑
            mock_db = AsyncMock()
            # 初始化变量 mock_result
            mock_result = MagicMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_result.scalar_one_or_none.return_value = (
                MagicMock(username="testuser")
            )
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 初始化变量 user
            user = await get_current_user(token=token)
            assert user.username == "testuser"

    async def test_invalid_token(self):

        # 执行 _make_refresh_payload 函数的核心逻辑
        with pytest.raises(HTTPException) as exc:


    # TestGetOptionalCurrentUser 类定义，封装相关属性和方法
            await get_current_user(token="invalid_token")
        assert exc.value.status_code == 401


# 定义 TestGetOptionalCurrentUser 类
class TestGetOptionalCurrentUser:
    async def test_no_token(self):
        # 函数 test_no_token 的初始化逻辑
        result = await get_optional_current_user(token=None)
        assert result is None

    async def test_invalid_token_returns_none(self):


    # TestRefreshToken 类定义，封装相关属性和方法
        result = await get_optional_current_user(token="invalid")
        assert result is None


# 定义 TestRefreshToken 类
class TestRefreshToken:
    """刷新令牌端点测试套件，覆盖正常流程和所有错误场景."""

    # 应用装饰器: staticmethod
    @staticmethod
    def _mock_request():
        # 函数 _mock_request 的初始化逻辑
        scope = {"type": "http", "client": ("127.0.0.1", 12345)}
        # 返回处理结果
        return Request(scope=scope)

    def _make_refresh_payload(self, sub="testuser", user_id="1"):
        # 函数 _make_refresh_payload 的初始化逻辑
        token_str, jti = create_refresh_token(
            # 初始化变量 data
            data={"sub": sub, "role": "user", "user_id": user_id}
        )
        # 返回处理结果
        return token_str, jti

    def _mock_db_with_user(self, user_active=True):
        # 函数 _mock_db_with_user 的初始化逻辑
        mock_db = AsyncMock()
        # 初始化变量 mock_user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.is_active = user_active
        mock_user.role = MagicMock(value="user")
        # 返回处理结果
        return mock_db, mock_user

    async def test_normal_refresh_success(self):
        # 函数 test_normal_refresh_success 的初始化逻辑
        token_str, jti = self._make_refresh_payload()
        # 初始化变量 request
        request = RefreshRequest(refresh_token=token_str)

        # 使用上下文管理器管理资源
        with patch("app.utils.auth.create_tokens") as mock_create_tokens:
            mock_create_tokens.return_value = TokenPair(
                # 初始化变量 access_token
                access_token="new_access",
                # 初始化变量 refresh_token
                refresh_token="new_refresh",
            )
            # 使用上下文管理器管理资源
            with patch(
                "app.utils.auth.get_async_db_session"
            ) as mock_session_ctx:
                # 初始化变量 mock_db
                mock_db = AsyncMock()

                # 初始化变量 blacklist_mock
                blacklist_mock = MagicMock()
                blacklist_mock.scalar_one_or_none.return_value = None

                # 初始化变量 user_mock
                user_mock = MagicMock()
                user_mock.scalar_one_or_none.return_value = MagicMock(
                    id=1, username="testuser", is_active=True
                )

                # 初始化变量 stored_token_mock
                stored_token_mock = MagicMock()
                stored_token_mock.scalar_one_or_none.return_value = MagicMock(
                    jti=jti,
                    # 初始化变量 expires_at
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                    # 初始化变量 is_revoked
                    is_revoked=False,
                )

                mock_db.execute = AsyncMock()
                mock_db.execute.side_effect = [
                    blacklist_mock,
                    user_mock,
                    stored_token_mock,
                ]
                mock_session_ctx.return_value.__aenter__.return_value = mock_db

                # 初始化变量 mock_req
                mock_req = self._mock_request()
                # 初始化变量 result
                result = await refresh_token(mock_req, request)
                assert result.access_token == "new_access"
                assert result.refresh_token == "new_refresh"
                assert result.token_type == "bearer"
                mock_create_tokens.assert_called_once_with("testuser")

    async def test_invalid_token_string(self):
        # 函数 test_invalid_token_string 的初始化逻辑
        request = RefreshRequest(refresh_token="invalid_token")

        # 初始化变量 mock_req
        mock_req = self._mock_request()
        # 使用上下文管理器管理资源
        with pytest.raises(HTTPException) as exc:
            # 异步等待操作完成
            await refresh_token(mock_req, request)
        assert exc.value.status_code == 401
        assert exc.value.detail == "令牌验证失败"

    async def test_wrong_token_type_access_not_refresh(self):
        # 函数 test_wrong_token_type_access_not_refresh 的初始化逻辑
        access_token = create_access_token(
            # 初始化变量 data
            data={"sub": "testuser", "role": "user", "user_id": "1"}
        )
        # 初始化变量 request
        request = RefreshRequest(refresh_token=access_token)

        # 初始化变量 mock_req
        mock_req = self._mock_request()
        # 使用上下文管理器管理资源
        with pytest.raises(HTTPException) as exc:
            # 异步等待操作完成
            await refresh_token(mock_req, request)
        assert exc.value.status_code == 401
        assert exc.value.detail == "令牌验证失败"

    async def test_missing_sub_field(self):
        # 函数 test_missing_sub_field 的初始化逻辑
        token_str, _jti = create_refresh_token(
            # 初始化变量 data
            data={"role": "user", "user_id": "1"}
        )
        # 初始化变量 request
        request = RefreshRequest(refresh_token=token_str)

        # 初始化变量 mock_req
        mock_req = self._mock_request()
        # 使用上下文管理器管理资源
        with pytest.raises(HTTPException) as exc:
            # 异步等待操作完成
            await refresh_token(mock_req, request)
        assert exc.value.status_code == 401
        assert exc.value.detail == "令牌验证失败"

    async def test_token_in_blacklist(self):
        # 函数 test_token_in_blacklist 的初始化逻辑
        token_str, _jti = self._make_refresh_payload()
        # 初始化变量 request
        request = RefreshRequest(refresh_token=token_str)

        # 使用上下文管理器管理资源
        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            # 初始化变量 mock_db
            mock_db = AsyncMock()

            # 初始化变量 blacklist_mock
            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = MagicMock()

            mock_db.execute = AsyncMock(return_value=blacklist_mock)
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 初始化变量 mock_req
            mock_req = self._mock_request()
            # 使用上下文管理器管理资源
            with pytest.raises(HTTPException) as exc:
                # 异步等待操作完成
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 401
            assert exc.value.detail == "令牌已被列入黑名单"

    async def test_user_not_found(self):
        # 函数 test_user_not_found 的初始化逻辑
        token_str, _jti = self._make_refresh_payload(user_id="999")
        # 初始化变量 request
        request = RefreshRequest(refresh_token=token_str)

        # 使用上下文管理器管理资源
        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            # 初始化变量 mock_db
            mock_db = AsyncMock()

            # 初始化变量 blacklist_mock
            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = None

            # 初始化变量 user_mock
            user_mock = MagicMock()
            user_mock.scalar_one_or_none.return_value = None

            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [blacklist_mock, user_mock]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 初始化变量 mock_req
            mock_req = self._mock_request()
            # 使用上下文管理器管理资源
            with pytest.raises(HTTPException) as exc:
                # 异步等待操作完成
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 404
            assert exc.value.detail == "用户不存在"

    async def test_user_disabled(self):
        # 函数 test_user_disabled 的初始化逻辑
        token_str, _jti = self._make_refresh_payload()
        # 初始化变量 request
        request = RefreshRequest(refresh_token=token_str)

        # 使用上下文管理器管理资源
        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            # 初始化变量 mock_db
            mock_db = AsyncMock()

            # 初始化变量 blacklist_mock
            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = None

            # 初始化变量 user_mock
            user_mock = MagicMock()
            user_mock.scalar_one_or_none.return_value = MagicMock(
                id=1, username="testuser", is_active=False
            )

            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [blacklist_mock, user_mock]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 初始化变量 mock_req
            mock_req = self._mock_request()
            # 使用上下文管理器管理资源
            with pytest.raises(HTTPException) as exc:
                # 异步等待操作完成
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 403
            assert exc.value.detail == "用户已被禁用"

    async def test_refresh_token_already_revoked(self):
        # 函数 test_refresh_token_already_revoked 的初始化逻辑
        token_str, _jti = self._make_refresh_payload()
        # 初始化变量 request
        request = RefreshRequest(refresh_token=token_str)

        # 使用上下文管理器管理资源
        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            # 初始化变量 mock_db
            mock_db = AsyncMock()

            # 初始化变量 blacklist_mock
            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = None

            # 初始化变量 user_mock
            user_mock = MagicMock()
            user_mock.scalar_one_or_none.return_value = MagicMock(
                id=1, username="testuser", is_active=True
            )

            # 初始化变量 stored_mock
            stored_mock = MagicMock()
            stored_mock.scalar_one_or_none.return_value = None

            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [
                blacklist_mock,
                user_mock,
                stored_mock,
            ]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 初始化变量 mock_req
            mock_req = self._mock_request()
            # 使用上下文管理器管理资源
            with pytest.raises(HTTPException) as exc:
                # 异步等待操作完成
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 403
            assert exc.value.detail == "刷新令牌已被吊销"

    async def test_refresh_token_expired(self):
        # 函数 test_refresh_token_expired 的初始化逻辑
        token_str, jti = self._make_refresh_payload()
        # 初始化变量 request
        request = RefreshRequest(refresh_token=token_str)

        # 使用上下文管理器管理资源
        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            # 初始化变量 mock_db
            mock_db = AsyncMock()

            # 初始化变量 blacklist_mock
            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = None

            # 初始化变量 user_mock
            user_mock = MagicMock()
            user_mock.scalar_one_or_none.return_value = MagicMock(
                id=1, username="testuser", is_active=True
            )

            # 初始化变量 stored_mock
            stored_mock = MagicMock()
            stored_mock.scalar_one_or_none.return_value = MagicMock(
                jti=jti,
                # 初始化变量 expires_at
                expires_at=datetime.now(UTC) - timedelta(days=1),
                # 初始化变量 is_revoked
                is_revoked=False,
            )

            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [
                blacklist_mock,
                user_mock,
                stored_mock,
            ]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 初始化变量 mock_req
            mock_req = self._mock_request()
            # 使用上下文管理器管理资源
            with pytest.raises(HTTPException) as exc:
                # 异步等待操作完成
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 401
            assert exc.value.detail == "刷新令牌已过期"

    async def test_refresh_token_no_expires_at(self):
        # 函数 test_refresh_token_no_expires_at 的初始化逻辑
        token_str, jti = self._make_refresh_payload()
        # 初始化变量 request
        request = RefreshRequest(refresh_token=token_str)

        # 使用上下文管理器管理资源
        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            # 初始化变量 mock_db
            mock_db = AsyncMock()

            # 初始化变量 blacklist_mock
            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = None

            # 初始化变量 user_mock
            user_mock = MagicMock()
            user_mock.scalar_one_or_none.return_value = MagicMock(
                id=1, username="testuser", is_active=True
            )

            # 初始化变量 stored_mock
            stored_mock = MagicMock()
            stored_mock.scalar_one_or_none.return_value = MagicMock(
                jti=jti,
                # 初始化变量 expires_at
                expires_at=None,
                # 初始化变量 is_revoked
                is_revoked=False,
            )

            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [
                blacklist_mock,
                user_mock,
                stored_mock,
            ]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            # 初始化变量 mock_req
            mock_req = self._mock_request()
            # 使用上下文管理器管理资源
            with pytest.raises(HTTPException) as exc:
                # 异步等待操作完成
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 401
            assert exc.value.detail == "刷新令牌已过期或无效"
