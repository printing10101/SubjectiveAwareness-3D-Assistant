"""日志配置模块.

提供结构化日志配置和请求上下文追踪功能。
使用loguru库实现多处理器日志系统，支持控制台格式化文本输出和文件JSON结构化输出，
并基于contextvars实现请求级的request_id上下文追踪。
"""

import contextvars
import os
from datetime import UTC, datetime
from typing import Any

from loguru import logger


# 请求ID上下文变量，用于在整个请求生命周期中追踪当前请求的唯一标识
# 默认值为空字符串，表示不在HTTP请求上下文中
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class RequestIdFilter:
    """日志过滤器，自动将当前线程/协程的request_id注入日志记录.

    通过contextvars获取当前请求的request_id，
    并写入日志记录的extra字段，供格式化器和JSON序列化使用。
    """

    def __call__(self, record: dict[str, Any]) -> bool:
        """将当前请求的 request_id 注入日志记录."""
        record["extra"]["request_id"] = request_id_var.get()
        return True


def console_formatter(record: dict[str, Any]) -> str:
    """控制台日志格式化函数.

    根据日志记录动态生成格式字符串。
    当存在request_id时自动追加到日志行末尾，否则省略。

    Args:
        record: 日志记录字典

    Returns:
        包含loguru格式占位符的格式字符串
    """
    request_id = record["extra"].get("request_id", "")
    request_id_part = f" [{request_id}]" if request_id else ""
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        f"<level>{{message}}</level>{request_id_part}\n"
    )


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    json_log_file: str = "app_{time:YYYY-MM-DD}.json",
    json_retention: str = "30 days",
    json_rotation: str = "00:00",
) -> None:
    """配置loguru多处理器日志系统.

    初始化日志系统，配置两个处理器（sink）：
    1. 控制台输出：使用带颜色的格式化文本，包含时间戳、日志级别、模块名、request_id和消息内容
    2. 文件输出：JSON结构化格式（JSONL），每条记录一行JSON，便于日志聚合和分析工具处理

    日志轮转策略：按天生成新日志文件（每天00:00轮转），保留最近30天的日志文件。

    Args:
        log_level: 日志级别，可选 DEBUG/INFO/WARNING/ERROR，默认 INFO
        log_dir: 日志文件存储目录，相对于项目根目录或绝对路径
        json_log_file: JSON日志文件名模板，支持loguru的{time}变量
        json_retention: JSON日志保留策略，默认30天
        json_rotation: JSON日志轮转策略，默认每天00:00轮转

    Example:
        >>> setup_logging(log_level="INFO", log_dir="logs")
        日志系统初始化完成

        >>> setup_logging(log_level="DEBUG", log_dir="/var/log/myapp")
        日志系统初始化完成（使用绝对路径）
    """
    logger.remove()

    os.makedirs(log_dir, exist_ok=True)

    request_id_filter = RequestIdFilter()

    logger.add(
        sink=lambda msg: print(msg, end=""),
        format=console_formatter,  # type: ignore[arg-type]
        level=log_level,
        colorize=True,
        filter=request_id_filter,  # type: ignore[arg-type]
    )

    logger.add(
        sink=os.path.join(log_dir, json_log_file),
        format="{message}",
        level=log_level,
        serialize=True,
        rotation=json_rotation,
        retention=json_retention,
        compression=None,
        filter=request_id_filter,  # type: ignore[arg-type]
    )

    logger.info(
        "日志系统初始化完成 | 日志级别: {} | JSON日志目录: {}",
        log_level,
        os.path.abspath(log_dir),
    )


def get_request_id() -> str:
    """获取当前请求的request_id.

    在HTTP请求处理过程中调用，返回当前请求的唯一标识符。
    如果在非HTTP请求上下文中调用，返回空字符串。

    Returns:
        当前请求的request_id，如果不在请求上下文中则返回空字符串

    Example:
        >>> get_request_id()
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        >>> get_request_id()
        ''  # 非请求上下文
    """
    return request_id_var.get()


def format_timestamp(dt: datetime | None = None) -> str:
    """生成ISO 8601格式的时间戳字符串.

    Args:
        dt: 可选的datetime对象，默认为当前UTC时间

    Returns:
        ISO 8601格式的时间戳字符串，包含UTC时区信息

    Example:
        >>> format_timestamp()
        '2024-01-15T10:30:45.123456+00:00'
    """
    if dt is None:
        dt = datetime.now(UTC)
    return dt.isoformat()
