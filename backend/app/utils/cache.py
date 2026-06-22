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

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import suppress
from functools import wraps
from pathlib import Path
from typing import Any

import redis.asyncio as redis
from loguru import logger

from app.config import AnalysisConfig
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

NULL_MARKER = "__CACHE_NULL__"

CACHE_KEY_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_:.\-]+$")
"""缓存键安全字符校验正则.

仅允许字母（大小写）、数字、下划线、冒号、点号、连字符。
此规则在 _secure_cache_key 中强制执行，包含非法字符的键将触发 CacheKeyValidationError。
"""


class CacheKeyValidationError(ValueError):
    """缓存键验证异常.

    当缓存键包含非法字符（超出 [a-zA-Z0-9_:.-] 范围）时抛出。

    Attributes:
        invalid_key: 触发异常的问题缓存键
        invalid_chars: 包含的非法字符集合
    """

    def __init__(self, key: str, invalid_chars: set[str]) -> None:
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
    invalid_chars = set(CACHE_KEY_PATTERN.sub("", raw_key))
    if invalid_chars:
        raise CacheKeyValidationError(raw_key, invalid_chars)

    salted = f"{AnalysisConfig.CACHE_SALT}:{raw_key}"
    hashed = hashlib.sha256(salted.encode()).hexdigest()
    truncated = hashed[: AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH]
    logger.debug(
        f"缓存键哈希: {raw_key!r} -> {truncated} (截取自{len(hashed)}位)"
    )
    return truncated


class CacheStats:
    """缓存统计计数器.

    线程安全的命中/未命中/错误计数及耗时统计。
    """

    def __init__(self) -> None:
        self.hits: int = 0
        self.misses: int = 0
        self.errors: int = 0
        self._total_time_ns: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()

    @property
    def hit_rate(self) -> float:
        """缓存命中率."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def avg_response_time_us(self) -> float:
        """平均响应时间（微秒）."""
        total = self.hits + self.misses
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
            self.errors += 1

    def snapshot(self) -> CacheSnapshot:
        """导出当前统计快照.

        Returns:
            CacheSnapshot: 包含 hits, misses, errors, hit_rate, avg_response_time_us
        """
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "hit_rate": round(self.hit_rate, 4),
            "avg_response_time_us": round(self.avg_response_time_us, 2),
        }


class CacheBackend(ABC):
    """缓存后端抽象基类 —— 唯一缓存协议.

    定义缓存操作的统一标准接口，所有缓存后端实现必须遵循此协议。
    接口涵盖核心 CRUD 操作、键存在性检查和资源清理。

    Usage:
        class MyBackend(CacheBackend):
            async def get(self, key: str) -> Any | None:
                ...

            async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
                ...

            async def delete(self, key: str) -> None:
                ...

            async def clear(self) -> None:
                ...

            async def exists(self, key: str) -> bool:
                ...

            @abstractmethod
    async def close(self) -> None:
                ...
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """获取缓存值."""
        ...

    @abstractmethod
    async def set(
        self, key: str, value: Any, ttl: int | None = None
    ) -> None:
        """设置缓存值."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除缓存键."""
        ...

    @abstractmethod
    async def clear(self) -> None:
        """清空所有缓存."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭后端连接资源（可选实现）."""


