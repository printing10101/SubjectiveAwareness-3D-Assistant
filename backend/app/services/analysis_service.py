"""分析服务模块.

提供案件分析的执行、查询、管理和结论生成功能。
所有数据库操作均使用异步 API。
"""

import json
import math
import time
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.case import Case
from app.services.prompt import CONCLUSION_GENERATION_PROMPT
from app.services.rule_engine import Rule
from app.services.tag_extractor import TagMatch
from app.types.analysis import AnalysisResult, GroundTruthAnalysis
from app.types.analysis_v2 import FinalVerdict, TierEnum, is_v2_result


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
    # 延迟导入以避免循环依赖
    from app.services.pipeline import analyze_pipeline

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


# ---------------------------------------------------------------------------
# 结论语言生成器（整合自 conclusion_generator.py）
# ---------------------------------------------------------------------------

# LLM 调用失败或返回非文本时的兜底结论最长截取字符数
_FALLBACK_TEXT_MAX: int = 600

# 兜底结论中默认列举的规则数量上限
_FALLBACK_RULE_TOP_N: int = 5

# 兜底结论中默认列举的标签数量上限
_FALLBACK_TAG_TOP_N: int = 5

# 模板化兜底结论使用的标题
_FALLBACK_TITLE: str = "辅助参考结论（降级）"

# 模板化结论的免责声明
_FALLBACK_DISCLAIMER: str = (
    "本结论由系统根据已命中的规则与标签按既定模板生成，仅供办案人员参考。"
    "完整结论需要由 LLM 在三段论结构下生成；当前可能未达到最高解释性。"
)


def _format_rule_hits(rule_hits: Sequence[Rule] | None) -> str:
    """把规则列表格式化为 prompt 注入片段."""
    if not rule_hits:
        return "（无规则命中）"

    lines: list[str] = []
    for r in rule_hits:
        weight = f"{r.weight:.2f}" if isinstance(r.weight, (int, float)) else "n/a"
        conclusion = (r.conclusion or "").strip()
        article = (r.article or "").strip()
        suffix = f" | 条款：{article}" if article else ""
        lines.append(f"- {r.rule_id} {r.name} (weight={weight}): {conclusion}{suffix}")
    return "\n".join(lines)


def _format_tags(tags: Sequence[TagMatch] | None) -> str:
    """把标签列表格式化为 prompt 注入片段."""
    if not tags:
        return "（无标签命中）"

    lines: list[str] = []
    for m in tags:
        conf = f"{m.confidence:.2f}" if isinstance(m.confidence, (int, float)) else "n/a"
        text = (m.matched_text or "").strip()[:60]
        lines.append(f"- {m.tag_id} ({m.match_type}, conf={conf}): {text}")
    return "\n".join(lines)


def _format_conflicts(conflicts: Sequence[Any] | None) -> str:
    """把冲突列表格式化为 prompt 注入片段."""
    if not conflicts:
        return "（无冲突）"

    lines: list[str] = []
    for c in conflicts:
        if isinstance(c, dict):
            check_id = c.get("check_id", "?")
            name = c.get("name", "")
            severity = c.get("severity", "")
        else:
            check_id = getattr(c, "check_id", "?")
            name = getattr(c, "name", "")
            severity = getattr(c, "severity", "")
        lines.append(f"- {check_id} ({severity}): {name}")
    return "\n".join(lines)


