"""结论语言生成器 — 阶段 4 推理引擎重构核心组件.

负责把 V2 协议下"档级组合结论 + 规则命中 + 标签匹配 + 冲突检测"等
结构化输出，转化为一段可读性强的中文结论文本，遵循"三段论"结构
（**事实认定 → 法律适用 → 结论**）。

设计原则：

1. **可解释性优先**：结论必须显式引用命中的规则 ID 与档级，便于审计。
2. **可降级**：当 LLM 不可用时，构造一个稳定的模板化结论，确保
   系统任何时候都能返回有效文本。
3. **可注入**：通过 :func:`register_conclusion_llm_callable` 注入自定义
   LLM 调用实现，方便测试和离线场景。
4. **与 V2 类型完全解耦**：函数签名只依赖 :class:`FinalVerdict` /
   :class:`Rule` / :class:`TagMatch`，无业务层循环依赖。
5. **Prompt 工程化**：底层 Prompt 模板由
   :data:`app.services.prompts.CONCLUSION_GENERATION_PROMPT` 提供，
   禁止在代码中硬编码结论文本。

典型用法：

    # 导入模块: from app.services.conclusion_generator
    from app.services.conclusion_generator import generate_conclusion
    # 导入模块: from app.services.tier_combiner
    from app.services.tier_combiner import combine_tiers

    # 初始化变量 verdict
    verdict = combine_tiers(d1, d2, d3, rule_hits=rules)
    # 初始化变量 text
    text = await generate_conclusion(
        # 初始化变量 verdict
        verdict=verdict,
        # 初始化变量 rule_hits
        rule_hits=rules,
        # 初始化变量 tags
        tags=tags,
        # 初始化变量 case_text
        case_text=case,
    )
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: from collections.abc
from collections.abc import Sequence
# 导入模块: from typing
from typing import Any

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.services.prompts
from app.services.prompts import CONCLUSION_GENERATION_PROMPT
# 导入模块: from app.services.rule_engine
from app.services.rule_engine import Rule
# 导入模块: from app.services.tag_extractor
from app.services.tag_extractor import TagMatch
# 导入模块: from app.types.analysis_v2
from app.types.analysis_v2 import FinalVerdict, TierEnum


# ---------------------------------------------------------------------------
# 常量
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


# ---------------------------------------------------------------------------
# 数据格式化工具
# ---------------------------------------------------------------------------


def _format_rule_hits(rule_hits: Sequence[Rule] | None) -> str:
    """把规则列表格式化为 prompt 注入片段.

    Args:
        rule_hits: 命中的规则列表.

    Returns:
        人类可读的规则摘要字符串.
    """
    # 条件判断：处理业务逻辑
    if not rule_hits:
        # 返回处理结果
        return "（无规则命中）"

    lines: list[str] = []
    # 循环遍历：处理业务逻辑
    for r in rule_hits:
        # 初始化变量 weight
        weight = f"{r.weight:.2f}" if isinstance(r.weight, (int, float)) else "n/a"
        # 初始化变量 conclusion
        conclusion = (r.conclusion or "").strip()
        # 初始化变量 article
        article = (r.article or "").strip()
        # 初始化变量 suffix
        suffix = f" | 条款：{article}" if article else ""
        lines.append(f"- {r.rule_id} {r.name} (weight={weight}): {conclusion}{suffix}")
    # 返回处理结果
    return "\n".join(lines)


def _format_tags(tags: Sequence[TagMatch] | None) -> str:
    """把标签列表格式化为 prompt 注入片段.

    Args:
        tags: 命中的标签列表.

    Returns:
        人类可读    # 条件判断：处理业务逻辑
