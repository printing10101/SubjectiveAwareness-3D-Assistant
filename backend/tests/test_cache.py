"""缓存系统单元测试.

覆盖 CacheBackend、FileCacheBackend、RedisCacheBackend、UnifiedCacheManager、
FileCache、RedisCache（旧版兼容）、CacheFallback 降级（旧版兼容）、
cache_result 装饰器和缓存键生成。
"""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fakeredis import aioredis as fakeredis

from app.config import AnalysisConfig
from app.utils.cache import (
    NULL_MARKER,
    BaseCache,
    CacheBackend,
    CacheFallback,
    CacheKeyValidationError,
    CacheManager,
    CacheStats,
    FileCache,
    FileCacheBackend,
    RedisCache,
    RedisCacheBackend,
    UnifiedCacheManager,
    _secure_cache_key,
    cache_delete,
    cache_get,
    cache_result,
    cache_set,
    get_cache_stats,
    get_unified_cache,
)
from app.utils.common import generate_cache_key


@pytest.fixture
def file_cache(tmp_path):
    cache = FileCache(ttl=60, max_size=10)
    cache._cache_dir = str(tmp_path)
    return cache


@pytest.fixture
def file_cache_backend(tmp_path):
    return FileCacheBackend(
        cache_dir=str(tmp_path), ttl=60, max_size=10
    )


@pytest.fixture
async def redis_cache():
    fake_redis = await fakeredis.FakeRedis()
    cache = RedisCache("redis://localhost:6379/0")
    cache._backend._client = fake_redis
    cache._backend._pool = None
    return cache


@pytest.fixture
async def redis_cache_backend():
    fake_redis = await fakeredis.FakeRedis()
    backend = RedisCacheBackend("redis://localhost:6379/0")
    backend._client = fake_redis
    backend._pool = None
    return backend


@pytest.fixture
def isolated_fallback():
    """创建隔离的 CacheFallback 用于装饰器和模块函数测试."""
    fallback = CacheFallback()
    fallback._redis_available = False
    fallback._manager._primary_available = False
    return fallback


class TestCacheBackend:
    def test_cache_backend_is_abstract(self):
        with pytest.raises(TypeError):
            CacheBackend()

    def test_file_cache_backend_is_instance(self):
        backend = FileCacheBackend()
        assert isinstance(backend, CacheBackend)

    def test_redis_cache_backend_is_instance(self):
        backend = RedisCacheBackend()
        assert isinstance(backend, CacheBackend)


class TestBaseCache:
    def test_base_cache_is_abstract(self):
        """旧版 BaseCache 保持抽象类语义."""
        with pytest.raises(TypeError):
            BaseCache()


class TestCacheStats:
    async def test_initial_state(self):
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.errors == 0
        assert stats.hit_rate == 0.0
        assert stats.avg_response_time_us == 0.0

    async def test_hit_rate(self):
        stats = CacheStats()
        await stats.record_hit(100000)
        await stats.record_miss(200000)
        assert stats.hit_rate == 0.5

    async def test_avg_response_time(self):
        stats = CacheStats()
        await stats.record_hit(300000)
        await stats.record_miss(100000)
        assert stats.avg_response_time_us == 200.0

    async def test_snapshot(self):
        stats = CacheStats()
        await stats.record_hit(100000)
        await stats.record_miss(200000)
        await stats.record_error()
        snap = stats.snapshot()
        assert snap["hits"] == 1
        assert snap["misses"] == 1
        assert snap["errors"] == 1
        assert snap["hit_rate"] == 0.5
        assert snap["avg_response_time_us"] == 150.0

    async def test_concurrent_recording(self):
        stats = CacheStats()

        async def record_many():
            for _ in range(100):
                await stats.record_hit(1000)

        await asyncio.gather(*(record_many() for _ in range(10)))
        assert stats.hits == 1000


