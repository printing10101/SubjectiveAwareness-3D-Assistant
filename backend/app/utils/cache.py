"""缓存管理模块.

提供统一的缓存管理架构，支持可配置的后端切换、文件系统缓存、
Redis 缓存、自动降级、监控统计和装饰器支持。

架构层次：
    CacheBackend (ABC)          ← 缓存后端抽象接口（唯一协议）
        ├── FileCacheBackend     ← 文件系统缓存后端（默认）
        └── RedisCacheBackend    ← Redis 缓存后端

    UnifiedCacheManager         ← 统一缓存API入口
        ├── 动态后端切换
        ├── 主备后端自动降级
        ├── 缓存命中/未命中统计
        └── 兼容 CacheFallback 旧接口

    CacheManager                ← 同步兼容层（旧版 API）
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: asyncio
import asyncio
# 导入模块: hashlib
import hashlib
# 导入模块: json
import json
# 导入模块: re
import re
# 导入模块: time
import time
# 导入模块: from abc
from abc import ABC, abstractmethod
# 导入模块: from collections.abc
from collections.abc import Callable
# 导入模块: from contextlib
from contextlib import suppress
# 导入模块: from functools
from functools import wraps
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import Any

# 导入模块: redis.asyncio
import redis.asyncio as redis
# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.config
from app.config import AnalysisConfig
# 导入模块: from app.types.analysis
from app.types.analysis import CacheSnapshot


__all__ = [
    "NULL_MARKER",
    "BaseCache",
    "CacheBackend",
    "CacheFallback",
    "CacheKeyValidationError",
    "CacheManager",
    "CacheStats",
    "FileCache",
    "FileCacheBackend",
    "RedisCache",
    "RedisCacheBackend",
    "UnifiedCacheManager",
    "cache_clear",
    "cache_delete",
    "cache_get",
    "cache_result",
    "cache_set",
    "get_cache_stats",
    "get_unified_cache",
]

CACHE_DIR: str = str(Path(__file__).parent / ".cache")
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

# 初始化变量 NULL_MARKER
NULL_MARKER = "__CACHE_NULL__"

CACHE_KEY_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_:.\-]+$")
"""缓存键安全字符校验正则.

