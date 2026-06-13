from unittest.mock import AsyncMock, patch

import pytest

from app.services.similar_cases import find_similar_cases


class TestFindSimilarCases:
    @pytest.fixture(autouse=True)
    def mock_get_client(self):
        with patch("app.services.similar_cases.get_client") as mock:
            client = AsyncMock()
            mock.return_value = client
            yield client

    async def test_found_cases(self, mock_get_client):
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
        results = await find_similar_cases("被告人提供银行卡给他人使用")
        assert len(results) == 2
        assert results[0]["case_id"] == "case_001"
        assert results[0]["similarity"] == 0.85

    async def test_empty_results(self, mock_get_client):
        mock_get_client.generate_json.return_value = []
        results = await find_similar_cases("未知案件")
        assert results == []

    async def test_dict_response(self, mock_get_client):
        mock_get_client.generate_json.return_value = {
            "similar_cases": [
                {"case_id": "c1", "similarity": 0.9,
                 "title": "案例", "summary": "摘要"},
            ]
        }
        results = await find_similar_cases("test")
        assert len(results) == 1

    async def test_llm_error(self, mock_get_client):
        mock_get_client.generate_json.side_effect = Exception("LLM error")
        results = await find_similar_cases("test")
        assert results == []

    async def test_long_text_truncated(self, mock_get_client):
        mock_get_client.generate_json.return_value = []
        long_text = "案情" * 1000
        await find_similar_cases(long_text)
        assert mock_get_client.generate_json.called
