"""JSON 工具模块.

提供鲁棒的 JSON 解析功能，支持自动修复常见格式错误，
包括 Markdown 代码块、尾部逗号、单引号、未引用键名等。
"""

import json
import re
from datetime import UTC, datetime
from typing import Any

from loguru import logger


def _strip_markdown_code_blocks(text: str) -> str:
    """移除 Markdown 代码块包裹标记.

    支持 `` ```json ... ``` ``、`` ``` ... ``` `` 以及多行变体。

    Args:
        text: 可能包含 Markdown 代码块的原始文本

    Returns:
        str: 剥离代码块标记后的纯文本
    """
    # 匹配 ```json\\n...\\n``` 或 ```\\n...\\n```
    pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _repair_trailing_commas(json_str: str) -> str:
    """修复 JSON 中的尾部逗号.

    处理对象 {...,} 和数组 [...,] 中最后的冗余逗号。

    Args:
        json_str: 待修复的 JSON 字符串

    Returns:
        str: 移除尾部逗号后的 JSON 字符串
    """
    # 移除对象/数组中最后一个元素后的逗号
    return re.sub(r",\s*([}\]])", r"\1", json_str)


def _repair_single_quotes(json_str: str) -> str:
    """将 JSON 中的单引号替换为双引号.

    注意：需谨慎处理字符串内部可能包含的引号，采用逐字符状态机方式处理。

    Args:
        json_str: 待修复的 JSON 字符串

    Returns:
        str: 单引号替换为双引号后的 JSON 字符串
    """
    result: list[str] = []
    in_double_quote = False
    in_single_quote = False
    escaped = False

    for ch in json_str:
        if escaped:
            result.append(ch)
            escaped = False
            continue

        if ch == "\\":
            result.append(ch)
            escaped = True
            continue

        if ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            result.append(ch)
        elif ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            result.append('"')
        else:
            result.append(ch)

    return "".join(result)


def _repair_unquoted_keys(json_str: str) -> str:
    """修复 JSON 中缺少引号的键名.

    匹配形如 `` {key: value} `` 或 `` {key : value} `` 的模式，
    为键名添加双引号。

    Args:
        json_str: 待修复的 JSON 字符串

    Returns:
        str: 键名添加引号后的 JSON 字符串
    """
    # 使用捕获组方法替代后行断言，避免 Python 3.11 之前版本中 look-behind
    # 必须为固定宽度模式的问题
    # 匹配模式：{,或换行 后跟零个或多个空白，然后是无引号键名，然后是空白和冒号
    pattern = r'([\{,]\s*)([a-zA-Z_\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]*)\s*:'
    return re.sub(pattern, r'\1"\2":', json_str)


def _repair_unescaped_special_chars(json_str: str) -> str:
    """修复字符串值中未转义的特殊字符.

    处理换行符、制表符等在 JSON 字符串中必须转义的字符。

    Args:
        json_str: 待修复的 JSON 字符串

    Returns:
        str: 转义特殊字符后的 JSON 字符串
    """
    # 在字符串值内部，将未转义的 \\n、\\t、\\r 替换为正确的转义形式
    result: list[str] = []
    in_string = False
    escaped = False

    for ch in json_str:
        if escaped:
            result.append(ch)
            escaped = False
            continue

        if ch == "\\":
            result.append(ch)
            escaped = True
            continue

        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue

        if in_string:
            if ch == "\n":
                result.append("\\n")
            elif ch == "\t":
                result.append("\\t")
            elif ch == "\r":
                result.append("\\r")
            else:
                result.append(ch)
        else:
            result.append(ch)

    return "".join(result)


def _build_default_dimension() -> dict[str, Any]:
    """构建默认维度分析结果.

    Returns:
        dict: 包含默认评分和理由的维度结果
    """
    from app.config import AnalysisConfig
    return {
        "score": AnalysisConfig.DEFAULT_DIMENSION_SCORE,
        "reasoning": AnalysisConfig.DEFAULT_REASONING,
    }


def _build_default_analysis_result() -> dict[str, Any]:
    """构建预设的默认分析结果，用于 JSON 解析失败时的降级返回.

    Returns:
        dict: 包含完整三维度默认值的结果字典
    """
    default_dim = _build_default_dimension()
    return {
        "ground_truth_analysis": {
            "dimension1": default_dim,
            "dimension2": default_dim,
            "dimension3": default_dim,
        },
        "subjective_knowledge": "未知",
        "sentence": "待定",
        "fallback": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def robust_json_parse(
    text: str,
    default: dict[str, Any] | None = None,
) -> dict[str, Any]:
    r"""鲁棒的 JSON 解析函数，具备自动修复与错误降级能力.

    依次尝试以下策略解析 JSON：
    1. 直接解析原始文本
    2. 移除 Markdown 代码块后解析
    3. 提取文本中第一个 { 到最后一个 } 之间的内容后解析
    4. 对提取的内容依次应用修复策略（尾部逗号、单引号、未引用键名、
       特殊字符转义）后尝试解析
    5. 所有策略均失败时，返回预设的默认数据结构

    Args:
        text: LLM 返回的原始文本，可能包含 Markdown 包裹或语法错误
        default: 解析失败时返回的默认字典，若为 None 则使用内置默认值

    Returns:
        dict: 解析后的 JSON 字典，或默认降级数据结构

    Example:
        >>> robust_json_parse('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}
        >>> robust_json_parse("{'key': 'value',}")
        {'key': 'value'}
        >>> robust_json_parse("not json at all")
        {'ground_truth_analysis': {...}, 'fallback': True, ...}
    """
    if default is None:
        default = _build_default_analysis_result()

    # 策略1: 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 策略2: 移除 Markdown 代码块后解析
    stripped = _strip_markdown_code_blocks(text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 策略3: 提取 JSON 对象（第一个 { 到最后一个 }）
    start = text.find("{")
    end = text.rfind("}")
    extracted = (
        text[start:end + 1]
        if start != -1 and end != -1 and end > start
        else stripped
    )

    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        pass

    # 策略4: 依次应用修复策略
    repair_candidates = [extracted]

    # 修复尾部逗号
    repaired = _repair_trailing_commas(extracted)
    repair_candidates.append(repaired)

    # 修复单引号
    repaired = _repair_single_quotes(extracted)
    repair_candidates.append(repaired)

    # 修复未引用键名
    repaired = _repair_unquoted_keys(extracted)
    repair_candidates.append(repaired)

    # 组合修复：尾部逗号 + 单引号 + 未引用键名
    combined = extracted
    combined = _repair_trailing_commas(combined)
    combined = _repair_single_quotes(combined)
    combined = _repair_unquoted_keys(combined)
    repair_candidates.append(combined)

    # 完整组合修复：包含特殊字符转义
    combined_full = _repair_unescaped_special_chars(combined)
    repair_candidates.append(combined_full)

    for candidate in repair_candidates:
        if candidate == extracted:
            continue  # 跳过已尝试的原始提取
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # 策略5: 所有策略均失败，返回默认值
    logger.warning("JSON 解析失败，使用默认降级结果")
    return default
