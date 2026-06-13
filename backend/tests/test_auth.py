from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, Request

from app.config import AnalysisConfig, settings
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


@pytest.fixture(autouse=True)
async def clear_auth_caches():
    """每个测试前清除认证缓存，避免跨测试污染."""
    await clear_all_user_cache()
    await clear_token_blacklist()
    yield


@pytest.fixture(autouse=True)
def ensure_jwt_key():
    original = settings.JWT_SECRET_KEY
    default_key = "change-this-to-a-secure-random-secret-key-in-production"
    if not original or original == default_key:
        settings.JWT_SECRET_KEY = (
            "test-secret-key-that-is-at-least-32-chars-long!!"
        )
    yield
    settings.JWT_SECRET_KEY = original


class TestPasswordUtils:
    def test_verify_password_correct(self):
        hashed = get_password_hash("test_password")
        assert verify_password("test_password", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = get_password_hash("test_password")
        assert verify_password("wrong_password", hashed) is False

    def test_password_hash_changes(self):
        h1 = get_password_hash("same_password")
        h2 = get_password_hash("same_password")
        assert h1 != h2

    def test_verify_empty_password(self):
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True
        assert verify_password("x", hashed) is False


class TestTokenUtils:
    def test_generate_jti_length(self):
        jti = _generate_jti()
        assert len(jti) == 64

    def test_generate_jti_uniqueness(self):
        jtis = {_generate_jti() for _ in range(100)}
        assert len(jtis) == 100

    def test_hash_token(self):
        token = "test_token_string"
        hashed = _hash_token(token)
        assert isinstance(hashed, str)
        assert len(hashed) == 64
        assert _hash_token(token) == _hash_token(token)

    def test_get_allowed_keys_with_primary(self):
        keys = _get_allowed_keys()
        assert len(keys) >= 1

    def test_get_allowed_keys_with_previous(self):
        with patch.object(settings, "JWT_SECRET_KEY_PREVIOUS", "previous-key"):
            keys = _get_allowed_keys()
            assert len(keys) >= 2


class TestCreateAccessToken:
    def test_create_valid_token(self):
        token = create_access_token(data={"sub": "testuser"})
        assert isinstance(token, str)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[AnalysisConfig.JWT_ALGORITHM],
        )
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_token_expiry(self):
        token = create_access_token(
            data={"sub": "user"},
            expires_delta=timedelta(seconds=-1),
        )
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[AnalysisConfig.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        assert payload["sub"] == "user"
        expired = datetime.fromtimestamp(payload["exp"], tz=UTC)
        assert expired < datetime.now(UTC)

    def test_token_with_custom_jti(self):
        custom_jti = "custom-jti-value"
        token = create_access_token(data={"sub": "user"}, jti=custom_jti)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[AnalysisConfig.JWT_ALGORITHM],
        )
        assert payload["jti"] == custom_jti


class TestCreateRefreshToken:
    def test_create_valid_refresh_token(self):
        token_str, jti = create_refresh_token(data={"sub": "testuser"})
        assert isinstance(token_str, str)
        assert isinstance(jti, str)
        payload = jwt.decode(
            token_str,
            settings.JWT_SECRET_KEY,
            algorithms=[AnalysisConfig.JWT_ALGORITHM],
        )
        assert payload["sub"] == "testuser"
        assert payload["type"] == "refresh"
        assert payload["jti"] == jti