仅允许字母（大小写）、数字、下划线、冒号、点号、连字符。
此规则在 _secure_cache_key 中强制执行，包含非法字符的键将触发 CacheKeyValidationError。
"""


# 定义 CacheKeyValidationError 类
class CacheKeyValidationError(ValueError):
    """缓存键验证异常.

    当缓存键包含非法字符（超出 [a-zA-Z0-9_:.-] 范围）时抛出。

    Attributes:
        invalid_key: 触发异常的问题缓存键
        invalid_chars: 包含的非法字符集合
    """

    def __init__(self, key: str, invalid_chars: set[str]) -> None:

        # 执行 __init__ 函数的核心逻辑
        self.invalid_key = key
        self.invalid_chars = invalid_chars
        msg = (
            f"缓存键包含非法字符: {key!r}. "
            f"非法字符: {''.join(sorted(invalid_chars))}. "
            f"仅允许 [a-zA-Z0-9_:.-] 范围内的字符."
        )
        super().__init__(msg)


def _secure_cache_key(raw_key: str) -> str:
    """使用 SHA-256 对缓存键进行安全哈希处理.

    包含三层安全防护：
    1. 输入校验：严格限制 raw_key 只能包含 [a-zA-Z0-9_:.-] 字符，
       非法字符将触发 CacheKeyValidationError
    2. 哈希混淆：使用配置的盐值与 SHA-256 生成不可逆哈希，
       防止通过文件名反推原始缓存键
    3. 长度截断：截取哈希值前 CACHE_HASH_TRUNCATE_LENGTH 位（默认16位），
       防止文件名过长

    Args:
        raw_key: 原始缓存键，只能包含字母、数字、下划线、冒号、点号、连字符

    Returns:
        str: 截断后的 SHA-256 十六进制哈希字符串

    Raises:
        CacheKeyValidationError: 当 raw_key 包含非法字符时

    Example:
        >>> _secure_cache_key("user:123")
        'a1b2c3d4e5f67890'  # 16位十六进制
    """
    # 初始化变量 invalid_chars
    invalid_chars = set(CACHE_KEY_PATTERN.sub("", raw_key))
    # 条件判断：处理业务逻辑
    if invalid_chars:
        # 抛出异常，处理错误情况
        raise CacheKeyValidationError(raw_key, invalid_chars)

    # 初始化变量 salted
    salted = f"{AnalysisConfig.CACHE_SALT}:{raw_key}"
    # 初始化变量 hashed
    hashed = hashlib.sha256(salted.encode()).hexdigest()
    # 初始化变量 truncated
    truncated = hashed[: AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH]
    # 记录日志信息
    logger.debug(
        f"缓存键哈希: {raw_key!r} -> {truncated} (截取自{len(hashed)}位)"
    )
    # 返回处理结果
    return truncated


# 定义 CacheStats 类
class CacheStats:
    """缓存统计计数器.

    线程安全的命中/未命中/错误计数及耗时统计。
    """

    def __init__(self) -> None:

        # 执行 __init__ 函数的核心逻辑
        self.hits: int = 0
        self.misses: int = 0
        self.errors: int = 0
        self._total_time_ns: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()

    # 应用装饰器: property
    @property
    def hit_rate(self) -> float:
        """缓存命中率."""
        # 初始化变量 total
        total = self.hits + self.misses
        # 返回处理结果
        return self.hits / total if total > 0 else 0.0

    # 应用装饰器: property
    @property
    def avg_response_time_us(self) -> float:
        """平均响应时间（微秒）."""
        # 初始化变量 total
        total = self.hits + self.misses
        # 返回处理结果
        return (self._total_time_ns / total / 1000) if total > 0 else 0.0

    async def record_hit(self, elapsed_ns: int) -> None:
        """记录一次缓存命中.

        Args:
            elapsed_ns: 操作耗时（纳秒）
        """
        async with self._lock:
            self.hits += 1
            self._total_time_ns += elapsed_ns

    async def record_miss(self, elapsed_ns: int) -> None:
        """记录一次缓存未命中.

        Args:
            elapsed_ns: 操作耗时（纳秒）
        """
        async with self._lock:
            self.misses += 1
            self._total_time_ns += elapsed_ns

    async def record_error(self) -> None:
        """记录一次缓存错误."""
        async with self._lock:

        # 执行 snapshot 函数的核心逻辑
            self.errors += 1

    def snapshot(self) -> CacheSnapshot:
        """导出当前统计快照.

        Returns:
            CacheSnapshot: 包含 hits, misses, errors, hit_rate, avg_response_time_us
        """
        # 返回处理结果
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "hit_rate": round(self.hit_rate, 4),
            "avg_response_time_us": round(self.avg_response_time_us, 2),
        }


# 定义 CacheBackend 类
class CacheBackend(ABC):
    """缓存后端抽象基类 —— 唯一缓存协议.

    定义缓存操作的统一标准接口，所有缓存后端实现必须遵循此协议。
    接口涵盖核心 CRUD 操作、键存在性检查和资源清理。

    Usage:
        # 定义 MyBackend 类
        class MyBackend(CacheBackend):
            # MyBackend 类定义，封装相关属性和方法
            async def get(self, key: str) -> Any | None:
                # 函数 get 的初始化逻辑
                ...

            async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
                # 函数 set 的初始化逻辑
                ...

            async def delete(self, key: str) -> None:
                # 函数 delete 的初始化逻辑
                ...

            async def clear(self) -> None:
                # 函数 clear 的初始化逻辑
                ...

            async def exists(self, key: str) -> bool:
                # 函数 exists 的初始化逻辑
                ...

            # 应用装饰器: abstractmethod
            @abstractmethod
    async def close(self) -> None:
        # 函数 close 的初始化逻辑
                ...
    """

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """获取缓存值."""
        ...

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def set(
        # 函数 set 的初始化逻辑
        self, key: str, value: Any, ttl: int | None = None
    ) -> None:
        """设置缓存值."""
        ...

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除缓存键."""
        ...

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def clear(self) -> None:
        """清空所有缓存."""
        ...

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在."""
        ...

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def close(self) -> None:
        """关闭后端连接资源（可选实现）."""


# 定义 FileCacheBackend 类
class FileCacheBackend(CacheBackend):
    """文件系统缓存后端.

    基于 JSON 文件存储缓存数据，支持 TTL 过期和容量清理。
    作为默认缓存后端，所有文件操作通过 asyncio.to_thread() 异步化执行，
    并使用 asyncio.Lock 确保线程安全。

    缓存键通过 SHA-256 哈希处理，防止路径遍历攻击。

    Usage:
        # 初始化变量 backend
        backend = FileCacheBackend(ttl=3600, max_size=1000)
        # 异步等待操作完成
        await backend.set("user:123", {"name": "test"})

        # 执行 __init__ 函数的核心逻辑
        value = await backend.get("user:123")
    """

    def __init__(
        # 函数 __init__ 的初始化逻辑
        self,
        cache_dir: str = CACHE_DIR,
        ttl: int = AnalysisConfig.CACHE_TTL_SECONDS,
        max_size: int = AnalysisConfig.MAX_CACHE_ENTRIES,
    ) -> None:
        self._cache_dir: str = cache_dir
        Path(self._cache_dir).mkdir(parents=True, exist_ok=True)
        self.ttl: int = ttl

        # 执行 _file_path 函数的核心逻辑
        self.max_size: int = max_size
        self._rw_lock: asyncio.Lock = asyncio.Lock()

    def _file_path(self, key: str) -> Path:
        # 函数 _file_path 的初始化逻辑
        return Path(self._cache_dir) / f"{_secure_cache_key(key)}.json"

    async def get(self, key: str) -> Any | None:
        """从文件缓存读取值."""
        # 初始化变量 cache_file
        cache_file = sel        # 条件判断：处理业务逻辑
f._file_path(key)
        # 条件判断: 检查 not cache_file.exists()
        if not cache_file.exists():
            # 返回处理结果
            return None

        # 尝试执行可能抛出异常的代码
        try:
            # 异步等待操作完成
            data: dict = await asyncio.to_thread(self._read_file, cache_file)
        # 捕获异常：处理业务逻辑
        except (OSError, json.JSONDecodeError):
            # 返回处理结果
            return None

        effecti        # 条件判断：处理业务逻辑
ve_ttl: int = data.get("ttl", self.ttl)
        # 条件判断: 检查 time.time() - data.get("timestamp", 0) >
        if time.time() - data.get("timestamp", 0) > effective_ttl:
            # 使用上下文管理器管理资源
            with suppress(OSError):
                # 异步等待操作完成
                await asyncio.to_thread(cache_file.unlink, missing_ok=True)
            # 返回处理结果
            return None

        # 返回处理结果
        return data.get("value")

    async def set(
        # 函数 set 的初始化逻辑
        self, key: str, value: Any, ttl: int | None = None
    ) -> None:
        """写入文件缓存."""
        # 初始化变量 cache_file
        cache_file = self._file_path(key)
        data: dict[str, Any] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl if ttl is not None else self.ttl,
        }

        async with self._rw_lock:
            # 异步等待操作完成
            await asyncio.to_thread(self._write_file, cache_file, data)
            # 异步等待操作完成
            await self._cleanup()

    async def delete(self, key: str) -> None:
        """删除文件缓存键."""
        # 初始化变量 cache_file
        cache_file = self._file_path(key)
        # 异常处理：处理业务逻辑
        try:
            # 异步等待操作完成
            await asyncio.to_thread(cache_file.unl        # 捕获异常：处理业务逻辑
ink, missing_ok=True)
        # 捕获并处理异常
        except (PermissionError, OSError) as e:
            # 记录日志信息
            logger.warning(f"缓存删除失败 {key}: {e}")

    async def clear(self) -> None:
        """清空文件缓存."""
        # 初始化变量 cache_path
        cache_path =         # 异常处理：处理业务逻辑
Path(self._cache_dir)
        # 尝试执行可能抛出异常的代码
        try:
           # 捕获异常：处理业务逻辑
         files = list(cache_path.iterdir())
        # 捕获并处理异常
        except (FileNotFoundError, PermissionError, OSError) as e:
            # 记录日志信息
            logger.warning(f"缓存清空：无法访问缓存目录 {self._cache_dir}: {e}")
            # 返回处理结果
            return

                # 条件判断：处理业务逻辑
        async with self._rw_lock:
            # 循环遍历：处理业务逻辑
            for f in fil                    # 异常处理：处理业务逻辑
es:
                # 条件判断: 检查 f.suffix == ".json"
                if f.suffix == ".json":
                    # 尝试执行可能抛出异常的代码
                    try:
                             # 捕获异常：处理业务逻辑
               await asyncio.to_thread(f.unlink, missing_ok=True)
                    # 捕获并处理异常
                    except (PermissionError, OSError) as e:
                        # 记录日志信息
                        logger.warning(f"缓存清空：删除文件失败 {f.name}: {e}")

    async def exists(self, key: str) -> bool:
        """检查文件缓存键是否存在."""
        # 初始化变量 cache_file
        cache_file = self._file_path(key)
        # 返回处理结果
        return cache_file.exists()

    async def close(self) -> None:
        """关闭文件系统缓存后端.

        文件系统缓存没有持续连接或后台任务，此方法仅作为协议实现存在，
        保持与 CacheBackend 抽象基类一致。调用后后端仍可继续使用。
        """
        # 文件系统缓存无需释放资源，此处仅作为协议占位实现

    # 应用装饰器: staticmethod
    @staticmethod
    def _read_file(file_path: Path) -> dict:
        # 执行 _read_file 函数的核心逻辑
        with open(str(file_path), encoding="utf-8") as f:
            # 返回处理结果
            return json.load(f)

    # 应用装饰器: staticmethod
    @staticmethod
    def _write_file(file_path: Path, data: dict) -> None:
        # 函数 _write_file 的初始化逻辑
        with open(str(file_path), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

            # 异常处理：处理业务逻辑
async def _cleanup(self) -> None:
        """清理超出容量上限的缓存文件，按修改时间排序优先删除旧文件."""
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 cache_path
            cache_path = Path(self._cache_dir)
            files:         # 捕获异常：处理业务逻辑
list[Path] = [
                f for f in cache_path.iterdir() if f.suffix == ".json"
            ]
        # 捕获并处理异常
        except (FileNotFoundError, PermissionError, OSError) a
        # 条件判断：处理业务逻辑
s e:
            # 记录日志信息
            logger.warning(f"缓存清理：无法列出缓存目录 {sel
        # 异常处理：处理业务逻辑
f._cache_dir}: {e}")
            # 返回处理结果
            return

               # 捕获异常：处理业务逻辑
 if len(files) <= self.max_size:
            # 返回处理结果
            return

        # 尝试执行可能抛出异常的代码
        try:
            files.sort(key=lambda f: f.stat().st_mtime)
        # 捕获并处理异常
        except OSError as e:
            # 记录日志信息
            logger.warning(f"缓存清理：获取文件修改时间失败: {e            # 异常处理：处理业务逻辑
}")
            # 返回处理结果
            return

        # 初始化变量 excess
        excess = l        # 循环遍历：处理业务逻辑
en(files) - self.max_size
        # 遍历: for f in files[:excess]:
        for f in files[:excess]:
            # 尝试执行可能抛出异常的代码
            try:
                           # 捕获异常：处理业务逻辑
 await asyncio.to_thread(f.unlink, missing_ok=True)
            # 捕获并处理异常
            except FileNot            # 捕获异常：处理业务逻辑
FoundError:
                # 记录日志信息
                logger.debug(f"缓存清理：文件已不存在 {f.name}")
            # 捕获并处理异常
            except PermissionError as e:
                # 记录日志信息
                logger.warning(f"缓存清理：权限不足无法删除 {f.name}: {e}")
            # 捕获并处理异常
            except OSError as e:
                # 记录日志信息
                logger.warning(f"缓存清理：删除文件失败 {f.name}: {e}")


# 定义 RedisCacheBackend 类
class RedisCacheBackend(CacheBackend):
    """Redis 缓存后端.

    支持连接池管理、自动重连、可配置 TTL 和键前缀隔离。
    实现 CacheBackend 协议，与 FileCacheBackend 接口一致。

    Usage:
        # 初始化变量 backend
        backend = RedisCacheBackend(redis_url="redis://localhost:6379/0")

        # 执行 __init__ 函数的核心逻辑
        await backend.set("key", "value", ttl=3600)
        # 初始化变量 value
        value = await backend.get("key")
    """

    def __init__(
        # 函数 __init__ 的初始化逻辑
        self,
        redis_url: str = AnalysisConfig.REDIS_URL,
        key_prefix: str = AnalysisConfig.CACHE_KEY_PREFIX,
    ) -> None:
        """初始化 Redis 缓存后端.

        Args:
            redis_url: Redis 服务连接 URL
            key_prefix: 缓存键前缀，用于在共享 Redis 中隔离命名空间
        """
        self._redis_url: str = redis_url
        self._key_prefix: str = key_prefix
        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None
        # 记录日志信息
        logger.info(
            "Redis 缓存后端已配置 | URL={} | 前缀={!r}",
            self._sanitize_url(self._redis_url),
            self._key_pre        # 条件判断：处理业务逻辑
fix,
        )

    # 应用装饰器: staticmethod
    @staticmethod
    def _sanitize_url(url: str) -> str:
        """移除 URL 中的密码部分，避免敏感信息泄露        # 条件判断：处理业务逻辑