class TestFileCacheBackend:
    """FileCacheBackend 核心功能测试."""

    async def test_set_and_get(self, file_cache_backend):
        await file_cache_backend.set("key1", {"data": "hello"})
        result = await file_cache_backend.get("key1")
        assert result == {"data": "hello"}

    async def test_get_nonexistent_key(self, file_cache_backend):
        result = await file_cache_backend.get("no_such_key")
        assert result is None

    async def test_ttl_expiry(self, file_cache_backend):
        file_cache_backend.ttl = 0
        await file_cache_backend.set("key2", "value")
        await asyncio.sleep(0.01)
        result = await file_cache_backend.get("key2")
        assert result is None

    async def test_delete(self, file_cache_backend):
        await file_cache_backend.set("key3", "value")
        await file_cache_backend.delete("key3")
        result = await file_cache_backend.get("key3")
        assert result is None

    async def test_clear(self, file_cache_backend):
        await file_cache_backend.set("k1", "v1")
        await file_cache_backend.set("k2", "v2")
        await file_cache_backend.clear()
        assert await file_cache_backend.get("k1") is None
        assert await file_cache_backend.get("k2") is None

    async def test_exists(self, file_cache_backend):
        await file_cache_backend.set("exists_key", "exists_val")
        assert await file_cache_backend.exists("exists_key") is True
        assert await file_cache_backend.exists("no_key") is False

    async def test_max_size_cleanup(self, file_cache_backend):
        file_cache_backend.max_size = 3
        for i in range(5):
            await file_cache_backend.set(f"key{i}", f"val{i}")
        await asyncio.sleep(0.01)
        count = 0
        for i in range(5):
            if await file_cache_backend.get(f"key{i}") == f"val{i}":
                count += 1
        assert count == 3

    async def test_null_marker_handling(self, file_cache_backend):
        await file_cache_backend.set("null_key", NULL_MARKER)
        result = await file_cache_backend.get("null_key")
        assert result == NULL_MARKER

    async def test_corrupt_json(self, file_cache_backend, tmp_path):
        safe_key = _secure_cache_key("bad")
        bad_file = tmp_path / f"{safe_key}.json"
        bad_file.write_text("not valid json")
        file_cache_backend._cache_dir = str(tmp_path)
        result = await file_cache_backend.get("bad")
        assert result is None

    async def test_key_hashing_security(self, file_cache_backend, tmp_path):
        """验证非法字符（路径遍历）的缓存键被正确拦截."""
        dangerous_key = "../../etc/passwd"
        with pytest.raises(CacheKeyValidationError) as exc_info:
            await file_cache_backend.set(dangerous_key, "secret")
        assert "/" in exc_info.value.invalid_chars

        with pytest.raises(CacheKeyValidationError) as exc_info:
            await file_cache_backend.get(dangerous_key)
        assert "/" in exc_info.value.invalid_chars

        with pytest.raises(CacheKeyValidationError) as exc_info:
            await file_cache_backend.delete(dangerous_key)
        assert "/" in exc_info.value.invalid_chars

    async def test_custom_ttl_override(self, file_cache_backend):
        await file_cache_backend.set("key_ttl", "value", ttl=1)
        assert await file_cache_backend.get("key_ttl") == "value"
        await asyncio.sleep(0.02)
        data_file = Path(file_cache_backend._cache_dir) / f"{_secure_cache_key('key_ttl')}.json"
        if data_file.exists():
            with open(str(data_file), encoding="utf-8") as f:
                stored = json.load(f)
            assert stored["ttl"] == 1

    async def test_concurrent_writes(self, file_cache_backend):
        file_cache_backend.max_size = 100

        async def writer(i: int):
            for j in range(10):
                await file_cache_backend.set(f"concurrent_{i}_{j}", f"val_{i}_{j}")

        await asyncio.gather(*(writer(i) for i in range(5)))
        for i in range(5):
            for j in range(10):
                assert await file_cache_backend.get(f"concurrent_{i}_{j}") == f"val_{i}_{j}"


