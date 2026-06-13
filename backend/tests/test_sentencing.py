from unittest.mock import AsyncMock, patch

import pytest

from app.services.sentencing import get_sentencing_suggestion


class TestGetSentencingSuggestion:
    @pytest.fixture(autouse=True)
    def mock_get_client(self):
        with patch("app.services.sentencing.get_client") as mock:
            client = AsyncMock()
            mock.return_value = client
            yield client

    async def test_successful_suggestion(
            self, sample_analysis_result, mock_get_client
    ):
        mock_get_client.generate_json.return_value = {
            "suggested_sentence": "有期徒刑一年",
            "reasoning": "根据案情分析",
            "legal_basis": ["刑法第287条"],
            "aggravating_factors": ["涉案金额较大"],
            "mitigating_factors": ["自首"],
        }
        result = await get_sentencing_suggestion(sample_analysis_result)
        assert result["suggested_sentence"] == "有期徒刑一年"
        assert "reasoning" in result

    async def test_with_legal_rules(
            self, sample_analysis_result, mock_get_client
    ):
        mock_get_client.generate_json.return_value = {
            "suggested_sentence": "有期徒刑六个月",
            "reasoning": "规则匹配分析",
        }
        rules = [{"name": "规则1", "description": "test"}]
        result = await get_sentencing_suggestion(
            sample_analysis_result, legal_rules=rules
        )
        assert result["suggested_sentence"] == "有期徒刑六个月"

    async def test_empty_rules(self, sample_analysis_result, mock_get_client):
        mock_get_client.generate_json.return_value = {
            "suggested_sentence": "有期徒刑一年",
            "reasoning": "无适用规则",
        }
        result = await get_sentencing_suggestion(
            sample_analysis_result, legal_rules=[]
        )
        assert result["suggested_sentence"] == "有期徒刑一年"

    async def test_llm_error(self, sample_analysis_result, mock_get_client):
        mock_get_client.generate_json.side_effect = Exception("LLM error")
        result = await get_sentencing_suggestion(sample_analysis_result)
        assert result["suggested_sentence"] == "待定"
        assert "分析失败" in result["reasoning"]