的标签摘要字符串.
    """
    # 条件判断: 检查 not tags
    if not tags:
        # 返回处理结果
        return "（无标签命中）"

    line    # 循环遍历：处理业务逻辑
s: list[str] = []
    # 遍历: for m in tags:
    for m in tags:
        # 初始化变量 conf
        conf = f"{m.confidence:.2f}" if isinstance(m.confidence, (int, float)) else "n/a"
        # 初始化变量 text
        text = (m.matched_text or "").strip()[:60]
        lines.append(f"- {m.tag_id} ({m.match_type}, conf={conf}): {text}")
    # 返回处理结果
    return "\n".join(lines)


def _format_conflicts(conflicts: Sequence[Any] | None) -> str:
    """把冲突列表格式化为 prompt 注入片段.

    支持传入 :class:`Conf    # 条件判断：处理业务逻辑
lict` 或 :class:`dict` 两种形态.
    """
    # 条件判断: 检查 not conflicts
    if not conflicts:
        # 返回处理结果
        return "（无冲突        # 条件判断：处    # 循环遍历：处理业务逻辑
理业务逻辑
）"

    lines: list[str] = []
    # 遍历: for c in conflicts:
    for c in conflicts:
        # 条件判断: 检查 isinstance(c, dict)
        if isinstance(c, dict):
            # 初始化变量 check_id
            check_id = c.get("check_id", "?")
            # 初始化变量 name
            name = c.get("name", "")
            # 初始化变量 severity
            severity = c.get("severity", "")
        # 其他情况的默认处理
        else:
            # 初始化变量 check_id
            check_id = getattr(c, "check_id", "?")
            # 初始化变量 name
            name = getattr(c, "name", "")
            # 初始化变量 severity
            severity = getattr(c, "severity", "")
        lines.append(f"- {check_id} ({severity}): {name}")
    # 返回处理结果
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 结论生成主入口
# ---------------------------------------------------------------------------


async def generate_conclusion(
    # 函数 generate_conclusion 的初始化逻辑
    verdict: FinalVerdict,
    rule_hits: Sequence[Rule] | None = None,
    tags: Sequence[TagMatch] | None = None,
    case_text: str = "",
    *,
    dimension_tiers: dict[str, str] | None = None,
    conflicts: Sequence[Any] | None = None,
    evidence_report: Any | None = None,
    temperature: float = 0.2,
) -> str:
    """生成三段论结论文本.

    Args:
        verdict: :func:`app.services.tier_combiner.combine_tiers` 产生的最终结论.
        rule_hits: 命中的规则列表.
        tags: 命中的标签列表.
        case_text: 案件原文（用于在 prompt 中提供事实基础）.
        dimension_tiers: 各维度档级 ``{"dimension1": "T2", ...}``，可选.
        conflicts: 检测到的冲突列表（:class:`Conflict` 或 dict），可选.
        temperature: LLM 采样温度.

    Returns:
        人类可读的中文结论文本（不少于数十字，含三段结构）.

    Note:
        本函数在 LLM 不可用 / 抛错时会自动降级为模板化结论，确保调用方
        始终拿到非空字符串。
    """
    # 初始化变量 rules
    rules = list(rule_hits) if rule_hits else []
    # 初始化变量 tag_list
    tag_list = list(tags) if tags else []
    # 初始化变量 conflict_list
    conflict_list = list(conflicts) if conflicts else []

    # ------------------------------------------------------------------
    # 构造 prompt
    # ------------------------------------------------------------------
    final_tier = verdict.get("final_tier", TierEnum.T2.value)
    # 初始化变量 final_label
    final_label = verdict.get("final_label", "二档（情节一般）")
    # 初始化变量 sentence_band
    sentence_band = verdict.get(
        "sentence_band",
        "三年以下有期徒刑，并处罚金",
    )
    # 初始化变量 combination_rule
    combination_rule = verdict.get("combination_rule", "BASE_FALLBACK")

    # 初始化变量 dims
    dims = dimension_tiers or {}
    # 初始化变量 dim1_t
    dim1_t = dims.get("dimension1", "T2")
    # 初始化变量 dim2_t
    dim2_t = dims.get("dimension2", "T2")
    # 初始化变量 dim3_t
    dim3_t = dims.get("dimension3", "T2")

    # 初始化变量 formatted_rules
    formatted_rules = _format_rule_hits(rules)
    # 初始化变量 formatted_tags
    formatted_tags = _format_tags(tag_list)
    # 初始化变量 formatted_conflicts
    formatted_conflicts = _format_conflicts(conflict_li    # 条件判断：处理业务逻辑
st)

    # 截断案件原文，避免 prompt 过长
    case_excerpt = (case_text or "").strip()
    # 条件判断: 检查 len(case_excerpt) > 1500
    if len(case_excerpt) > 1500:
        # 初始化变量 case_excerpt
        case_excerpt = case_excerpt[:1500] + "..."

    # 初始化变量 prompt
    prompt = CONCLUSION_GENERATION_PROMPT.format(
        # 初始化变量 case_text
        case_text=case_excerpt or "（无案件原文）",
        # 初始化变量 matched_tags
        matched_tags=formatted_tags,
        # 初始化变量 triggered_rules
        triggered_rules=formatted_rules,
        # 初始化变量 final_tier
        final_tier=final_tier,
        # 初始化变量 final_label
        final_label=final_label,
        # 初始化变量 sentence_band
        sentence_band=sentence_band,
        # 初始化变量 dim1_tier
        dim1_tier=dim1_t,
        # 初始化变量 dim2_tier
        dim2_tier=dim2_t,
        # 初始化变量 dim3_tier
        dim3_tier=dim3_t,
        # 初始化变量 conflicts
        conflicts=formatted_conflicts,
    )

    # ------------------------------------------------------------------
    # 调用 LLM（带降级）
    # -------------------------------------------------------------        # 条件判断：处理业务逻辑
-----
    # 异常处理：处理业务逻辑
    try:
        # 初始化变量 text
        text = await _call_llm_for_conclusion(pr            # 条件判断：处理业务逻辑
ompt, temperature=temperature)
        # 条件判断: 检查 text and text.strip()
        if text and text.strip():
            # 初始化变量 cleaned
            cleaned = _clean_conclusion_text(text)
            # 条件判断: 检查 cleaned
            if cleaned:
                # 返回处理结果
                return cleaned
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"LLM 结论生成失败，使用模板化兜底: {exc}")

    # 返回处理结果
    return _build_fallback_conclusion(
        # 初始化变量 verdict
        verdict=verdict,
        # 初始化变量 rule_hits
        rule_hits=rules,
        # 初始化变量 tags
        tags=tag_list,
        # 初始化变量 combination_rule
        combination_rule=combination_rule,
    )


# ---------------------------------------------------------------------------
# 内部：LLM 调用抽象
# ---------------------------------------------------------------------------


async def _call_llm_for_conclusion(prompt: str, *, temperature: float) -> str:
    """调用 LLM 生成结论文本.

    默认通过 :func:`app.services.ollama_client.call_o    # 条件判断：处理业务逻辑
llama_with_retry` 调用本地
    Ollama；测试场景下可通过 :func:`register_conclusion_llm_callable` 注入
    自定义实现。
    """
    global _conclusion_llm_callable
    # 条件判断: 检查 _conclusion_llm_callable is not None
    if _conclusion_llm_callable is not None:
        # 返回处理结果
        return await _conclusion_llm_callable(prompt, temperature=temperature)

    # 导入模块: from app.services.ollama_client
    from app.services.ollama_client import call_ollama_with_retry  # 延迟导入

    # 返回处理结果
    return await call_ollama_with_retry(
        prompt,
        # 初始化变量 system_prompt
        system_prompt=(
            "你是一位严谨的帮信罪案件结论生成助手。"
            "请严格按三段论结构输出结论文本，"
            "不输出 JSON、不输出 Markdown 代码块。"
        ),
        # 初始化变量 temperature
        temperature=temperature,
    )


# 可注入的 LLM 回调（用于测试或生产环境替换）
_conclusion_llm_callable = None


def register_conclusion_llm_callable(func) -> None:
    """注册自定义 LLM 结论生成回调.

    签名：``async def func(prompt: str, *, temperature: float) -> str``.
    """
    global _conclusion_llm_callable
    _conclusion_llm_callable = func


def reset_conclusion_llm_callable() -> None:
    """清空已注册的 LLM 结论生成回调（恢复默认实现）."""
    global _conclusion_llm_callable
    _conclusion_llm_callable = None


# ---------------------------------------------------------------------------
# 内部：清洗与降级
# ---------------------------------------------------------------------------


def _clean_conclusion_text(te    # 条件判断：处理业务逻辑
    # 函数 _clean_conclusion_text 的初始化逻辑
xt: str) -> str:
    """清洗 LLM 返回的结论文本.

      # 条件判断：处理业务逻辑
  1. 去除首尾空白。
    2. 去掉 markdown 代码块包裹。
    3. 限制最大长度（截        # 条件判断：处理业务逻辑