class TestRedisCacheBackend:
    """RedisCacheBackend 新核心后端测试 —— 实现 CacheBackend 协议."""

    async def test_set_and_get(self, redis_cache_backend):
        await redis_cache_backend.set("key1", {"data": "hello"})
        result = await redis_cache_backend.get("key1")
        assert result == {"data": "hello"}

    async def test_get_nonexistent_key(self, redis_cache_backend):
        result = await redis_cache_backend.get("no_such_key")
        assert result is None

    async def test_ttl(self, redis_cache_backend):
        await redis_cache_backend.set("key2", "value", ttl=1)
        result = await redis_cache_backend.get("key2")
        assert result == "value"
        await asyncio.sleep(1.1)
        result = await redis_cache_backend.get("key2")
        assert result is None

    async def test_delete(self, redis_cache_backend):
        await redis_cache_backend.set("key3", "value")
        await redis_cache_backend.delete("key3")
        result = await redis_cache_backend.get("key3")
        assert result is None

    async def test_exists(self, redis_cache_backend):
        await redis_cache_backend.set("key4", "value")
        assert await redis_cache_backend.exists("key4") is True
        assert await redis_cache_backend.exists("key5") is False

    async def test_clear(self, redis_cache_backend):
        await redis_cache_backend.set("k1", "v1")
        await redis_cache_backend.set("k2", "v2")
        await redis_cache_backend.clear()
        assert await redis_cache_backend.get("k1") is None

    async def test_null_marker(self, redis_cache_backend):
        await redis_cache_backend.set("null_key", NULL_MARKER)
        result = await redis_cache_backend.get("null_key")
        assert result == NULL_MARKER

    async def test_close(self, redis_cache_backend):
        await redis_cache_backend.close()
        assert redis_cache_backend._client is None

    async def test_complex_data_types(self, redis_cache_backend):
        data = {
            "str": "hello",
            "int": 42,
            "list": [1, 2, 3],
            "nested": {"a": {"b": [4, 5]}},
        }
        await redis_cache_backend.set("complex", data)
        result = await redis_cache_backend.get("complex")
        assert result == data

    async def test_default_ttl_used_when_none(self, redis_cache_backend):
        """验证 ttl=None 时使用默认 TTL."""
        await redis_cache_backend.set("default_ttl", "value", ttl=None)
        result = await redis_cache_backend.get("default_ttl")
        assert result == "value"


class TestFileCache:
    """FileCache 兼容旧版接口测试."""

    async def test_set_and_get(self, file_cache):
        await file_cache.set("key1", {"data": "hello"})
        result = await file_cache.get("key1")
        assert result == {"data": "hello"}

    async def test_get_nonexistent_key(self, file_cache):
        result = await file_cache.get("no_such_key")
        assert result is None

    async def test_ttl_expiry(self, file_cache):
        file_cache.ttl = 0
        await file_cache.set("key2", "value")
        await asyncio.sleep(0.01)
        result = await file_cache.get("key2")
        assert result is None

    async def test_delete(self, file_cache):
        await file_cache.set("key3", "value")
        await file_cache.delete("key3")
        result = await file_cache.get("key3")
        assert result is None

    async def test_exists(self, file_cache):
        await file_cache.set("key4", "value")
        assert await file_cache.exists("key4") is True
        assert await file_cache.exists("key5") is False

    async def test_clear(self, file_cache):
        await file_cache.set("k1", "v1")
        await file_cache.set("k2", "v2")
        await file_cache.clear()
        assert await file_cache.get("k1") is None
        assert await file_cache.get("k2") is None

    async def test_max_size_cleanup(self, file_cache):
        file_cache.max_size = 3
        for i in range(5):
            await file_cache.set(f"key{i}", f"val{i}")
        await asyncio.sleep(0.01)
        count = 0
        for i in range(5):
            if await file_cache.get(f"key{i}") == f"val{i}":
                count += 1
        assert count == 3

    async def test_null_marker_handling(self, file_cache):
        await file_cache.set("null_key", NULL_MARKER)
        result = await file_cache.get("null_key")
        assert result == NULL_MARKER

    async def test_corrupt_json(self, file_cache, tmp_path):
        safe_key = _secure_cache_key("bad")
        bad_file = tmp_path / f"{safe_key}.json"
        bad_file.write_text("not valid json")
        file_cache._cache_dir = str(tmp_path)
        result = await file_cache.get("bad")
        assert result is None


class TestRedisCache:
    """旧版 RedisCache 兼容测试."""

    async def test_set_and_get(self, redis_cache):
        await redis_cache.set("key1", {"data": "hello"})
        result = await redis_cache.get("key1")
        assert result == {"data": "hello"}

    async def test_get_nonexistent_key(self, redis_cache):
        result = await redis_cache.get("no_such_key")
        assert result is None

    async def test_ttl(self, redis_cache):
        await redis_cache.set("key2", "value", ttl=1)
        result = await redis_cache.get("key2")
        assert result == "value"
        await asyncio.sleep(1.1)
        result = await redis_cache.get("key2")
        assert result is None

    async def test_delete(self, redis_cache):
        await redis_cache.set("key3", "value")
        await redis_cache.delete("key3")
        result = await redis_cache.get("key3")
        assert result is None

    async def test_exists(self, redis_cache):
        await redis_cache.set("key4", "value")
        assert await redis_cache.exists("key4") is True
        assert await redis_cache.exists("key5") is False

    async def test_clear(self, redis_cache):
        await redis_cache.set("k1", "v1")
        await redis_cache.set("k2", "v2")
        await redis_cache.clear()
        assert await redis_cache.get("k1") is None

    async def test_null_marker(self, redis_cache):
        await redis_cache.set("null_key", NULL_MARKER)
        result = await redis_cache.get("null_key")
        assert result == NULL_MARKER

    async def test_close(self, redis_cache):
        await redis_cache.close()
        assert redis_cache._backend._client is None

    async def test_complex_data_types(self, redis_cache):
        data = {
            "str": "hello",
            "int": 42,
            "list": [1, 2, 3],
            "nested": {"a": {"b": [4, 5]}},
        }
        await redis_cache.set("complex", data)
        result = await redis_cache.get("complex")
        assert result == data


