"""案件路由模块.

提供案件的 CRUD RESTful API 端点。
所有数据库操作均使用异步 API。
"""

# 导入模块: from fastapi
from fastapi import APIRouter, HTTPException, Query, status

# 导入模块: from app.database
from app.database import get_async_db_session
# 导入模块: from app.models.case
from app.models.case import Case, CaseStatus
# 导入模块: from app.models.user
from app.models.user import User
# 导入模块: from app.schemas.case
from app.schemas.case import (
    CaseCreate,
    CaseResponse,
    CaseUpdate,
    PaginatedResponse,
)
# 导入模块: from app.services.case_service
from app.services.case_service import (
    create_case,
    delete_case,
    get_case,
    get_cases,
    update_case,
)
# 导入模块: from app.utils.auth
from app.utils.auth import optional_current_user_dep


# 初始化变量 router
router = APIRouter(prefix="/api/cases", tags=["cases"])


# 应用装饰器: router.get
@router.get("/", response_model=PaginatedResponse[CaseResponse])
async def list_cases(
    # 函数 list_cases 的初始化逻辑
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
        # 返回处理结果
        return await get_cases(  # type: ignore[return-value]
            db,
            # 初始化变量 page
            page=page,
            # 初始化变量 page_size
            page_size=page_size,
            # 初始化变量 sort_by
            sort_by=sort_by,
            # 初始化变量 sort_order
            sort_order=sort_order,
            # 初始化变量 status_filter
            status_filter=status_filter,
        )


# 应用装饰器: router.get
@router.get("/{case_id}", response_model=CaseResponse)
async def read_case(
    # 函数 read_case 的初始化逻辑
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
        # 异步等待操作完成
        case: Case | None = await get_case(db, case_id)
        # 条件判断：处理业务逻辑
        if not case:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=404, detail="案件不存在")
        # 返回处理结果
        return case  # type: ignore[return-value]


# 应用装饰器: router.post
@router.post(
    "/",
    # 初始化变量 response_model
    response_model=CaseResponse,
    # 初始化变量 status_code
    status_code=status.HTTP_201_CREATED,
)
async def create_new_case(
    # 函数 create_new_case 的初始化逻辑
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
        # 返回处理结果
        return (
            # 异步等待操作完成
            await create_case(db, case_data, user=current_user)
        )  # type: ignore[return-value]


# 应用装饰器: router.put
@router.put("/{case_id}", response_model=CaseResponse)
async def update_existing_case(
    # 函数 update_existing_case 的初始化逻辑
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
        # 返回处理结果
        return (
            # 异步等待操作完成
            await update_case(
                db, case_id, case_data, user=current_user
            )
        )  # type: ignore[return-value]


# 应用装饰器: router.delete
@router.delete("/{case_id}")
async def delete_existing_case(
    # 函数 delete_existing_case 的初始化逻辑
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
        # 返回处理结果
        return await delete_case(db, case_id, user=current_user)
