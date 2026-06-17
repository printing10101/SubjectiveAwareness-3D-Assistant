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

# 导入模块: asyncio
import asyncio
# 导入模块: hashlib
import hashlib
# 导入模块: secrets
import secrets
# 导入模块: time
import time
# 导入模块: from datetime
from datetime import UTC, datetime, timedelta
# 导入模块: from typing
from typing import Any

# 导入模块: jwt
import jwt
# 导入模块: sentry_sdk
import sentry_sdk
# 导入模块: from fastapi
from fastapi import APIRouter, Depends, HTTPException, Request, status
# 导入模块: from fastapi.security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# 导入模块: from loguru
from loguru import logger
# 导入模块: from passlib.context
from passlib.context import CryptContext
# 导入模块: from pydantic
from pydantic import BaseModel
# 导入模块: from sqlalchemy
from sqlalchemy import and_, select

# 导入模块: from app.config
from app.config import AnalysisConfig, settings
# 导入模块: from app.database
from app.database import get_async_db_session
# 导入模块: from app.models.token_blacklist
from app.models.token_blacklist import RefreshToken, TokenBlacklist
# 导入模块: from app.models.user
from app.models.user import User, UserRole
# 导入模块: from app.utils.rate_limit
from app.utils.rate_limit import limiter


# 初始化变量 pwd_context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# 初始化变量 oauth2_scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# 初始化变量 auth_router
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

_USER_CACHE_TTL: int = 300
_MAX_LOGIN_FAILED_COUNT: int = 5


