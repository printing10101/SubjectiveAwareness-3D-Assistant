from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.analysis_service import (
    _compute_knowledge_score,
    get_analyses_for_case,
    get_analysis,
    run_analysis,
)


class TestComputeKnowledgeScore:
    def test_all_dimensions_present(self, sample_analysis_result):
        score = _compute_knowledge_score(sample_analysis_result)
        assert score == pytest.approx(7.0, abs=0.1)

    def test_missing_ground_truth(self):
        result = {"fallback": False, "timestamp": "2024-01-01T00:00:00Z"}
        score = _compute_knowledge_score(result)
        assert score is None

    def test_partial_dimensions(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 8.0, "reasoning": "test"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(8.0, abs=0.1)

    def test_empty_dimensions(self):
        result = {
            "ground_truth_analysis": {},
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score is None

    def test_zero_scores(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 0.0, "reasoning": "test"},
                "dimension2": {"score": 0.0, "reasoning": "test"},
                "dimension3": {"score": 0.0, "reasoning": "test"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(0.0, abs=0.1)

    def test_score_above_ten_clamped(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 12.0, "reasoning": "exceeds max"},
                "dimension2": {"score": 15.0, "reasoning": "exceeds max"},
                "dimension3": {"score": 9.0, "reasoning": "within range"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(9.67, abs=0.1)
        assert 0.0 <= score <= 10.0

    def test_score_below_zero_clamped(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": -5.0, "reasoning": "negative"},
                "dimension2": {"score": -3.0, "reasoning": "negative"},
                "dimension3": {"score": 2.0, "reasoning": "within range"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(0.67, abs=0.1)
        assert 0.0 <= score <= 10.0

    def test_boundary_exact_zero(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 0.0, "reasoning": "boundary"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == 0.0

    def test_boundary_exact_ten(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 10.0, "reasoning": "boundary"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == 10.0

    def test_nan_score_filtered(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": float("nan"), "reasoning": "invalid"},
                "dimension2": {"score": 7.0, "reasoning": "valid"},
                "dimension3": {"score": float("nan"), "reasoning": "invalid"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(7.0, abs=0.1)
        assert 0.0 <= score <= 10.0

    def test_all_nan_scores_returns_none(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": float("nan"), "reasoning": "all nan"},
                "dimension2": {"score": float("nan"), "reasoning": "all nan"},
                "dimension3": {"score": float("nan"), "reasoning": "all nan"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score is None

    def test_score_type_not_number_filtered(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": "invalid_string", "reasoning": "test"},
                "dimension2": {"score": 5.0, "reasoning": "valid"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(5.0, abs=0.1)

    def test_all_scores_max_clamped_to_ten(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 20.0, "reasoning": "way over"},
                "dimension2": {"score": 50.0, "reasoning": "way over"},
                "dimension3": {"score": 100.0, "reasoning": "way over"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == 10.0

    def test_all_scores_min_clamped_to_zero(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": -10.0, "reasoning": "way under"},
                "dimension2": {"score": -50.0, "reasoning": "way under"},
                "dimension3": {"score": -100.0, "reasoning": "way under"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == 0.0

    def test_mixed_extreme_scores_clamped(self):
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": -10.0, "reasoning": "under"},
                "dimension2": {"score": 20.0, "reasoning": "over"},
                "dimension3": {"score": 5.0, "reasoning": "normal"},
            },
            "fallback": False,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(5.0, abs=0.1)
        assert 0.0 <= score <= 10.0


class TestRunAnalysis:
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
        return db

    async def test_case_not_found(self, mock_db):
        """验证案件不存在时抛出 404 异常."""
        mock_db.get.return_value = None
        with pytest.raises(HTTPException) as exc:
            await run_analysis(mock_db, case_id=999)
        assert exc.value.status_code == 404
        assert "案件不存在" in exc.value.detail

    async def test_successful_analysis(self, mock_db, sample_analysis_result):
        """验证正常分析流程：flush 被调用，commit 不被调用."""
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        with patch(
            "app.services.analysis_service.analyze_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result
            result = await run_analysis(mock_db, case_id=1)

            assert result is not None
            mock_db.add.assert_called_once()
            # 重构后: 使用 flush 获取自增ID，不提交事务
            mock_db.flush.assert_called_once()
            mock_db.commit.assert_not_called()
            mock_db.rollback.assert_not_called()

    async def test_flush_refresh_sequence(self, mock_db, sample_analysis_result):
        """验证 flush → refresh 的调用顺序是否正确."""
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        with patch(
            "app.services.analysis_service.analyze_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result
            await run_analysis(mock_db, case_id=1)

            # 验证调用顺序: add → flush → refresh
            mock_db.add.assert_called()
            mock_db.flush.assert_called()
            mock_db.refresh.assert_called()

    async def test_analysis_with_mode(self, mock_db, sample_analysis_result):
        """验证分析模式参数正确传递到管道."""
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        with patch(
            "app.services.analysis_service.analyze_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result
            result = await run_analysis(mock_db, case_id=1, mode="multi")
            assert result is not None
            mock_pipeline.assert_called_with("test case", mode="multi", version="v2")


class TestRunAnalysisTransactionManagement:
    """事务管理专项测试.

    验证 run_analysis 不管理事务生命周期，由调用方负责 commit/rollback。
    """

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.get = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    async def test_no_commit_called(self, mock_db, sample_analysis_result):
        """验证 run_analysis 从未调用 db.commit().

        这是避免事务双重提交的核心保证。
        """
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        with patch(
            "app.services.analysis_service.analyze_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result
            await run_analysis(mock_db, case_id=1)

            mock_db.commit.assert_not_called()

    async def test_no_rollback_called(self, mock_db, sample_analysis_result):
        """验证 run_analysis 从不调用 db.rollback().

        回滚应由调用方统一管理。
        """
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        with patch(
            "app.services.analysis_service.analyze_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result
            await run_analysis(mock_db, case_id=1)

            mock_db.rollback.assert_not_called()

    async def test_exception_propagates_to_caller(
        self, mock_db, sample_analysis_result
    ):
        """验证 flush 异常向上传播，不由 run_analysis 内部捕获.

        这样调用方的上下文管理器或 try/except 可以正确执行 rollback。
        """
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case
        mock_db.flush.side_effect = Exception("DB connection lost")

        with patch(
            "app.services.analysis_service.analyze_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result

            with pytest.raises(Exception) as exc:
                await run_analysis(mock_db, case_id=1)
            assert "DB connection lost" in str(exc.value)

            # 验证 run_analysis 没有尝试 rollback（由调用方处理）
            mock_db.rollback.assert_not_called()

    async def test_caller_can_rollback_on_exception(
        self, mock_db, sample_analysis_result
    ):
        """端到端验证：模拟调用方在异常时执行 rollback.

        模拟典型的调用模式:
            try:
                await run_analysis(db, case_id)
                await db.commit()
            except Exception:
                await db.rollback()
        """
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case
        mock_db.flush.side_effect = Exception("DB error")

        with patch(
            "app.services.analysis_service.analyze_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result

            # 模拟调用方的事务管理模式
            try:
                await run_analysis(mock_db, case_id=1)
                await mock_db.commit()
            except Exception:  # noqa: BLE001
                await mock_db.rollback()

            # 异常发生时 rollback 被调用，commit 未被调用
            mock_db.rollback.assert_called_once()
            mock_db.commit.assert_not_called()

    async def test_caller_commits_on_success(
        self, mock_db, sample_analysis_result
    ):
        """端到端验证：模拟调用方在成功时执行 commit.

        模拟典型的调用模式:
            result = await run_analysis(db, case_id)
            await db.commit()
        """
        mock_case = MagicMock()
        mock_case.case_text = "test case"
        mock_db.get.return_value = mock_case

        with patch(
            "app.services.analysis_service.analyze_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            mock_pipeline.return_value = sample_analysis_result

            # 模拟调用方的事务管理模式
            result = await run_analysis(mock_db, case_id=1)
            assert result is not None
            await mock_db.commit()

            # 成功时 commit 被调用，rollback 未被调用
            mock_db.commit.assert_called_once()
            mock_db.rollback.assert_not_called()


class TestGetAnalysis:
    async def test_found(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_result.scalar_one_or_none.return_value = "analysis_result"
        result = await get_analysis(mock_db, analysis_id=1)
        assert result == "analysis_result"

    async def test_not_found(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_result.scalar_one_or_none.return_value = None
        result = await get_analysis(mock_db, analysis_id=999)
        assert result is None


class TestGetAnalysesForCase:
    async def test_with_results(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_result.scalars.return_value.all.return_value = [
            "analysis1",
            "analysis2",
        ]
        results = await get_analyses_for_case(mock_db, case_id=1)
        assert len(results) == 2

    async def test_empty_results(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_result.scalars.return_value.all.return_value = []
        results = await get_analyses_for_case(mock_db, case_id=999)
        assert results == []
