"""分析管道核心模块.

V2 协议（阶段 4）：负责按"复杂度分类 → 标签抽取 → 规则匹配 →
维度1 → 维度2 → 维度3（带前置上下文）→ 档级组合 → 冲突检测
→ 结论生成"的顺序编排 LLM 调用，输出 :class:`AnalysisResultV2`。

V1 协议（向后兼容）：保留原 0-10 分评分管道 ``single_pass_analysis`` 、
``multi_dimension_analysis`` 与 ``self_consistency_analysis``，旧调用方
仍可使用。
"""

import asyncio
import json
import re
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from loguru import logger

from app.config import AnalysisConfig, settings
from app.database import get_async_db_session
from app.models.knowledge_entry import EntryStatus
from app.services.analysis_service import generate_conclusion
from app.services.conflict_detector import Conflict, detect_conflicts
from app.services.knowledge import ensure_fts_table, search_entries
from app.services.ollama_client import _extract_think_content, call_ollama_with_retry
from app.services.prompt import (
    ANALYSIS_SYSTEM_PROMPT,
    DIMENSION1_PROMPT,
    DIMENSION2_PROMPT,
    DIMENSION3_PROMPT,
    V2_DIMENSION1_PROMPT,
    V2_DIMENSION2_PROMPT,
    V2_DIMENSION3_PROMPT,
)
from app.services.rule_engine import Rule, load_rules
from app.services.tag_extractor import TagMatch, extract_tags
from app.services.analysis_helpers import combine_tiers
from app.types.analysis import (
    AnalysisResult,
    GroundTruthAnalysis,
)
from app.types.analysis_v2 import (
    AnalysisResultV2,
    FinalVerdict,
    PipelineMeta,
    TierEnum,
)
from app.utils.common import sanitize_json_string
from app.utils.monitoring import ANALYSIS_COUNTER, ANALYSIS_DURATION


ComplexityLevel = Literal["simple", "medium", "complex"]

_DEFAULT_SCORE = 5.0
_MAX_CONTEXT_LENGTH = 500
_MIN_SAMPLES_FOR_STDEV = 2
_SUMMARY_SNIPPET_LENGTH = 200
_MIN_REMAINING = 20
_MAX_SNIPPET_LENGTH = 1000

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


def _build_default_dimension() -> dict[str, Any]:
    """构建默认维度分析结果.

    Returns:
        dict: 包含默认评分和理由的维度结果
    """
    return {
        "score": AnalysisConfig.DEFAULT_DIMENSION_SCORE,
        "reasoning": AnalysisConfig.DEFAULT_REASONING,
    }