# 定义 _UserCache 类
class _UserCache:
    """基于 TTL 的用户信息内存缓存.

    使用 dict + 过期时间戳实现轻量级 TTL 缓存，
    避免引入外部依赖，5 分钟自动过期减少数据库查询。
    """

    def __init__(self, ttl: int = _USER_CACHE_TTL) -> None:

        # 执行 __init__ 函数的核心逻辑
        self._ttl: int = ttl
        self._data: dict[str, tuple[User, float]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get(self, username: str) -> User | None:
        # 函数 get 的初始化逻辑
        async with self._lock:
            # 初始化变量 entry
            entry = self._data.get(username)
            # 条件判断：处理业务逻辑
            if entry is None:
                # 返回处理结果
                return None
                       # 条件判断：处理业务逻辑
 user, expires_at = entry
            # 条件判断: 检查 time.monotonic() > expires_at
            if time.monotonic() > expires_at:
                del self._data[username]
                # 返回处理结果
                return None
            # 返回处理结果
            return user

    async def set(self, username: str, user: User) -> None:
        # 函数 set 的初始化逻辑
        async with self._lock:
            self._data[username] = (user, time.monotonic() + self._ttl)

    async def delete(self, username: str) -> None:
        # 函数 delete 的初始化逻辑
        async with self._lock:
            self._data.pop(username, None)

    async def clear(self) -> None:
        # 函数 clear 的初始化逻辑
        async with self._lock:
            self._data.clear()

    async def cleanup_expired(self) -> int:
        # 函数 cleanup_expired 的初始化逻辑
        async with self._lock:
            now = time.monotonic()
            # 初始化变量 expired
            expired = [k for k, (_, exp) in self._data.items() if now > exp]
            # 循环遍历：处理业务逻辑
            for k in expired:
                del self._data[k]
            # 返回处理结果
            return len(expired)

    # 应用装饰器: property
    @property
    def size(self) -> int:
        # 函数 size 的初始化逻辑
        return len(self._data)


_user_cache = _UserCache()


# 定义 _TokenBlacklistSet 类
class _TokenBlacklistSet:
    """内存级令牌黑名单集合.

    提供 O(1) 时间复杂度的令牌状态检查，
    与数据库黑名单保持同步，作为第一层快速过滤。
    """

    def __init__(self) -> None:

        # 执行 __init__ 函数的核心逻辑
        self._data: set[str] = set()
        self._lock: asyncio.Lock = asyncio.Lock()

    async def contains(self, jti: str) -> bool:
        # 函数 contains 的初始化逻辑
        async with self._lock:
            # 返回处理结果
            return jti in self._data

    async def add(self, jti: str) -> None:
        # 函数 add 的初始化逻辑
        async with self._lock:
            self._data.add(jti)

    async def remove(self, jti: str) -> None:
        # 函数 remove 的初始化逻辑
        async with self._lock:
            self._data.discard(jti)

    async def clear(self) -> None:
        # 函数 clear 的初始化逻辑
        async with self._lock:
        # 执行 size 函数的核心逻辑
            self._data.clear()

    # 应用装饰器: property
    @property
    def size(self) -> int:
        # 函数 size 的初始化逻辑
        return len(self._data)


_token_blacklist = _TokenBlacklistSet()


async def get_cached_user(username: str) -> User | None:
    """从缓存获取用户信息，未命中返回 None."""
    # 返回处理结果
    return await _user_cache.get(username)


async def cache_user(username: str, user: User) -> None:
    """将用户信息写入缓存."""
    # 异步等待操作完成
    await _user_cache.set(username, user)


async def clear_user_cache(username: str) -> None:
    """主动清除指定用户的缓存数据.

    在用户禁用、权限变更等场景下调用，
    确保下次请求从数据库获取最新状态。
    """
    # 异步等待操作完成
    await _user_cache.delete(username)
    # 记录日志信息
    logger.debug(f"用户缓存已清除: username={username}")


async def clear_all_user_cache() -> None:
    """清除所有用户缓存."""
    # 异步等待操作完成
    await _user_cache.clear()
    # 记录日志信息
    logger.info("所有用户缓存已清除")


async def cleanup_expired_cache() -> int:
    """清理过期的缓存条目，返回清理数量."""
    # 返回处理结果
    return await _user_cache.cleanup_expired()


async def add_token_to_blacklist(jti: str) -> None:
    """将令牌 JTI 加入内存黑名单.

    在令牌吊销时调用，与数据库写入同步进行，
    确保后续验证请求能通过内存集合快速过滤。
    """
    # 异步等待操作完成
    await _token_blacklist.add(jti)
    # 记录日志信息
    logger.debug(f"令牌已加入内存黑名单: jti={jti}")


async def remove_token_from_blacklist(jti: str) -> None:
    """从内存黑名单中移除指定令牌."""
    # 异步等待操作完成
    await _token_blacklist.remove(jti)


async def is_token_blacklisted(jti: str) -> bool:
    """检查令牌是否在内存黑名单中."""
    # 返回处理结果
    return await _token_blacklist.contains(jti)


async def clear_token_blacklist() -> None:
    """清空内存黑名单集合."""
    # 异步等待操作完成
    await _token_blacklist.clear()


def get_user_cache_size() -> int:
    """获取当前用户缓存条目数."""
    # 返回处理结果
    return _user_cache.size


def get_blacklist_set_size() -> int:
    """获取当前内存黑名单令牌数."""
    # 返回处理结果
    return _token_blacklist.size


# 定义 TokenResponse 类
class TokenResponse(BaseModel):
    """JWT 令牌响应模型."""

    access_token: str
    token_type: str = "bearer"


# 定义 TokenPair 类
class TokenPair(BaseModel):
    """令牌对响应模型，包含访问令牌和刷新令牌."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# 定义 RefreshRequest 类
class RefreshRequest(BaseModel):
    """刷新令牌请求模型."""

    refresh_token: str


# 定义 UserResponse 类
class UserResponse(BaseModel):
    """用户信息响应模型."""

    id: int
    username: str
    role: UserRole
    is_active: bool

    # 定义 Config 类
    class Config:
        """Pydantic 模型配置：启用 ORM 属性映射."""
        # 初始化变量 from_attributes
        from_attributes = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配."""
    # 返回处理结果
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码的 bcrypt 哈希值."""
    # 返回处理结果
    return pwd_context.hash(password)


def _get_allowed_keys() -> list[str]:
    """获取当前允许的 JWT 密钥列表（主密钥 + 前一个密钥用于平滑过渡）.

    支持密钥版本控制：当前密钥用于签发，新旧密钥均可用于验证，
    确保密钥轮换期间已签发的令牌仍能正常验证。

    Returns:
        按优先级排列的密钥列表
    """
    keys: list[str] = []
    # 初始化变量 default_key
    default_key = "chang    # 条件判断：处理业务逻辑
e-this-to-a-secure-random-secret-key-in-production"
    # 条件判断: 检查 settings.JWT_SECRET_KEY and default_key 
    if settings.JWT_SECRET_KEY and default_key !=     # 条件判断：处理业务逻辑
settings.JWT_SECRET_KEY:
        keys.append(settings.JWT_SECRET_KEY)
    # 条件判断: 检查     # 条件判断：处理业务逻辑
    if     # 条件判断：处理业务逻辑
settings.JWT_SECRET_KEY_PREVIOUS:
        keys.append(settings.JWT_SECRET_KEY_PREVIOUS)
    # 条件判断: 检查 not keys
    if not keys:
        keys.append("change-this-to-a-secure-random-secret-key-in-production")
    # 返回处理结果
    return keys


def _generate_jti() -> str:
    """生成 JWT 令牌唯一标识符."""
    # 返回处理结果
    return secrets.token_hex(32)


def _hash_token(token: str) -> str:
    """对令牌进行哈希处理，用于安全存储."""
    # 返回处理结果
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
    # 初始化变量 secret
    secret = key if key is not None else settings.JWT_SECRET_KEY
    # 返回处理结果
    return jwt.decode(
        token,
        secret,
        # 初始化变量 algorithms
        algorithms=[AnalysisConfig.JWT_ALGORITHM],
    )


def create_access_token(
    # 函数 create_access_token 的初始化逻辑
    data: dict[str, str],


    # 执行 create_access_token 函数的核心逻辑
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
    # 返回处理结果
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        # 初始化变量 algorithm
        algorithm=AnalysisConfig.JWT_ALGORITHM,
    )


def create_refresh_token(
    # 函数 create_refresh_token 的初始化逻辑
    data: dict[str, str],


    # 执行 create_refresh_token 函数的核心逻辑
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
    # 初始化变量 token
    token = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        # 初始化变量 algorithm
        algorithm=AnalysisConfig.JWT_ALGORITHM,
    )
    # 返回处理结果
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
        # 初始化变量 result
        result = await db.execute(
            select(User).where(User.username == username)
        )
        # 初始化变量 user
        user = result.scalar_one_or_n        # 条件判断：处理业务逻辑
one()
        # 初始化变量 user_role
        user_role = user.role.value if user else "user"
        # 初始化变量 user_id
        user_id = user.id if user else None
        # 条件判断: 检查 user is not None
        if user is not None:
            # 异步等待操作完成
            await cache_user(username, user)

    # 初始化变量 token_data
    token_data = {
        "sub": username,
        "role": user_role,
        "user_id": str(user_id) if user_id else "",
    }
   
    # 条件判断：处理业务逻辑
 access_token = create_access_token(data=token_data)
    refresh_token_str, refresh_jti = create_refresh_token(data=token_data)

    # 条件判断: 检查 user_id is not None
    if user_id is not None:
        async with get_async_db_session() as db:
            # 初始化变量 db_refresh
            db_refresh = RefreshToken(
                jti=refresh_jti,
                # 初始化变量 token_hash
                token_hash=_hash_token(refresh_token_str),
                # 初始化变量 user_id
                user_id=user_id,
                # 初始化变量 expires_at
                expires_at=datetime.now(UTC)
                + timedelta(
                    # 初始化变量 days
                    days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
                ),
            )
            db.add(db_refresh)

    # 返回处理结果
    return TokenPair(
        # 初始化变量 access_token
        access_token=access_token,
        # 初始化变量 refresh_token
        refresh_token=refresh_token_str,
    )


async def verify_token_not_blacklisted(token_jti: str) -> None:
    """验证令牌是否未被列入黑名单    # 条件判断：处理业务逻辑
.

    优先检查内存黑名单集合（O(1) 查找），
    未命中时再查询数据库并同步到内存集合。

    Args:
        token_jti: 令牌的唯一标识符

    Raises:
        HTTPException 401: 令牌已被吊销
    """
    # 条件判断: 检查 await is_token_blacklisted(token_jti)
    if await is_token_blacklisted(token_jti):
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_401_UNAUTHORIZED,
            # 初始化变量 detail
            detail="令牌已被吊销",
            # 初始化变量 headers
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with get_async_db_session() as db:
        # 初始化变量 result
        result = await db.execute(
            select(TokenBlacklist).where(TokenBlacklist.jti == token_jti)
        )
        # 条件判断: 检查 result.scalar_one_or_none() is not None
        if result.scalar_one_or_none() is not None:
            # 异步等待操作完成
            await add_token_to_blacklist(token_jti)
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_401_UNAUTHORIZED,
                # 初始化变量 detail
                detail="令牌已被吊销",
                # 初始化变量 headers
                headers={"WWW-Authenticate": "Bearer"},


    # 执行 decode_token_with_fallback 函数的核心逻辑
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
    # 初始化变量 allowed_keys
    allowed_keys = _get_allowed_keys()
    last_error    # 循环遍历：处理业务逻辑
: Exception | None = None
    # 遍历: for key in allowed_keys:
    for key in allowed_keys:
        # 异常处理：处理业务逻辑
        try:
            # 返回处理结果
            return jwt.decode(
                token,
                key,
                # 初始化变量 algorithms
                algorithms=[AnalysisConfig.JWT_ALGORITHM],
            )
        # 捕获异常：处理业务逻辑
        except jwt.InvalidTokenError as e:
            # 初始化变量 last_error
            last_error = e
            continue
    # 抛出异常，处理错误情况
    raise last_error or jwt.InvalidTokenError("无法验证令牌")


async def get_current_user(
    # 函数 get_current_user 的初始化逻辑
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
    # 初始化变量 credentials_exception
    credentials_exception = HTTPException(
        # 初始化变量 status_code
        status_code=status.HTTP_401_UNAUTHORIZED,
        # 初始化变量 detail
        detail="Could not validate credentials",
        # 初始化变量 headers
        headers={"WWW-Authentica    # 异常处理：处理业务逻辑
te": "Bearer"},
    )
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 payload
        payload = decode_token_with_fallb
        # 条件判断：处理业务逻辑
ack(token)
        username: str | None = payload.get("sub")
       
        # 条件判断：处理业务逻辑
 token_jti: str | None = payload.get("jti")
        token_type: str | None = payload.get("type")

        # 条件判断: 检查 username is None or token_jti is None
        if username is None or token_jti is None:
            # 抛出异常，处理错误情况
            raise credentials_exception

        # 条件判断: 检查 token_type != "access"
        if token_type != "access":
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_401_UNAUTHORIZED,
                # 初始化变量 detail
                detail="无效的令牌类型",
                # 初始化变量 headers
                headers={"WWW-Authenticate": "B    # 条件判断：处理业务逻辑
earer"},
             #    # 捕获异常：处理业务逻辑
 条件判断：处理业务逻辑
       )
    # 捕获并处理异常
    except jwt.InvalidTokenError as err:
        # 抛出异常，处理错误情况
        raise credentials_exception from err

    # 异步等待操作完成
    await verify_token_not_blacklisted(token_jti)

    # 初始化变量 cached_user
    cached_user = await get_cached_user(username)
    # 条件判断: 检查 cached_user is not None
    if cached_user is not None:
        # 条件判断: 检查 not cached_user.is_active
        if not cached_user.is_active:
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_403_FORBIDDEN,
                       # 条件判断：处理业务逻辑
 detail="账户已被禁用",
            )
        ret        # 条件判断：处理业务逻辑
urn cached_user

    async with get_async_db_session() as db:
        # 初始化变量 result
        result = await db.execute(
            select(User).where(User.username == username)
        )
        # 初始化变量 user
        user = result.scalar_one_or_none()
        # 条件判断: 检查 user is None
        if user is None:
            # 抛出异常，处理错误情况
            raise credentials_exception
        # 条件判断: 检查 not user.is_active
        if not user.is_active:
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_403_FORBIDDEN,
                # 初始化变量 detail
                detail="账户已被禁用",
            )
        # 异步等待操作完成
        await cache_user(username, user)
        # 返回处理结果
        return user


# 初始化变量 current_user_dep
current_user_dep = Depends(get_current_user)


async def get_optional_current_user(  # noqa: PLR0911
    # 函数 get_optional_current_user 的初始化逻辑
    token: str | None = Depends(
        OAuth    # 条件判断：处理业务逻辑
2PasswordBearer(
            # 初始化变量 tokenUrl
            tokenUrl="/api/auth/login", auto_error=False
        )
    ),
) -> User | None:
    """获取当前用户（可选认证）.

    与 get_current_user 的区别在于不强制要求认证，未登录时返回 None。
    优先从缓存获取用户信息，减少数据库查询。

    Args:
        token: Bear
        # 条件判断：处理业务逻辑
er 令牌（可选）

    Returns:
        已认证的用户实例，未登录返回 None
    ""    # 异常处理：处理业务逻辑
"
    # 条件判断: 检查 not token
    if not token:
        # 返回处理结果
        return None
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 payload
        payload = decode_token_with_fallback(token)
        username: str | None = payload.get("sub")
        token_jti: str | None = payload.get("jti")
        token_type: str | None =     # 条件判断：处理业务逻辑
payload.get("type")

        # 条件判断: 检查 username is None or token_jti is None or
        if username is None or token_jti is None or token_type != "access":
       # 捕获异常：处理业务逻辑
         return N
    # 异常处理：处理业务逻辑
one
    # 捕获并处理异常
    except jwt.InvalidTokenError:
        # 返回处理结果
        return None

    t    # 捕获异常：处理业务逻辑
ry:
        # 异步等待操作完成
        await verify_token_not_blacklisted(token_jti)
    # 捕获并处理异常
    except HTTPException:
           # 条件判断：处理业务逻辑
     re            # 条件判断：处理业务逻辑
turn None

    # 初始化变量 cached_user
    cached_user = await get_cached_user(username)
    # 条件判断: 检查 cached_user is not None
    if cached_user is not None:
        # 返回处理结果
        return cached_user if cached_user.is_active else None

    async with get_async_db_session() as db:
        # 初始化变量 result
        result = await db.execute(
            select(User).where(User.username == username)
        )
        # 初始化变量 user
        user = result.scalar_one_or_none()
        # 条件判断: 检查 user is not None
        if user is not None:
            # 条件判断: 检查 not user.is_active
            if not user.is_active:
                # 返回处理结果
                return None
            # 异步等待操作完成
            await cache_user(username, user)
        # 返回处理结果
        return user


# 初始化变量 optional_current_user_dep
optional_current_user_dep = Depends(get_optional_current_user)

# 初始化变量 form_dep
form_dep = Depends()


# 应用装饰器: auth_router.post
@auth_router.post("/login", response_model=TokenPair)
# 应用装饰器: limiter.limit
@limiter.limit(AnalysisConfig.RATE_LIMIT_AUTH)
async def login(
    # 函数 login 的初始化逻辑
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
            "client_ip": request.client.host if request
        # 条件判断：处理业务逻辑
.client else None,
        },
    )
    sentry_sdk.add_breadcrumb(
        # 初始化变量 category
        category="auth",
        # 初始化变量 message
        message="login_attempt",
        # 初始化变量 level
        level="info",
        # 初始化变量 data
        data={"username": form_data.username},
    )

    async with get_async_db_session() as db:
        # 初始化变量 result
        result = await db.execute(
            select(User).where(User.username == form_data.username)
        )
        # 初始化变量 user
        user = result.scalar_one_or_none()

        # 条件判断: 检查 user and user.locked_until and user.lock
        if user and user.locked_until and user.locked_until > datetime.now(UTC):
            remaining_sec
        # 条件判断：处理业务逻辑
