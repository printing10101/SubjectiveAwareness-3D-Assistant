"""知识库路由模块.

提供知识条目、标签、关联关系及法律规则的 CRUD RESTful API 端点。
所有数据库操作均使用异步 API。
"""

# 导入模块: from typing
from typing import Any

# 导入模块: from fastapi
from fastapi import APIRouter, Depends, HTTPException, Query, status

# 导入模块: from app.database
from app.database import get_async_db_session
# 导入模块: from app.models.knowledge_entry
from app.models.knowledge_entry import (
    EntryCategory,
    EntryStatus,
    KnowledgeEntry,
)
# 导入模块: from app.models.user
from app.models.user import User, UserRole
# 导入模块: from app.schemas.case
from app.schemas.case import PaginatedResponse
# 导入模块: from app.schemas.knowledge
from app.schemas.knowledge import (
    EntryRelationCreate,
    EntryRelationResponse,
    KnowledgeEntryCreate,
    KnowledgeEntryResponse,
    KnowledgeEntryUpdate,
    KnowledgeTagCreate,
    KnowledgeTagResponse,
    LegalRuleCreate,
    LegalRuleUpdate,
)
# 导入模块: from app.services.knowledge_graph
from app.services.knowledge_graph import (
    create_legal_rule,
    delete_legal_rule,
    get_legal_rule,
    get_legal_rules,
    update_legal_rule,
)
# 导入模块: from app.services.knowledge_graph_service
from app.services.knowledge_graph_service import (
    get_graph_data,
    get_node_neighbors,
    get_shortest_path,
)
# 导入模块: from app.services.knowledge_service
from app.services.knowledge_service import (
    add_entry_relation,
    add_entry_tag,
    create_entry,
    create_tag,
    delete_entry,
    get_all_tags,
    get_entries_paginated,
    get_entry,
    get_entry_relations,
    get_entry_tags,
    remove_entry_tag,
    update_entry,
)
# 导入模块: from app.utils.auth
from app.utils.auth import get_current_user, optional_current_user_dep


# 初始化变量 router
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

# 管理员权限依赖
admin_required = Depends(
    lambda u: u
    # 条件判断：处理业务逻辑
    if u and u.role == "admin"
    else HTTPException(403, "需要管理员权限"),
)

# ---------------------------------------------------------------------------
# 知识条目 CRUD 端点
# ---------------------------------------------------------------------------


# 应用装饰器: router.get
@router.get(
    "/entries",
    # 初始化变量 response_model
    response_model=PaginatedResponse[KnowledgeEntryResponse],
)
async def list_entries(  # noqa: PLR0913
    # 函数 list_entries 的初始化逻辑
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    category: EntryCategory | None = Query(  # noqa: B008
        None, description="按分类过滤",
    ),
    tag_id: int | None = Query(None, description="按标签ID过滤"),
    status_filter: EntryStatus | None = Query(  # noqa: B008
        None, alias="status", description="按状态过滤"
    ),
) -> PaginatedResponse[KnowledgeEntryResponse]:
    """获取知识条目列表（分页+排序+过滤）.

    Args:
        page: 页码（从1开始）
        page_size: 每页条数
        sort_by: 排序字段名
        sort_order: 排序方向
        category: 按分类过滤
        tag_id: 按标签ID过滤
        status_filter: 按状态过滤

    Returns:
        PaginatedResponse[KnowledgeEntryResponse]: 分页响应
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_entries_paginated(  # type: ignore[return-value]
            db,
            # 初始化变量 page
            page=page,
            # 初始化变量 page_size
            page_size=page_size,
            # 初始化变量 sort_by
            sort_by=sort_by,
            # 初始化变量 sort_order
            sort_order=sort_order,
            # 初始化变量 category_filter
            category_filter=category,
            # 初始化变量 tag_filter
            tag_filter=tag_id,
            # 初始化变量 status_filter
            status_filter=status_filter,
        )


# 应用装饰器: router.get
@router.get("/entries/{entry_id}", response_model=KnowledgeEntryResponse)
async def read_entry(
    # 函数 read_entry 的初始化逻辑
    entry_id: int,
) -> KnowledgeEntryResponse:
    """获取知识条目详情.

    Args:
        entry_id: 知识条目 ID

    Returns:
        KnowledgeEntryResponse: 条目详情

    Raises:
        HTTPException 404: 条目不存在
    """
    async with get_async_db_session() as db:
        # 异步等待操作完成
        entry: KnowledgeEntry | None = await get_en        # 条件判断：处理业务逻辑
try(db, entry_id)
        # 条件判断: 检查 not entry
        if not entry:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=404, detail="知识条目不存在")
        # 返回处理结果
        return entry  # type: ignore[return-value]


# 应用装饰器: router.post
@router.post(
    "/entries",
    # 初始化变量 response_model
    response_model=KnowledgeEntryResponse,
    # 初始化变量 status_code
    status_code=status.HTTP_201_CREATED,
)
async def create_new_entry(
    # 函数 create_new_entry 的初始化逻辑
    entry_data: KnowledgeEntryCreate,
    current_user: User | None = optional_current_user_dep,
) -> KnowledgeEntryResponse:
    """创建新知识条目.

    Args:
        entry_data: 知识条目创建数据
        current_user: 当前用户

    Returns:
        KnowledgeEntryResponse: 新创建的知识条目
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await create_entry(  # type: ignore[return-value]
            db, entry_data, user=current_user
        )


