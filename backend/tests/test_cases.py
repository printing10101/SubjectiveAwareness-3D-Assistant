"""案件模块测试.

测试案件 CRUD API 端点的功能。
使用 conftest.py 中统一的 client fixture。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.case import Case, CaseStatus
from app.schemas.case import PaginatedResponse
from app.services.case_service import (
    _build_sort_column,
    _validate_pagination_params,
    get_cases,
)


# 注意：不再定义模块级别的 client fixture，使用 conftest.py 中的统一 fixture
# 这确保所有测试使用相同的数据库注入和依赖覆盖配置


def _make_mock_case(
    case_id: int,
    title: str,
    status: CaseStatus = CaseStatus.pending,
):
    """创建模拟案件对象."""
    case = MagicMock(spec=Case)
    case.id = case_id
    case.title = title
    case.status = status
    case.description = f"description_{case_id}"
    case.case_text = f"案件文本_{case_id}"
    case.created_by = 1
    case.created_at = "2024-01-01T00:00:00Z"
    case.updated_at = "2024-01-01T00:00:00Z"
    return case


def _setup_mock_db(
    mock_session: AsyncMock,
    items: list,
    total: int | None = None,
) -> None:
    """设置模拟数据库会话的返回值."""
    mock_session.execute = AsyncMock()

    count_scalar = MagicMock()
    count_scalar.scalar_one.return_value = total if total is not None else len(items)

    items_scalar = MagicMock()
    items_scalar.all.return_value = items
    items_scalar.scalars.return_value = items_scalar

    mock_session.execute.side_effect = [count_scalar, items_scalar]


class TestPaginatedResponse:
    """PaginatedResponse 数据类单元测试."""

    def test_basic_pagination(self):
        resp = PaginatedResponse(
            items=["a", "b", "c"],
            total=10,
            page=1,
            page_size=3,
        )
        assert resp.items == ["a", "b", "c"]
        assert resp.total == 10
        assert resp.page == 1
        assert resp.page_size == 3
        assert resp.total_pages == 4
        assert resp.has_next is True
        assert resp.has_prev is False

    def test_first_page(self):
        resp = PaginatedResponse(
            items=[1, 2],
            total=20,
            page=1,
            page_size=10,
        )
        assert resp.has_prev is False
        assert resp.has_next is True
        assert resp.total_pages == 2

    def test_last_page(self):
        resp = PaginatedResponse(
            items=[19, 20],
            total=20,
            page=2,
            page_size=10,
        )
        assert resp.has_prev is True
        assert resp.has_next is False
        assert resp.total_pages == 2

    def test_single_page(self):
        resp = PaginatedResponse(
            items=[1, 2, 3],
            total=3,
            page=1,
            page_size=10,
        )
        assert resp.total_pages == 1
        assert resp.has_next is False
        assert resp.has_prev is False

    def test_empty_result(self):
        resp = PaginatedResponse(
            items=[],
            total=0,
            page=1,
            page_size=10,
        )
        assert resp.total_pages == 1
        assert resp.has_next is False
        assert resp.has_prev is False

    def test_total_pages_rounding(self):
        resp = PaginatedResponse(
            items=[],
            total=25,
            page=2,
            page_size=10,
        )
        assert resp.total_pages == 3

    def test_middle_page(self):
        resp = PaginatedResponse(
            items=[],
            total=30,
            page=2,
            page_size=10,
        )
        assert resp.has_prev is True
        assert resp.has_next is True
        assert resp.total_pages == 3

    def test_exact_fit_page(self):
        resp = PaginatedResponse(
            items=[],
            total=50,
            page=5,
            page_size=10,
        )
        assert resp.total_pages == 5
        assert resp.has_next is False


class TestValidatePaginationParams:
    """分页参数验证单元测试."""

    def test_valid_params(self):
        _validate_pagination_params(
            page=1, page_size=20,
            sort_by="created_at", sort_order="desc",
        )

    def test_page_zero(self):
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                page=0, page_size=20,
                sort_by="id", sort_order="asc",
            )
        assert exc.value.status_code == 422
        assert "页码" in exc.value.detail

    def test_page_negative(self):
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                page=-1, page_size=20,
                sort_by="id", sort_order="asc",
            )
        assert exc.value.status_code == 422

    def test_page_size_zero(self):
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                page=1, page_size=0,
                sort_by="id", sort_order="asc",
            )
        assert exc.value.status_code == 422
        assert "每页条数" in exc.value.detail

    def test_page_size_exceeds_max(self):
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                page=1, page_size=101,
                sort_by="id", sort_order="asc",
            )
        assert exc.value.status_code == 422

    def test_page_size_negative(self):
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                page=1, page_size=-5,
                sort_by="id", sort_order="asc",
            )
        assert exc.value.status_code == 422

    def test_invalid_sort_by(self):
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                page=1, page_size=20,
                sort_by="invalid_field", sort_order="asc",
            )
        assert exc.value.status_code == 422
        assert "无效的排序字段" in exc.value.detail

    def test_invalid_sort_order(self):
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                page=1, page_size=20,
                sort_by="id", sort_order="random",
            )
        assert exc.value.status_code == 422
        assert "无效的排序方向" in exc.value.detail

    def test_sql_injection_sort_by(self):
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                page=1, page_size=20,
                sort_by="1; DROP TABLE cases;",
                sort_order="asc",
            )
        assert exc.value.status_code == 422

    def test_all_valid_sort_fields(self):
        valid_fields = [
            "id", "title", "status",
            "created_by", "created_at", "updated_at",
        ]
        for field in valid_fields:
            _validate_pagination_params(
                page=1, page_size=20,
                sort_by=field, sort_order="asc",
            )

    def test_max_edge_page_size(self):
        _validate_pagination_params(
            page=1, page_size=100,
            sort_by="id", sort_order="asc",
        )

    def test_min_edge_page_size(self):
        _validate_pagination_params(
            page=1, page_size=1,
            sort_by="id", sort_order="asc",
        )


class TestBuildSortColumn:
    """排序表达式构建单元测试."""

    def test_sort_asc(self):
        expr = _build_sort_column("id", "asc")
        assert expr is not None

    def test_sort_desc(self):
        expr = _build_sort_column("created_at", "desc")
        assert expr is not None

    def test_sort_by_status(self):
        expr = _build_sort_column("status", "asc")
        assert expr is not None

    def test_sort_security(self):
        with pytest.raises(AttributeError):
            _build_sort_column("__invalid__", "asc")


@pytest.mark.asyncio
class TestGetCasesService:
    """get_cases 服务函数单元测试."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    async def test_basic_pagination_first_page(self, mock_db):
        items = [_make_mock_case(i, f"案件_{i}") for i in range(1, 11)]
        _setup_mock_db(mock_db, items, total=25)

        result = await get_cases(mock_db, page=1, page_size=10)

        assert isinstance(result, PaginatedResponse)
        assert len(result.items) == 10
        assert result.total == 25
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 3
        assert result.has_next is True
        assert result.has_prev is False

    async def test_last_page(self, mock_db):
        items = [_make_mock_case(i, f"案件_{i}") for i in range(21, 26)]
        _setup_mock_db(mock_db, items, total=25)

        result = await get_cases(mock_db, page=3, page_size=10)

        assert len(result.items) == 5
        assert result.total == 25
        assert result.page == 3
        assert result.total_pages == 3
        assert result.has_next is False
        assert result.has_prev is True

    async def test_empty_result(self, mock_db):
        _setup_mock_db(mock_db, [], total=0)

        result = await get_cases(mock_db, page=1, page_size=10)

        assert result.items == []
        assert result.total == 0
        assert result.total_pages == 1
        assert result.has_next is False
        assert result.has_prev is False

    async def test_single_item(self, mock_db):
        items = [_make_mock_case(1, "单案件")]
        _setup_mock_db(mock_db, items, total=1)

        result = await get_cases(mock_db, page=1, page_size=10)

        assert len(result.items) == 1
        assert result.total == 1
        assert result.total_pages == 1
        assert result.has_next is False
        assert result.has_prev is False

    async def test_with_status_filter(self, mock_db):
        items = [_make_mock_case(1, "已完成案件", CaseStatus.completed)]
        _setup_mock_db(mock_db, items, total=1)

        result = await get_cases(
            mock_db, page=1, page_size=10, status_filter=CaseStatus.completed
        )

        assert len(result.items) == 1
        assert result.total == 1

    async def test_custom_page_size(self, mock_db):
        items = [_make_mock_case(i, f"案件_{i}") for i in range(1, 6)]
        _setup_mock_db(mock_db, items, total=15)

        result = await get_cases(mock_db, page=2, page_size=5)

        assert len(result.items) == 5
        assert result.page == 2
        assert result.page_size == 5
        assert result.total_pages == 3

    async def test_invalid_page_raises(self, mock_db):
        with pytest.raises(HTTPException) as exc:
            await get_cases(mock_db, page=0, page_size=10)
        assert exc.value.status_code == 422

    async def test_invalid_page_size_raises(self, mock_db):
        with pytest.raises(HTTPException) as exc:
            await get_cases(mock_db, page=1, page_size=200)
        assert exc.value.status_code == 422

    async def test_invalid_sort_by_raises(self, mock_db):
        with pytest.raises(HTTPException) as exc:
            await get_cases(
                mock_db, page=1, page_size=10,
                sort_by="unknown_field",
            )
        assert exc.value.status_code == 422

    async def test_total_matches_item_count(self, mock_db):
        n = 7
        items = [_make_mock_case(i, f"案件_{i}") for i in range(1, n + 1)]
        _setup_mock_db(mock_db, items, total=n)

        result = await get_cases(mock_db, page=1, page_size=100)

        assert result.total == n
        assert len(result.items) == n
        assert result.total_pages == 1


