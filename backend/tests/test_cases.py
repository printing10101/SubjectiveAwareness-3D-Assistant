"""案件模块测试.

测试案件 CRUD API 端点的功能。
使用 conftest.py 中统一的 client fixture。
"""

# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, MagicMock

# 导入模块: pytest
import pytest
# 导入模块: from fastapi
from fastapi import HTTPException

# 导入模块: from app.models.case
from app.models.case import Case, CaseStatus
# 导入模块: from app.schemas.case
from app.schemas.case import PaginatedResponse
# 导入模块: from app.services.case_service
from app.services.case_service import (
    _build_sort_column,
    _validate_pagination_params,
    get_cases,
)


# 注意：不再定义模块级别的 client fixture，使用 conftest.py 中的统一 fixture
# 这确保所有测试使用相同的数据库注入和依赖覆盖配置


def _make_mock_case(
    # 函数 _make_mock_case 的初始化逻辑
    case_id: int,


    # 执行 _make_mock_case 函数的核心逻辑
    title: str,
    status: CaseStatus = CaseStatus.pending,
):
    """创建模拟案件对象."""
    # 初始化变量 case
    case = MagicMock(spec=Case)
    case.id = case_id
    case.title = title
    case.status = status
    case.description = f"description_{case_id}"
    case.case_text = f"案件文本_{case_id}"
    case.created_by = 1
    case.created_at = "2024-01-01T00:00:00Z"
    case.updated_at = "2024-01-01T00:00:00Z"
    # 返回处理结果
    return case


def _setup_mock_db(
    # 函数 _setup_mock_db 的初始化逻辑
    mock_session: AsyncMock,


    # 执行 _setup_mock_db 函数的核心逻辑
    items: list,
    total: int | None = None,
) -> None:
    """设置模拟数据库会话的返回值."""
    mock_session.execute = AsyncMock()

    # 初始化变量 count_scalar
    count_scalar = MagicMock()
    count_scalar.scalar_one.return_value = total if total is not None else len(items)

    # 初始化变量 items_scalar
    items_scalar = MagicMock()
    items_scalar.all.return_value = items
    items_scalar.scalars.return_value = items_scalar

    mock_session.execute.side_effect = [count_scalar, items_scalar]


