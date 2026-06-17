"""分析管道核心模块.

V2 协议（阶段 4）：负责按"复杂度分类 → 标签抽取 → 规则匹配 →
维度1 → 维度2 → 维度3（带前置上下文）→ 档级组合 → 冲突检测
→ 结论生成"的顺序编排 LLM 调用，输出 :class:`AnalysisResultV2`。

V1 协议（向后兼容）：保留原 0-10 分评分管道 ``single_pass_analysis`` 、
``multi_dimension_analysis`` 与 ``self_consistency_analysis``，旧调用方
仍可使用。
"""

# 导入模块: asyncio
import asyncio
# 导入模块: json
import json
# 导入模块: re
import re
# 导入模块: statistics
import statistics
# 导入模块: time
import time
# 导入模块: from dataclasses
from dataclasses import dataclass
# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from typing
from typing import Any, Literal

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.config
from app.config import AnalysisConfig, settings
# 导入模块: from app.database
from app.database import get_async_db_session
# 导入模块: from app.models.knowledge_entry
from app.models.knowledge_entry import EntryStatus
# 导入模块: from app.services.boundary_reminder
from app.services.boundary_reminder import check_boundary_alerts
# 导入模块: from app.services.conclusion_generator
from app.services.conclusion_generator import generate_conclusion
# 导入模块: from app.services.conflict_detector
from app.services.conflict_detector import Conflict, detect_conflicts
# 导入模块: from app.services.evidence_layer
from app.services.evidence_layer import build_evidence_layers, guard_against_single_layer_override
# 导入模块: from app.services.knowledge_search_service
from app.services.knowledge_search_service import ensure_fts_table, search_entries
# 导入模块: from app.services.ollama_client
from app.services.ollama_client import _extract_think_content, call_ollama_with_retry
# 导入模块: from app.services.path_identifier
from app.services.path_identifier import identify_legal_path
# 导入模块: from app.services.prompts
from app.services.prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    DIMENSION1_PROMPT,
    DIMENSION2_PROMPT,
    DIMENSION3_PROMPT,
    V2_DIMENSION1_PROMPT,
    V2_DIMENSION2_PROMPT,
    V2_DIMENSION3_PROMPT,
)
# 导入模块: from app.services.rule_engine
from app.services.rule_engine import Rule, load_rules
# 导入模块: from app.services.subject_stratifier
from app.services.subject_stratifier import stratify_subjects
# 导入模块: from app.services.tag_extractor
from app.services.tag_extractor import TagMatch, extract_tags
# 导入模块: from app.services.tier_combiner
from app.services.tier_combiner import combine_tiers
# 导入模块: from app.types.analysis
from app.types.analysis import (
    AnalysisResult,
    GroundTruthAnalysis,
)
# 导入模块: from app.types.analysis_v2
from app.types.analysis_v2 import (
    AnalysisResultV2,
    FinalVerdict,
    PipelineMeta,
    TierEnum,
)
# 导入模块: from app.types.evidence_layer
from app.types.evidence_layer import EvidenceLayerReport
# 导入模块: from app.utils.common
from app.utils.common import sanitize_json_string
# 导入模块: from app.utils.monitoring
from app.utils.monitoring import ANALYSIS_COUNTER, ANALYSIS_DURATION


# 初始化变量 ComplexityLevel
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


# 应用装饰器: dataclass
@dataclass
# 定义 ComplexityFactors 类
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
    # 返回处理结果
    return {
        "score": AnalysisConfig.DEFAULT_DIMENSION_SCORE,
        "reasoning": AnalysisConfig.DEFAULT_REASONING,
    }


def _build_default_analysis_result() -> AnalysisResult:
    """构建预设的默认分析结果，用于 JSON 解析失败时的降级返回.

    Returns:
        AnalysisResult: 包含完整三维度默认值的结果字典
    """
    # 初始化变量 default_dim
    default_dim = _build_default_dimension()
    # 返回处理结果
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
    # 初始化变量 match
    match = re.search(pattern, text, re.DOTALL)
    # 条件判断：处理业务逻辑
    if match:
        # 返回处理结果
        return match.group(1).strip()
    # 返回处理结果
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
    # 初始化变量 in_double_quote
    in_double_quote = False
    # 初始化变量 in_single_quote
    in_single_quote = False
    # 初始化变量 escaped
    escaped = False

    for ch in json_str:
        # 条件判断: 检查 escaped
        if escaped:
            result.append(ch)
            escaped = False
            continue

        # 条件判断: 检查 ch == "\\"
        if ch == "\\":
            result.append(ch)
            # 初始化变量 escaped
            escaped = True
            continue

        # 条件判断: 检查 ch == '"' and not in_single_quote
        if ch == '"' and not in_single_quote:
            # 初始化变量 in_double_quote
            in_double_quote = not in_double_quote
            result.append(ch)
        # 条件判断: 检查 elch == "'" and not in_double_quote
        elif ch == "'" and not in_double_quote:
            # 初始化变量 in_single_quote
            in_single_quote = not in_single_quote
            result.append('"')
        # 其他情况的默认处理
        else:
            result.append(ch)

    # 返回处理结果
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
    # 返回处理结果
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
    # 初始化变量 in_string
    in_string = False
    # 初始化变量 escaped
    escaped = False

    # 遍历: for ch in json_str:
    for ch in json_str:
        # 条件判断: 检查 escaped
        if escaped:
            result.append(ch)
            escaped = False
            continue

        # 条件判断: 检查 ch == "\\"
        if ch == "\\":
            result.append(ch)
            escaped = True
            continue

        # 条件判断: 检查 ch == '"'
        if ch == '"':
            # 初始化变量 in_string
            in_string = not in_string
            result.append(ch)
            continue

        # 条件判断: 检查 in_string
        if in_string:
            # 条件判断: 检查 ch == "\n"
            if ch == "\n":
                result.append("\\n")
            # 条件判断: 检查 elch == "\t"
            elif ch == "\t":
                result.append("\\t")
            # 条件判断: 检查 elch == "\r"
            elif ch == "\r":
                result.append("\\r")
            # 其他情况的默认处理
            else:
                result.append(ch)
        # 其他情况的默认处理
        else:
            result.append(ch)

    # 返回处理结果
    return "".join(result)


