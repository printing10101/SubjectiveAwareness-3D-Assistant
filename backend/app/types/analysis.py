"""分析相关类型定义.

定义分析管道中使用所有复杂数据结构的 TypedDict 类型，
确保类型安全、代码可读性和静态类型检查的有效性。

V1 协议（默认）使用 0-10 评分；V2 协议（``app.types.analysis_v2``）
使用"三维度 × 四档"档级 + 规则/标签/冲突整合，通过
``version: Literal["v1", "v2"]`` 字段区分。旧 v1 数据仍可被读取，
新写入结果可显式指定 version。
"""

from typing import Any, Literal, NotRequired

from typing_extensions import TypedDict


class DimensionResult(TypedDict):
    """维度分析基础结果.

    所有分析维度共享的基础字段。

    Attributes:
        score: 评分（0-10 之间的浮点数）
        reasoning: 分析理由文本
    """

    score: float
    reasoning: str


class Dimension1Result(DimensionResult):
    """维度1分析结果（事实知识审查）.

    Attributes:
        score: 评分（0-10）
        reasoning: 分析理由
        key_indicators: 关键指标列表（可选）
        sentence_suggestion: 量刑建议（可选）
    """

    key_indicators: NotRequired[list[str]]
    sentence_suggestion: NotRequired[str]


class Dimension2Result(DimensionResult):
    """维度2分析结果（模式匹配分析）.

    Attributes:
        score: 评分（0-10）
        reasoning: 分析理由
        pattern_match: 模式匹配结果描述（可选）
    """

    pattern_match: NotRequired[str]


class Dimension3Result(DimensionResult):
    """维度3分析结果（矛盾分析）.

    Attributes:
        score: 评分（0-10）
        reasoning: 分析理由
        contradictions: 矛盾点列表（可选）
    """

    contradictions: NotRequired[list[str]]


class GroundTruthAnalysis(TypedDict):
    """三维度综合分析结果.

    Attributes:
        dimension1: 事实知识审查分析结果
        dimension2: 模式匹配分析结果
        dimension3: 矛盾分析结果
    """

    dimension1: Dimension1Result
    dimension2: Dimension2Result
    dimension3: Dimension3Result


class DimensionMeta(TypedDict):
    """单维度分析执行元数据.

    Attributes:
        status: 执行状态（"success" 或 "failed"）
        duration_ms: 执行耗时（毫秒）
        start_time: 开始时间（ISO 格式）
        end_time: 结束时间（ISO 格式）
        error: 错误信息（仅失败时存在）
        error_type: 异常类型名称（仅失败时存在）
        error_time: 异常发生时间（ISO 格式，仅失败时存在）
    """

    status: str
    duration_ms: float
    start_time: str
    end_time: str
    error: NotRequired[str]
    error_type: NotRequired[str]
    error_time: NotRequired[str]


class AnalysisResult(TypedDict):
    """主分析结果.

    案件分析管道的完整输出数据结构。

    Attributes:
        version: 协议版本（``"v1"`` 默认，``"v2"`` 见 :mod:`app.types.analysis_v2`）。
                  默认 v1 以保持向后兼容——读旧数据时该字段缺失，按 v1 处理。
        subjective_knowledge: 主观明知程度判定（可选）
        sentence: 量刑建议（可选）
        court: 建议法院（可选）
        ground_truth_analysis: 三维度综合分析（可选）
        fallback: 是否使用回退结果
        timestamp: 分析完成时间戳（ISO 格式）
        dimension_meta: 各维度执行元数据（可选，包含状态、耗时、异常详情）
        confidence: 整体置信度（0-1，Self-Consistency 模式，可选）
        confidence_details: 各维度一致性详情（Self-Consistency 模式，可选）
        num_samples: 实际采样次数（Self-Consistency 模式，可选）
        sample_scores: 所有采样的原始评分（Self-Consistency 模式，可选）
        knowledge_used: 是否使用了知识图谱增强（可选）
        knowledge_entries: 使用的知识条目摘要列表（可选）
    """

    version: NotRequired[Literal["v1", "v2"]]
    subjective_knowledge: NotRequired[str]
    sentence: NotRequired[str]
    court: NotRequired[str]
    ground_truth_analysis: NotRequired[GroundTruthAnalysis]
    fallback: bool
    timestamp: str
    dimension_meta: NotRequired[dict[str, DimensionMeta]]
    confidence: NotRequired[float]
    confidence_details: NotRequired[dict[str, Any]]
    num_samples: NotRequired[int]
    sample_scores: NotRequired[list[dict[str, Any]]]
    knowledge_used: NotRequired[bool]
    knowledge_entries: NotRequired[list[dict[str, str]]]


class SentencingSuggestion(TypedDict):
    """量刑建议结果.

    Attributes:
        suggested_sentence: 建议量刑
        reasoning: 量刑理由
        legal_basis: 法律依据列表（可选）
        aggravating_factors: 加重情节列表（可选）
        mitigating_factors: 从轻情节列表（可选）
        raw_response: LLM 原始响应文本（可选）
    """

    suggested_sentence: str
    reasoning: str
    legal_basis: NotRequired[list[str]]
    aggravating_factors: NotRequired[list[str]]
    mitigating_factors: NotRequired[list[str]]
    raw_response: NotRequired[str]


class SimilarCase(TypedDict):
    """相似案例信息.

    Attributes:
        case_id: 案例 ID
        similarity: 相似度（0-1 之间的浮点数）
        title: 案例标题
        summary: 案例摘要
    """

    case_id: str
    similarity: float
    title: str
    summary: str


class CacheSnapshot(TypedDict):
    """缓存统计快照.

    Attributes:
        hits: 命中次数
        misses: 未命中次数
        errors: 错误次数
        hit_rate: 命中率（0-1 之间的浮点数）
        avg_response_time_us: 平均响应时间（微秒）
    """

    hits: int
    misses: int
    errors: int
    hit_rate: float
    avg_response_time_us: float


class AnalysisReport(TypedDict):
    """分析报告记录.

    Attributes:
        id: 分析记录 ID
        case_id: 关联案件 ID（可选）
        knowledge_score: 知识评分（可选）
        mode: 分析模式
        result: 分析结果 JSON 字符串
        created_at: 创建时间的 ISO 格式字符串（可选）
    """

    id: int
    case_id: int | None
    knowledge_score: float | None
    mode: str
    result: str
    created_at: str | None


class ReportList(TypedDict):
    """分析报告列表.

    Attributes:
        total: 报告总数
        analyses: 分析报告列表
    """

    total: int
    analyses: list[AnalysisReport]


class ExperimentResult(TypedDict):
    """A/B 测试实验结果.

    Attributes:
        experiment_name: 实验名称标识
        status: 实验状态（如 "completed"）
        params: 实验参数字典
        metrics: 实验指标，包含 accuracy 和 response_time
    """

    experiment_name: str
    status: str
    params: dict[str, Any]
    metrics: dict[str, float]
