"""认证与授权工具模块.

提供 JWT 令牌生成/验证、令牌对（access + refresh）、
令牌黑名单、密钥轮换、密码哈希和用户认证依赖注入。
所有数据库操作均使用异步 API，避免阻塞事件循环。

性能优化：
- 基于 TTLCache 的用户信息缓存（5分钟 TTL），减少数据库重复查询
- 内存级令牌黑名单集合，O(1) 检查已吊销令牌
- 异步锁保护缓存操作，防止并发竞态条件
- 主动缓存清除策略：用户禁用/令牌吊销时即时失效缓存
"""

import asyncio
import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from loguru import logger
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import and_, select

from app.config import AnalysisConfig, settings
from app.database import get_async_db_session
from app.models.token_blacklist import RefreshToken, TokenBlacklist
from app.models.user import User, UserRole
from app.utils.rate_limit import limiter


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

_USER_CACHE_TTL: int = 300
_MAX_LOGIN_FAILED_COUNT: int = 5


class _UserCache:
    """基于 TTL 的用户信息内存缓存.

    使用 dict + 过期时间戳实现轻量级 TTL 缓存，
    避免引入外部依赖，5 分钟自动过期减少数据库查询。
    """

    def __init__(self, ttl: int = _USER_CACHE_TTL) -> None:
        self._ttl: int = ttl
        self._data: dict[str, tuple[User, float]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get(self, username: str) -> User | None:
        async with self._lock:
            entry = self._data.get(username)
            if entry is None:
                return None
            user, expires_at = entry
            if time.monotonic() > expires_at:
                del self._data[username]
                return None
            return user

    async def set(self, username: str, user: User) -> None:
        async with self._lock:
            self._data[username] = (user, time.monotonic() + self._ttl)

    async def delete(self, username: str) -> None:
        async with self._lock:
            self._data.pop(username, None)

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()

    async def cleanup_expired(self) -> int:
        async with self._lock:
            now = time.monotonic()
            expired = [k for k, (_, exp) in self._data.items() if now > exp]
            for k in expired:
                del self._data[k]
            return len(expired)

    @property
    def size(self) -> int:
        return len(self._data)


_user_cache = _UserCache()


class _TokenBlacklistSet:
    """内存级令牌黑名单集合.

    提供 O(1) 时间复杂度的令牌状态检查，
    与数据库黑名单保持同步，作为第一层快速过滤。
    """

    def __init__(self) -> None:
        self._data: set[str] = set()
        self._lock: asyncio.Lock = asyncio.Lock()

    async def contains(self, jti: str) -> bool:
        async with self._lock:
            return jti in self._data

    async def add(self, jti: str) -> None:
        async with self._lock:
            self._data.add(jti)

    async def remove(self, jti: str) -> None:
        async with self._lock:
            self._data.discard(jti)

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()

    @property
    def size(self) -> int:
        return len(self._data)


_token_blacklist = _TokenBlacklistSet()


async def get_cached_user(username: str) -> User | None:
    """从缓存获取用户信息，未命中返回 None."""
    return await _user_cache.get(username)


async def cache_user(username: str, user: User) -> None:
    """将用户信息写入缓存."""
    await _user_cache.set(username, user)


async def clear_user_cache(username: str) -> None:
    """主动清除指定用户的缓存数据.

    在用户禁用、权限变更等场景下调用，
    确保下次请求从数据库获取最新状态。
    """
    await _user_cache.delete(username)
    logger.debug(f"用户缓存已清除: username={username}")


async def clear_all_user_cache() -> None:
    """清除所有用户缓存."""
    await _user_cache.clear()
    logger.info("所有用户缓存已清除")


async def cleanup_expired_cache() -> int:
    """清理过期的缓存条目，返回清理数量."""
    return await _user_cache.cleanup_expired()


async def add_token_to_blacklist(jti: str) -> None:
    """将令牌 JTI 加入内存黑名单.

    在令牌吊销时调用，与数据库写入同步进行，
    确保后续验证请求能通过内存集合快速过滤。
    """
    await _token_blacklist.add(jti)
    logger.debug(f"令牌已加入内存黑名单: jti={jti}")


async def remove_token_from_blacklist(jti: str) -> None:
    """从内存黑名单中移除指定令牌."""
    await _token_blacklist.remove(jti)


async def is_token_blacklisted(jti: str) -> bool:
    """检查令牌是否在内存黑名单中."""
    return await _token_blacklist.contains(jti)


async def clear_token_blacklist() -> None:
    """清空内存黑名单集合."""
    await _token_blacklist.clear()


def get_user_cache_size() -> int:
    """获取当前用户缓存条目数."""
    return _user_cache.size


def get_blacklist_set_size() -> int:
    """获取当前内存黑名单令牌数."""
    return _token_blacklist.size


class TokenResponse(BaseModel):
    """JWT 令牌响应模型."""

    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    """令牌对响应模型，包含访问令牌和刷新令牌."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """刷新令牌请求模型."""

    refresh_token: str


class UserResponse(BaseModel):
    """用户信息响应模型."""

    id: int
    username: str
    role: UserRole
    is_active: bool

    class Config:
        """Pydantic 模型配置：启用 ORM 属性映射."""
        from_attributes = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码的 bcrypt 哈希值."""
    return pwd_context.hash(password)


def _get_allowed_keys() -> list[str]:
    """获取当前允许的 JWT 密钥列表（主密钥 + 前一个密钥用于平滑过渡）.

    支持密钥版本控制：当前密钥用于签发，新旧密钥均可用于验证，
    确保密钥轮换期间已签发的令牌仍能正常验证。

    Returns:
        按优先级排列的密钥列表
    """
    keys: list[str] = []
    default_key = "change-this-to-a-secure-random-secret-key-in-production"
    if settings.JWT_SECRET_KEY and default_key != settings.JWT_SECRET_KEY:
        keys.append(settings.JWT_SECRET_KEY)
    if settings.JWT_SECRET_KEY_PREVIOUS:
        keys.append(settings.JWT_SECRET_KEY_PREVIOUS)
    if not keys:
        keys.append("change-this-to-a-secure-random-secret-key-in-production")
    return keys


def _generate_jti() -> str:
    """生成 JWT 令牌唯一标识符."""
    return secrets.token_hex(32)


def _hash_token(token: str) -> str:
    """对令牌进行哈希处理，用于安全存储."""
    return hashlib.sha256(token.encode()).hexdigest()


def decode_token(token: str, key: str | None = None) -> dict[str, Any]:
    """使用 PyJWT 解码并验证 JWT 令牌.

    验证令牌的签名、过期时间和算法，
    对过期和无效令牌分别抛出明确的异常类型。

    Args:
        token: JWT 令牌字符串
        key: 可选的解密密钥，不传则使用默认 JWT_SECRET_KEY

    Returns:
        解码后的 payload 字典

    Raises:
        jwt.ExpiredSignatureError: 令牌已过期
        jwt.InvalidTokenError: 令牌无效（签名错误、格式错误等）
    """
    secret = key if key is not None else settings.JWT_SECRET_KEY
    return jwt.decode(
        token,
        secret,
        algorithms=[AnalysisConfig.JWT_ALGORITHM],
    )


def create_access_token(
    data: dict[str, str],
    expires_delta: timedelta | None = None,
    jti: str | None = None,
) -> str:
    """创建 JWT 访问令牌.

    Args:
        data: 要编码到令牌中的数据（应包含 'sub' 键）
        expires_delta: 自定义过期时间，默认使用配置中的值
        jti: 令牌唯一标识符，不传则自动生成

    Returns:
        编码后的 JWT 字符串
    """
    to_encode: dict[str, Any] = data.copy()
    expire: datetime = datetime.now(UTC) + (
        expires_delta
        or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "jti": jti or _generate_jti(),
        "type": "access",
        "key_version": settings.JWT_KEY_VERSION,
    })
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=AnalysisConfig.JWT_ALGORITHM,
    )


