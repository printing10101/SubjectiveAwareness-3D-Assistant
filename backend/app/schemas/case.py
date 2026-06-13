"""案件相关的 Pydantic 数据验证模型.

定义案件创建、更新和响应的数据结构及字段校验规则。
"""

import math
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, computed_field, field_serializer, field_validator

from app.config import AnalysisConfig
from app.models.case import CaseStatus
from app.utils.encryption import mask_sensitive_info


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """泛型分页响应模型.

    标准化所有分页查询的响应格式，包含当前页数据、总数统计
    及导航辅助属性（total_pages、has_next、has_prev）。

    Attributes:
        items: 当前页数据列表
        total: 符合条件的记录总数
        page: 当前页码（从1开始）
        page_size: 每页记录数
        total_pages: 总页数（派生属性）
        has_next: 是否有下一页（派生属性）
        has_prev: 是否有上一页（派生属性）
    """

    items: list[T]
    total: int
    page: int
    page_size: int

    @computed_field
    @property
    def total_pages(self) -> int:
        """计算总页数，至少为1."""
        return max(1, math.ceil(self.total / self.page_size))

    @computed_field
    @property
    def has_next(self) -> bool:
        """当前页之后是否还有数据."""
        return self.page < self.total_pages

    @computed_field
    @property
    def has_prev(self) -> bool:
        """当前页之前是否还有数据."""
        return self.page > 1


class CaseBase(BaseModel):
    """案件基础模型."""

    # 启用 use_enum_values + validate_default，让 case.status 比较可直接与字符串进行，
    # 且默认值 CaseStatus.pending 也会被序列化为字符串。
    model_config = ConfigDict(use_enum_values=True, validate_default=True)

    title: str
    description: str | None = None
    case_text: str
    status: CaseStatus | None = CaseStatus.pending


class CaseCreate(CaseBase):
    """创建案件请求模型，包含字段级验证."""

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """验证案件标题.

        Args:
            v: 原始标题字符串

        Returns:
            str: 去除首尾空格后的标题

        Raises:
            ValueError: 标题为空或超过最大长度
        """
        if not v or not v.strip():
            msg = "案件名称不能为空"
            raise ValueError(msg)
        if len(v.strip()) > AnalysisConfig.MAX_TITLE_LENGTH:
            msg = f"案件名称不能超过{AnalysisConfig.MAX_TITLE_LENGTH}个字符"
            raise ValueError(msg)
        return v.strip()

    @field_validator("case_text")
    @classmethod
    def validate_case_text(cls, v: str) -> str:
        """验证案件事实文本.

        Args:
            v: 原始事实文本

        Returns:
            str: 去除首尾空格后的文本

        Raises:
            ValueError: 文本为空或少于最小长度
        """
        if not v or not v.strip():
            msg = "事实文本不能为空"
            raise ValueError(msg)
        if len(v.strip()) < AnalysisConfig.MIN_CASE_LENGTH:
            msg = f"事实文本不能少于{AnalysisConfig.MIN_CASE_LENGTH}个字符"
            raise ValueError(msg)
        return v.strip()


class CaseUpdate(BaseModel):
    """更新案件请求模型，所有字段可选."""

    # 启用 use_enum_values + validate_default，让 status 以字符串形式存储，
    # 与 CaseCreate 保持一致，避免字符串断言失败。
    model_config = ConfigDict(use_enum_values=True, validate_default=True)

    title: str | None = None
    description: str | None = None
    case_text: str | None = None
    status: CaseStatus | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """验证案件标题（更新时可选）."""
        if v is not None:
            if not v.strip():
                msg = "案件名称不能为空"
                raise ValueError(msg)
            if len(v.strip()) > AnalysisConfig.MAX_TITLE_LENGTH:
                msg = f"案件名称不能超过{AnalysisConfig.MAX_TITLE_LENGTH}个字符"
                raise ValueError(msg)
        return v.strip() if v else v

    @field_validator("case_text")
    @classmethod
    def validate_case_text(cls, v: str | None) -> str | None:
        """验证案件事实文本（更新时可选）."""
        if v is not None:
            if not v.strip():
                msg = "事实文本不能为空"
                raise ValueError(msg)
            if len(v.strip()) < AnalysisConfig.MIN_CASE_LENGTH:
                msg = f"事实文本不能少于{AnalysisConfig.MIN_CASE_LENGTH}个字符"
                raise ValueError(msg)
        return v.strip() if v else v


class CaseResponse(BaseModel):
    """案件响应模型（case_text 自动脱敏）."""

    id: int
    title: str
    description: str | None = None
    case_text: str
    status: str
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("case_text")
    def mask_case_text(self, value: str) -> str:
        """序列化时自动脱敏案件事实文本."""
        return mask_sensitive_info(value)

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
