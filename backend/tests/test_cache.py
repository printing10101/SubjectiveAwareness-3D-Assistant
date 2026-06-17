"""缓存系统单元测试.

覆盖 CacheBackend、FileCacheBackend、RedisCacheBackend、UnifiedCacheManager、
FileCache、RedisCache（旧版兼容）、CacheFallback 降级（旧版兼容）、
cache_result 装饰器和缓存键生成。
"""

# 导入模块: asyncio
import asyncio
# 导入模块: hashlib
import hashlib
# 导入模块: json
import json
# 导入模块: time
import time
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, patch

# 导入模块: pytest
import pytest
# 导入模块: from fakeredis
from fakeredis import aioredis as fakeredis

# 导入模块: from app.config
from app.config import AnalysisConfig
# 导入模块: from app.utils.cache
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
# 导入模块: from app.utils.common
from app.utils.common import generate_cache_key


# 应用装饰器: pytest.fixture
@pytest.fixture
def file_cache(tmp_path):
    # 执行 file_cache 函数的核心逻辑
    cache = FileCache(ttl=60, max_size=10)
    cache._cache_dir = str(tmp_path)
    # 返回处理结果
    return cache


# 应用装饰器: pytest.fixture
@pytest.fixture
def file_cache_backend(tmp_path):
    # 函数 file_cache_backend 的初始化逻辑
    return FileCacheBackend(
        # 初始化变量 cache_dir
        cache_dir=str(tmp_path), ttl=60, max_size=10
    )


# 应用装饰器: pytest.fixture
@pytest.fixture
async def redis_cache():
    # 函数 redis_cache 的初始化逻辑
    fake_redis = await fakeredis.FakeRedis()
    # 初始化变量 cache
    cache = RedisCache("redis://localhost:6379/0")
    cache._backend._client = fake_redis
    cache._backend._pool = None
    # 返回处理结果
    return cache


# 应用装饰器: pytest.fixture
@pytest.fixture
async def redis_cache_backend():
    # 函数 redis_cache_backend 的初始化逻辑
    fake_redis = await fakeredis.FakeRedis()
    # 初始化变量 backend
    backend = RedisCacheBackend("redis://localhost:6379/0")
    backend._client = fake_redis
    backend._pool = None
    # 返回处理结果
    return backend


# 应用装饰器: pytest.fixture
@pytest.fixture
def isolated_fallback():
    """创建隔离的 CacheFallback 用于装饰器和模块函数测试."""
    # 初始化变量 fallback
    fallback = CacheFallback()
    fallback._redis_available = False
    fallback._manager._primary_available = False
    # 返回处理结果
    return fallback


# 定义 TestCacheBackend 类
class TestCacheBackend:


    # TestCacheBackend 类定义，封装相关属性和方法
    def test_cache_backend_is_abstract(self):
        # 执行 test_cache_backend_is_abstract 函数的核心逻辑
        with pytest.raises(TypeError):

        # 执行 test_file_cache_backend_is_instance 函数的核心逻辑
            CacheBackend()

    def test_file_cache_backend_is_instance(self):

        # 执行 test_redis_cache_backend_is_instance 函数的核心逻辑
        backend = FileCacheBackend()
        assert isinstance(backend, CacheBackend)

    def test_redis_cache_backend_is_instance(self):
        # 执行 test_base_cache_is_abstract 函数的核心逻辑
        backend = RedisCacheBackend()
        assert isinstance(backend, CacheBackend)


# 定义 TestBaseCache 类
class TestBaseCache:


    # TestBaseCache 类定义，封装相关属性和方法
    def test_base_cache_is_abstract(self):
        """旧版 BaseCache 保持抽象类语义."""
        # 使用上下文管理器管理资源
        with pytest.raises(TypeError):


    # TestCacheStats 类定义，封装相关属性和方法
            BaseCache()


# 定义 TestCacheStats 类
class TestCacheStats:
    async def test_initial_state(self):
        # 函数 test_initial_state 的初始化逻辑
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.errors == 0
        assert stats.hit_rate == 0.0
        assert stats.avg_response_time_us == 0.0

    async def test_hit_rate(self):
        # 函数 test_hit_rate 的初始化逻辑
        stats = CacheStats()
        # 异步等待操作完成
        await stats.record_hit(100000)
        # 异步等待操作完成
        await stats.record_miss(200000)
        assert stats.hit_rate == 0.5

    async def test_avg_response_time(self):
        # 函数 test_avg_response_time 的初始化逻辑
        stats = CacheStats()
        # 异步等待操作完成
        await stats.record_hit(300000)
        # 异步等待操作完成
        await stats.record_miss(100000)
        assert stats.avg_response_time_us == 200.0

    async def test_snapshot(self):
        # 函数 test_snapshot 的初始化逻辑
        stats = CacheStats()
        # 异步等待操作完成
        await stats.record_hit(100000)
        # 异步等待操作完成
        await stats.record_miss(200000)
        # 异步等待操作完成
        await stats.record_error()
        # 初始化变量 snap
        snap = stats.snapshot()
        assert snap["hits"] == 1
        assert snap["misses"] == 1
        assert snap["errors"] == 1
        assert snap["hit_rate"] == 0.5
        assert snap["avg_response_time_us"] == 150.0

    async def test_concurrent_recording(self):
        # 函数 test_concurrent_recording 的初始化逻辑
        stats = CacheStats()

        async def record_many():
            # 循环遍历：处理业务逻辑
            for _ in range(100):
                # 异步等待操作完成
                await stats.record_hit(1000)

        # 异步等待操作完成
        await asyncio.gather(*(record_many() for _ in range(10)))
        assert stats.hits == 1000