class TestCacheFallback:
    """旧版 CacheFallback 降级兼容测试 —— 内部委托给 UnifiedCacheManager."""

    async def test_redis_primary(self, redis_cache):
        fallback = CacheFallback()
        fallback._redis = redis_cache
        fallback._manager._primary = redis_cache._backend
        fallback._redis_available = True
        fallback._manager._primary_available = True

        await fallback.set("key1", {"data": "from_redis"})
        result = await fallback.get("key1")
        assert result == {"data": "from_redis"}

    async def test_fallback_to_file(self):
        fallback = CacheFallback()
        fallback._redis_available = False
        fallback._manager._primary_available = False

        await fallback.set("key1", {"data": "from_file"})
        result = await fallback.get("key1")
        assert result == {"data": "from_file"}

    async def test_redis_downgrade_on_error(self):
        fallback = CacheFallback()
        mock_primary = AsyncMock(spec=CacheBackend)
        mock_primary.get = AsyncMock(side_effect=ConnectionError("simulated"))
        mock_primary.set = AsyncMock(side_effect=ConnectionError("simulated"))
        fallback._manager._primary = mock_primary
        fallback._manager._primary_available = True
        fallback._redis_available = True

        await fallback.set("key1", {"data": "downgraded"})
        assert fallback._redis_available is False
        assert fallback._manager._primary_available is False
        result = await fallback.get("key1")
        assert result == {"data": "downgraded"}

    async def test_stats_tracking(self):
        fallback = CacheFallback()
        fallback._redis_available = False
        fallback._manager._primary_available = False

        await fallback.set("k1", "v1")
        await fallback.get("k1")
        await fallback.get("k1")
        await fallback.get("missing")

        snap = fallback.snapshot()
        assert snap["hits"] == 2
        assert snap["misses"] == 1
        assert snap["hit_rate"] == pytest.approx(2 / 3, abs=0.01)

    async def test_exists(self):
        fallback = CacheFallback()
        fallback._redis_available = False
        fallback._manager._primary_available = False

        await fallback.set("exist_key", "value")
        assert await fallback.exists("exist_key") is True
        assert await fallback.exists("nonexist_key") is False