async def generate_conclusion(
    verdict: FinalVerdict,
    rule_hits: Sequence[Rule] | None = None,
    tags: Sequence[TagMatch] | None = None,
    case_text: str = "",
    *,
    dimension_tiers: dict[str, str] | None = None,
    conflicts: Sequence[Any] | None = None,
    temperature: float = 0.2,
) -> str:
    """生成三段论结论文本."""
    rules = list(rule_hits) if rule_hits else []
    tag_list = list(tags) if tags else []
    conflict_list = list(conflicts) if conflicts else []

    final_tier = verdict.get("final_tier", TierEnum.T2.value)
    final_label = verdict.get("final_label", "二档（情节一般）")
    sentence_band = verdict.get(
        "sentence_band",
        "三年以下有期徒刑，并处罚金",
    )
    combination_rule = verdict.get("combination_rule", "BASE_FALLBACK")

    dims = dimension_tiers or {}
    dim1_t = dims.get("dimension1", "T2")
    dim2_t = dims.get("dimension2", "T2")
    dim3_t = dims.get("dimension3", "T2")

    formatted_rules = _format_rule_hits(rules)
    formatted_tags = _format_tags(tag_list)
    formatted_conflicts = _format_conflicts(conflict_list)

    case_excerpt = (case_text or "").strip()
    if len(case_excerpt) > 1500:
        case_excerpt = case_excerpt[:1500] + "..."

    prompt = CONCLUSION_GENERATION_PROMPT.format(
        case_text=case_excerpt or "（无案件原文）",
        matched_tags=formatted_tags,
        triggered_rules=formatted_rules,
        final_tier=final_tier,
        final_label=final_label,
        sentence_band=sentence_band,
        dim1_tier=dim1_t,
        dim2_tier=dim2_t,
        dim3_tier=dim3_t,
        conflicts=formatted_conflicts,
    )

    try:
        text = await _call_llm_for_conclusion(prompt, temperature=temperature)
        if text and text.strip():
            cleaned = _clean_conclusion_text(text)
            if cleaned:
                return cleaned
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"LLM 结论生成失败，使用模板化兜底: {exc}")

    return _build_fallback_conclusion(
        verdict=verdict,
        rule_hits=rules,
        tags=tag_list,
        combination_rule=combination_rule,
    )


async def _call_llm_for_conclusion(prompt: str, *, temperature: float) -> str:
    """调用 LLM 生成结论文本."""
    global _conclusion_llm_callable
    if _conclusion_llm_callable is not None:
        return await _conclusion_llm_callable(prompt, temperature=temperature)

    from app.services.ollama_client import call_ollama_with_retry

    return await call_ollama_with_retry(
        prompt,
        system_prompt=(
            "你是一位严谨的帮信罪案件结论生成助手。"
            "请严格按三段论结构输出结论文本，"
            "不输出 JSON、不输出 Markdown 代码块。"
        ),
        temperature=temperature,
    )


_conclusion_llm_callable = None


def register_conclusion_llm_callable(func) -> None:
    """注册自定义 LLM 结论生成回调."""
    global _conclusion_llm_callable
    _conclusion_llm_callable = func


def reset_conclusion_llm_callable() -> None:
    """清空已注册的 LLM 结论生成回调."""
    global _conclusion_llm_callable
    _conclusion_llm_callable = None


def _clean_conclusion_text(text: str) -> str:
    """清洗 LLM 返回的结论文本."""
    cleaned = text.strip()
    if not cleaned:
        return ""

    if cleaned.startswith("```"):
        first_nl = cleaned.find("\n")
        if first_nl != -1:
            cleaned = cleaned[first_nl + 1 :]
        cleaned = cleaned.removesuffix("```")

    cleaned = cleaned.strip()

    if len(cleaned) > _FALLBACK_TEXT_MAX:
        cleaned = cleaned[:_FALLBACK_TEXT_MAX] + "..."

    return cleaned


def _build_fallback_conclusion(
    *,
    verdict: FinalVerdict,
    rule_hits: list[Rule],
    tags: list[TagMatch],
    combination_rule: str,
) -> str:
    """构造模板化兜底结论."""
    final_tier = verdict.get("final_tier", "T2")
    final_label = verdict.get("final_label", "二档（情节一般）")
    sentence_band = verdict.get(
        "sentence_band",
        "三年以下有期徒刑，并处罚金",
    )

    fact_parts: list[str] = []
    for t in tags[:_FALLBACK_TAG_TOP_N]:
        text = (t.matched_text or "").strip()[:40]
        if text:
            fact_parts.append(f"{t.tag_id}（{text}）")
    fact_str = "、".join(fact_parts) if fact_parts else "未抽取到具体事实标签"

    rule_parts: list[str] = []
    for r in rule_hits[:_FALLBACK_RULE_TOP_N]:
        rule_parts.append(f"{r.rule_id}（{r.name}）")
    rule_str = "、".join(rule_parts) if rule_parts else "未命中具体规则"

    text = (
        f"【{_FALLBACK_TITLE}】\n\n"
        f"**一、事实认定**\n"
        f"系统已抽取的事实标签：{fact_str}。\n\n"
        f"**二、法律适用**\n"
        f"触发的规则：{rule_str}。\n"
        f"档级组合规则：{combination_rule}。\n\n"
        f"**三、结论**\n"
        f"经三维度档级组合，案件综合判定为【{final_tier} {final_label}】，"
        f"建议量刑区间为：{sentence_band}。\n\n"
        f"⚠️ {_FALLBACK_DISCLAIMER}"
    )
    return text