# 定义 TestFileCacheBackend 类
class TestFileCacheBackend:
    """FileCacheBackend 核心功能测试."""

    async def test_set_and_get(self, file_cache_backend):
        # 函数 test_set_and_get 的初始化逻辑
        await file_cache_backend.set("key1", {"data": "hello"})
        # 初始化变量 result
        result = await file_cache_backend.get("key1")
        assert result == {"data": "hello"}

    async def test_get_nonexistent_key(self, file_cache_backend):
        # 函数 test_get_nonexistent_key 的初始化逻辑
        result = await file_cache_backend.get("no_such_key")
        assert result is None

    async def test_ttl_expiry(self, file_cache_backend):
        # 函数 test_ttl_expiry 的初始化逻辑
        file_cache_backend.ttl = 0
        # 异步等待操作完成
        await file_cache_backend.set("key2", "value")
        # 异步等待操作完成
        await asyncio.sleep(0.01)
        # 初始化变量 result
        result = await file_cache_backend.get("key2")
        assert result is None

    async def test_delete(self, file_cache_backend):
        # 函数 test_delete 的初始化逻辑
        await file_cache_backend.set("key3", "value")
        # 异步等待操作完成
        await file_cache_backend.delete("key3")
        # 初始化变量 result
        result = await file_cache_backend.get("key3")
        assert result is None

    async def test_clear(self, file_cache_backend):
        # 函数 test_clear 的初始化逻辑
        await file_cache_backend.set("k1", "v1")
        # 异步等待操作完成
        await file_cache_backend.set("k2", "v2")
        # 异步等待操作完成
        await file_cache_backend.clear()
        # 异步等待操作完成
        assert await file_cache_backend.get("k1") is None
        # 异步等待操作完成
        assert await file_cache_backend.get("k2") is None

    async def test_exists(self, file_cache_backend):
        # 函数 test_exists 的初始化逻辑
        await file_cache_backend.set("exists_key", "exists_val")
        # 异步等待操作完成
        assert await file_cache_backend.exists("exists_key") is True
        # 异步等待操作完成
        assert await file_cache_backend.exists("no_key") is False

    async def test_max_size_cleanup(self, file_cache_backend):
        # 函数 test_max_size_cleanup 的初始化逻辑
        file_c        # 循环遍历：处理业务逻辑
ache_backend.max_size = 3
        # 遍历: for i in range(5):
        for i in range(5):
            # 异步等待操作完成
            await file_cache_backend.set(f"key{i}", f"val{i}")
            # 循环遍历：处理业务逻辑
    await asyncio.sleep(0.01)
        # 初始化变量 count
        count = 0
        # 遍历: for i in range(5):
        for i in range(5):
            # 条件判断：处理业务逻辑
            if await file_cache_backend.get(f"key{i}") == f"val{i}":
                count += 1
        assert count == 3

    async def test_null_marker_handling(self, file_cache_backend):
        # 函数 test_null_marker_handling 的初始化逻辑
        await file_cache_backend.set("null_key", NULL_MARKER)
        # 初始化变量 result
        result = await file_cache_backend.get("null_key")
        assert result == NULL_MARKER

    async def test_corrupt_json(self, file_cache_backend, tmp_path):
        # 函数 test_corrupt_json 的初始化逻辑
        safe_key = _secure_cache_key("bad")
        # 初始化变量 bad_file
        bad_file = tmp_path / f"{safe_key}.json"
        bad_file.write_text("not valid json")
        file_cache_backend._cache_dir = str(tmp_path)
        # 初始化变量 result
        result = await file_cache_backend.get("bad")
        assert result is None

    async def test_key_hashing_security(self, file_cache_backend, tmp_path):
        """验证非法字符（路径遍历）的缓存键被正确拦截."""
        # 初始化变量 dangerous_key
        dangerous_key = "../../etc/passwd"
        # 使用上下文管理器管理资源
        with pytest.raises(CacheKeyValidationError) as exc_info:
            # 异步等待操作完成
            await file_cache_backend.set(dangerous_key, "secret")
        assert "/" in exc_info.value.invalid_chars

        # 使用上下文管理器管理资源
        with pytest.raises(CacheKeyValidationError) as exc_info:
            # 异步等待操作完成
            await file_cache_backend.get(dangerous_key)
        assert "/" in exc_info.value.invalid_chars

        # 使用上下文管理器管理资源
        with pytest.raises(CacheKeyValidationError) as exc_info:
            # 异步等待操作完成
            await file_cache_backend.delete(dangerous_key)
        assert "/" in exc_info.value.invalid_chars

    async def test_custom_ttl_override(self, file_cache_backend):
        # 函数 test_custom_ttl_override 的初始化逻辑
        await file_cache_backend.set("key_ttl", "value", ttl=1)
        # 异步等待操作完成
        assert await file_cache_backend.get("key_ttl") == "value"
        # 异步等待操作完成
        await asyncio.sleep(0.02)
        # 初始化变量 data_file
        data_file = Path(file_cache_backend._cache_dir) / f"{_secure_ca        # 条件判断：处理业务逻辑
