"""复杂度评估模块.

根据案件文本的法律关键词、句子数、证据数、涉案人数等维度
评估案件复杂度，返回 simple/medium/complex 三级分类。
"""

import re
from dataclasses import dataclass
from typing import Literal

from loguru import logger

from app.config import AnalysisConfig

ComplexityLevel = Literal["simple", "medium", "complex"]

# ---------------------------------------------------------------------------
# 复杂度评估 — 法律关键词与模式定义
# ---------------------------------------------------------------------------

_KEYWORD_LEGAL: frozenset[str] = frozenset(
    {
        "故意", "过失", "明知", "应知", "非法", "犯罪", "违法", "侵害",
        "损害", "诈骗", "盗窃", "抢劫", "抢夺", "故意杀人", "故意伤害",
        "强奸", "绑架", "拐卖", "贪污", "受贿", "行贿", "挪用", "侵占",
        "职务侵占", "贩毒", "走私", "洗钱", "伪造", "变造", "假冒",
        "侵犯", "破坏", "扰乱", "寻衅滋事", "聚众斗殴", "敲诈勒索",
        "威胁", "胁迫", "暴力", "非法占有", "非法经营", "非法集资",
        "非法吸收公众存款", "组织领导", "黑社会", "传销", "开设赌场",
        "赌博", "危险驾驶", "交通肇事", "重大责任事故",
        "生产销售伪劣产品", "污染环境", "非法采矿",
        "掩饰隐瞒犯罪所得", "窝藏", "包庇", "妨害作证",
        "自首", "立功", "坦白", "认罪认罚", "累犯", "惯犯", "初犯",
        "偶犯", "未遂", "中止", "预备", "既遂", "主犯", "从犯",
        "胁从犯", "教唆犯", "正当防卫", "紧急避险", "防卫过当",
        "情节严重", "情节特别严重", "数额较大", "数额巨大",
        "数额特别巨大", "共同犯罪", "数罪并罚", "缓刑", "假释",
        "减刑", "社区矫正", "剥夺政治权利",
    }
)

_EVIDENCE_TERMS: tuple[str, ...] = (
    "证据", "证人", "证言", "物证", "书证", "鉴定", "鉴定意见",
    "现场", "现场勘查", "监控", "监控录像", "DNA", "指纹", "血迹",
    "痕迹", "尸检", "伤情鉴定", "价格认定", "电子数据",
    "银行流水", "转账记录", "聊天记录", "通话记录",
    "微信记录", "短信记录", "笔录", "供述", "辩解", "陈述",
    "辨认笔录", "指认", "扣押", "提取", "查封",
    "赃款", "赃物", "作案工具", "凶器",
    "视频", "照片", "录音", "录像",
    "审计报告", "会计鉴定", "司法鉴定",
    "勘验笔录", "检查笔录", "侦查实验", "电子证据",
)

_PEOPLE_ROLE_TERMS: tuple[str, ...] = (
    "被告人", "被害人", "原告", "被告", "证人", "嫌疑人", "犯罪嫌疑人",
    "共犯", "从犯", "主犯", "同案犯", "原告人", "申请人", "被申请人",
    "上诉人", "被上诉人", "申诉人", "辩护人", "代理人",
    "法定代表人", "诉讼代表人", "第三人",
    "受害人", "举报人", "报案人", "知情人",
)


@dataclass
class ComplexityFactors:
    """案件复杂度评估因子数据类.

    系统存储和管理所有复杂度评估因子的统计数值。

    Attributes:
        keyword_count: 关键法律术语数量
        sentence_count: 句子总数
        evidence_count: 证据线索数量
        people_count: 涉案相关人数
    """

    keyword_count: int = 0
    sentence_count: int = 0
    evidence_count: int = 0
    people_count: int = 0


def _count_keywords(text: str) -> int:
    """统计文本中关键法律术语的出现次数.

    对 _KEYWORD_LEGAL 中定义的每个法律术语进行子串匹配，
    长术语优先匹配以避免重复计数（如"故意伤害"优先于"故意"）。

    Args:
        text: 案件事实文本

    Returns:
        int: 匹配到的关键法律术语总数

    Example:
        >>> _count_keywords("被告人故意伤害被害人，明知其行为违法")
        4
    """
    count = 0
    remaining = text
    for keyword in sorted(_KEYWORD_LEGAL, key=len, reverse=True):
        occurrences = remaining.count(keyword)
        if occurrences > 0:
            count += occurrences
            remaining = remaining.replace(keyword, "\x00")
    return count


def _count_sentences(text: str) -> int:
    """统计文本中的句子总数.

    按中英文句子结束标点（。！？；.!?;）进行分割，
    过滤空白句子后返回有效句子数量。

    Args:
        text: 案件事实文本

    Returns:
        int: 句子总数，至少为 1

    Example:
        >>> _count_sentences("被告人认罪。法院审理。判决如下。")
        3
    """
    sentences = re.split(r"[。！？；.!?;]+", text)
    valid = [s.strip() for s in sentences if s.strip()]
    return len(valid) if valid else 1


def _count_evidence(text: str) -> int:
    """统计文本中提及的证据线索数量.

    通过匹配 _EVIDENCE_TERMS 中定义的证据相关术语进行统计。

    Args:
        text: 案件事实文本

    Returns:
        int: 证据线索数量

    Example:
        >>> _count_evidence("现场勘查发现指纹，监控录像记录了全过程")
        3
    """
    count = 0
    remaining = text
    for term in sorted(_EVIDENCE_TERMS, key=len, reverse=True):
        occurrences = remaining.count(term)
        if occurrences > 0:
            count += occurrences
            remaining = remaining.replace(term, "\x00")
    return count