class TestCasesAPIEndpoint:
    """案件列表 API 端点集成测试."""

    def test_list_cases_returns_paginated_response(self, client):
        response = client.get("/api/cases/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert "has_next" in data
        assert "has_prev" in data
        assert isinstance(data["items"], list)

    def test_list_cases_default_params(self, client):
        response = client.get("/api/cases/")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_cases_custom_page_and_size(self, client):
        response = client.get("/api/cases/?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_list_cases_sort_by_title_desc(self, client):
        response = client.get("/api/cases/?sort_by=title&sort_order=desc")
        assert response.status_code == 200

    def test_list_cases_sort_by_created_at_asc(self, client):
        response = client.get("/api/cases/?sort_by=created_at&sort_order=asc")
        assert response.status_code == 200

    def test_list_cases_status_filter(self, client):
        response = client.get("/api/cases/?status=pending")
        assert response.status_code == 200

    def test_list_cases_invalid_page(self, client):
        response = client.get("/api/cases/?page=0")
        assert response.status_code == 422

    def test_list_cases_invalid_page_size_negative(self, client):
        response = client.get("/api/cases/?page_size=0")
        assert response.status_code == 422

    def test_list_cases_page_size_too_large(self, client):
        response = client.get("/api/cases/?page_size=101")
        assert response.status_code == 422

    def test_list_cases_last_page_has_no_next(self, client):
        response = client.get("/api/cases/?page=1&page_size=100")
        assert response.status_code == 200
        data = response.json()
        assert data["has_prev"] is False
        if data["total"] <= data["page_size"]:
            assert data["has_next"] is False

    def test_list_cases_has_prev_on_page_two(self, client):
        response = client.get("/api/cases/?page=2&page_size=1")
        assert response.status_code in (200, 422)
        if response.status_code == 200:
            data = response.json()
            if len(data["items"]) > 0:
                assert data["has_prev"] is True

    def test_create_case(self, client):
        response = client.post(
            "/api/cases/",
            json={
                "title": "测试案件",
                "case_text": "这是一个测试案件的描述。",
                "status": "pending",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "测试案件"
        assert "id" in data

    def test_get_case_not_found(self, client):
        response = client.get("/api/cases/99999")
        assert response.status_code == 404