def create_refresh_token(
    data: dict[str, str],
    expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """创建 JWT 刷新令牌并返回令牌字符串和 JTI.

    Args:
        data: 要编码到令牌中的数据（应包含 'sub' 键）
        expires_delta: 自定义过期时间，默认使用配置中的值

    Returns:
        (token_string, jti) 元组
    """
    jti = _generate_jti()
    expire: datetime = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode: dict[str, Any] = data.copy()
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "type": "refresh",
        "key_version": settings.JWT_KEY_VERSION,
    })
    token = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=AnalysisConfig.JWT_ALGORITHM,
    )
    return token, jti


async def create_tokens(username: str) -> TokenPair:
    """创建完整的令牌对（访问令牌 + 刷新令牌）.

    自动将刷新令牌安全存储到数据库中。
    令牌中包含用户角色信息，用于限流策略。
    查询用户信息后写入缓存，减少后续请求的数据库查询。

    Args:
        username: 用户名

    Returns:
        TokenPair 包含 access_token, refresh_token 和 token_type
    """
    async with get_async_db_session() as db:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        user_role = user.role.value if user else "user"
        user_id = user.id if user else None
        if user is not None:
            await cache_user(username, user)

    token_data = {
        "sub": username,
        "role": user_role,
        "user_id": str(user_id) if user_id else "",
    }
    access_token = create_access_token(data=token_data)
    refresh_token_str, refresh_jti = create_refresh_token(data=token_data)

    if user_id is not None:
        async with get_async_db_session() as db:
            db_refresh = RefreshToken(
                jti=refresh_jti,
                token_hash=_hash_token(refresh_token_str),
                user_id=user_id,
                expires_at=datetime.now(UTC)
                + timedelta(
                    days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
                ),
            )
            db.add(db_refresh)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token_str,
    )