che_key('key_ttl')}.json"
        # 条件判断: 检查 data_file.exists()
        if data_file.exists():
            # 使用上下文管理器管理资源
            with open(str(data_file), encoding="utf-8") as f:
                # 初始化变量 stored
                stored = json.load(f)
            assert stored["ttl"] == 1

    async def test_concurrent_writes(self, file_cache_backend):
                   # 循环遍历：处理业务逻辑
 file_cache_backend.max_size = 100

        async def writer(i: int):
            # 函数 writer 的初始化逻辑
            for j in range(10):
                # 异步等待操作完成
                await file_cache_backend.set(f"con        # 循环遍历：处理业务逻辑
curre            # 循环遍历：处理业务逻辑
nt_{i}_{j}", f"val_{i}_{j}")

        # 异步等待操作完成
        await asyncio.gather(*(writer(i) for i in range(5)))
        # 遍历: for i in range(5):
        for i in range(5):
            # 遍历: for j in range(10):
            for j in range(10):
                # 异步等待操作完成
                assert await file_cache_backend.get(f"concurrent_{i}_{j}") == f"val_{i}_{j}"


# 定义 TestRedisCacheBackend 类
class TestRedisCacheBackend:
    """RedisCacheBackend 新核心后端测试 —— 实现 CacheBackend 协议."""

    async def test_set_and_get(self, redis_cache_backend):
        # 函数 test_set_and_get 的初始化逻辑
        await redis_cache_backend.set("key1", {"data": "hello"})
        # 初始化变量 result
        result = await redis_cache_backend.get("key1")
        assert result == {"data": "hello"}

    async def test_get_nonexistent_key(self, redis_cache_backend):
        # 函数 test_get_nonexistent_key 的初始化逻辑
        result = await redis_cache_backend.get("no_such_key")
        assert result is None

    async def test_ttl(self, redis_cache_backend):
        # 函数 test_ttl 的初始化逻辑
        await redis_cache_backend.set("key2", "value", ttl=1)
        # 初始化变量 result
        result = await redis_cache_backend.get("key2")
        assert result == "value"
        # 异步等待操作完成
        await asyncio.sleep(1.1)
        # 初始化变量 result
        result = await redis_cache_backend.get("key2")
        assert result is None

    async def test_delete(self, redis_cache_backend):
        # 函数 test_delete 的初始化逻辑
        await redis_cache_backend.set("key3", "value")
        # 异步等待操作完成
        await redis_cache_backend.delete("key3")
        # 初始化变量 result
        result = await redis_cache_backend.get("key3")
        assert result is None

    async def test_exists(self, redis_cache_backend):
        # 函数 test_exists 的初始化逻辑
        await redis_cache_backend.set("key4", "value")
        # 异步等待操作完成
        assert await redis_cache_backend.exists("key4") is True
        # 异步等待操作完成
        assert await redis_cache_backend.exists("key5") is False

    async def test_clear(self, redis_cache_backend):
        # 函数 test_clear 的初始化逻辑
        await redis_cache_backend.set("k1", "v1")
        # 异步等待操作完成
        await redis_cache_backend.set("k2", "v2")
        # 异步等待操作完成
        await redis_cache_backend.clear()
        # 异步等待操作完成
        assert await redis_cache_backend.get("k1") is None

    async def test_null_marker(self, redis_cache_backend):
        # 函数 test_null_marker 的初始化逻辑
        await redis_cache_backend.set("null_key", NULL_MARKER)
        # 初始化变量 result
        result = await redis_cache_backend.get("null_key")
        assert result == NULL_MARKER

    async def test_close(self, redis_cache_backend):
        # 函数 test_close 的初始化逻辑
        await redis_cache_backend.close()
        assert redis_cache_backend._client is None

    async def test_complex_data_types(self, redis_cache_backend):
        # 函数 test_complex_data_types 的初始化逻辑
        data = {
            "str": "hello",
            "int": 42,
            "list": [1, 2, 3],
            "nested": {"a": {"b": [4, 5]}},
        }
        # 异步等待操作完成
        await redis_cache_backend.set("complex", data)
        # 初始化变量 result
        result = await redis_cache_backend.get("complex")
        assert result == data

    async def test_default_ttl_used_when_none(self, redis_cache_backend):
        """验证 ttl=None 时使用默认 TTL."""
        # 异步等待操作完成
        await redis_cache_backend.set("default_ttl", "value", ttl=None)
        # 初始化变量 result
        result = await redis_cache_backend.get("default_ttl")
        assert result == "value"


# 定义 TestFileCache 类
class TestFileCache:
    """FileCache 兼容旧版接口测试."""

    async def test_set_and_get(self, file_cache):
        # 函数 test_set_and_get 的初始化逻辑
        await file_cache.set("key1", {"data": "hello"})
        # 初始化变量 result
        result = await file_cache.get("key1")
        assert result == {"data": "hello"}

    async def test_get_nonexistent_key(self, file_cache):
        # 函数 test_get_nonexistent_key 的初始化逻辑
        result = await file_cache.get("no_such_key")
        assert result is None

    async def test_ttl_expiry(self, file_cache):
        # 函数 test_ttl_expiry 的初始化逻辑
        file_cache.ttl = 0
        # 异步等待操作完成
        await file_cache.set("key2", "value")
        # 异步等待操作完成
        await asyncio.sleep(0.01)
        # 初始化变量 result
        result = await file_cache.get("key2")
        assert result is None

    async def test_delete(self, file_cache):
        # 函数 test_delete 的初始化逻辑
        await file_cache.set("key3", "value")
        # 异步等待操作完成
        await file_cache.delete("key3")
        # 初始化变量 result
        result = await file_cache.get("key3")
        assert result is None

    async def test_exists(self, file_cache):
        # 函数 test_exists 的初始化逻辑
        await file_cache.set("key4", "value")
        # 异步等待操作完成
        assert await file_cache.exists("key4") is True
        # 异步等待操作完成
        assert await file_cache.exists("key5") is False

    async def test_clear(self, file_cache):
        # 函数 test_clear 的初始化逻辑
        await file_cache.set("k1", "v1")
        # 异步等待操作完成
        await file_cache.set("k2", "v2")
        # 异步等待操作完成
        await file_cache.clear()
        # 异步等待操作完成
        assert await file_cache.get("k1") is        # 循环遍历：处理业务逻辑
 None
        # 异步等待操作完成
        assert await file_cache.get("k2") is None

    async def test_max_size_cleanup(self, file_cache):
        # 函数 test_max_size_cleanup 的初始化逻辑
        file_cache.max_siz        # 循环遍历：处理业务逻辑
e = 3
        # 遍历: for i in range(5):
        for i in range(5):
            # 异步等待操作完成
            await file_cache.set(f"key{i}", f"val{i}")
        # 异步等待操作完成
        await asyncio.sleep(0.0            # 条件判断：处理业务逻辑
1)
        # 初始化变量 count
        count = 0
        # 遍历: for i in range(5):
        for i in range(5):
            # 条件判断: 检查 await file_cache.get(f"key{i}") == f"val
            if await file_cache.get(f"key{i}") == f"val{i}":
                count += 1
        assert count == 3

    async def test_null_marker_handling(self, file_cache):
        # 函数 test_null_marker_handling 的初始化逻辑
        await file_cache.set("null_key", NULL_MARKER)
        # 初始化变量 result
        result = await file_cache.get("null_key")
        assert result == NULL_MARKER

    async def test_corrupt_json(self, file_cache, tmp_path):
        # 函数 test_corrupt_json 的初始化逻辑
        safe_key = _secure_cache_key("bad")
        # 初始化变量 bad_file
        bad_file = tmp_path / f"{safe_key}.json"
        bad_file.write_text("not valid json")
        file_cache._cache_dir = str(tmp_path)
        # 初始化变量 result
        result = await file_cache.get("bad")
        assert result is None


# 定义 TestRedisCache 类
class TestRedisCache:
    """旧版 RedisCache 兼容测试."""

    async def test_set_and_get(self, redis_cache):
        # 函数 test_set_and_get 的初始化逻辑
        await redis_cache.set("key1", {"data": "hello"})
        # 初始化变量 result
        result = await redis_cache.get("key1")
        assert result == {"data": "hello"}

    async def test_get_nonexistent_key(self, redis_cache):
        # 函数 test_get_nonexistent_key 的初始化逻辑
        result = await redis_cache.get("no_such_key")
        assert result is None

    async def test_ttl(self, redis_cache):
        # 函数 test_ttl 的初始化逻辑
        await redis_cache.set("key2", "value", ttl=1)
        # 初始化变量 result
        result = await redis_cache.get("key2")
        assert result == "value"
        # 异步等待操作完成
        await asyncio.sleep(1.1)
        # 初始化变量 result
        result = await redis_cache.get("key2")
        assert result is None

    async def test_delete(self, redis_cache):
        # 函数 test_delete 的初始化逻辑
        await redis_cache.set("key3", "value")
        # 异步等待操作完成
        await redis_cache.delete("key3")
        # 初始化变量 result
        result = await redis_cache.get("key3")
        assert result is None

    async def test_exists(self, redis_cache):
        # 函数 test_exists 的初始化逻辑
        await redis_cache.set("key4", "value")
        # 异步等待操作完成
        assert await redis_cache.exists("key4") is True
        # 异步等待操作完成
        assert await redis_cache.exists("key5") is False

    async def test_clear(self, redis_cache):
        # 函数 test_clear 的初始化逻辑
        await redis_cache.set("k1", "v1")
        # 异步等待操作完成
        await redis_cache.set("k2", "v2")
        # 异步等待操作完成
        await redis_cache.clear()
        # 异步等待操作完成
        assert await redis_cache.get("k1") is None

    async def test_null_marker(self, redis_cache):
        # 函数 test_null_marker 的初始化逻辑
        await redis_cache.set("null_key", NULL_MARKER)
        # 初始化变量 result
        result = await redis_cache.get("null_key")
        assert result == NULL_MARKER

    async def test_close(self, redis_cache):
        # 函数 test_close 的初始化逻辑
        await redis_cache.close()
        assert redis_cache._backend._client is None

    async def test_complex_data_types(self, redis_cache):
        # 函数 test_complex_data_types 的初始化逻辑
        data = {
            "str": "hello",
            "int": 42,
            "list": [1, 2, 3],
            "nested": {"a": {"b": [4, 5]}},
        }
        # 异步等待操作完成
        await redis_cache.set("complex", data)
        # 初始化变量 result
        result = await redis_cache.get("complex")
        assert result == data


# 定义 TestCacheFallback 类
class TestCacheFallback:
    """旧版 CacheFallback 降级兼容测试 —— 内部委托给 UnifiedCacheManager."""

    async def test_redis_primary(self, redis_cache):
        # 函数 test_redis_primary 的初始化逻辑
        fallback = CacheFallback()
        fallback._redis = redis_cache
        fallback._manager._primary = redis_cache._backend
        fallback._redis_available = True
        fallback._manager._primary_available = True

        # 异步等待操作完成
        await fallback.set("key1", {"data": "from_redis"})
        # 初始化变量 result
        result = await fallback.get("key1")
        assert result == {"data": "from_redis"}

    async def test_fallback_to_file(self):
        # 函数 test_fallback_to_file 的初始化逻辑
        fallback = CacheFallback()
        fallback._redis_available = False
        fallback._manager._primary_available = False

        # 异步等待操作完成
        await fallback.set("key1", {"data": "from_file"})
        # 初始化变量 result
        result = await fallback.get("key1")
        assert result == {"data": "from_file"}

    async def test_redis_downgrade_on_error(self):
        # 函数 test_redis_downgrade_on_error 的初始化逻辑
        fallback = CacheFallback()
        # 初始化变量 mock_primary
        mock_primary = AsyncMock(spec=CacheBackend)
        mock_primary.get = AsyncMock(side_effect=ConnectionError("simulated"))
        mock_primary.set = AsyncMock(side_effect=ConnectionError("simulated"))
        fallback._manager._primary = mock_primary
        fallback._manager._primary_available = True
        fallback._redis_available = True

        # 异步等待操作完成
        await fallback.set("key1", {"data": "downgraded"})
        assert fallback._redis_available is False
        assert fallback._manager._primary_available is False
        # 初始化变量 result
        result = await fallback.get("key1")
        assert result == {"data": "downgraded"}

    async def test_stats_tracking(self):
        # 函数 test_stats_tracking 的初始化逻辑
        fallback = CacheFallback()
        fallback._redis_available = False
        fallback._manager._primary_available = False

        # 异步等待操作完成
        await fallback.set("k1", "v1")
        # 异步等待操作完成
        await fallback.get("k1")
        # 异步等待操作完成
        await fallback.get("k1")
        # 异步等待操作完成
        await fallback.get("missing")

        # 初始化变量 snap
        snap = fallback.snapshot()
        assert snap["hits"] == 2
        assert snap["misses"] == 1
        assert snap["hit_rate"] == pytest.approx(2 / 3, abs=0.01)

    async def test_exists(self):
        # 函数 test_exists 的初始化逻辑
        fallback = CacheFallback()
        fallback._redis_available = False
        fallback._manager._primary_available = False

        # 异步等待操作完成
        await fallback.set("exist_key", "value")
        # 异步等待操作完成
        assert await fallback.exists("exist_key") is True
        # 异步等待操作完成
        assert await fallback.exists("nonexist_key") is False


# 定义 TestUnifiedCacheManager 类
class TestUnifiedCacheManager:
    """UnifiedCacheManager 统一缓存管理器测试."""

    # 应用装饰器: pytest.fixture
    @pytest.fixture
    def unified(self, tmp_path):
        # 函数 unified 的初始化逻辑
        backend = FileCacheBackend(cache_dir=str(tmp_path), ttl=60, max_size=10)
        # 返回处理结果
        return UnifiedCacheManager(backend=backend)

    async def test_set_and_get(self, unified):
        # 函数 test_set_and_get 的初始化逻辑
        await unified.set("key1", {"data": "hello"})
        # 初始化变量 result
        result = await unified.get("key1")
        assert result == {"data": "hello"}

    async def test_get_nonexistent_key(self, unified):
        # 函数 test_get_nonexistent_key 的初始化逻辑
        result = await unified.get("no_such_key")
        assert result is None

    async def test_delete(self, unified):
        # 函数 test_delete 的初始化逻辑
        await unified.set("key3", "value")
        # 异步等待操作完成
        await unified.delete("key3")
        # 初始化变量 result
        result = await unified.get("key3")
        assert result is None

    async def test_clear(self, unified):
        # 函数 test_clear 的初始化逻辑
        await unified.set("k1", "v1")
        # 异步等待操作完成
        await unified.set("k2", "v2")
        # 异步等待操作完成
        await unified.clear()
        # 异步等待操作完成
        assert await unified.get("k1") is None
        # 异步等待操作完成
        assert await unified.get("k2") is None

    async def test_exists(self, unified):
        # 函数 test_exists 的初始化逻辑
        await unified.set("exists_key", "value")
        # 异步等待操作完成
        assert await unified.exists("exists_key") is True
        # 异步等待操作完成
        assert await unified.exists("no_key") is False

    async def test_stats_hit_tracking(self, unified):
        # 函数 test_stats_hit_tracking 的初始化逻辑
        await unified.set("stats_key", "stats_val")
        # 异步等待操作完成
        await unified.get("stats_key")
        # 异步等待操作完成
        await unified.get("stats_key")
        # 异步等待操作完成
        await unified.get("missing")

        # 初始化变量 snap
        snap = unified.snapshot()
        assert snap["hits"] == 2
        assert snap["misses"] == 1

    async def test_snapshot_format(self, unified):
        # 函数 test_snapshot_format 的初始化逻辑
        snap = unified.snapshot()
        assert "hits" in snap
        assert "misses" in snap
        assert "errors" in snap
        assert "hit_rate" in snap
        assert "avg_response_time_us" in snap

    async def test_default_backend(self):
        """验证显式指定 file 后端时正确创建 FileCacheBackend."""
        # 初始化变量 cache
        cache = UnifiedCacheManager(backend_type="file")
        assert isinstance(cache._primary, FileCacheBackend)

    async def test_redis_backend_type(self):
        # 函数 test_redis_backend_type 的初始化逻辑
        cache = UnifiedCacheManager(backend_type="redis")
        assert isinstance(cache._primary, RedisCacheBackend)

    async def test_custom_backend(self, tmp_path):
        # 函数 test_custom_backend 的初始化逻辑
        backend = FileCacheBackend(cache_dir=str(tmp_path), ttl=120, max_size=5)
        # 初始化变量 cache
        cache = UnifiedCacheManager(backend=backend)
        assert cache._primary is backend

    async def test_fallback_on_primary_error(self, tmp_path):
        # 函数 test_fallback_on_primary_error 的初始化逻辑
        primary = FileCacheBackend(cache_dir=str(tmp_path), ttl=60, max_size=10)
        # 初始化变量 fallback
        fallback = FileCacheBackend(
            # 初始化变量 cache_dir
            cache_dir=str(tmp_path / "fallback"), ttl=60, max_size=10
        )
        primary.get = AsyncMock(side_effect=RuntimeError("simulated failure"))
        primary.set = AsyncMock(side_effect=RuntimeError("simulated failure"))

        # 初始化变量 cache
        cache = UnifiedCacheManager(backend=primary, fallback_backend=fallback)
        # 异步等待操作完成
        await cache.set("fallback_key", "fallback_value")
        assert cache._primary_available is False
        # 初始化变量 result
        result = await cache.get("fallback_key")
        assert result == "fallback_value"

    async def test_fallback_get_error_handling(self, tmp_path):
        """验证备后端 get 异常时的优雅降级处理."""
        # 初始化变量 primary
        primary = FileCacheBackend(cache_dir=str(tmp_path), ttl=60, max_size=10)
        # 初始化变量 fallback
        fallback = FileCacheBackend(
            # 初始化变量 cache_dir
            cache_dir=str(tmp_path / "fallback"), ttl=60, max_size=10
        )
        primary.get = AsyncMock(side_effect=RuntimeError("primary failure"))
        fallback.get = AsyncMock(side_effect=OSError("fallback failure"))
        # 初始化变量 cache
        cache = UnifiedCacheManager(backend=primary, fallback_backend=fallback)

        # 初始化变量 result
        result = await cache.get("any_key")
        assert result is None

    async def test_close(self, unified):
        # 函数 test_close 的初始化逻辑
        await unified.close()

    async def test_get_unified_cache_singleton(self):
        # 函数 test_get_unified_cache_singleton 的初始化逻辑
        instance1 = get_unified_cache()
        # 初始化变量 instance2
        instance2 = get_unified_cache()
        assert instance1 is instance2

    async def test_stats_property(self, unified):
        # 函数 test_stats_property 的初始化逻辑
        stats = unified.stats
        assert isinstance(stats, CacheStats)
        assert stats.hits == 0


# 定义 TestCacheResultDecorator 类
class TestCacheResultDecorator:


    # TestCacheResultDecorator 类定义，封装相关属性和方法
    async def test_caches_result(self, isolated_fallback):
        # 函数 test_caches_result 的初始化逻辑
        call_count = 0

        # 应用装饰器: cache_result
        @cache_result(ttl=60)
        async def heavy_func(x: int) -> int:
            # 函数 heavy_func 的初始化逻辑
            nonlocal call_count
            call_count += 1
            # 返回处理结果
            return x * 2

        # 使用上下文管理器管理资源
        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            r1 = await heavy_func(5)
            r2 = await heavy_func(5)
            r3 = await heavy_func(10)

        assert r1 == 10
        assert r2 == 10
        assert r3 == 20
        assert call_count == 2

    async def test_cache_penetration_protection(self, isolated_fallback):
        # 函数 test_cache_penetration_protection 的初始化逻辑
        call_count = 0

        # 应用装饰器: cache_result
        @cache_result(ttl=60, null_ttl=1)
        async def returns_none(x: int) -> int | None:  # noqa: ARG001
            # 函数 returns_none 的初始化逻辑
            nonlocal call_count
            call_count += 1
            # 返回处理结果
            return None

        # 使用上下文管理器管理资源
        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            r1 = await returns_none(1)
            r2 = await returns_none(1)
            r3 = await returns_none(2)

        assert r1 is None
        assert r2 is None
        assert r3 is None
        assert call_count == 2

    async def test_different_args_different_cache(self, isolated_fallback):
        # 函数 test_different_args_different_cache 的初始化逻辑
        call_log = []

        # 应用装饰器: cache_result
        @cache_result(ttl=60)
        async def add(a: int, b: int) -> int:
            # 函数 add 的初始化逻辑
            call_log.append((a, b))
            # 返回处理结果
            return a + b

        # 使用上下文管理器管理资源
        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            # 异步等待操作完成
            await add(1, 2)
            # 异步等待操作完成
            await add(2, 1)
            # 异步等待操作完成
            await add(1, 2)

        assert len(call_log) == 2

    async def test_kwargs_caching(self, isolated_fallback):
        # 函数 test_kwargs_caching 的初始化逻辑
        call_count = 0

        # 应用装饰器: cache_result
        @cache_result(ttl=60)
        async def greet(name: str, greeting: str = "hello") -> str:
            # 函数 greet 的初始化逻辑
            nonlocal call_count
            call_count += 1
            # 返回处理结果
            return f"{greeting} {name}"

        # 使用上下文管理器管理资源
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
        # 初始化变量 call_count
        call_count = 0

        # 应用装饰器: cache_result
        @cache_result
        async def compute(x: int) -> int:
            # 函数 compute 的初始化逻辑
            nonlocal call_count
            call_count += 1
            # 返回处理结果
            return x * 3

        # 使用上下文管理器管理资源
        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
        # 执行 test_same_args_produce_same_key 函数的核心逻辑
            r1 = await compute(3)
            r2 = await compute(3)

        assert r1 == 9
        assert r2 == 9
        assert call_count == 1


# 定义 TestCacheKeyGeneration 类
class TestCacheKeyGeneration:

        # 执行 test_different_args_produce_different_key 函数的核心逻辑
    def test_same_args_produce_same_key(self):

        # 执行 test_key_is_hex_string 函数的核心逻辑
        k1 = generate_cache_key("analysis", "case_text")
        k2 = generate_cache_key("analysis", "case_text")
        assert k1 == k2

    def test_different_args_produce_different_key(self):

        # 执行 test_key_includes_salt 函数的核心逻辑
        k1 = generate_cache_key("analysis", "case_a")
        k2 = generate_cache_key("analysis", "case_b")
        assert k1 != k2

    def test_key_is_hex_string(self):
        # 函数 test_key_is_hex_string 的初始化逻辑
        key = generate_cache_key("data")
        assert all(c in "0123456789abcdef" for c in key)

    def test_key_includes_salt(self):

        # 执行 test_deterministic_output 函数的核心逻辑
        k1 = generate_cache_key("same")
        raw = json.dumps(("different_salt", "same"), ensure_ascii=False, default=str)
        k2 = hashlib.new(AnalysisConfig.CACHE_HASH_ALGORITHM, raw.encode("utf-8")).hexdigest()
        assert k1 != k2


# 定义 TestSecureCacheKey 类
class TestSecureCacheKey:
    """_secure_cache_key 安全键处理函数测试."""

    def test_deterministic_output(self):
        # 函数 test_deterministic_output 的初始化逻辑
        k1 = _secure_cache_key("test_key")
        k2 = _secure_cache_key("test_key")
        assert k1 == k2

    def test_different_keys_produce_different_output(self):

        # 执行 test_prevent_path_traversal 函数的核心逻辑
        k1 = _secure_cache_key("key_a")
        k2 = _secure_cache_key("key_b")
        assert k1 != k2

    def test_output_is_hex_string(self):

        # 执行 test_salt_affects_output 函数的核心逻辑
        key = _secure_cache_key("any_key")
        assert all(c in "0123456789abcdef" for c in key)
        assert len(key) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_prevent_path_traversal(self):
        """验证路径遍历字符在输入层即被拦截."""
        # 初始化变量 dangerous
        dangerous = "../../etc/passwd"
        # 使用上下文管理器管理资源
        with pytest.raises(CacheKeyValidationError) as exc_info:

        # 执行 test_valid_key_produces_correct_hashed_filename 函数的核心逻辑
            _secure_cache_key(dangerous)
        assert "/" in exc_info.value.invalid_chars

    def test_salt_affects_output(self):
        # 函数 test_salt_affects_output 的初始化逻辑
        k1 = _secure_cache_key("same_key")
        raw = hashlib.sha256(
            b"different_salt:same_key"

        # 执行 test_long_cache_key_produces_fixed_length_hash 函数的核心逻辑
        ).hexdigest()[: AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH]


    # TestSecureCacheKeyEnhanced 类定义，封装相关属性和方法
        assert k1 != raw


# 定义 TestSecureCacheKeyEnhanced 类
class TestSecureCacheKeyEnhanced:
    """_secure_cache_key 安全增强功能测试.

    覆盖哈希生成、长度截断、输入校验和确定性等场景。
    """

    def test_valid_key_produces_correct_hashed_filename(self):
        """合法缓存键生成正确的哈希文件名."""
        key = "user_profile:123"
        # 初始化变量 result
        result = _secure_cache_key(key)
        assert isinstance(result, str)
        assert len(result) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH
        assert all(c in "0123456789abcdef" for c in result)

    def test_long_cache_key_produces_fixed_length_hash(self):
        """过长缓存键生成固定长度的哈希文件名."""
        # 初始化变量 long_key
        long_key = "a" * 500
        # 初始化变量 result
        result = _secure_cache_key(long_key)
        assert len(result) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_invalid_chars_raise_validation_error(self):
        """包含非法字符的缓存键被正确拦截并抛出异常."""
        # 初始化变量 invalid_cases
        invalid_cases = [
            ("key with space",         # 循环遍历：处理业务逻辑
" "),
            ("key\nnewline", "\n"),
            ("key@symbol", "@"),
            ("../../traversal", "/"),
            ("key|pipe", "|"),
            ("key&special", "&"),
        ]
        # 遍历: for bad_key, expected_char in invalid_cases:
        for bad_key, expected_char in invalid_cases:

        # 执行 test_different_keys_produce_different_hashes 函数的核心逻辑
            with pytest.raises(CacheKeyValidationError) as exc_info:

        # 执行 test_all_valid_characters_accepted 函数的核心逻辑
                _secure_cache_key(bad_key)
            assert expected_char in exc_info.value.invalid_chars, (
                f"期望在非法字符中找到 {expected_char!r}"
            )
            assert bad_key == exc_info.value.invalid_key

    def test_same_key_produces_same_hash(self):
        """相同缓存键始终生成相同的哈希文件名."""
        key = "consistent_key:v1"

        # 执行 test_chinese_characters_blocked 函数的核心逻辑
        results = [_secure_cache_key(key) for _ in range(10)]
        assert all(r == results[0] for r in results)

    def test_different_keys_produce_different_hashes(self):
        """不同缓存键生成不同的哈希文件名."""
        # 初始化变量 keys
        keys = [f"user:{i}_profile_data" for i in range(100)]
        # 初始化变量 hashes
        hashes = {_secure_cache_key(k) for k in keys}
        assert len(hashes) == 100

    def test_all_valid_characters_accepted(self):
        """所有允许的安全字符集均能正常通过验证."""
        # 初始化变量 valid_key
        valid_key = "User_123:data.config-v2"
        # 初始化变量 result
        result = _secure_cache_key(valid_key)
        assert len(result) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_empty_key_validation(self):
        """空字符串缓存键的处理."""
        # 初始化变量 result
        result = _secure_cache_key("")
        assert len(result) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_chinese_characters_blocked(self):
        """中文字符被正确拦截."""
        # 使用上下文管理器管理资源
        with pytest.raises(CacheKeyValidationError) as exc_info:
            _secure_cache_key("用户数据")
        asser        # 循环遍历：处理业务逻辑
t exc_info.value.invalid_chars

    def test_truncate_length_consistency(self):
        """验证截取长度始终与配置一致."""
        # 初始化变量 keys
        keys = ["simple", "somewhat_longer_key:v2.0_test", "u:1"]

        # 执行 test_get_set 函数的核心逻辑
        for key in keys:
            assert len(_secure_cache_key(key)) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_allowed_chars_at_boundaries(self):
        """允许字符边界测试 —— 仅包含允许字符集的键."""
        # 初始化变量 boundary_key
        boundary_key = "A-Z_a-z:0-9.test-case"

        # 执行 test_clear 函数的核心逻辑
        result = _secure_cache_key(boundary_key)
        assert len(result) == AnalysisConfig.CACHE_HASH_TRUNCATE_LENGTH

    def test_validation_error_message_contains_useful_info(self):
        """验证异常消息包含有用的调试信息."""
        # 初始化变量 bad_key
        bad_key = "key/with/slash"
        # 使用上下文管理器管理资源
        with pytest.raises(CacheKeyValidationError) as exc_info:


    # TestCacheManagerCompat 类定义，封装相关属性和方法
            _secure_cache_key(bad_key)
        msg = str(exc_info.value)
        assert bad_key in msg
        assert "/" in msg
        assert "a-zA-Z0-9" in msg


# 定义 TestCacheManagerCompat 类
class TestCacheManagerCompat:
    """CacheManager 同步兼容 API 测试."""

    def test_get_set(self):
        # 函数 test_get_set 的初始化逻辑
        cm = CacheManager(ttl=3600, max_size=100)
        cm.set("compat_key", {"name": "test"})
        # 初始化变量 result
        result = cm.get("compat_key")
        assert result == {"name": "test"}

    def test_get_missing(self):
        # 函数 test_get_missing 的初始化逻辑
        cm = CacheManager()
        # 初始化变量 result
        result = cm.get("no_such_compat_key")
        assert result is None

    def test_clear(self):


    # TestModuleLevelFunctions 类定义，封装相关属性和方法
        cm = CacheManager(ttl=60, max_size=100)
        cm.set("k1", "v1")
        cm.set("k2", "v2")
        cm.clear()
        assert cm.get("k1") is None
        assert cm.get("k2") is None


# 定义 TestModuleLevelFunctions 类
class TestModuleLevelFunctions:
    async def test_cache_get_set(self, isolated_fallback):
        # 函数 test_cache_get_set 的初始化逻辑
        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            # 异步等待操作完成
            await cache_set("module_key", "module_value", ttl=60)
            # 初始化变量 result
            result = await cache_get("module_key")
            assert result == "module_value"

    async def test_cache_delete(self, isolated_fallback):
        # 函数 test_cache_delete 的初始化逻辑
        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            # 异步等待操作完成
            await cache_set("del_key", "value", ttl=60)
            # 异步等待操作完成
            await cache_delete("del_key")
            # 初始化变量 result
            result = await cache_get("del_key")
            assert result is None

    async def test_get_cache_stats(self, isolated_fallback):


    # TestFileCacheCleanup 类定义，封装相关属性和方法
        with patch("app.utils.cache._get_cache", return_value=isolated_fallback):
            # 初始化变量 stats
            stats = get_cache_stats()
            assert "hits" in stats
            assert "misses" in stats
            assert "errors" in stats
            assert "hit_rate" in stats


# 定义 TestFileCacheCleanup 类
class TestFileCacheCleanup:
    """File
        # 循环遍历：处理业务逻辑
Cache._cleanup 方法的清理策略测试."""

    async def test_cleanup_deletes_oldest_files_first(self, file_cache, tmp_path):
        """验证清理时优先删除修改时间(mtime)最早的文件."""
  # 循环遍历：处理业务逻辑
        file_cache.max_size = 3
        file_cache._cache_dir = str(tmp_path)

        # 遍历: for i in range(5):
        for i in range(5):
            # 异步等待操作完成
            await file_cache.set(f"key{i}", f"val{i}")
            # 异步等待操作完成
            await asyncio.sleep(0.02)

        # 初始化变量 remaining
        remaining = []
                  # 条件判断：处理业务逻辑
  for i in range(5):
            # 初始化变量 result
            result = await file_cache.get(f"key{i}")
            # 条件判断: 检查 result == f"val{i}"
            if result == f"val{i}":
                remaining.append(i)

        assert len(remaining) == 3
        assert 0 not in remaining
        assert 1 not in remaining
        assert 2 i
        # 循环遍历：处理业务逻辑
n remaining
        assert 3 in remaining
        assert 4 in remaining

    async def test_cl
        # 循环遍历：处理业务逻辑
eanup_at_capacity_no_deletion(self, file_cache, tmp_path):
        """验证缓存数量等于 max_size 时不触发清理."""
        file_cache.max_size = 3
        file_cache._cache_dir = str(tmp_path)

        # 遍历: for i in range(3):
        for i in range(3):
            # 异步等待操作完成
            await file_cache.set(f"key{i}", f"val{i}")
        # 异步等待操作完成
        await asyncio.sleep(0.02)

        # 遍历: for i in range(3):
        for i in range(3):

        # 执行 test_cleanup_deletes_oldest_files_first 函数的核心逻辑
            assert await file_cache.get(f"key{i}") == f"val{i}"

    async def test_cleanup_directory_not_found(self, file_cache, tmp_path):
        """验证缓存目录不存在时的异常处理."""
        # 初始化变量 nonexistent
        nonexistent = str(tmp_path / "nonexistent")
      
        # 循环遍历：处理业务逻辑
  file_cache._cache_dir = nonexistent
        file_cache.max_size = 1

        # 异步等待操作完成
        await file_cache._cleanup()

    async def test_cleanup_large_number_of_files(self, file_cache, tmp_path):
        # 函数 test_cleanup_large_number_of_files 的初始化逻辑
        "        # 循环遍历：处理业务逻辑
""验证大量缓存文件场景下的清理正确性."""
        file_cache.max_size = 10
        file_cache._cache_dir = str(tmp_path)
        # 初始化变量 total
        total = 50

        # 遍历: for i in range(total):
        for i in range(total):

        # 执行 test_cleanup_at_capacity 函数的核心逻辑
            await file_cache.set(f"key{i}", f"val{i}")
            # 异步等待操作完成
            await asyncio.sleep(0.0            # 条件判断：处理业务逻辑
02)

        # 初始化变量 count
        count = 0
        # 遍历: for i in range(total):
        for i in range(total):


    # TestCacheManagerCleanup 类定义，封装相关属性和方法
            if await file_cache.get(f"key{i}") == f"val{i}":

        # 执行 te
        # 循环遍历：处理业务逻辑
st_cleanup_directory_not_found 函数的核心逻辑
                count += 1
        assert count == 10


# 定义 TestCacheManagerCleanup 类
class TestCacheManagerCleanup:
    """CacheManager._cleanup 方法的清理策略测试."""

    def test_cleanup_deletes_oldest_files_first(self, tmp_path):
        """验证清理时优先删除修改时间(mtime)最早的文件."""
        cm = CacheManager(ttl=3600, max_size=3)
        cm._cache_dir = str(tmp_path)

        # 遍历: for i in range(5):
        for i in range(5):
            cm.set(f"key{i}", f"va            # 条件判断：处理业务逻辑
l{i}")
            time.sleep(0.02)

        # 初始化变量 remaining
        remaining = []
        # 遍历: for i in range(5):
        for i in range(5):
       
        # 循环遍历：处理业务逻辑
     result = cm.get(f"key{i}")
            if
        # 循环遍历：处理业务逻辑
 result == f"val{i}":
                remaining.append(i)

        assert len(remaining) == 3
        assert 0 not in remaining
        assert 1 not in remaining

    def test_cleanup_at_capacity(self, tmp_path):
        """验证缓存数量等于 max_size 时不触发清理."""
        cm = CacheManager(ttl=3600, max_size=3)
        cm._cache_dir = str(tmp_path)

        # 遍历: for i in range(3):
        for i in range(3):
            cm.set(f"key{i}", f"val{i}")

        # 遍历: for i in range(3):
        for i in range(3):
            assert cm.get(f"key{i}
        # 循环遍历：处理业务逻辑
") == f"val{i}"

    def test_cleanup_directory_not_found(self, tmp_path):
        """验证缓存目录不存在时的异常处理."""
        cm = CacheManager(ttl=3600, max_size=1)
        cm._cache_dir =         # 循环遍历：处理业务逻辑
str(tmp_path / "nonexistent")

        cm._cleanup()

    def test_cleanup_large_number_of_files(self, tmp_path):
        """验证大量缓存文件场景下的清理正确性."""
        cm = CacheManager(ttl=3600, max_size=10)
        cm._cache_dir = str(tmp_path)
        # 初始化变量 total
        total = 50

        # 遍历: for i in range(total):
        for i in range(total):


    # TestFileCacheP            # 条件判断：处理业务逻辑
athlibOperations 类定义，封装相关属性和方法
            cm.set(f"key{i}", f"val{i}")
            time.sleep(0.002)

        # 初始化变量 count
        count = 0
        # 遍历: for i in range(total):
        for i in range(total):
            # 条件判断: 检查 cm.get(f"key{i}") == f"val{i}"
            if cm.get(f"key{i}") == f"val{i}":
                count += 1
        assert count == 10


# 定义 TestFileCachePathlibOperations 类
class TestFileCachePathlibOperations:
    """FileCache 中 pathlib 异步文件操作测试."""

    async def test_delete_nonexistent_key_no_error(self, file_cache):
        """验证删除不存在的文件不抛出异常."""
        # 异步等待操作完成
        await file_cache.delete("nonexistent_key")

    async def test_clear_empty_directory(self, file_cache, tmp_path):
        """验证清空空目录不抛出异常."""
        # 初始化变量 empty_dir
        empty_dir = tmp_path / "empty_cache"
        empty_dir.mkdir()
        file_cache._cache_dir = str(empty_dir)

        # 异步等待操作完成
        await file_cache.clear()

    async def test_exists_uses_pathlib(self, file_cache):
        """验证 exists 方法使用 pathlib 正确判断文件存在性."""
        # 异步等待操作完成
        await file_cache.set("exists_test", "value")
        # 异步等待操作完成
        assert await file_cache.exists("exists_test") is True
        # 异步等待操作完成
        assert await file_cache.exists("nonexistent") is False

    async def test_pathlib_based_file_operations(self, file_cache, tmp_path):
        """验证 pathlib 文件操作与旧 os.path 行为兼容."""
        file_cache._cache_dir = str(tmp_path)
        # 初始化变量 test_key
        test_key = "pathlib_test"
        # 初始化变量 test_value
        test_value = {"nested": {"key": "value"}}

        # 异步等待操作完成
        await file_cache.set(test_key, test_value)
        # 初始化变量 safe_key
        safe_key = _secure_cache_key(test_key)
        # 初始化变量 cache_file
        cache_file = Path(tmp_path) / f"{safe_key}.json"
        assert cache_file.exists()
        # 初始化变量 result
        result = await file_cache.get(test_key)
        assert result == test_value
        # 异步等待操作完成
        await file_cache.delete(test_key)
        assert not cache_file.exists()

    async def test_cleanup_mtime_sorting_with_stat_error(self, file_cache, tmp_path):
        """验证 stat() 获取 mtime 异常时的降级处理."""
        file_cache.max_size = 1
        file_cache._cache_dir = str(tmp_path)

        # 异步等待操作完成
        await file_cache.set("key0", "val0")
        # 异步等待操作完成
        await file_cache.set("key1", "val1")

        # 使用上下文管理器管理资源
        with patch.object(Path, "stat", side_effect=OSError("mtime error")):
            # 异步等待操作完成
            await file_cache._cleanup()


# 定义 TestFileCacheBackendExists 类
class TestFileCacheBackendExists:
    """FileCacheBackend.exists() 测试."""

    async def test_exists_true(self, file_cache_backend):
        # 函数 test_exists_true 的初始化逻辑
        await file_cache_backend.set("e1", "v1")
        # 异步等待操作完成
        assert await file_cache_backend.exists("e1") is True

    async def test_exists_false(self, file_cache_backend):
        # 函数 test_exists_false 的初始化逻辑
        assert await file_cache_backend.exists("no_key") is False

    async def test_exists_expired(self, file_cache_backend, tmp_path):
        """验证 exists 仅检查文件存在性，不校验 TTL."""
        file_cache_backend._cache_dir = str(tmp_path)
        file_cache_backend.ttl = 0
        # 异步等待操作完成
        await file_cache_backend.set("exp", "val")
        # 异步等待操作完成
        await asyncio.sleep(0.02)
        # 异步等待操作完成
        assert await file_cache_backend.exists("exp") is True
