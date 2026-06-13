"""案件路由模块.

提供案件的 CRUD RESTful API 端点。
所有数据库操作均使用异步 API。
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_async_db_session
from app.models.case import Case, CaseStatus
from app.models.user import User
from app.schemas.case import (
    CaseCreate,
    CaseResponse,
    CaseUpdate,
    PaginatedResponse,
)
from app.services.case_service import (
    create_case,
    delete_case,
    get_case,
    get_cases,
    update_case,
)
from app.utils.auth import optional_current_user_dep


router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("/", response_model=PaginatedResponse[CaseResponse])
async def list_cases(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    status_filter: CaseStatus | None = Query(  # noqa: B008
        None, alias="status"
    ),
) -> PaginatedResponse[CaseResponse]:
    """获取案件列表（分页+排序）.

    Args:
        page: 页码（从1开始）
        page_size: 每页条数
        sort_by: 排序字段名
        sort_order: 排序方向
        status_filter: 状态筛选条件

    Returns:
        PaginatedResponse[CaseResponse]: 分页响应，包含
            items、total、total_pages、has_next、has_prev
    """
    async with get_async_db_session() as db:
        return await get_cases(  # type: ignore[return-value]
            db,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            status_filter=status_filter,
        )


@router.get("/{case_id}", response_model=CaseResponse)
async def read_case(
    case_id: int,
) -> CaseResponse:
    """获取单个案件详情.

    Args:
        case_id: 案件 ID

    Returns:
        CaseResponse: 案件详情

    Raises:
        HTTPException 404: 案件不存在
    """
    async with get_async_db_session() as db:
        case: Case | None = await get_case(db, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="案件不存在")
        return case  # type: ignore[return-value]


@router.post(
    "/",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_case(
    case_data: CaseCreate,
    current_user: User | None = optional_current_user_dep,
) -> CaseResponse:
    """创建新案件.

    Args:
        case_data: 案件创建数据
        current_user: 当前用户（可选）

    Returns:
        CaseResponse: 新创建的案件
    """
    async with get_async_db_session() as db:
        return (
            await create_case(db, case_data, user=current_user)
        )  # type: ignore[return-value]


@router.put("/{case_id}", response_model=CaseResponse)
async def update_existing_case(
    case_id: int,
    case_data: CaseUpdate,
    current_user: User | None = optional_current_user_dep,
) -> CaseResponse:
    """更新案件信息.

    Args:
        case_id: 案件 ID
        case_data: 更新数据
        current_user: 当前用户

    Returns:
        CaseResponse: 更新后的案件
    """
    async with get_async_db_session() as db:
        return (
            await update_case(
                db, case_id, case_data, user=current_user
            )
        )  # type: ignore[return-value]


@router.delete("/{case_id}")
async def delete_existing_case(
    case_id: int,
    current_user: User | None = optional_current_user_dep,
) -> bool:
    """删除案件.

    Args:
        case_id: 案件 ID
        current_user: 当前用户

    Returns:
        bool: 删除成功返回 True
    """
    async with get_async_db_session() as db:
        return await delete_case(db, case_id, user=current_user)
