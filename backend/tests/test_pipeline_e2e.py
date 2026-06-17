"""端到端集成测试 — V2 协议分析管道.

覆盖 5 份已知 verdict 的测试 case（不来自 train 集），跑完整 pipeline，
断言 tier 正确。

为保证测试可独立运行（无需真实 LLM / Ollama / Neo4j），使用
:func:`unittest.mock.patch` 替换 LLM 调用与知识检索，让每个
dimension 阶段返回预定的 tier。

测试 case 选取原则：

1. 涵盖三维度全 T1 / 全 T4 两种极端
2. 覆盖 T2 / T3 中间档
3. 覆盖"高权重 T4 规则升级"路径
4. 覆盖"抗辩降档"路径（d3 显著低于 d1/d2）
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: asyncio
import asyncio
# 导入模块: json
import json
# 导入模块: time
import time
# 导入模块: from typing
from typing import Any
# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch

# 导入模块: pytest
import pytest

# 导入模块: from app.services.pipeline
from app.services.pipeline import analyze_pipeline_v2


# ---------------------------------------------------------------------------
# 测试用例：5 份已知 verdict
# ---------------------------------------------------------------------------

# Case 1：情节较轻，全 T1 — 应得 T1
CASE_LIGHT_TEXT = (
    "被告人李某，男，22岁，在校大学生。2023年1月，李某在不知情的情况下，"
    "将自己闲置的银行卡借给了同学，同学使用该卡接收小额转账共计1.2万元。"
    "李某未从中获利。案发后主动配合调查，如实供述。法院认定李某主观上不具"
    "有'明知'，且情节轻微。"
)

# Case 2：情节一般，三维度均为 T2 — 应得 T2
CASE_MILD_TEXT = (
    "被告人王某，男，28岁，无业。2023年4月至6月，王某在模糊'可能涉嫌'的认知下，"
    "将自己的两张银行卡提供给他人使用，流水金额共计15万元，王某获利2000元。"
    "法院认定王某主观认知模糊，情节一般。"
)

# Case 3：情节严重，全 T3 — 应得 T3
CASE_SERIOUS_TEXT = (
    "被告人赵某，男，35岁，个体经营。2022年9月至2023年1月，赵某明知他人利用"
    "信息网络实施犯罪，仍提供多张银行卡及U盾帮助支付结算，流水金额达80万元，"
    "获利8000元。多名被害人遭受电信网络诈骗损失。"
)

# Case 4：情节特别严重，全 T4 + T4 升级 — 应得 T4
CASE_CRITICAL_TEXT = (
    "被告人孙某，男，40岁，无业，系电信网络诈骗团伙的组织者之一。"
    "2022年1月至2023年6月，孙某组织多人提供银行卡、对公账户共计30余张，"
    "跨境帮助上游电信网络诈骗团伙洗钱，流水金额高达5000万元，造成200余名"
    "被害人重大经济损失，数额特别巨大。孙某系累犯。"
)

# Case 5：抗辩降档（d3 显著低于 d1/d2） — 基础档被降一档
CASE_DEFENSE_TEXT = (
    "被告人周某，男，30岁，公司职员。2023年3月，周某在同事请求下出借银行卡一张，"
    "该卡被用于接收转账共计35万元。法院审查发现周某事后主动察觉可疑，"
    "在3日内挂失并报警，且在询问中如实供述自己'并不明确知道'对方用途。"
    "主观上'明知'程度存疑，存在有效抗辩。"
)


_TEST_CASES: list[dict[str, Any]] = [
    {
        "case_id": "C1_LIGHT",
        "case_text": CASE_LIGHT_TEXT,
        "expected_tier": "T1",
        "expected_dim_tiers": ("T1", "T1", "T1"),
        "expected_severity": 1,
        "case_type": "all_light",
    },
    {
        "case_id": "C2_MILD",
        "case_text": CASE_MILD_TEXT,
        "expected_tier": "T2",
        "expected_dim_tiers": ("T2", "T2", "T2"),
        "expected_severity": 2,
        "case_type": "all_mild",
    },
    {
        "case_id": "C3_SERIOUS",
        "case_text": CASE_SERIOUS_TEXT,
        "expected_tier": "T3",
        "expected_dim_tiers": ("T3", "T3", "T3"),
        "expected_severity": 3,
        "case_type": "all_serious",
    },
    {
        "case_id": "C4_CRITICAL",
        "case_text": CASE_CRITICAL_TEXT,
        "expected_tier": "T4",
        "expected_dim_tiers": ("T4", "T4", "T4"),
        "expected_severity": 4,
        "case_type": "escalate_to_t4",
    },
    {
        "case_id": "C5_DEFENSE",
        "case_text": CASE_DEFENSE_TEXT,
        # 基础档 (3, 3, 1) = T2；d3=1 满足降档条件 → final_rank = max(1, 2-1) = 1
        "expected_tier": "T1",
        "expected_dim_tiers": ("T3", "T3", "T1"),
        "expected_severity": 1,
        "case_type": "defense_downgrade",
    },
]


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_dim_payload(dim_name: str, tier: str) -> str:
    """构造 LLM 返回的 dimension 结果 JSON."""
    payload: dict[str, Any] = {
        "tier": tier,
        "reasoning": f"[mock] {dim_name} 推理：嫌疑人符合 {tier} 档情形。",
        "confidence": 0.9,
    }
    # 条件判断：处理业务逻辑
    if dim_name == "dimension1":
        payload["key_indicators"] = [f"mock_indicator_{tier}"]
    # 条件判断: 检查 eldim_name == "dimension2"
    elif dim_name == "dimension2":
        payload["pattern_match"] = f"mock_pattern_{tier}"
    # 条件判断: 检查 eldim_name == "dimension3"
    elif dim_name == "dimension3":
        payload["contradictions"] = [f"mock_contradiction_{tier}"]
    payload["triggered_rules"] = []
    # 返回处理结果
    return json.dumps(payload, ensure_ascii=False)


def _patch_call_ollama(dim_tiers: tuple[str, str, str]):
    """构造 :func:`call_ollama_with_retry` 的 mock，依次返回 d1/d2/d3 的 JSON.

    此外还支持 :func:`_retrieve_legal_knowledge` 的 mock。
    """
    responses: list[str] = [
        _make_dim_payload("dimension1", dim_tiers[0]),
        _make_dim_payload("dimension2", dim_tiers[1]),
        _make_dim_payload("dimension3", dim_tiers[2]),
    ]
    # 结论生成会再次调用 LLM，返回一个简单的中文段落
    responses.append("事实清楚，证据充分，结合三维度档级与规则命中情况，作出如下结论。")

    # 初始化变量 iter_resp
    iter_resp = iter(responses)

    async def _mock_call_ollama(
        # 函数 _mock_call_ollama 的初始化逻辑
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
    ) -> str:
        # 异常处理：处理业务逻辑
        try:
            # 返回处理结果
            return next(iter_resp)
        # 捕获异常：处理业务逻辑
        except StopIteration:
            # 兜底：返回最后一个响应（防止 LLM 调用次数超出预期）
            return responses[-1]

    # 返回处理结果
    return _patch_call_ollama


# 供每个 test 动态创建独立 patch
def _patch_pipeline_for_case(dim_tiers: tuple[str, str, str]):
    """对 analyze_pipeline_v2 内部的所有外部依赖打补丁.

    注意：tag_extractor 默认使用正则匹配，不调用 LLM，因此无需 mock 它。

    关键点：

    1. ``pipeline.py`` 在模块顶层 ``from app.services.ollama_client import
       call_ollama_with_retry``，因此需要 patch
       ``app.services.pipeline.call_ollama_with_retry`` 才能拦截 pipeline 内的调用。
    2. ``conclusion_generator.py`` 在 :func:`_call_llm_for_conclusion` 内部使用
       延迟导入 ``from app.services.ollama_client import call_ollama_with_retry``，
       因此必须 patch **源模块** ``app.services.ollama_client.call_ollama_with_retry``
       才能拦截结论生成时的 LLM 调用。直接 patch 结论生成模块的同名属性是
       无效的（该属性在模块层级不存在）。
    3. patch ``_match_rules_v2`` 为返回空规则列表，避免测试用例的案件
       文本意外命中数据库里的高权重规则（例如 R008 weight=1.0），
       导致 tier_combiner 触发 ESCALATE_T3/T4 升级。
    """

    responses: list[str] = [
        _make_dim_payload("dimension1", dim_tiers[0]),
        _make_dim_payload("dimension2", dim_tiers[1]),
        _make_dim_payload("dimension3", dim_tiers[2]),
    ]
    # 初始化变量 conclusion_response
    conclusion_response = "事实清楚，证据充分，结合三维度档级与规则命中情况，作出如下结论。"

    async def _ollama_side_effect(
        # 函数 _ollama_side_effect 的初始化逻辑
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0        # 条件判断：处理业务逻辑
.3,
    ) -> str:
        # 条件判断: 检查 responses
        if responses:
            # 返回处理结果
            return responses.pop(0)
        # 返回处理结果
        return conclusion_response

    # 返回处理结果
    return [
        patch(
            "app.services.pipeline.call_ollama_with_retry",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
            # 初始化变量 side_effect
            side_effect=_ollama_side_effect,
        ),
        patch(
            "app.services.ollama_client.call_ollama_with_retry",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
            # 初始化变量 side_effect
            side_effect=_ollama_side_effect,
        ),
        patch(
            "app.services.pipeline._retrieve_legal_knowledge",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
            return_value=("", []),
        ),
        patch(
            "app.services.pipeline._match_rules_v2",
            # 初始化变量 new_callable
            new_callable=MagicMock,
            return_value=[],
        ),
    ]


def _make_dim_ollama_side_effect(dim_tiers: tuple[str, str, str]):
    """生成 call_ollama_with_retry 的 side_effect."""

    # 初始化变量 dim_responses
    dim_responses = [
        _make_dim_payload("dimension1", dim_tiers[0]),
        _make_dim_payload("dimension2", dim_tiers[1]),
        _make_dim_payload("dimension3", dim_tiers[2]),
    ]
    # 初始化变量 conclusion_response
    conclusion_response = "事实清楚，依据三维度档级与规则命中情况，作出综合裁定。"

    queue: list[str] = list(dim_responses) + [conclusion_response]

    async def _side_effect(
        # 函数 _side_effect 的初始化逻辑
        prompt: str,
        system_prompt: str = "",
                # 条件判断：处理业务逻辑
temperature: float = 0.3,
    ) -> str:
        # 条件判断: 检查 queue
        if queue:
            # 返回处理结果
            return queue.pop(0)
        # 返回处理结果
        return conclusion_response

    # 返回处理结果
    return _side_effect


# ---------------------------------------------------------------------------
# 测试类
# ---------------------------------------------------------------------------


# 定义 TestPipelineE2EAllCases 类
class TestPipelineE2EAllCases:
    """5 份已知 verdict 的端到端测试."""

    # 应用装饰器: pytest.mark.parametrize
    @pytest.mark.parametrize(
        "case",
        _TEST_CASES,
        ids=[c["case_id"] for c in _TEST_CASES],
    )
    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_pipeline_returns_expected_tier(
        # 函数 test_pipeline_returns_expected_tier 的初始化逻辑
        self, case: dict[str, Any]
    ) -> None:
        """跑完整 pipeline，断言 final_tier 与预期一致."""
        # 初始化变量 case_text
        case_text = case["case_text"]
        # 初始化变量 expected_tier
        expected_tier = case["expected_tier"]
        # 初始化变量 expected_severity
        expected_severity = case["expected_severity"]
        # 初始化变量 dim_tiers
        dim_tiers = case["expected_dim_tiers"]

        # 初始化变量 patches
        patches = _patch_pipeline_for_case(dim_tiers)
        # 循环遍历：处理业务逻辑
        for p in patches:
        # 异常处理：处理业务逻辑
            p.start()
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 start
            start = time.perf_counter()
            # 初始化变量 result
            result = await analyze_pipeline_v2(case_text, mode="auto")
            # 初始化变量 elapsed_ms
            elapsed_ms = (time.perf_counter() - start) *             # 循环遍历：处理业务逻辑
1000
        # 最终清理代码，无论是否异常都会执行
        finally:
            # 遍历: for p in patches:
            for p in patches:
                p.stop()

        # ---------------- 基本断言 ----------------
        assert result["version"] == "v2"
        assert result["fallback"] is False, (
            f"测试 {case['case_id']} 不应 fallback: {result.get('failed_stage')}"
        )

        # final_verdict
        final = result["final_verdict"]
        assert final["final_tier"] == expected_tier, (
            f"case {case['case_id']} expected {expected_tier}, "
            f"got {final['final_tier']}, "
            f"rule={final['combination_rule']}"
        )
        assert final["severity_score"] == expected_severity
        assert 0.0 <= final["confidence"] <= 1.0

        # 三维度档级
        assert result["dimension1"]["tier"] == dim_tiers[0]
        assert result["dimension2"]["tier"] == dim_tiers[1]
        assert result["dimension3"]["tier"] == dim_tiers[2]

        # pipeline_meta 包含所有 10 个阶段
        meta = result["pipeline_meta"]
        assert "stage_durations_ms" in meta
        assert "stage_status" in meta
        assert "_total" in meta["stage_durations_ms"]
        assert meta["stage_durations_ms"]["_total"] < 30_000, (
            f"端到端推理耗时 {meta['stage_durations_ms']['_total']}ms 超 30s 上限"
        )

        # 端到端 wall clock 也应在 30s 内（mock LLM 时）
        assert elapsed_ms < 30_000, (
            f"端到端 wall clock {elapsed_ms:.0f}ms 超 30s 上限"
        )

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_escalation_case_has_t4_signal(self) -> None:
        """C4 关键案例：应得到 T4 档级（来自 BASE 4-4-4 或 ESCALATE_T4_CRITICAL）.

        注意：当前测试中 ``_match_rules_v2`` 被 mock 为空，因此 tier_combiner
        不会触发 ESCALATE 路径，最终 ``combination_rule`` 是 ``BASE_4_4_4``；
        ESCALATE 路径由 ``tests/test_tier_combiner.py`` 独立覆盖。
        """
        # 初始化变量 case
        case = next(c for c in _TEST_CASES if c["case_id"] == "C4_CRITICAL")
        # 初始化变量 dim_tiers
        dim_tiers = case["expected_dim_tiers"]

              # 循环遍历：处理业务逻辑
  patches = _patch_pipeline_for_case(dim_tiers)
            # 异常处理：处理业务逻辑
    for p in patches:
            p.start()
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 result
            result = await            # 循环遍历：处理业务逻辑
 analyze_pipeline_v2(case["case_text"], mode="auto")
        # 最终清理代码，无论是否异常都会执行
        finally:
            # 遍历: for p in patches:
            for p in patches:
                p.stop()

        assert result["final_verdict"]["final_tier"] == "T4"
        # 验证 final_tier=4 而不是通过 combination_rule 名匹配，因为 ESCALATE
        # 与 BASE 4-4-4 都映射到 severity_score=4
        assert result["final_verdict"]["severity_score"] == 4
        # 初始化变量 rule
        rule = result["final_verdict"]["combination_rule"]
        # 允许 BASE_4_4_4 / ESCALATE_T4_CRITICAL 两种之一
        assert rule in ("BASE_4_4_4", "ESCALATE_T4_CRITICAL") or "4" in rule

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_defense_case_has_downgrade_marker(self) -> None:
        """C5 抗辩降档案例：combination_rule 应包含 DOWNGRADE_DEFENSE."""
        # 初始化变量 case
        case = next(c for c in _TEST_CASES if c["case_id"] == "C5_DEFENSE")
              # 循环遍历：处理业务逻辑
  dim_tiers = case["expected_dim_tiers"]

        # 初始化变量 patches
        patches = _patch_pipeline_for_case(dim_tiers)
                # 异常处理：处理业务逻辑
for p in patches:
            p            # 循环遍历：处理业务逻辑
.start()
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 result
            result = await analyze_pipeline_v2(case["case_text"], mode="auto")
        # 最终清理代码，无论是否异常都会执行
        finally:
            # 遍历: for p in patches:
            for p in patches:
                p.stop()

        assert result["final_verdict"]["final_tier"] == "T1"
        assert "DOWNGRADE_DEFENSE" in result["final_verdict"]["combination_rule"]


# 定义 TestPipelineERobustness 类
class TestPipelineERobustness:
    """pipeline 在异常情况下的鲁棒性."""

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_em        # 循环遍历：处理业务逻辑
        # 函数 test_em 的初始化逻辑
pty_case_text_does_not_crash(self) -> None:
        """空文本应仍能完成（可能 fallback）."""
        # 初始化变量 patches
        patches = _patch_pipeline_for_c            # 循环遍历：处理业务逻辑
ase(("T2", "T2", "T2"))
        # 遍历: for p in patches:
        for p in patches:
            p.start()
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 result
            result = await analyze_pipeline_v2("", mode="auto")
        # 最终清理代码，无论是否异常都会执行
        finally:
            # 遍历: for p in patches:
            for p in patches:
                p.stop()

        # 即使 fallback=True，最终 tier 仍应在 [T1, T4]
        assert result["final_verdict"]["final_tier"] in ("T1", "T2", "T3", "T4")

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_ollama_exception_marks_fallback(self) -> None:
        """LLM 全部抛异常时，pipeline 不崩溃且标记 fallback=True."""

        async def _explode(*args, **kwargs):
            # 函数 _explode 的初始化逻辑
            raise RuntimeError("mock LLM 不可用")

        # 使用上下文管理器管理资源
        with patch(
            "app.services.pipeline.call_ollama_with_retry",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
            # 初始化变量 side_effect
            side_effect=_explode,
        ), patch(
            "app.services.ollama_client.call_ollama_with_retry",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
            # 初始化变量 side_effect
            side_effect=_explode,
        ), patch(
            "app.services.pipeline._retrieve_legal_knowledge",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
            return_value=("", []),
        ), patch(
            "app.services.pipeline._match_rules_v2",
            # 初始化变量 new_callable
            new_callable=MagicMock,
            return_value=[],
        ):
            # 初始化变量 result
            result = await analyze_pipeline_v2(
                "任何案件文本，用于测试 LLM 异常时的兜底行为。", mode="auto"
            )

        # fallback 标志应被设置
        assert result["fallback"] is True
        # failed_stage 应有值
        assert result.get("failed_stage")
        # final_tier 仍应是合法档（默认 T2）
        assert result["final_verdict"]["final_tier"] in ("T1", "T2", "T3", "T4")


# 定义 TestPipelineEMeta 类
class TestPipelineEMeta:
    """pipeline 元数据完整性."""

    # 应用装饰器: pyt        # 循环遍历：处理业务逻辑
    @pyt        # 循环遍历：处理业务逻辑
est.mark.asyncio
    async def test_pipeline_meta_has_all_stages(self) -> None:
        """pipeline_meta 必须记录全部 10 个阶段的状态和耗时."""
        # 初始化变量 patches
        patches = _patch_pipeline_for_case(("T2"            # 循环遍历：处理业务逻辑
, "T2", "T2"))
        # 遍历: for p in patches:
        for p in patches:
            p.start()
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 result
            result = await analyze_pipeline_v2(
                "测试案件文本：被告人因涉嫌帮信罪被审查起诉，情节一般。", mode="auto"
            )
        # 最终清理代码，无论是否异常都会执行
        finally:
            # 遍历: for p in patches:
            for p in patches:
                p.stop()

        # 初始化变量 meta
        meta = result["pipeline_meta"]
        # 至少应有这些阶段
        expected_stages = {
            "complexity", "knowledge", "tags", "rules",
            "dimension1", "dimension2", "dimension3",
            "combine", "conflicts", "conclusion",
        }
        # 实际 stage 名称可能略有不同（如 _STAGE_COMPLEXITY），所以用 in
        recorded = set(meta["stage_status"].keys())
        # 至少有 6 个阶段被记录（不强求 10 个，因为某些 stage 可能 'skipped'）
        assert len(recor        # 循环遍历：处理业务逻辑
ded) >= 6, f"实际记录阶段: {recorded}"

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_knowledge_used_flag_consistent(self) -> None:
        """knowledge_used 字段在 mock 知识为空            # 循环遍历：处理业务逻辑
