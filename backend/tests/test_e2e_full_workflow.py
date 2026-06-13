"""完整业务流程端到端测试.

覆盖流程: 文件上传 → 数据解析 → 案例分析 → 报告生成 → 人工审查

测试原则:
- 可独立运行，不依赖外部服务（使用 mock）
- 覆盖完整业务流程的每个阶段
- 验证数据在各阶段间的正确传递
- 确保错误处理和边界情况
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.services.document_processor import process_document
from app.services.pipeline import analyze_pipeline_v2
from app.services.report_generator import generate_report


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------

SAMPLE_CASE_TEXT = """
被告人张某，男，35岁，无业。2023年1月至6月期间，张某明知他人利用信息网络
实施电信网络诈骗犯罪，仍提供自己名下的3张银行卡及U盾帮助支付结算。经查明，
上述账户共接收诈骗资金流水120万元，张某从中获利1.5万元。多名被害人遭受
电信网络诈骗损失。案发后，张某被公安机关抓获，如实供述犯罪事实。
"""

SAMPLE_DOCUMENT_CONTENT = {
    "case_id": "TEST_E2E_001",
    "defendant_name": "张某",
    "case_summary": SAMPLE_CASE_TEXT,
    "evidence_list": [
        {"type": "银行流水", "description": "3张银行卡交易记录"},
        {"type": "被告人供述", "description": "如实供述犯罪事实"},
    ],
}


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_dimension_result(tier: str) -> str:
    """构造维度分析的 mock LLM 返回."""
    return json.dumps(
        {
            "tier": tier,
            "reasoning": f"[mock] 维度分析推理：符合 {tier} 档情形。",
            "confidence": 0.85,
            "key_indicators": [f"mock_indicator_{tier}"],
            "triggered_rules": [],
        },
        ensure_ascii=False,
    )


def _patch_pipeline_mocks(dim_tiers: tuple[str, str, str] = ("T3", "T3", "T3")):
    """为 pipeline 创建所有必要的 mock patches."""
    dim_responses = [
        _make_mock_dimension_result(dim_tiers[0]),
        _make_mock_dimension_result(dim_tiers[1]),
        _make_mock_dimension_result(dim_tiers[2]),
    ]
    conclusion_response = "事实清楚，证据充分，作出如下结论。"

    queue = list(dim_responses) + [conclusion_response]

    async def _ollama_side_effect(*args, **kwargs) -> str:
        if queue:
            return queue.pop(0)
        return conclusion_response

    return [
        patch(
            "app.services.pipeline.call_ollama_with_retry",
            new_callable=AsyncMock,
            side_effect=_ollama_side_effect,
        ),
        patch(
            "app.services.ollama_client.call_ollama_with_retry",
            new_callable=AsyncMock,
            side_effect=_ollama_side_effect,
        ),
        patch(
            "app.services.pipeline._retrieve_legal_knowledge",
            new_callable=AsyncMock,
            return_value=("", []),
        ),
        patch(
            "app.services.pipeline._match_rules_v2",
            new_callable=MagicMock,
            return_value=[],
        ),
    ]


# ---------------------------------------------------------------------------
# 阶段 1: 文件上传与数据解析
# ---------------------------------------------------------------------------


class TestStage1DocumentProcessing:
    """阶段 1: 文件上传与数据解析测试."""

    def test_process_document_from_text(self) -> None:
        """测试从文本内容处理文档."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8",
        ) as f:
            f.write(SAMPLE_CASE_TEXT)
            temp_path = f.name

        try:
            # 创建 UploadFile 对象
            with open(temp_path, "rb") as file:
                upload_file = UploadFile(
                    file=file,
                    filename=Path(temp_path).name,
                    headers={"content-type": "text/plain"},
                )
                result = asyncio.run(process_document(upload_file))
                # process_document 返回字符串
                assert isinstance(result, str)
                assert len(result) > 0
        finally:
            Path(temp_path).unlink()

    def test_process_document_extracts_key_info(self) -> None:
        """测试文档处理提取关键信息."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8",
        ) as f:
            f.write(SAMPLE_CASE_TEXT)
            temp_path = f.name

        try:
            # 创建 UploadFile 对象
            with open(temp_path, "rb") as file:
                upload_file = UploadFile(
                    file=file,
                    filename=Path(temp_path).name,
                    headers={"content-type": "text/plain"},
                )
                result = asyncio.run(process_document(upload_file))
                # process_document 返回字符串，应包含案件关键要素
                assert isinstance(result, str)
                assert "张某" in result or "被告人" in result
        finally:
            Path(temp_path).unlink()

    def test_process_document_handles_empty_file(self) -> None:
        """测试处理空文件."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            temp_path = f.name

        try:
            # 创建 UploadFile 对象
            with open(temp_path, "rb") as file:
                upload_file = UploadFile(
                    file=file,
                    filename=Path(temp_path).name,
                    headers={"content-type": "text/plain"},
                )
                result = asyncio.run(process_document(upload_file))
                # 空文件应返回结果但内容为空
                assert result is not None
        finally:
            Path(temp_path).unlink()