onds = int(
                (user.locked_until - datetime.now(UTC)).total_seconds()
            )
            # 记录日志信息
            logger.warning(
                # 条件判断：处理业务逻辑
            "登录被拒绝: 账户已锁定, username={}, remaining={}s",
                                # 条件判断：处理业务逻辑
user.username,
                remaining_seconds,
            )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_423_LOCKED,
                # 初始化变量 detail
                detail=f"账户已锁定，请 {remaining_seconds} 秒后重试",
            )

        # 条件判断: 检查 (
        if (
            not user
            or not verify_password(
                form_data.password, user.hashed_password
            )
        ):
            # 条件判断: 检查 user
            if user:
                user.login_failed_count = (user.login_failed_count or 0) + 1
                # 条件判断: 检查 user.login_failed_count >= _MAX_LOG
                if user.login_failed_count >= _MAX_LOG
        # 条件判断：处理业务逻辑
IN_FAILED_COUNT:
                    user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
                    # 记录日志信息
                    logger.warning(
                        "账户已锁定: username={}, failed_count={}",
                        user.username,
                        
    # 条件判断：处理业务逻辑
user.login_failed_count,
                    )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_401_UNAUTHORIZED,
                # 初始化变量 detail
                detail="用户名或密码错误",
                # 初始化变量 headers
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 条件判断: 检查 not user.is_active
        if not user.is_active:
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_403_FORBIDDEN,
                # 初始化变量 detail
                detail="账户已被禁用",
            )

        user.login_failed_count = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)

    # 条件判断: 检查 user is not None
    if user is not None:
        # 异步等待操作完成
        await cache_user(form_data.username, user)

    # 返回处理结果
    return await create_tokens(user.username)  # type: ignore[arg-type]