class TestUnifiedCacheManager:
    """UnifiedCacheManager 统一缓存管理器测试."""

    @pytest.fixture
    def unified(self, tmp_path):
        backend = FileCacheBackend(cache_dir=str(tmp_path), ttl=60, max_size=10)
        return UnifiedCacheManager(backend=backend)

    async def test_set_and_get(self, unified):
        await unified.set("key1", {"data": "hello"})
        result = await unified.get("key1")
        assert result == {"data": "hello"}

    async def test_get_nonexistent_key(self, unified):
        result = await unified.get("no_such_key")
        assert result is None

    async def test_delete(self, unified):
        await unified.set("key3", "value")
        await unified.delete("key3")
        result = await unified.get("key3")
        assert result is None

    async def test_clear(self, unified):
        await unified.set("k1", "v1")
        await unified.set("k2", "v2")
        await unified.clear()
        assert await unified.get("k1") is None
        assert await unified.get("k2") is None

    async def test_exists(self, unified):
        await unified.set("exists_key", "value")
        assert await unified.exists("exists_key") is True
        assert await unified.exists("no_key") is False

    async def test_stats_hit_tracking(self, unified):
        await unified.set("stats_key", "stats_val")
        await unified.get("stats_key")
        await unified.get("stats_key")
        await unified.get("missing")

        snap = unified.snapshot()
        assert snap["hits"] == 2
        assert snap["misses"] == 1

    async def test_snapshot_format(self, unified):
        snap = unified.snapshot()
        assert "hits" in snap
        assert "misses" in snap
        assert "errors" in snap
        assert "hit_rate" in snap
        assert "avg_response_time_us" in snap

    async def test_default_backend(self):
        """验证显式指定 file 后端时正确创建 FileCacheBackend."""
        cache = UnifiedCacheManager(backend_type="file")
        assert isinstance(cache._primary, FileCacheBackend)

    async def test_redis_backend_type(self):
        cache = UnifiedCacheManager(backend_type="redis")
        assert isinstance(cache._primary, RedisCacheBackend)

    async def test_custom_backend(self, tmp_path):
        backend = FileCacheBackend(cache_dir=str(tmp_path), ttl=120, max_size=5)
        cache = UnifiedCacheManager(backend=backend)
        assert cache._primary is backend

    async def test_fallback_on_primary_error(self, tmp_path):
        primary = FileCacheBackend(cache_dir=str(tmp_path), ttl=60, max_size=10)
        fallback = FileCacheBackend(
            cache_dir=str(tmp_path / "fallback"), ttl=60, max_size=10
        )
        primary.get = AsyncMock(side_effect=RuntimeError("simulated failure"))
        primary.set = AsyncMock(side_effect=RuntimeError("simulated failure"))

        cache = UnifiedCacheManager(backend=primary, fallback_backend=fallback)
        await cache.set("fallback_key", "fallback_value")
        assert cache._primary_available is False
        result = await cache.get("fallback_key")
        assert result == "fallback_value"

    async def test_fallback_get_error_handling(self, tmp_path):
        """验证备后端 get 异常时的优雅降级处理."""
        primary = FileCacheBackend(cache_dir=str(tmp_path), ttl=60, max_size=10)
        fallback = FileCacheBackend(
            cache_dir=str(tmp_path / "fallback"), ttl=60, max_size=10
        )
        primary.get = AsyncMock(side_effect=RuntimeError("primary failure"))
        fallback.get = AsyncMock(side_effect=OSError("fallback failure"))
        cache = UnifiedCacheManager(backend=primary, fallback_backend=fallback)

        result = await cache.get("any_key")
        assert result is None

    async def test_close(self, unified):
        await unified.close()

    async def test_get_unified_cache_singleton(self):
        instance1 = get_unified_cache()
        instance2 = get_unified_cache()
        assert instance1 is instance2

    async def test_stats_property(self, unified):
        stats = unified.stats
        assert isinstance(stats, CacheStats)
        assert stats.hits == 0


class TestCacheResultDecorator:
    async def test_caches_result(self, isolated_fallback):
        call_count = 0

        @cache_result(ttl=60)
        async def heavy_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            r1 = await heavy_func(5)
            r2 = await heavy_func(5)
            r3 = await heavy_func(10)

        assert r1 == 10
        assert r2 == 10
        assert r3 == 20
        assert call_count == 2

    async def test_cache_penetration_protection(self, isolated_fallback):
        call_count = 0

        @cache_result(ttl=60, null_ttl=1)
        async def returns_none(x: int) -> int | None:  # noqa: ARG001
            nonlocal call_count
            call_count += 1
            return None

        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            r1 = await returns_none(1)
            r2 = await returns_none(1)
            r3 = await returns_none(2)

        assert r1 is None
        assert r2 is None
        assert r3 is None
        assert call_count == 2

    async def test_different_args_different_cache(self, isolated_fallback):
        call_log = []

        @cache_result(ttl=60)
        async def add(a: int, b: int) -> int:
            call_log.append((a, b))
            return a + b

        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            await add(1, 2)
            await add(2, 1)
            await add(1, 2)

        assert len(call_log) == 2

    async def test_kwargs_caching(self, isolated_fallback):
        call_count = 0

        @cache_result(ttl=60)
        async def greet(name: str, greeting: str = "hello") -> str:
            nonlocal call_count
            call_count += 1
            return f"{greeting} {name}"

        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            r1 = await greet("world")
            r2 = await greet("world")
            r3 = await greet("world", greeting="hi")

        assert r1 == "hello world"
        assert r2 == "hello world"
        assert r3 == "hi world"
        assert call_count == 2

    async def test_without_parentheses(self, isolated_fallback):
        """测试不带括号使用装饰器: @cache_result."""
        call_count = 0

        @cache_result
        async def compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 3

        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            r1 = await compute(3)
            r2 = await compute(3)

        assert r1 == 9
        assert r2 == 9
        assert call_count == 1