# 应用装饰器: router.put
@router.put("/entries/{entry_id}", response_model=KnowledgeEntryResponse)
async def update_existing_entry(
    # 函数 update_existing_entry 的初始化逻辑
    entry_id: int,
    entry_data: KnowledgeEntryUpdate,
    current_user: User | None = optional_current_user_dep,
) -> KnowledgeEntryResponse:
    """更新知识条目.

    Args:
        entry_id: 条目 ID
        entry_data: 更新数据
        current_user: 当前用户

    Returns:
        KnowledgeEntryResponse: 更新后的知识条目
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await update_entry(  # type: ignore[return-value]
            db, entry_id, entry_data, user=current_user
        )


# 应用装饰器: router.delete
@router.delete("/entries/{entry_id}")
async def delete_existing_entry(
    # 函数 delete_existing_entry 的初始化逻辑
    entry_id: int,
    current_user: User | None = optional_current_user_dep,
) -> bool:
    """删除知识条目.

    Args:
        entry_id: 条目 ID
        current_user: 当前用户

    Returns:
        bool: 删除成功返回 True
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await delete_entry(db, entry_id, user=current_user)


# ---------------------------------------------------------------------------
# 条目关联关系端点
# ---------------------------------------------------------------------------


# 应用装饰器: router.get
@router.get(
    "/entries/{entry_id}/relations",
    # 初始化变量 response_model
    response_model=list[EntryRelationResponse],
)
async def list_entry_relations(
    # 函数 list_entry_relations 的初始化逻辑
    entry_id: int,
) -> list[EntryRelationResponse]:
    """获取指定知识条目的所有关联关系.

    Args:
        entry_id: 知识条目 ID

    Returns:
        list[EntryRelationResponse]: 关联关系列表
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_entry_relations(
            db, entry_id,
        )  # type: ignore[return-value]


# 应用装饰器: router.post
@router.post(
    "/entries/{entry_id}/relations",
    # 初始化变量 response_model
    response_model=EntryRelationResponse,
    # 初始化变量 status_code
    status_code=status.HTTP_201_CREATED,
)
async def create_entry_relation(
    # 函数 create_entry_relation 的初始化逻辑
    entry_id: int,
    relation_data: EntryRelationCreate,
    current_user: User = Depends(get_current_user),  # noqa: B008, ARG001
) -> EntryRelationResponse:
    """为指定知识条目添加关联关系（需要登录）.

    Args:
        entry_id: 源条目 ID
        relation_data: 关联关系数据
        current_user: 当前用户（必须登录）

    Returns:
        EntryRelationResponse: 新创建的关联关系
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await add_entry_relation(  # type: ignore[return-value]
            db, entry_id, relation_data
        )


# ---------------------------------------------------------------------------
# 条目标签端点
# ---------------------------------------------------------------------------


# 应用装饰器: router.get
@router.get(
    "/entries/{entry_id}/tags",
    # 初始化变量 response_model
    response_model=list[KnowledgeTagResponse],
)
async def list_entry_tags(
    # 函数 list_entry_tags 的初始化逻辑
    entry_id: int,
) -> list[KnowledgeTagResponse]:
    """获取指定知识条目的所有标签.

    Args:
        entry_id: 知识条目 ID

    Returns:
        list[KnowledgeTagResponse]: 标签列表
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_entry_tags(db, entry_id)  # type: ignore[return-value]


# 应用装饰器: router.post
@router.post(
    "/entries/{entry_id}/tags",
    # 初始化变量 response_model
    response_model=KnowledgeTagResponse,
    # 初始化变量 status_code
    status_code=status.HTTP_201_CREATED,
)
async def add_tag_to_entry(
    # 函数 add_tag_to_entry 的初始化逻辑
    entry_id: int,
    tag_data: dict[str, int],
) -> KnowledgeTagResponse:
    """为指定知识条目添加标签.

    Args:
        entry_id: 知识条目 ID
        tag_data: 包含 tag_id 的请求体 {"tag_id": 1}

    Returns:
        KnowledgeTagResponse: 添加的标签
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await add_entry_tag(  # type: ignore[return-value]
            db, entry_id, tag_data["tag_id"]
        )