def robust_json_parse(
    # 函数 robust_json_parse 的初始化逻辑
    text: str,


    # 执行 robust_json_parse 函数的核心逻辑
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
        {'key': 'va    # 条件判断：处理业务逻辑
lue'}
        >>> robust_json_parse("{'key': 'value',}")
        {'key': 'value'}
        >>> robust_json_parse("not json at all")
        {'ground_truth_analysis': {...}, 'fallback': True, ...}
    """
    # 条件判断: 检查 default is None
    if default is None:
        # 初始化变量 default
        default = _build_default_analysis_result()

    # 策略1: 直接解析
    # 异常处理：处理业务逻辑
    try:
        # 返回处理结果
        return json.loads(text)
    # 捕获异常：处理业务逻辑
    except json.JSONDecodeError:
        pass

    # 策略2: 移除 Markdown 代码块后解析
    stripped = _strip_markdown_code_blocks(text)
    try:
        # 返回处理结果
        return json.loads(stripped)
    # 捕获并处理异常
    except json.JSONDecodeError:
        pass

    # 策略3: 提取 JSON 对象（第一个 { 到最后一个 }）
    start = text.find("{")
    end = text.rfind("}")
    # 初始化变量 extracted
    extracted = (
        text[start:end + 1]
        # 条件判断: 检查 start != -1 and end != -1 and end > start
        if start != -1 and end != -1 and end > start
        else stripped
    )

    # 尝试执行可能抛出异常的代码
    try:
     # 捕获异常：处理业务逻辑
       return json.loads(extracted)
    # 捕获并处理异常
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
    # 初始化变量 combined
    combined = _repair_trailing_commas(combined)
    # 初始化变量 combined
    combined = _repair_single_quotes(combined)
    combined = _repair_unquoted_keys(combined)
    repair_candidates.append(combined)

    # 完整组合修复：包含特殊字符转义
    combined_full = _repair_unescaped_special_chars(combined)
    repair_candidates.append(combined_full)

    # 遍历: for candidate in repair_candidates:
    for candidate in repair_candidates:
        if candidate == extracted:
            continue  # 跳过已尝试的原始提取
        # 捕获异常：处理业务逻辑
        try:
            # 返回处理结果
            return json.loads(candidate)
        # 捕获并处理异常
        except json.JSONDecodeError:
            continue

    # 策略5: 所有策略均失败，返回默认值
    logger.warning("JSON 解析失败，使用默认降级结果")
    # 返回处理结果
    return default


def _count_keywords(text: str) -> int:
    """统计文本中关键法律术语的出现次数.

    对 _KEYWORD_LEGAL 中定义的每个法律术语进行子串匹配，
    长术语优先匹配以避免重复计数（如"故意伤害"优先于"故意"）。

    Args:
        text: 案件事实文本

            # 条件判断：处理业务逻辑
Returns:
        int: 匹配到的关键法律术语总数

    Example:
        >>> _count_keywords("被告人故意伤害被害人，明知其行为违法")
        4
    """
    # 初始化变量 count
    count = 0
    # 初始化变量 remaining
    remaining = text
    # 循环遍历：处理业务逻辑
    for keyword in sorted(_KEYWORD_LEGAL, key=len, reverse=True):
        # 初始化变量 occurrences
        occurrences = remaining.count(keyword)
        # 条件判断: 检查 occurrences > 0
        if occurrences > 0:
            count += occurrences
            # 初始化变量 remaining
            remaining = remaining.replace(keyword, "\x00")
    # 返回处理结果
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
    # 初始化变量 sentences
    sentences = re.split(r"[。！？；.!?;]+", text)
    # 初始化变量 valid
    valid = [s.strip() for s in sentences if s.strip()]
    # 返回处理结果
    return len(valid) if valid else 1


def _count_evidence(text: str) -> int:
    """统计文本中提及的证据线索数量.

    通过匹配 _EVIDENCE_TERMS 中定义的证据相关术语进行统计。

            # 条件判断：处理业务逻辑
Args:
        text: 案件事实文本

    Returns:
        int: 证据线索数量

    Example:
        >>> _count_evidence("现场勘查发现指纹，监控录像记录了全过程")
        3
    """
    # 初始化变量 count
    count = 0
    remaining = text
    # 遍历: for term in sorted(_EVIDENCE_TERMS, key=len, rever
    for term in sorted(_EVIDENCE_TERMS, key=len, reverse=True):
        # 初始化变量 occurrences
        occurrences = remaining.count(term)
        # 条件判断: 检查 occurrences > 0
        if occurrences > 0:
            count += occurrences
            # 初始化变量 remaining
            remaining = remaining.replace(term, "\x00")
    # 返回处理结果
    return count


def _count_people(text: str) -> int:
    """统计文本中涉及的相关人员数量.

    通过匹配 _PEOPLE_ROLE_TERMS 中定义的人员角色术语
    以及中文姓名模式（如"张某"、"李某某"）进行统计。

    为避免重复计数，角色术语采用长词优先替换策略；
    姓名模式匹配在原始文本上进行，确保不被角色替换干扰。
          # 条件判断：处理业务逻辑
  同一姓名只计一次。

    Args:
        text: 案件事实文本

    Returns:
        int: 涉案人员数量

    Example:
        >>> _count_people("被告人张某与被害人李某发生冲突，证人王某作证")
        3
    """
    # 初始化变量 count
    count = 0
    # 初始化变量 remaining
    remaining = text

    # 遍历: for role in sorted(_PEOPLE_ROLE_TERMS, key=len, re
    for role in sorted(_PEOPLE_ROLE_TERMS, key=len, reverse=True):
        # 初始化变量 occurrences
        occurrences = remaining.count(role)
        # 条件判断: 检查 occurrences > 0
        if occurrences > 0:
            count += occurrences
            # 初始化变量 remaining
            remaining = remaining.replace(role, "\x00")

    # 初始化变量 name_pattern
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
        # 循环遍历：处理业务逻辑
)
    found_names: set[str] = set()
    # 遍历: for match in name_pattern.finditer(text):
    for match in name_pattern.finditer(text):
        # 初始化变量 name_start
        name_start = match.start()
        # 初始化变量 suffix_match
        suffix_match = re.match(r"某{1,2}|某某", text[name_start + 1:])
        # 条件判断: 检查 suffix_match
        if suffix_match:
            # 初始化变量 full_name
            full_name = text[name_start:name_start + 1 + suffix_match.end()]
            # 条件判断: 检查 full_name not in found_names
            if full_name not in found_names:
                found_names.add(full_name)
                count += 1

    # 返回处理结果
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
    # 返回处理结果
    return ComplexityFactors(
        # 初始化变量 keyword_count
        keyword_count=_count_keywords(case_text),
        # 初始化变量 sentence_count
        sentence_count=_count_sentences(case_text),
        # 初始化变量 evidence_count
        evidence_count=_count_evidence(case_text),
        # 初始化变量 people_count
        people_count=_count_people(case_text),
    )


def _compute_composite_score(factors: ComplexityFactors) -> float:


    # 执行 _compute_composite_score 函数的核心逻辑
    r"""根据各评估因子计算加权综合复杂度分数.

    使用 AnalysisConfig 中配置的各因子权重值进行加权求和：

    .. math::
        # 初始化变量 score
        score = keyword_count \\times w_k + sentence_count \\times w_s
              + evidence_count \\times w_e + people_count \\times w_p

    Args:
        factors: 复杂度评估因子数据对象

    Returns:
        float: 加权综合复杂度分数
    """
    # 返回处理结果
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

    # 条件判断：处理业务逻辑
        'medium'
    """
    # 初始化变量 factors
    factors = _compute_complexity_factors(case_text)
    # 初始化变量 score
    score = _compute_composite_score(factors)

    # 记录日志信息
    logger.debug(
        f"复杂度评估: keywords={factors.keyword_count}, "
        f"sentences={factors.sentence_count}, "
        f"evidence={factors.evidence_count}, "
        f"people={factors.people_count}, "
        f"composite_score={score:.1f}"
    )

    # 条件判断: 检查 score <= AnalysisConfig.COMPLEXITY_COMPO
    if score <= AnalysisConfig.COMPLEXITY_COMPOSITE_SIMPLE_MAX:
        # 返回处理结果
        return "simple"
    # 条件判断: 检查 score <= AnalysisConfig.COMPLEXITY_COMPO
    if score <= AnalysisConfig.COMPLEXITY_COMPOSITE_MEDIUM_MAX:
        # 返回处理结果
        return "medium"
    # 返回处理结果
    return "complex"


async def single_pass_analysis(
    # 函数 single_pass_analysis 的初始化逻辑
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
    # 记录日志信息
    logger.info(f"使用单通道分析模式 ({mode}), temperature={temperature}")
    system_prompt: str = ANALYSIS_SYSTEM_PROMPT.replace("{legal_knowledge}", legal_knowledge)
    user_prompt: str = f"请对以下案件进行三维度分析：\n\n{case_text}"

    # 异步等待操作完成
    response: str = await call_ollama_with_retry(
        user_prompt, system_prompt=system_prompt, temperature=temperature
    )
    reasoning_text, _ = _extract_think_content(response)
    result: AnalysisResult = robust_json_parse(sanitize_json_string(response))
    # 条件判断: 检查 reasoning_text
    if reasoning_text:
        result["reasoning_process"] = reasoning_text
    # 返回处理结果
    return result


async def _single_dimension_analysis(
    # 函数 _single_dimension_analysis 的初始化逻辑
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
      # 条件判断：处理业务逻辑
      Exception: LLM 调用失败时向上传播异常
    """
    prompt: str = user_prompt if user_prompt is not None else case_text
    # 初始化变量 response
    response = await call_ollama_with_retry(
        prompt, system_prompt=system_prompt, temperature=temperature
    )
    reasoning_text, _ = _extract_think_content(response)
    # 初始化变量 cleaned
    cleaned = sanitize_json_string(response)
    # 初始化变量 result
    result = robust_json_parse(
        cleaned,
        # 初始化变量 default
        default=_build_default_dimension(),
    )
    # 条件判断: 检查 reasoning_text
    if reasoning_text:
        result["reasoning_process"] = reasoning_text
    # 返回处理结果
    return result


async def _timed_dimension_analysis(
    # 函数 _timed_dimension_analysis 的初始化逻辑
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

    # 尝试执行可能抛出异常的代码
    try:
        # 异步等待操作完成
        result: dict[str, Any] = await _single_dimension_analysis(
            case_text, system_prompt, dimension_name,
            # 初始化变量 user_prompt
            user_prompt=user_prompt, temperature=temperature,
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        result = _build_default_dimension()
        # 初始化变量 status
        status = "failed"
        # 初始化变量 error_info
        error_info = {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "error_time": datetime.now(UTC).isoformat(),
        }
        # 记录日志信息
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
    # 记录日志信息
    logger.info(
        f"{dimension_name} 执行完成: 状态={status}, 耗时={duration_ms}ms"
    )
    # 返回处理结果
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
        str:        # 条件判断：处理业务逻辑
 格式化的前置分析文本摘要（不超过500字）
    """
    parts: list[str] = []

    dim1_score: float = dim1_result.get("score", _DEFAULT_SCORE)
    dim1_reasoning: str = dim1_result.get("reasoning", "无分析结果")
    dim1_indicators: list[str] = dim1_result.get("key_indicators", [])

    if dim1_reasoning == "自动分析结果" and dim1_score == _DEFAULT_SCORE:
        parts.append("【事实审查维度分析失败，该维度无法提供有效分析，请独立判断】")
    # 其他情况的默认处理
    else:
        parts.append("【事实审查维度结论】")
        parts.append(f"评分：{dim1_score}/10")
        # 条件判断: 检查 dim1_indicators
        if dim1_indicators:
            parts.append(f"关键指标：{'、'.join(dim1_indicators[:5])}")
        parts.append(f"分析摘要：{dim1_reasoning[:200]}")

    dim2_score: float = dim2_result.get("score", _DEFAULT_SCORE)
    dim2_reasoning: str = dim2_result.get("reasoning", "无分析结果")
    dim2_pattern: str = dim2_result.get("pattern_match", "无匹配结果")

    # 条件判断: 检查 dim2_reasoning == "自动分析结果" and dim2_scor
    if dim2_reasoning == "自动分析结果" and dim2_score == _DEFAULT_SCORE:
        parts.append("【模式匹配维度分析失败，该维度无法提供有效分析，请独立判断】")
    # 其他情况的默认处理
    else:
        parts.append("")
        parts.append("【模式匹配维度结论】")
        parts.append(f"评分：{dim2_score}/10")
        parts.append(f"模式匹配：{dim2_pattern}")
        parts.append(f"分析摘要：{dim2_reasoning[:200]}")

    context: str = "\n".join(parts)

    # 条件判断: 检查 len(context) > _MAX_CONTEXT_LENGTH
    if len(context) > _MAX_CONTEXT_LENGTH:
        # 初始化变量 context
        context = context[:_MAX_CONTEXT_LENGTH - 3] + "..."

    # 返回处理结果
    return context


async def multi_dimension_analysis(
    # 函数 multi_dimension_analysis 的初始化逻辑
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
    # 记录日志信息
    logger.info(f"使用多维度两阶段分析模式, temperature={temperature}")

    dim1_prompt: str = DIMENSION1_PROMPT.replace("{legal_knowledge}", legal_knowledge)
    dim2_prompt: str = DIMENSION2_PROMPT.replace("{legal_knowledge}", "")

    # ------------------------------------------------------------------
    # 第一阶段：并行执行维度1（事实审查）和维度2（模式匹配）
    # ------------------------------------------------------------------
    phase1_dim_names: list[str] = ["dimension1", "dimension2"]
    # 初始化变量 phase1_results
    phase1_results = await asyncio.gather(
        _timed_dimension_analysis(case_text, dim1_prompt, "维度1", temperature=temperature),
        _timed_dimension_analysis(case_text, dim2_prompt, "维度2", temperature=temperature),
        return_exceptions=True,
    )

    dimension_results: dict[str, dict[str, Any]] = {}
    dimension_meta: dict[str, dict[str, Any]] = {}

    # 遍历: for dim_name, gather_result in zip(
    for dim_name, gather_result in zip(
        phase1_dim_names, phase1_results, strict=True
    ):
        # 条件判断: 检查 isinstance(gather_result, BaseException)
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
            # 记录日志信息
            logger.error(
                f"{dim_name} 分析异常: "
                f"类型={type(gather_result).__name__}, "
                f"错误={gather_result}, "
                f"时间={error_time}"
            )
        # 其他情况的默认处理
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
        # 初始化变量 prior_analysis
        prior_analysis=context,
        # 初始化变量 case_text
        case_text=case_text,
    )
    dim3_result: dict[str, Any]
    dim3_timing: dict[str, Any]
    # 异步等待操作完成
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

    # 返回处理结果
    return {
        "ground_truth_analysis": ground_truth,
        "subjective_knowledge": subjective_knowledge,
        "sentence": sentence_suggestion,
        "fallback": False,
        "timestamp": datetime.now(UTC).isoformat(),
        "dimension_meta": dimension_meta,
    }


async def self_consistency_analysis(  # noqa: PLR0912, PLR0915
    # 函数 self_consistency_analysis 的初始化逻辑
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
            # 条件判断：处理业务逻辑
        sample_temperature: 采样温度（高于默认值以引入多样性）
        legal_knowledge: 注入的检索知识（可选）

    Returns:
        AnalysisResult: 包含 SC 置信度指标的分析结果
    """
    # 记录日志信息
    logger.info(
        f"Self-Consistency 分析: samples={n_samples}, "
        f"temperature={sample_temperature}, mode={mode}"
    )

    dim_names: list[str] = ["dimension1", "dimension2", "dimension3"]
    all_results: list[AnalysisResult] = []
    sample_scores_list: list[dict[str, Any]] = []

    # 遍历: for i in range(n_samples):
    for i in range(n_samples):
        # 记录日志信息
        logger.info(f"Self-Consistency 采样 {i + 1}/{n_samples}")
        # 尝试执行可能抛出异常的代码
        try:
            # 条件判断: 检查 mode == "single"
            if mode == "single":
                # 初始化变量 result
                result = await single_pass_analysis(
                    case_text, mode=mode, temperature=sample_temperature,
                    # 初始化变量 legal_knowledge
                    legal_knowledge=legal_knowledge,
                )
            # 条件判断: 检查 elmode == "multi"
            elif mode == "multi":
                # 初始化变量 result
                result = await multi_dimension_analysis(
                    case_text, mode=mode, temperature=sample_temperature,
                    # 初始化变量 legal_knowledge
                    legal_knowledge=legal_knowledge,
                )
            # 其他情况的默认处理
            else:
                complexity: ComplexityLevel = classify_complexity(case_text)
                # 条件判断: 检查 complexity == "simple"
                if complexity == "simple":
                    # 初始化变量 result
                    result = await single_pass_analysis(
                        case_text, mode=mode, temperature=sample_temperature,
                        # 初始化变量 legal_knowledge
                        legal_knowledge=legal_knowledge,
                    )
                # 其他情况的默认处理
                else:
                    # 初始化变量 result
                    result = await multi_dimension_analysis(
                        case_text, mode=mode, temperature=sample_temperature,
                        legal_knowledge=legal_knowledge,
                    )

            all_results.append(result)

            gta = result.get("ground_truth_analysis", {}) or {}
            # 初始化变量 sample_scores
            sample_scores = {}
            # 遍历: for dim in dim_names:
            for dim in dim_names:
                dim_data = gta.get(dim, {}) or {}
                sample_scores[dim] = dim_data.get("score", 5.0)
            sample_scores_list.append(sample_scores)

        # 捕获并处理异常
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"Self-Consistency 采样 {i + 1} 失败: {exc}"
            )
            continue

    # 条件判断: 检查 not all_results
    if not all_results:
        # 记录日志信息
        logger.warning("Self-Consistency 所有采样均失败，使用默认降级结果")
        # 初始化变量 result
        result = _build_default_analysis_result()
        result["confidence"] = 0.0
        result["confidence_details"] = {}
        result["num_samples"] = 0
        result["sample_scores"] = []
        # 返回处理结果
        return result

    # 初始化变量 actual_samples
    actual_samples = len(all_results)

    dim_scores: dict[str, list[float]] = {d: [] for d in dim_names}
    dim_reasonings: dict[str, list[str]] = {d: [] for d in dim_names}

    for sample in sample_scores_list:
        for dim in dim_names:
            score = sample.get(dim, 5.0)
            dim_scores[dim].append(score)

    # 遍历: for result in all_results:
    for result in all_results:
        gta = result.get("ground_truth_analysis", {}) or {}
        # 遍历: for dim in dim_names:
        for dim in dim_names:
            # 初始化变量 dim_data
            dim_data = gta.get(dim, {}) or {}
            # 初始化变量 reasoning
            reasoning = dim_data.get("reasoning", "")
            dim_reasonings[dim].append(reasoning)

    final_scores: dict[str, float] = {}
    dim_std: dict[str, float] = {}
    dim_confidence: dict[str, float] = {}
    confidence_details: dict[str, Any] = {}

    # 遍历: for dim in dim_names:
    for dim in dim_names:
        # 初始化变量 scores
        scores = dim_scores[dim]
        # 条件判断: 检查 scores
        if scores:
            final_scores[dim] = statistics.median(scores)
        # 其他情况的默认处理
        else:
            final_scores[dim] = 5.0

        # 条件判断: 检查 len(scores) >= _MIN_SAMPLES_FOR_STDEV
        if len(scores) >= _MIN_SAMPLES_FOR_STDEV:
            dim_std[dim] = statistics.stdev(scores)
        # 其他情况的默认处理
        else:
            dim_std[dim] = 0.0

        # 初始化变量 max_possible_std
        max_possible_std = 5.0
        # 初始化变量 conf
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

    # 初始化变量 best_result
    best_result = all_results[0]
    # 初始化变量 best_deviation
    best_deviation = float("inf")
    # 遍历: for result in all_results:
    for result in all_results:
        gta = result.get("ground_truth_analysis", {}) or {}
        # 初始化变量 deviation
        deviation = 0.0
        # 遍历: for dim in dim_names:
        for dim in dim_names:
            # 初始化变量 dim_data
            dim_data = gta.get(dim, {}) or {}
            # 初始化变量 score
            score = dim_data.get("score", 5.0)
            deviation += abs(score - final_scores[dim])
        # 条件判断: 检查 deviation < best_deviation
        if deviation < best_deviation:
            # 初始化变量 best_deviation
            best_deviation = deviation
            # 初始化变量 best_result
            best_result = result

    final_result: AnalysisResult = dict(best_result)
    gta = final_result.get("ground_truth_analysis")
    # 条件判断: 检查 gta
    if gta:
        # 遍历: for dim in dim_names:
        for dim in dim_names:
            # 条件判断: 检查 dim in gta
            if dim in gta:
                # 初始化变量 dim_copy
                dim_copy = dict(gta[dim])
                dim_copy["score"] = final_scores[dim]
                gta[dim] = dim_copy

    final_result["confidence"] = overall_confidence
    final_result["confidence_details"] = confidence_details
    final_result["num_samples"] = actual_samples
    final_result["sample_scores"] = sample_scores_list

    # 记录日志信息
    logger.info(
        f"Self-Consistency 完成: samples={actual_samples}, "
        f"confidence={overall_confidence}"
    )

    # 返回处理结果
    return final_result


async def _retrieve_neo4j_knowledge(
    # 函数 _retrieve_neo4j_knowledge 的初始化逻辑
    case_text: str,
    max_entries: int = 5,
) -> list[dict[str, str]] | None:
    """从 Neo4j 图数据库中检索与案件相关的法律知识.

    策略：

    1. 若 ``settings.NEO4J_URI`` 为空，直接返回 ``None``，由调用方降级到 SQL    # 条件判断：处理业务逻辑
ite FTS。
    2. 尝试调用 Neo4j 驱动执行关键词查询；任何异常（连接失败、驱动不可用等）
       均返回 ``None``，由调用方降级。

    Returns:
        命中的知识条目摘要列表；若 Neo4j 未配置或不可
    # 异常处理：处理业务逻辑
用则返回 ``None``.
    """
    # 条件判断: 检查 settings.NEO4J_URI is None
    if settings.NEO4J_URI is None:
        # 返回处理结果
        return None

    # 尝试执行可能抛出异常的代码
    try:
        # 延迟导入避免无 Neo4j 环境下拉起驱动
        from neo4j import GraphDatabase  # type: ignore

    # 异常处理：处理业务逻辑
    except ImportError:
        # 记录日志信息
        logger.warning("Neo4j 驱动未安装，回退到 SQLite FTS")
        # 返回处理结果
        return None

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 driver
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            # 初始化变量 auth
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    # 捕获并处理异常
    except Exception:  # noqa: BLE001
        logger.warning("Neo4j 驱动初始化失败，回退到 SQLite FTS", exc_info=True)
        # 返回处理结果
        return None

    # 初始化变量 keywords
    keywords = [kw for kw in _KEYWORD_LEGAL if kw in case_text][:3]
    # 条件判断: 检查 not keywords
    if not keywords:
        driver.close()
        return []

    # 初始化变量 query
    query = (
        "MATCH (n:KnowledgeEntry) "
        "WHERE any(k IN $keywords WHERE n.title CONTAINS k OR n.summary CONTAINS k) "
        "RETURN n.title AS title, n.summary AS summary "
        "LIMIT $limit"
    )
    # 尝试执行可能抛出异常的代码
    try:
        # 使用上下文管理器管理资源
        with driver.session() as session:
            result = session.run(query, keywords=keywords, limit=max_entries)
            records = [dict(record) for record in result]
    # 捕获并处理异常
    except Exception:  # noqa: BLE001
        logger.warning("Neo4j 查询失败，回退到 SQLite FTS", exc_info=True)
        driver.close()
        # 返回处理结果
        return None
    # 最终清理代码，无论是否异常都会执行
    finally:
        driver.close()

    entries: list[dict[str, str]] = []
    # 遍历: for r in records:
    for r in records:
        # 初始化变量 title
        title = (r.get("title") or "").strip()
        # 初始化变量 summary
        summary = (r.get("summary") or "").strip()
        # 条件判断: 检查 not title
        if not title:
            continue
        entries.append({"title": title, "summary": summary})
    # 返回处理结果
    return entries


async def _retrieve_legal_knowledge(
    # 函数 _retrieve_legal_knowledge 的初始化逻辑
    case_text: str,
    max_entries: int = 5,
) -> tuple[str, list[dict[str, str]]]:
    """从知识库中检索与案件相关的法律知识.

    检索优先级：**Neo        # 条件判断：处理业务逻辑
4j > SQLite FTS > 内存关键词匹配**。

    1. **Neo4j**：若 ``settings.NEO4J_URI`` 已配置且驱动可用，优先使用 Neo4j 检索。
    2. **SQLite FTS**：若 Neo4j 未配置或不可用，回退到 SQLite FTS 全文搜索
       （基于 :func:`ensure_fts_table` + :func:`search_entries`）。
    3. **内存关键词匹配**：若 SQLite FTS 仍未命中，回退到 ``_KEYWORD_LEGAL``
       在案件文本中的字面匹配并构造最小摘要。

    Args:
            # 条件判断：处理业务逻辑
        case_tex    # 异常处理：处理业务逻辑
t: 案件文本
        max_entries: 最大返回条目数

    Returns:
        tuple: (格式化的相关知识文本, 知识条目摘要列表).
              三级兜底均无命中时返回 ("", [])。
    """
    # 尝试执行可能抛出异常的代码
    try:
        # 1) 尝试 Neo4j
        neo4j_entries = await _retrieve_neo4j_knowledge(case_text, max_entries)
        # 条件判断: 检查 neo4j_entries
        if neo4j_entries:
            # 记录日志信息
            logger.info(f"Neo4j 命中 {len(neo4j_entries)} 条")
            # 返回处理结果
            return _format_knowledge_entries(neo4j_entries)

        # 2) 回退到 SQLite FTS
        keywords = [kw for kw in _KEYWORD_LEGAL if kw in case_text]
        # 条件判断: 检查 keywords
        if keywords:
            async with get_async_db_session() as db:
                # 异步等待操作完成
                await ensure_fts_table(db)
                # 初始化变量 results
                results = await search_entries(
                    db,
                    " ".join(keywords[:3]),
                    # 初始化变量 status
                    status=EntryStatus.active,
                    # 初始化变量 limit
                    limit=max_entries,
                )
            # 条件判断: 检查 results
            if results:
                logger.info(f"SQLite FTS 命中 {len(results)} 条")
                # 返回处理结果
                return _format_knowledge_entries(
                    [
                        {
                            "title": r.get("title", ""),
                            "summary": r.get("summary", "") or "",
                        }
                        # 遍历: for r in results
                        for r in results
                    ]
                )

        # 3) 内存关键词兜底：基于 _KEYWORD_LEGAL 命中给出最简摘要
        if keywords:
            # 记录日志信息
            logger.info(f"使用内存关键词兜底: {keywords[:3]}")
            # 初始化变量 stub_entries
            stub_entries = [
                {
                    "title": f"法律关键词命中：{kw}",
                    "summary": f"案件文本中检测到关键词 {kw}，建议结合相关法条进一步分析。",
                }
                # 遍历: for kw in keywords[:max_entries]
                for kw in keywords[:max_entries]
                # 条件判断：处理业务逻辑
        ]
            # 返回处理结果
            return _format_knowledge_entries(stub_entries)

        # 记录日志信息
        logger.info("案件文本中未匹配到法律关键词，跳过知识检索")
        # 返回处理结果
        return "", []

    # 捕获并处理异常
    except Exception:  # noqa: BLE001


    # 执行 _format_knowledge_entries 函数的核心逻辑
        logger.warning("知识检索异常，跳过知识注入", exc_info=True)
        # 返回处理结果
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
    # 条件判断: 检查 not entries
    if not entries:
        # 返回处理结果
        return "", []

    # 初始化变量 knowledge_parts
    knowledge_parts = ["【相关知识】"]
    # 初始化变量 total_len
    total_len = 0
    entries_info: list[dict[str, str]] = []

    # 遍历: for entry in entries:
    for entry in entries:
        # 初始化变量 title
        title = (entry.get("title") or "").strip()
        # 初始化变量 summary
        summary = (entry.get("summary") or "").strip()
        # 条件判断: 检查 not title
        if not title:
            continue
        # 初始化变量 snippet
        snippet = (
            summary[:_SUMMARY_SNIPPET_LENGTH]
            # 条件判断: 检查 len(summary) > _SUMMARY_SNIPPET_LENGTH
            if len(summary) > _SUMMARY_SNIPPET_LENGTH
            else summary
        )
        # 初始化变量 entry_text
        entry_text = f"[{title}] {snippet}" if snippet else f"[{title}]"

        # 条件判断: 检查 total_len + len(entry_text) > _MAX_SNIPPET_LENGTH
        if total_len + len(entry_text) > _MAX_SNIPPET_LENGTH:
            # 初始化变量 remaining
            remaining = _MAX_SNIPPET_LENGTH - total_len
            # 条件判断: 检查 remaining > _MIN_REMAINING
            if remaining > _MIN_REMAINING:
                # 初始化变量 entry_text
                entry_text = entry_text[:remaining] + "..."
                knowledge_parts.append(entry_text)
            break

        knowledge_parts.append(entry_text)
        total_len += len(entry_text)
        entries_info.append({"title": title, "summary": snippet})

    # 条件判断: 检查 not entries_info
    if not entries_info:
        # 返回处理结果
        return "", []
    # 返回处理结果
    return "\n\n".join(knowledge_parts), entries_info


# 应用装饰器: ANALYSIS_DURATION.time
@ANALYSIS_DURATION.time()
async def analyze_pipeline(
    # 函数 analyze_pipeline 的初始化逻辑
    case_text: str,
    mode: str = "auto",
) -> AnalysisResult:
    """主分析管道入口.

    根据案件复杂度自动选择单通道或多维    # 异常处理：处理业务逻辑
度分析策略。

    Args:
        case_text: 案件事实文本
        mode: 分析模式（"auto"、"single"、"multi"）

    Returns:
        AnalysisResult: 分析结果字典，包含时间戳和回退标志
    """
    # 尝试执行可能抛出异常的代码
    try:
        # 异步等待操作完成
        legal_knowledge, knowledge_entries = await _retrieve_legal_knowledge(case_text)
        knowledge_used: bool = bool(legal_knowledge)

        # 条件判断: 检查 legal_knowledge
        if legal_knowledge:
            # 记录日志信息
            logger.info(f"知识注入启用: {len(knowledge_entries)} 条知识条目")

        # 条件判断: 检查 AnalysisConfig.SC_ENABLED and mode != "s
        if AnalysisConfig.SC_ENABLED and mode != "single":
            # 记录日志信息
            logger.info(
                f"启用 Self-Consistency 多次采样: "
                f"samples={AnalysisConfig.SC_NUM_SAMPLES}, "
                f"temperature={AnalysisConfig.SC_TEMPERATURE}"
            )
            # 初始化变量 result
            result = await self_consistency_analysis(
                case_text, mode=mode,
                # 初始化变量 n_samples
                n_samples=AnalysisConfig.SC_NUM_SAMPLES,
                # 初始化变量 sample_temperature
                sample_temperature=AnalysisConfig.SC_TEMPERATURE,
                # 初始化变量 legal_knowledge
                legal_knowledge=legal_knowledge,
            )
            result["fallback"] = False
            result["timestamp"] = datetime.now(UTC).isoformat()
            result["knowledge_used"] = knowledge_used
            result["knowledge_entries"] = knowledge_entries
            # 返回处理结果
            return result

        complexity: ComplexityLevel = classify_complexity(case_text)
        # 记录日志信息
        logger.info(f"自动模式: 复杂度='{complexity}'")

        # 条件判断: 检查 mode == "single" or (
        if mode == "single" or (
            # 初始化变量 mode
            mode == "auto" and complexity == "simple"
        ):
            # 记录日志信息
            logger.info("推理模式: single")
            # 异步等待操作完成
            result: AnalysisResult = await single_pass_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )
        # 条件判断: 检查 elmode == "multi" or (
        elif mode == "multi" or (
            # 初始化变量 mode
            mode == "auto" and complexity in ("medium", "complex")
        ):
            # 记录日志信息
            logger.info("推理模式: multi")
            # 初始化变量 result
            result = await multi_dimension_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )
        # 其他情况的默认处理
        else:
            # 初始化变量 result
            result = await single_pass_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )

        # 条件判断: 检查 "ground_truth_analysis" not in result
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
        # 返回处理结果
        return result
    # 捕获并处理异常
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

# V1.2 新增阶段名常量
_STAGE_PATH_IDENTIFICATION: str = "path_identification"
_STAGE_SUBJECT_STRATIFICATION: str = "subject_stratification"
_STAGE_EVIDENCE_LAYERING: str = "evidence_layering"
_STAGE_BOUNDARY_CHECK: str = "boundary_check"


# ---------------------------------------------------------------------------
# V2 辅助：构造默认维度结果 / 兜底结果
# ---------------------------------------------------------------------------


def _build_default_v2_dimension(
    # 函数 _build_default_v2_dimension 的初始化逻辑
    dim_name: str,


    # 执行 _build_default_v2_dimension 函数的核心逻辑
    fallback_reason: str = "",
) -> dict[str, Any]:
    """构造 V2 协议的默认维度结果.

    当某维度 LLM 调用失败或 JSON 解析失败时使用.
    """
    # 返回处理结果
    return {
        "tier": _V2_DEFAULT_TIER,
        "reasoning": (
            f"维度 {dim_name} 分析失败，使用默认档级 {_V2_DEFAULT_TIER}。"
            + (f"原因：{fallback_reason}" if fallback_reason else "")
        ),
        "key_indicators": [],


    # 执行 _build_default_v2_analysis_result 函数的核心逻辑
        "triggered_rules": [],
        "fallback": True,
    }


def _build_default_v2_analysis_result(
    # 函数 _build_default_v2_analysis_result 的初始化逻辑
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
        # 初始化变量 rule_hits
        rule_hits=[],
    )
    # 返回处理结果
    return {
        "version": "v2",
        "subjective_knowledge": _V2_DEFAULT_KNOWLEDGE,
      # 条件判断：处理业务逻辑
      "sentence": _V2_DEFAULT_SENTENCE,
        "court": "基层人民法院",
          # 条件判断：处理业务逻辑
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
    # 条件判断: 检查 not tags
    if not tags:
        # 返回处理结果
        return "（无候选标签）"
    lines: list[str] = []
    # 遍历: for t in tags:
    for t in tags:
        # 条件判断: 检查 isinstance(t, dict)
        if isinstance(t, dict):
            # 初始化变量 tag_id
            tag_id = t.get("tag_id", "?")
            # 初始化变量 name
            name = t.get("name", "")
            # 初始化变量 category
            category = t.get("category", "")
            # 初始化变量 extraction_hints
            extraction_hints = t.get("extraction_hints"    # 条件判断：处理业务逻辑
, [])
        # 其他情况的默认处理
        else:
            # 初始化变量 tag_id
            tag_id = getattr(t, "tag_id", "?")
            # 初始化变量 name
            name = getattr(t, "name", "")
            # 初始化变量 category
            category = getattr(t, "category", "")
            # 初始化变量 extraction_hints
            extraction_hints = getattr(t, "extraction_hints", []    # 循环遍历：处理业务逻辑
)
        # 初始化变量 hints_str
        hints_str = "、".join(extraction_hints or []) or "—"
        lines.append(f"- {tag_id} {name}（{category}）| 提示词：{hints_str}")
    # 返回处理结果
    return "\n".join(lines)


def _format_rule_candidates(rules: list[Rule] | None) -> str:
    """把 Rule 列表格式化为 prompt 注入片段（候选列表）."""
    # 条件判断: 检查 not rules
    if not rules:
        # 返回处理结果
        return "（无候选规则）"
    lines: list[str] = []
    # 遍历: for r in rules:
    for r in rules:
        # 初始化变量 weight
        weight = f"{r.weight:.2f}" if isinstance(r.weight, (int, float)) else "n/a"
        # 初始化变量 conclusion
        conclusion = (r.conclusion or "").strip()[:80]


    # 执行 _format_matched_tags_for_prompt 函数的核心逻辑
        conditions = (r.conditions or "").strip()[:120]
        lines.append(
            f"- {r.rule_id} {r.name} (weight={weight})\n"
            f"   条件：{conditions}\n"
            f"   结论：{conclusion}"
        )
    # 返回处理结果
    return "\n".join(lines)


def _format_matched_tags_for_prompt(matches: list[TagMatch]) -> str:
    """把已抽取的 TagMatch 列表格式化为 prompt 注入片段."""
    # 条件判断: 检查 not matches
    if not matches:
        # 返回处理结果
        return "（未抽取到任何事实标签）"
    lines: list[str] = []


    # 执行 _format_matched_rules_for_prompt 函数的核心逻辑
    for m in matches[:_V2_TAG_INJECTION_TOP_N]:
        # 初始化变量 conf
        conf = f"{m.confidence:.2f}" if isinstance(m.confidence, (int, float)) else "n/a"
        # 初始化变量 text
        text = (m.matched_text or "").strip()[:60]
        lines.append(f"- {m.tag_id}（{m.match_type}，conf={conf}）：{text}")
    # 返回处理结果
    return "\n".join(lines)


def _format_matched_rules_for_prompt(rules: list[Rule]) -> str:
    """把命中的 Rule 列表格式化为 prompt 注入片段."""
    # 条件判断: 检查 not rules
    if not rules:
        # 返回处理结果
        return "（未命中任何具体规则）"
    lines: list[str] = []
    # 遍历: for r in rules[:_V2_RULE_INJECTION_TOP_N]:
    for r in rules[:_V2_RULE_INJECTION_TOP_N]:
        # 初始化变量 weight
        weight = f"{r.weight:.2f}" if isinstance(r.weight, (int, float)) else "n/a"
        # 初始化变量 conclusion
        conclusion = (r.conclusion or "").strip()[:80]
        # 初始化变量 article
        article = (r.article or "").strip()
        # 初始化变量 suffix
        suffix = f" | {article}" if article else ""
        lines.append(f"- {r.rule_id} {r.name} (weight={weight}): {conclusion}{suffix}")
    # 返回处理结果
    return "\n".join(lines)


# -------------------------------------------------------
# V2 辅助：单维度 tier 抽取
# -------------------------------------------------------


def _extract_tier_from_v2_response(result: dict[str, Any]) -> str:
    """从 V2 维度 LLM 响应中抽取档级.

    支持 ``tier`` 字段、``final_tier`` 字段或嵌套字段; 失败时返回 T2.
    """
    # 条件判断: 检查 not isinstance(result, dict)
    if not isinstance(result, dict):
        # 返回处理结果
        return _V2_DEFAULT_TIER

    # 常见字段名
    for key in ("tier", "final_tier", "档级", "tier_value"):
        # 条件判断：处理业务逻辑
        if key in result:
            # 返回处理结果
            return TierEnum.coerce(result[key]).value

    # 嵌套字段
    gta = result.get("ground_truth_analysis")
    # 条件判断: 检查 isinstance(gta, dict)
    if isinstance(gta, dict):
        # 遍历: for dim in ("dimension1", "dimension2", "dimension
        for dim in ("dimension1", "dimension2", "dimension3"):
            d = gta.get(dim)
            # 条件判断: 检查 isinstance(d, dict) and "tier" in d
            if isinstance(d, dict) and "tier" in d:
                # 返回处理结果
                return TierEnum.coerce(d["tier"]).value

    # 返回处理结果
    return _V2_DEFAULT_TIER


def _build_v2_dimension_result(
    # 函数 _build_v2_dimension_result 的初始化逻辑
    dim_name: str,
    raw_result: dict[str, Any],
    fallback_used: bool = False,
) -> dict[str, Any]:
    """把 LLM 返回的 dict 转换为 V2 维度结果结构.

    适配 LLM 偶尔输出 ``{tier, reasoning, key_indicators, triggered_rules}``
    或带其他多余字段的情况.
    """
    # 初始化变量 tier
    tier = _extract_tier_from_v2_response(raw_result)
    # 初始化变量 reasoning
    reasoning = raw_result.get("reasoning") or raw_result.get("analysis") or ""
    # 条件判断: 检查 not isinstance(reasoning, str)
    if not isinstance(reasoning, str):
        # 初始化变量 reasoning
        reasoning = str(reasoning)

    # 触发规则
    triggered_raw = raw_result.get("triggered_rules", [])
    # 条件判断: 检查 not isinstance(triggered_raw, list)
    if not isinstance(triggered_raw, list):
        # 初始化变量 triggered_raw
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

    # 条件判断: 检查 dim_name == "dimension1"
    if dim_name == "dimension1":
        # 初始化变量 indicators
        indicators = raw_result.get("key_indicators", [])
        # 条件判断: 检查 not isinstance(indicators, list)
        if not isinstance(indicators, list):
            # 初始化变量 indicators
            indicators = []
        base["key_indicators"] = [str(x) for x in indicators][:10]
    # 条件判断: 检查 eldim_name == "dimension2"
    elif dim_name == "dimension2":
        # 初始化变量 pattern
        pattern = raw_result.get("pattern_match", "")
        base["pattern_match"] = str(pattern) if pattern else ""
    # 条件判断: 检查 eldim_name == "dimension3"
    elif dim_name == "dimension3":
        # 初始化变量 contradictions
        contradictions = raw_result.get("contradictions", [])
        # 条件判断: 检查 not isinstance(contradictions, list)
        if not isinstance(contradictions, list):


    # 执行 _format_v2_dimension1_prompt 函数的核心逻辑
            contradictions = []
        base["contradictions"] = [str(x) for x in contradictions][:10]

    # 返回处理结果
    return base


# ---------------------------------------------------------------------------
# V2 辅助：构造 V2 维度 prompt
# ---------------------------------------------------------------------------


def _format_v2_dimension1_prompt(
    # 函数 _format_v2_dimension1_prompt 的初始化逻辑
    *,
    case_text: str,


    # 执行 _format_v2_dimension2_prompt 函数的核心逻辑
    matched_tags_text: str,
    triggered_rules_text: str,
    legal_knowledge: str,
) -> str:
    # 返回处理结果
    return V2_DIMENSION1_PROMPT.format(
        # 初始化变量 matched_tags
        matched_tags=matched_tags_text,
        # 初始化变量 triggered_rules
        triggered_rules=triggered_rules_text,
        # 初始化变量 legal_knowledge
        legal_knowledge=legal_knowledge or "（无相关检索知识）",
        # 初始化变量 case_text
        case_text=case_text,
    )


def _format_v2_dimension2_prompt(
    # 函数 _format_v2_dimension2_prompt 的初始化逻辑
    *,
    case_text: str,


    # 执行 _format_v2_dimension3_prompt 函数的核心逻辑
    matched_tags_text: str,
    triggered_rules_text: str,
    legal_knowledge: str,
) -> str:
    # 返回处理结果
    return V2_DIMENSION2_PROMPT.format(
        # 初始化变量 matched_tags
        matched_tags=matched_tags_text,
        # 初始化变量 triggered_rules
        triggered_rules=triggered_rules_text,
        # 初始化变量 legal_knowledge
        legal_knowledge=legal_knowledge or "（无相关检索知识）",
        # 初始化变量 case_text
        case_text=case_text,
    )


def _format_v2_dimension3_prompt(
    # 函数 _format_v2_dimension3_prompt 的初始化逻辑
    *,
    case_text: str,
    matched_tags_text: str,
    triggered_rules_text: str,
    legal_knowledge: str,
    prior_dim1_text: str,
    prior_dim2_text: str,
) -> str:
    # 返回处理结果
    return V2_DIMENSION3_PROMPT.format(
        # 初始化变量 prior_dim1
        prior_dim1=prior_dim1_text,
        # 初始化变量 prior_dim2
        prior_dim2=prior_dim2_text    # 条件判断：处理业务逻辑
,
        # 初始化变量 matched_tags
        matched_tags=matched_tags_text,
        # 初始化变量 triggered_rules
        triggered_rules=triggered_rules_text,
        # 初始化变量 legal_knowledge
        legal_knowledge=legal_knowledge or "（无相关检索知识）",
        # 初始化变量 case_text
        case_text=case_text,
    )


# ---------------------------------------------------------------------
# V2 辅助：V2 标签抽取（关键词 + 可选 LLM）
# ---------------------------------------------------------------------------


async def _extract_tags_v2(
    # 函数 _extract_tags_v2 的初始化逻辑
    case_text: str,
    rules: list[Rule] | None = None,
) -> list[TagMatch]:
    """V2 协议的标签抽取（先走关键词，必要时 LLM 兜底）.

    复用 :func:`extract_tags` 的实现；失败时返回空列表，确保不阻断后续流程.
    """
    # 尝试执行可能抛出异常的代码
    try:
        # 返回处理结果
        return extract_tags(case_text, rules=rules or [])
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"V2 标签抽取异常: {exc}")
        # 返回处理结果
        return []


# ---------------------------------------------------------------------------
# V2 辅助：V2 规则匹配（关键词 / LLM 兜底）
# --------------------------------------------------------


def _match_rules_v2(
    # 函数 _match_rules_v2 的初始化逻辑
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
    # 初始化变量 rules
    rules = load_rules()
    # 条件判断: 检查 not rules
    if not rules:
        # 返回处理结果
        return []

    # 收集案件文本里的关键词（来自 tag_matches + 案件文本）
    case_keywords: set[str] = set()
    # 遍历: for m in tag_matches:
    for m in tag_matches:
        # 遍历: for token in (m.tag_id, m.matched_text):
        for token in (m.tag_id, m.matched_text):
            # 条件判断: 检查 token
            if token:
                case_keywords.add(str(token).strip())

    # 简单分词：使用案件文本中出现的中文双字以上片段
    if case_text:
        # 遍历: for ch in re.findall(r"[\u4e00-\u9fff]{2,}", case_
        for ch in re.findall(r"[\u4e00-\u9fff]{2,}", case_text):
            case_keywords.add(ch)

    scored: list[tuple[int, Rule]] = []
    # 遍历: for r in rules:
    for r in rules:
        # 初始化变量 haystack
        haystack = " ".join(
            [
                r.name or "",
                r.conclusion or "",
                r.conditions or "",
                " ".join(r.applicable_scenarios or []),
            ]
        )
        # 初始化变量 hits
        hits = sum(1 for kw in case_keywords if kw and kw in haystack)
        # 至少 1 个命中且权重 > 0
        if hits > 0 and (r.weight or 0) > 0:
            scored.append((hits, r))

    # 按命中数 * 权重排序
    scored.sort(key=lambda x: x[0] * (x[1].weight or 0.0), reverse=True)
    # 初始化变量 matched
    matched = [r for _, r in scored[:_V2_RULE_INJECTION_TOP_N]]

    # 条件判断: 检查 not matched
    if not matched:
        # 兜底：返回权重最高的 1 条规则
        sorted_rules = sorted(
            rules, key=lambda r: r.weight or 0.0, reverse=True
        )
        # 条件判断: 检查 sorted_rules
        if sorted_rules:
            # 初始化变量 matched
            matched = [sorted_rules[0]]

    # 返回处理结果
    return matched


# ---------------------------------------------------------------------------
# V2 辅助：单维度 LLM 调用（带降级）
# ---------------------------------------------------------------------------


async def _v2_run_single_dimension(
    # 函数 _v2_run_single_dimension 的初始化逻辑
    case_text: str,
    system_prompt: str,
    dim_name: str,
    user_prompt: str,
    temperature: float = _V2_DEFAULT_TEMPERATURE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """V2 协议下单个维度的 LLM 调用.

    返回 ``(dimension_result, timing_meta)``. 失败时使用默认档级.
    """
    # 初始化变量 start
    start = time.perf_counter()
    # 初始化变量 start_ts
    start_ts = datetime.now(UTC).isoformat()
    # 初始化变量 status
    status = "success"
    error_info: dict[str, str] = {}

    dim_result: dict[str, Any] = _build_default_v2_dimension(dim_name)
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 response
        response = await call_ollama_with_retry(
            user_prompt,
            # 初始化变量 system_prompt
            system_prompt=system_prompt,
            # 初始化变量 temperature
            temperature=temperature,
        )
        reasoning_text, _ = _extract_think_content(response)
        # 初始化变量 cleaned
        cleaned = sanitize_json_string(response)
        # 初始化变量 parsed
        parsed = robust_json_parse(cleaned, default=dim_result)
        # 兼容 LLM 返回的嵌套结构
        if "ground_truth_analysis" in parsed and dim_name in parsed["ground_truth_analysis"]:
            # 初始化变量 parsed
            parsed = parsed["ground_truth_analysis"][dim_name]
            dim_result = _build_v2_dimension_result(dim_name, parsed, fallback_used=False)
        # 条件判断: 检查 reasoning_text
        if reasoning_text:
            dim_result["reasoning_process"] = reasoning_text
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        # 初始化变量 error_info
        error_info = {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "error_time": datetime.now(UTC).isoformat(),
        }
        # 记录日志信息
        logger.error(f"V2 {dim_name} 异常: {exc}")
        # 初始化变量 dim_result
        dim_result = _build_default_v2_dimension(
            dim_name, fallback_reason=str(exc)
        )

    # 初始化变量 duration_ms
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    timing: dict[str, Any] = {


    # 执行 _build_v2_prior_context 函数的核心逻辑
        "status": status,
        # 执行 _shorten 函数的核心逻辑
        "duration_ms": duration_ms,
        "start_time": start_ts,
        "end_time": datetime.now(UTC).isoformat(),
        **error_info,
    }
    # 返回处理结果
    return dim_result, timing


# ---------------------------------------------------------------------------
# V2 辅助：prior context 构建
# ---------------------------------------------------------------------------


def _build_v2_prior_context(
    # 函数 _build_v2_prior_context 的初始化逻辑
    dim1: dict[str, Any],
    dim2: dict[str, Any],


    # 执行 _record_stage 函数的核心逻辑
) -> tuple[str, str]:
    """构建维度 3 用的前置上下文（事实审查 + 模式匹配摘要）.

    返回 ``(prior_dim1_text, prior_dim2_text)`` 各自最长 300 字.
    """
    def _shorten(d: dict[str, Any]) -> str:
        # 函数 _shorten 的初始化逻辑
        tier = d.get("tier", _V2_DEFAULT_TIER)
        # 初始化变量 reasoning
        reasoning = d.get("reasoning", "无")
        # 条件判断: 检查 d.get("fallback")
        if d.get("fallback"):
            # 返回处理结果
            return f"[默认档级] {tier}（该维度分析失败）"
        # 初始化变量 text
        text = f"档级：{tier}\n推理摘要：{reasoning[:300]}"
        # 返回处理结果
        return text

    # 返回处理结果
    return _shorten(dim1), _shorten(dim2)


# ---------------------------------------------------------------------------
# V2 辅助：阶段包装（异常隔离 + 计时）
# ---------------------------------------------------------------------------


def _record_stage(
    # 函数 _record_stage 的初始化逻辑
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


# 应用装饰器: ANALYSIS_DURATION.time
@ANALYSIS_DURATION.time()
async def analyze_pipeline_v2(
    # 函数 analyze_pipeline_v2 的初始化逻辑
    case_text: str,
    mode: str = "auto",
) -> AnalysisResultV2:
    """V2 协议下的主分析管道入口（V1.2 升级版）.

    新8步骤流程：
    1. 标签提取 (tag_extractor)
    2. 规范路径识别 (B1)
    3. 多主体分层 (B2)
    4. 证据强度分层 (B3)
    5. 边界提醒 (B4)
    6. 三维度打分（基于EvidenceLayerReport）
    7. 结论生成
    8. 冲突校验

    任一阶段失败不阻断，标记 ``fallback=True`` 并记录 ``failed_stage``.
    """
    meta: PipelineMeta = {
        "stage_durations_ms": {},
        "stage_status": {},
    }
    failed_stage: str = ""
    # 初始化变量 overall_start
    overall_start = time.perf_counter()

    # 前置步骤：复杂度分类（保留）
    stage_start = time.perf_counter()
    # 尝试执行可能抛出异常的代码
    try:
        complexity: ComplexityLevel = classify_complexity(case_text)
        _record_stage(
            meta, _STAGE_COMPLEXITY,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        complexity = "medium"
        _record_stage(
            meta, _STAGE_COMPLEXITY,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_COMPLEXITY
        # 记录日志信息
        logger.warning(f"复杂度分类失败: {exc}")

    # 前置步骤：知识检索（保留）
    stage_start = time.perf_counter()
    knowledge_text: str = ""
    knowledge_entries: list[dict[str, str]] = []
    knowledge_used: bool = False
    # 尝试执行可能抛出异常的代码
    try:
        # 异步等待操作完成
        knowledge_text, knowledge_entries = await _retrieve_legal_knowledge(case_text)
        # 初始化变量 knowledge_used
        knowledge_used = bool(knowledge_text)
        _record_stage(
            meta, _STAGE_KNOWLEDGE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if knowledge_text else "skipped",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_KNOWLEDGE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
       # 异常处理：处理业务逻辑
     )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_KNOWLEDGE
        # 记录日志信息
        logger.warning(f"知识检索失败: {exc}")

    # ========== V1.2 新 8 步骤流程 ==========

    # Step 1: 标签提取
    stage_start = time.perf_counter()
    tag_matches: list[TagMatch] = []
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 tag_matches
        tag_matches = await _extract_tags_v2(case_text, rules=None)
        _record_stage(
            meta, _STAGE_TAGS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if tag_matches else "skipped",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_TAGS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        failed_stage = failed_stage or _STAGE_TAGS
        # 记录日志信息
        logger.warning(f"标签提取失败: {exc}")

    matched_tag_ids: list[str] = list({m.tag_id for m in tag_matches})

    # Step 2: 规范路径识别 (B1)
    stage_start = time.perf_counter()
    # 初始化变量 identified_path
    identified_path = "规范路径待核实"
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 identified_path
        identified_path = identify_legal_path(case_text)
        _record_stage(
            meta, _STAGE_PATH_IDENTIFICATION,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_PATH_IDENTIFICATION,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_PATH_IDENTIFICATION
        # 记录日志信息
        logger.warning(f"规范路径识别失败: {exc}")

    # Step 3: 多主体分层 (B2)
    stage_start = time.perf_counter()
    subjects = []
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 subjects
        subjects = stratify_subjects(case_text)
        _record_stage(
            meta, _STAGE_SUBJECT_STRATIFICATION,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if subjects else "skipped",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_SUBJECT_STRATIFICATION,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_SUBJECT_STRATIFICATION
        # 记录日志信息
        logger.warning(f"多主体分层失败: {exc}")

    # Step 4: 证据强度分层 (B3)
    stage_start = time.perf_counter()
    evidence_layers = []
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 evidence_layers
        evidence_layers = build_evidence_layers(case_text)
        _record_stage(
            meta, _STAGE_EVIDENCE_LAYERING,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if evidence_layers else "skipped",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_EVIDENCE_LAYERING,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_EVIDENCE_LAYERING
        # 记录日志信息
        logger.warning(f"证据强度分层失败: {exc}")

    # Step 5: 边界提醒 (B4)
    stage_start = time.perf_counter()
    # 初始化变量 boundary_alerts
    boundary_alerts = []
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 boundary_alerts
        boundary_alerts = check_boundary_alerts(case_text)
        _record_stage(
            meta, _STAGE_BOUNDARY_CHECK,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if boundary_alerts else "skipped",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_BOUNDARY_CHECK,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_BOUNDARY_CHECK
        # 记录日志信息
        logger.warning(f"边界提醒失败: {exc}")

    # 构建 EvidenceLayerReport
    evidence_report = EvidenceLayerReport(
        identified_path=identified_path,
        # 初始化变量 subjects
        subjects=subjects,
        # 初始化变量 evidence_layers
        evidence_layers=evidence_layers,
        # 初始化变量 boundary_alerts
        boundary_alerts=boundary_alerts,
        # 初始化变量 is_primary_path_bangxin
        is_primary_path_bangxin=(identified_path == "帮信罪主路径"),
    )

    # Step 6: 三维度打分（基于 EvidenceLayerReport）
    # 规则匹配（保留）
    stage_start = time.perf_counter()
    rule_hits: list[Rule] = []
    # 尝试执行可能抛出异常的代码
    try:
        rule_hits = _match_rules_v2(case_text, tag_matches)
        _record_stage(
            meta, _STAGE_RULES,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if rule_hits else "skipped",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_RULES,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_RULES
        # 记录日志信息
        logger.warning(f"规则匹配失败: {exc}")

    triggered_rule_ids: list[str] = [r.rule_id for r in rule_hits]

    # 初始化变量 matched_tags_text
    matched_tags_text = _format_matched_tags_for_prompt(tag_matches)
    # 初始化变量 triggered_rules_text
    triggered_rules_text = _format_matched_rules_for_prompt(rule_hits)

    # 集成 guard_against_single_layer_override 机制
    can_affirm_knowledge = guard_against_single_layer_override(evidence_report)

    # 维度 1
    stage_start = time.perf_counter()
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 dim1_prompt
        dim1_prompt = _format_v2_dimension1_prompt(
            # 初始化变量 case_text
            case_text=case_text,
            # 初始化变量 matched_tags_text
            matched_tags_text=matched_tags_text,
            # 初始化变量 triggered_rules_text
            triggered_rules_text=triggered_rules_text,
            # 初始化变量 legal_knowledge
            legal_knowledge=knowledge_text,
        )
        # 异步等待操作完成
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
        # 条件判断: 检查 dim1_meta.get("status") == "failed"
        if dim1_meta.get("status") == "failed":
            # 初始化变量 failed_stage
            failed_stage = failed_stage or _STAGE_DIM1
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        dim1_result = _build_default_v2_dimension("dimension1", fallback_reason=str(exc))
        _record_stage(
            meta, _STAGE_DIM1,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_DIM1
        # 记录日志信息
        logger.warning(f"维度1执行失败: {exc}")

    # 维度 2
    stage_start = time.perf_counter()
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 dim2_prompt
        dim2_prompt = _format_v2_dimension2_prompt(
            # 初始化变量 case_text
            case_text=case_text,
            # 初始化变量 matched_tags_text
            matched_tags_text=matched_tags_text,
            # 初始化变量 triggered_rules_text
            triggered_rules_text=triggered_rules_text,
            # 初始化变量 legal_knowledge
            legal_knowledge=knowledge_text,
        )
        # 异步等待操作完成
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
        # 条件判断: 检查 dim2_meta.get("status") == "failed"
        if dim2_meta.get("status") == "failed":
            # 初始化变量 failed_stage
            failed_stage = failed_stage or _STAGE_DIM2
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        dim2_result = _build_default_v2_dimension("dimension2", fallback_reason=str(exc))
        _record_stage(
            meta, _STAGE_DIM2,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_DIM2
        # 记录日志信息
        logger.warning(f"维度2执行失败: {exc}")

    # 维度 3（带前置上下文）
    stage_start = time.perf_counter()
    prior_dim1_text, prior_dim2_text = _build_v2_prior_context(dim1_result, dim2_result)
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 dim3_prompt
        dim3_prompt = _format_v2_dimension3_prompt(
            # 初始化变量 case_text
            case_text=case_text,
            # 初始化变量 matched_tags_text
            matched_tags_text=matched_tags_text,
            # 初始化变量 triggered_rules_text
            triggered_rules_text=triggered_rules_text,
            # 初始化变量 legal_knowledge
            legal_knowledge=knowledge_text,
            # 初始化变量 prior_dim1_text
            prior_dim1_text=prior_dim1_text,
            # 初始化变量 prior_dim2_text
            prior_dim2_text=prior_dim2_text,
        )
        # 异步等待操作完成
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
        # 条件判断: 检查 dim3_meta.get("status") == "failed"
        if dim3_meta.get("status") == "failed":
            # 初始化变量 failed_stage
            failed_stage = failed_stage or _STAGE_DIM3
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        dim3_result = _build_default_v2_dimension("dimension3", fallback_reason=str(exc))
        _record_stage(
            meta, _STAGE_DIM3,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_DIM3
        # 记录日志信息
        logger.warning(f"维度3执行失败: {exc}")

    # 档级组合
    stage_start = time.perf_counter()
    # 尝试执行可能抛出异常的代码
    try:
        verdict: FinalVerdict = combine_tiers(
            dim1_result.get("tier", _V2_DEFAULT_TIER),
            dim2_result.get("tier", _V2_DEFAULT_TIER),
            dim3_result.get("tier", _V2_DEFAULT_TIER),
            # 初始化变量 rule_hits
            rule_hits=rule_hits,
        )
        _record_stage(
            meta, _STAGE_COMBINE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        verdict = combine_tiers(
            _V2_DEFAULT_TIER, _V2_DEFAULT_TIER, _V2_DEFAULT_TIER, rule_hits=[]
        )
        _record_stage(
            meta, _STAGE_COMBINE,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_COMBINE
        # 记录日志信息
        logger.warning(f"档级组合失败: {exc}")

    # Step 7: 结论生成
    stage_start = time.perf_counter()
    conclusion_text: str = ""
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 conclusion_text
        conclusion_text = await generate_conclusion(
            # 初始化变量 verdict
            verdict=verdict,
            # 初始化变量 rule_hits
            rule_hits=rule_hits,
            # 初始化变量 tags
            tags=tag_matches,
            # 初始化变量 case_text
            case_text=case_text,
            # 初始化变量 dimension_tiers
            dimension_tiers={
                "dimension1": dim1_result.get("tier", _V2_DEFAULT_TIER),
                "dimension2": dim2_result.get("tier", _V2_DEFAULT_TIER),
                "dimension3": dim3_result.get("tier", _V2_DEFAULT_TIER),
            },
            # 初始化变量 conflicts
            conflicts=[],  # 冲突检测在 Step 8
            evidence_report=evidence_report,  # 传递证据层报告
        )
        _record_stage(
            meta, _STAGE_CONCLUSION,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success" if conclusion_text else "skipped",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_CONCLUSION,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_CONCLUSION
        # 记录日志信息
        logger.warning(f"结论生成失败: {exc}")

    # Step 8: 冲突校验
    stage_start = time.perf_counter()
    conflicts: list[Conflict] = []
    # 尝试执行可能抛出异常的代码
    try:
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
        # 初始化变量 conflicts
        conflicts = detect_conflicts(
            tag_matches, rule_hits, dim_results_for_conflict
        )
        _record_stage(
            meta, _STAGE_CONFLICTS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "success",
        )
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        _record_stage(
            meta, _STAGE_CONFLICTS,
            round((time.perf_counter() - stage_start) * 1000, 2),
            "failed",
        )
        # 初始化变量 failed_stage
        failed_stage = failed_stage or _STAGE_CONFLICTS
        # 记录日志信息
        logger.warning(f"冲突校验失败: {exc}")

    # 整体置信度：维度的均值（0-1）
    confidences: list[float] = []
    # 遍历: for d in (dim1_result, dim2_result, dim3_result):
    for d in (dim1_result, dim2_result, dim3_result):
        c = d.get("confidence")
        # 条件判断: 检查 isinstance(c, (int, float))
        if isinstance(c, (int, float)):
            confidences.append(max(0.0, min(1.0, float(c))))
    overall_confidence: float = (
        round(sum(confidences) / len(confidences), 4) if confidences else 0.5
    )

    # 冲突序列化为 dict
    conflicts_payload: list[dict[str, Any]] = [c.to_dict() for c in conflicts]

    # 根据路径识别结果决定是否引用第287-2条
    should_cite_article = evidence_report.should_cite_article_287_2()
    # 初始化变量 scoring_mode
    scoring_mode = evidence_report.get_scoring_mode()

    result: AnalysisResultV2 = {
        "version": "v2",
        "subjective_knowledge": (
            dim1_result.get("key_indicators", [None])[0]
            # 条件判断: 检查 dim1_result.get("key_indicators")
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
            # 遍历: for s in (_STAGE_DIM1, _STAGE_DIM2, _STAGE_DIM3, _
            for s in (_STAGE_DIM1, _STAGE_DIM2, _STAGE_DIM3, _STAGE_COMBINE)
        ),
        "timestamp": datetime.now(UTC).isoformat(),
        "knowledge_used": knowledge_used,
        "knowledge_entries": knowledge_entries,
        "disclaimer": (
            "本结论由 V2 协议（三维度 × 四档）生成，"
            "并集成了规则、标签、冲突检测结果，仅供办案人员参考。"
        ),
        # V1.2 新增字段
        "identified_path": identified_path,  # type: ignore[typeddict-unknown-key]
        "scoring_mode": scoring_mode,  # type: ignore[typeddict-unknown-key]
        "should_cite_article_287_2": should_cite_article,  # type: ignore[typeddict-unknown-key]
        "can_affirm_knowledge": can_affirm_knowledge,  # type: ignore[typeddict-unknown-key]
        "evidence_layer_count": len(evidence_layers),  # type: ignore[typeddict-unknown-key]
        "boundary_alert_count": len(boundary_alerts),  # type: ignore[typeddict-unknown-key]
    }

    # 条件判断: 检查 failed_stage
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

    # 尝试执行可能抛出异常的代码
    try:
        ANALYSIS_COUNTER.labels(mode=mode, status="success").inc()
    # 捕获并处理异常
    except Exception:  # noqa: BLE001
        pass

    # 记录日志信息
    logger.info(
        f"V2 管道完成 (V1.2): complexity={complexity}, "
        f"path={identified_path}, scoring_mode={scoring_mode}, "
        f"final_tier={verdict.get('final_tier')}, "
        f"fallback={result['fallback']}, "
        f"total_ms={meta['stage_durations_ms'].get('_total')}"
    )

    # 返回处理结果
    return result


# ---------------------------------------------------------------------------
# 兼容性别名 — V1 协议默认行为不变
# ---------------------------------------------------------------------------


async def analyze_pipeline(  # noqa: F811
    # 函数 analyze_pipeline 的初始化逻辑
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
    # 条件判断: 检查 version == "v1"
    if version == "v1":
        # 委托给原 V1 实现（这里通过包内函数名重命名解决）
        return await _analyze_pipeline_v1(case_text, mode=mode)
    # 默认 v2
    return await analyze_pipeline_v2(case_text, mode=mode)


async def _analyze_pipeline_v1(case_text: str, mode: str = "auto") -> AnalysisResult:
    """V1 协议下的主分析管道入口（保留 0-10 评分，向后兼容）."""
    # 尝试执行可能抛出异常的代码
    try:
        # 异步等待操作完成
        legal_knowledge, knowledge_entries = await _retrieve_legal_knowledge(case_text)
        knowledge_used: bool = bool(legal_knowledge)

        # 条件判断: 检查 legal_knowledge
        if legal_knowledge:
            # 记录日志信息
            logger.info(f"知识注入启用: {len(knowledge_entries)} 条知识条目")

        # 条件判断: 检查 AnalysisConfig.SC_ENABLED and mode != "s
        if AnalysisConfig.SC_ENABLED and mode != "single":
            # 记录日志信息
            logger.info(
                f"启用 Self-Consistency 多次采样: "
                f"samples={AnalysisConfig.SC_NUM_SAMPLES}, "
                f"temperature={AnalysisConfig.SC_TEMPERATURE}"
            )
            # 初始化变量 result
            result = await self_consistency_analysis(
                case_text, mode=mode,
                # 初始化变量 n_samples
                n_samples=AnalysisConfig.SC_NUM_SAMPLES,
                # 初始化变量 sample_temperature
                sample_temperature=AnalysisConfig.SC_TEMPERATURE,
                # 初始化变量 legal_knowledge
                legal_knowledge=legal_knowledge,
            )
            result["fallback"] = False
            result["timestamp"] = datetime.now(UTC).isoformat()
            result["knowledge_used"] = knowledge_used
            result["knowledge_entries"] = knowledge_entries
            # 返回处理结果
            return result

        complexity: ComplexityLevel = classify_complexity(case_text)
        # 记录日志信息
        logger.info(f"自动模式: 复杂度='{complexity}'")

        # 条件判断: 检查 mode == "single" or (
        if mode == "single" or (
            # 初始化变量 mode
            mode == "auto" and complexity == "simple"
        ):
            # 记录日志信息
            logger.info("推理模式: single")
            # 异步等待操作完成
            result: AnalysisResult = await single_pass_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )
        # 条件判断: 检查 elmode == "multi" or (
        elif mode == "multi" or (
            # 初始化变量 mode
            mode == "auto" and complexity in ("medium", "complex")
        ):
            # 记录日志信息
            logger.info("推理模式: multi")
            # 初始化变量 result
            result = await multi_dimension_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )
        # 其他情况的默认处理
        else:
            # 初始化变量 result
            result = await single_pass_analysis(
                case_text, mode, legal_knowledge=legal_knowledge,
            )

        # 条件判断: 检查 "ground_truth_analysis" not in result
        if "ground_truth_analysis" not in result:
            result["ground_truth_analysis"] = {
                "dimension1": _build_default_dimension(),
         # 捕获异常：处理业务逻辑
           "dimension2": _build_default_dimension(),
                "dimension3": _build_default_dimension(),
            }

        result["fallback"] = result.get("fallback", False)
        result["timestamp"] = datetime.now(UTC).isoformat()
        result["knowledge_used"] = knowledge_used
        result["knowledge_entries"] = knowledge_entries

        ANALYSIS_COUNTER.labels(mode=mode, status="success").inc()
        # 返回处理结果
        return result
    # 捕获并处理异常
    except Exception:
        ANALYSIS_COUNTER.labels(mode=mode, status="error").inc()
        raise