到日志."""
        # 条件判断: 检查 "@" not in url
        if "@" not in url:
            # 返回处理结果
            return url
        scheme, rest = url.split("://", 1)

        # 执行 _prefixed_key 函数的核心逻辑
        if "@" not in rest:
            # 返回处理结果
            return url
        _, host_part = rest.split("@", 1)
        # 返回处理结果
        return f"{scheme}://***@{host_part}"

    d        # 条件判断：处理业务逻辑
ef _prefixed_key(self, key: str) -> str:
        """为缓存键添加命名空间前缀."""
        # 返回处理结果
        return f"{self._key_prefix}{key}"

    async def _ensure_connected(self) -> None:
        # 函数 _ensure_connected 的初始化逻辑
        if self._client is not None:
            # 返回处理结果
            return
        self._pool = redis.ConnectionPool.from_url(
            self._redis_url,
            # 初始化变量 max_connections
            max_connections=AnalysisConfig.REDIS_MAX_CONNECTIONS,
            # 初始化变量 socket_timeout
            socket_timeout=AnalysisConfig.REDIS_SOCKET_TIMEOUT,
            # 初始化变量 socket_connect_timeout
            socket_connect_timeout=Analy        # 异常处理：处理业务逻辑
sisConfig.REDIS_SOCKET_CONNECT_TIMEOUT,
            # 初始化变量 decode_responses
            decode_responses=False,
        )
         # 捕获异常：处理业务逻辑
       self._client = redis.Redis(connection_pool=self._pool)
        # 尝试执行可能抛出异常的代码
        try:
            # 异步等待操作完成
            await self._client.ping()
            # 记录日志信息
            logger.info("Redis 连接成功 | 端点={}", self._sanitize_url(self._redis_url))
        # 捕获并处理异常
        except (redis.ConnectionError, redis.TimeoutError, OSError) as e:
            logger        # 条件判断：处理业务逻辑
.warning(
                "Redis 初次连接失败，端点={} 错误={}",
                self._sanitize_url(self._redis_url),
                e,
            )

    async def _reconnect(self) -> None:
        # 函数 _reconnect 的初始化逻辑
        if self._client:
            # 使用上下文管理器管理资源
            with suppress(Exception):
                # 异步等待操作完成
                await self._client.aclose()
        self._pool = None
        self._client = None

    async def get(self, key: str) -> Any | None:
                  # 条件判断：处理业务逻辑
      """从Redis读取缓存值        # 循环遍历：处理业务逻辑