class FileCacheBackend(CacheBackend):
    """文件系统缓存后端.

    基于 JSON 文件存储缓存数据，支持 TTL 过期和容量清理。
    作为默认缓存后端，所有文件操作通过 asyncio.to_thread() 异步化执行，
    并使用 asyncio.Lock 确保线程安全。

    缓存键通过 SHA-256 哈希处理，防止路径遍历攻击。

    Usage:
        backend = FileCacheBackend(ttl=3600, max_size=1000)
        await backend.set("user:123", {"name": "test"})
        value = await backend.get("user:123")
    """

    def __init__(
        self,
        cache_dir: str = CACHE_DIR,
        ttl: int = AnalysisConfig.CACHE_TTL_SECONDS,
        max_size: int = AnalysisConfig.MAX_CACHE_ENTRIES,
    ) -> None:
        self._cache_dir: str = cache_dir
        Path(self._cache_dir).mkdir(parents=True, exist_ok=True)
        self.ttl: int = ttl
        self.max_size: int = max_size
        self._rw_lock: asyncio.Lock = asyncio.Lock()

    def _file_path(self, key: str) -> Path:
        return Path(self._cache_dir) / f"{_secure_cache_key(key)}.json"

    async def get(self, key: str) -> Any | None:
        """从文件缓存读取值."""
        cache_file = self._file_path(key)
        if not cache_file.exists():
            return None

        try:
            data: dict = await asyncio.to_thread(self._read_file, cache_file)
        except (OSError, json.JSONDecodeError):
            return None

        effective_ttl: int = data.get("ttl", self.ttl)
        if time.time() - data.get("timestamp", 0) > effective_ttl:
            with suppress(OSError):
                await asyncio.to_thread(cache_file.unlink, missing_ok=True)
            return None

        return data.get("value")

    async def set(
        self, key: str, value: Any, ttl: int | None = None
    ) -> None:
        """写入文件缓存."""
        cache_file = self._file_path(key)
        data: dict[str, Any] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl if ttl is not None else self.ttl,
        }

        async with self._rw_lock:
            await asyncio.to_thread(self._write_file, cache_file, data)
            await self._cleanup()

    async def delete(self, key: str) -> None:
        """删除文件缓存键."""
        cache_file = self._file_path(key)
        try:
            await asyncio.to_thread(cache_file.unlink, missing_ok=True)
        except (PermissionError, OSError) as e:
            logger.warning(f"缓存删除失败 {key}: {e}")

    async def clear(self) -> None:
        """清空文件缓存."""
        cache_path = Path(self._cache_dir)
        try:
            files = list(cache_path.iterdir())
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.warning(f"缓存清空：无法访问缓存目录 {self._cache_dir}: {e}")
            return

        async with self._rw_lock:
            for f in files:
                if f.suffix == ".json":
                    try:
                        await asyncio.to_thread(f.unlink, missing_ok=True)
                    except (PermissionError, OSError) as e:
                        logger.warning(f"缓存清空：删除文件失败 {f.name}: {e}")

    async def exists(self, key: str) -> bool:
        """检查文件缓存键是否存在."""
        cache_file = self._file_path(key)
        return cache_file.exists()

    async def close(self) -> None:
        """关闭文件系统缓存后端.

        文件系统缓存没有持续连接或后台任务，此方法仅作为协议实现存在，
        保持与 CacheBackend 抽象基类一致。调用后后端仍可继续使用。
        """
        # 文件系统缓存无需释放资源，此处仅作为协议占位实现

    @staticmethod
    def _read_file(file_path: Path) -> dict:
        with open(str(file_path), encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write_file(file_path: Path, data: dict) -> None:
        with open(str(file_path), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    async def _cleanup(self) -> None:
        """清理超出容量上限的缓存文件，按修改时间排序优先删除旧文件."""
        try:
            cache_path = Path(self._cache_dir)
            files: list[Path] = [
                f for f in cache_path.iterdir() if f.suffix == ".json"
            ]
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.warning(f"缓存清理：无法列出缓存目录 {self._cache_dir}: {e}")
            return

        if len(files) <= self.max_size:
            return

        try:
            files.sort(key=lambda f: f.stat().st_mtime)
        except OSError as e:
            logger.warning(f"缓存清理：获取文件修改时间失败: {e}")
            return

        excess = len(files) - self.max_size
        for f in files[:excess]:
            try:
                await asyncio.to_thread(f.unlink, missing_ok=True)
            except FileNotFoundError:
                logger.debug(f"缓存清理：文件已不存在 {f.name}")
            except PermissionError as e:
                logger.warning(f"缓存清理：权限不足无法删除 {f.name}: {e}")
            except OSError as e:
                logger.warning(f"缓存清理：删除文件失败 {f.name}: {e}")


class RedisCacheBackend(CacheBackend):
    """Redis 缓存后端.

    支持连接池管理、自动重连、可配置 TTL 和键前缀隔离。
    实现 CacheBackend 协议，与 FileCacheBackend 接口一致。

    Usage:
        backend = RedisCacheBackend(redis_url="redis://localhost:6379/0")
        await backend.set("key", "value", ttl=3600)
        value = await backend.get("key")
    """

    def __init__(
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
        logger.info(
            "Redis 缓存后端已配置 | URL={} | 前缀={!r}",
            self._sanitize_url(self._redis_url),
            self._key_prefix,
        )

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """移除 URL 中的密码部分，避免敏感信息泄露到日志."""
        if "@" not in url:
            return url
        scheme, rest = url.split("://", 1)
        if "@" not in rest:
            return url
        _, host_part = rest.split("@", 1)
        return f"{scheme}://***@{host_part}"

    def _prefixed_key(self, key: str) -> str:
        """为缓存键添加命名空间前缀."""
        return f"{self._key_prefix}{key}"

    async def _ensure_connected(self) -> None:
        if self._client is not None:
            return
        self._pool = redis.ConnectionPool.from_url(
            self._redis_url,
            max_connections=AnalysisConfig.REDIS_MAX_CONNECTIONS,
            socket_timeout=AnalysisConfig.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=AnalysisConfig.REDIS_SOCKET_CONNECT_TIMEOUT,
            decode_responses=False,
        )
        self._client = redis.Redis(connection_pool=self._pool)
        try:
            await self._client.ping()
            logger.info("Redis 连接成功 | 端点={}", self._sanitize_url(self._redis_url))
        except (redis.ConnectionError, redis.TimeoutError, OSError) as e:
            logger.warning(
                "Redis 初次连接失败，端点={} 错误={}",
                self._sanitize_url(self._redis_url),
                e,
            )

    async def _reconnect(self) -> None:
        if self._client:
            with suppress(Exception):
                await self._client.aclose()
        self._pool = None
        self._client = None

    async def get(self, key: str) -> Any | None:
        """从Redis读取缓存值."""
        prefixed = self._prefixed_key(key)
        for attempt in range(AnalysisConfig.REDIS_RETRY_MAX_ATTEMPTS):
            try:
                await self._ensure_connected()
                if self._client is None:
                    return None
                data: bytes | None = await self._client.get(prefixed)
                if data is None:
                    return None
                return json.loads(data)
            except (redis.ConnectionError, redis.TimeoutError, OSError):
                if attempt < AnalysisConfig.REDIS_RETRY_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(AnalysisConfig.REDIS_RETRY_DELAY)
                    await self._reconnect()
        return None

    async def set(
        self, key: str, value: Any, ttl: int | None = None
    ) -> None:
        """写入Redis缓存."""
        prefixed = self._prefixed_key(key)
        effective_ttl = ttl if ttl is not None else AnalysisConfig.CACHE_TTL_SECONDS
        for attempt in range(AnalysisConfig.REDIS_RETRY_MAX_ATTEMPTS):
            try:
                await self._ensure_connected()
                if self._client is None:
                    return
                payload: str = json.dumps(value, ensure_ascii=False, default=str)
                await self._client.setex(prefixed, effective_ttl, payload)
                return
            except (redis.ConnectionError, redis.TimeoutError, OSError):
                if attempt < AnalysisConfig.REDIS_RETRY_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(AnalysisConfig.REDIS_RETRY_DELAY)
                    await self._reconnect()

    async def delete(self, key: str) -> None:
        """删除Redis缓存键."""
        prefixed = self._prefixed_key(key)
        try:
            await self._ensure_connected()
            if self._client is not None:
                await self._client.delete(prefixed)
        except (redis.ConnectionError, redis.TimeoutError):
            pass

    async def clear(self) -> None:
        """清空Redis数据库(仅清空带前缀的键,避免误删共享实例数据)."""
        try:
            await self._ensure_connected()
            if self._client is None:
                return
            pattern: str = f"{self._key_prefix}*"
            cursor: int = 0
            deleted = 0
            while True:
                cursor, batch = await self._client.scan(
                    cursor=cursor, match=pattern, count=200
                )
                if batch:
                    await self._client.delete(*batch)
                    deleted += len(batch)
                if cursor == 0:
                    break
            logger.info(
                "Redis 缓存已清空(前缀={!r}, 共删除 {} 个键)",
                self._key_prefix,
                deleted,
            )
        except (redis.ConnectionError, redis.TimeoutError):
            pass

    async def exists(self, key: str) -> bool:
        """检查Redis缓存键是否存在."""
        prefixed = self._prefixed_key(key)
        try:
            await self._ensure_connected()
            if self._client is not None:
                return bool(await self._client.exists(prefixed))
            return False
        except (redis.ConnectionError, redis.TimeoutError):
            return False

    async def close(self) -> None:
        """关闭 Redis 连接."""
        if self._client:
            with suppress(Exception):
                await self._client.aclose()
        self._pool = None
        self._client = None


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
        await cache.set("key", "value")
        result = await cache.get("key")

        # 使用 Redis 后端 + 文件降级
        redis_backend = RedisCacheBackend()
        file_backend = FileCacheBackend()
        cache = UnifiedCacheManager(backend=redis_backend, fallback_backend=file_backend)

        # 通过全局单例获取
        cache = get_unified_cache()
    """

    def __init__(
        self,
        backend: CacheBackend | None = None,
        fallback_backend: CacheBackend | None = None,
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

        if backend is not None:
            self._primary: CacheBackend = backend
        else:
            self._primary = self._create_backend(self._backend_type)

        self._fallback: CacheBackend | None = fallback_backend
        self._primary_available: bool = True

        logger.info(
            "统一缓存管理器已初始化 | 主后端={} | 降级后端={}",
            type(self._primary).__name__,
            type(self._fallback).__name__ if self._fallback is not None else "无",
        )

    @staticmethod
    def _create_backend(backend_type: str) -> CacheBackend:
        backend_type_normalized = (backend_type or "").strip().lower()
        if backend_type_normalized == "redis":
            logger.info("按配置 CACHE_BACKEND=redis 创建 Redis 缓存后端")
            return RedisCacheBackend()
        if backend_type_normalized == "file":
            logger.info("按配置 CACHE_BACKEND=file 创建文件缓存后端")
            return FileCacheBackend()
        logger.warning(
            "未知的 CACHE_BACKEND={!r}，回退到 file 缓存后端",
            backend_type,
        )
        return FileCacheBackend()

    @property
    def stats(self) -> CacheStats:
        """缓存统计对象."""
        return self._stats

    def snapshot(self) -> CacheSnapshot:
        """导出缓存统计快照.

        Returns:
            CacheSnapshot: 包含 hits, misses, errors, hit_rate, avg_response_time_us
        """
        return self._stats.snapshot()

    async def get(self, key: str) -> Any | None:
        """从缓存读取数据，支持主备降级.

        Args:
            key: 缓存键

        Returns:
            Any | None: 缓存值或 None
        """
        start = time.perf_counter_ns()

        if self._primary_available:
            try:
                value = await self._primary.get(key)
                elapsed = time.perf_counter_ns() - start
                if value is not None:
                    await self._stats.record_hit(elapsed)
                    return value
                await self._stats.record_miss(elapsed)
                return None
            except Exception as e:  # noqa: BLE001
                logger.warning(f"主缓存后端不可用，尝试降级: {e}")
                self._primary_available = False
                await self._stats.record_error()

        if self._fallback is not None:
            try:
                value = await self._fallback.get(key)
                elapsed = time.perf_counter_ns() - start
                if value is not None:
                    await self._stats.record_hit(elapsed)
                else:
                    await self._stats.record_miss(elapsed)
                return value
            except Exception:  # noqa: BLE001
                await self._stats.record_error()

        elapsed = time.perf_counter_ns() - start
        await self._stats.record_miss(elapsed)
        return None

    async def set(
        self, key: str, value: Any, ttl: int | None = None
    ) -> None:
        """写入缓存，优先写入主后端.

        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 过期时间（秒），None 表示使用默认值
        """
        if self._primary_available:
            try:
                await self._primary.set(key, value, ttl)
                self._primary_available = True
                return
            except Exception as e:  # noqa: BLE001
                logger.warning(f"主缓存后端写入失败，降级: {e}")
                self._primary_available = False
                await self._stats.record_error()

        if self._fallback is not None:
            try:
                await self._fallback.set(key, value, ttl)
            except Exception:  # noqa: BLE001
                await self._stats.record_error()

    async def delete(self, key: str) -> None:
        """删除缓存条目，同时清理主备后端.

        Args:
            key: 缓存键
        """
        if self._primary_available:
            with suppress(Exception):
                await self._primary.delete(key)
        if self._fallback is not None:
            with suppress(Exception):
                await self._fallback.delete(key)

    async def clear(self) -> None:
        """清空主备后端所有缓存."""
        if self._primary_available:
            with suppress(Exception):
                await self._primary.clear()
        if self._fallback is not None:
            with suppress(Exception):
                await self._fallback.clear()

    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在.

        Args:
            key: 缓存键

        Returns:
            bool: 如果缓存存在且未过期返回 True，否则返回 False
        """
        value = await self.get(key)
        return value is not None

    async def close(self) -> None:
        """关闭缓存管理器及底层后端连接."""
        with suppress(Exception):
            await self._primary.close()
        if self._fallback is not None:
            with suppress(Exception):
                await self._fallback.close()


class BaseCache(ABC):
    """旧版缓存抽象基类（已废弃）.

    保留此类仅用于向后兼容。
    新代码请直接使用 CacheBackend 协议。

    内部将 ttl: int = 0 语义转换为 CacheBackend 的 ttl: int | None = None，
    ttl=0 表示使用默认 TTL。
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """获取缓存值."""
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """设置缓存值."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除缓存键."""
        ...

    @abstractmethod
    async def clear(self) -> None:
        """清空所有缓存."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在."""
        ...


class FileCache(BaseCache):
    """旧版文件系统缓存（已废弃）.

    保留此类仅用于向后兼容。
    内部委托给 FileCacheBackend，新代码请直接使用 FileCacheBackend。

    使用延迟初始化模式：_backend 在首次访问时创建，
    允许在构造后修改 _cache_dir（测试场景常用）。
    """

    def __init__(
        self,
        ttl: int = AnalysisConfig.CACHE_TTL_SECONDS,
        max_size: int = AnalysisConfig.MAX_CACHE_ENTRIES,
    ) -> None:
        self.ttl: int = ttl
        self.max_size: int = max_size
        self._cache_dir: str = CACHE_DIR

    def _get_backend(self) -> FileCacheBackend:
        backend: FileCacheBackend | None = self.__dict__.get("_backend")
        if backend is None:
            backend = FileCacheBackend(
                cache_dir=self._cache_dir, ttl=self.ttl, max_size=self.max_size
            )
            self._backend: FileCacheBackend = backend
        return backend

    async def get(self, key: str) -> Any | None:
        """读取缓存值."""
        return await self._get_backend().get(key)

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """写入缓存值."""
        effective_ttl = ttl if ttl > 0 else None
        await self._get_backend().set(key, value, effective_ttl)

    async def delete(self, key: str) -> None:
        """删除缓存键."""
        await self._get_backend().delete(key)

    async def clear(self) -> None:
        """清空所有缓存."""
        await self._get_backend().clear()

    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在."""
        return await self._get_backend().exists(key)

    async def _cleanup(self) -> None:
        """清理超出容量上限的缓存文件（委托给后端）."""
        await self._get_backend()._cleanup()


class RedisCache(BaseCache):
    """旧版 Redis 缓存后端（已废弃）.

    保留此类仅用于向后兼容。
    内部委托给 RedisCacheBackend，新代码请直接使用 RedisCacheBackend。
    """

    def __init__(
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
            redis_url=redis_url, key_prefix=key_prefix
        )

    async def get(self, key: str) -> Any | None:
        """读取缓存值."""
        return await self._backend.get(key)

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """写入缓存值."""
        effective_ttl: int | None = ttl if ttl > 0 else None
        await self._backend.set(key, value, effective_ttl)

    async def delete(self, key: str) -> None:
        """删除缓存键."""
        await self._backend.delete(key)

    async def clear(self) -> None:
        """清空所有缓存."""
        await self._backend.clear()

    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在."""
        return await self._backend.exists(key)

    async def close(self) -> None:
        """关闭 Redis 连接."""
        await self._backend.close()


class CacheFallback(BaseCache):
    """旧版带降级的缓存管理器（已废弃）.

    保留此类仅用于向后兼容。
    内部委托给 UnifiedCacheManager，提供与旧版完全兼容的 API。
    Redis 优先，不可用时自动降级至文件缓存。
    """

    def __init__(self) -> None:
        self._redis: RedisCache = RedisCache()
        self._file: FileCache = FileCache()
        self._redis_available: bool = True
        self._stats: CacheStats = CacheStats()
        self._manager: UnifiedCacheManager = UnifiedCacheManager(
            backend=self._redis._backend,
            fallback_backend=self._file._get_backend(),
        )

    @property
    def stats(self) -> CacheStats:
        """缓存统计对象."""
        return self._stats

    def snapshot(self) -> CacheSnapshot:
        """导出缓存统计快照.

        Returns:
            CacheSnapshot: 包含 hits, misses, errors, hit_rate, avg_response_time_us
        """
        return self._stats.snapshot()

    async def get(self, key: str) -> Any | None:
        """获取缓存值（含统计追踪）."""
        start = time.perf_counter_ns()

        result = await self._manager.get(key)
        elapsed = time.perf_counter_ns() - start

        if result is not None:
            await self._stats.record_hit(elapsed)
        else:
            await self._stats.record_miss(elapsed)

        if not self._manager._primary_available:
            self._redis_available = False

        return result

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """设置缓存值."""
        effective_ttl: int | None = ttl if ttl > 0 else None
        await self._manager.set(key, value, effective_ttl)
        self._redis_available = self._manager._primary_available

    async def delete(self, key: str) -> None:
        """删除缓存键."""
        await self._manager.delete(key)

    async def clear(self) -> None:
        """清空所有缓存."""
        await self._manager.clear()

    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在."""
        value = await self.get(key)
        return value is not None

    async def close(self) -> None:
        """关闭缓存管理器及底层连接."""
        await self._manager.close()


class CacheManager:
    """兼容旧版同步接口的缓存管理器.

    保留此类的同步 API 供已有代码使用（如 analysis.py 中的同步缓存调用）。
    新代码应直接使用 cache_get / cache_set / UnifiedCacheManager。
    """

    def __init__(
        self,
        ttl: int = AnalysisConfig.CACHE_TTL_SECONDS,
        max_size: int = AnalysisConfig.MAX_CACHE_ENTRIES,
    ) -> None:
        self.ttl: int = ttl
        self.max_size: int = max_size
        self._cache_dir: str = CACHE_DIR
        self._backend: FileCacheBackend = FileCacheBackend(
            cache_dir=CACHE_DIR, ttl=ttl, max_size=max_size
        )

    def get(self, key: str) -> Any | None:
        """从文件缓存同步读取数据.

        Args:
            key: 缓存键

        Returns:
            Any | None: 缓存值或 None
        """
        cache_file = Path(self._cache_dir) / f"{_secure_cache_key(key)}.json"
        if not cache_file.exists():
            return None
        try:
            with open(str(cache_file), encoding="utf-8") as f:
                data: dict = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        effective_ttl: int = data.get("ttl", self.ttl)
        if time.time() - data.get("timestamp", 0) > effective_ttl:
            with suppress(PermissionError, OSError):
                cache_file.unlink(missing_ok=True)
            return None
        value = data.get("value")
        return None if value == NULL_MARKER else value

    def set(self, key: str, value: Any) -> None:
        """同步写入文件缓存.

        Args:
            key: 缓存键
            value: 要缓存的值
        """
        cache_file = Path(self._cache_dir) / f"{_secure_cache_key(key)}.json"
        data: dict[str, Any] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": self.ttl,
        }
        with open(str(cache_file), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        self._cleanup()

    def _cleanup(self) -> None:
        """清理超出容量上限的缓存文件，按修改时间排序优先删除旧文件."""
        try:
            cache_path = Path(self._cache_dir)
            files: list[Path] = [
                f for f in cache_path.iterdir() if f.suffix == ".json"
            ]
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.warning(f"缓存清理：无法列出缓存目录 {self._cache_dir}: {e}")
            return

        if len(files) <= self.max_size:
            return

        try:
            files.sort(key=lambda f: f.stat().st_mtime)
        except OSError as e:
            logger.warning(f"缓存清理：获取文件修改时间失败: {e}")
            return

        excess = len(files) - self.max_size
        for f in files[:excess]:
            try:
                f.unlink(missing_ok=True)
            except FileNotFoundError:
                logger.debug(f"缓存清理：文件已不存在 {f.name}")
            except PermissionError as e:
                logger.warning(f"缓存清理：权限不足无法删除 {f.name}: {e}")
            except OSError as e:
                logger.warning(f"缓存清理：删除文件失败 {f.name}: {e}")

    def clear(self) -> None:
        """同步清空所有缓存文件."""
        cache_path = Path(self._cache_dir)
        try:
            for f in cache_path.iterdir():
                if f.suffix == ".json":
                    try:
                        f.unlink(missing_ok=True)
                    except (PermissionError, OSError) as e:
                        logger.warning(f"缓存清空：删除文件失败 {f.name}: {e}")
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.warning(f"缓存清空：无法访问缓存目录 {self._cache_dir}: {e}")


cache_manager = CacheManager()

# --- 模块级单例 — UnifiedCacheManager ---

_unified_instance: UnifiedCacheManager | None = None
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
    return _unified_instance


def _get_cache() -> CacheFallback:
    """获取旧版 CacheFallback 单例（向后兼容）.

    内部委托给全局 UnifiedCacheManager 单例，
    确保 stats 统计在所有调用方之间一致。
    """
    global _unified_instance, _fallback_instance  # noqa: PLW0603
    if _unified_instance is None:
        _unified_instance = UnifiedCacheManager()
    if _fallback_instance is None:
        _fallback_instance = CacheFallback()
        _fallback_instance._manager = _unified_instance
    return _fallback_instance


def _get_key_lock(key: str) -> asyncio.Lock:
    if key not in _key_locks:
        _key_locks[key] = asyncio.Lock()
    return _key_locks[key]


async def cache_get(key: str) -> Any | None:
    """异步读取缓存.

    Args:
        key: 缓存键

    Returns:
        Any | None: 缓存值，NULL_MARKER 返回 None
    """
    value = await _get_cache().get(key)
    return None if value == NULL_MARKER else value


async def cache_set(key: str, value: Any, ttl: int = 0) -> None:
    """异步写入缓存.

    Args:
        key: 缓存键
        value: 要缓存的值
        ttl: 过期时间（秒），0 使用默认值
    """
    await _get_cache().set(key, value, ttl)


async def cache_delete(key: str) -> None:
    """异步删除缓存.

    Args:
        key: 缓存键
    """
    await _get_cache().delete(key)


async def cache_clear() -> None:
    """异步清空所有缓存."""
    await _get_cache().clear()


def get_cache_stats() -> CacheSnapshot:
    """获取缓存统计信息.

    Returns:
        CacheSnapshot: 包含 hits, misses, errors, hit_rate, avg_response_time_us
    """
    return _get_cache().snapshot()


def _build_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """构建装饰器缓存键.

    使用 SHA-256 哈希 + 盐值，确保缓存键的唯一性和安全性。

    Args:
        func_name: 函数名
        args: 位置参数元组
        kwargs: 关键字参数字典

    Returns:
        str: 十六进制哈希缓存键
    """
    salt: str = AnalysisConfig.CACHE_SALT
    algo: str = AnalysisConfig.CACHE_HASH_ALGORITHM

    def _make_hashable(obj: Any) -> Any:
        if isinstance(obj, dict):
            return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
        if isinstance(obj, (list, tuple, set)):
            return tuple(_make_hashable(i) for i in obj)
        return obj

    try:
        raw_args: tuple = tuple(_make_hashable(a) for a in args)
    except Exception:  # noqa: BLE001
        raw_args = (str(args),)
    try:
        raw_kwargs: tuple = tuple(
            sorted((k, _make_hashable(v)) for k, v in kwargs.items())
        )
    except Exception:  # noqa: BLE001
        raw_kwargs = (str(kwargs),)

    raw: str = json.dumps(
        (salt, func_name, raw_args, raw_kwargs),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.new(algo, raw.encode("utf-8")).hexdigest()


def cache_result(
    ttl: int = 0, null_ttl: int = 60
) -> Callable[..., Any]:
    """异步函数缓存装饰器.

    支持缓存穿透防护：对 None 结果使用较短 TTL 缓存，
    防止大量请求穿透到后端。

    内置基于 asyncio.Lock 的缓存击穿防护，
    同一 key 仅允许一个请求执行原始函数。

    Args:
        ttl: 正常结果缓存过期时间（秒），0 表示使用默认 3600 秒
        null_ttl: 空结果缓存过期时间（秒），默认 60 秒

    Returns:
        Callable[..., Any]: 装饰后的异步函数

    Usage:
        @cache_result(ttl=600)
        async def expensive_query(x: int) -> dict:
            ...
    """
    if callable(ttl):
        func = ttl
        ttl = 0
        return _build_decorator(func, ttl, null_ttl)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return _build_decorator(func, ttl, null_ttl)

    return decorator


def _build_decorator(
    func: Callable[..., Any], ttl: int, null_ttl: int
) -> Callable[..., Any]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        cache = _get_cache()
        cache_key: str = _build_cache_key(func.__name__, args, kwargs)
        lock = _get_key_lock(cache_key)

        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug(f"装饰器缓存命中: {cache_key}")
            return None if cached == NULL_MARKER else cached

        async with lock:
            cached = await cache.get(cache_key)
            if cached is not None:
                return None if cached == NULL_MARKER else cached

            result = await func(*args, **kwargs)
            if result is None:
                await cache.set(cache_key, NULL_MARKER, null_ttl)
            else:
                await cache.set(cache_key, result, ttl)
            return result

    return wrapper
