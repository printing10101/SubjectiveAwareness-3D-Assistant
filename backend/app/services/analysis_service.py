"""分析服务模块.

提供案件分析的执行、查询和管理功能。
所有数据库操作均使用异步 API。
"""

import json
import math
import time
from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.case import Case
from app.services.pipeline import analyze_pipeline
from app.types.analysis import AnalysisResult, GroundTruthAnalysis
from app.types.analysis_v2 import is_v2_result


# 知识评分的维度键列表（V1 协议，0-10 分制）
_KNOWLEDGE_DIMENSION_KEYS: list[str] = ["dimension1", "dimension2", "dimension3"]

# 标准免责声明：附加到所有分析结果中，明确辅助参考工具的法律属性
ANALYSIS_DISCLAIMER: str = (
    "本分析结果为系统辅助生成，不构成法律意见，仅供参考。"
    "所有结论须经专业人员人工审查确认。"
)


# ---------------------------------------------------------------------------
# 置信度常量（0-1）
# ---------------------------------------------------------------------------

# V1 历史数据缩放因子：旧 knowledge_score 是 0-10 分，需要除以 10
_V1_SCORE_TO_CONFIDENCE: float = 0.1

# V2 置信度组成权重
_WEIGHT_SELF_CONSISTENCY: float = 0.50  # 维度间一致性
_WEIGHT_RULE_HIT: float = 0.30          # 规则命中率
_WEIGHT_CONFLICT_PENALTY: float = 0.20  # 冲突惩罚

# Self-Consistency 期望的最小采样数
_MIN_SAMPLES_FOR_CONSISTENCY: int = 1

# 冲突惩罚表（按冲突数）
_CONFLICT_PENALTY_TABLE: dict[int, float] = {
    0: 0.0,
    1: 0.05,
    2: 0.15,
    3: 0.30,
}
_CONFLICT_PENALTY_MAX: float = 0.30  # 超过 3 个冲突也按 0.30 扣

# 规则命中率饱和阈值：命中规则数 / 总规则数 >= 此值时按 1.0 算
_RULE_HIT_SATURATION: float = 0.20

# 兜底默认置信度
_DEFAULT_CONFIDENCE: float = 0.5


def _compute_knowledge_score(result: AnalysisResult) -> float | None:
    """V1 协议：从分析结果中计算 0-10 知识评分.

    对所有维度的评分取平均值，并通过 max(0.0, min(10.0, score)) 钳制到 [0, 10] 范围。
    NaN 值被过滤，若所有维度评分均为非有效数值则返回 None。

    **本函数仅用于 V1 协议与历史数据兼容**。V2 协议请改用
    :func:`_compute_confidence`。

    Args:
        result: V1 分析结果字典

    Returns:
        float | None: 钳制后的平均知识评分（0-10），无有效评分时返回 None
    """
    ground_truth: GroundTruthAnalysis | None = result.get("ground_truth_analysis")
    if ground_truth is None:
        return None
    scores: list[float] = []
    for dim_key in _KNOWLEDGE_DIMENSION_KEYS:
        if dim_key in ground_truth and "score" in ground_truth[dim_key]:  # type: ignore[literal-required]
            raw: float = ground_truth[dim_key]["score"]  # type: ignore[literal-required]
            if isinstance(raw, (int, float)) and not math.isnan(raw):
                clamped: float = max(0.0, min(10.0, raw))
                scores.append(clamped)
    if scores:
        avg: float = sum(scores) / len(scores)
        return max(0.0, min(10.0, avg))
    return None


def _compute_self_consistency(result: Mapping[str, Any]) -> float:
    """计算三维度档级一致性 (0-1).

    三个维度档级完全相同 → 1.0；仅一档差异 → 0.85；两档以上差异 → 0.6。
    缺少任一维度档级时降级为 0.5。
    """
    dims = (result.get("dimension1"), result.get("dimension2"), result.get("dimension3"))
    tiers: list[str] = []
    for d in dims:
        if isinstance(d, Mapping) and d.get("tier"):
            tiers.append(str(d["tier"]))
    if len(tiers) < 3:
        return 0.5
    unique = set(tiers)
    if len(unique) == 1:
        return 1.0
    if len(unique) == 2:
        return 0.85
    return 0.6


