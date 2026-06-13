"""性能基准测试.

使用 pytest-benchmark 对核心功能进行性能基准测试。
建立 API 响应时间基线和各函数执行性能基线。
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.pipeline import classify_complexity
from app.utils.common import generate_cache_key, sanitize_json_string


class TestBenchmarkKeyFunctions:
    def test_benchmark_classify_complexity(self, benchmark):
        text = "a" * 500
        result = benchmark(classify_complexity, text)
        assert result in ("simple", "medium", "complex")

    def test_benchmark_sanitize_json(self, benchmark):
        text = '```json\n{"key": "value", "nested": {"a": 1}}\n```'
        result = benchmark(sanitize_json_string, text)
        assert "```" not in result

    def test_benchmark_cache_key_generation(self, benchmark):
        benchmark.pedantic(
            generate_cache_key,
            args=("analysis", "case_text_123", "mode", "single"),
            rounds=100,
            iterations=10,
        )

    def test_benchmark_mask_sensitive_info(self, benchmark):
        from app.utils.encryption import mask_sensitive_info  # noqa: PLC0415

        text = (
            "张三，身份证110101199001011234，电话13812345678，"
            "银行卡6222021234567890123，邮箱test@example.com"
        )
        result = benchmark(mask_sensitive_info, text)
        assert "110101199001011234" not in result


class TestBenchmarkPipeline:
    async def test_benchmark_analyze_pipeline_simple(
            self, benchmark, sample_case_text
    ):
        with patch(
            "app.services.pipeline.call_ollama_with_retry",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = json.dumps(
                {
                    "subjective_knowledge": "明知",
                    "sentence": "有期徒刑一年",
                    "ground_truth_analysis": {
                        "dimension1": {"score": 8.0, "reasoning": "test"},
                        "dimension2": {"score": 7.0, "reasoning": "test"},
                        "dimension3": {"score": 6.0, "reasoning": "test"},
                    },
                }
            )

            from app.services.pipeline import analyze_pipeline  # noqa: PLC0415

            result = await benchmark(
                analyze_pipeline, sample_case_text, mode="single"
            )
            assert result["fallback"] is False

    async def test_benchmark_analysis_service(
            self, benchmark, sample_analysis_result
    ):
        from app.services.analysis_service import _compute_knowledge_score  # noqa: PLC0415

        result = benchmark(_compute_knowledge_score, sample_analysis_result)
        assert result is not None


@pytest.mark.benchmark
class TestBenchmarkEncryption:
    def test_benchmark_encrypt_text(self, benchmark):
        from app.utils.encryption import EncryptedText  # noqa: PLC0415

        et = EncryptedText()
        original = "这是一段需要加密的敏感案件描述文本" * 10
        result = benchmark(et.process_bind_param, original, None)
        assert result != original

    def test_benchmark_decrypt_text(self, benchmark):
        from app.utils.encryption import EncryptedText  # noqa: PLC0415

        et = EncryptedText()
        original = "测试文本" * 20
        encrypted = et.process_bind_param(original, None)
        result = benchmark(et.process_result_value, encrypted, None)
        assert result == original