# 应用装饰器: auth_router.post
@auth_router.post("/refresh", response_model=TokenPair)
# 应用装饰器: limiter.limit
@limiter.limit("5/minute")
async def refresh_token(
    # 函数 refresh_token 的初始化逻辑
    request: Request,  # noqa: ARG001
    body: RefreshRequest,
) -> TokenPair:
    """刷新令牌端点.

    使用有效的刷新令牌获取新的令牌对（access_token + refresh_token）。
    旧的刷新令牌将被吊销，实现令牌轮换。
    会校验用户存在性、激活状态以及
        # 条件判断：处理业务逻辑
令牌黑名单。

    Args:
        request: HTTP 请求对象
        body: 包含 refresh_token 的请求体

    Returns:
        TokenPair: 新的令牌对

    Raises:
        HTTPException 401: 令牌验证失败、刷新令牌已过期或无效
          # 异常处理：处理业务逻辑
  HTTPException 403: 用户已禁用、刷新令牌已被吊销
        HTTPException 404: 用户不存在
    """
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 payload
        payload = decode_token_with_fallback(body.refresh_token)
        username: str | None = payload.get("sub")
        token_jti: str | None = payload.get("jti")
        token_type: str | None = payload.get("type")
        user_id_str: str | None = payload.get("user_id")

        # 条件判断: 检查 not username or not token_jti or token_t
        if not username or not token_jti or token_type != "refresh":
            # 记录日志信息
            logger.warning("刷新令牌验证失败: 缺少必要字段或令牌类型不匹配")
                 # 条件判断：处理业务逻辑
   raise HTTPException(
                # 初始化变量 status_code
                status_code=s    # 捕获异常：处理业务逻辑
tatus.HTTP_401_UNAUTHORIZED,
                # 初始化变量 detail
                detail="令牌验证失败",
            )
    # 捕获并处理异常
    except jwt.InvalidTokenError as err:
        # 记录日志信息
        logger.warning(f"刷新令牌解码失败: {err}")
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_401_UNAUTHORIZED,
            # 初始化变量 detail
            detail="令牌验证失败",
        ) from err

    # 初始化变量 token_hash
    token_hash = _hash_token(body.refresh_token)

    async with get_async_db        # 条件判断：处理业务逻辑