def _build_default_analysis_result() -> AnalysisResult:
    """构建预设的默认分析结果，用于 JSON 解析失败时的降级返回.

    Returns:
        AnalysisResult: 包含完整三维度默认值的结果字典
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
        >>> robust_json_parse('```json\\\\n{"key": "value"}\\\\n```')
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


async def single_pass_analysis(
    case_text: str,
    mode: str = "auto",
    temperature: float = AnalysisConfig.OLLAMA_DEFAULT_TEMPERATURE,
    legal_knowledge: str = "",
) -> AnalysisResult:
    """单通道分析（适用于简单案件）.

    在单次 LLM 调用中完成所有维度分析。

    Args:
        case_text: 案件事实文本
        mode: 分析模式
        temperature: 生成温度
        legal_knowledge: 注入的检索知识（可选）

    Returns:
        AnalysisResult: 包含三维度分析结果的字典
    """
    logger.info(f"使用单通道分析模式 ({mode}), temperature={temperature}")
    system_prompt: str = ANALYSIS_SYSTEM_PROMPT.replace("{legal_knowledge}", legal_knowledge)
    user_prompt: str = f"请对以下案件进行三维度分析：\n\n{case_text}"

    response: str = await call_ollama_with_retry(
        user_prompt, system_prompt=system_prompt, temperature=temperature
    )
    reasoning_text, _ = _extract_think_content(response)
    result: AnalysisResult = robust_json_parse(sanitize_json_string(response))
    if reasoning_text:
        result["reasoning_process"] = reasoning_text
    return result


async def _single_dimension_analysis(
    case_text: str,
    system_prompt: str,
    _dimension_name: str,
    user_prompt: str | None = None,
    temperature: float = AnalysisConfig.OLLAMA_DEFAULT_TEMPERATURE,
) -> dict[str, Any]:
    """单个维度的独立分析.

    对单个维度调用 LLM，并使用 robust_json_parse 处理响应。
    异常会向上传播，由调用方（_timed_dimension_analysis）统一捕获并记录。

    Args:
        case_text: 案件事实文本（当 user_prompt 为 None 时作为用户消息）
        system_prompt: 当前维度的系统提示词
        dimension_name: 维度名称（用于日志记录）
        user_prompt: 自定义用户消息，为 None 时使用 case_text
        temperature: 生成温度

    Returns:
        dict: 该维度的分析结果字典

    Raises:
        Exception: LLM 调用失败时向上传播异常
    """
    prompt: str = user_prompt if user_prompt is not None else case_text
    response = await call_ollama_with_retry(
        prompt, system_prompt=system_prompt, temperature=temperature
    )
    reasoning_text, _ = _extract_think_content(response)
    cleaned = sanitize_json_string(response)
    result = robust_json_parse(
        cleaned,
        default=_build_default_dimension(),
    )
    if reasoning_text:
        result["reasoning_process"] = reasoning_text
    return result


async def _timed_dimension_analysis(
    case_text: str,
    system_prompt: str,
    dimension_name: str,
    user_prompt: str | None = None,
    temperature: float = AnalysisConfig.OLLAMA_DEFAULT_TEMPERATURE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """带性能计时的单维度分析包装器.

    在 _single_dimension_analysis 基础上增加精确的性能计时
    和详细的异常信息记录。

    Args:
        case_text: 案件事实文本（当 user_prompt 为 None 时作为用户消息）
        system_prompt: 当前维度的系统提示词
        dimension_name: 维度名称
        user_prompt: 自定义用户消息，为 None 时使用 case_text
        temperature: 生成温度

    Returns:
        tuple: (维度分析结果字典, 执行元数据字典)
    """
    start_time: float = time.perf_counter()
    start_ts: str = datetime.now(UTC).isoformat()
    status: str = "success"
    error_info: dict[str, str] = {}

    try:
        result: dict[str, Any] = await _single_dimension_analysis(
            case_text, system_prompt, dimension_name,
            user_prompt=user_prompt, temperature=temperature,
        )
    except Exception as exc:  # noqa: BLE001
        result = _build_default_dimension()
        status = "failed"
        error_info = {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "error_time": datetime.now(UTC).isoformat(),
        }
        logger.error(
            f"{dimension_name} 分析异常: "
            f"类型={type(exc).__name__}, "
            f"错误={exc}, "
            f"时间={error_info['error_time']}"
        )

    end_time: float = time.perf_counter()
    duration_ms: float = round((end_time - start_time) * 1000, 2)

    timing: dict[str, Any] = {
        "status": status,
        "duration_ms": duration_ms,
        "start_time": start_ts,
        "end_time": datetime.now(UTC).isoformat(),
        **error_info,
    }
    logger.info(
        f"{dimension_name} 执行完成: 状态={status}, 耗时={duration_ms}ms"
    )
    return result, timing


def _build_prior_analysis_context(
    dim1_result: dict[str, Any],
    dim2_result: dict[str, Any],
) -> str:
    """将维度1（事实审查）和维度2（模式匹配）的结果摘要为维度3可用的上下文.

    Args:
        dim1_result: 维度1的事实审查分析结果
        dim2_result: 维度2的模式匹配分析结果

    Returns:
        str: 格式化的前置分析文本摘要（不超过500字）
    """
    parts: list[str] = []

    dim1_score: float = dim1_result.get("score", _DEFAULT_SCORE)
    dim1_reasoning: str = dim1_result.get("reasoning", "无分析结果")
    dim1_indicators: list[str] = dim1_result.get("key_indicators", [])

    if dim1_reasoning == "自动分析结果" and dim1_score == _DEFAULT_SCORE:
        parts.append("【事实审查维度分析失败，该维度无法提供有效分析，请独立判断】")
    else:
        parts.append("【事实审查维度结论】")
        parts.append(f"评分：{dim1_score}/10")
        if dim1_indicators:
            parts.append(f"关键指标：{'、'.join(dim1_indicators[:5])}")
        parts.append(f"分析摘要：{dim1_reasoning[:200]}")

    dim2_score: float = dim2_result.get("score", _DEFAULT_SCORE)
    dim2_reasoning: str = dim2_result.get("reasoning", "无分析结果")
    dim2_pattern: str = dim2_result.get("pattern_match", "无匹配结果")

    if dim2_reasoning == "自动分析结果" and dim2_score == _DEFAULT_SCORE:
        parts.append("【模式匹配维度分析失败，该维度无法提供有效分析，请独立判断】")
    else:
        parts.append("")
        parts.append("【模式匹配维度结论】")
        parts.append(f"评分：{dim2_score}/10")
        parts.append(f"模式匹配：{dim2_pattern}")
        parts.append(f"分析摘要：{dim2_reasoning[:200]}")

    context: str = "\n".join(parts)

    if len(context) > _MAX_CONTEXT_LENGTH:
        context = context[:_MAX_CONTEXT_LENGTH - 3] + "..."

    return context


async def multi_dimension_analysis(
    case_text: str,
    mode: str = "auto",  # noqa: ARG001
    temperature: float = AnalysisConfig.OLLAMA_DEFAULT_TEMPERATURE,
    legal_knowledge: str = "",
) -> AnalysisResult:
    """多维度分析（适用于复杂案件）.

    采用两阶段推理策略：
    第一阶段：并行执行维度1（事实审查）和维度2（模式匹配）
    第二阶段：将维度1和维度2的结果摘要注入维度3（矛盾分析），
              使其能基于前置分析结果进行更有依据的矛盾识别。

    各维度异常隔离，互不干扰。任一维度失败时自动使用默认值降级。
    同时记录各维度的执行状态、耗时和异常详情。

    Args:
        case_text: 案件事实文本
        mode: 分析模式
        temperature: 生成温度
        legal_knowledge: 注入的检索知识（可选）

    Returns:
        AnalysisResult: 包含三维度分析结果、量刑建议和各维度执行元数据的字典
    """
    logger.info(f"使用多维度两阶段分析模式, temperature={temperature}")

    dim1_prompt: str = DIMENSION1_PROMPT.replace("{legal_knowledge}", legal_knowledge)
    dim2_prompt: str = DIMENSION2_PROMPT.replace("{legal_knowledge}", "")

    # ------------------------------------------------------------------
    # 第一阶段：并行执行维度1（事实审查）和维度2（模式匹配）
    # ------------------------------------------------------------------
    phase1_dim_names: list[str] = ["dimension1", "dimension2"]
    phase1_results = await asyncio.gather(
        _timed_dimension_analysis(case_text, dim1_prompt, "维度1", temperature=temperature),
        _timed_dimension_analysis(case_text, dim2_prompt, "维度2", temperature=temperature),
        return_exceptions=True,
    )

    dimension_results: dict[str, dict[str, Any]] = {}
    dimension_meta: dict[str, dict[str, Any]] = {}

    for dim_name, gather_result in zip(
        phase1_dim_names, phase1_results, strict=True
    ):
        if isinstance(gather_result, BaseException):
            error_time: str = datetime.now(UTC).isoformat()
            dimension_results[dim_name] = _build_default_dimension()
            dimension_meta[dim_name] = {
                "status": "failed",
                "duration_ms": 0.0,
                "start_time": "",
                "end_time": error_time,
                "error": str(gather_result),
                "error_type": type(gather_result).__name__,
                "error_time": error_time,
            }
            logger.error(
                f"{dim_name} 分析异常: "
                f"类型={type(gather_result).__name__}, "
                f"错误={gather_result}, "
                f"时间={error_time}"
            )
        else:
            dim_result, timing = gather_result
            dimension_results[dim_name] = dim_result
            dimension_meta[dim_name] = timing

    # ------------------------------------------------------------------
    # 构建前置分析上下文（供维度3使用）
    # ------------------------------------------------------------------
    context: str = _build_prior_analysis_context(
        dimension_results.get("dimension1", _build_default_dimension()),
        dimension_results.get("dimension2", _build_default_dimension()),
    )

    # ------------------------------------------------------------------
    # 第二阶段：串行执行维度3（矛盾分析），注入前置分析结果
    # ------------------------------------------------------------------
    enriched_prompt: str = DIMENSION3_PROMPT.replace("{legal_knowledge}", "").format(
        prior_analysis=context,
        case_text=case_text,
    )
    dim3_result: dict[str, Any]
    dim3_timing: dict[str, Any]
    dim3_result, dim3_timing = await _timed_dimension_analysis(
        case_text, enriched_prompt, "维度3", temperature=temperature,
    )
    dimension_results["dimension3"] = dim3_result
    dimension_meta["dimension3"] = dim3_timing

    ground_truth: GroundTruthAnalysis = {
        "dimension1": dimension_results["dimension1"],
        "dimension2": dimension_results["dimension2"],
        "dimension3": dimension_results["dimension3"],
    }
    dim1: dict[str, Any] = dimension_results["dimension1"]
    key_indicators: list[str] = dim1.get("key_indicators", ["未知"])
    subjective_knowledge: str = key_indicators[0] if key_indicators else "未知"
    sentence_suggestion: str = dim1.get("sentence_suggestion", "待定")

    return {
        "ground_truth_analysis": ground_truth,
        "subjective_knowledge": subjective_knowledge,
        "sentence": sentence_suggestion,
        "fallback": False,
        "timestamp": datetime.now(UTC).isoformat(),
        "dimension_meta": dimension_meta,
    }


async def self_consistency_analysis(  # noqa: PLR0912, PLR0915
    case_text: str,
    mode: str = "auto",
    n_samples: int = 3,
    sample_temperature: float = 0.5,
    legal_knowledge: str = "",
) -> AnalysisResult:
    """Self-Consistency 多次采样验证分析.

    通过多次独立采样 LLM 分析结果，计算评分中位数和一致性指标，
    有效降低单次推理的随机偏差，尤其适用于边界案例。

    流程：
    1. 循环调用 n_samples 次分析（根据 mode 选择单通道或多维度）
       - 每次使用 sample_temperature 而非默认温度以引入多样性
    2. 收集所有采样结果
    3. 对每个维度的 score 取中位数作为最终分数
    4. 计算每个维度的评分一致性（标准差）
    5. 合并 reasoning 文本（选取最接近中位数的采样结果）
    6. 计算整体置信度（基于三个维度的一致性综合评估）

    Args:
        case_text: 案件事实文本
        mode: 分析模式
        n_samples: 采样次数
        sample_temperature: 采样温度（高于默认值以引入多样性）
        legal_knowledge: 注入的检索知识（可选）

    Returns:
        AnalysisResult: 包含 SC 置信度指标的分析结果
    """
    logger.info(
        f"Self-Consistency 分析: samples={n_samples}, "
        f"temperature={sample_temperature}, mode={mode}"
    )

    dim_names: list[str] = ["dimension1", "dimension2", "dimension3"]
    all_results: list[AnalysisResult] = []
    sample_scores_list: list[dict[str, Any]] = []

    for i in range(n_samples):
        logger.info(f"Self-Consistency 采样 {i + 1}/{n_samples}")
        try:
            if mode == "single":
                result = await single_pass_analysis(
                    case_text, mode=mode, temperature=sample_temperature,
                    legal_knowledge=legal_knowledge,
                )
            elif mode == "multi":
                result = await multi_dimension_analysis(
                    case_text, mode=mode, temperature=sample_temperature,
                    legal_knowledge=legal_knowledge,
                )
            else:
                complexity: ComplexityLevel = classify_complexity(case_text)
                if complexity == "simple":
                    result = await single_pass_analysis(
                        case_text, mode=mode, temperature=sample_temperature,
                        legal_knowledge=legal_knowledge,
                    )
                else:
                    result = await multi_dimension_analysis(
                        case_text, mode=mode, temperature=sample_temperature,
                        legal_knowledge=legal_knowledge,
                    )

            all_results.append(result)

            gta = result.get("ground_truth_analysis", {}) or {}
            sample_scores = {}
            for dim in dim_names:
                dim_data = gta.get(dim, {}) or {}
                sample_scores[dim] = dim_data.get("score", 5.0)
            sample_scores_list.append(sample_scores)

        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"Self-Consistency 采样 {i + 1} 失败: {exc}"
            )
            continue

    if not all_results:
        logger.warning("Self-Consistency 所有采样均失败，使用默认降级结果")
        result = _build_default_analysis_result()
        result["confidence"] = 0.0
        result["confidence_details"] = {}
        result["num_samples"] = 0
        result["sample_scores"] = []
        return result

    actual_samples = len(all_results)

    dim_scores: dict[str, list[float]] = {d: [] for d in dim_names}
    dim_reasonings: dict[str, list[str]] = {d: [] for d in dim_names}

    for sample in sample_scores_list:
        for dim in dim_names:
            score = sample.get(dim, 5.0)
            dim_scores[dim].append(score)

    for result in all_results:
        gta = result.get("ground_truth_analysis", {}) or {}
        for dim in dim_names:
            dim_data = gta.get(dim, {}) or {}
            reasoning = dim_data.get("reasoning", "")
            dim_reasonings[dim].append(reasoning)

    final_scores: dict[str, float] = {}
    dim_std: dict[str, float] = {}
    dim_confidence: dict[str, float] = {}
    confidence_details: dict[str, Any] = {}

    for dim in dim_names:
        scores = dim_scores[dim]
        if scores:
            final_scores[dim] = statistics.median(scores)
        else:
            final_scores[dim] = 5.0

        if len(scores) >= _MIN_SAMPLES_FOR_STDEV:
            dim_std[dim] = statistics.stdev(scores)
        else:
            dim_std[dim] = 0.0

        max_possible_std = 5.0
        conf = max(0.0, 1.0 - dim_std[dim] / max_possible_std)
        dim_confidence[dim] = round(conf, 4)

        confidence_details[dim] = {
            "scores": scores,
            "median": round(final_scores[dim], 2),
            "mean": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "std_dev": round(dim_std[dim], 4),
            "min": round(min(scores), 2) if scores else 0.0,
            "max": round(max(scores), 2) if scores else 0.0,
            "confidence": dim_confidence[dim],
        }

    overall_confidence = round(
        sum(dim_confidence.values()) / len(dim_confidence), 4
    )

    best_result = all_results[0]
    best_deviation = float("inf")
    for result in all_results:
        gta = result.get("ground_truth_analysis", {}) or {}
        deviation = 0.0
        for dim in dim_names:
            dim_data = gta.get(dim, {}) or {}
            score = dim_data.get("score", 5.0)
            deviation += abs(score - final_scores[dim])
        if deviation < best_deviation:
            best_deviation = deviation
            best_result = result

    final_result: AnalysisResult = dict(best_result)
    gta = final_result.get("ground_truth_analysis")
    if gta:
        for dim in dim_names:
            if dim in gta:
                dim_copy = dict(gta[dim])
                dim_copy["score"] = final_scores[dim]
                gta[dim] = dim_copy

    final_result["confidence"] = overall_confidence
    final_result["confidence_details"] = confidence_details
    final_result["num_samples"] = actual_samples
    final_result["sample_scores"] = sample_scores_list

    logger.info(
        f"Self-Consistency 完成: samples={actual_samples}, "
        f"confidence={overall_confidence}"
    )

    return final_result


async def _retrieve_neo4j_knowledge(
    case_text: str,
    max_entries: int = 5,
) -> list[dict[str, str]] | None:
    """从 Neo4j 图数据库中检索与案件相关的法律知识.

    策略：

    1. 若 ``settings.NEO4J_URI`` 为空，直接返回 ``None``，由调用方降级到 SQLite FTS。
    2. 尝试调用 Neo4j 驱动执行关键词查询；任何异常（连接失败、驱动不可用等）
       均返回 ``None``，由调用方降级。

    Returns:
        命中的知识条目摘要列表；若 Neo4j 未配置或不可用则返回 ``None``.
    """
    if settings.NEO4J_URI is None:
        return None

    try:
        # 延迟导入避免无 Neo4j 环境下拉起驱动
        from neo4j import GraphDatabase  # type: ignore
    except ImportError:
        logger.warning("Neo4j 驱动未安装，回退到 SQLite FTS")
        return None

    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    except Exception:  # noqa: BLE001
        logger.warning("Neo4j 驱动初始化失败，回退到 SQLite FTS", exc_info=True)
        return None

    keywords = [kw for kw in _KEYWORD_LEGAL if kw in case_text][:3]
    if not keywords:
        driver.close()
        return []

    query = (
        "MATCH (n:KnowledgeEntry) "
        "WHERE any(k IN $keywords WHERE n.title CONTAINS k OR n.summary CONTAINS k) "
        "RETURN n.title AS title, n.summary AS summary "
        "LIMIT $limit"
    )
    try:
        with driver.session() as session:
            result = session.run(query, keywords=keywords, limit=max_entries)
            records = [dict(record) for record in result]
    except Exception:  # noqa: BLE001
        logger.warning("Neo4j 查询失败，回退到 SQLite FTS", exc_info=True)
        driver.close()
        return None
    finally:
        driver.close()

    entries: list[dict[str, str]] = []
    for r in records:
        title = (r.get("title") or "").strip()
        summary = (r.get("summary") or "").strip()
        if not title:
            continue
        entries.append({"title": title, "summary": summary})
    return entries


async def _retrieve_legal_knowledge(
    case_text: str,
    max_entries: int = 5,
) -> tuple[str, list[dict[str, str]]]:
    """从知识库中检索与案件相关的法律知识.

    检索优先级：**Neo4j > SQLite FTS > 内存关键词匹配**。

    1. **Neo4j**：若 ``settings.NEO4J_URI`` 已配置且驱动可用，优先使用 Neo4j 检索。
    2. **SQLite FTS**：若 Neo4j 未配置或不可用，回退到 SQLite FTS 全文搜索
       （基于 :func:`ensure_fts_table` + :func:`search_entries`）。
    3. **内存关键词匹配**：若 SQLite FTS 仍未命中，回退到 ``_KEYWORD_LEGAL``
       在案件文本中的字面匹配并构造最小摘要。

    Args:
        case_text: 案件文本
        max_entries: 最大返回条目数

    Returns:
        tuple: (格式化的相关知识文本, 知识条目摘要列表).
              三级兜底均无命中时返回 ("", [])。
    """
    try:
        # 1) 尝试 Neo4j
        neo4j_entries = await _retrieve_neo4j_knowledge(case_text, max_entries)
        if neo4j_entries:
            logger.info(f"Neo4j 命中 {len(neo4j_entries)} 条")
            return _format_knowledge_entries(neo4j_entries)

        # 2) 回退到 SQLite FTS
        keywords = [kw for kw in _KEYWORD_LEGAL if kw in case_text]
        if keywords:
            async with get_async_db_session() as db:
                await ensure_fts_table(db)
                results = await search_entries(
                    db,
                    " ".join(keywords[:3]),
                    status=EntryStatus.active,
                    limit=max_entries,
                )
            if results:
                logger.info(f"SQLite FTS 命中 {len(results)} 条")
                return _format_knowledge_entries(
                    [
                        {
                            "title": r.get("title", ""),
                            "summary": r.get("summary", "") or "",
                        }
                        for r in results
                    ]
                )

        # 3) 内存关键词兜底：基于 _KEYWORD_LEGAL 命中给出最简摘要
        if keywords:
            logger.info(f"使用内存关键词兜底: {keywords[:3]}")
            stub_entries = [
                {
                    "title": f"法律关键词命中：{kw}",
                    "summary": f"案件文本中检测到关键词 {kw}，建议结合相关法条进一步分析。",
                }
                for kw in keywords[:max_entries]
            ]
            return _format_knowledge_entries(stub_entries)

        logger.info("案件文本中未匹配到法律关键词，跳过知识检索")
        return "", []

    except Exception:  # noqa: BLE001
        logger.warning("知识检索异常，跳过知识注入", exc_info=True)
        return "", []


def _format_knowledge_entries(
    entries: list[dict[str, str]],
) -> tuple[str, list[dict[str, str]]]:
    """将知识条目列表格式化为提示词注入片段.

    Args:
        entries: 知识条目列表，每项含 title 与 summary.

    Returns:
        tuple: (格式化的相关知识文本, 知识条目摘要列表).
    """
    if not entries:
        return "", []

    knowledge_parts = ["【相关知识】"]
    total_len = 0
    entries_info: list[dict[str, str]] = []

    for entry in entries:
        title = (entry.get("title") or "").strip()
        summary = (entry.get("summary") or "").strip()
        if not title:
            continue
        snippet = (
            summary[:_SUMMARY_SNIPPET_LENGTH]
            if len(summary) > _SUMMARY_SNIPPET_LENGTH
            else summary
        )
        entry_text = f"[{title}] {snippet}" if snippet else f"[{title}]"

        if total_len + len(entry_text) > _MAX_SNIPPET_LENGTH:
            remaining = _MAX_SNIPPET_LENGTH - total_len
            if remaining > _MIN_REMAINING:
                entry_text = entry_text[:remaining] + "..."
                knowledge_parts.append(entry_text)
            break

        knowledge_parts.append(entry_text)
        total_len += len(entry_text)
        entries_info.append({"title": title, "summary": snippet})

    if not entries_info:
        return "", []
    return "\n\n".join(knowledge_parts), entries_info


@ANALYSIS_DURATION.time()
async def analyze_pipeline(
    case_text: str,
    mode: str = "auto",
) -> AnalysisResult:
    """主分析管道入口.

    根据案件复杂度自动选择单通道或多维度分析策略。

    Args:
        case_text: 案件事实文本
        mode: 分析模式（"auto"、"single"、"multi"）

    Returns:
        AnalysisResult: 分析结果字典，包含时间戳和回退标志
    """
    try:
        legal_knowledge, knowledge_entries = await _retrieve_legal_knowledge(case_text)
        knowledge_used: bool = bool(legal_knowledge)

        if legal_knowledge:
            logger.info(f"知识注入启用: {len(knowledge_entries)} 条知识条目")

        if AnalysisConfig.SC_ENABLED and mode != "single":
            logger.info(
                f"启用 Self-Consistency 多次采样: "
                f"samples={AnalysisConfig.SC_NUM_SAMPLES}, "
                f"temperature={AnalysisConfig.SC_TEMPERATURE}"
            )
            result = await self_consistency_analysis(
                case_text, mode=mode,
                n_samples=AnalysisConfig.SC_NUM_SAMPLES,
                sample_temperature=AnalysisConfig.SC_TEMPERATURE,
                legal_knowledge=legal_knowledge,
            )
            result["fallback"] = False
            result["timestamp"] = datetime.now(UTC).isoformat()
            result["knowledge_used"] = knowledge_used
            result["knowledge_entries"] = knowledge_entries
            return result

        complexity: ComplexityLevel = classify_complexity(case_text)
        logger.info(f"自动模式: 复杂度='{complexity}'")

        if mode == "single" or (
            mode == "auto" and complexity == "simple"
        ):
            logger.info("推理模式: single")
            result: AnalysisResult = await single_pass_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )
        elif mode == "multi" or (
            mode == "auto" and complexity in ("medium", "complex")
        ):
            logger.info("推理模式: multi")
            result = await multi_dimension_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )
        else:
            result = await single_pass_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )

        if "ground_truth_analysis" not in result:
            result["ground_truth_analysis"] = {
                "dimension1": _build_default_dimension(),
                "dimension2": _build_default_dimension(),
                "dimension3": _build_default_dimension(),
            }

        result["fallback"] = result.get("fallback", False)
        result["timestamp"] = datetime.now(UTC).isoformat()
        result["knowledge_used"] = knowledge_used
        result["knowledge_entries"] = knowledge_entries

        ANALYSIS_COUNTER.labels(mode=mode, status="success").inc()
        return result
    except Exception:
        ANALYSIS_COUNTER.labels(mode=mode, status="error").inc()
        raise


# ===========================================================================
# 阶段 4 — V2 协议：标签抽取 / 规则匹配 / 档级组合 / 结论生成
# ===========================================================================


# 规则注入时取的最大规则数
_V2_RULE_INJECTION_TOP_N: int = 10

# 标签注入时取的最大标签数
_V2_TAG_INJECTION_TOP_N: int = 12

# 维度间档级上下文最大字符数
_V2_PRIOR_CONTEXT_MAX: int = 600

# V2 维度 prompt 默认温度
_V2_DEFAULT_TEMPERATURE: float = 0.2

# 缺省 tier 字符串
_V2_DEFAULT_TIER: str = TierEnum.T2.value

# 缺省最终量刑
_V2_DEFAULT_SENTENCE: str = "待定"

# 缺省主观明知
_V2_DEFAULT_KNOWLEDGE: str = "未知"

# 阶段名常量（用于 pipeline_meta 与日志）
_STAGE_COMPLEXITY: str = "complexity_classification"
_STAGE_KNOWLEDGE: str = "knowledge_retrieval"
_STAGE_TAGS: str = "tag_extraction"
_STAGE_RULES: str = "rule_matching"
_STAGE_DIM1: str = "dimension1"
_STAGE_DIM2: str = "dimension2"
_STAGE_DIM3: str = "dimension3"
_STAGE_COMBINE: str = "tier_combination"
_STAGE_CONFLICTS: str = "conflict_detection"
_STAGE_CONCLUSION: str = "conclusion_generation"


# ---------------------------------------------------------------------------
# V2 辅助：构造默认维度结果 / 兜底结果
# ---------------------------------------------------------------------------


def _build_default_v2_dimension(
    dim_name: str,
    fallback_reason: str = "",
) -> dict[str, Any]:
    """构造 V2 协议的默认维度结果.

    当某维度 LLM 调用失败或 JSON 解析失败时使用.
    """
    return {
        "tier": _V2_DEFAULT_TIER,
        "reasoning": (
            f"维度 {dim_name} 分析失败，使用默认档级 {_V2_DEFAULT_TIER}。"
            + (f"原因：{fallback_reason}" if fallback_reason else "")
        ),
        "key_indicators": [],
        "triggered_rules": [],
        "fallback": True,
    }


def _build_default_v2_analysis_result(
    case_text: str,
    failed_stage: str = "",
    error: str = "",
) -> AnalysisResultV2:
    """构造 V2 协议下的兜底分析结果.

    适用于整个管道在第一阶段就崩溃的极端情况.
    """
    default_dim: dict[str, Any] = _build_default_v2_dimension("全维度")
    verdict: FinalVerdict = combine_tiers(
        _V2_DEFAULT_TIER,
        _V2_DEFAULT_TIER,
        _V2_DEFAULT_TIER,
        rule_hits=[],
    )
    return {
        "version": "v2",
        "subjective_knowledge": _V2_DEFAULT_KNOWLEDGE,
        "sentence": _V2_DEFAULT_SENTENCE,
        "court": "基层人民法院",
        "dimension1": {**default_dim, "key_indicators": []},
        "dimension2": {**default_dim, "pattern_match": ""},
        "dimension3": {**default_dim, "contradictions": []},
        "final_verdict": verdict,
        "triggered_rule_ids": [],
        "matched_tag_ids": [],
        "conflicts": [],
        "fallback": True,
        "failed_stage": failed_stage or "pipeline",
        "timestamp": datetime.now(UTC).isoformat(),
        "pipeline_meta": {
            "stage_durations_ms": {},
            "stage_status": {},
            "failed_stage": failed_stage or "pipeline",
        },
        "disclaimer": (
            "本结论由系统兜底生成，LLM 调用失败，仅作辅助参考。"
        ),
    }


# ---------------------------------------------------------------------------
# V2 辅助：标签 / 规则格式化
# ---------------------------------------------------------------------------


def _format_tag_candidates(tags: list[Any] | None) -> str:
    """把 tag 元数据格式化为 prompt 注入片段（候选列表）."""
    if not tags:
        return "（无候选标签）"
    lines: list[str] = []
    for t in tags:
        if isinstance(t, dict):
            tag_id = t.get("tag_id", "?")
            name = t.get("name", "")
            category = t.get("category", "")
            extraction_hints = t.get("extraction_hints", [])
        else:
            tag_id = getattr(t, "tag_id", "?")
            name = getattr(t, "name", "")
            category = getattr(t, "category", "")
            extraction_hints = getattr(t, "extraction_hints", [])
        hints_str = "、".join(extraction_hints or []) or "—"
        lines.append(f"- {tag_id} {name}（{category}）| 提示词：{hints_str}")
    return "\n".join(lines)


def _format_rule_candidates(rules: list[Rule] | None) -> str:
    """把 Rule 列表格式化为 prompt 注入片段（候选列表）."""
    if not rules:
        return "（无候选规则）"
    lines: list[str] = []
    for r in rules:
        weight = f"{r.weight:.2f}" if isinstance(r.weight, (int, float)) else "n/a"
        conclusion = (r.conclusion or "").strip()[:80]
        conditions = (r.conditions or "").strip()[:120]
        lines.append(
            f"- {r.rule_id} {r.name} (weight={weight})\n"
            f"   条件：{conditions}\n"
            f"   结论：{conclusion}"
        )
    return "\n".join(lines)


def _format_matched_tags_for_prompt(matches: list[TagMatch]) -> str:
    """把已抽取的 TagMatch 列表格式化为 prompt 注入片段."""
    if not matches:
        return "（未抽取到任何事实标签）"
    lines: list[str] = []
    for m in matches[:_V2_TAG_INJECTION_TOP_N]:
        conf = f"{m.confidence:.2f}" if isinstance(m.confidence, (int, float)) else "n/a"
        text = (m.matched_text or "").strip()[:60]
        lines.append(f"- {m.tag_id}（{m.match_type}，conf={conf}）：{text}")
    return "\n".join(lines)


def _format_matched_rules_for_prompt(rules: list[Rule]) -> str:
    """把命中的 Rule 列表格式化为 prompt 注入片段."""
    if not rules:
        return "（未命中任何具体规则）"
    lines: list[str] = []
    for r in rules[:_V2_RULE_INJECTION_TOP_N]:
        weight = f"{r.weight:.2f}" if isinstance(r.weight, (int, float)) else "n/a"
        conclusion = (r.conclusion or "").strip()[:80]
        article = (r.article or "").strip()
        suffix = f" | {article}" if article else ""
        lines.append(f"- {r.rule_id} {r.name} (weight={weight}): {conclusion}{suffix}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# V2 辅助：单维度 tier 抽取
# ---------------------------------------------------------------------------


def _extract_tier_from_v2_response(result: dict[str, Any]) -> str:
    """从 V2 维度 LLM 响应中抽取档级.

    支持 ``tier`` 字段、``final_tier`` 字段或嵌套字段; 失败时返回 T2.
    """
    if not isinstance(result, dict):
        return _V2_DEFAULT_TIER

    # 常见字段名
    for key in ("tier", "final_tier", "档级", "tier_value"):
        if key in result:
            return TierEnum.coerce(result[key]).value

    # 嵌套字段
    gta = result.get("ground_truth_analysis")
    if isinstance(gta, dict):
        for dim in ("dimension1", "dimension2", "dimension3"):
            d = gta.get(dim)
            if isinstance(d, dict) and "tier" in d:
                return TierEnum.coerce(d["tier"]).value

    return _V2_DEFAULT_TIER


def _build_v2_dimension_result(
    dim_name: str,
    raw_result: dict[str, Any],
    fallback_used: bool = False,
) -> dict[str, Any]:
    """把 LLM 返回的 dict 转换为 V2 维度结果结构.

    适配 LLM 偶尔输出 ``{tier, reasoning, key_indicators, triggered_rules}``
    或带其他多余字段的情况.
    """
    tier = _extract_tier_from_v2_response(raw_result)
    reasoning = raw_result.get("reasoning") or raw_result.get("analysis") or ""
    if not isinstance(reasoning, str):
        reasoning = str(reasoning)

    # 触发规则
    triggered_raw = raw_result.get("triggered_rules", [])
    if not isinstance(triggered_raw, list):
        triggered_raw = []
    triggered_rules: list[str] = [
        str(x).strip() for x in triggered_raw if str(x).strip()
    ]

    base: dict[str, Any] = {
        "tier": tier,
        "reasoning": reasoning,
        "triggered_rules": triggered_rules,
        "fallback": fallback_used,
    }

    if dim_name == "dimension1":
        indicators = raw_result.get("key_indicators", [])
        if not isinstance(indicators, list):
            indicators = []
        base["key_indicators"] = [str(x) for x in indicators][:10]
    elif dim_name == "dimension2":
        pattern = raw_result.get("pattern_match", "")
        base["pattern_match"] = str(pattern) if pattern else ""
    elif dim_name == "dimension3":
        contradictions = raw_result.get("contradictions", [])
        if not isinstance(contradictions, list):
            contradictions = []
        base["contradictions"] = [str(x) for x in contradictions][:10]

    return base


# ---------------------------------------------------------------------------
# V2 辅助：构造 V2 维度 prompt
# ---------------------------------------------------------------------------


def _format_v2_dimension1_prompt(
    *,
    case_text: str,
    matched_tags_text: str,
    triggered_rules_text: str,
    legal_knowledge: str,
) -> str:
    return V2_DIMENSION1_PROMPT.format(
        matched_tags=matched_tags_text,
        triggered_rules=triggered_rules_text,
        legal_knowledge=legal_knowledge or "（无相关检索知识）",
        case_text=case_text,
    )


def _format_v2_dimension2_prompt(
    *,
    case_text: str,
    matched_tags_text: str,
    triggered_rules_text: str,
    legal_knowledge: str,
) -> str:
    return V2_DIMENSION2_PROMPT.format(
        matched_tags=matched_tags_text,
        triggered_rules=triggered_rules_text,
        legal_knowledge=legal_knowledge or "（无相关检索知识）",
        case_text=case_text,
    )


def _format_v2_dimension3_prompt(
    *,
    case_text: str,
    matched_tags_text: str,
    triggered_rules_text: str,
    legal_knowledge: str,
    prior_dim1_text: str,
    prior_dim2_text: str,
) -> str:
    return V2_DIMENSION3_PROMPT.format(
        prior_dim1=prior_dim1_text,
        prior_dim2=prior_dim2_text,
        matched_tags=matched_tags_text,
        triggered_rules=triggered_rules_text,
        legal_knowledge=legal_knowledge or "（无相关检索知识）",
        case_text=case_text,
    )


# ---------------------------------------------------------------------------
# V2 辅助：V2 标签抽取（关键词 + 可选 LLM）
# ---------------------------------------------------------------------------


async def _extract_tags_v2(
    case_text: str,
    rules: list[Rule] | None = None,
) -> list[TagMatch]:
    """V2 协议的标签抽取（先走关键词，必要时 LLM 兜底）.

    复用 :func:`extract_tags` 的实现；失败时返回空列表，确保不阻断后续流程.
    """
    try:
        return extract_tags(case_text, rules=rules or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"V2 标签抽取异常: {exc}")
        return []


# ---------------------------------------------------------------------------
# V2 辅助：V2 规则匹配（关键词 / LLM 兜底）
# ---------------------------------------------------------------------------


def _match_rules_v2(
    case_text: str,
    tag_matches: list[TagMatch],
) -> list[Rule]:
    """V2 协议的规则匹配.

    实现策略（启发式，避免 LLM 不可用时无规则命中）：

    1. 加载所有规则；
    2. 遍历规则，统计其 ``conditions`` / ``conclusion`` / ``applicable_scenarios``
       文本与案件文本的关键词命中数；
    3. 命中数 ≥ 1 即视为命中；
    4. 至少返回 1 条 fallback 规则，避免下游无规则可参与档级组合。
    """
    rules = load_rules()
    if not rules:
        return []

    # 收集案件文本里的关键词（来自 tag_matches + 案件文本）
    case_keywords: set[str] = set()
    for m in tag_matches:
        for token in (m.tag_id, m.matched_text):
            if token:
                case_keywords.add(str(token).strip())

    # 简单分词：使用案件文本中出现的中文双字以上片段
    if case_text:
        for ch in re.findall(r"[\u4e00-\u9fff]{2,}", case_text):
            case_keywords.add(ch)

    scored: list[tuple[int, Rule]] = []
    for r in rules:
        haystack = " ".join(
            [
                r.name or "",
                r.conclusion or "",
                r.conditions or "",
                " ".join(r.applicable_scenarios or []),
            ]
        )
        hits = sum(1 for kw in case_keywords if kw and kw in haystack)
        # 至少 1 个命中且权重 > 0
        if hits > 0 and (r.weight or 0) > 0:
            scored.append((hits, r))

    # 按命中数 * 权重排序
    scored.sort(key=lambda x: x[0] * (x[1].weight or 0.0), reverse=True)
    matched = [r for _, r in scored[:_V2_RULE_INJECTION_TOP_N]]

    if not matched:
        # 兜底：返回权重最高的 1 条规则
        sorted_rules = sorted(
            rules, key=lambda r: r.weight or 0.0, reverse=True
        )
        if sorted_rules:
            matched = [sorted_rules[0]]

    return matched


# ---------------------------------------------------------------------------
# V2 辅助：单维度 LLM 调用（带降级）
# ---------------------------------------------------------------------------


async def _v2_run_single_dimension(
    case_text: str,
    system_prompt: str,
    dim_name: str,
    user_prompt: str,
    temperature: float = _V2_DEFAULT_TEMPERATURE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """V2 协议下单个维度的 LLM 调用.

    返回 ``(dimension_result, timing_meta)``. 失败时使用默认档级.
    """
    start = time.perf_counter()
    start_ts = datetime.now(UTC).isoformat()
    status = "success"
    error_info: dict[str, str] = {}

    dim_result: dict[str, Any] = _build_default_v2_dimension(dim_name)
    try:
        response = await call_ollama_with_retry(
            user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )
        reasoning_text, _ = _extract_think_content(response)
        cleaned = sanitize_json_string(response)
        parsed = robust_json_parse(cleaned, default=dim_result)
        # 兼容 LLM 返回的嵌套结构
        if "ground_truth_analysis" in parsed and dim_name in parsed["ground_truth_analysis"]:
            parsed = parsed["ground_truth_analysis"][dim_name]
        dim_result = _build_v2_dimension_result(dim_name, parsed, fallback_used=False)
        if reasoning_text:
            dim_result["reasoning_process"] = reasoning_text
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        error_info = {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "error_time": datetime.now(UTC).isoformat(),
        }
        logger.error(f"V2 {dim_name} 异常: {exc}")
        dim_result = _build_default_v2_dimension(
            dim_name, fallback_reason=str(exc)
        )

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    timing: dict[str, Any] = {
        "status": status,
        "duration_ms": duration_ms,
        "start_time": start_ts,
        "end_time": datetime.now(UTC).isoformat(),
        **error_info,
    }
    return dim_result, timing


# ---------------------------------------------------------------------------
# V2 辅助：prior context 构建
# ---------------------------------------------------------------------------


def _build_v2_prior_context(
    dim1: dict[str, Any],
    dim2: dict[str, Any],
) -> tuple[str, str]:
    """构建维度 3 用的前置上下文（事实审查 + 模式匹配摘要）.

    返回 ``(prior_dim1_text, prior_dim2_text)`` 各自最长 300 字.
    """
    def _shorten(d: dict[str, Any]) -> str:
        tier = d.get("tier", _V2_DEFAULT_TIER)
        reasoning = d.get("reasoning", "无")
        if d.get("fallback"):
            return f"[默认档级] {tier}（该维度分析失败）"
        text = f"档级：{tier}\n推理摘要：{reasoning[:300]}"
        return text

    return _shorten(dim1), _shorten(dim2)


# ---------------------------------------------------------------------------
# V2 辅助：阶段包装（异常隔离 + 计时）
# ---------------------------------------------------------------------------


def _record_stage(
    meta: PipelineMeta,
    name: str,
    duration_ms: float,
    status: str,
) -> None:
    """记录单个阶段的耗时与状态到 pipeline_meta."""
    meta["stage_durations_ms"][name] = duration_ms
    meta["stage_status"][name] = status


# ---------------------------------------------------------------------------
# V2 主分析管道入口
# ---------------------------------------------------------------------------


@ANALYSIS_DURATION.time()
async def analyze_pipeline_v2(
    case_text: str,
    mode: str = "auto",
) -> AnalysisResultV2:
    """V2 协议下的主分析管道入口.

    顺序：

    1. 复杂度分类
    2. 知识检索（Neo4j / SQLite FTS / 内存兜底）
    3. 标签抽取
    4. 规则匹配
    5. 维度 1（事实审查）
    6. 维度 2（模式匹配）
    7. 维度 3（矛盾分析，带前置上下文）
    8. 档级组合
    9. 冲突检测
    10. 结论生成

    任一阶段失败不阻断，标记 ``fallback=True`` 并记录 ``failed_stage``.
    """
    meta: PipelineMeta = {
        "stage_durations_ms": {},
        "stage_status": {},
    }
    failed_stage: str = ""
    overall_start = time.perf_counter()

    # 阶段 1：复杂度分类
    stage_start = time.perf_counter()
    try:
        complexity: ComplexityLevel = classify_complexity(case_text)
        _record_stage(
            meta, _STAGE_COMPLEXITY,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success",
        )
    except Exception as exc:  # noqa: BLE001
        complexity = "medium"
        _record_stage(
            meta, _STAGE_COMPLEXITY,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_COMPLEXITY
        logger.warning(f"复杂度分类失败: {exc}")

    # 阶段 2：知识检索
    stage_start = time.perf_counter()
    knowledge_text: str = ""
    knowledge_entries: list[dict[str, str]] = []
    knowledge_used: bool = False
    try:
        knowledge_text, knowledge_entries = await _retrieve_legal_knowledge(case_text)
        knowledge_used = bool(knowledge_text)
        _record_stage(
            meta, _STAGE_KNOWLEDGE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if knowledge_text else "skipped",
        )
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_KNOWLEDGE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_KNOWLEDGE
        logger.warning(f"知识检索失败: {exc}")

    # 阶段 3：标签抽取
    stage_start = time.perf_counter()
    tag_matches: list[TagMatch] = []
    try:
        tag_matches = await _extract_tags_v2(case_text, rules=None)
        _record_stage(
            meta, _STAGE_TAGS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if tag_matches else "skipped",
        )
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_TAGS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_TAGS
        logger.warning(f"标签抽取失败: {exc}")

    matched_tag_ids: list[str] = list({m.tag_id for m in tag_matches})

    # 阶段 4：规则匹配
    stage_start = time.perf_counter()
    rule_hits: list[Rule] = []
    try:
        rule_hits = _match_rules_v2(case_text, tag_matches)
        _record_stage(
            meta, _STAGE_RULES,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if rule_hits else "skipped",
        )
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_RULES,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_RULES
        logger.warning(f"规则匹配失败: {exc}")

    triggered_rule_ids: list[str] = [r.rule_id for r in rule_hits]

    matched_tags_text = _format_matched_tags_for_prompt(tag_matches)
    triggered_rules_text = _format_matched_rules_for_prompt(rule_hits)

    # 阶段 5：维度 1
    stage_start = time.perf_counter()
    try:
        dim1_prompt = _format_v2_dimension1_prompt(
            case_text=case_text,
            matched_tags_text=matched_tags_text,
            triggered_rules_text=triggered_rules_text,
            legal_knowledge=knowledge_text,
        )
        dim1_result, dim1_meta = await _v2_run_single_dimension(
            case_text,
            "你是帮信罪事实审查维度的专业分析助手，按 5 步推理并输出 tier。",
            "dimension1",
            dim1_prompt,
        )
        _record_stage(
            meta, _STAGE_DIM1, dim1_meta.get("duration_ms", 0.0),
            dim1_meta.get("status", "unknown"),
        )
        # _v2_run_single_dimension 内部已吞掉异常并把 status 置为 "failed"，
        # 此处需要把它转写到顶层 failed_stage 上，供后续 fallback 标识。
        if dim1_meta.get("status") == "failed":
            failed_stage = failed_stage or _STAGE_DIM1
    except Exception as exc:  # noqa: BLE001
        dim1_result = _build_default_v2_dimension("dimension1", fallback_reason=str(exc))
        _record_stage(
            meta, _STAGE_DIM1,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_DIM1
        logger.warning(f"维度1执行失败: {exc}")

    # 阶段 6：维度 2
    stage_start = time.perf_counter()
    try:
        dim2_prompt = _format_v2_dimension2_prompt(
            case_text=case_text,
            matched_tags_text=matched_tags_text,
            triggered_rules_text=triggered_rules_text,
            legal_knowledge=knowledge_text,
        )
        dim2_result, dim2_meta = await _v2_run_single_dimension(
            case_text,
            "你是帮信罪模式匹配维度的专业分析助手，按 5 步推理并输出 tier。",
            "dimension2",
            dim2_prompt,
        )
        _record_stage(
            meta, _STAGE_DIM2, dim2_meta.get("duration_ms", 0.0),
            dim2_meta.get("status", "unknown"),
        )
        if dim2_meta.get("status") == "failed":
            failed_stage = failed_stage or _STAGE_DIM2
    except Exception as exc:  # noqa: BLE001
        dim2_result = _build_default_v2_dimension("dimension2", fallback_reason=str(exc))
        _record_stage(
            meta, _STAGE_DIM2,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_DIM2
        logger.warning(f"维度2执行失败: {exc}")

    # 阶段 7：维度 3（带前置上下文）
    stage_start = time.perf_counter()
    prior_dim1_text, prior_dim2_text = _build_v2_prior_context(dim1_result, dim2_result)
    try:
        dim3_prompt = _format_v2_dimension3_prompt(
            case_text=case_text,
            matched_tags_text=matched_tags_text,
            triggered_rules_text=triggered_rules_text,
            legal_knowledge=knowledge_text,
            prior_dim1_text=prior_dim1_text,
            prior_dim2_text=prior_dim2_text,
        )
        dim3_result, dim3_meta = await _v2_run_single_dimension(
            case_text,
            "你是帮信罪矛盾分析维度的专业分析助手，按 5 步推理并输出 tier。",
            "dimension3",
            dim3_prompt,
        )
        _record_stage(
            meta, _STAGE_DIM3, dim3_meta.get("duration_ms", 0.0),
            dim3_meta.get("status", "unknown"),
        )
        if dim3_meta.get("status") == "failed":
            failed_stage = failed_stage or _STAGE_DIM3
    except Exception as exc:  # noqa: BLE001
        dim3_result = _build_default_v2_dimension("dimension3", fallback_reason=str(exc))
        _record_stage(
            meta, _STAGE_DIM3,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_DIM3
        logger.warning(f"维度3执行失败: {exc}")

    # 阶段 8：档级组合
    stage_start = time.perf_counter()
    try:
        verdict: FinalVerdict = combine_tiers(
            dim1_result.get("tier", _V2_DEFAULT_TIER),
            dim2_result.get("tier", _V2_DEFAULT_TIER),
            dim3_result.get("tier", _V2_DEFAULT_TIER),
            rule_hits=rule_hits,
        )
        _record_stage(
            meta, _STAGE_COMBINE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success",
        )
    except Exception as exc:  # noqa: BLE001
        verdict = combine_tiers(
            _V2_DEFAULT_TIER, _V2_DEFAULT_TIER, _V2_DEFAULT_TIER, rule_hits=[]
        )
        _record_stage(
            meta, _STAGE_COMBINE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_COMBINE
        logger.warning(f"档级组合失败: {exc}")

    # 阶段 9：冲突检测
    stage_start = time.perf_counter()
    conflicts: list[Conflict] = []
    try:
        # 把维度结果转换为冲突检测器期望的简单 dict
        dim_results_for_conflict: dict[str, dict[str, Any]] = {
            "dimension1": {
                "tier": dim1_result.get("tier", _V2_DEFAULT_TIER),
                "reasoning": dim1_result.get("reasoning", ""),
            },
            "dimension2": {
                "tier": dim2_result.get("tier", _V2_DEFAULT_TIER),
                "reasoning": dim2_result.get("reasoning", ""),
            },
            "dimension3": {
                "tier": dim3_result.get("tier", _V2_DEFAULT_TIER),
                "reasoning": dim3_result.get("reasoning", ""),
            },
        }
        conflicts = detect_conflicts(
            tag_matches, rule_hits, dim_results_for_conflict
        )
        _record_stage(
            meta, _STAGE_CONFLICTS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success",
        )
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_CONFLICTS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_CONFLICTS
        logger.warning(f"冲突检测失败: {exc}")

    # 阶段 10：结论生成
    stage_start = time.perf_counter()
    conclusion_text: str = ""
    try:
        conclusion_text = await generate_conclusion(
            verdict=verdict,
            rule_hits=rule_hits,
            tags=tag_matches,
            case_text=case_text,
            dimension_tiers={
                "dimension1": dim1_result.get("tier", _V2_DEFAULT_TIER),
                "dimension2": dim2_result.get("tier", _V2_DEFAULT_TIER),
                "dimension3": dim3_result.get("tier", _V2_DEFAULT_TIER),
            },
            conflicts=conflicts,
        )
        _record_stage(
            meta, _STAGE_CONCLUSION,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if conclusion_text else "skipped",
        )
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_CONCLUSION,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_CONCLUSION
        logger.warning(f"结论生成失败: {exc}")

    # 整体置信度：维度的均值（0-1）
    confidences: list[float] = []
    for d in (dim1_result, dim2_result, dim3_result):
        c = d.get("confidence")
        if isinstance(c, (int, float)):
            confidences.append(max(0.0, min(1.0, float(c))))
    overall_confidence: float = (
        round(sum(confidences) / len(confidences), 4) if confidences else 0.5
    )

    # 冲突序列化为 dict
    conflicts_payload: list[dict[str, Any]] = [c.to_dict() for c in conflicts]

    result: AnalysisResultV2 = {
        "version": "v2",
        "subjective_knowledge": (
            dim1_result.get("key_indicators", [None])[0]
            if dim1_result.get("key_indicators")
            else _V2_DEFAULT_KNOWLEDGE
        ),
        "sentence": verdict.get("sentence_band", _V2_DEFAULT_SENTENCE),
        "court": "基层人民法院",
        "dimension1": {  # type: ignore[typeddict-item]
            "tier": dim1_result.get("tier", _V2_DEFAULT_TIER),
            "reasoning": dim1_result.get("reasoning", ""),
            "key_indicators": dim1_result.get("key_indicators", []),
            "triggered_rules": dim1_result.get("triggered_rules", []),
        },
        "dimension2": {  # type: ignore[typeddict-item]
            "tier": dim2_result.get("tier", _V2_DEFAULT_TIER),
            "reasoning": dim2_result.get("reasoning", ""),
            "pattern_match": dim2_result.get("pattern_match", ""),
            "triggered_rules": dim2_result.get("triggered_rules", []),
        },
        "dimension3": {  # type: ignore[typeddict-item]
            "tier": dim3_result.get("tier", _V2_DEFAULT_TIER),
            "reasoning": dim3_result.get("reasoning", ""),
            "contradictions": dim3_result.get("contradictions", []),
            "triggered_rules": dim3_result.get("triggered_rules", []),
        },
        "final_verdict": verdict,
        "triggered_rule_ids": triggered_rule_ids,
        "matched_tag_ids": matched_tag_ids,
        "conflicts": conflicts_payload,
        "confidence": overall_confidence,
        "pipeline_meta": meta,
        "fallback": bool(failed_stage) or any(
            meta["stage_status"].get(s) == "failed"
            for s in (_STAGE_DIM1, _STAGE_DIM2, _STAGE_DIM3, _STAGE_COMBINE)
        ),
        "timestamp": datetime.now(UTC).isoformat(),
        "knowledge_used": knowledge_used,
        "knowledge_entries": knowledge_entries,
        "disclaimer": (
            "本结论由 V2 协议（三维度 × 四档）生成，"
            "并集成了规则、标签、冲突检测结果，仅供办案人员参考。"
        ),
    }

    if failed_stage:
        result["failed_stage"] = failed_stage
        meta["failed_stage"] = failed_stage

    # 把 LLM 原始推理（仅维度 1）放在顶层，方便阅读
    if dim1_result.get("reasoning_process"):
        result["reasoning_process"] = dim1_result["reasoning_process"]

    # 把结论文本附加在 result.conclusion_text 字段上（不破坏 TypedDict）
    result["conclusion_text"] = conclusion_text  # type: ignore[typeddict-unknown-key]

    # 整体耗时
    meta["stage_durations_ms"]["_total"] = round(
        (time.perf_counter() - overall_start) * 1000, 2
    )

    try:
        ANALYSIS_COUNTER.labels(mode=mode, status="success").inc()
    except Exception:  # noqa: BLE001
        pass

    logger.info(
        f"V2 管道完成: complexity={complexity}, "
        f"final_tier={verdict.get('final_tier')}, "
        f"fallback={result['fallback']}, "
        f"total_ms={meta['stage_durations_ms'].get('_total')}"
    )

    return result


# ---------------------------------------------------------------------------
# 兼容性别名 — V1 协议默认行为不变
# ---------------------------------------------------------------------------


async def analyze_pipeline(  # noqa: F811
    case_text: str,
    mode: str = "auto",
    version: str = "v2",
) -> Any:
    """主分析管道入口（同时支持 V1 / V2 协议）.

    Args:
        case_text: 案件事实文本
        mode: 分析模式（auto/single/multi）
        version: 协议版本 ``"v1"``（保留 0-10 评分）或 ``"v2"``（档级 + 规则/标签/冲突）
    """
    if version == "v1":
        # 委托给原 V1 实现（这里通过包内函数名重命名解决）
        return await _analyze_pipeline_v1(case_text, mode=mode)
    # 默认 v2
    return await analyze_pipeline_v2(case_text, mode=mode)


async def _analyze_pipeline_v1(case_text: str, mode: str = "auto") -> AnalysisResult:
    """V1 协议下的主分析管道入口（保留 0-10 评分，向后兼容）."""
    try:
        legal_knowledge, knowledge_entries = await _retrieve_legal_knowledge(case_text)
        knowledge_used: bool = bool(legal_knowledge)

        if legal_knowledge:
            logger.info(f"知识注入启用: {len(knowledge_entries)} 条知识条目")

        if AnalysisConfig.SC_ENABLED and mode != "single":
            logger.info(
                f"启用 Self-Consistency 多次采样: "
                f"samples={AnalysisConfig.SC_NUM_SAMPLES}, "
                f"temperature={AnalysisConfig.SC_TEMPERATURE}"
            )
            result = await self_consistency_analysis(
                case_text, mode=mode,
                n_samples=AnalysisConfig.SC_NUM_SAMPLES,
                sample_temperature=AnalysisConfig.SC_TEMPERATURE,
                legal_knowledge=legal_knowledge,
            )
            result["fallback"] = False
            result["timestamp"] = datetime.now(UTC).isoformat()
            result["knowledge_used"] = knowledge_used
            result["knowledge_entries"] = knowledge_entries
            return result

        complexity: ComplexityLevel = classify_complexity(case_text)
        logger.info(f"自动模式: 复杂度='{complexity}'")

        if mode == "single" or (
            mode == "auto" and complexity == "simple"
        ):
            logger.info("推理模式: single")
            result: AnalysisResult = await single_pass_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )
        elif mode == "multi" or (
            mode == "auto" and complexity in ("medium", "complex")
        ):
            logger.info("推理模式: multi")
            result = await multi_dimension_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )
        else:
            result = await single_pass_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )

        if "ground_truth_analysis" not in result:
            result["ground_truth_analysis"] = {
                "dimension1": _build_default_dimension(),
                "dimension2": _build_default_dimension(),
                "dimension3": _build_default_dimension(),
            }

        result["fallback"] = result.get("fallback", False)
        result["timestamp"] = datetime.now(UTC).isoformat()
        result["knowledge_used"] = knowledge_used
        result["knowledge_entries"] = knowledge_entries

        ANALYSIS_COUNTER.labels(mode=mode, status="success").inc()
        return result
    except Exception:
        ANALYSIS_COUNTER.labels(mode=mode, status="error").inc()
        raise