def _count_people(text: str) -> int:
    """统计文本中涉及的相关人员数量.

    通过匹配 _PEOPLE_ROLE_TERMS 中定义的人员角色术语
    以及中文姓名模式（如"张某"、"李某某"）进行统计。

    为避免重复计数，角色术语采用长词优先替换策略；
    姓名模式匹配在原始文本上进行，确保不被角色替换干扰。
    同一姓名只计一次。

    Args:
        text: 案件事实文本

    Returns:
        int: 涉案人员数量

    Example:
        >>> _count_people("被告人张某与被害人李某发生冲突，证人王某作证")
        3
    """
    count = 0
    remaining = text

    for role in sorted(_PEOPLE_ROLE_TERMS, key=len, reverse=True):
        occurrences = remaining.count(role)
        if occurrences > 0:
            count += occurrences
            remaining = remaining.replace(role, "\x00")

    name_pattern = re.compile(
        r"[赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张"
        r"孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎"
        r"鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤"
        r"滕殷罗毕郝邬安常乐于时傅皮下齐康伍余元卜顾孟平黄"
        r"和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞"
        r"熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭"
        r"梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫"
        r"经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚"
        r"程嵇邢滑裴陆荣翁荀羊於惠甄麴家封芮羿储靳汲邴糜松"
        r"井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫"
        r"宁仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄"
        r"印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双"
        r"闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍卻璩桑桂濮牛寿通"
        r"边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容"
        r"向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东"
        r"欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空"
        r"曾毋沙乜养鞠须丰巢关蒯相查後荆红游竺权逯盖益桓公"
        r"万俟司马上官欧阳夏侯诸葛闻人东方赫连皇甫尉迟公羊"
        r"澹台公冶宗政濮阳淳于单于太叔申屠公孙仲孙轩辕令狐"
        r"锺离宇文长孙慕容鲜于闾丘司徒司空丌官司寇仉督子车"
        r"颛孙端木巫马公西漆雕乐正壤驷公良拓跋夹谷宰父穀梁"
        r"段干百里东郭南门呼延归海羊舌微生岳帅缑亢况後有琴"
        r"梁丘左丘东门西门商牟佘佴伯赏南宫墨哈谯笪年爱阳佟"
        r"第五言福]"
    )
    found_names: set[str] = set()
    for match in name_pattern.finditer(text):
        name_start = match.start()
        suffix_match = re.match(r"某{1,2}|某某", text[name_start + 1:])
        if suffix_match:
            full_name = text[name_start:name_start + 1 + suffix_match.end()]
            if full_name not in found_names:
                found_names.add(full_name)
                count += 1

    return count


def _compute_complexity_factors(case_text: str) -> ComplexityFactors:
    """对文本执行多维度复杂度分析，计算所有评估因子.

    依次执行关键词、句子、证据线索和涉案人数的统计，
    将结果封装为 ComplexityFactors 对象。

    Args:
        case_text: 案件事实文本

    Returns:
        ComplexityFactors: 包含所有评估因子数值的数据对象
    """
    return ComplexityFactors(
        keyword_count=_count_keywords(case_text),
        sentence_count=_count_sentences(case_text),
        evidence_count=_count_evidence(case_text),
        people_count=_count_people(case_text),
    )


def _compute_composite_score(factors: ComplexityFactors) -> float:
    r"""根据各评估因子计算加权综合复杂度分数.

    使用 AnalysisConfig 中配置的各因子权重值进行加权求和：

    .. math::
        score = keyword_count \\times w_k + sentence_count \\times w_s
              + evidence_count \\times w_e + people_count \\times w_p

    Args:
        factors: 复杂度评估因子数据对象

    Returns:
        float: 加权综合复杂度分数
    """
    return (
        factors.keyword_count * AnalysisConfig.COMPLEXITY_WEIGHT_KEYWORD
        + factors.sentence_count * AnalysisConfig.COMPLEXITY_WEIGHT_SENTENCE
        + factors.evidence_count * AnalysisConfig.COMPLEXITY_WEIGHT_EVIDENCE
        + factors.people_count * AnalysisConfig.COMPLEXITY_WEIGHT_PEOPLE
    )


def classify_complexity(case_text: str) -> ComplexityLevel:
    """基于多维度分析对案件复杂度进行分类.

    从以下四个维度评估文本复杂度：

    - **关键词数量**：文本中包含的法律术语和重要概念数量
    - **句子数量**：文本中的句子总数
    - **证据线索数**：文本中提及的证据相关线索数量
    - **涉案人数**：文本中涉及的相关人员数量

    各因子按预设权重进行加权求和得到综合分数，
    再根据分数阈值映射为中文分类标签。

    Args:
        case_text: 案件事实文本

    Returns:
        ComplexityLevel: 复杂度级别——``"simple"``（简单）、
            ``"medium"``（中等）或 ``"complex"``（复杂）

    Example:
        >>> classify_complexity("被告人故意伤害被害人，案发后自首。")
        'simple'
        >>> classify_complexity(
        ...     "被告人张某明知他人实施诈骗，仍提供银行卡用于转账，"
        ...     "银行流水显示涉案金额50万元。证人王某证实。"
        ... )
        'medium'
    """
    factors = _compute_complexity_factors(case_text)
    score = _compute_composite_score(factors)

    logger.debug(
        f"复杂度评估: keywords={factors.keyword_count}, "
        f"sentences={factors.sentence_count}, "
        f"evidence={factors.evidence_count}, "
        f"people={factors.people_count}, "
        f"composite_score={score:.1f}"
    )

    if score <= AnalysisConfig.COMPLEXITY_COMPOSITE_SIMPLE_MAX:
        return "simple"
    if score <= AnalysisConfig.COMPLEXITY_COMPOSITE_MEDIUM_MAX:
        return "medium"
    return "complex"