# 应用装饰器: router.delete
@router.delete("/entries/{entry_id}/tags/{tag_id}")
async def remove_tag_from_entry(
    # 函数 remove_tag_from_entry 的初始化逻辑
    entry_id: int,
    tag_id: int,
) -> bool:
    """从指定知识条目中移除特定标签.

    Args:
        entry_id: 知识条目 ID
        tag_id: 标签 ID

    Returns:
        bool: 移除成功返回 True
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await remove_entry_tag(db, entry_id, tag_id)


# ---------------------------------------------------------------------------
# 标签管理端点
# ---------------------------------------------------------------------------


# 应用装饰器: router.get
@router.get("/tags", response_model=list[KnowledgeTagResponse])
async def list_tags() -> list[KnowledgeTagResponse]:
    """获取系统中所有标签列表.

    Returns:
        list[KnowledgeTagResponse]: 标签列表
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_all_tags(db)  # type: ignore[return-value]


# 应用装饰器: router.post
@router.post(
    "/tags",
    # 初始化变量 response_model
    response_model=KnowledgeTagResponse,
    # 初始化变量 status_code
    status_code=status.HTTP_201_CREATED,
)
async def create_new_tag(
    # 函数 create_new_tag 的初始化逻辑
    tag_data: KnowledgeTagCreate,
    current_user: User | None = optional_current_user_dep,
) -> KnowledgeTagResponse:
    """创建新标签.

    Args:
        tag_data: 标签创建数据
        current_user: 当前用户

    Returns:
        KnowledgeTagResponse: 新创建的标签
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await create_tag(  # type: ignore[return-value]
            db, tag_data, user=current_user
        )


# ---------------------------------------------------------------------------
# 法律规则端点（需要管理员权限）
# ---------------------------------------------------------------------------


# 应用装饰器: router.get
@router.get("/rules")
async def list_rules(
    # 函数 list_rules 的初始化逻辑
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(100, ge=1, le=100, description="每页数量，最大100"),
) -> list[dict[str, Any]]:
    """获取法律规则列表（公开读取）.

    Args:
        skip: 分页偏移量（必须 >= 0）
        limit: 每页数量（1-100）

    Returns:
        list[dict[str, Any]]: 法律规则列表
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_legal_rules(
            db, skip=skip, limit=limit,
        )  # type: ignore[return-value]


# 应用装饰器: router.get
@router.get("/rules/{rule_id}")
async def read_rule(
    # 函数 read_rule 的初始化逻辑
    rule_id: int,
) -> dict[str, Any]:
    """获取单个法律规则（公开读取）.

    Args:
        rule_id: 规则 ID

    Returns:
        dict[str, Any]: 规则详情

    Raises:
        HTTPException 404: 规则不存在
    """
    async with get_async_db_session() as db:
        r        # 条件判断：处理业务逻辑
ule = await get_legal_rule(db, rule_id)
        # 条件判断: 检查 not rule
        if not rule:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=404, detail="规则不存在")
        # 返回处理结果
        return rule  # type: ignore[return-value]


# 应用装饰器: router.post
@router.post("/rules", dependencies=[Depends(get_current_user)])
async def create_rule(
    # 函数 create_rule 的初始化逻辑
    rule_data: LegalRuleCreate,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    """创建新法律规则（需要管理员权限）.

    Args:
        rule_data: 规则数据（使用 Pydantic schema 验证）
        current_user: 当前用户（必须是管理员）

    Returns:
        dict[str, Any]    # 条件判断：处理业务逻辑
: 新创建的规则

    Raises:
        HTTPException 403: 非管理员
    """
    # 条件判断: 检查 current_user.role != UserRole.admin
    if current_user.role != UserRole.admin:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_403_FORBIDDEN,
            # 初始化变量 detail
            detail="只有管理员可以创建法律规则"
        )
    async with get_async_db_session() as db:
        # 返回处理结果
        return await create_legal_rule(
            db, rule_data.model_dump(),
        )  # type: ignore[return-value]


