"""test_sentencing - 单元测试模块.

本模块包含帮信罪主观明知智能分析系统的测试用例，
用于验证相关功能的正确性和稳定性。

测试范围：
    - 功能验证：确保核心功能按预期工作
    - 边界测试：验证边界条件下的行为
    - 异常处理：确保异常情况的正确处理
    - 性能测试：验证系统性能指标

测试框架：pytest
依赖服务：FastAPI TestClient, 数据库测试环境

# 应用装饰器: author 帮信罪智能分析系统开发团队
@author 帮信罪智能分析系统开发团队
# 应用装饰器: version 1.0.0
@version 1.0.0
"""

# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, patch

# 导入模块: pytest
import pytest

# 导入模块: from app.services.sentencing
from app.services.sentencing import get_sentencing_suggestion


# 定义 TestGetSentencingSuggestion 类
class TestGetSentencingSuggestion:


    # TestGetSentencingSuggestion 类定义，封装相关属性和方法
    @pytest.fixture(autouse=True)
    def mock_get_client(self):
        # 执行 mock_get_client 函数的核心逻辑
        with patch("app.services.sentencing.get_client") as mock:
            # 初始化变量 client
            client = AsyncMock()
            mock.return_value = client
            # 生成器产出值
            yield client

    async def test_successful_suggestion(
        # 函数 test_successful_suggestion 的初始化逻辑
            self, sample_analysis_result, mock_get_client
    ):
        mock_get_client.generate_json.return_value = {
            "suggested_sentence": "有期徒刑一年",
            "reasoning": "根据案情分析",
            "legal_basis": ["刑法第287条"],
            "aggravating_factors": ["涉案金额较大"],
            "mitigating_factors": ["自首"],
        }
        # 初始化变量 result
        result = await get_sentencing_suggestion(sample_analysis_result)
        assert result["suggested_sentence"] == "有期徒刑一年"
        assert "reasoning" in result

    async def test_with_legal_rules(
        # 函数 test_with_legal_rules 的初始化逻辑
            self, sample_analysis_result, mock_get_client
    ):
        mock_get_client.generate_json.return_value = {
            "suggested_sentence": "有期徒刑六个月",
            "reasoning": "规则匹配分析",
        }
        # 初始化变量 rules
        rules = [{"name": "规则1", "description": "test"}]
        # 初始化变量 result
        result = await get_sentencing_suggestion(
            sample_analysis_result, legal_rules=rules
        )
        assert result["suggested_sentence"] == "有期徒刑六个月"

    async def test_empty_rules(self, sample_analysis_result, mock_get_client):
        # 函数 test_empty_rules 的初始化逻辑
        mock_get_client.generate_json.return_value = {
            "suggested_sentence": "有期徒刑一年",
            "reasoning": "无适用规则",
        }
        # 初始化变量 result
        result = await get_sentencing_suggestion(
            sample_analysis_result, legal_rules=[]
        )
        assert result["suggested_sentence"] == "有期徒刑一年"

    async def test_llm_error(self, sample_analysis_result, mock_get_client):
        # 函数 test_llm_error 的初始化逻辑
        mock_get_client.generate_json.side_effect = Exception("LLM error")
        # 初始化变量 result
        result = await get_sentencing_suggestion(sample_analysis_result)
        assert result["suggested_sentence"] == "待定"
        assert "分析失败" in result["reasoning"]