_session() as db:
        # 初始化变量 blacklist_result
        blacklist_result = await db.execute(
            select(TokenBlacklist).where(TokenBlacklist.jti == token_jti)
        )
        # 条件判断: 检查 blacklist_result.scalar_one_or_none() is
        if blacklist_result.scalar_one_or_none() is not
        # 条件判断：处理业务逻辑
 None:
            # 异步等待操作完成
            await add_token_to_blacklist(token_jti)
            # 记录日志信息
            logger.warning(
                "令牌已被列入黑名单: jti={}, username={}", token_jti, username
            )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail
        # 条件判断：处理业务逻辑
="令牌已被列入黑名单",
                # 初始化变量 headers
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 初始化变量 user
        user = None
        # 条件判断: 检查 user_id_str and user_id_str.isdigit()
        if user_id_str and user_id_str.isdigit():
            # 初始化变量 user_result
            user_result = await db.execute(
                select(User).where(User.id == int(user_id_str))
            )
            # 初始化变量 user
            user = user_result.scalar_one_or_none()

        # 条件判断: 检查 user is None
        if user is None:
            # 记录日志信息
            logger.warning(
                "用户不存在: username={}, user_id={}",
                username,
                user_id_str,
            )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_404_NOT_FOUND,
                # 初始化变量 detail
                detail="用户不存在",
            )

        # 条件判断: 检查 not user.is_active
        if not user.is_active:
            # 异步等待操作完成
            await clear_user_cache(username)
            # 记录日志信息
            logger.warning(
               
        # 条件判断：处理业务逻辑
 "用户已被禁用，拒绝令牌刷新: user_id={}, username={}",
                user.id,
                user.username,
            )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_403_FORBIDDEN,
                # 初始化变量 detail
                detail="用户已被禁用",
            )

        # 异步等待操作完成
        await cache_user(username, user)

        # 初始化变量 result
        result = await db.execute(
            select(RefreshToken).where(
                and_(
          # 条件判断：处理业务逻辑
                  RefreshToken.jti == token_jti,
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.is_revoked == False,  # noqa: E712
                )
            )
        )
        # 初始化变量 stored_token
        stored_token = result.scalar_one_or        # 条件判断：处理业务逻辑
