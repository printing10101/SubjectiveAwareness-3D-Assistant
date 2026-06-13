from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.knowledge_graph import (
    _sanitize_rule_data,
    create_legal_rule,
    delete_legal_rule,
    get_legal_rule,
    get_legal_rules,
    update_legal_rule,
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    mock_result = MagicMock()
    db.execute = AsyncMock(return_value=mock_result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = MagicMock()
    return db


class TestSanitizeRuleData:
    def test_allows_valid_fields(self):
        data = {"rule_id": "R001", "name": "Test Rule", "invalid_field": "bad"}
        result = _sanitize_rule_data(data)
        assert "rule_id" in result
        assert "name" in result
        assert "invalid_field" not in result

    def test_empty_data(self):
        assert _sanitize_rule_data({}) == {}

    def test_only_valid_fields(self):
        data = {
            "rule_id": "R001", "name": "Name", "description": "Desc",
            "source_law": "Law", "article": "Art", "conditions": "Cond",
            "conclusion": "Conc", "evidence_types": "Types", "weight": 1.0,
        }
        result = _sanitize_rule_data(data)
        assert result == data


class TestGetLegalRules:
    async def test_empty_list(self, mock_db):
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        rules = await get_legal_rules(mock_db)
        assert rules == []

    async def test_with_results(self, mock_db):
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_db.execute.return_value.scalars.return_value.all.return_value = (
            [mock_rule]
        )
        rules = await get_legal_rules(mock_db)
        assert len(rules) == 1

    async def test_pagination(self, mock_db):
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        await get_legal_rules(mock_db, skip=10, limit=50)
        call_args = mock_db.execute.call_args[0][0]
        assert hasattr(call_args, "_limit")


class TestGetLegalRule:
    async def test_not_found(self, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        rule = await get_legal_rule(mock_db, 999)
        assert rule is None

    async def test_found(self, mock_db):
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_db.execute.return_value.scalar_one_or_none.return_value = (
            mock_rule
        )
        rule = await get_legal_rule(mock_db, 1)
        assert rule is not None
        assert rule.id == 1


class TestCreateLegalRule:
    async def test_success(self, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        rule_data = {
            "rule_id": "R001", "name": "Test Rule",
            "description": "Description",
        }
        await create_legal_rule(mock_db, rule_data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_sanitizes_data(self, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        rule_data = {
            "rule_id": "R001", "name": "Test Rule",
            "invalid_field": "should_be_removed",
        }
        await create_legal_rule(mock_db, rule_data)
        mock_db.commit.assert_called_once()

    async def test_db_error(self, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_db.commit.side_effect = Exception("DB error")
        with pytest.raises(HTTPException) as exc:
            await create_legal_rule(
                mock_db, {"rule_id": "R001", "name": "Test"}
            )
        assert exc.value.status_code == 500
        mock_db.rollback.assert_called_once()


class TestUpdateLegalRule:
    async def test_not_found(self, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        with pytest.raises(HTTPException) as exc:
            await update_legal_rule(mock_db, 999, {"title": "New"})
        assert exc.value.status_code == 404


class TestDeleteLegalRule:
    async def test_not_found(self, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        with pytest.raises(HTTPException) as exc:
            await delete_legal_rule(mock_db, 999)
        assert exc.value.status_code == 404