# 应用装饰器: router.put
@router.put("/rules/{rule_id}")
async def update_existing_rule(
    # 函数 update_existing_rule 的初始化逻辑
    rule_id: int,
    rule_data: LegalRuleUpdate,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    """更新法律规则（需要管理员权限）.

    Args:
        rule_id: 规则 ID
        rule_data: 更新数据（使用 Pydantic schema 验证）
        current_user: 当前用户（必须是管理员）

    Returns:
        dict[str, Any]: 更新后的规则

    R    # 条件判断：处理业务逻辑
aises:
        HTTPException 403: 非管理员
        HTTPException 404: 规则不存在
    """
    # 条件判断: 检查 current_user.role != "admin"
    if current_user.role != "admin":
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_403_FORBIDDEN,
            # 初始化变量 detail
            detail="只有管理员可以修改法律规则"
        )
    async with get_async_db_session() as db:
        # 返回处理结果
        return await update_legal_rule(
            db, rule_id, rule_data.model_dump(exclude_unset=True),
        )  # type: ignore[return-value]


# 应用装饰器: router.delete
@router.delete("/rules/{rule_id}")
async def delete_existing_rule(
    # 函数 delete_existing_rule 的初始化逻辑
    rule_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> bool:
    """删除法律规则（需要管理员权限）.

    Args:
        rule_id: 规则 ID
        current_user: 当前用户（必须是    # 条件判断：处理业务逻辑
管理员）

    Returns:
        bool: 删除成功返回 True

    Raises:
        HTTPException 403: 非管理员
    """
    # 条件判断: 检查 current_user.role != UserRole.admin
    if current_user.role != UserRole.admin:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_403_FORBIDDEN,
            # 初始化变量 detail
            detail="只有管理员可以更新法律规则"
        )
    async with get_async_db_session() as db:
        # 返回处理结果
        return await delete_legal_rule(db, rule_id)


# ---------------------------------------------------------------------------
# 知识图谱端点
# ---------------------------------------------------------------------------


# 应用装饰器: router.get
@router.get("/graph")
async def get_knowledge_graph(
    # 函数 get_knowledge_graph 的初始化逻辑
    category: list[str] | None = Query(None, description="分类筛选列表"),  # noqa: B008
    tag: list[str] | None = Query(None, description="标签筛选列表"),  # noqa: B008
    relation_type: list[str] | None = Query(  # noqa: B008
        None, alias="relationType", description="关系类型筛选列表",
    ),
    search: str | None = Query(None, description="标题搜索关键词"),
    entry_ids: list[int] | None = Query(  # noqa: B008
        None, alias="entryIds", description="指定条目ID列表",
    ),
) -> dict[str, Any]:
    """获取知识图谱数据.

    支持分类、标签、关系类型等多条件组合筛选，
    返回包含节点完整属性与边关系信息的图谱数据。

    Args:
        category: 分类筛选列表
        tag: 标签名称筛选列表
        relation_type: 关系类型筛选列表
        search: 标题搜索关键词
        entry_ids: 指定条目ID列表（迷你模式使用）

    Returns:
        dict: 包含 nodes 和 edges 的图谱数据
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_graph_data(
            db,
            # 初始化变量 category_filters
            category_filters=category,
            # 初始化变量 tag_filters
            tag_filters=tag,
            # 初始化变量 relation_type_filters
            relation_type_filters=relation_type,
            # 初始化变量 search_query
            search_query=search,
            # 初始化变量 entry_ids
            entry_ids=entry_ids,
        )


# 应用装饰器: router.get
@router.get("/graph/neighbors/{entry_id}")
async def get_entry_neighbors(
    # 函数 get_entry_neighbors 的初始化逻辑
    entry_id: int,
    depth: int = Query(1, ge=1, le=3, description="邻居获取深度（1-3）"),
) -> dict[str, Any]:
    """获取指定节点的直接邻居节点及关联边.

    使用BFS算法按深度层级获取邻居节点。

    Args:
        entry_id: 中心节点条目ID
        depth: 邻居获取深度

    Returns:
        dict: 包含 nodes 和 edges 的邻居图谱数据
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_node_neighbors(db, entry_id, depth)


# 应用装饰器: router.get
@router.get("/graph/shortest-path")
async def get_graph_shortest_path(
    # 函数 get_graph_shortest_path 的初始化逻辑
    source_id: int = Query(..., alias="sourceId", description="起始节点ID"),
    target_id: int = Query(..., alias="targetId", description="目标节点ID"),
) -> dict[str, Any]:
    """计算并返回两个节点间的最短路径.

    Args:
        source_id: 起始节点ID
        target_id: 目标节点ID

    Returns:
        dict: 包含 path_nodes, path_edges 和 path_length 的最短路径数据
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await get_shortest_path(db, source_id, target_id)