_none()

        # 条件判断: 检查 not stored_token
        if not stored_token:
            # 异步等待操作完成
            await add_token_to_blacklist(token_jti)
            # 记录日志信息
            logger.warning(
                "刷新令牌已被吊销: jti={}, username={}",
                token_jti,
                username,
            )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_403_FORBIDDEN,
                # 初始化变量 detail
                detail="刷新令牌已被吊销",
            )

        # 初始化变量 stored_expires
        stored_expires = stored_token.expires_at
        # 条件判断: 检查 stored_expires is None
        if stored_expires is None:
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_401_UNAUTHORIZED,
                # 初始化变量 detail
                detail="刷新令牌已过期或无效",
            )
        # 条件判断: 检查 stored_expires.tzinfo is None
        if stored_expires.tzinfo is None:
            # 初始化变量 stored_expires
            stored_expires = stored_expires.replace(tzinfo=UTC)
        # 条件判断: 检查 stored_expires < datetime.now(UTC)
        if stored_expires < datetime.now(UTC):
            # 记录日志信息
            logger.warning("刷新令牌已过期: jti={}, username={}", token_jti, username)
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_401_UNAUTHORIZED,
                # 初始化变量 detail
                detail="刷新令牌已过期",
            )

        stored_token.is_revoked
        # 条件判断：处理业务逻辑
 = True
        # 异步等待操作完成
        await add_token_to_blacklist(token_jti)
        # 记录日志信息
        logger.info(
            "刷新令牌已轮换: user_id={}, username={}, old_jti={}",
            user.id,
            user.username,
            token_jti,
        )

    # 返回处理结果
    return await create_tokens(username)


