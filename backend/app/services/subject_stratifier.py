"""多主体分层模块 (B2).

V1.2 法律引擎升级 - 第二步：识别并分层多个被告人。
"""

# 导入模块: re
import re

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.types.evidence_layer
from app.types.evidence_layer import SubjectInfo

# 被告人姓名模式（张某、李某、王某某等）
_SUBJECT_NAME_PATTERN = re.compile(
    r"被告人([赵钱孙李周吴郑王张刘陈杨黄赵周吴徐孙马朱胡郭林何高罗郑梁谢宋唐许韩冯邓曹彭曾田萧潘袁蔡蒋余于杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史贺顾毛郝孔邵毛常万顾赖武康])某{1,2}"
)

# 客观行为关键词
_BEHAVIOR_KEYWORDS = [
    "提供银行卡", "出租银行卡", "出借银行卡",
    "代为取款", "负责取款", "取现",
    "转账", "转移资金", "支付结算",
    "联系上线", "联系下线", "介绍",
    "提供技术支持", "提供账户",
    "帮助转移", "代为销售",
]

# 认知证据关键词
_COGNITION_KEYWORDS = [
    "明知", "知道", "应当知道",
    "被告知", "认识到",
    "聊天记录显示", "通话记录显示",
    "供述", "承认",
]

# 辩解关键词
_DEFENSE_KEYWORDS = [
    "辩称", "辩解", "不认可",
    "不知情", "不清楚", "不知道",
    "被蒙蔽", "被骗",
]


def _extract_subject_names(text: str) -> list[str]:
    """提取被告人姓名."""
    # 初始化变量 matches
    matches = _SUBJECT_NAME_PATTERN.findall(text)
    # 去重并保持顺序
    seen = set()
    # 初始化变量 names
    names = []
    # 循环遍历：处理业务逻辑
    for name in matches:
        # 条件判断：处理业务逻辑
        if name not in seen:
            seen.add(name)
            names.append(name)
    # 返回处理结果
    return names


def _extract_behavior(text: str, subject_name: str) -> str:
    """提取指定主体的客观行为."""
    be    # 循环遍历：处理业务逻辑
havior_parts = []
    # 遍历: for kw i        # 条件判断：处理业务逻辑
    for kw i        # 条件判断：处理业务逻辑
n _BEHAVIOR_KEYWORDS:
        # 条件判断: 检查 kw in text
        if kw in text:
            # 初始化变量 pattern
            pattern = f"{            # 条件判断：处理业务逻辑
subject_name}.*?{kw}|{kw}.*?{subject_name}"
            # 条件判断: 检查 re.search(pattern, text, re.DOTALL)
            if re.search(pattern, text, re.DOTALL):
                behavior_parts.append(kw)
    # 返回处理结果
    return "、".join(behavior_parts) if behavior_parts else "行为待确认"


def _extract_cognition(text: str, subject_name: str) -> list[str]:
    """提取指定主体        # 条件判断：处理业务逻辑
的认知证据."""
    # 初始化变量 cognition_parts
    cognition_parts = []
    # 遍历: for kw in _COGNITION_KEYWORDS:
    for kw in _COGNITION_KEYWORDS:
            # 条件判断：处理业务逻辑
        if kw in text:
            # 初始化变量 pattern
            pattern = f"{subject_name}.*?{kw}|{kw}.*?{subject_name}"
            # 条件判断: 检查 re.search(pattern, text, re.DOTALL)
            if re.search(pattern, text, re.DOTALL):
                cognition_parts.append(kw)
    # 返回处理结果
    return cognition_parts


def _extract_defense(text: str, subject_name: str) -> str:
         # 条件判断：处理业务逻辑
   """提取指定主体的辩解."""
    # 遍历: for kw in _DEFENSE_KEYWORDS:
    for kw in _DEFENSE_KEYWORDS:
        # 初始化变量 pattern
        pattern = f"{subject_name}.*?{kw}|{kw}.*?{subject_name}"
        # 条件判断: 检查 re.search(pattern, text, re.DOTALL)
        if re.search(pattern, text, re.DOTALL):
            # 返回处理结果
            return kw
    # 返回处理结果
    return ""


def stratify_subjects(case_text: str) -> list[SubjectInfo]:
    """对案件中的多个主体进行分层分析.

    识别所有被告人，并为每个被告人提取：
    - 角色定位
    - 客观行为
    - 认知证据
    - 辩解或争议

    Args:
        case_text: 案件事实文本

    Returns:
        list[SubjectInfo]: 主体信息列表
    """
    # 记录日志信息
    logger.info("开始多主体分层 (B2)")

    # 初始化变量 names
    names = _extract_subject_names(case_text)
    # 记录日志信息
    logger.debug(f"识别到 {len(names)}    # 循环遍历：处理业务逻辑
 个被告人: {names}")

    # 初始化变量 subjects
    subjects = []
    # 遍历: for name in names:
    for name in names:
        # 初始化变量 behavior
        behavior = _extract_behavior(case_text, name)
        # 初始化变量 cognition
        cognition = _extract_cognition(case_text, name)
        # 初始化变量 defense
        defense = _extract_defense(case_text, name)

        # 初始化变量 subject
        subject = SubjectInfo(
            # 初始化变量 name
            name=name,
            # 初始化变量 role
            role="被告人",
            # 初始化变量 objective_behavior
            objective_behavior=behavior,
            # 初始化变量 cognitive_evidence
            cognitive_evidence=cognition,
            # 初始化变量 defense
            defense=defense,
        )
        subjects.append(subject)
        # 记录日志信息
        logger.debug(f"主体 {name}: behavior={behavior}, cognition={cognition}")

    # 返回处理结果
    return subjects