def _compute_rule_hit_rate(result: Mapping[str, Any]) -> float:
    """计算规则命中率 (0-1).

    规则命中数 / 规则池大小。规则池大小以 ``total_rules`` 字段为准，
    若未提供，则按 56（项目当前规则总数）回退。
    命中数 / 池大小 >= ``_RULE_HIT_SATURATION`` 时按 1.0 算，避免
    极少数规则命中就 0.1 显得太"绝望"。
    """
    triggered = result.get("triggered_rule_ids") or []
    if not isinstance(triggered, list) or not triggered:
        return 0.0
    total = result.get("total_rules")
    if not isinstance(total, int) or total <= 0:
        total = 56
    rate = min(1.0, len(triggered) / max(1, total))
    return min(1.0, rate / _RULE_HIT_SATURATION)


def _compute_conflict_penalty(result: Mapping[str, Any]) -> float:
    """计算冲突惩罚 (0-1，越大越扣分)."""
    conflicts = result.get("conflicts")
    if not isinstance(conflicts, list):
        return 0.0
    n = len(conflicts)
    if n == 0:
        return 0.0
    if n >= len(_CONFLICT_PENALTY_TABLE):
        return _CONFLICT_PENALTY_MAX
    return _CONFLICT_PENALTY_TABLE.get(n, _CONFLICT_PENALTY_MAX)


def _compute_confidence(result: Mapping[str, Any]) -> float:
    """计算综合置信度 (0-1).

    同时支持 V1 与 V2 协议：

    - **V2 协议**（推荐）：基于
        1) 三维度档级一致性（self-consistency），
        2) 规则命中率（rule hit rate），
        3) 冲突惩罚（conflict penalty），
       加权平均得到最终置信度。

    - **V1 协议**（历史数据）：将 V1 0-10 评分除以 10 直接缩放为 0-1 置信度，
       并在存在 self-consistency 字段时纳入修正。

    公式（V2）::

        confidence = (
            W_consistency * consistency
            + W_rule_hit * rule_hit
            - W_conflict_penalty * conflict_penalty
        )

    任何一项缺失时按 0 参与，但权重按"有效项的归一化权重"再分配，确保
    总和仍在 [0, 1]。

    Args:
        result: 分析结果字典（V1 或 V2）

    Returns:
        float: 置信度（0-1），无任何有效信号时返回 :data:`_DEFAULT_CONFIDENCE`。
    """
    if not isinstance(result, Mapping):
        return _DEFAULT_CONFIDENCE

    # ---------- V2 协议 ----------
    if is_v2_result(dict(result)):
        consistency = _compute_self_consistency(result)
        rule_hit = _compute_rule_hit_rate(result)
        conflict_pen = _compute_conflict_penalty(result)

        # 若三个信号全为 0，返回兜底
        if consistency == 0.0 and rule_hit == 0.0 and conflict_pen == 0.0:
            return _DEFAULT_CONFIDENCE

        # 归一化权重（剔除 0 值项）
        weights: list[tuple[float, float]] = []
        if consistency > 0.0:
            weights.append((_WEIGHT_SELF_CONSISTENCY, consistency))
        if rule_hit > 0.0:
            weights.append((_WEIGHT_RULE_HIT, rule_hit))
        if conflict_pen > 0.0:
            # 冲突是负向信号
            weights.append((_WEIGHT_CONFLICT_PENALTY, conflict_pen))

        if not weights:
            return _DEFAULT_CONFIDENCE

        total_weight = sum(w for w, _ in weights)
        # 惩罚项按"扣分"方式加入：positive_sum - penalty_sum
        positive = sum(w * v for w, v in weights[:2])
        penalty = (weights[-1][0] * weights[-1][1]) if len(weights) >= 3 else 0.0

        # 归一化到 [0, 1]
        norm = total_weight if total_weight > 0 else 1.0
        raw = (positive - penalty) / norm
        return float(max(0.0, min(1.0, raw)))

    # ---------- V1 协议（向后兼容） ----------
    v1_score = _compute_knowledge_score(dict(result))  # type: ignore[arg-type]
    if v1_score is None:
        return _DEFAULT_CONFIDENCE
    confidence = v1_score * _V1_SCORE_TO_CONFIDENCE
    return float(max(0.0, min(1.0, confidence)))