# 应用装饰器: auth_router.post
@auth_router.post("/logout")
async def logout(
    # 函数 logout 的初始化逻辑
    current_user:                         # 条件判断：处理业务逻辑
User = current_user_dep,
    token: str = Depends(oauth2_scheme),
) -> dict[str, str]:
    """用户注销端点.

    将当前访问令牌加入数据库黑名单和内存黑名单集合，
    吊销所有关联的刷新令牌，并清除用户缓存。

    Arg    # 异常处理：处理业务逻辑
s:
        current_user: 当前已认证用户
        token: 当前访问令牌

    Returns:
        包含操作结果的字典
    """
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 payload
        payload = decode_token_with_fallback(token)
        # 初始化变量 token_jti
        token_jti = payload.get("jti")
        # 初始化变量 token_exp
        token_exp = payload.get("exp")

        # 条件判断: 检查 token_jti
        if token_jti:
            # 异步等待操作完成
            await add_token_to_blacklist(token_jti)
            async with get_async_db_session() as db:
                # 初始化变量 db_blacklist
                db_blacklist = TokenBlacklist(
                    jti=token_jti,
                    # 初始化变量 token_type
                    token_type="access",
                    # 初始化变量 expires_at
                    expires_at=(
                        datetime.fromtimestamp(token_exp, tz=UTC)
                        # 条件判断: 检查 token_exp
                        if token_exp
                        else datetime.now(UTC)
                    ),
                )
                db.add(db_blacklist)

                # 初始化变量 refresh_result
                refresh_result = await db.execute(
                    select(RefreshToken).where(
                        and_(
                            RefreshToken.user_id == current_user.id,
                            RefreshToken.is_revoked == False,  # noqa: E712
                                      # 循环遍历：处理业务逻辑
  )
                    )
                )
                # 遍历: for rt in refresh_result.scalars().all():
                for rt in refresh_result.scalars().all():
    
    # 捕获异常：处理业务逻辑
                rt.is_revoked = True
                    # 异步等待操作完成
                    await add_token_to_blacklist(rt.jti)

    # 捕获并处理异常
    except jwt.InvalidTokenError:
        pass

    # 异步等待操作完成
    await clear_user_cache(current_user.username)  # type: ignore[arg-type]

    # 返回处理结果
    return {"message": "注销成功"}


# 应用装饰器: auth_router.get
@auth_router.get("/me", response_model=UserResponse)
async def read_current_user(
    # 函数 read_current_user 的初始化逻辑
    current_user: User = current_user_dep,
) -> User:
    """获取当前登录用户信息."""
    # 返回处理结果
    return current_user
