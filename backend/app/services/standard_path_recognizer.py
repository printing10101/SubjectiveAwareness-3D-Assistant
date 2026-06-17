"""规范路径识别器模块.

负责根据案件事实标签自动识别案件应适用的规范路径。
支持四种路径分类：帮信罪主路径、诈骗罪共同犯罪路径、掩饰隐瞒犯罪所得路径、待核实路径。

典型用法：

    # 导入模块: from app.services.standard_path_recognizer
    from app.services.standard_path_recognizer import recognize_standard_path, StandardPath

    # 初始化变量 case_data
    case_data = {...}  # 案件数据
    path = recognize_standard_path(case_data)
    print(path)  # StandardPath.MAIN_HELPER
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: from enum
from enum import Enum
# 导入模块: from typing
from typing import Any


# 定义 StandardPath 类
class StandardPath(str, Enum):
    """规范路径枚举.

    定义案件可能适用的四种规范路径，按判定优先级排序：
    FRAUD_COCONSPIRATOR > MONEY_LAUNDERING > MAIN_HELPER > PENDING_VERIFICATION
    """

    # 初始化变量 MAIN_HELPER
    MAIN_HELPER = "帮信罪主路径"
    # 初始化变量 FRAUD_COCONSPIRATOR
    FRAUD_COCONSPIRATOR = "诈骗罪共同犯罪路径"
    # 初始化变量 MONEY_LAUNDERING
    MONEY_LAUNDERING = "掩饰隐瞒犯罪所得路径"
    # 初始化变量 PENDING_VERIFICATION
    PENDING_VERIFICATION = "规范路径待核实"


# 事实标签关键词定义
_FRAUD_COCONSPIRATOR_KEYWORDS = [
    "明知是诈骗钱款",
    "明知诈骗",
    "仍取现",
    "分装",
    "上线安排",
    "明确告知诈骗",
    "知道是诈骗",
    "从事诈骗",
    "诈骗团伙",
    "诈骗犯罪",
    "电信网络诈骗",
    "接收诈骗资金",
    "诈骗所得",
    "诈骗信息",
    "电信诈骗",
    "网络诈骗",
    "发送诈骗",
    "用于诈骗",
    "诈骗活动",
]

_MONEY_LAUNDERING_KEYWORDS = [
    "长期取现",
    "按比例抽成",
    "验卡防冻",
    "转移资金",
    "洗前",
    "洗钱",
    "掩饰隐瞒",
    "资金转移",
    "套现",
    "取现转移",
    "帮助转移",
    "资金流转",
    "跑分",
    "接收赌资",
    "网络赌博",
    "资金清洗",
    "代购清洗",
    "POS机套现",
    "刷卡套现",
    "付款账户频繁更换",
]

_MAIN_HELPER_KEYWORDS = [
    "提供银行卡",
    "帮转账",
    "不知具体上游",
    "出租银行卡",
    "出售银行卡",
    "提供账户",
    "帮助支付结算",
    "提供技术支持",
    "提供广告推广",
    "提供支付接口",
    "提供U盾",
    "收购银行卡",
    "卖卡",
    "开卡",
    "提供手机卡",
    "代为保管",
    "养卡",
    "代管",
    "提供实名认证",
    "代办认证",
    "开发APP",
    "技术开发",
    "功能开发",
    "系统维护",
    "服务器维护",
    "网络维护",
    "技术维护",
    "代收转寄",
    "代收包裹",
    "虚假签名",
    "虚假姓名签收",
    "商户入驻审核",
    "资质材料审核",
    "人脸识别验证",
    "推广APP",
    "推广话术",
    "非法放贷平台",
    "快递员代收",
    "借用手机",
    "提供手机",
    "出借手机",
]


def _contains_any_keyword(text: str, keywords: list[str]) -> bool:
    """检查文本是否包含任意关键词.

    Args:
        text: 待检查的文本
        keywords: 关键词列表

    Returns:
        是否包含任意关键词
    """
    # 初始化变量 text_lower
    text_lower = text.lower()
    # 返回处理结果
    return any(keyword.lower() in text_lower for keyword in keywords)


def _extract_case_text(case_data: dict[str, Any]) -> str:
    """从案件数据中提取用于判定的文本内容.

    Args:
        case_data: 案件数据字典

    Returns:
        合并后的案件文本内容
    """
    # 初始化变量 texts
    texts = []

    # 提取案件事实
    # 条件判断：处理业务逻辑
    if "case_facts" in case_data:
        texts.append(case_data["case_facts"]    # 条件判断：处理业务逻辑
)

    # 提取实际判决理由
    if "actual_judgment" in case_data:
        judg        # 条件判断：处理业务逻辑
ment = case_data["actual_judgment"]
        # 条件判断: 检查 "reasoning" in judgment
        if "reasoning" in judgment:
                # 条件判断：处理业务逻辑
texts.append(judgment["reasoning"])

    # 提取真实判决分析中的关键指标
    if "ground_truth_analysis" in case_data:
        # 初始化变量 analysis
        analysis = case_data["ground_truth_an            # 条件判断：处理业务逻辑
alysis"]
        # 遍历: for dim_key in ["dimension1", "di                #
        for dim_key in ["dimension1", "di                # 条件判断：处理业务逻辑
mension2", "dimension3"]:
            # 条件判断: 检查 dim_key in analysis
            if dim_key in analysis:
                        # 条件判断：处理业务逻辑
        dim = analysis[dim_key]
                # 条件判断: 检查 "key_indicators"                 # 条件判断：
                if "key_indicators"                 # 条件判断：处理业务逻辑
in dim:
                    texts.extend(dim["key_indicators"])
                # 条件判断: 检查 "pattern_match" in dim
                if "pattern_match" in dim:
                    texts.append(dim["pattern_match"])
                # 条件判断: 检查 "reasoning" in dim
                if "reasoning" in dim:
                    texts.append(dim["reasoning"])

    # 返回处理结果
    return "\n".join(texts)


def detect_fraud_coconspirator(case_data: dict[str, Any]) -> StandardPath | None:
    """检测是否构成诈骗罪共同犯罪路径.

    判定条件：当识别到"明知是诈骗钱款仍取现/分装/上线安排"等事实标签时触发。
    这是最高优先级的判定。

    Args:
        case_data: 案件数据字典

    Returns:
        如果命中返回 FRAUD_COCONSPIRATOR，否则返回 None
    """
    # 初始化变量 case_text
    case_text = _extract_case_text(case_data)

    # 检查是否包含诈骗罪共同犯罪的关键词
    if _contains_any_keyword(case_text, _FRAUD_COCONSPIRATOR_KEYWORDS):
        # 进一步验证：需要有        # 条件判断：处理业务逻辑
明确的诈骗明知证据
        # 初始化变量 fraud_indicators
        fraud_indicators = [
            "明确告知",
            "知道是诈骗",
            "从事诈骗",
            "诈骗团伙",
            "明知诈骗",
            "接收诈骗资金",
            "诈骗所得",
        ]
        # 条件判断: 检查 _contains_any_keyword(case_text, fraud_i
        if _contains_any_keyword(case_text, fraud_indicators):
            # 返回处理结果
            return StandardPath.FRAUD_COCONSPIRATOR

    # 返回处理结果
    return None


def detect_money_laundering(case_data: dict[str, Any]) -> StandardPath | None:
    """检测是否构成掩饰隐瞒犯罪所得路径.

    判定条件：当识别到"长期取现 + 按比例抽成 + 验卡防冻"等事实标签组合时触发。
    优先级次于诈骗罪共同犯罪路径。

    Args:
        case_data: 案件数据字典

    Returns:
        如果命中返回 MONEY_LAUNDERING，否则返回 None
    """
    # 初始化变量 case_text
    case_text = _extract_case_text(case_
    # 条件判断：处理业务逻辑
data)

    # 检查是否包含掩饰隐瞒犯罪所得的关键词组合
    money_laundering_indicators = [
        "转移资金",
        "洗钱",
        "掩饰隐瞒",
        "资金转移",
        "套现",
        "取现转移",
        "帮助转移",
        "资金流转",
        "跑分",
    ]

    # 条件判断: 检查 _contains_any_keyword(case_text, money_l
    if _contains_any_keyword(case_text, money_laundering_        # 条件判断：处理业务逻辑
indicators):
        # 需要有资金操作相关的行为
        fund_operation_keywords = [
            "取现",
            "转账",
            "接收资金",
            "接收赌资",
            "网络赌博",
            "按比例",
            "抽成",
            "提成",
        ]
        # 条件判断: 检查 _contains_any_keyword(case_text, fund_op
        if _contains_any_keyword(case_text, fund_operation_keywords):
            # 返回处理结果
            return StandardPath.MONEY_LAUNDERING

    # 返回处理结果
    return None


def detect_main_helper(case_data: dict[str, Any]) -> StandardPath | None:
    # 函数 detect_main_helper 的初始化逻辑
    ""    # 条件判断：处理业务逻辑
"检测是否构成帮信罪主路径.

    判定条件：当识别到"提供银行卡 + 帮转账 + 不知具体上游"等事实标签组合时触发。
    优先级次于诈骗罪共同犯罪和掩饰隐瞒犯罪所得路径。

    Args:
        case_data: 案件数据字典

    Returns:
        如果命中返回 MAIN_HELPER，否则返回 None
    """
    # 初始化变量 case_text
    case_text = _extract_case_text(case_data)

    # 检查是否包含帮信罪的关键词
    if _contains_any_keyword(case_text, _MAIN_HELPER_KEYWORDS):
        # 返回处理结果
        return StandardPath.MAIN_HELPER

    # 返回处理结果
    return None