async def run_analysis(
    db: AsyncSession,
    case_id: int,
    mode: str = "auto",
    version: str = "v2",
) -> Analysis:
    """执行案件分析.

    事务管理策略:
        - 本函数不管理事务生命周期，不调用 db.commit() 或 db.rollback()
        - 使用 db.flush() 获取数据库生成的自增 ID，而不提交当前事务
        - 调用方（路由层或上下文管理器）统一负责事务的提交与回滚
        - 如果本函数内部抛出异常，调用方会在上下文管理器退出时自动回滚

    设计考量:
        - 避免事务双重提交：get_async_db_session() 上下文管理器退出时自动 commit，
          若本函数也调用 commit() 会导致重复提交
        - 单一职责：服务层专注于业务逻辑，事务管理属于基础设施层的职责

    Args:
        db: 异步数据库会话（由调用方注入，事务生命周期由调用方管理）
        case_id: 案件 ID
        mode: 分析模式（默认 "auto"）
        version: 协议版本 ``"v1"`` 或 ``"v2"``（默认 V2）

    Returns:
        Analysis: 分析结果记录（已 flush 但未 commit，调用方提交后可持久化）

    Raises:
        HTTPException 404: 案件不存在
    """
    case: Case | None = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    start_time: float = time.time()
    result_data: AnalysisResult = await analyze_pipeline(
        str(case.case_text), mode=mode, version=version
    )
    elapsed: int = int((time.time() - start_time) * 1000)

    logger.info(
        "分析完成: version={}, fallback={}, time={}ms",
        version,
        result_data.get("fallback", "no"),
        elapsed,
    )

    # 置信度：V2 走 _compute_confidence，V1 走 _compute_knowledge_score * 0.1
    # 字段 "knowledge_score" 实际语义从 0-10 评分改为 0-1 置信度
    confidence: float | None = _compute_confidence(dict(result_data))

    # 在结果中追加免责声明字段，确保所有分析输出都明确标注辅助参考属性
    result_data_with_disclaimer: dict = dict(result_data)
    result_data_with_disclaimer["disclaimer"] = ANALYSIS_DISCLAIMER

    db_analysis = Analysis(
        case_id=case_id,
        result_json=json.dumps(result_data_with_disclaimer, ensure_ascii=False),
        knowledge_score=confidence,  # type: ignore[arg-type]
        mode=mode,
    )
    db.add(db_analysis)
    # 仅刷新到数据库，获取自增ID，不提交事务
    await db.flush()
    await db.refresh(db_analysis)
    return db_analysis


async def get_analysis(db: AsyncSession, analysis_id: int) -> Analysis | None:
    """根据 ID 查询分析结果.

    Args:
        db: 异步数据库会话
        analysis_id: 分析结果 ID

    Returns:
        Analysis | None: 分析结果记录，不存在返回 None
    """
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    return result.scalar_one_or_none()


async def get_analyses_for_case(db: AsyncSession, case_id: int) -> list[Analysis]:
    """查询某案件的所有历史分析结果.

    Args:
        db: 异步数据库会话
        case_id: 案件 ID

    Returns:
        list[Analysis]: 分析结果列表
    """
    result = await db.execute(
        select(Analysis).where(Analysis.case_id == case_id)
    )
    return list(result.scalars().all())