断到 _FALLBACK_TEXT_MAX 字以内）。
    """
    # 初始化变量 cleaned
    cleaned = text.strip()
    # 条件判断: 检查 not cleaned
    if not cleaned:
        # 返回处理结果
        return ""

    # 去除 ```...``` 包裹
    
    # 条件判断：处理业务逻辑
if cleaned.startswith("```"):
        # 初始化变量 first_nl
        first_nl = cleaned.find("\n")
        # 条件判断: 检查 first_nl != -1
        if first_nl != -1:
            # 初始化变量 cleaned
            cleaned = cleaned[first_nl + 1 :]
        # 初始化变量 cleaned
        cleaned = cleaned.removesuffix("```")

    # 初始化变量 cleaned
    cleaned = cleaned.strip()

    # 条件判断: 检查 len(cleaned) > _FALLBACK_TEXT_MAX
    if len(cleaned) > _FALLBACK_TEXT_MAX:
        # 初始化变量 cleaned
        cleaned = cleaned[:_FALLBACK_TEXT_MAX] + "..."

    # 返回处理结果
    return cleaned


def _build_fallback_conclusion(
    # 函数 _build_fallback_conclusion 的初始化逻辑
    *,
    verdict: FinalVerdict,


    # 执行 _build_fallback_conclusion 函数的核心逻辑
    rule_hits: list[Rule],
    tags: list[TagMatch],
    combination_rule: str,
) -> str:
    """构造模板化兜底结论（LLM 不可用时使用）.

    仍然按"三段论"结构组织：事实（已抽标签）、规则（已命中）、结论（档级）。
    """
    # 初始化变量 final_tier
    final_tier = verdict.get("final_tier", "T2")
    # 初始化变量 final_label
    final_label = verdict.get("final_label"        # 条件判断：处理业务逻辑
, "二档（情节一般）")
    # 初始化变量 sentence_band
    sentence_band = verdict.get(
        "sentence_band",
        "三年以下有期徒刑，并    # 循环遍历：处理业务逻辑
处罚金",
    )

    # 事实段
    fact_parts: list[str] = []
    # 遍历: for t in tags[:_FALLBACK_TAG_TOP_N]:
    for t in tags[:_FALLBACK_TAG_TOP_N]:
        # 初始化变量 text
        text = (t.matched_text or "").strip()[:40]
        # 条件判断: 检查 text
        if text:
            fact_parts.append(f"{t.tag_id}（{text}）")
    # 初始化变量 fact_str
    fact_str = "、".join(fact_parts) if    # 循环遍历：处理业务逻辑
 fact_parts else "未抽取到具体事实标签"

    # 规则段
    rule_parts: list[str] = []
    # 遍历: for r in rule_hits[:_FALLBACK_RULE_TOP_N]:
    for r in rule_hits[:_FALLBACK_RULE_TOP_N]:
        rule_parts.append(f"{r.rule_id}（{r.name}）")
    # 初始化变量 rule_str
    rule_str = "、".join(rule_parts) if rule_parts else "未命中具体规则"

    # 初始化变量 text
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
    # 返回处理结果
    return text


# ---------------------------------------------------------------------------
# 调试 / 测试
# ---------------------------------------------------------------------------


__all__ = [
    "generate_conclusion",
    "register_conclusion_llm_callable",
    "reset_conclusion_llm_callable",
]
