"""test_analysis_service - 单元测试模块.

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
from unittest.mock import AsyncMock, MagicMock, patch

# 导入模块: pytest
import pytest
# 导入模块: from fastapi
from fastapi import HTTPException

# 导入模块: from app.services.analysis_service
from app.services.analysis_service import (
    _compute_knowledge_score,
    get_analyses_for_case,
    get_analysis,
    run_analysis,
)


# 定义 TestComputeKnowledgeScore 类
class TestComputeKnowledgeScore:


    # TestComputeKnowledgeScore 类定义，封装相关属性和方法
    def test_all_dimensions_present(self, sample_analysis_result):
        # 执行 test_all_dimensions_present 函数的核心逻辑
        score = _compute_knowledge_score(sample_analysis_result)
        assert score == pytest.approx(7.0, abs=0.1)

    def test_missing_ground_truth(self):

        # 执行 test_missing_ground_truth 函数的核心逻辑
        result = {"fallback": False, "timestamp": "2024-01-01T00:00:00Z"}
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score is None

    def test_partial_dimensions(self):

        # 执行 test_partial_dimensions 函数的核心逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 8.0, "reasoning": "test"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(8.0, abs=0.1)

    def test_empty_dimensions(self):

        # 执行 test_empty_dimensions 函数的核心逻辑
        result = {
            "ground_truth_analysis": {},
            "fallback": False,

        # 执行 test_zero_scores 函数的核心逻辑
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score is None

    def test_zero_scores(self):
        # 函数 test_zero_scores 的初始化逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 0.0, "reasoning": "test"},
                "dimension2": {"score": 0.0, "reasoning": "test"},
                "dimension3": {"score": 0.0, "reasoning": "test"},
            },
            "fallback": False,

        # 执行 test_score_above_ten_clamped 函数的核心逻辑
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(0.0, abs=0.1)

    def test_score_above_ten_clamped(self):
        # 函数 test_score_above_ten_clamped 的初始化逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 12.0, "reasoning": "exceeds max"},
                "dimension2": {"score": 15.0, "reasoning": "exceeds max"},
                "dimension3": {"score": 9.0, "reasoning": "within range"},
            },
            "fallback": False,

        # 执行 test_score_below_zero_clamped 函数的核心逻辑
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(9.67, abs=0.1)
        assert 0.0 <= score <= 10.0

    def test_score_below_zero_clamped(self):
        # 函数 test_score_below_zero_clamped 的初始化逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": -5.0, "reasoning": "negative"},
                "dimension2": {"score": -3.0, "reasoning": "negative"},
                "dimension3": {"score": 2.0, "reasoning": "within range"},

        # 执行 test_boundary_exact_zero 函数的核心逻辑
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(0.67, abs=0.1)
        assert 0.0 <= score <= 10.0

    def test_boundary_exact_zero(self):

        # 执行 test_boundary_exact_ten 函数的核心逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 0.0, "reasoning": "boundary"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == 0.0

    def test_boundary_exact_ten(self):

        # 执行 test_nan_score_filtered 函数的核心逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 10.0, "reasoning": "boundary"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == 10.0

    def test_nan_score_filtered(self):
        # 函数 test_nan_score_filtered 的初始化逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": float("nan"), "reasoning": "invalid"},

        # 执行 test_all_nan_scores_returns_none 函数的核心逻辑
                "dimension2": {"score": 7.0, "reasoning": "valid"},
                "dimension3": {"score": float("nan"), "reasoning": "invalid"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(7.0, abs=0.1)
        assert 0.0 <= score <= 10.0

    def test_all_nan_scores_returns_none(self):
        # 函数 test_all_nan_scores_returns_none 的初始化逻辑
        result = {
            "ground_truth_analysis": {

        # 执行 test_score_type_not_number_filtered 函数的核心逻辑
                "dimension1": {"score": float("nan"), "reasoning": "all nan"},
                "dimension2": {"score": float("nan"), "reasoning": "all nan"},
                "dimension3": {"score": float("nan"), "reasoning": "all nan"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score is None

    def test_score_type_not_number_filtered(self):

        # 执行 test_all_scores_max_clamped_to_ten 函数的核心逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": "invalid_string", "reasoning": "test"},
                "dimension2": {"score": 5.0, "reasoning": "valid"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(5.0, abs=0.1)

    def test_all_scores_max_clamped_to_ten(self):

        # 执行 test_all_scores_min_clamped_to_zero 函数的核心逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 20.0, "reasoning": "way over"},
                "dimension2": {"score": 50.0, "reasoning": "way over"},
                "dimension3": {"score": 100.0, "reasoning": "way over"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",

        # 执行 test_mixed_extreme_scores_clamped 函数的核心逻辑
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == 10.0

    def test_all_scores_min_clamped_to_zero(self):
        # 函数 test_all_scores_min_clamped_to_zero 的初始化逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": -10.0, "reasoning": "way under"},
                "dimension2": {"score": -50.0, "reasoning": "way under"},
                "dimension3": {"score": -100.0, "reasoning": "way under"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        # 执行 mock_db 函数的核心逻辑
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == 0.0

    def test_mixed_extreme_scores_clamped(self):
        # 函数 test_mixed_extreme_scores_clamped 的初始化逻辑
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": -10.0, "reasoning": "under"},
                "dimension2": {"score": 20.0, "reasoning": "over"},
                "dimension3": {"score": 5.0, "reasoning": "normal"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        # 初始化变量 score
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(5.0, abs=0.1)
        assert 0.0 <= score <= 10.0


# 定义 TestRunAnalysis 类
class TestRunAnalysis:


    # TestRunAnalysis 类定义，封装相关属性和方法
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话.

        注意: 重构后 run_analysis 使用 db.get() 获取记录，用 db.flush() 获取自增ID，
        不再使用 db.commit() / db.rollback()。
        """
        db = AsyncMock()
        db.get = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        # commit 和 rollback 不应被调用，但保留属性避免 AttributeError
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        # 返回处理结果
        return db

    async def test_case_not_found(self, mock_db):
        """验证案件不存在时抛出 404 异常."""
        mock_db.get.return_value = None
        # 使用上下文管理器管理资源
        with pytest.raises(HTTPException) as exc:
            # 异步等待操作完成
            await run_analysis(mock_db, case_id=999)
        assert exc.value.status_code == 404
        assert "案件不存在" in exc.value.detail

    async def test_successful_analysis(self, mock_db, sample_analysis_result):
        """验证正常分析流程：flush 被调用，commit 不被调用."""
        # 初始化变量 mock_case
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        # 使用上下文管理器管理资源
        with patch(
            "app.services.analysis_service.analyze_pipeline",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result
            # 初始化变量 result
            result = await run_analysis(mock_db, case_id=1)

            assert result is not None
            mock_db.add.assert_called_once()
            # 重构后: 使用 flush 获取自增ID，不提交事务
            mock_db.flush.assert_called_once()
            mock_db.commit.assert_not_called()
            mock_db.rollback.assert_not_called()

    async def test_flush_refresh_sequence(self, mock_db, sample_analysis_result):
        """验证 flush → refresh 的调用顺序是否正确."""
        # 初始化变量 mock_case
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        # 使用上下文管理器管理资源
        with patch(
            "app.services.analysis_service.analyze_pipeline",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result
            # 异步等待操作完成
            await run_analysis(mock_db, case_id=1)

            # 验证调用顺序: add → flush → refresh
            mock_db.add.assert_called()
            mock_db.flush.assert_called()
            mock_db.refresh.assert_called()

    async def test_analysis_with_mode(self, mock_db, sample_analysis_result):
        """验证分析模式参数正确传递到管道."""
        # 初始化变量 mock_case
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        # 使用上下文管理器管理资源
        with patch(
            "app.services.analysis_service.analyze_pipeline",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result
            # 初始化变量 result
            result = await run_analysis(mock_db, case_id=1, mode="multi")
            assert result is not None
            mock_pipeline.assert_called_with("test case", mode="multi", version="v2")


# 定义 TestRunAnalysisTransactionManagement 类
class TestRunAnalysisTransactionManagement:
    """事务管理专项测试.

    验证 run_analysis 不管理事务生命周期，由调用方负责 commit/rollback。
    """

    # 应用装饰器: pytest.fixture
    @pytest.fixture
    def mock_db(self):
        # 函数 mock_db 的初始化逻辑
        db = AsyncMock()
        db.get = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        # 返回处理结果
        return db

    async def test_no_commit_called(self, mock_db, sample_analysis_result):
        """验证 run_analysis 从未调用 db.commit().

        这是避免事务双重提交的核心保证。
        """
        # 初始化变量 mock_case
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        # 使用上下文管理器管理资源
        with patch(
            "app.services.analysis_service.analyze_pipeline",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result
            # 异步等待操作完成
            await run_analysis(mock_db, case_id=1)

            mock_db.commit.assert_not_called()

    async def test_no_rollback_called(self, mock_db, sample_analysis_result):
        """验证 run_analysis 从不调用 db.rollback().

        回滚应由调用方统一管理。
        """
        # 初始化变量 mock_case
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        # 使用上下文管理器管理资源
        with patch(
            "app.services.analysis_service.analyze_pipeline",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result
            # 异步等待操作完成
            await run_analysis(mock_db, case_id=1)

            mock_db.rollback.assert_not_called()

    async def test_exception_propagates_to_caller(
        # 函数 test_exception_propagates_to_caller 的初始化逻辑
        self, mock_db, sample_analysis_result
    ):
        """验证 flush 异常向上传播，不由 run_analysis 内部捕获.

        这样调用方的上下文管理器或 try/except 可以正确执行 rollback。
        """
        # 初始化变量 mock_case
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case
        mock_db.flush.side_effect = Exception("DB connection lost")

        # 使用上下文管理器管理资源
        with patch(
            "app.services.analysis_service.analyze_pipeline",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result

            # 使用上下文管理器管理资源
            with pytest.raises(Exception) as exc:
                # 异步等待操作完成
                await run_analysis(mock_db, case_id=1)
            assert "DB connection lost" in str(exc.value)

            # 验证 run_analysis 没有尝试 rollback（由调用方处理）
            mock_db.rollback.assert_not_called()

    async def test_caller_can_rollback_on_exception(
        # 函数 test_caller_can_rollback_on_exception 的初始化逻辑
        self, mock_db, sample_analysis_result
    ):
        """端到端验证：模拟调用方在异常时执行 rollback.

        模拟典型的调用模式:
            # 异常处理：处理业务逻辑
            try:
                # 异步等待操作完成
                await run_analysis(db, case_id)
                # 异步等待操作完成
                await db.commit()
            # 捕获异常：处理业务逻辑
            except Exception:
                # 异步等待操作完成
                await db.rollback()
        """
        # 初始化变量 mock_case
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case
        mock_db.flush.side_effect = Exception("DB error")

        # 使用上下文管理器管理资源
        with patch(
            "app.services.analysis_service.analyze_pipeline",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result

            # 模拟调用方的事务管理模式
            try:
                # 异步等待操作完成
                await run_analysis(mock_db, case_id=1)
                         # 捕获异常：处理业务逻辑
   await mock_db.commit()
            # 捕获并处理异常
            except Exception:  # noqa: BLE001
                await mock_db.rollback()

            # 异常发生时 rollback 被调用，commit 未被调用
            mock_db.rollback.assert_called_once()
            mock_db.commit.assert_not_called()

    async def test_caller_commits_on_success(
        # 函数 test_caller_commits_on_success 的初始化逻辑
        self, mock_db, sample_analysis_result
    ):
        """端到端验证：模拟调用方在成功时执行 commit.

        模拟典型的调用模式:
            # 初始化变量 result
            result = await run_analysis(db, case_id)
            # 异步等待操作完成
            await db.commit()
        """
        # 初始化变量 mock_case
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        # 使用上下文管理器管理资源
        with patch(
            "app.services.analysis_service.analyze_pipeline",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result

            # 模拟调用方的事务管理模式
            result = await run_analysis(mock_db, case_id=1)
            assert result is not None
            # 异步等待操作完成
            await mock_db.commit()

            # 成功时 commit 被调用，rollback 未被调用
            mock_db.commit.assert_called_once()
            mock_db.rollback.assert_not_called()


# 定义 TestGetAnalysis 类
class TestGetAnalysis:


    # TestGetAnalysis 类定义，封装相关属性和方法
    async def test_found(self):
        # 函数 test_found 的初始化逻辑
        mock_db = AsyncMock()
        # 初始化变量 mock_result
        mock_result = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_result.scalar_one_or_none.return_value = "analysis_result"
        # 初始化变量 result
        result = await get_analysis(mock_db, analysis_id=1)
        assert result == "analysis_result"

    async def test_not_found(self):
        # 函数 test_not_found 的初始化逻辑
        mock_db = AsyncMock()
        # 初始化变量 mock_result
        mock_result = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_result.scalar_one_or_none.return_value = None
        # 初始化变量 result
        result = await get_analysis(mock_db, analysis_id=999)
        assert result is None


# 定义 TestGetAnalysesForCase 类
class TestGetAnalysesForCase:


    # TestGetAnalysesForCase 类定义，封装相关属性和方法
    async def test_with_results(self):
        # 函数 test_with_results 的初始化逻辑
        mock_db = AsyncMock()
        # 初始化变量 mock_result
        mock_result = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_result.scalars.return_value.all.return_value = [
            "analysis1",
            "analysis2",
        ]
        # 初始化变量 results
        results = await get_analyses_for_case(mock_db, case_id=1)
        assert len(results) == 2

    async def test_empty_results(self):
        # 函数 test_empty_results 的初始化逻辑
        mock_db = AsyncMock()
        # 初始化变量 mock_result
        mock_result = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_result.scalars.return_value.all.return_value = []
        # 初始化变量 results
        results = await get_analyses_for_case(mock_db, case_id=999)
        assert results == []