class TestDecodeTokenWithFallback:
    def test_decode_valid_token(self):
        token = create_access_token(data={"sub": "testuser"})
        payload = decode_token_with_fallback(token)
        assert payload["sub"] == "testuser"

    def test_decode_invalid_token(self):
        with pytest.raises(jwt.InvalidTokenError):
            decode_token_with_fallback("invalid_token_string")

    def test_decode_expired_token(self):
        token = create_access_token(
            data={"sub": "user"},
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(jwt.InvalidTokenError):
            decode_token_with_fallback(token)

    def test_fallback_to_previous_key(self):
        token = create_access_token(data={"sub": "user"})
        with (
            patch.object(
                settings, "JWT_SECRET_KEY", "new-different-key"
            ),
            pytest.raises(jwt.InvalidTokenError),
        ):
            decode_token_with_fallback(token)


class TestDecodeToken:
    def test_decode_valid_token(self):
        token = create_access_token(data={"sub": "testuser"})
        payload = decode_token(token)
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_decode_with_explicit_key(self):
        token = create_access_token(data={"sub": "testuser"})
        payload = decode_token(token, key=settings.JWT_SECRET_KEY)
        assert payload["sub"] == "testuser"

    def test_decode_invalid_token_raises_invalid_token_error(self):
        with pytest.raises(jwt.InvalidTokenError):
            decode_token("invalid_token_string")

    def test_decode_expired_token_raises_expired_signature_error(self):
        token = create_access_token(
            data={"sub": "user"},
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token)

    def test_decode_wrong_key_raises_invalid_token_error(self):
        token = create_access_token(data={"sub": "user"})
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(token, key="wrong-secret-key-that-does-not-match")

    def test_decode_token_preserves_original_claims(self):
        token_data = {"sub": "testuser", "role": "admin", "user_id": "42"}
        token = create_access_token(data=token_data)
        payload = decode_token(token)
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"
        assert payload["user_id"] == "42"


class TestCreateTokens:
    async def test_create_tokens_pair(self):
        with patch("app.utils.auth.get_async_db_session") as mock_session_ctx:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_result.scalar_one_or_none.return_value = MagicMock(
                id=1, role=MagicMock(value="user")
            )
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            result = await create_tokens("testuser")
            assert isinstance(result, TokenPair)
            assert result.access_token is not None
            assert result.refresh_token is not None
            assert result.token_type == "bearer"

    async def test_create_tokens_unknown_user(self):
        with patch("app.utils.auth.get_async_db_session") as mock_session_ctx:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_result.scalar_one_or_none.return_value = None
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            result = await create_tokens("unknown_user")
            assert isinstance(result, TokenPair)


class TestVerifyTokenNotBlacklisted:
    async def test_not_blacklisted(self):
        with patch("app.utils.auth.get_async_db_session") as mock_session_ctx:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_result.scalar_one_or_none.return_value = None
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            await verify_token_not_blacklisted("some_jti")

    async def test_is_blacklisted(self):
        with patch("app.utils.auth.get_async_db_session") as mock_session_ctx:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_result.scalar_one_or_none.return_value = MagicMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            with pytest.raises(HTTPException) as exc:
                await verify_token_not_blacklisted("blacklisted_jti")
            assert exc.value.status_code == 401


class TestGetCurrentUser:
    async def test_valid_token(self):
        token = create_access_token(data={"sub": "testuser"})
        with (
            patch(
                "app.utils.auth.verify_token_not_blacklisted",
                new_callable=AsyncMock,
            ),
            patch("app.utils.auth.get_async_db_session") as mock_session_ctx,
        ):
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_result.scalar_one_or_none.return_value = (
                MagicMock(username="testuser")
            )
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            user = await get_current_user(token=token)
            assert user.username == "testuser"

    async def test_invalid_token(self):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(token="invalid_token")
        assert exc.value.status_code == 401


class TestGetOptionalCurrentUser:
    async def test_no_token(self):
        result = await get_optional_current_user(token=None)
        assert result is None

    async def test_invalid_token_returns_none(self):
        result = await get_optional_current_user(token="invalid")
        assert result is None


class TestRefreshToken:
    """刷新令牌端点测试套件，覆盖正常流程和所有错误场景."""

    @staticmethod
    def _mock_request():
        scope = {"type": "http", "client": ("127.0.0.1", 12345)}
        return Request(scope=scope)

    def _make_refresh_payload(self, sub="testuser", user_id="1"):
        token_str, jti = create_refresh_token(
            data={"sub": sub, "role": "user", "user_id": user_id}
        )
        return token_str, jti

    def _mock_db_with_user(self, user_active=True):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.is_active = user_active
        mock_user.role = MagicMock(value="user")
        return mock_db, mock_user

    async def test_normal_refresh_success(self):
        token_str, jti = self._make_refresh_payload()
        request = RefreshRequest(refresh_token=token_str)

        with patch("app.utils.auth.create_tokens") as mock_create_tokens:
            mock_create_tokens.return_value = TokenPair(
                access_token="new_access",
                refresh_token="new_refresh",
            )
            with patch(
                "app.utils.auth.get_async_db_session"
            ) as mock_session_ctx:
                mock_db = AsyncMock()

                blacklist_mock = MagicMock()
                blacklist_mock.scalar_one_or_none.return_value = None

                user_mock = MagicMock()
                user_mock.scalar_one_or_none.return_value = MagicMock(
                    id=1, username="testuser", is_active=True
                )

                stored_token_mock = MagicMock()
                stored_token_mock.scalar_one_or_none.return_value = MagicMock(
                    jti=jti,
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                    is_revoked=False,
                )

                mock_db.execute = AsyncMock()
                mock_db.execute.side_effect = [
                    blacklist_mock,
                    user_mock,
                    stored_token_mock,
                ]
                mock_session_ctx.return_value.__aenter__.return_value = mock_db

                mock_req = self._mock_request()
                result = await refresh_token(mock_req, request)
                assert result.access_token == "new_access"
                assert result.refresh_token == "new_refresh"
                assert result.token_type == "bearer"
                mock_create_tokens.assert_called_once_with("testuser")

    async def test_invalid_token_string(self):
        request = RefreshRequest(refresh_token="invalid_token")

        mock_req = self._mock_request()
        with pytest.raises(HTTPException) as exc:
            await refresh_token(mock_req, request)
        assert exc.value.status_code == 401
        assert exc.value.detail == "令牌验证失败"

    async def test_wrong_token_type_access_not_refresh(self):
        access_token = create_access_token(
            data={"sub": "testuser", "role": "user", "user_id": "1"}
        )
        request = RefreshRequest(refresh_token=access_token)

        mock_req = self._mock_request()
        with pytest.raises(HTTPException) as exc:
            await refresh_token(mock_req, request)
        assert exc.value.status_code == 401
        assert exc.value.detail == "令牌验证失败"

    async def test_missing_sub_field(self):
        token_str, _jti = create_refresh_token(
            data={"role": "user", "user_id": "1"}
        )
        request = RefreshRequest(refresh_token=token_str)

        mock_req = self._mock_request()
        with pytest.raises(HTTPException) as exc:
            await refresh_token(mock_req, request)
        assert exc.value.status_code == 401
        assert exc.value.detail == "令牌验证失败"

    async def test_token_in_blacklist(self):
        token_str, _jti = self._make_refresh_payload()
        request = RefreshRequest(refresh_token=token_str)

        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            mock_db = AsyncMock()

            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = MagicMock()

            mock_db.execute = AsyncMock(return_value=blacklist_mock)
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            mock_req = self._mock_request()
            with pytest.raises(HTTPException) as exc:
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 401
            assert exc.value.detail == "令牌已被列入黑名单"

    async def test_user_not_found(self):
        token_str, _jti = self._make_refresh_payload(user_id="999")
        request = RefreshRequest(refresh_token=token_str)

        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            mock_db = AsyncMock()

            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = None

            user_mock = MagicMock()
            user_mock.scalar_one_or_none.return_value = None

            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [blacklist_mock, user_mock]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            mock_req = self._mock_request()
            with pytest.raises(HTTPException) as exc:
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 404
            assert exc.value.detail == "用户不存在"

    async def test_user_disabled(self):
        token_str, _jti = self._make_refresh_payload()
        request = RefreshRequest(refresh_token=token_str)

        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            mock_db = AsyncMock()

            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = None

            user_mock = MagicMock()
            user_mock.scalar_one_or_none.return_value = MagicMock(
                id=1, username="testuser", is_active=False
            )

            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [blacklist_mock, user_mock]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            mock_req = self._mock_request()
            with pytest.raises(HTTPException) as exc:
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 403
            assert exc.value.detail == "用户已被禁用"

    async def test_refresh_token_already_revoked(self):
        token_str, _jti = self._make_refresh_payload()
        request = RefreshRequest(refresh_token=token_str)

        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            mock_db = AsyncMock()

            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = None

            user_mock = MagicMock()
            user_mock.scalar_one_or_none.return_value = MagicMock(
                id=1, username="testuser", is_active=True
            )

            stored_mock = MagicMock()
            stored_mock.scalar_one_or_none.return_value = None

            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [
                blacklist_mock,
                user_mock,
                stored_mock,
            ]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            mock_req = self._mock_request()
            with pytest.raises(HTTPException) as exc:
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 403
            assert exc.value.detail == "刷新令牌已被吊销"

    async def test_refresh_token_expired(self):
        token_str, jti = self._make_refresh_payload()
        request = RefreshRequest(refresh_token=token_str)

        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            mock_db = AsyncMock()

            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = None

            user_mock = MagicMock()
            user_mock.scalar_one_or_none.return_value = MagicMock(
                id=1, username="testuser", is_active=True
            )

            stored_mock = MagicMock()
            stored_mock.scalar_one_or_none.return_value = MagicMock(
                jti=jti,
                expires_at=datetime.now(UTC) - timedelta(days=1),
                is_revoked=False,
            )

            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [
                blacklist_mock,
                user_mock,
                stored_mock,
            ]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            mock_req = self._mock_request()
            with pytest.raises(HTTPException) as exc:
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 401
            assert exc.value.detail == "刷新令牌已过期"

    async def test_refresh_token_no_expires_at(self):
        token_str, jti = self._make_refresh_payload()
        request = RefreshRequest(refresh_token=token_str)

        with patch(
            "app.utils.auth.get_async_db_session"
        ) as mock_session_ctx:
            mock_db = AsyncMock()

            blacklist_mock = MagicMock()
            blacklist_mock.scalar_one_or_none.return_value = None

            user_mock = MagicMock()
            user_mock.scalar_one_or_none.return_value = MagicMock(
                id=1, username="testuser", is_active=True
            )

            stored_mock = MagicMock()
            stored_mock.scalar_one_or_none.return_value = MagicMock(
                jti=jti,
                expires_at=None,
                is_revoked=False,
            )

            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [
                blacklist_mock,
                user_mock,
                stored_mock,
            ]
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            mock_req = self._mock_request()
            with pytest.raises(HTTPException) as exc:
                await refresh_token(mock_req, request)
            assert exc.value.status_code == 401
            assert exc.value.detail == "刷新令牌已过期或无效"