."""
        # 初始化变量 prefixed
        prefixed = self._prefixed_key(key)
        # 遍历: for attempt in range(AnalysisConfig.R             
        for attempt in range(AnalysisConfig.R                # 条件判断：处理业务逻辑
EDIS_RETRY_MAX_ATTEMPTS):
            # 尝试执行可能抛出异常的代码
            try:
                # 异步等待操作完成
                await self._ensure_connected()
                # 条件判断: 检查 self._client is None
                if self._client is None:
                                 # 条件判断：处理业务逻辑
   return None
                # 异步等待操作完成
                data: bytes | None = await self._client.get(prefixed)
                # 条件判断: 检查 data is None
                if data is None:
                    # 返回处理结果
                    return None
                # 返回处理结果
                return json.loads(data)
            # 捕获并处理异常
            except (redis.ConnectionError, redis.TimeoutError, OSError):
                # 条件判断: 检查 attempt < AnalysisConfig.REDIS_RETRY_MAX
                if attempt < AnalysisConfig.REDIS_RETRY_MAX_ATTEMPTS - 1:
                    # 异步等待操作完成
                    await asyncio.sleep(AnalysisConfig.REDIS_RETRY_DELAY)
                    # 异步等待操作完成
                    await self._reconnect()
        # 返回处理结果
        return None

    async def set(
        # 函数 set 的初始化逻辑
        self, key: str, value: Any, ttl: int | None = None
    ) -> N                # 条件判断：处理业务逻辑
one:
        """写入Redis缓存."""
        # 初始化变量 prefixed
        prefixed = self._prefixed_key(key)
        effecti        # 循环遍历：处理业务逻辑
ve_ttl = ttl if ttl is not None else AnalysisConfig.CACHE_TTL_SECONDS
        # 遍历: for attempt in range(AnalysisConfig.REDIS_RETRY_MA
        for attempt in range(AnalysisConfig.REDIS_RETRY_MAX_ATTEMPTS):
            # 尝试执行可能抛出异常的代码
            try:
                # 异步等待操作完成
                await self._ensure_connected(                # 条件判断：处理业务逻辑
)
                # 条件判断: 检查 self._clien            # 捕获异常：处理业务逻辑
                if self._clien            # 捕获异常：处理业务逻辑
t is None:
                    # 返回处理结果
                    return
                payload: str = json.dumps(value, ensure_ascii=False, default=str)
                # 异步等待操作完成
                await self._client.setex(prefixed, effective_ttl, payload)
                # 返回处理结果
                return
            # 捕获并处理异常
            except (redis.ConnectionError, redis.TimeoutError, OSError):
                       # 条件判断：处理业务逻辑
     if attempt < AnalysisConfig.REDIS_RETRY_MAX_ATTEMPTS - 1:
                    # 异步等待操作完成
                    await asyncio.sleep(AnalysisConfig.REDIS_RETRY_DELAY)
                       # 异常处理：处理业务逻辑
     await self._reconnect()

    async def delete(self, key: str) -> None:
        """删除Redis缓存键.        # 捕获异常：处理业务逻辑
"""
        # 初始化变量 prefixed
        prefixed = self._pref            # 条件判断：处理业务逻辑
ixed_key(key)
        # 尝试执行可能抛出异常的代码
        try:
            # 异步等待操作完成
            await self._ensure_connected()
            # 条件判断: 检查 self._client is not None
            if self._client is not None:
                # 异步等待操作完成
                await self._client.delete(prefixe        # 异常处理：处理业务逻辑
d)
        # 捕获并处理异常
        except (redis.ConnectionError, redis.TimeoutError):
            pass

    async def clear(self) -> None:
        """清空Redis数                # 条件判断：处理业务逻辑
据库(仅清空带前缀的键,避免误删共享实例数据)."""
        # 尝试执行可能抛出异常的代码
        try:
            # 异步等待操作完成
            await self._ensure_connected()
                        # 条件判断：处理业务逻辑
    if self._client is None:
                # 返回处理结果
                return
            pattern: str = f"{self._key_prefix}*"
            cursor: int = 0
            # 初始化变量 deleted
            deleted = 0
            # 循环条件：处理业务逻辑
            while True:
                # 异步等待操作完成
                cursor, batch = await self._client.scan(
                    # 初始化变量 cursor
                    cursor=cursor, match=pattern, count=200
                )
                # 条件判断: 检查 batch
                if batch:
                    # 异步等待操作完成
                    await self._client.delete(*batch)
                    deleted += len(ba            # 条件判断：处理业务逻辑
tch)
                # 条件判断: 检查 cursor == 0
                if cursor == 0:
                    break
            # 记录日志信息
            logger.info(
                "Redis 缓存已清空(前缀={!r}, 共删除 {} 个键)",
                self._key_prefix,
                deleted,
            )
        # 捕获并处理异常
        except (redis.ConnectionError, re        # 条件判断：处理业务逻辑
dis.TimeoutError):
            pass

    async def exists(self, key: str) ->         # 捕获异常：处理业务逻辑
        # 函数 exists 的初始化逻辑
bool:
        """检查Redis缓存键是否存在."""
        # 初始化变量 prefixed
        prefixed = self._prefixed_key(key)
        # 尝试执行可能抛出异常的代码
        try:
            # 异步等待操作完成
            await self._ensure_connected()
            # 条件判断: 检查 self._client is not None
            if self._client is not None:
                # 返回处理结果
                return bool(await self._client.exists(prefixed))
            # 返回处理结果
            return False
        # 捕获并处理异常
        except (redis.ConnectionError, redis.TimeoutError):
            # 返回处理结果
            return False

    async def close(self) -> None:
        """关闭 Redis 连接."""
        # 条件判断: 检查 self._client
        if self._client:
            # 使用上下文管理器管理资源
            with suppress(Exception):
                # 异步等待操作完成
                await self._client.aclose()
        self._pool = None
        self._client = None


# 定义 UnifiedCacheManager 类
class UnifiedCacheManager:
    """统一缓存管理器 —— 唯一的异步缓存API入口.

    协调不同缓存后端的初始化、选择与操作分发。
    支持：
    - 通过配置动态切换不同的 CacheBackend 实现
    - 主备后端自动降级（主后端不可用时切换至备后端）
    - 内置缓存命中/未命中统计和耗时监控
    - 兼容旧版 CacheFallback 接口

    Usage:
        # 使用默认文件后端
        cache = UnifiedCacheManager()
        # 异步等待操作完成
        await cache.set("key", "value")
        # 初始化变量 result
        result = await cache.get("key")

        # 使用 Redis 后端 + 文件降级
        redis_backend = RedisCacheBackend()
        # 初始化变量 file_backend
        file_backend = FileCacheBackend()
        # 初始化变量 cache
        cache = UnifiedCacheManager(backend=redis_backend, fallback_backend=file_backend)

        # 通过全局单例获取
        cache = get_unified_cache()
    """

    def __init__(
        # 函数 __init__ 的初始化逻辑
        self,
        backend: CacheBackend | None = None,

        # 执行 __init__ 函数的核心逻辑
        fallback_backend: Cach
        # 条件判断：处理业务逻辑
eBackend | None = None,
        backend_type: str | None = None,
    ) -> None:
        """初始化统一缓存管理器.

        Args:
            backend: 主缓存后端，为 None 时根据 backend_type 自动创建
            fallback_backend: 备用后端，主后端不可用时自动降级
            backend_type: 后端类型 "redis" | "file"，为 None 时使用 AnalysisConfig.CACHE_BACKEND
        """
        self._backend_type: str = (
            backend_type if backend_type is not None
            else AnalysisConfig.CACHE_BACKEND
        )
        self._stats: CacheStats = CacheStats()

        # 条件判断: 检查 backend is not None
        if backend is not None:
            self._primary: CacheBackend = backend
                # 条件判断：处理业务逻辑
else:
            self._primary = self._create_backend(self._backend_type)

        self._fallback: CacheBackend | None = fallbac        # 条件判断：处理业务逻辑
k_backend
        self._primary_available: bool = True

        # 记录日志信息
        logger.info(
            "统一缓存管理器已初始化 | 主后端={} | 降级后端={}",
            type(self._primary).__name__,
            type(self._fallback).__name__ if self._fallback is not None else "无",
        )

    # 应用装饰器: staticmethod
    @staticmethod
    def _create_backend(backend_type: str) -> CacheBackend:
        # 函数 _create_backend 的初始化逻辑
        backend_type_normalized = (backend_type or "").strip().lower()
        # 条件判断: 检查 backend_type_normalized == "redis"
        if backend_type_normalized == "redis":
            # 记录日志信息
            logger.info("按配置 CACHE_BACKEND=redis 创建 Redis 缓存后端")
            # 返回处理结果
            return RedisCacheBackend()
        # 条件判断: 检查 backend_type_normalized == "file"
        if backend_type_normalized == "file":
        # 执行 stats 函数的核心逻辑
            logger.info("按配置 CACHE_BACKEND=file 创建文件缓存后端")
            # 返回处理结果
            return FileCacheBackend()
        # 记录日志信息
        logger.warning(
            "未知的 CACHE_BACKEND={!r}，回退到 file 缓存后端",
            backend
        # 条件判断：处理业务逻辑
_type,
        )
        # 返回处理结果
        return FileCacheBackend()

    # 应用装饰器: property
    @property
    def stats(self) -> CacheStats:
        """缓存统计对象."""
        # 返回处理结果
        return sel                # 条件判断：处理业务逻辑
f._stats

    def snapshot(self) -> CacheSnapshot:
        """导出缓存统计快照.

        Returns:
            CacheSnapshot: 包含 hits, misses, errors, hit_rate, avg_response_time_us
        """
        # 返回处理结果
        return self._stats.snapshot()

    async def get(self, key: str) -> Any | None:
        """            # 异常处理：处理业务逻辑