class TestCacheKeyGeneration:
    def test_same_args_produce_same_key(self):
        k1 = generate_cache_key("analysis", "case_text")
        k2 = generate_cache_key("analysis", "case_text")
        assert k1 == k2

    def test_different_args_produce_different_key(self):
        k1 = generate_cache_key("analysis", "case_a")
        k2 = generate_cache_key("analysis", "case_b")
        assert k1 != k2

    def test_key_is_hex_string(self):
        key = generate_cache_key("data")
        assert all(c in "0123456789abcdef" for c in key)

    def test_key_includes_salt(self):
        k1 = generate_cache_key("same")
        raw = json.dumps(("different_salt", "same"), ensure_ascii=False, default=str)
        k2 = hashlib.new(AnalysisConfig.CACHE_HASH_ALGORITHM, raw.encode("utf-8")).hexdigest()
        assert k1 != k2


class TestSecureCacheKey:
    """_secure_cache_key 安全键处理函数测试."""

    def test_deterministic_output(self):
        k1 = _secure_cache_key("test_key")
        k2 = _secure_cache_key("test_key")
        assert k1 == k2

    def test_different_keys_produce_different_output(self):
        k1 = _secure_cache_key("key_a")
        k2 = _secure_cache_key("key_b")
        assert k1 != k2

    def test_output_is_hex_string(self):
        key = _secure_cache_key("any_key")
        assert all(c in "0123456789abcdef" for c in key)
        assert len(key) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_prevent_path_traversal(self):
        """验证路径遍历字符在输入层即被拦截."""
        dangerous = "../../etc/passwd"
        with pytest.raises(CacheKeyValidationError) as exc_info:
            _secure_cache_key(dangerous)
        assert "/" in exc_info.value.invalid_chars

    def test_salt_affects_output(self):
        k1 = _secure_cache_key("same_key")
        raw = hashlib.sha256(
            b"different_salt:same_key"
        ).hexdigest()[: AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH]
        assert k1 != raw


class TestSecureCacheKeyEnhanced:
    """_secure_cache_key 安全增强功能测试.

    覆盖哈希生成、长度截断、输入校验和确定性等场景。
    """

    def test_valid_key_produces_correct_hashed_filename(self):
        """合法缓存键生成正确的哈希文件名."""
        key = "user_profile:123"
        result = _secure_cache_key(key)
        assert isinstance(result, str)
        assert len(result) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH
        assert all(c in "0123456789abcdef" for c in result)

    def test_long_cache_key_produces_fixed_length_hash(self):
        """过长缓存键生成固定长度的哈希文件名."""
        long_key = "a" * 500
        result = _secure_cache_key(long_key)
        assert len(result) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_invalid_chars_raise_validation_error(self):
        """包含非法字符的缓存键被正确拦截并抛出异常."""
        invalid_cases = [
            ("key with space", " "),
            ("key\nnewline", "\n"),
            ("key@symbol", "@"),
            ("../../traversal", "/"),
            ("key|pipe", "|"),
            ("key&special", "&"),
        ]
        for bad_key, expected_char in invalid_cases:
            with pytest.raises(CacheKeyValidationError) as exc_info:
                _secure_cache_key(bad_key)
            assert expected_char in exc_info.value.invalid_chars, (
                f"期望在非法字符中找到 {expected_char!r}"
            )
            assert bad_key == exc_info.value.invalid_key

    def test_same_key_produces_same_hash(self):
        """相同缓存键始终生成相同的哈希文件名."""
        key = "consistent_key:v1"
        results = [_secure_cache_key(key) for _ in range(10)]
        assert all(r == results[0] for r in results)

    def test_different_keys_produce_different_hashes(self):
        """不同缓存键生成不同的哈希文件名."""
        keys = [f"user:{i}_profile_data" for i in range(100)]
        hashes = {_secure_cache_key(k) for k in keys}
        assert len(hashes) == 100

    def test_all_valid_characters_accepted(self):
        """所有允许的安全字符集均能正常通过验证."""
        valid_key = "User_123:data.config-v2"
        result = _secure_cache_key(valid_key)
        assert len(result) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_empty_key_validation(self):
        """空字符串缓存键的处理."""
        result = _secure_cache_key("")
        assert len(result) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_chinese_characters_blocked(self):
        """中文字符被正确拦截."""
        with pytest.raises(CacheKeyValidationError) as exc_info:
            _secure_cache_key("用户数据")
        assert exc_info.value.invalid_chars

    def test_truncate_length_consistency(self):
        """验证截取长度始终与配置一致."""
        keys = ["simple", "somewhat_longer_key:v2.0_test", "u:1"]
        for key in keys:
            assert len(_secure_cache_key(key)) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_allowed_chars_at_boundaries(self):
        """允许字符边界测试 —— 仅包含允许字符集的键."""
        boundary_key = "A-Z_a-z:0-9.test-case"
        result = _secure_cache_key(boundary_key)
        assert len(result) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_validation_error_message_contains_useful_info(self):
        """验证异常消息包含有用的调试信息."""
        bad_key = "key/with/slash"
        with pytest.raises(CacheKeyValidationError) as exc_info:
            _secure_cache_key(bad_key)
        msg = str(exc_info.value)
        assert bad_key in msg
        assert "/" in msg
        assert "a-zA-Z0-9" in msg