# ---------------------------------------------------------------------------
# 阶段 2: 案例分析 (Pipeline)
# ---------------------------------------------------------------------------


class TestStage2CaseAnalysis:
    """阶段 2: 案例分析测试."""

    @pytest.mark.asyncio
    async def test_pipeline_full_analysis(self) -> None:
        """测试完整 pipeline 分析流程."""
        patches = _patch_pipeline_mocks(("T3", "T3", "T3"))
        for p in patches:
            p.start()

        try:
            result = await analyze_pipeline_v2(SAMPLE_CASE_TEXT, mode="auto")

            # 验证基本结构
            assert result["version"] == "v2"
            assert "final_verdict" in result
            assert "dimension1" in result
            assert "dimension2" in result
            assert "dimension3" in result

            # 验证最终裁定
            final = result["final_verdict"]
            assert "final_tier" in final
            assert "severity_score" in final
            assert 0.0 <= final["confidence"] <= 1.0

        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_pipeline_produces_valid_tier(self) -> None:
        """测试 pipeline 产生有效的档级."""
        patches = _patch_pipeline_mocks(("T2", "T2", "T2"))
        for p in patches:
            p.start()

        try:
            result = await analyze_pipeline_v2(SAMPLE_CASE_TEXT, mode="auto")
            tier = result["final_verdict"]["final_tier"]
            assert tier in ("T1", "T2", "T3", "T4")
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_pipeline_includes_metadata(self) -> None:
        """测试 pipeline 包含完整的元数据."""
        patches = _patch_pipeline_mocks(("T2", "T2", "T2"))
        for p in patches:
            p.start()

        try:
            result = await analyze_pipeline_v2(SAMPLE_CASE_TEXT, mode="auto")
            assert "pipeline_meta" in result
            assert "stage_status" in result["pipeline_meta"]
            assert "timestamp" in result
        finally:
            for p in patches:
                p.stop()


# ---------------------------------------------------------------------------
# 阶段 3: 报告生成
# ---------------------------------------------------------------------------


class TestStage3ReportGeneration:
    """阶段 3: 报告生成测试."""

    @pytest.mark.asyncio
    async def test_generate_report_from_analysis(self) -> None:
        """测试从分析结果生成报告."""
        patches = _patch_pipeline_mocks(("T3", "T3", "T3"))
        for p in patches:
            p.start()

        try:
            analysis_result = await analyze_pipeline_v2(SAMPLE_CASE_TEXT, mode="auto")

            # 创建 mock Case 对象
            from unittest.mock import MagicMock
            mock_case = MagicMock()
            mock_case.id = 1
            mock_case.title = "测试案件"
            mock_case.case_text = SAMPLE_CASE_TEXT
            mock_case.created_at = datetime.now()

            report = generate_report(analysis_result, mock_case)

            assert report is not None
            assert isinstance(report, dict)
            # 报告应包含章节结构和元数据
            assert "chapters" in report
            assert "metadata" in report

        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_report_contains_recommendation(self) -> None:
        """测试报告包含裁定建议."""
        patches = _patch_pipeline_mocks(("T3", "T3", "T3"))
        for p in patches:
            p.start()

        try:
            analysis_result = await analyze_pipeline_v2(SAMPLE_CASE_TEXT, mode="auto")

            # 创建 mock Case 对象
            from unittest.mock import MagicMock
            mock_case = MagicMock()
            mock_case.id = 1
            mock_case.title = "测试案件"
            mock_case.case_text = SAMPLE_CASE_TEXT
            mock_case.created_at = datetime.now()

            report = generate_report(analysis_result, mock_case)

            # 报告应包含裁定相关信息
            report_str = json.dumps(report, ensure_ascii=False, default=str) if isinstance(report, dict) else report
            assert "裁定" in report_str or "建议" in report_str or "tier" in report_str.lower()

        finally:
            for p in patches:
                p.stop()


# ---------------------------------------------------------------------------
# 阶段 4: 人工审查支持
# ---------------------------------------------------------------------------


class TestStage4ManualReview:
    """阶段 4: 人工审查支持测试."""

    @pytest.mark.asyncio
    async def test_result_supports_review_workflow(self) -> None:
        """测试结果支持人工审查工作流."""
        patches = _patch_pipeline_mocks(("T3", "T3", "T3"))
        for p in patches:
            p.start()

        try:
            result = await analyze_pipeline_v2(SAMPLE_CASE_TEXT, mode="auto")

            # 应包含审查所需的关键信息
            assert "final_verdict" in result
            assert "dimension1" in result
            assert "dimension2" in result
            assert "dimension3" in result

            # 审查者需要看到推理依据
            final = result["final_verdict"]
            assert "combination_rule" in final or "reasoning" in str(final)

        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_result_includes_confidence_for_reviewer(self) -> None:
        """测试结果包含供审查者参考的置信度."""
        patches = _patch_pipeline_mocks(("T2", "T2", "T2"))
        for p in patches:
            p.start()

        try:
            result = await analyze_pipeline_v2(SAMPLE_CASE_TEXT, mode="auto")
            confidence = result["final_verdict"]["confidence"]
            assert 0.0 <= confidence <= 1.0
            # 置信度应帮助审查者判断是否需要更仔细审查
        finally:
            for p in patches:
                p.stop()