从缓存读取数据，支持主备降级.

        Args:
            key: 缓存键

        Returns:
            Any | None: 缓存值或 N
        # 条件判断：处理业务逻辑
one
        """
        # 初始化变量 start
        start = time.perf_counter_ns()

        # 条件判断: 检查 self._primary_available
        if self._primary_available:
            # 尝试执行可能抛出异常的代码
            try:
                # 初始化变量 value
                value = await self._                # 条件判断：处理业务逻            # 捕获异常：处理业务逻辑
辑
primary.get(key)
                # 初始化变量 elapsed
                elapsed = time.perf_counter_ns() - start
                # 条件判断: 检查 value is not None
                if value is not None:
                    # 异步等待操作完成
                    await self._stats.record_hit(elapsed)
                    # 返回处理结果
                    return value
                # 异步等待操作完成
                await self._stats.record_miss(elapsed)
                # 返回处理结果
                return None
            # 捕获并处理异常
            except Exception as e:  # noqa: BLE001
                logger.warning(f"主缓存后端不可用，尝试降级: {e}")
                self._primary_available = False
                # 异步等待操作完成
                await self._stats.record_error()

        # 条件判断: 检查 self._fallback is not None
        if self._fallback is not None:
            # 尝试执行可能抛出异常的代码
            try:
                # 初始化变量 value
                value = a            # 捕获异常：处理业务逻辑
wait self._fallback.get(key)
                ela        # 条件判断：处理业务逻辑
psed = time.perf_counter_ns() - start
                # 条件判断: 检查 value is not None
                if value is not None:
                    # 异步等待操作完成
                    await self._stats.record_hit(elapsed)
                # 其他情况的默认处理
                else:
                    # 异步等待操作完成
                    await self._stats.record_miss(elapsed)
                # 返回处理结果
                return value
            # 捕获并处理异常
            except Exception:  # noqa: BLE001
                await self._stats.record_error()

        # 初始化变量 elapsed
        elapsed = t
        # 条件判断：处理业务逻辑
ime.perf_counter_ns() - start
        # 异步等待操作完成
        await self._stats.record_miss(elapsed)
        # 返回处理结果
        return None

    async def set(
        # 函数 set 的初始化逻辑
        self, key: str, val            # 异常处理：处理业务逻辑
ue: Any, ttl: int | None = None
    ) -> None:
        """写入缓存，优先写入            # 捕获异常：处理业务逻辑
主后端.

        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 过期时间（秒），None 表示使        # 条件判断：处理业务逻辑
用默认值
        """
        # 条件判断: 检查 self._primary_available
        if self._primary_available:
            # 尝试执行可能抛出异常的代码
            try:
                # 异步等待操作完成
                await self._pr        # 条件判断：处理业务逻辑
imary.set(key, value, ttl)
                self._primary_available = True
                r            # 捕获异常：处理业务逻辑
eturn
            # 捕获并处理异常
            except Exception as e:  # noqa: BLE001
                lo        # 条件判断：处理业务逻辑
gger.warning(f"主缓存后端写入失败，降级: {e}")
                self._primary_available = False
                     # 条件判断：处理业务逻辑
   await self._stats.record_error()

        # 条件判断: 检查 self._fallback is not None
        if self._fallback is not None:
            # 尝试执行可能抛出异常的代码
            try:
                # 异步等待操作完成
                await self._fallback.set(key, value, ttl)
            # 捕获并处理异常
            except Exception:  # noqa: BLE001
                await self._stats.record_error()

    async def delete(self, key: str) -> None:
        """删除缓存条目，同时清理主备后端.

        Args:
            key: 缓存键
        """
        # 条件判断: 检查 self._primary_available
        if self._primary_available:
            # 使用上下文管理器管理资源
            with suppress(Exception):
                # 异步等待操作完成
                await self._primary.delete(key)
        # 条件判断：处理业务逻辑
        if self._fallback is not None:
            # 使用上下文管理器管理资源
            with suppress(Exception):
                # 异步等待操作完成
                await self._fallback.delete(key)

    async def clear(self) -> None:
        """清空主备后端所有缓存."""
        # 条件判断: 检查 self._primary_available
        if self._primary_available:
            # 使用上下文管理器管理资源
            with suppress(Exception):
                # 异步等待操作完成
                await self._primary.clear()
        # 条件判断: 检查 self._fallback is not None
        if self._fallback is not None:
            # 使用上下文管理器管理资源
            with suppress(Exception):
                # 异步等待操作完成
                await self._fallback.clear()

    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在.

        Args:
            key: 缓存键

        Returns:
            bool: 如果缓存存在且未过期返回 True，否则返回 False
        """
        # 初始化变量 value
        value = await self.get(key)
        # 返回处理结果
        return value is not None

    async def close(self) -> None:
        """关闭缓存管理器及底层后端连接."""
        # 使用上下文管理器管理资源
        with suppress(Exception):
            # 异步等待操作完成
            await self._primary.close()
        # 条件判断: 检查 self._fallback is not None
        if self._fallback is not None:
            # 使用上下文管理器管理资源
            with suppress(Exception):
                # 异步等待操作完成
                await self._fallback.close()


