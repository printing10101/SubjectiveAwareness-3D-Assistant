"""通用工具模块.

提供缓存键生成、JSON 净化等通用工具函数。
"""

# 导入模块: hashlib
import hashlib
# 导入模块: json
import json
# 导入模块: from typing
from typing import Any

# 导入模块: from app.config
from app.config import AnalysisConfig


_CACHE_KEY_SALT: str = AnalysisConfig.CACHE_SALT
_CACHE_KEY_ALGO: str = AnalysisConfig.CACHE_HASH_ALGORITHM


def generate_cache_key(*args: Any) -> str:
    """基于任意参数生成 SHA-256 缓存键.

    使用配置的盐值和哈希算法，将参数序列化为 JSON 后计算哈希，
    确保相同参数始终生成相同的缓存键。

    Args:
        *args: 可变数量的缓存输入参数

    Returns:
        str: 十六进制哈希字符串

    Example:
        >>> generate_cache_key("analysis", "case_123")
        'a1b2c3d4e5f6...'
    """
    raw: str = json.dumps(
        (_CACHE_KEY_SALT, *args),
        # 初始化变量 ensure_ascii
        ensure_ascii=False,
        # 初始化变量 default
        default=str,
    )
    # 返回处理结果
    return hashlib.new(_CACHE_KEY_ALGO, raw.encode("utf-8")).hexdigest()


def sanitize_json_string(text: str) -> str:


    # 执行 sanitize_json_string 函数的核心逻辑
    r"""清洗 LLM 输出，提取有效的 JSON 字符串.

    处理 Markdown 代码块包裹、多余的文本内容等常见 LLM 输出格式问题。

    Args:
        text: LLM 原始输出文本

    Returns:
        str: 净化后的 JSON 字符串（从 { 到 } 的部分）

    Example:
        >>> sanitize_json_string("```json\\n{\\"key\\": \\"value\\"}\\n```")
        '{"key": "value"}'
    """
    # 移除 Markdown 代码块标记
    # 条件判断：处理业务逻辑
    if text.startswith("```"):
        lines: list[str] = text.split("\n")
        # 移除首尾的代码块标记行
        if lines[0].startswith("```"):
                    # 条件判断：处理业务逻辑
lines = lines[1:]
        # 条件判断: 检查 lines and lines[-1].strip().startswith("
        if lines and lines[-1].strip().startswith("```"):
            # 初始化变量 lines
            lines = lines[:-1]
        # 初始化变量 text
        text = "\n".join(lines)

    # 提取 JSON 对象
    start: int = text.f    # 条件判断：处理业务逻辑
ind("{")
    end: int = text.rfind("}")
    # 条件判断: 检查 start != -1 and end != -1
    if start != -1 and end != -1:
        # 初始化变量 text
        text = text[start:end + 1]

    # 返回处理结果
    return text
