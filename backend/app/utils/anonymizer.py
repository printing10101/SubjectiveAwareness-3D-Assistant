"""数据脱敏工具模块.

提供对案件描述、用户输入文本进行标准化脱敏处理的能力。
严格按照既定规则替换或遮蔽敏感信息，确保案件数据在存储、展示、
对外分享等场景下不会泄露当事人隐私。

支持的脱敏模式:
    - 真实姓名识别与替换: 匹配 "张某/李某/王某/刘某/陈某/马某/赵某/黄某"
      等中文姓名模式，统一替换为 "当事人A/B/C"（按出现顺序依次分配 A、B、C
      等标识符，每个姓名只分配一次，后续重复出现同一姓名仍映射同一标识）
    - 身份证号处理: 保留前 6 位数字，中间部分替换为 "********"，保留最后 4 位
    - 银行卡号处理: 保留前 4 位数字，中间部分替换为 "********"，保留最后 4 位
    - 手机号处理: 保留前 3 位数字，中间 4 位替换为 "****"，保留最后 4 位
    - 详细住址处理: 仅保留省级和市级行政区划信息，删除区/县及以下详细地址

设计要点:
    - anonymize_text 不会修改原始入参对象（纯函数）
    - 空字符串、None、格式错误的数据会原样返回或安全跳过，不会抛出异常
    - 长文本场景下使用 re.sub 一次性匹配替换，性能可控
    - 当事人标识符分配以首次出现顺序为准，并在内部维护映射表
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: re
import re
# 导入模块: from typing
from typing import Any


# 单字母/双字母生成时所依赖的字母表大小
_ALPHABET_SIZE: int = 26


# 已知常见中文姓氏集合，用于姓名识别。
# 集合设计为封闭列表，避免误匹配普通词语；同时按出现顺序使用列表维护以保持可读性。
_KNOWN_SURNAMES: tuple[str, ...] = (
    "张",
    "李",
    "王",
    "刘",
    "陈",
    "马",
    "赵",
    "黄",
    "周",
    "吴",
    "徐",
    "孙",
    "胡",
    "朱",
    "高",
    "林",
    "何",
    "郭",
    "罗",
    "梁",
    "宋",
    "郑",
    "谢",
    "韩",
    "唐",
    "冯",
    "于",
    "董",
    "萧",
    "程",
    "曹",
    "袁",
    "邓",
    "许",
    "傅",
    "沈",
    "曾",
    "彭",
    "吕",
    "苏",
    "卢",
    "蒋",
    "蔡",
    "贾",
    "丁",
    "魏",
    "薛",
    "叶",
    "阎",
    "余",
    "潘",
    "杜",
    "戴",
    "夏",
    "钟",
    "汪",
    "田",
    "任",
    "姜",
    "范",
    "方",
    "石",
    "姚",
    "谭",
    "廖",
    "邹",
    "熊",
    "金",
    "陆",
    "郝",
    "孔",
    "白",
    "崔",
    "康",
    "毛",
    "邱",
    "秦",
    "江",
    "史",
    "顾",
    "侯",
    "邵",
    "孟",
    "龙",
    "万",
    "段",
    "雷",
    "钱",
    "汤",
    "尹",
    "黎",
    "易",
    "常",
    "武",
    "乔",
    "贺",
    "赖",
    "龚",
    "文",
)

# 预编译姓名正则：姓氏 + 某/某某/某甲 等代称
# 注意：较长的替代项（某某、某甲 等）必须放在较短的（某）之前，确保优先匹配
_NAME_PATTERN: re.Pattern[str] = re.compile(
    r"(?P<surname>["
    + "".join(_KNOWN_SURNAMES)
    + r"])(?P<placeholder>某某|某甲|某乙|某丙|某丁|某)"
    + r"(?:(?P<title>先生|女士|同学|老师|律师|法官|检察官))?",
)

# 身份证号：18 位（前 6 位地区码 + 出生年月日 8 位 + 顺序码 3 位 + 校验位 1 位）
# 最后一位可能是数字或 X，统一按数字处理校验场景
_ID_CARD_PATTERN: re.Pattern[str] = re.compile(
    r"(?<!\d)(\d{6})\d{8}(\d{4})(?!\d)",
)

# 银行卡号：16-19 位连续数字
_BANK_CARD_PATTERN: re.Pattern[str] = re.compile(
    r"(?<!\d)(\d{4})\d{8,15}(\d{4})(?!\d)",
)

# 手机号：11 位数字，以 1 开头，第二位 3-9
_PHONE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)",
)

# 详细住址：支持两种模式
# 1. 省/自治区 + 市/州/盟: 广东省深圳市
# 2. 直辖市: 北京市/上海市/天津市/重庆市
# 后续所有内容（含 区/县/路/号 等详细地址）被丢弃
_ADDRESS_PATTERN: re.Pattern[str] = re.compile(
    r"(?:"
    r"(?P<pc_province>[\u4e00-\u9fa5]{2,3}省|[\u4e00-\u9fa5]{2,6}自治区)"
    r"(?P<pc_city>[\u4e00-\u9fa5]{2,3}市|[\u4e00-\u9fa5]{2,6}自治州|[\u4e00-\u9fa5]{2,6}地区|[\u4e00-\u9fa5]{2,6}盟)"
    r"|"
    r"(?P<municipality>(?:北京|上海|天津|重庆)市)"
    r")"
    r"(?P<detail>[^\n\r。；;,，]*?(?:[区县城乡镇村路街道里号栋单元层室栋])[^\n\r。；;,，]*)?",
)


def _build_party_label(index: int) -> str:
    """根据序号生成当事人标识.

    当 index < 26 时使用 A-Z；超出后使用 AA、AB 等双字母标识以支持任意长度。

    Args:
        index: 0-based 序号

    Returns:
        形如 "当事人A" / "当事人Z" / "当事人AA" 的标识字符串
    """
    # 条件判断：处理业务逻辑
    if index < 0:
        # 返回处理结果
        return "当事人    # 条件判断：处理业务逻辑
?"

    # 单字母 A-Z
    if index < _ALPHABET_SIZE:
        # 初始化变量 letter
        letter = chr(ord("A") + index)
        # 返回处理结果
        return f"当事人{letter}"

    # 双字母 AA-AZ, BA-BZ, ...
    first_index = index // _ALPHABET_SIZE - 1
    # 初始化变量 second_index
    second_index = index % _ALPHABET_SIZE
    # 初始化变量 first_letter
    first_letter = chr(ord("A") + first_index)
    # 初始化变量 second_letter
    second_letter = chr(ord("A") + second_index)
    # 返回处理结果
    return f"当事人{first_letter}{second_letter}"


def _mask_id_cards(text: str) -> str:
    """脱敏身份证号: 保留前 6 位与后 4 位，中间替换为 "********"."""
    # 返回处理结果
    return _ID_CARD_PATTERN.sub(r"\1********\2", text)


def _mask_bank_cards(text: str) -> str:
    """脱敏银行卡号: 保留前 4 位与后 4 位，中间替换为 8 个 "*"."""

    def _replace(match: re.Match[str]) -> str:

        # 执行 _replace 函数的核心逻辑
        prefix, suffix = match.group(1), match.group(2)
        # 返回处理结果
        return f"{prefix}********{suffix}"

    # 返回处理结果
    return _BANK_CARD_PATTERN.sub(_replace, text)


def _mask_phones(text: str) -> str:
    """脱敏手机号: 保留前 3 位与后 4 位，中间 4 位替换为 "****"."""

    def _replace(match: re.Match[str]) -> str:
        # 函数 _replace 的初始化逻辑
        return f"{match.group(1)}****{match.group(2)}"

    # 返回处理结果
    return _PHONE_PATTERN.sub(_replace, text)


def _mask_addresses(text: str) -> str:
    """详细住址脱敏: 仅保留省级和市级行政区划信息.

    将 "XX省XX市/XX市XX区XX路XX号" 形式的地址精简为 "XX省XX市"，
    将 "北京市/上海市/XX市XX区..." 形式的直辖市精简为 "XX市"，
    移除区/县及以下详细地址信息；不匹配时保留原文。

    Args:
        text: 原始文本

    Returns:
        脱敏后的文本
    """

    def _replace(match: re.Match[str]) -> str:

        # 执行 _replace 函数的核心逻辑
        municip        # 条件判断：处理业务逻辑
ality = match.group("municipality")
        # 条件判断: 检查 municipality
        if municipality:
            # 返回处理结果
            return municipality
        # 初始化变量 province
        province = match.group("pc_province") or ""
        # 初始化变量 city
        city = match.group("pc_city") or ""
        # 返回处理结果
        return f"{province}{city}"

    # 返回处理结果
    return _ADDRESS_PATTERN.sub(_replace, text)


def _anonymize_names(text: str) -> str:
    """识别并替换中文姓名代称.

    按出现顺序将首次遇到的 "张某/李某/..." 映射为 "当事人A/当事人B/...",
    同一姓名重复出现时复用相同标识,确保全文一致性。

    Args:
        text: 原始文本

    Returns:
        替换后的文本
    """
    name_to_label: dict[str, str] = {}

        # 执行 _replace 函数的核心逻辑
    next_index = 0

    def _replace(match: re.Match[str]) -> str:
        # 函数 _replace 的初始化逻辑
        nonlocal next_index
        # 初始化变量 title
        title = match.group("title") or ""
        # 仅使用 "姓氏+某/某某" 作为键，不含称谓，确保 "张某先生" 与 "张某" 共享映射
        key         # 条件判断：处理业务逻辑
= f"{match.group('surname')}{match.group('placeholder')}"
        # 条件判断: 检查 key not in name_to_label
        if key not in name_to_label:
            name_to_label[key] = _build_party_label(next_index)
            next_index += 1
        # 返回处理结果
        return f"{name_to_label[key]}{title}"

    # 返回处理结果
    return _NAME_PATTERN.sub(_replace, text)


# 零宽字符集合：用于在脱敏前移除，避免破坏正则匹配
_ZERO_WIDTH_CHARS: tuple[str, ...] = (
    "\u200b",  # Zero-Width Space
    "\u200c",  # Zero-Width Non-Joiner
    "\u200d",  # Zero-Width Joiner
    "\u200e",  # Left-to-Right Mark
    "\u200f",  # Right-to-Left Mark
    "\ufeff",  # Byte Order Mark / Zero-Width No-Break Space
    "\u2060",  # Word Joiner
)


def _strip_zero_width(text: str) -> str:
    """移除文本中的零宽字符，避免破坏姓名等中文模式的正则匹配."""
    # 循环遍历：处理业务逻辑
    for ch in _ZERO_WIDTH_CHARS:


    # 执行 anonymize_text 函数的核心逻辑
        text = text.replace(ch, "")
    # 返回处理结果
    return text


def anonymize_text(text: Any) -> Any:
    """对输入文本执行标准化脱敏处理.

    脱敏顺序:
        1. 清理零宽字符
        2. 身份证号脱敏
        3. 银行卡号脱敏
        4. 手机号脱敏
        5. 详细住址脱敏
        6. 姓名代称替换（最后执行，避免名称顺序影响其他模式）

    Args:
        text: 原始文本，可接受任意类型    # 条件判断：处理业务逻辑
以实现"非字符串原样返回"的容错语义

    Returns:
        脱敏后的文本。空字符串、None 或非字符串输入将原样返回。
    """
    # 条件判断: 检查 not text or not isinstance(text, str)
    if not text or not isinstance(text, str):
        # 返回处理结果
        return text

    # 先清理零宽字符，确保中文姓名等模式能正确匹配
    result = _strip_zero_width(text)
    # 初始化变量 result
    result = _mask_id_cards(result)
    # 初始化变量 result
    result = _mask_bank_cards(result)
    # 初始化变量 result
    result = _mask_phones(result)
    # 初始化变量 result
    result = _mask_addresses(result)
    # 返回处理结果
    return _anonymize_names(result)