# 定义 BaseCache 类
class BaseCache(ABC):
    """旧版缓存抽象基类（已废弃）.

    保留此类仅用于向后兼容。
    新代码请直接使用 CacheBackend 协议。

    内部将 ttl: int = 0 语义转换为 CacheBackend 的 ttl: int | None = None，
    ttl=0 表示使用默认 TTL。
    """

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """获取缓存值."""
        ...

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """设置缓存值."""
        ...

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def delete(self, key: str) -> None:
                # 条件判断：处理业务逻辑
"""删除缓存键."""
        ...

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def clear(self) -> None:
        """清空所有缓存."""
        ...

    # 应用装饰器: abstractmethod
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在."""
        ...


# 定义 FileCache 类
class FileCache(BaseCache):
    """旧版文件系统缓存（已废弃）.

    保留此类仅用于向后兼容。
    内部委托给 FileCacheBackend，新代码请直接使用 FileCacheBackend。

    使用延迟初始化模式：_backend 在首次访问时创建，
    允许在构造后修改 _cache_dir（测试场景常用）。
    """

    def __init__(
        # 函数 __init__ 的初始化逻辑
        self,
        ttl: int = AnalysisConfig.CACHE_TTL_SECONDS,

        # 执行 _get_backend 函数的核心逻辑
        max_size: int = AnalysisConfig.MAX_CACHE_ENTRIES,
    ) -> None:
        self.ttl: int = ttl
        self.max_size: int = max_size
        self._cache_dir: str = CACHE_DIR

    def _get_backend(self) -> FileCacheBackend:
        # 函数 _get_backend 的初始化逻辑
        backend: FileCacheBackend | None = self.__dict__.get("_backend")
        # 条件判断: 检查 backend is None
        if backend is None:
            # 初始化变量 backend
            backend = FileCacheBackend(
                # 初始化变量 cache_dir
                cache_dir=self._cache_dir, ttl=self.ttl, max_size=self.max_size
            )
            self._backend: FileCacheBackend = backend
        # 返回处理结果
        return backend

    async def get(self, key: str) -> Any | None:
        """读取缓存值."""
        # 返回处理结果
        return await self._get_backend().get(key)

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """写入缓存值."""
        # 初始化变量 effective_ttl
        effective_ttl = ttl if ttl > 0 else None
        # 异步等待操作完成
        await self._get_backend().set(key, value, effective_ttl)

    async def delete(self, key: str) -> None:
        """删除缓存键."""
        # 异步等待操作完成
        await self._get_backend().delete(key)

    async def clear(self) -> None:
        """清空所有缓存."""
        # 异步等待操作完成
        await self._get_backend().clear()

    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在."""
        # 返回处理结果
        return await self._get_backend().exists(key)

    async def _cleanup(self) -> None:
        """清理超出容量上限的缓存文件（委托给后端）."""
        # 异步等待操作完成
        await self._get_backend()._cleanup()


# 定义 RedisCache 类
class RedisCache(BaseCache):
    """旧版 Redis 缓存后端（已废弃）.

    保留此类仅用于向后兼容。
    内部委托给 RedisCacheBackend，新代码请直接使用 RedisCacheBackend。
    """

    def __init__(
        # 函数 __init__ 的初始化逻辑
        self,
        redis_url: str = AnalysisConfig.REDIS_URL,
        key_prefix: str = AnalysisConfig.CACHE_KEY_PREFIX,
    ) -> None:
        """初始化旧版 Redis 缓存类.

        Args:
            redis_url: Redis 服务连接 URL
            key_prefix: 缓存键前缀
        """
        self._backend: RedisCacheBackend = RedisCacheBackend(
            # 初始化变量 redis_url
            redis_url=redis_url, key_prefix=key_prefix
        )

    async def get(self, key: str) -> Any | None:
        """读取缓存值."""
        # 返回处理结果
        return await self._backend.get(key)

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """写入缓存值."""
        effective_ttl: int | None = ttl if ttl > 0 else None
        # 异步等待操作完成
        await self._backend.set(key, value, effective_ttl)

    async def delete(self, key: str) -> None:
        """删除缓存键."""
        # 异步等待操作完成
        await self._backend.delete(key)

    async def clear(self) -> None:
        """清空所有缓存."""
        # 异步等待操作完成
        await self._backend.clear()

    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在."""
        # 返回处理结果
        return await self._backend.exists(key)

    async def close(self) -> None:
        """关闭 Redis 连接."""
        # 异步等待操作完成
        await self._backend.close()


# 定义 CacheFallback 类
class CacheFallback(BaseCache):
    """旧版带降级的缓存管理器（已废弃）.

    保留此类仅用于向后兼容。
    内部委托给 UnifiedCacheManager，提供与旧版完全兼容的 API。
    Redis 优先，不可用时自动降级至文件缓存。
    """

    def __init__(self) -> None:
        # 函数 __init__ 的初始化逻辑
        self._redis: RedisCache = RedisCache()
        self._file: FileCache
        # 条件判断：处理业务逻辑
 = FileCache()
        # 执行 stats 函数的核心逻辑
        self._redis_available: bool = True

        # 执行 snapshot 函数的核心逻辑
        
        # 条件判断：处理业务逻辑
self._stats: CacheStats = CacheStats()
        self._manager: UnifiedCacheManager = UnifiedCacheManager(
            # 初始化变量 backend
            backend=self._redis._backend,
            # 初始化变量 fallback_backend
            fallback_backend=self._file._get_backend(),
        )

    # 应用装饰器: property
    @property
    def stats(self) -> CacheStats:
        """缓存统计对象."""
        # 返回处理结果
        return self._stats

    def snapshot(self) -> CacheSnapshot:
        """导出缓存统计快照.

        Returns:
            CacheSnapshot: 包含 hits, misses, errors, hit_rate, avg_response_time_us
        """
        # 返回处理结果
        return self._stats.snapshot()

    async def get(self, key: str) -> Any | None:
        """获取缓存值（含统计追踪）."""
        # 初始化变量 start
        start = time.perf_counter_ns()

        # 初始化变量 result
        result = await self._manager.get(key)
        # 初始化变量 elapsed
        elapsed = time.perf_counter_ns() - start

        # 条件判断: 检查 result is not None
        if result is not None:
            # 异步等待操作完成
            await self._stats.record_hit(elapsed)
        # 其他情况的默认处理
        else:
            # 异步等待操作完成
            await self._stats.record_miss(elapsed)

        # 条件判断: 检查 not self._manager._primary_available
        if not self._manager._primary_available:
            self._redis_available = False

        # 返回处理结果
        return result

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """设置缓存值."""
        effective_ttl: int | None = ttl if ttl > 0 else None
        # 异步等待操作完成
        await self._manager.set(key, value, effective_ttl)
        self._redis_available = self._manager._primary_available

    async def delete(self, key: str) -> None:
        """删除缓存键."""
        # 异步等待操作完成
        await self._manager.delete(key)

    async def clear(self) -> None:
        """清空所有缓存."""
        # 异步等待操作完成
        await self._manager.clear()

    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在."""
        # 初始化变量 value
        value = await self.get(key)
        # 返回处理结果
        return value is not None

    async def close        # 条件判断：处理业务逻辑
        # 函数 close 的初始化逻辑