def recognize_standard_path(case_data: dict[str, Any]) -> StandardPath:
    """识别案件的规范路径.

    按照优先级顺序进行判定：
    1. FRAUD_COCONSPIRATO    # 条件判断：处理业务逻辑
R（诈骗罪共同犯罪路径）- 最高优先级
    2. MONEY_LAUNDERING（掩饰隐瞒犯罪所得路径）
    3. MAIN_HELPER（帮信罪主路    # 条件判断：处理业务逻辑
径）
    4. PENDING_VERIFICATION（规范路径待核实）- 以上均不命中时

    Args:
        case_da    # 条件判断：处理业务逻辑
ta: 案件数据字典

    Returns:
        识别出的规范路径
    """
    # 按优先级顺序进行判定
    result = detect_fraud_coconspirator(case_data)
    # 条件判断: 检查 result is not None
    if result is not None:
        # 返回处理结果
        return result

    # 初始化变量 result
    result = detect_money_laundering(case_data)
    # 条件判断: 检查 result is not None
    if result is not None:
        # 返回处理结果
        return result

    # 初始化变量 result
    result = detect_main_helper(case_data)
    # 条件判断: 检查 result is not None
    if result is not None:
        # 返回处理结果
        return result

    # 以上均不命中，返回待核实
    return StandardPath.PENDING_VERIFICATION