async def verify_token_not_blacklisted(token_jti: str) -> None:
    """验证令牌是否未被列入黑名单.

    优先检查内存黑名单集合（O(1) 查找），
    未命中时再查询数据库并同步到内存集合。

    Args:
        token_jti: 令牌的唯一标识符

    Raises:
        HTTPException 401: 令牌已被吊销
    """
    if await is_token_blacklisted(token_jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已被吊销",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with get_async_db_session() as db:
        result = await db.execute(
            select(TokenBlacklist).where(TokenBlacklist.jti == token_jti)
        )
        if result.scalar_one_or_none() is not None:
            await add_token_to_blacklist(token_jti)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已被吊销",
                headers={"WWW-Authenticate": "Bearer"},
            )


def decode_token_with_fallback(token: str) -> dict[str, Any]:
    """使用密钥回退机制解码 JWT 令牌.

    依次尝试当前密钥和前一个密钥（如果有），
    支持密钥轮换期间的平滑过渡。

    Args:
        token: JWT 令牌字符串

    Returns:
        解码后的 payload

    Raises:
        JWTError: 所有密钥都无法验证令牌
    """
    allowed_keys = _get_allowed_keys()
    last_error: Exception | None = None
    for key in allowed_keys:
        try:
            return jwt.decode(
                token,
                key,
                algorithms=[AnalysisConfig.JWT_ALGORITHM],
            )
        except jwt.InvalidTokenError as e:
            last_error = e
            continue
    raise last_error or jwt.InvalidTokenError("无法验证令牌")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    """从 JWT 令牌中获取当前已认证用户.

    作为 FastAPI 依赖项使用，验证令牌有效性、检查黑名单，
    优先从缓存获取用户信息，减少数据库查询。

    Args:
        token: Bearer 令牌

    Returns:
        已认证的用户模型实例

    Raises:
        HTTPException 401: 令牌无效、已吊销或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token_with_fallback(token)
        username: str | None = payload.get("sub")
        token_jti: str | None = payload.get("jti")
        token_type: str | None = payload.get("type")

        if username is None or token_jti is None:
            raise credentials_exception

        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌类型",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.InvalidTokenError as err:
        raise credentials_exception from err

    await verify_token_not_blacklisted(token_jti)

    cached_user = await get_cached_user(username)
    if cached_user is not None:
        if not cached_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用",
            )
        return cached_user

    async with get_async_db_session() as db:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用",
            )
        await cache_user(username, user)
        return user


current_user_dep = Depends(get_current_user)


async def get_optional_current_user(  # noqa: PLR0911
    token: str | None = Depends(
        OAuth2PasswordBearer(
            tokenUrl="/api/auth/login", auto_error=False
        )
    ),
) -> User | None:
    """获取当前用户（可选认证）.

    与 get_current_user 的区别在于不强制要求认证，未登录时返回 None。
    优先从缓存获取用户信息，减少数据库查询。

    Args:
        token: Bearer 令牌（可选）

    Returns:
        已认证的用户实例，未登录返回 None
    """
    if not token:
        return None
    try:
        payload = decode_token_with_fallback(token)
        username: str | None = payload.get("sub")
        token_jti: str | None = payload.get("jti")
        token_type: str | None = payload.get("type")

        if username is None or token_jti is None or token_type != "access":
            return None
    except jwt.InvalidTokenError:
        return None

    try:
        await verify_token_not_blacklisted(token_jti)
    except HTTPException:
        return None

    cached_user = await get_cached_user(username)
    if cached_user is not None:
        return cached_user if cached_user.is_active else None

    async with get_async_db_session() as db:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            if not user.is_active:
                return None
            await cache_user(username, user)
        return user


optional_current_user_dep = Depends(get_optional_current_user)

form_dep = Depends()


@auth_router.post("/login", response_model=TokenPair)
@limiter.limit(AnalysisConfig.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = form_dep,
) -> TokenPair:
    """用户登录端点.

    验证用户名密码，返回包含 access_token 和 refresh_token 的令牌对。
    刷新令牌安全存储在数据库中。
    连续登录失败 5 次将锁定账户 15 分钟。

    Args:
        request: HTTP 请求对象
        form_data: 登录表单（username + password）

    Returns:
        TokenPair: 包含访问令牌和刷新令牌

    Raises:
        HTTPException 401: 用户名或密码错误
        HTTPException 403: 账户已被禁用
        HTTPException 423: 账户已锁定
    """
    # 为 Sentry 提供认证上下文，密码字段绝不发送
    sentry_sdk.set_context(
        "auth_login",
        {
            "username": form_data.username,
            "client_ip": request.client.host if request.client else None,
        },
    )
    sentry_sdk.add_breadcrumb(
        category="auth",
        message="login_attempt",
        level="info",
        data={"username": form_data.username},
    )

    async with get_async_db_session() as db:
        result = await db.execute(
            select(User).where(User.username == form_data.username)
        )
        user = result.scalar_one_or_none()

        if user and user.locked_until and user.locked_until > datetime.now(UTC):
            remaining_seconds = int(
                (user.locked_until - datetime.now(UTC)).total_seconds()
            )
            logger.warning(
                "登录被拒绝: 账户已锁定, username={}, remaining={}s",
                user.username,
                remaining_seconds,
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"账户已锁定，请 {remaining_seconds} 秒后重试",
            )

        if (
            not user
            or not verify_password(
                form_data.password, user.hashed_password
            )
        ):
            if user:
                user.login_failed_count = (user.login_failed_count or 0) + 1
                if user.login_failed_count >= _MAX_LOGIN_FAILED_COUNT:
                    user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
                    logger.warning(
                        "账户已锁定: username={}, failed_count={}",
                        user.username,
                        user.login_failed_count,
                    )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用",
            )

        user.login_failed_count = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)

    if user is not None:
        await cache_user(form_data.username, user)

    return await create_tokens(user.username)  # type: ignore[arg-type]


@auth_router.post("/refresh", response_model=TokenPair)
@limiter.limit("5/minute")
async def refresh_token(
    request: Request,  # noqa: ARG001
    body: RefreshRequest,
) -> TokenPair:
    """刷新令牌端点.

    使用有效的刷新令牌获取新的令牌对（access_token + refresh_token）。
    旧的刷新令牌将被吊销，实现令牌轮换。
    会校验用户存在性、激活状态以及令牌黑名单。

    Args:
        request: HTTP 请求对象
        body: 包含 refresh_token 的请求体

    Returns:
        TokenPair: 新的令牌对

    Raises:
        HTTPException 401: 令牌验证失败、刷新令牌已过期或无效
        HTTPException 403: 用户已禁用、刷新令牌已被吊销
        HTTPException 404: 用户不存在
    """
    try:
        payload = decode_token_with_fallback(body.refresh_token)
        username: str | None = payload.get("sub")
        token_jti: str | None = payload.get("jti")
        token_type: str | None = payload.get("type")
        user_id_str: str | None = payload.get("user_id")

        if not username or not token_jti or token_type != "refresh":
            logger.warning("刷新令牌验证失败: 缺少必要字段或令牌类型不匹配")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌验证失败",
            )
    except jwt.InvalidTokenError as err:
        logger.warning(f"刷新令牌解码失败: {err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌验证失败",
        ) from err

    token_hash = _hash_token(body.refresh_token)

    async with get_async_db_session() as db:
        blacklist_result = await db.execute(
            select(TokenBlacklist).where(TokenBlacklist.jti == token_jti)
        )
        if blacklist_result.scalar_one_or_none() is not None:
            await add_token_to_blacklist(token_jti)
            logger.warning(
                "令牌已被列入黑名单: jti={}, username={}", token_jti, username
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已被列入黑名单",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = None
        if user_id_str and user_id_str.isdigit():
            user_result = await db.execute(
                select(User).where(User.id == int(user_id_str))
            )
            user = user_result.scalar_one_or_none()

        if user is None:
            logger.warning(
                "用户不存在: username={}, user_id={}",
                username,
                user_id_str,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )

        if not user.is_active:
            await clear_user_cache(username)
            logger.warning(
                "用户已被禁用，拒绝令牌刷新: user_id={}, username={}",
                user.id,
                user.username,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用",
            )

        await cache_user(username, user)

        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.jti == token_jti,
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.is_revoked == False,  # noqa: E712
                )
            )
        )
        stored_token = result.scalar_one_or_none()

        if not stored_token:
            await add_token_to_blacklist(token_jti)
            logger.warning(
                "刷新令牌已被吊销: jti={}, username={}",
                token_jti,
                username,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="刷新令牌已被吊销",
            )

        stored_expires = stored_token.expires_at
        if stored_expires is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌已过期或无效",
            )
        if stored_expires.tzinfo is None:
            stored_expires = stored_expires.replace(tzinfo=UTC)
        if stored_expires < datetime.now(UTC):
            logger.warning("刷新令牌已过期: jti={}, username={}", token_jti, username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌已过期",
            )

        stored_token.is_revoked = True
        await add_token_to_blacklist(token_jti)
        logger.info(
            "刷新令牌已轮换: user_id={}, username={}, old_jti={}",
            user.id,
            user.username,
            token_jti,
        )

    return await create_tokens(username)


@auth_router.post("/logout")
async def logout(
    current_user: User = current_user_dep,
    token: str = Depends(oauth2_scheme),
) -> dict[str, str]:
    """用户注销端点.

    将当前访问令牌加入数据库黑名单和内存黑名单集合，
    吊销所有关联的刷新令牌，并清除用户缓存。

    Args:
        current_user: 当前已认证用户
        token: 当前访问令牌

    Returns:
        包含操作结果的字典
    """
    try:
        payload = decode_token_with_fallback(token)
        token_jti = payload.get("jti")
        token_exp = payload.get("exp")

        if token_jti:
            await add_token_to_blacklist(token_jti)
            async with get_async_db_session() as db:
                db_blacklist = TokenBlacklist(
                    jti=token_jti,
                    token_type="access",
                    expires_at=(
                        datetime.fromtimestamp(token_exp, tz=UTC)
                        if token_exp
                        else datetime.now(UTC)
                    ),
                )
                db.add(db_blacklist)

                refresh_result = await db.execute(
                    select(RefreshToken).where(
                        and_(
                            RefreshToken.user_id == current_user.id,
                            RefreshToken.is_revoked == False,  # noqa: E712
                        )
                    )
                )
                for rt in refresh_result.scalars().all():
                    rt.is_revoked = True
                    await add_token_to_blacklist(rt.jti)

    except jwt.InvalidTokenError:
        pass

    await clear_user_cache(current_user.username)  # type: ignore[arg-type]

    return {"message": "注销成功"}


@auth_router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: User = current_user_dep,
) -> User:
    """获取当前登录用户信息."""
    return current_user