# ---------------------------------------------------------------------------
# 完整流程集成测试
# ---------------------------------------------------------------------------


class TestFullWorkflowIntegration:
    """完整业务流程集成测试."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self) -> None:
        """测试完整端到端工作流."""
        # 阶段 1: 文档处理 - 创建 UploadFile 对象
        from io import BytesIO

        from fastapi import UploadFile

        file_content = SAMPLE_CASE_TEXT.encode("utf-8")
        upload_file = UploadFile(
            filename="test_case.txt",
            file=BytesIO(file_content)
        )

        try:
            doc_result = await process_document(upload_file)
            # process_document 返回字符串（案件文本）
            case_text = doc_result if isinstance(doc_result, str) else doc_result.get("case_text", doc_result.get("content", ""))
            assert len(case_text) > 0

            # 阶段 2: 案例分析
            patches = _patch_pipeline_mocks(("T3", "T3", "T3"))
            for p in patches:
                p.start()

            try:
                analysis_result = await analyze_pipeline_v2(case_text, mode="auto")
                assert analysis_result["version"] == "v2"
                assert "final_verdict" in analysis_result

                # 阶段 3: 报告生成 - 需要传入 case 对象
                from datetime import datetime
                from unittest.mock import MagicMock

                mock_case = MagicMock()
                mock_case.id = 1
                mock_case.title = "测试案件"
                mock_case.case_text = case_text
                mock_case.created_at = datetime.now()

                report = generate_report(analysis_result, mock_case)
                assert report is not None

                # 阶段 4: 验证审查支持
                final = analysis_result["final_verdict"]
                assert "final_tier" in final
                assert "confidence" in final

            finally:
                for p in patches:
                    p.stop()

        finally:
            # UploadFile 不需要手动删除
            pass

    @pytest.mark.asyncio
    async def test_workflow_handles_pipeline_failure_gracefully(self) -> None:
        """测试工作流在 pipeline 失败时优雅处理."""
        # 模拟 LLM 完全不可用
        async def _explode(*args, **kwargs):
            raise RuntimeError("LLM 服务不可用")

        with patch(
            "app.services.pipeline.call_ollama_with_retry",
            new_callable=AsyncMock,
            side_effect=_explode,
        ), patch(
            "app.services.ollama_client.call_ollama_with_retry",
            new_callable=AsyncMock,
            side_effect=_explode,
        ), patch(
            "app.services.pipeline._retrieve_legal_knowledge",
            new_callable=AsyncMock,
            return_value=("", []),
        ), patch(
            "app.services.pipeline._match_rules_v2",
            new_callable=MagicMock,
            return_value=[],
        ):
            # 即使 LLM 失败，pipeline 也应返回结果（fallback 模式）
            result = await analyze_pipeline_v2(SAMPLE_CASE_TEXT, mode="auto")
            assert result is not None
            assert result.get("fallback", False) is True
            # 最终裁定仍应有默认值
            assert "final_verdict" in result


# ---------------------------------------------------------------------------
# 边界情况与异常处理
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """边界情况测试."""

    @pytest.mark.asyncio
    async def test_very_long_case_text(self) -> None:
        """测试处理超长案件文本."""
        long_text = SAMPLE_CASE_TEXT * 50  # 约 50 倍长度
        patches = _patch_pipeline_mocks(("T2", "T2", "T2"))
        for p in patches:
            p.start()

        try:
            result = await analyze_pipeline_v2(long_text, mode="auto")
            assert result is not None
            assert "final_verdict" in result
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_case_with_special_characters(self) -> None:
        """测试处理包含特殊字符的案件文本."""
        special_text = "被告人李某\n\t\r特殊符号：@#$%^&*()案件内容..."
        patches = _patch_pipeline_mocks(("T1", "T1", "T1"))
        for p in patches:
            p.start()

        try:
            result = await analyze_pipeline_v2(special_text, mode="auto")
            assert result is not None
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_concurrent_analyses(self) -> None:
        """测试并发分析多个案件."""
        patches = _patch_pipeline_mocks(("T2", "T2", "T2"))
        for p in patches:
            p.start()

        try:
            tasks = [
                analyze_pipeline_v2(SAMPLE_CASE_TEXT, mode="auto")
                for _ in range(3)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                assert not isinstance(result, Exception)
                assert "final_verdict" in result
        finally:
            for p in patches:
                p.stop()
