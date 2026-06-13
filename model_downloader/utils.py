"""模型下载与处理工具 - 工具函数模块"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    verbose: bool = False,
) -> None:
    """配置日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径（可选）
        verbose: 是否输出详细日志
    """
    # 移除默认 handler
    logger.remove()

    # 设置日志级别
    if verbose:
        level = "DEBUG"

    # 控制台输出
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        level=level,
        format=log_format,
        colorize=True,
    )

    # 文件输出（如果指定）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_file),
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            rotation="10 MB",
            retention="7 days",
        )

    logger.debug(f"日志系统已初始化，级别: {level}")


def format_bytes(num_bytes: int) -> str:
    """格式化字节数为人类可读字符串

    Args:
        num_bytes: 字节数

    Returns:
        格式化后的字符串，如 "1.23 MB"
    """
    if num_bytes < 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0

    while num_bytes >= 1024 and unit_index < len(units) - 1:
        num_bytes /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{num_bytes} B"
    return f"{num_bytes:.2f} {units[unit_index]}"


def ensure_directory(path: Path) -> Path:
    """确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        创建或已存在的目录路径
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def check_command_exists(command: str) -> bool:
    """检查命令行工具是否存在

    Args:
        command: 命令名称

    Returns:
        命令是否存在
    """
    import shutil

    return shutil.which(command) is not None