(self) -> None:
        """关闭缓存管理器及底层连接."""
        # 异步等待操作完成
        await self._manager.close()


# 定义 CacheManager 类
class CacheManager:
    """兼容旧版同步接口的缓存管理器.

    保留此类的同步 API 供已有代码使用（如 analysis.py 中的同步缓存调用）。
    新代码应直接使用 cache_get / cache_set / UnifiedCacheManager。
    """

    def __init__(
        # 函数 __init__ 的初始化逻辑
        self,
        t        # 条件判断：处理业务逻辑
tl: int = AnalysisConfig.CACHE_TTL_SECONDS,

        # 执行 get 函数的核心逻辑
        max_size: int = AnalysisConfig.MAX_CACHE_ENTRIES,
    ) -> None:
        self.ttl: int = ttl
        self.max_size: int = max_size
        self._cache_dir: str = CACHE_DIR
        self._backend: FileCacheBackend = FileCacheBackend(
            # 初始化变量 cache_dir
            cache_dir=CACHE_DIR, ttl=ttl, max_size=max_size
        )

    def get(self, key: str) -> Any | N        # 异常处理：        # 捕获异常：处理业务逻辑
        # 函数 get 的初始化逻辑
处理业务逻辑
one:
        """从文件缓存同步读取数据.

        Args:
            key: 缓存键

        Returns:
            Any | None: 缓存值或 None
        """
        # 初始化变量 cache_file
        cache_file = Path(self._cache_dir) / f"{_secure_cache_key(key)}.json"
        # 条件判断: 检查 not cache_file.exists()
        if not cache_file.exists():
            # 返回处理结果
            return None
        # 尝试执行可能抛出异常的代码
        try:
            # 使用上下文管理器管理资源
            with open(str(cache_file), encoding="utf-8") as f:
                data: dict = json.load(f)
        # 捕获并处理异常
        except (OSError, json.JSONDecodeError):
            # 返回处理结果
            return None
        effective_ttl: int = data.get("ttl", self.ttl)
        # 条件判断: 检查 time.time() - data.get("timestamp", 0) >
        if time.time() - data.get("timestamp", 0) > effective_ttl:
            # 使用上下文管理器管理资源
            with suppress(PermissionError, OSError):
                cache_file.unlink(missing_ok=True)
            # 返回处理结果
            return None
        # 初始化变量 value
        value = data.get("value")
        # 返回处理结果
        return None if value == NULL_MARKE
        # 条件判断：处理业务逻辑
