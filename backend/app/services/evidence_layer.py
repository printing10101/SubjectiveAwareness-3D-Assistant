"""证据强度分层模块 (B3).

V1.2 法律引擎升级 - 第三步：将证据按强度分层。
"""

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.types.evidence_layer
from app.types.evidence_layer import (
    EvidenceLayer,
    EvidenceLayerReport,
    EvidenceStrength,
)

# 直接认知性证据关键词
_DIRECT_COGNITION_KEYWORDS = [
    "被告人供述", "供述明知", "承认明知",
    "同案犯供述", "共犯供述",
    "证人证言证实", "被害人陈述",
    "聊天记录显示明知", "通话记录显示明知",
    "书面供述", "讯问笔录",
]

# 客观异常事实关键词
_OBJECTIVE_ANOMALY_KEYWORDS = [
    "账户短期内大量资金",
    "交易模式异常",
    "频繁转账",
    "资金快进快出",
    "夜间频繁交易",
    "多个账户集中使用",
    "异常取款行为",
]

# 认知增强因素关键词
_COGNITIVE_ENHANCEMENT_KEYWORDS = [
    "被明确告知",
    "被告知违法",
    "被告知犯罪",
    "他人提醒",
    "银行提醒",
    "公安机关提醒",
    "仍继续提供",
    "仍不放弃",
]

# 辩解检验材料关键词
_DEFENSE_TEST_KEYWORDS = [
    "辩称不知情",
    "辩称被骗",
    "辩称被蒙蔽",
    "辩解合理",
    "辩解不合理",
    "与客观证据矛盾",
]


def _build_layer(
    # 函数 _build_layer 的初始化逻辑
    strength: EvidenceStrength,


    # 执行 _build_layer 函数的核心逻辑
    keywords: list[str],
    case_text: str,
    legal_basis: str = "",
) -> EvidenceLayer | None:
    """构建单个证据层."""
    # 初始化变量 matched_facts
    matched_facts = []
    # 循环遍历：处理业务逻辑
    for kw in keywords:
        # 条件判断：处理业务逻辑
        if kw in case_text:
            mat    
    # 条件判断：处理业务逻辑
ched_facts.append(kw)
    
    # 条件判断: 检查 matched_facts
    if matched_facts:
        # 返回处理结果
        return EvidenceLayer(
            # 初始化变量 strength
            strength=strength,
            # 初始化变量 facts
            facts=matched_facts,
            # 初始化变量 legal_basis
            legal_basis=legal_basis,
        )
    # 返回处理结果
    return None


def build_evidence_layers(case_text: str) -> list[EvidenceLayer]:
    """构建证据强度分层.

    将证据分为四层：
    1. 直接认知性证据（被告人供述、同案犯供述等）
    2. 客观异常事实（账户异常、交易异常等）
    3. 认知增强因素（被告知、被提醒等）
    4. 辩解检验材料（辩解及其合理性检验）

    Args:
        case_text: 案件事实文本

    Returns:
        list[EvidenceLayer]: 证据层列表
    """
    # 记录日志信息
    logger.info("开始证据强度分层 (B3)")

    # 初始化变量 layers
    layers = []

    # 第一层：直接认知性证据
    layer1 = _build_layer(
        "直接认知性证据",
        _DIRECT_COGNITION_KEYWORDS,
     # 条件判断：处理业务逻辑
       case_text,
        "刑法第287-2条",
    )
    # 条件判断: 检查 layer1
    if layer1:
        layers.append(layer1)
        # 记录日志信息
        logger.debug(f"直接认知性证据: {layer1.facts}")

    # 第二层：客观异常事实
    layer2 = _build_layer(
        "客观异常事实",
        _OBJECTIVE_A    # 条件判断：处理业务逻辑
NOMALY_KEYWORDS,
        case_text,
        "刑法第287-2条",
    )
    # 条件判断: 检查 layer2
    if layer2:
        layers.append(layer2)
        # 记录日志信息
        logger.debug(f"客观异常事实: {layer2.facts}")

    # 第三层：认知增强因素
    layer3 = _build_layer(
        "认知增强因素",
          # 条件判断：处理业务逻辑
  _COGNITIVE_ENHANCEMENT_KEYWORDS,
        case_text,
        "刑法第287-2条",
    )
    # 条件判断: 检查 layer3
    if layer3:
        layers.append(layer3)
        # 记录日志信息
        logger.debug(f"认知增强因素: {layer3.facts}")

    # 第四层：辩解检验材料
    layer4 = _build_laye    # 条件判断：处理业务逻辑
r(
        "辩解检验材料",
        _DEFENSE_TEST_KEYWORDS,
        case_text,
        "刑法第287-2条",
    )
    # 条件判断: 检查 layer4
    if layer4:
        layers.append(layer4)
        # 记录日志信息
        logger.debug(f"辩解检验材料: {layer4.facts}")

    # 记录日志信息
    logger.info(f"构建完成 {len(layers)} 个证据层")
    # 返回处理结果
    return layers


def guard_against_single_layer_override(report: EvidenceLayerReport) -> bool:
    """防止单层覆盖机制.

    规则：仅当存在直接认知性证据时，才能认定主观明知。
    仅有客观异常事实不足以单独认定明知。

    Args:
        report: 证据层报告

    Returns:
        bool: True表示可以认定明知，False表示不可以
    """
    # 记录日志信息
    logger.info("执行防止单层覆盖检查")

 
    # 条件判断：处理业务逻辑
   has_direct_cognition = any(
        layer.stre        # 循环遍历：处理业务逻辑
ngth == "直接认知性证据"
        # 遍历: for layer in report.evidence_layers
        for layer in report.evidence_layers
    )

    # 条件判断: 检查 has_direct_cognition
    if has_direct_cognition:
        # 记录日志信息
        logger.info("存在直接认知性证据，可以认定明知")
        # 返回处理结果
        return True
    
    # 记录日志信息
    logger.warning("缺乏直接认知性证据，不可以仅凭其他证据认定明知")
    # 返回处理结果
    return False
