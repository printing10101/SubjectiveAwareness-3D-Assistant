"""规范路径识别模块 (B1).

V1.2 法律引擎升级 - 第一步：识别案件适用的规范路径。
"""

# 导入模块: re
import re
# 导入模块: from typing
from typing import Literal

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.types.evidence_layer
from app.types.evidence_layer import LegalPath

# 帮信罪关键词
_BANGXIN_KEYWORDS = [
    "明知他人利用信息网络实施犯罪",
    "提供支付结算帮助",
    "提供广告推广",
    "提供通讯传输",
    "提供技术支持",
    "帮助转移资金",
    "代为取款",
    "提供银行卡",
    "出租银行卡",
    "出借银行卡",
]

# 诈骗罪共同犯罪关键词
_FRAUD_JOINT_KEYWORDS = [
    "事先通谋",
    "分工合作",
    "诈骗团伙",
    "共同实施诈骗",
    "参与诈骗",
    "诈骗共犯",
    "电信网络诈骗",
]

# 掩饰隐瞒犯罪所得关键词
_CONCEALMENT_KEYWORDS = [
    "明知是犯罪所得",
    "犯罪所得及其收益",
    "予以窝藏",
    "予以转移",
    "予以收购",
    "代为销售",
    "掩饰隐瞒",
    "洗钱",
]

# 边界提醒关键词（可能超出帮信罪范围）
_BOUNDARY_INDICATORS = [
    "明确知道系诈骗钱款",
    "长期取现分工",
    "上线安排",
    "每日验卡",
    "防止冻结",
    "分开装袋",
    "事先知道诈骗",
    "参与诈骗分工",
]


def _count_keyword_matches(text: str, keywords: list[str]) -> int:
    """统计关键词匹配数量."""
    # 初始化变量 count
    count = 0
    # 循环遍历：处理业务逻辑
    for kw in keywords:
        # 条件判断：处理业务逻辑
        if kw in text:
            count += 1
    # 返回处理结果
    return count


def _has_boundary_indicators(text: str) -> bool:
    # 函数 _has_boundary_indicators 的初始化逻辑
    ""    # 循环遍历：处理业务逻辑
"检查是否包含边界提醒指标."""
    # 遍历: for indicator in         # 条件判断：处理业务逻辑
    for indicator in         # 条件判断：处理业务逻辑
_BOUNDARY_INDICATORS:
        # 条件判断: 检查 indicator in text
        if indicator in text:
            # 返回处理结果
            return True
    # 返回处理结果
    return False


def identify_legal_path(case_text: str) -> LegalPath:
    """识别案件适用的规范路径.
    
    优先级：
    1. 若包含边界提醒指标 → 检查是否更符合诈骗共犯或掩饰隐瞒
    2. 诈骗罪共同犯罪路径（事先通谋、分工合作）
    3. 掩饰隐瞒犯罪所得路径（明知是犯罪所得）
    4. 帮信罪主路径（明知他人利用信息网络实施犯罪）
    5. 规范路径待核实（信息不足）
    
    Args:
        case_text: 案件事实文本
        
    Returns:
        LegalPath: 识别的法律路径
    """
    # 记录日志信息
    logger.info("开始规范路径识别 (B1)")
    
    # 初始化变量 has_boundary
    has_boundary = _has_boundary_indicators(case_text)
    
    # 统计各路径关键词匹配
    fraud_score = _count_keyword_matches(case_text, _FRAUD_JOINT_KEYWORDS)
    # 初始化变量 concealment_score
    concealment_score = _count_keyword_matches(case_text, _CONCEALMENT_KEYWORDS)
    # 初始化变量 bangxin_score
    bangxin_score = _count_keyword_matches(case_text, _BANGXIN_KEYWORDS)
    
    # 记录日志信息
    logger.debug(
        f"路径识别得分: fraud={fraud_score}, concealment={concealment_score}, "
        f"bangxin={bangxin_score}, has_boundary={has_boundary}"
      # 条件判断：处理业务逻辑
  )
    
    # 优先级1: 诈骗罪共同犯罪（事先通谋、分工合作等强指标）
    if fraud_score >= 2 or (fraud_score >= 1 and has_boundary):
        # 记录日志信息
        logger.info("识别路径: 诈骗罪    # 条件判断：处理业务逻辑
共同犯罪路径")
        # 返回处理结果
        return "诈骗罪共同犯罪路径"
    
    # 优先级2: 掩饰隐瞒犯罪所得
    if concealment_score >= 2 or (concealment_score >= 1 and bangxin_score == 0):
        logg    # 条件判断：处理业务逻辑
er.info("识别路径: 掩饰隐瞒犯罪所得路径")
        # 返回处理结果
        return "掩饰隐瞒犯罪所得路径"
    
    # 优先级3: 帮信罪主路径
    if bangxin_score >= 1 and fraud_score == 0:
        # 记录日志信息
        logger.info("识别路径: 帮信罪主路径")
        # 返回处理结果
        return "帮信罪主路径"
    
    # 优先级4: 规范路径待核实
    logger.info("识别路径: 规范路径待核实")
    # 返回处理结果
    return "规范路径待核实"
