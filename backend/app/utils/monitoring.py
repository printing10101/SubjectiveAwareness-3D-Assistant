"""Prometheus 监控指标模块.

定义分析操作的监控指标，包括计数器（按模式和状态维度）和
持续时间直方图，用于生产环境的可观测性。

包含以下核心指标：
- ANALYSIS_COUNTER: 分析操作计数器（按模式和状态）
- ANALYSIS_DURATION: 分析持续时间直方图
- LLM_CALL_DURATION: LLM调用持续时间直方图（按prompt类型）
- CACHE_HIT_RATIO: 缓存命中率Gauge
- PIPELINE_FAILURE_COUNTER: 流水线失败计数器（按处理阶段）
"""

# 导入模块: from prometheus_client
from prometheus_client import Counter, Gauge, Histogram


# ---------------------------------------------------------------------------
# 基础分析指标
# ---------------------------------------------------------------------------

# 分析操作计数器 - 按分析模式和操作状态标记
ANALYSIS_COUNTER = Counter(
    "analysis_total",
    "Total number of analysis operations performed",
    ["mode", "status"],
)

# 分析持续时间直方图 - 记录每次分析的耗时（秒）
ANALYSIS_DURATION = Histogram(
    "analysis_duration_seconds",
    "Duration of analysis operations in seconds",
    # 初始化变量 buckets
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)


# ---------------------------------------------------------------------------
# LLM 调用监控指标
# ---------------------------------------------------------------------------

# LLM调用持续时间直方图 - 按prompt类型分桶统计
# prompt类型包括: fact_check, pattern_match, contradiction, sentencing, similarity
LLM_CALL_DURATION = Histogram(
    "llm_call_duration_seconds",
    "Duration of LLM API calls in seconds, bucketed by prompt type",
    # 初始化变量 labelnames
    labelnames=["prompt_type"],
    # 初始化变量 buckets
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60],
)

# LLM调用计数器 - 按prompt类型和状态统计
LLM_CALL_COUNTER = Counter(
    "llm_call_total",
    "Total number of LLM API calls",
    ["prompt_type", "status"],
)

# LLM调用失败计数器
LLM_CALL_FAILURE_COUNTER = Counter(
    "llm_call_failure_total",
    "Total number of failed LLM API calls",
    ["prompt_type", "error_type"],
)


# ---------------------------------------------------------------------------
# 缓存监控指标
# ---------------------------------------------------------------------------

# 缓存命中率 - Gauge类型，实时反映当前缓存命中率
# 值范围: 0.0 - 1.0，由缓存管理器定期更新
CACHE_HIT_RATIO = Gauge(
    "cache_hit_ratio",
    "Current cache hit ratio (0.0 to 1.0)",
)

# 缓存操作计数器 - 按操作类型（hit/miss/set/delete）统计
CACHE_OPERATION_COUNTER = Counter(
    "cache_operation_total",
    "Total number of cache operations",
    ["operation"],
)

# 缓存条目数 - 当前缓存中的条目数量
CACHE_ENTRIES_COUNT = Gauge(
    "cache_entries_count",
    "Current number of entries in cache",
)


# ---------------------------------------------------------------------------
# 流水线监控指标
# ---------------------------------------------------------------------------

# 流水线失败计数器 - 按处理阶段分桶统计
# 处理阶段包括: input_validation, knowledge_retrieval, llm_inference,
#               result_aggregation, output_formatting, database_persistence
PIPELINE_FAILURE_COUNTER = Counter(
    "pipeline_failure_total",
    "Total number of pipeline failures by processing stage",
    ["stage"],
)

# 流水线执行计数器 - 按状态（success/failure/timeout）统计
PIPELINE_EXECUTION_COUNTER = Counter(
    "pipeline_execution_total",
    "Total number of pipeline executions",
    ["status"],
)

# 流水线执行时间直方图 - 完整流水线执行时间
PIPELINE_DURATION = Histogram(
    "pipeline_duration_seconds",
    "Duration of complete pipeline execution in seconds",
    # 初始化变量 buckets
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
)


# ---------------------------------------------------------------------------
# 系统健康指标
# ---------------------------------------------------------------------------

# 活跃连接数 - 当前活跃的数据库连接数
ACTIVE_DB_CONNECTIONS = Gauge(
    "active_db_connections",
    "Current number of active database connections",
)

# HTTP请求计数器 - 按方法和状态码统计
HTTP_REQUEST_COUNTER = Counter(
    "http_request_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

# HTTP请求延迟直方图
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Duration of HTTP requests in seconds",
    ["method", "endpoint"],
    # 初始化变量 buckets
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10],
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def update_cache_hit_ratio(hits: int, misses: int) -> None:
    """更新缓存命中率指标.

    Args:
        hits: 缓存命中次数
        misses: 缓存未命中次数

    Example:
        >>> update_cache_hit_ratio(85, 15)  # 命中率 85%
    """
    # 初始化变量 total
    total = hits + misses
    # 条件判断：处理业务逻辑
    if total > 0:
        # 初始化变量 ratio
        ratio = hits / total
        CACHE_HIT_RATIO.set(ratio)


def record_llm_call(prompt_type: str, duration: float, success: bool) -> None:
    """记录LLM调用指标.

    Args:
        prompt_type: prompt类型（fact_check, pattern_match等）
        duration: 调用持续时间（秒）
        success: 是否成功
    """
    LLM_CALL_DURATION.labels(prompt_type=prompt_type).observe(duration)
    # 初始化变量 status
    status = "success" if success else "failure"
    LLM_CALL_COUNTER.labels(prompt_type=prompt_type, status=status).inc()


def record_pipeline_failure(stage: str) -> None:
    """记录流水线失败.

    Args:
        stage: 处理阶段名称
    """
    PIPELINE_FAILURE_COUNTER.labels(stage=stage).inc()


def record_pipeline_execution(status: str, duration: float) -> None:
    """记录流水线执行.

    Args:
        status: 执行状态（success/failure/timeout）
        duration: 执行时间（秒）
    """
    PIPELINE_EXECUTION_COUNTER.labels(status=status).inc()
    PIPELINE_DURATION.observe(duration)


def record_cache_operation(operation: str) -> None:
    """记录缓存操作.

    Args:
        operation: 操作类型（hit/miss/set/delete）
    """
    CACHE_OPERATION_COUNTER.labels(operation=operation).inc()
