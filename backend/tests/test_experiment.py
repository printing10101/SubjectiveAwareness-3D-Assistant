"""test_experiment - 单元测试模块.

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

# 导入模块: from app.services.experiment
from app.services.experiment import run_experiment


# 定义 TestRunExperiment 类
class TestRunExperiment:


    # TestRunExperiment 类定义，封装相关属性和方法
    async def test_simple_experiment(self):
        # 函数 test_simple_experiment 的初始化逻辑
        result = await run_experiment("test_experiment", {"param1": "value1"})
        assert result["experiment_name"] == "test_experiment"
        assert result["status"] == "completed"
        assert result["params"] == {"param1": "value1"}
        assert "accuracy" in result["metrics"]
        assert "response_time" in result["metrics"]

    async def test_empty_params(self):
        # 函数 test_empty_params 的初始化逻辑
        result = await run_experiment("empty_test", {})
        assert result["experiment_name"] == "empty_test"
        assert result["params"] == {}

    async def test_complex_params(self):
        # 函数 test_complex_params 的初始化逻辑
        params = {"model": "deepseek-r1:7b", "temperature": 0.3, "top_k": 3}
        # 初始化变量 result
        result = await run_experiment("sentencing_v2", params)
        assert result["params"] == params
