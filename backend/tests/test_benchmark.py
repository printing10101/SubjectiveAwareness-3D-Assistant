"""性能基准测试.

使用 pytest-benchmark 对核心功能进行性能基准测试。
建立 API 响应时间基线和各函数执行性能基线。
"""

# 导入模块: json
import json
# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, patch

# 导入模块: pytest
import pytest

# 导入模块: from app.services.pipeline
from app.services.pipeline import classify_complexity
# 导入模块: from app.utils.common
from app.utils.common import generate_cache_key, sanitize_json_string


# 定义 TestBenchmarkKeyFunctions 类
class TestBenchmarkKeyFunctions:


    # TestBenchmarkKeyFunctions 类定义，封装相关属性和方法
    def test_benchmark_classify_complexity(self, benchmark):
        # 执行 test_benchmark_classify_complexity 函数的核心逻辑
        text = "a" * 500
        # 初始化变量 result
        result = benchmark(classify_complexity, text)
        assert result in ("simple", "medium", "complex")

    def test_benchmark_sanitize_json(self, benchmark):

        # 执行 test_benchmark_sanitize_json 函数的核心逻辑
        text = '```json\n{"key": "value", "nested": {"a": 1}}\n```'
        # 初始化变量 result
        result = benchmark(sanitize_json_string, text)
        assert "```" not in result

    def test_benchmark_cache_key_generation(self, benchmark):

        # 执行 test_benchmark_cache_key_generation 函数的核心逻辑
        benchmark.pedantic(
            generate_cache_key,
            # 初始化变量 args
            args=("analysis", "case_text_123", "mode", "single"),
            # 初始化变量 rounds
            rounds=100,
            # 初始化变量 iterations
            iterations=10,
        )

    def test_benchmark_mask_sensitive_info(self, benchmark):

        # 执行 test_benchmark_mask_sensitive_info 函数的核心逻辑
        from app.utils.encryption import mask_sensitive_info  # noqa: PLC0415

        # 初始化变量 text
        text = (
            "张三，身份证110101199001011234，电话13812345678，"
            "银行卡6222021234567890123，邮箱test@example.com"
        )
        # 初始化变量 result
        result = benchmark(mask_sensitive_info, text)
        assert "110101199001011234" not in result


# 定义 TestBenchmarkPipeline 类
class TestBenchmarkPipeline:


    # TestBenchmarkPipeline 类定义，封装相关属性和方法
    async def test_benchmark_analyze_pipeline_simple(
        # 函数 test_benchmark_analyze_pipeline_simple 的初始化逻辑
            self, benchmark, sample_case_text
    ):
        # 使用上下文管理器管理资源
        with patch(
            "app.services.pipeline.call_ollama_with_retry",
            # 初始化变量 new_callable
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

            # 导入模块: from app.services.pipeline
            from app.services.pipeline import analyze_pipeline  # noqa: PLC0415

            # 初始化变量 result
            result = await benchmark(
                analyze_pipeline, sample_case_text, mode="single"
            )
            assert result["fallback"] is False

    async def test_benchmark_analysis_service(
        # 函数 test_benchmark_analysis_service 的初始化逻辑
            self, benchmark, sample_analysis_result
    ):
        # 导入模块: from app.services.analysis_service
        from app.services.analysis_service import _compute_knowledge_score  # noqa: PLC0415

        # 初始化变量 result
        result = benchmark(_compute_knowledge_score, sample_analysis_result)
        assert result is not None


# 应用装饰器: pytest.mark.benchmark
@pytest.mark.benchmark
# 定义 TestBenchmarkEncryption 类
class TestBenchmarkEncryption:
    # TestBenchmarkEncryption 类定义，封装相关属性和方法
    def test_benchmark_encrypt_text(self, benchmark):
        # 函数 test_benchmark_encrypt_text 的初始化逻辑
        from app.utils.encryption import EncryptedText  # noqa: PLC0415

        et = EncryptedText()
        # 初始化变量 original
        original = "这是一段需要加密的敏感案件描述文本" * 10
        # 初始化变量 result
        result = benchmark(et.process_bind_param, original, None)
        assert result != original

    def test_benchmark_decrypt_text(self, benchmark):
        # 函数 test_benchmark_decrypt_text 的初始化逻辑
        from app.utils.encryption import EncryptedText  # noqa: PLC0415

        et = EncryptedText()
        # 初始化变量 original
        original = "测试文本" * 20
        # 初始化变量 encrypted
        encrypted = et.process_bind_param(original, None)
        # 初始化变量 result
        result = benchmark(et.process_result_value, encrypted, None)
        assert result == original
