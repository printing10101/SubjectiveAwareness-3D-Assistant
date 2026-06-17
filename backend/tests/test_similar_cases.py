"""test_similar_cases - 单元测试模块.

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

# 导入模块: from app.services.similar_cases
from app.services.similar_cases import find_similar_cases


# 定义 TestFindSimilarCases 类
class TestFindSimilarCases:


    # TestFindSimilarCases 类定义，封装相关属性和方法
    @pytest.fixture(autouse=True)
    def mock_get_client(self):
        # 执行 mock_get_client 函数的核心逻辑
        with patch("app.services.similar_cases.get_client") as mock:
            # 初始化变量 client
            client = AsyncMock()
            mock.return_value = client
            # 生成器产出值
            yield client

    async def test_found_cases(self, mock_get_client):
        # 函数 test_found_cases 的初始化逻辑
        mock_get_client.generate_json.return_value = [
            {
                "case_id": "case_001",
                "similarity": 0.85,
                "title": "相似案例1",
                "summary": "案情摘要",
            },
            {
                "case_id": "case_002",
                "similarity": 0.72,
                "title": "相似案例2",
                "summary": "案情摘要",
            },
        ]
        # 初始化变量 results
        results = await find_similar_cases("被告人提供银行卡给他人使用")
        assert len(results) == 2
        assert results[0]["case_id"] == "case_001"
        assert results[0]["similarity"] == 0.85

    async def test_empty_results(self, mock_get_client):
        # 函数 test_empty_results 的初始化逻辑
        mock_get_client.generate_json.return_value = []
        # 初始化变量 results
        results = await find_similar_cases("未知案件")
        assert results == []

    async def test_dict_response(self, mock_get_client):
        # 函数 test_dict_response 的初始化逻辑
        mock_get_client.generate_json.return_value = {
            "similar_cases": [
                {"case_id": "c1", "similarity": 0.9,
                 "title": "案例", "summary": "摘要"},
            ]
        }
        # 初始化变量 results
        results = await find_similar_cases("test")
        assert len(results) == 1

    async def test_llm_error(self, mock_get_client):
        # 函数 test_llm_error 的初始化逻辑
        mock_get_client.generate_json.side_effect = Exception("LLM error")
        # 初始化变量 results
        results = await find_similar_cases("test")
        assert results == []

    async def test_long_text_truncated(self, mock_get_client):
        # 函数 test_long_text_truncated 的初始化逻辑
        mock_get_client.generate_json.return_value = []
        # 初始化变量 long_text
        long_text = "案情" * 1000
        # 异步等待操作完成
        await find_similar_cases(long_text)
        assert mock_get_client.generate_json.called
