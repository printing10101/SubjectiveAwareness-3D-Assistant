"""通用服务基础模块.

提供服务模块的通用能力，包括分页、排序、验证等辅助函数。
所有服务可复用这些基础功能，减少重复代码。
"""

from __future__ import annotations

import logging
from math import ceil
from typing import Any, Generic, TypeVar

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

T = TypeVar("T", bound=DeclarativeBase)


# 分页相关常量
MAX_PAGE_SIZE: int = 100
DEFAULT_PAGE_SIZE: int = 20
MIN_PAGE: int = 1


class BaseService(Generic[T]):
    """服务基类，提供通用能力"""

    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)

    async def health_check(self) -> dict:
        """健康检查"""
        return {"status": "healthy", "service": self.__class__.__name__}

    def validate_input(self, data: dict, schema: type) -> bool:
        """输入验证"""
        try:
            schema(**data)
            return True
        except Exception as e:
            self.logger.warning(f"Input validation failed: {e}")
            return False

    async def get_by_id(self, model: type[T], id: int) -> T | None:
        """根据ID获取记录"""
        if not self.db:
            raise ValueError("Database session not provided")
        result = await self.db.execute(
            select(model).where(model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        model: type[T],
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[T], int]:
        """分页获取所有记录"""
        if not self.db:
            raise ValueError("Database session not provided")
        
        validate_pagination_params(page, page_size)
        
        total = await get_paginated_count(self.db, model)
        items = await get_paginated_items(
            self.db, model, page, page_size
        )
        
        return items, total

    async def create(self, instance: T) -> T:
        """创建记录"""
        if not self.db:
            raise ValueError("Database session not provided")
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def update(self, instance: T) -> T:
        """更新记录"""
        if not self.db:
            raise ValueError("Database session not provided")
        await self.db.flush()
        return instance

    async def delete(self, instance: T) -> None:
        """删除记录"""
        if not self.db:
            raise ValueError("Database session not provided")
        await self.db.delete(instance)
        await self.db.flush()


def validate_pagination_params(
    page: int,
    page_size: int,
    max_page_size: int = MAX_PAGE_SIZE,
) -> None:
    """验证分页参数.

    Args:
        page: 页码（从1开始）
        page_size: 每页条数
        max_page_size: 最大每页条数

    Raises:
        HTTPException 422: 参数无效
    """
    if page < MIN_PAGE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"页码必须大于等于{MIN_PAGE}",
        )
    if page_size < 1 or page_size > max_page_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"每页条数必须在1到{max_page_size}之间",
        )


def validate_sort_params(
    sort_by: str,
    sort_order: str,
    allowed_fields: set[str] | frozenset[str],
) -> None:
    """验证排序参数.

    Args:
        sort_by: 排序字段名
        sort_order: 排序方向（asc/desc）
        allowed_fields: 允许的排序字段集合

    Raises:
        HTTPException 422: 参数无效
    """
    valid_sort_orders = {"asc", "desc"}
    
    if sort_by not in allowed_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的排序字段'{sort_by}'，允许的字段: {sorted(allowed_fields)}",
        )
    if sort_order not in valid_sort_orders:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的排序方向'{sort_order}'，仅支持'asc'和'desc'",
        )


def calculate_offset(page: int, page_size: int) -> int:
    """计算分页偏移量.

    Args:
        page: 页码（从1开始）
        page_size: 每页条数

    Returns:
        int: 偏移量
    """
    return (page - 1) * page_size


def calculate_total_pages(total: int, page_size: int) -> int:
    """计算总页数.

    Args:
        total: 总记录数
        page_size: 每页条数

    Returns:
        int: 总页数
    """
    if total <= 0:
        return 0
    return max(1, ceil(total / page_size))


async def get_paginated_count(
    db: AsyncSession,
    model: type[T],
) -> int:
    """获取记录总数.

    Args:
        db: 异步数据库会话
        model: SQLAlchemy 模型类

    Returns:
        int: 记录总数
    """
    result = await db.execute(select(func.count(model.id)))
    return result.scalar() or 0


async def get_paginated_items(
    db: AsyncSession,
    model: type[T],
    page: int,
    page_size: int,
    order_by: Any = None,
) -> list[T]:
    """获取分页记录列表.

    Args:
        db: 异步数据库会话
        model: SQLAlchemy 模型类
        page: 页码（从1开始）
        page_size: 每页条数
        order_by: 排序表达式，默认为 None

    Returns:
        list[T]: 记录列表
    """
    query = select(model)
    
    if order_by is not None:
        query = query.order_by(order_by)
    else:
        # 默认按创建时间倒序
        if hasattr(model, "created_at"):
            query = query.order_by(model.created_at.desc())
    
    offset = calculate_offset(page, page_size)
    result = await db.execute(
        query.offset(offset).limit(page_size)
    )
    
    return list(result.scalars().all())


def build_sort_expression(
    model: type[T],
    sort_by: str,
    sort_order: str,
) -> Any:
    """构建排序表达式.

    Args:
        model: SQLAlchemy 模型类
        sort_by: 已验证的排序字段名
        sort_order: 已验证的排序方向（asc/desc）

    Returns:
        排序表达式
    """
    column = getattr(model, sort_by)
    return column.desc() if sort_order == "desc" else column.asc()


def log_service_call(service_name: str, **kwargs: Any) -> None:
    """记录服务调用日志.

    Args:
        service_name: 服务名称
        **kwargs: 调用参数
    """
    logger.debug(f"调用服务: {service_name}", **kwargs)


def handle_service_error(
    error: Exception,
    service_name: str,
    detail: str | None = None,
) -> None:
    """处理服务错误并记录日志.

    Args:
        error: 异常实例
        service_name: 服务名称
        detail: 错误详情
    """
    error_msg = str(error)
    logger.error(
        f"服务错误: {service_name}",
        error=error_msg,
        detail=detail or error_msg,
    )
    raise