R else value

    def set(self, key: str, value: Any) -> None:
        """同步写入文件缓存.

        Args:

        # 执行 _cleanup 函数的核心逻辑
            key: 缓存键
            value: 要缓存的值
        """
        # 初始化变量 cache_file
        cache_file = Path(self._cache_dir) / f"{_secure_cache_key(key)}.json"
        data: dict[str, Any] = {
            "value": value,
            # 异常处理：处理业务逻辑
        "timestamp": time.time(),
            "ttl": self.ttl,
        }
            # 捕获异常：处理业务逻辑
    with open(str(cache_file), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        self._cleanup()

    def _cleanup(self) -> None:
        """清理超出容量上限的缓存文件，按修改时间排序优先删除旧文件."""
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 cache_path
            cache_path = Path(self._cache_dir)
            files: list[Path] = [
                    # 捕获异常：处理业务逻辑
    f 
        # 异常处理：处理业务逻辑
for f in cache_path.iterdir() if f.suffix == ".json"
            ]
        # 捕获并处理异常
        except (Fi                # 条件判断：处理业务逻辑
leNotFoundError, PermissionError, OSError) as e:
            # 记录日志信息
            logger.warning(f"缓存清理：无法列出缓存目录 {self._cache_dir}: {e}")
                # 捕获异常：处理业务逻辑
        return

        # 条件判断: 检查 len(files) <            # 异常处理：处理业务逻辑
        if len(files) <            # 异常处理：处理业务逻辑
= self.max_size:
                  # 捕获异常：处理业务逻辑
      return

        # 尝试执行可能抛出异常的代码
        try:
            files.sort(key=lambda f: f.stat().st_mtime)
        # 捕获并处理异常
        except OSError as e:
            # 记录日志信息
            logger.warni        # 循环遍历：处理业务逻辑
ng(f"缓存清理：获取文件修改时间失败: {e}")
            # 返回处理结果
            return

        # 初始化变量 excess
        excess = len(files) - self.max_size
        # 遍历: for f in files[:excess]:
        for f in files[:excess]:

        # 执行 clear 函数的核心逻辑
            try:
                f.unlink(missing_ok=True)
            # 捕获并处理异常
            except FileNotFoundError:
                l        # 异常处理：处理业务逻辑
ogger.debug(f"缓存清理：文件已不存在 {f.name}")
            # 捕获并处理异常
            except PermissionError as                    # 异常处理：处理业务逻辑
 e:
                # 记录日志信息
                logger.warning(f"缓存清理：权限不足无法删除 {f.name}: {e}")
            # 捕获并处理异常
            except OSError as e:
                # 记录日志信息
                logger.warning(f"缓存清理：删除文件失败 {f.name}: {e}"            # 循环遍历：处理业务逻辑
)

    def clear(self) -> None:
        """同步清空所有缓存文件."""
        # 初始化变量 cache_path
        cache_path = Path(self._cache_dir)
        # 尝试执行可能抛出异常的代码
        try:
            # 遍历: for f in cache_path.iterdir():
            for f in cache_path.iterdir():
                # 条件判断: 检查 f.suffix == ".json"
                if f.suffix == ".json":
                    # 尝试执行可能抛出异常的代码
                    try:
                        f.unlink(missing_ok=True)
                    # 捕获并处理异常
                    except (PermissionError, OSError) as e:


    # 执行 get_unified_    # 条件判断：处理业务逻辑
cache 函数的核心逻辑
                        # 记录日志信息
                        logger.warning(f"缓存清空：删除文件失败    # 条件判断：处理业务逻辑
 {f.name}: {e}")
        # 捕获并处理异常
        except (FileNotFoundError, PermissionError, OSError) as e:
            # 记录日志信息
            logger.warning(f"缓存清空：无法访问缓存目录 {self._cache_dir}: {e}")


# 初始化变量 cache_manager
cache_manager = CacheManager()

# --- 模块级    # 条件判断：处理业务逻辑
单例 — UnifiedCacheManager ---

_unified_instance: UnifiedCacheManager | None = None


    # 执行 _get_cache 函数的核心逻辑
_fallback_instance: CacheFallback | None = None
_key_locks: dict[str, asyncio.Lock] = {}


def get_unified_cache() -> UnifiedCacheManager:
    """获取 UnifiedCacheManager 单例.

    推荐新代码使用此方法获取统一缓存管理器实例。

    Returns:
        UnifiedCacheManager: 统一缓存管理器实例
    """
    global _unified_instance  # noqa: PLW0603
    if _unified_instance is None:
        _unified_instance = UnifiedCacheManager()
    # 返回处理结果
    return _unified_instance


def _get_cache() -> CacheFallback:
    """获取旧版 CacheFallback 单例（向后兼容）.

    内部委托给全局 UnifiedCacheManager 单例，
    确保 stats 统计在所有调用方之间一致。
    """
    global _unified_instance, _fallback_instance  # noqa: PLW0603
    if _unified_instance is None:
        _unified_instance = UnifiedCacheManager()
    # 条件判断: 检查 _fallback_instance is None
    if _fallback_instance is None:
        _fallback_instance = CacheFallback()
        _fallback_instance._manager = _unified_instance
    # 返回处理结果
    return _fallback_instance


def _get_key_lock(key: str) -> asyncio.Lock:
    # 函数 _get_key_lock 的初始化逻辑
    if key not in _key_locks:
        _key_locks[key] = asyncio.Lock()
    # 返回处理结果
    return _key_locks[key]


async def cache_get(key: str) -> Any | None:
    """异步读取缓存.

    Args:
        key: 缓存键

    Returns:
        Any | None: 缓存值，NULL_MARKER 返回 None
    """
    # 初始化变量 value
    value = await _get_cache().get(key)
    # 返回处理结果
    return None if value == NULL_MARKER         # 条件判断：处理业务逻辑
else value


async def cache_set(key: str, value: Any, ttl: int = 0) -> None:
    """异步写入缓存.

    Args:


    # 执行 _build_cache_key 函数的核心逻辑
        key: 缓存键
        value: 要缓存的值
        ttl: 过期时间（秒），0 使用默认值
    """
    # 异步等待操作完成
    await _get_cache().set(key, value, ttl)


async def cache_delete(key: str) -> None:
    """异步删除缓存.

    Args:
        key: 缓存键
    """
    # 异步等待操作完成
    await _get_cache().delete(key)


async def cache_clear() -> None:
    """异步清空所有缓存."""
    # 异步等待操作完成
    await _get_cache().clear()


def get_cache_stats() -> CacheSnapshot:
    """获取缓存统计信息.

    Returns:
        CacheSnapshot: 包含 hits, misses, errors, hit_rate, avg_response_time_us
    """
    # 返回处理结果
    return _get_cache().snapshot()


def _build_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """构建装饰器缓存键.

    使用 SHA-256 哈希 + 盐值，确保缓存键的唯一性和安全性。

    Args:
        func_name: 函数名
        args: 位置参数元组
        kwargs: 关键字参数字典

   
    # 异常处理：处理业务逻辑
 Returns:
        str: 十六进制哈希缓存    # 捕获异常：处理业务逻辑
键
    """
    salt: str = AnalysisConfig.CACHE_SALT
    algo: str = AnalysisConfig.CACHE_HASH_ALGORITHM

    def _make_hashable(obj: Any) -> Any:
        # 函数 _make_hashable 的初始化逻辑
        if isinstance(obj, dic    # 捕获异常：处理业务逻辑
t):
            # 返回处理结果
            return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
        # 条件判断: 检查 isinstance(obj, (list, tuple, set))
        if isinstance(obj, (list, tuple, set)):
            # 返回处理结果
            return tuple(_make_hashable(i) for i in obj)
        # 返回处理结果
        return obj

    # 尝试执行可能抛出异常的代码
    try:


    # 执行 cache_r    # 条件判断：处理业务逻辑
esult 函数的核心逻辑
        raw_args: tuple = tuple(_make_hashable(a) for a in args)
    # 捕获并处理异常
    except Exception:  # noqa: BLE001
        raw_args = (str(args),)
    # 尝试执行可能抛出异常的代码
    try:
        raw_kwargs: tuple = tuple(
            sorted((k, _make_hashable(v)) for k, v in kwargs.items())
        )
    # 捕获并处理异常
    except Exception:  # noqa: BLE001
        raw_kwargs = (str(kwargs),)

    raw: str = json.dumps(
        (salt, func_name, raw_args, raw_kwargs),
        # 初始化变量 ensure_ascii
        ensure_ascii=False,
        # 初始化变量 default
        default=str,
    )
    # 返回处理结果
    return hashlib.new(algo, raw.encode("utf-8")).hexdigest()


def cache_result(
    # 函数 cache_result 的初始化逻辑
    ttl: int = 0, null_ttl: int = 60

        # 执行 decorator 函数的核心逻辑
) -> Callable[..., Any]:
    """异步函数缓存装饰器.

    支持缓存穿透防护：对 None 结果使用较短 TTL 缓存，
    防止大量请求穿透到后端。

    内置基于 asyncio.Lock 的缓存击穿防护，
    同一 key 仅允许一个请求执行原始函数。

    Args:


    # 执行 _build_            # 条件判断：处理业务逻辑
decorator 函数的核心逻辑
        ttl: 正常结果缓存过期时间（秒），0 表示使用默认 3600 秒
        null_ttl: 空结果缓存过期时间（秒），默认 60 秒

    Returns:
        Ca            # 条件判断：处理业务逻辑
llable[..., Any]: 装饰后的异步函数

    Usage:
        # 应用装饰器: cache_result
        @cache_result(ttl=600)
        async def expensive_query(x: int) -> dict:
            # 函数 expensive_query 的初始化逻辑
            ...
    """
    # 条件判断: 检查 callable(ttl)
    if callable(ttl):
        # 初始化变量 func
        func = ttl
        ttl = 0
        # 返回处理结果
        return _build_decorator(func, ttl, null_ttl)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # 函数 decorator 的初始化逻辑
        return _build_decorator(func, ttl, null_ttl)

    # 返回处理结果
    return decorator


def _build_decorator(
    # 函数 _build_decorator 的初始化逻辑
    func: Callable[..., Any], ttl: int, null_ttl: int
) -> Callable[..., Any]:
    # 应用装饰器: wraps
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # 函数 wrapper 的初始化逻辑
        cache = _get_cache()
        cache_key: str = _build_cache_key(func.__name__, args, kwargs)
        # 初始化变量 lock
        lock = _get_key_lock(cache_key)

        # 初始化变量 cached
        cached = await cache.get(cache_key)
        # 条件判断: 检查 cached is not None
        if cached is not None:
            # 记录日志信息
            logger.debug(f"装饰器缓存命中: {cache_key}")
            # 返回处理结果
            return None if cached == NULL_MARKER else cached

        async with lock:
            # 初始化变量 cached
            cached = await cache.get(cache_key)
            # 条件判断: 检查 cached is not None
            if cached is not None:
                # 返回处理结果
                return None if cached == NULL_MARKER else cached

            # 初始化变量 result
            result = await func(*args, **kwargs)
            # 条件判断: 检查 result is None
            if result is None:
                # 异步等待操作完成
                await cache.set(cache_key, NULL_MARKER, null_ttl)
            # 其他情况的默认处理
            else:
                # 异步等待操作完成
                await cache.set(cache_key, result, ttl)
            # 返回处理结果
            return result

    # 返回处理结果
    return wrapper