def recognize_standard_path_with_reason(
    # 函数 recognize_standard_path_with_reason 的初始化逻辑
    case_data: dict[str, Any],


    # 执行 recognize_standard_path_with_reason 函数的核心逻辑
) -> dict[str, Any]:
    """识别案件的规范路径并返回判定理由.

    Args:
        case_data: 案件数据字典

    Returns:
        包含路径和判定理由的字典
    """
    # 初始化变量 case_text
    case_text = _extract_case_text(case_data)

    # 按优先级顺序进行判定，记录命中原因
    if detect_fraud_coconspirator
    # 条件判断：处理业务逻辑
(case_data) is not None:
        # 初始化变量 matched_keywords
        matched_keywords = [
            kw for kw in _FRAUD_COCONSPIRATOR_KEYWORDS if kw.lower() in case            # 条件判断：处理业务逻辑
_text.lower()
        ]
        # 返回处理结果
        return {
            "path": StandardPath.FRAUD_COCONSPIRATOR,
            "reason": "识别到诈骗罪共同犯罪相关事实标签",
            "matched_keywords": matched_keywords,
        }

    if
    # 条件判断：处理业务逻辑
 detect_money_laundering(case_data) is not None:
        # 初始化变量 matched_keywords
        matched_keywords = [
            kw
            # 循环遍历：处理业务逻辑
            for kw in _MONEY_LAUNDERING_KEYWORDS
            # 条件判断: 检查 kw.lower() in case_text.lower()
            if kw.lower() in case_text.lower()
        ]
        # 返回处理结果
        return {
            "path": StandardPath.MONEY_LAUNDERING,
            "reason": "识别到掩饰隐瞒犯罪所得相关事实标签组合",
            "matched_keywords": matched_keywords,
        }

    # 条件判断: 检查 detect_main_helper(case_data) is not Non
    if detect_main_helper(case_data) is not None:
        # 初始化变量 matched_keywords
        matched_keywords = [
            kw for kw in _MAIN_HELPER_KEYWORDS if kw.lower() in case_text.lower()
        ]
        # 返回处理结果
        return {
            "path": StandardPath.MAIN_HELPER,
            "reason": "识别到帮信罪主路径相关事实标签",
            "matched_keywords": matched_keywords,
        }

    # 返回处理结果
    return {
        "path": StandardPath.PENDING_VERIFICATION,
        "reason": "未识别到明确的路径分类标签，需要人工核实",
        "matched_keywords": [],
    }
