"""主体分析服务.

整合多主体分层分析功能，针对帮信罪案件中涉及多个犯罪主体的情形，
对每个主体独立进行角色识别、客观行为提取、认知证据分析和辩解理由推断。

模块功能：
- SubjectRole: 犯罪主体角色枚举
- SubjectAnalysis: 单个主体的分析结果数据类
- analyze_subjects(): 对案件中的每个主体进行独立分析
- get_multi_subject_ratio(): 统计多主体案件比例
- stratify_subjects(): 多主体分层分析（返回 SubjectInfo 格式）

角色识别规则基于事实标签匹配：
- 组织者(ORGANIZER)：同时满足"招募他人"和"分工"标签
- 中间人(INTERMEDIARY)：满足"联系上下线"标签
- 持卡人(ACCOUNT_HOLDER)：满足"交卡"标签
- 取款人(WITHDRAWER)：满足"ATM操作"标签
- 提供者(PROVIDER)：满足"提供"相关标签
- 未知(UNKNOWN)：无法匹配任何角色规则
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from app.types.evidence_layer import SubjectInfo

__all__ = [
    "SubjectRole",
    "SubjectAnalysis",
    "analyze_subjects",
    "get_multi_subject_ratio",
    "stratify_subjects",
]


# =============================================================================
# 第一部分：核心数据结构和枚举
# =============================================================================


class SubjectRole(str, Enum):
    """犯罪主体角色枚举.

    基于帮信罪案件中的常见角色分类，按参与程度和分工划分。

    Attributes:
        ORGANIZER: 组织者，负责招募人员并安排分工
        INTERMEDIARY: 中间人，负责联系上下线
        PROVIDER: 提供者，提供银行卡、支付工具等
        ACCOUNT_HOLDER: 持卡人，交出本人银行账户
        WITHDRAWER: 取款人，负责 ATM 取现操作
        UNKNOWN: 角色无法识别
    """

    ORGANIZER = "organizer"
    INTERMEDIARY = "intermediary"
    PROVIDER = "provider"
    ACCOUNT_HOLDER = "account_holder"
    WITHDRAWER = "withdrawer"
    UNKNOWN = "unknown"


@dataclass
class SubjectAnalysis:
    """单个主体的分析结果.

    Attributes:
        name: 主体名称（如"张某"、"李某"）
        role: 识别出的角色
        objective_behavior: 具体客观行为描述
        cognitive_evidence: 支持角色判定的证据列表
        defense: 主体可能的辩解理由
        matched_tags: 匹配到的事实标签列表
    """

    name: str
    role: SubjectRole
    objective_behavior: str = ""
    cognitive_evidence: list[str] = field(default_factory=list)
    defense: str = ""
    matched_tags: list[str] = field(default_factory=list)


# =============================================================================
# 第二部分：角色识别规则定义
# =============================================================================


# 每个角色的标签匹配规则：
#   key = SubjectRole
#   value = dict(required=必须同时出现的标签集合, optional=出现任一即可的标签集合)
_ROLE_RULES: dict[SubjectRole, dict[str, list[str]]] = {
    SubjectRole.ORGANIZER: {
        "required": [],
        "optional": ["招募他人", "分工", "组织", "策划", "指使", "安排"],
    },
    SubjectRole.INTERMEDIARY: {
        "required": [],
        "optional": ["联系上下线", "介绍", "居间", "牵线", "中间人", "联络"],
    },
    SubjectRole.ACCOUNT_HOLDER: {
        "required": [],
        "optional": ["交卡", "提供银行卡", "出借银行卡", "出售银行卡", "出租账户"],
    },
    SubjectRole.WITHDRAWER: {
        "required": [],
        "optional": ["ATM操作", "ATM取款", "取现", "取款", "柜面取款"],
    },
    SubjectRole.PROVIDER: {
        "required": [],
        "optional": ["提供", " supplied", "供给", "出借", "出租", "出售"],
    },
}

# 角色识别优先级（高优先级角色先匹配，避免 PROVIDER 的"提供"误匹配持卡人）
_ROLE_PRIORITY: list[SubjectRole] = [
    SubjectRole.ORGANIZER,
    SubjectRole.INTERMEDIARY,
    SubjectRole.WITHDRAWER,
    SubjectRole.ACCOUNT_HOLDER,
    SubjectRole.PROVIDER,
]

# 中文姓名正则：常见姓氏 + 某{0,2}
_NAME_PATTERN = re.compile(
    r"((?:被告人|犯罪嫌疑人|同案犯|共犯))"
    r"([\u4e00-\u9fff][某]{0,2})"
)

# 用于提取人名（不依赖角色前缀）
_BARE_NAME_PATTERN = re.compile(
    r"[\u4e00-\u9fff][某]{1,2}"
)

# 常见姓氏集合（用于辅助识别）
_COMMON_SURNAMES: frozenset[str] = frozenset(
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张"
    "孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎"
    "鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤"
    "滕殷罗毕郝邬安常乐于时傅皮下齐康伍余元卜顾孟平黄"
    "和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞"
    "熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭"
    "梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫"
    "经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚"
    "程嵇邢滑裴陆荣翁"
)

# =============================================================================
# 第三部分：stratify_subjects 相关常量（来自 subject_stratifier.py）
# =============================================================================

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


# =============================================================================
# 第四部分：内部辅助函数（analyze_subjects 相关）
# =============================================================================


def _extract_subject_names(case_text: str) -> list[str]:
    """从案件事实文本中提取涉案主体名称.

    优先匹配带角色前缀的姓名（如"被告人张某"），
    其次匹配裸名（如"张某"、"李某某"）。
    去重并保持首次出现顺序。

    Args:
        case_text: 案件事实文本

    Returns:
        list[str]: 去重后的主体名称列表
    """
    names: list[str] = []
    seen: set[str] = set()

    # 优先：带角色前缀的姓名
    for match in _NAME_PATTERN.finditer(case_text):
        name = match.group(2)
        if name not in seen:
            seen.add(name)
            names.append(name)

    # 补充：裸名匹配
    for match in _BARE_NAME_PATTERN.finditer(case_text):
        name = match.group()
        if len(name) >= 2 and name[0] in _COMMON_SURNAMES and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _identify_role(text_segment: str) -> tuple[SubjectRole, list[str]]:
    """根据文本片段中的事实标签识别主体角色.

    按优先级依次匹配角色规则：
    - ORGANIZER 需同时满足 required 中的所有标签
    - 其他角色只需匹配 optional 中任一标签
    - 均不匹配则返回 UNKNOWN

    Args:
        text_segment: 与该主体相关的文本片段

    Returns:
        tuple: (识别出的角色, 匹配到的标签列表)
    """
    matched_tags: list[str] = []

    # 遍历: for role in _ROLE_PRIORITY:
    for role in _ROLE_PRIORITY:
        rules = _ROLE_RULES[role]
        required = rules.get("required", [])
        optional = rules.get("optional", [])

        # 检查 required 标签是否全部出现
        required_hit = all(tag in text_segment for tag in required)
        if not required_hit:
            continue

        # 检查 optional 标签是否有任一命中（required 全满足时，optional 为空也通过）
        optional_hits = [tag for tag in optional if tag in text_segment]
        if required and not optional and required_hit:
            # required 全命中且无 optional 要求 → 直接匹配
            matched_tags = list(required)
            return role, matched_tags
        if optional_hits:
            matched_tags = [tag for tag in optional if tag in text_segment]
            if required:
                matched_tags = list(required) + matched_tags
            return role, matched_tags
    return SubjectRole.UNKNOWN, []


def _extract_text_segment(case_text: str, name: str) -> str:
    """提取与指定主体相关的文本片段.

    策略：以主体名称为中心，提取包含该名称的句子（以句号分割）。
    当句子同时包含多个主体名称时，仅保留当前主体首次出现位置之前
    到句子结尾的部分，避免其他主体的行为标签干扰角色识别。

    Args:
        case_text: 完整案件事实文本
        name: 主体名称

    Returns:
        str: 包含该主体的文本片段
    """
    sentences = re.split(r"[。！？；\n]+", case_text)
    relevant: list[str] = []
    # 遍历: for sent in sentences:
    for sent in sentences:
        if name not in sent:
            continue
        # 查找句子中是否包含其他主体名称
        other_names = _BARE_NAME_PATTERN.findall(sent)
        other_names = [n for n in other_names if n != name and len(n) >= 2]
        if other_names:
            # 提取当前名称附近的上下文（前后各30字符）
            idx = sent.find(name)
            start = max(0, idx - 30)
            end = min(len(sent), idx + len(name) + 80)
            relevant.append(sent[start:end].strip())
        # 其他情况的默认处理
        else:
            relevant.append(sent.strip())
    return "。".join(relevant)


def _extract_objective_behavior(text_segment: str, role: SubjectRole) -> str:
    """从文本片段中提取客观行为描述.

    根据角色类型提取对应的行为关键词上下文。

    Args:
        text_segment: 主体相关文本片段
        role: 已识别的角色

    Returns:
        str: 客观行为描述
    """
    behavior_keywords: dict[SubjectRole, list[str]] = {
        SubjectRole.ORGANIZER: ["招募", "组织", "策划", "指使", "安排", "分工"],
        SubjectRole.INTERMEDIARY: ["联系", "介绍", "居间", "联络", "沟通"],
        SubjectRole.PROVIDER: ["提供", "出借", "出租", "出售"],
        SubjectRole.ACCOUNT_HOLDER: ["交卡", "银行卡", "账户", "卡号"],
        SubjectRole.WITHDRAWER: ["取款", "取现", "ATM", "柜面"],
        SubjectRole.UNKNOWN: [],
    }
    keywords = behavior_keywords.get(role, [])
    if not keywords:
        # 对 UNKNOWN 角色，返回文本片段的前 100 字符作为行为描述
        return text_segment[:100] if text_segment else "行为待查"
    matched_parts: list[str] = []
    sentences = re.split(r"[。！？；\n]+", text_segment)
    # 遍历: for sent in sentences:
    for sent in sentences:
        if any(kw in sent for kw in keywords):
            matched_parts.append(sent.strip())
    if matched_parts:
        return "；".join(matched_parts)
    return text_segment[:100] if text_segment else "行为待查"


def _extract_cognitive_evidence(text_segment: str) -> list[str]:
    """提取支持角色判定的认知证据.

    识别文本中表示主观明知的证据表述。

    Args:
        text_segment: 主体相关文本片段

    Returns:
        list[str]: 认知证据列表
    """
    evidence_patterns: list[tuple[str, str]] = [
        ("明知", "明知故犯的主观认知"),
        ("知道", "直接知情"),
        ("应当知道", "应知推定"),
        ("被告知", "被告知后仍参与"),
        ("聊天记录", "聊天记录中的认知证据"),
        ("转账记录", "转账记录中的资金流向证据"),
        ("银行流水", "银行流水中的交易证据"),
        ("供述", "供述中的自认证据"),
        ("证人证言", "证人证言佐证"),
        ("监控", "监控录像客观证据"),
    ]

    evidence: list[str] = []
    # 遍历: for pattern, label in evidence_patterns:
    for pattern, label in evidence_patterns:
        if pattern in text_segment:
            evidence.append(f"{label}：文本中出现'{pattern}'相关表述")
    if not evidence:
        evidence.append("暂未提取到明确的认知证据，需进一步审查")
    return evidence


def _infer_defense(role: SubjectRole, text_segment: str) -> str:
    """根据角色和文本推断可能的辩解理由.

    Args:
        role: 已识别的角色
        text_segment: 主体相关文本片段

    Returns:
        str: 推断的辩解理由
    """
    defense_map: dict[SubjectRole, str] = {
        SubjectRole.ORGANIZER: (
            "可能辩称不具有组织意图，仅系参与者之一；"
            "或主张对其他参与者的行为不知情"
        ),
        SubjectRole.INTERMEDIARY: (
            "可能辩称仅提供信息传递，不了解上下游的犯罪意图；"
            "或主张系正常居间介绍行为"
        ),
        SubjectRole.PROVIDER: (
            "可能辩称提供工具时不知对方用于犯罪；"
            "或主张系正常借用、租赁关系"
        ),
        SubjectRole.ACCOUNT_HOLDER: (
            "可能辩称银行卡系被盗用或遗失后被人冒用；"
            "或主张不知他人将银行卡用于违法犯罪"
        ),
        SubjectRole.WITHDRAWER: (
            "可能辩称不知取款资金系犯罪所得；"
            "或主张系受他人指示的正常工作行为"
        ),
        SubjectRole.UNKNOWN: (
            "角色尚不明确，需结合全案证据进一步分析其主观认知和客观行为"
        ),
    }
    base_defense = defense_map.get(role, defense_map[SubjectRole.UNKNOWN])

    # 检查是否有认罪/坦白情节
    if "认罪" in text_segment or "坦白" in text_segment:
        base_defense += "；但存在认罪/坦白情节，可能影响辩解策略"
    if "自首" in text_segment:
        base_defense += "；存在自首情节"
    return base_defense


# =============================================================================
# 第五部分：stratify_subjects 相关内部函数
# =============================================================================


def _extract_subject_names_simple(text: str) -> list[str]:
    """提取被告人姓名（简化版本，用于 stratify_subjects）.

    Args:
        text: 案件文本

    Returns:
        list[str]: 去重后的被告人姓名列表
    """
    matches = _SUBJECT_NAME_PATTERN.findall(text)
    # 去重并保持顺序
    seen: set[str] = set()
    names: list[str] = []
    # 循环遍历：处理业务逻辑
    for name in matches:
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _extract_behavior(text: str, subject_name: str) -> str:
    """提取指定主体的客观行为.

    Args:
        text: 案件文本
        subject_name: 主体名称

    Returns:
        str: 客观行为描述
    """
    behavior_parts = []
    # 遍历: for kw in _BEHAVIOR_KEYWORDS:
    for kw in _BEHAVIOR_KEYWORDS:
        if kw in text:
            pattern = f"{subject_name}.*?{kw}|{kw}.*?{subject_name}"
            if re.search(pattern, text, re.DOTALL):
                behavior_parts.append(kw)
    return "、".join(behavior_parts) if behavior_parts else "行为待确认"


def _extract_cognition(text: str, subject_name: str) -> list[str]:
    """提取指定主体的认知证据.

    Args:
        text: 案件文本
        subject_name: 主体名称

    Returns:
        list[str]: 认知证据列表
    """
    cognition_parts = []
    # 遍历: for kw in _COGNITION_KEYWORDS:
    for kw in _COGNITION_KEYWORDS:
        if kw in text:
            pattern = f"{subject_name}.*?{kw}|{kw}.*?{subject_name}"
            if re.search(pattern, text, re.DOTALL):
                cognition_parts.append(kw)
    return cognition_parts


def _extract_defense(text: str, subject_name: str) -> str:
    """提取指定主体的辩解.

    Args:
        text: 案件文本
        subject_name: 主体名称

    Returns:
        str: 辩解内容
    """
    # 遍历: for kw in _DEFENSE_KEYWORDS:
    for kw in _DEFENSE_KEYWORDS:
        pattern = f"{subject_name}.*?{kw}|{kw}.*?{subject_name}"
        if re.search(pattern, text, re.DOTALL):
            return kw
    return ""


# =============================================================================
# 第六部分：公共 API 函数
# =============================================================================


def analyze_subjects(case: Any) -> list[SubjectAnalysis]:
    """对案件中的每个主体进行独立分析.

    核心分析函数：从案件文本中提取所有涉案主体，为每个主体独立输出
    角色、客观行为、认知证据和辩解理由。

    Args:
        case: 案件对象，需具备 case_text 属性（字符串类型的案件事实文本）。
              也接受 dict 类型，此时从 case["case_text"] 获取文本。

    Returns:
        list[SubjectAnalysis]: 每个主体一条分析结果。
            若无法识别任何主体，返回仅包含一个 UNKNOWN 角色的列表。
    """
    # 获取案件文本
    if isinstance(case, dict):
        case_text = case.get("case_text", "")
    elif hasattr(case, "case_text"):
        case_text = str(case.case_text or "")
    # 其他情况的默认处理
    else:
        case_text = str(case or "")
    if not case_text.strip():
        return [
            SubjectAnalysis(
                name="未知主体",
                role=SubjectRole.UNKNOWN,
                objective_behavior="案件文本为空，无法分析",
                cognitive_evidence=["无可用文本"],
                defense="无法判断",
            )
        ]

    # 提取主体名称
    subject_names = _extract_subject_names(case_text)
    if not subject_names:
        # 无法识别任何主体 → 返回 [UNKNOWN]
        return [
            SubjectAnalysis(
                name="未知主体",
                role=SubjectRole.UNKNOWN,
                objective_behavior=case_text[:100],
                cognitive_evidence=["未能从文本中识别出具体主体名称"],
                defense="主体不可识别",
            )
        ]

    # 为每个主体独立分析
    results: list[SubjectAnalysis] = []
    # 遍历: for name in subject_names:
    for name in subject_names:
        segment = _extract_text_segment(case_text, name)
        role, matched_tags = _identify_role(segment)
        objective_behavior = _extract_objective_behavior(segment, role)
        cognitive_evidence = _extract_cognitive_evidence(segment)
        defense = _infer_defense(role, segment)

        results.append(
            SubjectAnalysis(
                name=name,
                role=role,
                objective_behavior=objective_behavior,
                cognitive_evidence=cognitive_evidence,
                defense=defense,
                matched_tags=matched_tags,
            )
        )
    return results


def get_multi_subject_ratio(cases: list[Any]) -> dict[str, Any]:
    """统计多主体案件在总案件中的比例.

    Args:
        cases: 案件列表，每个案件需具备 case_text 属性或为 dict

    Returns:
        dict: 统计结果，包含 total_cases、multi_subject_cases、ratio 等
    """
    total = len(cases)
    multi_count = 0
    multi_details: list[dict[str, Any]] = []

    # 遍历: for i, case in enumerate(cases):
    for i, case in enumerate(cases):
        analyses = analyze_subjects(case)
        if len(analyses) > 1:
            multi_count += 1
            multi_details.append(
                {"index": i,
                    "subject_count": len(analyses),
                    "roles": [a.role.value for a in analyses],
                }
            )
    ratio = multi_count / total if total > 0 else 0.0
    return {
        "total_cases": total,
        "multi_subject_cases": multi_count,
        "single_subject_cases": total - multi_count,
        "ratio": round(ratio, 4),
        "ratio_percent": f"{ratio * 100:.2f}%",
        "details": multi_details,
    }


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
    names = _extract_subject_names_simple(case_text)
    # 记录日志信息
    logger.debug(f"识别到 {len(names)} 个被告人: {names}")
    subjects = []
    # 遍历: for name in names:
    for name in names:
        behavior = _extract_behavior(case_text, name)
        cognition = _extract_cognition(case_text, name)
        defense = _extract_defense(case_text, name)
        subject = SubjectInfo(
            name=name,
            role="被告人",
            objective_behavior=behavior,
            cognitive_evidence=cognition,
            defense=defense,
        )
        subjects.append(subject)
        # 记录日志信息
        logger.debug(f"主体 {name}: behavior={behavior}, cognition={cognition}")
    return subjects
