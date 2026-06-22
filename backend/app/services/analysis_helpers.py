"""分析辅助服务统一模块.

整合量刑建议、相似案例检索、规范路径识别、档级组合四大分析辅助功能。
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from loguru import logger

from app.services.ollama_client import get_client
from app.services.prompt import SENTENCING_PROMPT, SIMILAR_CASES_PROMPT
from app.services.rule_engine import Rule
from app.types.analysis import AnalysisResult
from app.types.analysis_v2 import FinalVerdict, TierEnum


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

__all__ = [
    # 量刑建议
    "SentencingSuggestion",
    "get_sentencing_suggestion",
    # 相似案例检索
    "SimilarCaseResult",
    "find_similar_cases",
    # 规范路径识别
    "StandardPath",
    "recognize_standard_path",
    "recognize_standard_path_with_reason",
    "detect_fraud_coconspirator",
    "detect_money_laundering",
    "detect_main_helper",
    # 档级组合（整合自 tier_combiner.py）
    "combine_tiers",
    "combine_tiers_with_overrides",
    "all_combinations",
    "debug_dump_table",
]


# ===========================================================================
# 第一部分：量刑建议
# ===========================================================================


@dataclass
class SentencingSuggestion:
    """量刑建议结果."""

    suggested_sentence: str
    reasoning: str
    error: bool = False  # 标记是否为错误降级结果
    raw_response: str | None = None  # 原始响应（仅错误时有值）


async def get_sentencing_suggestion(
    analysis_result: AnalysisResult,
    legal_rules: list | None = None,
) -> SentencingSuggestion:
    """从 LLM 获取量刑建议.

    将案件分析结果和适用法律规则组合为提示词，调用 LLM 生成量刑建议。
    当分析失败时，返回带有 error=True 标记的降级结果，调用方可据此判断。

    Args:
        analysis_result: 案件分析结果字典
        legal_rules: 适用法律规则列表（可选）

    Returns:
        SentencingSuggestion: 包含 suggested_sentence、reasoning 和 error 标记的建议

    Example:
        >>> result = await get_sentencing_suggestion({"crime": "theft"})
        >>> if result.error:
        >>>     print("分析失败，使用降级结果")
        >>> else:
        >>>     print(f"建议刑期: {result.suggested_sentence}")
    """
    if legal_rules:
        rules_text: str = "\n".join([str(r) for r in legal_rules])
    else:
        rules_text = "无"

    prompt: str = SENTENCING_PROMPT.format(
        analysis_result=json.dumps(analysis_result, ensure_ascii=False),
        legal_rules=rules_text,
    )

    try:
        client = get_client()
        result = await client.generate_json(prompt)

        # 验证返回结果结构
        if isinstance(result, dict):
            suggested_sentence = result.get("suggested_sentence", "待定")
            reasoning = result.get("reasoning", "未提供理由")

            # 验证必需字段存在
            if not suggested_sentence or not reasoning:
                logger.warning(
                    "量刑建议缺少必需字段: suggested_sentence={}, reasoning={}",
                    suggested_sentence,
                    reasoning,
                )
                return SentencingSuggestion(
                    suggested_sentence="待定",
                    reasoning="LLM 返回结果缺少必需字段",
                    error=True,
                    raw_response=json.dumps(result, ensure_ascii=False),
                )

            return SentencingSuggestion(
                suggested_sentence=str(suggested_sentence),
                reasoning=str(reasoning),
                error=False,
            )

        # LLM 返回非 dict 类型
        logger.warning("LLM 返回非预期的类型: {}", type(result).__name__)
        return SentencingSuggestion(
            suggested_sentence="待定",
            reasoning="LLM 返回格式错误",
            error=True,
            raw_response=str(result),
        )

    except json.JSONDecodeError as e:
        logger.error("量刑建议 JSON 解析失败: {}", e)
        return SentencingSuggestion(
            suggested_sentence="待定",
            reasoning=f"JSON 解析失败: {e}",
            error=True,
        )

    except Exception as e:  # noqa: BLE001
        logger.error("获取量刑建议失败: {}", e)
        return SentencingSuggestion(
            suggested_sentence="待定",
            reasoning=f"分析失败: {e}",
            error=True,
        )


# ===========================================================================
# 第二部分：相似案例检索
# ===========================================================================


_MAX_CASE_TEXT_LENGTH: int = 1000


@dataclass
class SimilarCaseResult:
    """相似案例检索结果."""

    cases: list[dict[str, Any]]  # 相似案例列表
    error: bool = False  # 标记是否为错误降级结果
    error_message: str | None = None  # 错误信息（仅错误时有值）
    truncated: bool = False  # 标记是否截断了原文


async def find_similar_cases(
    case_text: str,
    top_k: int = 3,
) -> SimilarCaseResult:
    """使用 LLM 查找相似案例.

    将案件文本截取后作为提示词，调用 LLM 进行相似案例匹配。
    当检索失败时，返回带有 error=True 标记的降级结果，调用方可据此判断。

    Args:
        case_text: 案件事实文本
        top_k: 返回的最大相似案例数（默认 3）

    Returns:
        SimilarCaseResult: 包含 cases 列表和 error 标记的结果

    Example:
        >>> result = await find_similar_cases("被告人实施盗窃...")
        >>> if result.error:
        >>>     print("检索失败，无相似案例")
        >>> else:
        >>>     print(f"找到 {len(result.cases)} 个相似案例")
    """
    # 检查是否需要截断
    truncated = len(case_text) > _MAX_CASE_TEXT_LENGTH
    if truncated:
        logger.warning(
            "案件文本过长，截取前 {} 字符进行检索（原文 {} 字符）",
            _MAX_CASE_TEXT_LENGTH,
            len(case_text),
        )

    truncated_text = case_text[:_MAX_CASE_TEXT_LENGTH]
    prompt: str = SIMILAR_CASES_PROMPT.format(case_text=truncated_text)

    try:
        client = get_client()
        data = await client.generate_json(prompt, field="similar_cases")

        # 处理返回结果
        cases: list[dict[str, Any]] = []
        if isinstance(data, list):
            cases = data
        elif isinstance(data, dict):
            cases = data.get("similar_cases", [])

        # 验证每个案例的结构
        valid_cases: list[dict[str, Any]] = []
        for case in cases:
            if isinstance(case, dict) and ("case_id" in case or "title" in case):
                if "similarity" in case:
                    try:
                        sim = float(case["similarity"])
                        case["similarity"] = max(0.0, min(1.0, sim))
                    except (ValueError, TypeError):
                        case["similarity"] = 0.5  # 默认相似度
                valid_cases.append(case)

        # 限制返回数量
        valid_cases = valid_cases[:top_k]

        return SimilarCaseResult(
            cases=valid_cases,
            error=False,
            truncated=truncated,
        )

    except Exception as e:  # noqa: BLE001
        logger.error("查找相似案例失败: {}", e)
        return SimilarCaseResult(
            cases=[],
            error=True,
            error_message=str(e),
            truncated=truncated,
        )


# ===========================================================================
# 第三部分：规范路径识别
# ===========================================================================


class StandardPath(str, Enum):
    """规范路径枚举.

    定义案件可能适用的四种规范路径，按判定优先级排序：
    FRAUD_COCONSPIRATOR > MONEY_LAUNDERING > MAIN_HELPER > PENDING_VERIFICATION
    """

    MAIN_HELPER = "帮信罪主路径"
    FRAUD_COCONSPIRATOR = "诈骗罪共同犯罪路径"
    MONEY_LAUNDERING = "掩饰隐瞒犯罪所得路径"
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
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)


def _extract_case_text(case_data: dict[str, Any]) -> str:
    """从案件数据中提取用于判定的文本内容.

    Args:
        case_data: 案件数据字典

    Returns:
        合并后的案件文本内容
    """
    texts = []

    # 提取案件事实
    if "case_facts" in case_data:
        texts.append(case_data["case_facts"])

    # 提取实际判决理由
    if "actual_judgment" in case_data:
        judgment = case_data["actual_judgment"]
        if "reasoning" in judgment:
            texts.append(judgment["reasoning"])

    # 提取真实判决分析中的关键指标
    if "ground_truth_analysis" in case_data:
        analysis = case_data["ground_truth_analysis"]
        # 遍历: for dim_key in ["dimension1", "dimension2", "dimension3"]
        for dim_key in ["dimension1", "dimension2", "dimension3"]:
            if dim_key in analysis:
                dim = analysis[dim_key]
                if "key_indicators" in dim:
                    texts.extend(dim["key_indicators"])
                if "pattern_match" in dim:
                    texts.append(dim["pattern_match"])
                if "reasoning" in dim:
                    texts.append(dim["reasoning"])
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
    case_text = _extract_case_text(case_data)

    # 检查是否包含诈骗罪共同犯罪的关键词
    if _contains_any_keyword(case_text, _FRAUD_COCONSPIRATOR_KEYWORDS):
        # 进一步验证：需要有明确的诈骗明知证据
        fraud_indicators = [
            "明确告知",
            "知道是诈骗",
            "从事诈骗",
            "诈骗团伙",
            "明知诈骗",
            "接收诈骗资金",
            "诈骗所得",
        ]
        if _contains_any_keyword(case_text, fraud_indicators):
            return StandardPath.FRAUD_COCONSPIRATOR
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
    case_text = _extract_case_text(case_data)

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
    if _contains_any_keyword(case_text, money_laundering_indicators):
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
        if _contains_any_keyword(case_text, fund_operation_keywords):
            return StandardPath.MONEY_LAUNDERING
    return None


def detect_main_helper(case_data: dict[str, Any]) -> StandardPath | None:
    """检测是否构成帮信罪主路径.

    判定条件：当识别到"提供银行卡 + 帮转账 + 不知具体上游"等事实标签组合时触发。
    优先级次于诈骗罪共同犯罪和掩饰隐瞒犯罪所得路径。

    Args:
        case_data: 案件数据字典

    Returns:
        如果命中返回 MAIN_HELPER，否则返回 None
    """
    case_text = _extract_case_text(case_data)

    # 检查是否包含帮信罪的关键词
    if _contains_any_keyword(case_text, _MAIN_HELPER_KEYWORDS):
        return StandardPath.MAIN_HELPER
    return None


def recognize_standard_path(case_data: dict[str, Any]) -> StandardPath:
    """识别案件的规范路径.

    按照优先级顺序进行判定：
    1. FRAUD_COCONSPIRATOR（诈骗罪共同犯罪路径）- 最高优先级
    2. MONEY_LAUNDERING（掩饰隐瞒犯罪所得路径）
    3. MAIN_HELPER（帮信罪主路径）
    4. PENDING_VERIFICATION（规范路径待核实）- 以上均不命中时

    Args:
        case_data: 案件数据字典

    Returns:
        识别出的规范路径
    """
    # 按优先级顺序进行判定
    result = detect_fraud_coconspirator(case_data)
    if result is not None:
        return result
    result = detect_money_laundering(case_data)
    if result is not None:
        return result
    result = detect_main_helper(case_data)
    if result is not None:
        return result

    # 以上均不命中，返回待核实
    return StandardPath.PENDING_VERIFICATION


def recognize_standard_path_with_reason(
    case_data: dict[str, Any],
) -> dict[str, Any]:
    """识别案件的规范路径并返回判定理由.

    Args:
        case_data: 案件数据字典

    Returns:
        包含路径和判定理由的字典
    """
    case_text = _extract_case_text(case_data)

    # 按优先级顺序进行判定，记录命中原因
    if detect_fraud_coconspirator(case_data) is not None:
        matched_keywords = [
            kw for kw in _FRAUD_COCONSPIRATOR_KEYWORDS if kw.lower() in case_text.lower()
        ]
        return {
            "path": StandardPath.FRAUD_COCONSPIRATOR,
            "reason": "识别到诈骗罪共同犯罪相关事实标签",
            "matched_keywords": matched_keywords,
        }

    if detect_money_laundering(case_data) is not None:
        matched_keywords = [
            kw
            # 循环遍历：处理业务逻辑
            for kw in _MONEY_LAUNDERING_KEYWORDS
            if kw.lower() in case_text.lower()
        ]
        return {
            "path": StandardPath.MONEY_LAUNDERING,
            "reason": "识别到掩饰隐瞒犯罪所得相关事实标签组合",
            "matched_keywords": matched_keywords,
        }
    if detect_main_helper(case_data) is not None:
        matched_keywords = [
            kw for kw in _MAIN_HELPER_KEYWORDS if kw.lower() in case_text.lower()
        ]
        return {
            "path": StandardPath.MAIN_HELPER,
            "reason": "识别到帮信罪主路径相关事实标签",
            "matched_keywords": matched_keywords,
        }
    return {
        "path": StandardPath.PENDING_VERIFICATION,
        "reason": "未识别到明确的路径分类标签，需要人工核实",
        "matched_keywords": [],
    }


# ===========================================================================
# 第四部分：档级组合（整合自 tier_combiner.py）
# ===========================================================================

# 高权重规则触发阈值（≥ 此值视为"高权重规则命中"）
_HIGH_RULE_WEIGHT_THRESHOLD: float = 0.8

# 极高权重规则触发阈值（≥ 此值视为"组织者/主犯"信号）
_VERY_HIGH_RULE_WEIGHT_THRESHOLD: float = 0.9

# T4 升级因子：上游犯罪为电信网络诈骗/跨境/恐怖主义时，无视三维度档级直接升 T4
_T4_ESCALATION_KEYWORDS: tuple[str, ...] = (
    "电信网络诈骗", "跨境", "恐怖主义", "黑社会", "贩毒",
    "组织者", "主犯", "累犯", "数额特别巨大",
    "上游犯罪为", "严重危害", "国家机关",
)

# 4×4×4 = 64 种组合的"基础映射表"
# 索引：(d1, d2, d3) → (final_tier, combination_rule_id)
_BASE_COMBINATION: dict[tuple[int, int, int], tuple[int, str]] = {
    # ---- 三个全为 T1（1,1,1）→ 16 种中前 1 ----
    (1, 1, 1): (1, "BASE_1_1_1"),
    (1, 1, 2): (1, "BASE_1_1_2"),
    (1, 1, 3): (2, "BASE_1_1_3"),
    (1, 1, 4): (2, "BASE_1_1_4"),

    (1, 2, 1): (1, "BASE_1_2_1"),
    (1, 2, 2): (2, "BASE_1_2_2"),
    (1, 2, 3): (2, "BASE_1_2_3"),
    (1, 2, 4): (2, "BASE_1_2_4"),

    (1, 3, 1): (2, "BASE_1_3_1"),
    (1, 3, 2): (2, "BASE_1_3_2"),
    (1, 3, 3): (3, "BASE_1_3_3"),
    (1, 3, 4): (3, "BASE_1_3_4"),

    (1, 4, 1): (2, "BASE_1_4_1"),
    (1, 4, 2): (2, "BASE_1_4_2"),
    (1, 4, 3): (3, "BASE_1_4_3"),
    (1, 4, 4): (3, "BASE_1_4_4"),

    # ---- d1 = 2 ----
    (2, 1, 1): (1, "BASE_2_1_1"),
    (2, 1, 2): (2, "BASE_2_1_2"),
    (2, 1, 3): (2, "BASE_2_1_3"),
    (2, 1, 4): (2, "BASE_2_1_4"),

    (2, 2, 1): (1, "BASE_2_2_1"),
    (2, 2, 2): (2, "BASE_2_2_2"),
    (2, 2, 3): (2, "BASE_2_2_3"),
    (2, 2, 4): (3, "BASE_2_2_4"),

    (2, 3, 1): (2, "BASE_2_3_1"),
    (2, 3, 2): (2, "BASE_2_3_2"),
    (2, 3, 3): (3, "BASE_2_3_3"),
    (2, 3, 4): (3, "BASE_2_3_4"),

    (2, 4, 1): (2, "BASE_2_4_1"),
    (2, 4, 2): (3, "BASE_2_4_2"),
    (2, 4, 3): (3, "BASE_2_4_3"),
    (2, 4, 4): (3, "BASE_2_4_4"),

    # ---- d1 = 3 ----
    (3, 1, 1): (2, "BASE_3_1_1"),
    (3, 1, 2): (2, "BASE_3_1_2"),
    (3, 1, 3): (3, "BASE_3_1_3"),
    (3, 1, 4): (3, "BASE_3_1_4"),

    (3, 2, 1): (2, "BASE_3_2_1"),
    (3, 2, 2): (2, "BASE_3_2_2"),
    (3, 2, 3): (3, "BASE_3_2_3"),
    (3, 2, 4): (3, "BASE_3_2_4"),

    (3, 3, 1): (2, "BASE_3_3_1"),
    (3, 3, 2): (3, "BASE_3_3_2"),
    (3, 3, 3): (3, "BASE_3_3_3"),
    (3, 3, 4): (3, "BASE_3_3_4"),

    (3, 4, 1): (3, "BASE_3_4_1"),
    (3, 4, 2): (3, "BASE_3_4_2"),
    (3, 4, 3): (3, "BASE_3_4_3"),
    (3, 4, 4): (4, "BASE_3_4_4"),

    # ---- d1 = 4 ----
    (4, 1, 1): (2, "BASE_4_1_1"),
    (4, 1, 2): (2, "BASE_4_1_2"),
    (4, 1, 3): (3, "BASE_4_1_3"),
    (4, 1, 4): (3, "BASE_4_1_4"),

    (4, 2, 1): (2, "BASE_4_2_1"),
    (4, 2, 2): (3, "BASE_4_2_2"),
    (4, 2, 3): (3, "BASE_4_2_3"),
    (4, 2, 4): (3, "BASE_4_2_4"),

    (4, 3, 1): (3, "BASE_4_3_1"),
    (4, 3, 2): (3, "BASE_4_3_2"),
    (4, 3, 3): (3, "BASE_4_3_3"),
    (4, 3, 4): (4, "BASE_4_3_4"),

    (4, 4, 1): (3, "BASE_4_4_1"),
    (4, 4, 2): (3, "BASE_4_4_2"),
    (4, 4, 3): (4, "BASE_4_4_3"),
    (4, 4, 4): (4, "BASE_4_4_4"),
}

assert len(_BASE_COMBINATION) == 64, (
    f"档级组合表必须覆盖 4×4×4=64 种组合，实际 {len(_BASE_COMBINATION)}"
)


def combine_tiers(
    d1: TierEnum | str | int | None,
    d2: TierEnum | str | int | None,
    d3: TierEnum | str | int | None,
    rule_hits: Iterable[Rule] | None = None,
) -> FinalVerdict:
    """档级组合主入口."""
    t1 = TierEnum.coerce(d1)
    t2 = TierEnum.coerce(d2)
    t3 = TierEnum.coerce(d3)
    rules = list(rule_hits) if rule_hits else []

    return combine_tiers_with_overrides(t1, t2, t3, rules)


def combine_tiers_with_overrides(
    d1: TierEnum,
    d2: TierEnum,
    d3: TierEnum,
    rule_hits: list[Rule] | None = None,
) -> FinalVerdict:
    """带 override 上下文的档级组合."""
    rules = rule_hits or []
    key = (d1.rank, d2.rank, d3.rank)
    base_tier_rank, rule_id = _BASE_COMBINATION.get(key, (2, "BASE_FALLBACK"))

    # 升级判定
    has_t4_signal: bool = _contains_t4_signal(rules)
    has_high_weight: bool = any(
        r.weight >= _HIGH_RULE_WEIGHT_THRESHOLD for r in rules
    )
    has_very_high_weight: bool = any(
        r.weight >= _VERY_HIGH_RULE_WEIGHT_THRESHOLD for r in rules
    )

    final_rank = base_tier_rank

    if has_t4_signal and has_very_high_weight:
        final_rank = 4
        rule_id = "ESCALATE_T4_CRITICAL"
    elif has_t4_signal and has_high_weight:
        final_rank = max(final_rank, 3)
        rule_id = "ESCALATE_T3_HEAVY"
    elif has_high_weight and final_rank < 3:
        final_rank = 3
        rule_id = "ESCALATE_T3_HEAVY"

    # 抗辩降档
    if d3.rank <= d1.rank - 1 and d3.rank <= d2.rank - 1 and final_rank > 1:
        final_rank -= 1
        rule_id = f"DOWNGRADE_DEFENSE_{rule_id}"

    final_rank = max(1, min(4, final_rank))
    final_tier = TierEnum(f"T{final_rank}")

    confidence = _compute_combiner_confidence(d1, d2, d3, rules)

    return FinalVerdict(
        final_tier=final_tier.value,
        final_label=final_tier.chinese_label,
        sentence_band=final_tier.sentence_band,
        confidence=round(confidence, 4),
        severity_score=final_rank,
        combination_rule=rule_id,
    )


def _contains_t4_signal(rules: Iterable[Rule]) -> bool:
    """判断是否触发了 T4 升级信号."""
    for r in rules:
        haystack = " ".join(
            [
                r.name or "",
                r.conclusion or "",
                r.conditions or "",
                " ".join(r.applicable_scenarios or []),
            ]
        )
        if any(kw in haystack for kw in _T4_ESCALATION_KEYWORDS):
            return True
    return False


def _compute_combiner_confidence(
    d1: TierEnum,
    d2: TierEnum,
    d3: TierEnum,
    rules: list[Rule],
) -> float:
    """档级组合的置信度."""
    ranks = [d1.rank, d2.rank, d3.rank]
    spread = max(ranks) - min(ranks)
    base_conf = {
        0: 1.00,
        1: 0.85,
        2: 0.65,
        3: 0.45,
    }.get(spread, 0.45)

    rule_bonus = min(0.20, len(rules) * 0.02)
    return max(0.0, min(1.0, base_conf + rule_bonus))


def all_combinations() -> list[tuple[tuple[int, int, int], tuple[int, str]]]:
    """返回 64 种基础组合的有序列表."""
    return list(_BASE_COMBINATION.items())


def debug_dump_table() -> str:
    """以 4×4×4 形式打印档级组合表."""
    lines: list[str] = ["档级组合基础映射 (d1 × d2 → d3 → final_tier)："]
    for d1 in range(1, 5):
        for d2 in range(1, 5):
            row: list[str] = [f"d1={d1} d2={d2} →"]
            for d3 in range(1, 5):
                rank, _ = _BASE_COMBINATION[(d1, d2, d3)]
                row.append(f"d3={d3}:T{rank}")
            lines.append(" ".join(row))
    return "\n".join(lines)