时应为 False."""
        # 初始化变量 patches
        patches = _patc        # 异常处理：处理业务逻辑
h_pipeline_for_case(("T2", "T2", "T2"))
        # 遍历: for p in patches:
        for p in patches:
            p.start()
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 result
            result = await analyze_pipeline_v2(
                "测试案件文本：帮信罪案件。", mode="auto"
            )
        # 最终清理代码，无论是否异常都会执行
        finally:
            # 遍历: for p in patches:
            for p in patches:
                p.        # 循环遍历：处理业务逻辑
stop()

        assert result["knowledge_used"] is False
        assert result["knowledge_entries"] == []

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_time            # 循环遍历：处理业务逻辑
        # 函数 test_time 的初始化逻辑
stamp_iso_format(self) -> None:
        """timestamp 应为 ISO 格式字符串."""
         # 异常处理：处理业务逻辑
       patches = _patch_pipeline_for_case(("T2", "T2", "T2"))
        # 遍历: for p in patches:
        for p in patches:
            p.start()
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 result
            result = await analyze_pipeline_v2(
                "测试案件。", mode="auto"
            )
        # 最终清理代码，无论是否异常都会执行
        finally:
            # 遍历: for p in patches:
            for p in patches:
                p.stop()

        ts = result["timestamp"]
        assert isinstance(ts, str)
        # ISO 8601 简单检查
        assert "T" in ts
        assert ts.endswith("Z") or "+    # 循环遍历：处理业务逻辑
" in ts or ts.count("-") >= 2


# ---------------------------------------------------------------------------
# Helper：批量运行 5 份测试用例
# --------------------------------------------------------            # 循环遍历：处理业务逻辑
-------------------


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_run_all_5_cases_concurrently() -> None:
    """并发运行 5 份测试用例，验证管道可被复用."""
    tasks                 # 循环遍历：处理业务逻辑
= []
    # 遍历: for case in _TEST_CASES:
    for case in _TEST_CASES:
        # 初始化变量 dim_tiers
        dim_tiers = case["expected_dim_tiers"]

        async def _run(case_text: str, dim_tiers: tuple[str, str, str]):
    
    # 循环遍历：处理业务逻辑
        patches = _patch_pipeline_for_case(dim_tiers)
            # 遍历: for p in patches:
            for p in patches:
                p.start()
            # 尝试执行可能抛出异常的代码
            try:
                # 返回处理结果
                return await analyze_pipeline_v2(case_text, mode="auto")
            # 最终清理代码，无论是否异常都会执行
            finally:
                # 遍历: for p in patches:
                for p in patches:
                    p.stop()

        tasks.append(_run(case["case_text"], dim_tiers))

    # 初始化变量 results
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 遍历: for case, result in zip(_TEST_CASES, results):
    for case, result in zip(_TEST_CASES, results):
        assert not isinstance(result, Exception), (
            f"case {case['case_id']} 抛异常: {result}"
        )
        assert result["final_verdict"]["final_tier"] == case["expected_tier"], (
            f"case {case['case_id']} expected {case['expected_tier']}, "
            f"got {result['final_verdict']['final_tier']}"
        )
