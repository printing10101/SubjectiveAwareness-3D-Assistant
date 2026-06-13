"""启动主应用服务器.

在配置的端口上启动 FastAPI 案件分析 API 服务。
支持环境变量配置、日志级别设置、超时控制及重试机制。
"""

import os
import sys
from pathlib import Path

import uvicorn
from loguru import logger

from app.config import settings


def validate_environment() -> None:
    """验证关键环境变量配置."""
    # 检查 Ollama 服务连接
    ollama_url = settings.OLLAMA_BASE_URL
    logger.info(f"Ollama 服务地址: {ollama_url}")

    # 检查数据库连接
    db_url = settings.DATABASE_URL
    logger.info(f"数据库连接: {db_url.split('@')[-1] if '@' in db_url else 'SQLite'}")

    # 检查 Redis 连接（如果使用）
    if settings.CACHE_BACKEND == "redis":
        redis_url = settings.REDIS_URL
        logger.info(f"Redis 连接: {redis_url.split('@')[-1] if '@' in redis_url else 'localhost'}")

    # 检查 JWT 密钥
    if settings.APP_ENV == "production" and not settings.JWT_SECRET_KEY:
        logger.error("生产环境必须配置 JWT_SECRET_KEY")
        sys.exit(1)

    # 检查加密密钥
    if settings.APP_ENV == "production" and not settings.ENCRYPTION_KEY:
        logger.error("生产环境必须配置 ENCRYPTION_KEY")
        sys.exit(1)


def configure_logging() -> None:
    """配置日志系统."""
    log_level = settings.LOG_LEVEL
    log_dir = Path(settings.LOG_DIR)

    # 确保日志目录存在
    log_dir.mkdir(parents=True, exist_ok=True)

    # 配置 loguru
    logger.remove()  # 移除默认处理器
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # 每日轮转
        retention="7 days",  # 保留7天
        compression="zip",  # 压缩旧日志
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger.info(f"日志系统配置完成: level={log_level}, dir={log_dir}")


def start_server() -> None:
    """启动应用服务器."""
    host: str = settings.SERVER_HOST
    port: int = settings.SERVER_PORT
    reload: bool = settings.DEBUG
    workers: int = int(os.getenv("UVICORN_WORKERS", "1"))
    timeout_keep_alive: int = int(os.getenv("UVICORN_TIMEOUT_KEEP_ALIVE", "5"))
    timeout_graceful_shutdown: int = int(os.getenv("UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN", "30"))

    logger.info("=" * 60)
    logger.info(f"启动主应用服务: {host}:{port}")
    logger.info(f"环境: {settings.APP_ENV}")
    logger.info(f"DEBUG: {reload}")
    logger.info(f"Workers: {workers}")
    logger.info(f"Keep-Alive Timeout: {timeout_keep_alive}s")
    logger.info(f"Graceful Shutdown Timeout: {timeout_graceful_shutdown}s")
    logger.info("=" * 60)

    # 生产环境配置
    uvicorn_config = {
        "host": host,
        "port": port,
        "reload": reload,
        "workers": workers if not reload else 1,  # reload模式下不支持多worker
        "timeout_keep_alive": timeout_keep_alive,
        "timeout_graceful_shutdown": timeout_graceful_shutdown,
        "log_level": settings.LOG_LEVEL.lower(),
        "access_log": True,
    }

    try:
        uvicorn.run("app.main:app", **uvicorn_config)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在优雅关闭服务...")
    except Exception as e:
        logger.exception(f"服务启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 配置日志
    configure_logging()

    # 验证环境
    validate_environment()

    # 启动服务
    start_server()