# 定义 TestPaginatedResponse 类
class TestPaginatedResponse:
    """PaginatedResponse 数据类单元测试."""

    def test_basic_pagination(self):

        # 执行 test_basic_pagination 函数的核心逻辑
        resp = PaginatedResponse(
            # 初始化变量 items
            items=["a", "b", "c"],
            # 初始化变量 total
            total=10,
            # 初始化变量 page
            page=1,
            # 初始化变量 page_size
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

        # 执行 test_first_page 函数的核心逻辑
        resp = PaginatedResponse(
            # 初始化变量 items
            items=[1, 2],
            # 初始化变量 total
            total=20,
            # 初始化变量 page
            page=1,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.has_prev is False
        assert resp.has_next is True
        assert resp.total_pages == 2

    def test_last_page(self):

        # 执行 test_last_page 函数的核心逻辑
        resp = PaginatedResponse(
            # 初始化变量 items
            items=[19, 20],
            # 初始化变量 total
            total=20,
            # 初始化变量 page
            page=2,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.has_prev is True
        assert resp.has_next is False
        assert resp.total_pages == 2

    def test_single_page(self):

        # 执行 test_single_page 函数的核心逻辑
        resp = PaginatedResponse(
            # 初始化变量 items
            items=[1, 2, 3],
            # 初始化变量 total
            total=3,
            # 初始化变量 page
            page=1,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.total_pages == 1
        assert resp.has_next is False
        assert resp.has_prev is False

    def test_empty_result(self):

        # 执行 test_empty_result 函数的核心逻辑
        resp = PaginatedResponse(
            # 初始化变量 items
            items=[],
            # 初始化变量 total
            total=0,
            # 初始化变量 page
            page=1,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.total_pages == 1
        assert resp.has_next is False
        assert resp.has_prev is False

    def test_total_pages_rounding(self):

        # 执行 test_total_pages_rounding 函数的核心逻辑
        resp = PaginatedResponse(
            # 初始化变量 items
            items=[],
            # 初始化变量 total
            total=25,
            # 初始化变量 page
            page=2,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.total_pages == 3

    def test_middle_page(self):

        # 执行 test_exact_fit_page 函数的核心逻辑
        resp = PaginatedResponse(
            # 初始化变量 items
            items=[],
            # 初始化变量 total
            total=30,
            # 初始化变量 page
            page=2,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.has_prev is True
        assert resp.has_next is True
        assert resp.total_pages == 3

    def test_exact_fit_page(self):

        # 执行 test_valid_params 函数的核心逻辑
        resp = PaginatedResponse(
            # 初始化变量 items
            items=[],
            # 初始化变量 total
            total=50,
            # 初始化变量 page
            page=5,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.total_pages == 5
        assert resp.has_next is False


# 定义 TestValidatePaginationParams 类
class TestValidatePaginationParams:
    """分页参数验证单元测试."""

    def test_valid_params(self):
        # 函数 test_valid_params 的初始化逻辑
        _validate_pagination_params(
            # 初始化变量 page
            page=1, page_size=20,
            # 初始化变量 sort_by
            sort_by="created_at", sort_order="desc",
        )

    def test_page_zero(self):

        # 执行 test_page_negative 函数的核心逻辑
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                # 初始化变量 page
                page=0, page_size=20,
                # 初始化变量 sort_by
                sort_by="id", sort_order="asc",
            )
        assert exc.value.status_code == 422
        assert "页码" in exc.value.detail

    def test_page_negative(self):

        # 执行 test_page_size_zero 函数的核心逻辑
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                # 初始化变量 page
                page=-1, page_size=20,
                # 初始化变量 sort_by
                sort_by="id", sort_order="asc",
            )
        assert exc.value.status_code == 422

    def test_page_size_zero(self):

        # 执行 test_page_size_exceeds_max 函数的核心逻辑
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                # 初始化变量 page
                page=1, page_size=0,
                # 初始化变量 sort_by
                sort_by="id", sort_order="asc",
            )
        assert exc.value.status_code == 422
        assert "每页条数" in exc.value.detail

    def test_page_size_exceeds_max(self):

        # 执行 test_page_size_negative 函数的核心逻辑
        with pytest.raises(HTTPException) as exc:

        # 执行 test_invalid_sort_by 函数的核心逻辑
            _validate_pagination_params(
                # 初始化变量 page
                page=1, page_size=101,
                # 初始化变量 sort_by
                sort_by="id", sort_order="asc",
            )
        assert exc.value.status_code == 422

    def test_page_size_negative(self):

        # 执行 test_invalid_sort_order 函数的核心逻辑
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                # 初始化变量 page
                page=1, page_size=-5,
                # 初始化变量 sort_by
                sort_by="id", sort_order="asc",
            )
        assert exc.value.status_code == 422

    def test_invalid_sort_by(self):

        # 执行 test_sql_injection_sort_by 函数的核心逻辑
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                # 初始化变量 page
                page=1, page_size=20,
                # 初始化变量 sort_by
                sort_by="invalid_field", sort_order="asc",
            )
        assert exc.value.status_code == 422
        assert "无效的排序字段" in exc.value.detail

    def test_invalid_sort_order(self):

        # 执行 test_all_valid_sort_fields 函数的核心逻辑
        with pytest.raises(HTTPException) as exc:
            _validate_pagination_params(
                # 初始化变量 page
                page=1, page_size=20,
                # 初始化变量 sort_by
                sort_by="id", sort_order="random",
            )
        assert exc.value.status_code == 422
        assert "无效的排序方向" in exc.value.detail

    def test_sql_injection_sort_by(self):

        # 执行 test_max_edge_page_size 函数的核心逻辑
        with pytest.raises(HTTPException) as exc:

        # 执行 test_min_edge_page_size 函数的核心逻辑
            _validate_pagination_params(
                # 初始化变量 page
                page=1, page_size=20,
                # 初始化变量 sort_by
                sort_by="1; DROP TABLE cases;",
                # 初始化变量 sort_order
                sort_order="asc",
            )
        assert exc.value.status_code == 422

    def test_all_valid_sort_fields(self):

        # 执行 test_sort_asc 函数的核心逻辑
        valid_fields = [
            "id", "title", "status",
            "created_by", "created_at", "updated_at",
        ]
        # 循环遍历：处理业务逻辑
        for field in valid_fields:

        # 执行 test_sort_by_status 函数的核心逻辑
            _validate_pagination_params(
                # 初始化变量 page
                page=1, page_size=20,
                # 初始化变量 sort_by
                sort_by=field, sort_order="asc",
            )

    def test_max_edge_page_size(self):

        # 执行 test_sort_security 函数的核心逻辑
        _validate_pagination_params(
            # 初始化变量 page
            page=1, page_size=100,
            # 初始化变量 sort_by
            sort_by="id", sort_order="asc",
        )

    def test_min_edge_page_size(self):
        # 执行 mock_db 函数的核心逻辑
        _validate_pagination_params(
            # 初始化变量 page
            page=1, page_size=1,
            # 初始化变量 sort_by
            sort_by="id", sort_order="asc",
        )


# 定义 TestBuildSortColumn 类
class TestBuildSortColumn:
    """排序表达式构建单元测试."""

    def test_sort_asc(self):
        # 函数 test_sort_asc 的初始化逻辑
        expr = _build_sort_column("id", "asc")
        assert expr is not None

    def test_sort_desc(self):
        # 函数 test_sort_desc 的初始化逻辑
        expr = _build_sort_column("created_at", "desc")
        assert expr is not None

    def test_sort_by_status(self):
        # 函数 test_sort_by_status 的初始化逻辑
        expr = _build_sort_column("status", "asc")
        assert expr is not None

    def test_sort_security(self):
        # 函数 test_sort_security 的初始化逻辑
        with pytest.raises(AttributeError):
            _build_sort_column("__invalid__", "asc")


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
# 定义 TestGetCasesService 类
class TestGetCasesService:
    """get_cases 服务函数单元测试."""

    # 应用装饰器: pytest.fixture
    @pytest.fixture
    def mock_db(self):
        # 函数 mock_db 的初始化逻辑
        return AsyncMock()

    async def test_basic_pagination_first_page(self, mock_db):
        # 函数 test_basic_pagination_first_page 的初始化逻辑
        items = [_make_mock_case(i, f"案件_{i}") for i in range(1, 11)]
        _setup_mock_db(mock_db, items, total=25)

        # 初始化变量 result
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
        # 函数 test_last_page 的初始化逻辑
        items = [_make_mock_case(i, f"案件_{i}") for i in range(21, 26)]
        _setup_mock_db(mock_db, items, total=25)

        # 初始化变量 result
        result = await get_cases(mock_db, page=3, page_size=10)

        assert len(result.items) == 5
        assert result.total == 25
        assert result.page == 3
        assert result.total_pages == 3
        assert result.has_next is False
        assert result.has_prev is True

    async def test_empty_result(self, mock_db):
        # 函数 test_empty_result 的初始化逻辑
        _setup_mock_db(mock_db, [], total=0)

        # 初始化变量 result
        result = await get_cases(mock_db, page=1, page_size=10)

        assert result.items == []
        assert result.total == 0
        assert result.total_pages == 1
        assert result.has_next is False
        assert result.has_prev is False

    async def test_single_item(self, mock_db):
        # 函数 test_single_item 的初始化逻辑
        items = [_make_mock_case(1, "单案件")]
        _setup_mock_db(mock_db, items, total=1)

        # 初始化变量 result
        result = await get_cases(mock_db, page=1, page_size=10)

        assert len(result.items) == 1
        assert result.total == 1
        assert result.total_pages == 1
        assert result.has_next is False
        assert result.has_prev is False

    async def test_with_status_filter(self, mock_db):
        # 函数 test_with_status_filter 的初始化逻辑
        items = [_make_mock_case(1, "已完成案件", CaseStatus.completed)]
        _setup_mock_db(mock_db, items, total=1)

        # 初始化变量 result
        result = await get_cases(
            mock_db, page=1, page_size=10, status_filter=CaseStatus.completed
        )

        assert len(result.items) == 1
        assert result.total == 1

    async def test_custom_page_size(self, mock_db):
        # 函数 test_custom_page_size 的初始化逻辑
        items = [_make_mock_case(i, f"案件_{i}") for i in range(1, 6)]
        _setup_mock_db(mock_db, items, total=15)

        # 初始化变量 result
        result = await get_cases(mock_db, page=2, page_size=5)

        assert len(result.items) == 5
        assert result.page == 2
        assert result.page_size == 5
        assert result.total_pages == 3

    async def test_invalid_page_raises(self, mock_db):
        # 函数 test_invalid_page_raises 的初始化逻辑
        with pytest.raises(HTTPException) as exc:
            # 异步等待操作完成
            await get_cases(mock_db, page=0, page_size=10)
        assert exc.value.status_code == 422

    async def test_invalid_page_size_raises(self, mock_db):

        # 执行 test_list_cases_returns_paginated_response 函数的核心逻辑
        with pytest.raises(HTTPException) as exc:
            # 异步等待操作完成
            await get_cases(mock_db, page=1, page_size=200)
        assert exc.value.status_code == 422

    async def test_invalid_sort_by_raises(self, mock_db):
        # 函数 test_invalid_sort_by_raises 的初始化逻辑
        with pytest.raises(HTTPException) as exc:
            # 异步等待操作完成
            await get_cases(
                mock_db, page=1, page_size=10,
                # 初始化变量 sort_by
                sort_by="unknown_field",
            )
        assert exc.value.status_code == 422

    async def test_total_matches_item_count(self, mock_db):

        # 执行 test_list_cases_default_params 函数的核心逻辑
        n = 7
        # 初始化变量 items
        items = [_make_mock_case(i, f"案件_{i}") for i in range(1, n + 1)]
        _setup_mock_db(mock_db, items, total=n)

        # 初始化变量 result
        result = await get_cases(mock_db, page=1, page_size=100)

        assert result.total == n
        assert len(result.items) == n
        assert result.total_pages == 1


# 定义 TestCasesAPIEndpoint 类
class TestCasesAPIEndpoint:
    """案件列表 API 端点集成测试."""

    def test_list_cases_returns_paginated_response(self, client):
        # 函数 test_list_cases_returns_paginated_response 的初始化逻辑
        response = client.get("/api/cases/")
        assert response.status_code == 200
        # 初始化变量 data
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

        # 执行 test_list_cases_sort_by_created_at_asc 函数的核心逻辑
        response = client.get("/api/cases/")
        assert response.status_code == 200
        # 初始化变量 data
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_cases_custom_page_and_size(self, client):

        # 执行 test_list_cases_invalid_page_size_negative 函数的核心逻辑
        response = client.get("/api/cases/?page=1&page_size=5")
        assert response.status_code == 200
        # 初始化变量 data
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_list_cases_sort_by_title_desc(self, client):

        # 执行 test_list_cases_last_page_has_no_next 函数的核心逻辑
        response = client.get("/api/cases/?sort_by=title&sort_order=desc")
        assert response.status_code == 200

    def test_list_cases_sort_by_created_at_asc(self, client):

        # 执行 test_list_cases_has_prev_on_page_two 函数的核心逻辑
        response = client.get("/api/cases/?sort_by=created_at&sort_order=asc")
        assert response.status_code == 200

    def test_list_cases_status_filter(self, client):

        # 执行 test_create_case 函数的核心逻辑
        response = client.get("/api/cases/?status=pending")
        assert response.status_code == 200

    def test_list_cases_invalid_page(self, client):
        # 函数 test_list_cases_invalid_page 的初始化逻辑
        response = client.get("/api/cases/?page=0")
        assert response.status_code == 422

    def test_list_cases_invalid_page_size_negative(self, client):

        # 执行 test_get_case_not_found 函数的核心逻辑
        response = client.get("/api/cases/?page_size=0")
        assert response.status_code == 422

    def test_list_cases_page_size_too_large(self, client):
        # 函数 test_list_cases_page_size_too_large 的初始化逻辑
        response = client.get("/api/cases/?page_size=101")
        assert response.status_code == 422

    def test_list_cases_last_page_has_no_next(self, client):
        # 函数 test_list_cases_last_page_has_no_next 的初始化逻辑
        response = client.get("/api/cases/?page=1&page_size=100")
        assert response.status_code == 200
        # 初始化变量 data
        data = response.json()
        assert data["has_prev"] is False
        # 条件判断：处理业务逻辑
        if data["total"] <= data["page_size"]:
            assert data["has_next"] is False

    def test_list_cases_has_prev_on_page_two(self, client):
        # 函数 test_list_cases_has_prev_on_page_two 的初始化逻辑
        response = client.get("/api/cases/?page=2&page_size=1")
        assert response.stat        # 条件判断：处理业务逻辑
us_code in (200, 422)
        # 条件判断: 检查 response.status_code            # 条件判断：处
        if response.status_code            # 条件判断：处理业务逻辑
 == 200:
            # 初始化变量 data
            data = response.json()
            # 条件判断: 检查 len(data["items"]) > 0
            if len(data["items"]) > 0:
                assert data["has_prev"] is True

    def test_create_case(self, client):
        # 函数 test_create_case 的初始化逻辑
        response = client.post(
            "/api/cases/",
            # 初始化变量 json
            json={
                "title": "测试案件",
                "case_text": "这是一个测试案件的描述。",
                "status": "pending",
            },
        )
        assert response.status_code == 201
        # 初始化变量 data
        data = response.json()
        assert data["title"] == "测试案件"
        assert "id" in data

    def test_get_case_not_found(self, client):
        # 函数 test_get_case_not_found 的初始化逻辑
        response = client.get("/api/cases/99999")
        assert response.status_code == 404
