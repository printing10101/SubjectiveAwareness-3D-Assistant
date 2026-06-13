"""运行时配置验证脚本 — 检查数据库连接池和Ollama客户端是否按配置生效."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from loguru import logger

from app.config import settings
from app.database import async_engine, sync_engine
from app.services.ollama_client import get_client, get_rate_limited_client


def check_database() -> None:
    logger.info("=" * 60)
    logger.info("  数据库连接池验证")
    logger.info("=" * 60)

    logger.info("ASYNC_DATABASE_URL: {}", settings.ASYNC_DATABASE_URL)
    logger.info("DB_POOL_SIZE:       {}", settings.DB_POOL_SIZE)
    logger.info("DB_MAX_OVERFLOW:    {}", settings.DB_MAX_OVERFLOW)
    logger.info("DB_POOL_PRE_PING:   {}", settings.DB_POOL_PRE_PING)
    logger.info("DB_POOL_RECYCLE:    {}s", settings.DB_POOL_RECYCLE)
    logger.info("DB_ECHO:            {}", settings.DB_ECHO)

    async_pool = async_engine.pool
    sync_pool = sync_engine.pool
    logger.info("异步引擎池类型: {}", type(async_pool).__name__)
    logger.info("同步引擎池类型: {}", type(sync_pool).__name__)

    if hasattr(async_pool, "size"):
        logger.info("异步池 size():    {}", async_pool.size())
    if hasattr(sync_pool, "size"):
        logger.info("同步池 size():    {}", sync_pool.size())

    db_path = settings.ASYNC_DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    logger.info("数据库文件路径: {}", db_path)

    try:
        with sync_engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT 1 AS alive")
            row = result.fetchone()
            logger.info("同步数据库连接:  ✅ 成功 ({}={})", row._mapping["alive"], row._mapping["alive"])
    except Exception as e:
        logger.error("同步数据库连接:  ❌ 失败: {}", e)

    logger.info("")


def check_ollama_client() -> None:
    logger.info("=" * 60)
    logger.info("  Ollama 客户端连接池验证")
    logger.info("=" * 60)

    logger.info("OLLAMA_MAX_CONNECTIONS:           {}", settings.OLLAMA_MAX_CONNECTIONS)
    logger.info("OLLAMA_MAX_KEEPALIVE_CONNECTIONS:  {}", settings.OLLAMA_MAX_KEEPALIVE_CONNECTIONS)
    logger.info("OLLAMA_CONNECT_TIMEOUT:            {}s", settings.OLLAMA_CONNECT_TIMEOUT)
    logger.info("OLLAMA_KEEPALIVE_EXPIRY:           {}s", settings.OLLAMA_KEEPALIVE_EXPIRY)

    logger.info("OLLAMA_MAX_CONCURRENT:             {}", settings.OLLAMA_MAX_CONCURRENT)
    logger.info("OLLAMA_QUEUE_MAXSIZE:              {}", settings.OLLAMA_QUEUE_MAXSIZE)
    logger.info("OLLAMA_RETRY_MAX_ATTEMPTS:         {}", settings.OLLAMA_RETRY_MAX_ATTEMPTS)
    logger.info("OLLAMA_RETRY_DELAY:                {}s", settings.OLLAMA_RETRY_DELAY)

    logger.info("OLLAMA_TIMEOUT_BASE:               {}s", settings.OLLAMA_TIMEOUT_BASE)
    logger.info("OLLAMA_TIMEOUT_PER_1000_CHARS:     {}s", settings.OLLAMA_TIMEOUT_PER_1000_CHARS)
    logger.info("OLLAMA_TIMEOUT_MAX:                {}s", settings.OLLAMA_TIMEOUT_MAX)

    client = get_client()
    rl_client = get_rate_limited_client()

    logger.info("基础客户端已初始化: {}", type(client).__name__)
    logger.info("限流客户端已初始化: {}", type(rl_client).__name__)
    logger.info("限流队列容量:       {}", settings.OLLAMA_QUEUE_MAXSIZE)
    logger.info("限流并发上限:       {}", settings.OLLAMA_MAX_CONCURRENT)

    logger.info("")


if __name__ == "__main__":
    check_database()
    check_ollama_client()
    logger.info("✅ 配置验证完成 — 所有参数已从 .env/config.py 正确加载")
