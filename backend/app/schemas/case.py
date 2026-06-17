"""案件相关的 Pydantic 数据验证模型.

定义案件创建、更新和响应的数据结构及字段校验规则。
"""

# 导入模块: math
import math
# 导入模块: from datetime
from datetime import datetime
# 导入模块: from typing
from typing import Generic, TypeVar

# 导入模块: from pydantic
from pydantic import BaseModel, ConfigDict, computed_field, field_serializer, field_validator

# 导入模块: from app.config
from app.config import AnalysisConfig
# 导入模块: from app.models.case
from app.models.case import CaseStatus
# 导入模块: from app.utils.encryption
from app.utils.encryption import mask_sensitive_info


T = TypeVar("T")


# 定义 PaginatedResponse 类
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

    # 应用装饰器: computed_field
    @computed_field
    # 应用装饰器: property
    @property
    def total_pages(self) -> int:
        """计算总页数，至少为1."""
        # 返回处理结果
        return max(1, math.ceil(self.total / self.page_size))

    # 应用装饰器: computed_field
    @computed_field
    # 应用装饰器: property
    @property
    def has_next(self) -> bool:
        """当前页之后是否还有数据."""
        # 返回处理结果
        return self.page < self.total_pages

    # 应用装饰器: computed_field
    @computed_field
    # 应用装饰器: property
    @property
    def has_prev(self) -> bool:
        """当前页之前是否还有数据."""
        # 返回处理结果
        return self.page > 1


# 定义 CaseBase 类
class CaseBase(BaseModel):
    """案件基础模型."""

    # 启用 use_enum_values + validate_default，让 case.status 比较可直接与字符串进行，
    # 且默认值 CaseStatus.pending 也会被序列化为字符串。
    model_config = ConfigDict(use_enum_values=True, validate_default=True)

    title: str
    description: str | None = None
    case_text: str
    status: CaseStatus | None = CaseStatus.pending


# 定义 CaseCreate 类
class CaseCreate(CaseBase):
    """创建案件请求模型，包含字段级验证."""

    # 应用装饰器: field_validator
    @field_validator("title")
    # 应用装饰器: classmethod
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
        # 条件判断：处理业务逻辑
        if not v or not v.strip():
            msg = "案件名称不能为空"
                    # 条件判断：处理业务逻辑
raise ValueError(msg)
        # 条件判断: 检查 len(v.strip()) > AnalysisConfig.MAX_TITL
        if len(v.strip()) > AnalysisConfig.MAX_TITLE_LENGTH:
            msg = f"案件名称不能超过{AnalysisConfig.MAX_TITLE_LENGTH}个字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return v.strip()

    # 应用装饰器: field_validator
    @field_validator("case_text")
    # 应用装饰器: classmethod
    @classmethod
    def validate_case_text(cls, v: str) -> str:
        """验证案件事实文本.

        Args:
            v: 原始事实文本

        Returns:
            str: 去除首尾空格后的文本

        Raises:
            # 条件判断：处理业务逻辑
        ValueError: 文本为空或少于最小长度
        """
        # 条件判断: 检查 not v or not v.strip(        # 条件判断：处理业务
        if not v or not v.strip(        # 条件判断：处理业务逻辑
):
            msg = "事实文本不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 条件判断: 检查 len(v.strip()) < AnalysisConfig.MIN_CASE
        if len(v.strip()) < AnalysisConfig.MIN_CASE_LENGTH:
            msg = f"事实文本不能少于{AnalysisConfig.MIN_CASE_LENGTH}个字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return v.strip()


# 定义 CaseUpdate 类
class CaseUpdate(BaseModel):
    """更新案件请求模型，所有字段可选."""

    # 启用 use_enum_values + validate_default，让 status 以字符串形式存储，
    # 与 CaseCreate 保持一致，避免字符串断言失败。
    model_config = ConfigDict(use_enum_values=True, validate_default=True)

    title: str | None = None
    description: str | None = None
    case_text: str | None = None
    status: CaseStatus | None = None

    # 应用装饰器: field_validator
    @field_validator("title")
    # 应用装饰器: classmethod
    @classmethod
    def validate_title(cl            # 条件判断：处理业务逻辑
        # 函数 validate_title 的初始化逻辑
s, v: str | None) -> str | None:
        """验证案件标题（更新时可选）."""
        # 条件判断: 检查 v             # 条件判断：处理业务逻辑
        if v             # 条件判断：处理业务逻辑
is not None:
            # 条件判断: 检查 not v.strip()
            if not v.strip():
                msg = "案件名称不能为空"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 条件判断: 检查 len(v.strip()) > AnalysisConfig.MAX_TITL
            if len(v.strip()) > AnalysisConfig.MAX_TITLE_LENGTH:
                msg = f"案件名称不能超过{AnalysisConfig.MAX_TITLE_LENGTH}个字符"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
        # 返回处理结果
        return v.strip() if v else v

            # 条件判断：处理业务逻辑
@fie            # 条件判断：处理业务逻辑
ld_validator("case_text")
    # 应用装饰器: classmethod
    @classmethod
    def validate_case_text(cls,             # 条件判断：处理业务逻辑
        # 函数 validate_case_text 的初始化逻辑
v: str | None) -> str | None:
        """验证案件事实文本（更新时可选）."""
        # 条件判断: 检查 v is not None
        if v is not None:
            # 条件判断: 检查 not v.strip()
            if not v.strip():
                msg = "事实文本不能为空"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 条件判断: 检查 len(v.strip()) < AnalysisConfig.MIN_CASE
            if len(v.strip()) < AnalysisConfig.MIN_CASE_LENGTH:
                msg = f"事实文本不能少于{AnalysisConfig.MIN_CASE_LENGTH}个字符"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
        # 返回处理结果
        return v.strip() if v else v


# 定义 CaseResponse 类
class CaseResponse(BaseModel):
    """案件响应模型（case_text 自动脱敏）."""

    id: int
    title: str
    description: str | None = None
    case_text: str | None = None
    stat        # 条件判断：处理业务逻辑
us: str
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    # 应用装饰器: field_serializer
    @field_serializer("case_text")
    def mask_case_text(self, value: str | None) -> str:
        """序列化时自动脱敏案件事实文本."""
        # 条件判断: 检查 value is None
        if value is None:
            # 返回处理结果
            return ""
        # 返回处理结果
        return mask_sensitive_info(value)

    # 定义 Config 类
    class Config:
        """Pydantic model configuration."""

        # 初始化变量 from_attributes
        from_attributes = True