class TestCacheManagerCompat:
    """CacheManager 同步兼容 API 测试."""

    def test_get_set(self):
        cm = CacheManager(ttl=3600, max_size=100)
        cm.set("compat_key", {"name": "test"})
        result = cm.get("compat_key")
        assert result == {"name": "test"}

    def test_get_missing(self):
        cm = CacheManager()
        result = cm.get("no_such_compat_key")
        assert result is None

    def test_clear(self):
        cm = CacheManager(ttl=60, max_size=100)
        cm.set("k1", "v1")
        cm.set("k2", "v2")
        cm.clear()
        assert cm.get("k1") is None
        assert cm.get("k2") is None


class TestModuleLevelFunctions:
    async def test_cache_get_set(self, isolated_fallback):
        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            await cache_set("module_key", "module_value", ttl=60)
            result = await cache_get("module_key")
            assert result == "module_value"

    async def test_cache_delete(self, isolated_fallback):
        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            await cache_set("del_key", "value", ttl=60)
            await cache_delete("del_key")
            result = await cache_get("del_key")
            assert result is None

    async def test_get_cache_stats(self, isolated_fallback):
        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            stats = get_cache_stats()
            assert "hits" in stats
            assert "misses" in stats
            assert "errors" in stats
            assert "hit_rate" in stats


class TestFileCacheCleanup:
    """FileCache._cleanup 方法的清理策略测试."""

    async def test_cleanup_deletes_oldest_files_first(self, file_cache, tmp_path):
        """验证清理时优先删除修改时间(mtime)最早的文件."""
        file_cache.max_size = 3
        file_cache._cache_dir = str(tmp_path)

        for i in range(5):
            await file_cache.set(f"key{i}", f"val{i}")
            await asyncio.sleep(0.02)

        remaining = []
        for i in range(5):
            result = await file_cache.get(f"key{i}")
            if result == f"val{i}":
                remaining.append(i)

        assert len(remaining) == 3
        assert 0 not in remaining
        assert 1 not in remaining
        assert 2 in remaining
        assert 3 in remaining
        assert 4 in remaining

    async def test_cleanup_at_capacity_no_deletion(self, file_cache, tmp_path):
        """验证缓存数量等于 max_size 时不触发清理."""
        file_cache.max_size = 3
        file_cache._cache_dir = str(tmp_path)

        for i in range(3):
            await file_cache.set(f"key{i}", f"val{i}")
        await asyncio.sleep(0.02)

        for i in range(3):
            assert await file_cache.get(f"key{i}") == f"val{i}"

    async def test_cleanup_directory_not_found(self, file_cache, tmp_path):
        """验证缓存目录不存在时的异常处理."""
        nonexistent = str(tmp_path / "nonexistent")
        file_cache._cache_dir = nonexistent
        file_cache.max_size = 1

        await file_cache._cleanup()

    async def test_cleanup_large_number_of_files(self, file_cache, tmp_path):
        """验证大量缓存文件场景下的清理正确性."""
        file_cache.max_size = 10
        file_cache._cache_dir = str(tmp_path)
        total = 50

        for i in range(total):
            await file_cache.set(f"key{i}", f"val{i}")
            await asyncio.sleep(0.002)

        count = 0
        for i in range(total):
            if await file_cache.get(f"key{i}") == f"val{i}":
                count += 1
        assert count == 10


class TestCacheManagerCleanup:
    """CacheManager._cleanup 方法的清理策略测试."""

    def test_cleanup_deletes_oldest_files_first(self, tmp_path):
        """验证清理时优先删除修改时间(mtime)最早的文件."""
        cm = CacheManager(ttl=3600, max_size=3)
        cm._cache_dir = str(tmp_path)

        for i in range(5):
            cm.set(f"key{i}", f"val{i}")
            time.sleep(0.02)

        remaining = []
        for i in range(5):
            result = cm.get(f"key{i}")
            if result == f"val{i}":
                remaining.append(i)

        assert len(remaining) == 3
        assert 0 not in remaining
        assert 1 not in remaining

    def test_cleanup_at_capacity(self, tmp_path):
        """验证缓存数量等于 max_size 时不触发清理."""
        cm = CacheManager(ttl=3600, max_size=3)
        cm._cache_dir = str(tmp_path)

        for i in range(3):
            cm.set(f"key{i}", f"val{i}")

        for i in range(3):
            assert cm.get(f"key{i}") == f"val{i}"

    def test_cleanup_directory_not_found(self, tmp_path):
        """验证缓存目录不存在时的异常处理."""
        cm = CacheManager(ttl=3600, max_size=1)
        cm._cache_dir = str(tmp_path / "nonexistent")

        cm._cleanup()

    def test_cleanup_large_number_of_files(self, tmp_path):
        """验证大量缓存文件场景下的清理正确性."""
        cm = CacheManager(ttl=3600, max_size=10)
        cm._cache_dir = str(tmp_path)
        total = 50

        for i in range(total):
            cm.set(f"key{i}", f"val{i}")
            time.sleep(0.002)

        count = 0
        for i in range(total):
            if cm.get(f"key{i}") == f"val{i}":
                count += 1
        assert count == 10


class TestFileCachePathlibOperations:
    """FileCache 中 pathlib 异步文件操作测试."""

    async def test_delete_nonexistent_key_no_error(self, file_cache):
        """验证删除不存在的文件不抛出异常."""
        await file_cache.delete("nonexistent_key")

    async def test_clear_empty_directory(self, file_cache, tmp_path):
        """验证清空空目录不抛出异常."""
        empty_dir = tmp_path / "empty_cache"
        empty_dir.mkdir()
        file_cache._cache_dir = str(empty_dir)

        await file_cache.clear()

    async def test_exists_uses_pathlib(self, file_cache):
        """验证 exists 方法使用 pathlib 正确判断文件存在性."""
        await file_cache.set("exists_test", "value")
        assert await file_cache.exists("exists_test") is True
        assert await file_cache.exists("nonexistent") is False

    async def test_pathlib_based_file_operations(self, file_cache, tmp_path):
        """验证 pathlib 文件操作与旧 os.path 行为兼容."""
        file_cache._cache_dir = str(tmp_path)
        test_key = "pathlib_test"
        test_value = {"nested": {"key": "value"}}

        await file_cache.set(test_key, test_value)
        safe_key = _secure_cache_key(test_key)
        cache_file = Path(tmp_path) / f"{safe_key}.json"
        assert cache_file.exists()
        result = await file_cache.get(test_key)
        assert result == test_value
        await file_cache.delete(test_key)
        assert not cache_file.exists()

    async def test_cleanup_mtime_sorting_with_stat_error(self, file_cache, tmp_path):
        """验证 stat() 获取 mtime 异常时的降级处理."""
        file_cache.max_size = 1
        file_cache._cache_dir = str(tmp_path)

        await file_cache.set("key0", "val0")
        await file_cache.set("key1", "val1")

        with patch.object(Path, "stat", side_effect=OSError("mtime error")):
            await file_cache._cleanup()


class TestFileCacheBackendExists:
    """FileCacheBackend.exists() 测试."""

    async def test_exists_true(self, file_cache_backend):
        await file_cache_backend.set("e1", "v1")
        assert await file_cache_backend.exists("e1") is True

    async def test_exists_false(self, file_cache_backend):
        assert await file_cache_backend.exists("no_key") is False

    async def test_exists_expired(self, file_cache_backend, tmp_path):
        """验证 exists 仅检查文件存在性，不校验 TTL."""
        file_cache_backend._cache_dir = str(tmp_path)
        file_cache_backend.ttl = 0
        await file_cache_backend.set("exp", "val")
        await asyncio.sleep(0.02)
        assert await file_cache_backend.exists("exp") is True
