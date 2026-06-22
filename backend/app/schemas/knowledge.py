"""知识库相关的 Pydantic 数据验证模型.

定义知识条目、标签、关联关系的创建、更新和响应的数据结构及字段校验规则。
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, computed_field, field_validator

from app.models.entry_relation import RelationType
from app.models.knowledge_entry import EntryCategory, EntryStatus, SourceType


_MAX_TITLE_LENGTH: int = 255
_MAX_CONTENT_MIN_LENGTH: int = 10
_MAX_TAG_NAME_LENGTH: int = 50
_MIN_TAG_NAME_LENGTH: int = 2
_MAX_SUMMARY_LENGTH: int = 500
_MAX_PAGE_SIZE: int = 100
_MAX_RULE_ID_LENGTH: int = 50
_MAX_RULE_NAME_LENGTH: int = 200
_INVALID_TITLE_PATTERN: re.Pattern = re.compile(r"[<>{}|\\^~\[\]`]")
_MALICIOUS_PATTERN: re.Pattern = re.compile(
    r"(<script[\s>]|javascript:|on\w+\s*=|\.\./|"
    r"\b(SELECT|DROP|DELETE|INSERT|UPDATE|ALTER|EXEC|UNION)\b)",
    re.IGNORECASE,
)


class KnowledgeEntryCreate(BaseModel):
    """创建知识条目请求模型，包含字段级验证.

    Attributes:
        title: 知识条目标题（3-255字符，不含特殊字符）
        content: 知识条目正文内容（至少10字符，不含恶意内容）
        category: 知识条目分类
        tags: 标签名称列表（每个标签2-50字符）
        source_type: 知识来源类型，默认 "manual"
    """

    title: str
    content: str
    category: EntryCategory
    tags: list[str] | None = None
    source_type: str = "manual"

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """验证知识条目标题.

        检查标题长度和特殊字符，确保符合业务规范。

        Args:
            v: 原始标题字符串

        Returns:
            str: 去除首尾空格后的标题

        Raises:
            ValueError: 标题长度不符合要求或包含特殊字符
        """
        if not v or not v.strip():
            msg = "知识条目标题不能为空"
            raise ValueError(msg)
        stripped = v.strip()
        if len(stripped) < _MIN_TAG_NAME_LENGTH + 1:
            msg = f"知识条目标题不能少于{_MIN_TAG_NAME_LENGTH + 1}个字符"
            raise ValueError(msg)
        if len(stripped) > _MAX_TITLE_LENGTH:
            msg = f"知识条目标题不能超过{_MAX_TITLE_LENGTH}个字符"
            raise ValueError(msg)
        if _INVALID_TITLE_PATTERN.search(stripped):
            msg = "知识条目标题包含不允许的特殊字符"
            raise ValueError(msg)
        return stripped

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """验证知识条目内容.

        检查内容长度和安全性，防止恶意内容注入。

        Args:
            v: 原始内容字符串

        Returns:
            str: 去除首尾空格后的内容

        Raises:
            ValueError: 内容长度不足或包含恶意代码
        """
        if not v or not v.strip():
            msg = "知识条目内容不能为空"
            raise ValueError(msg)
        stripped = v.strip()
        if len(stripped) < _MAX_CONTENT_MIN_LENGTH:
            msg = f"知识条目内容不能少于{_MAX_CONTENT_MIN_LENGTH}个字符"
            raise ValueError(msg)
        if _MALICIOUS_PATTERN.search(stripped):
            msg = "知识条目内容包含潜在安全风险，请检查后重试"
            raise ValueError(msg)
        return stripped

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """验证标签列表.

        Args:
            v: 标签名称列表

        Returns:
            list[str] | None: 去除首尾空格后的标签列表

        Raises:
            ValueError: 标签名称长度不符合要求
        """
        if v is None:
            return v
        result: list[str] = []
        for tag in v:
            tag_stripped = tag.strip()
            if len(tag_stripped) < _MIN_TAG_NAME_LENGTH:
                msg = f"标签名称不能少于{_MIN_TAG_NAME_LENGTH}个字符"
                raise ValueError(msg)
            if len(tag_stripped) > _MAX_TAG_NAME_LENGTH:
                msg = f"标签名称不能超过{_MAX_TAG_NAME_LENGTH}个字符"
                raise ValueError(msg)
            result.append(tag_stripped)
        return result

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        """验证来源类型."""
        allowed = {item.value for item in SourceType}
        if v not in allowed:
            msg = f"来源类型必须为以下之一: {', '.join(sorted(allowed))}"
            raise ValueError(msg)
        return v


class KnowledgeEntryUpdate(BaseModel):
    """更新知识条目请求模型，所有字段可选.

    Attributes:
        title: 知识条目标题（3-255字符，不含特殊字符）
        content: 知识条目正文内容（至少10字符，不含恶意内容）
        summary: 知识条目摘要（最多500字符）
        category: 知识条目分类
        status: 知识条目状态
        confidence: 信心评分（0.0-1.0）
        tags: 标签名称列表（每个标签2-50字符）
    """

    title: str | None = None
    content: str | None = None
    summary: str | None = None
    category: EntryCategory | None = None
    status: EntryStatus | None = None
    confidence: float | None = None
    tags: list[str] | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """验证知识条目标题（更新时可选）.

        Args:
            v: 原始标题字符串

        Returns:
            str | None: 去除首尾空格后的标题

        Raises:
            ValueError: 标题长度不符合要求或包含特殊字符
        """
        if v is not None:
            if not v.strip():
                msg = "知识条目标题不能为空"
                raise ValueError(msg)
            stripped = v.strip()
            if len(stripped) < _MIN_TAG_NAME_LENGTH + 1:
                msg = f"知识条目标题不能少于{_MIN_TAG_NAME_LENGTH + 1}个字符"
                raise ValueError(msg)
            if len(stripped) > _MAX_TITLE_LENGTH:
                msg = f"知识条目标题不能超过{_MAX_TITLE_LENGTH}个字符"
                raise ValueError(msg)
            if _INVALID_TITLE_PATTERN.search(stripped):
                msg = "知识条目标题包含不允许的特殊字符"
                raise ValueError(msg)
            return stripped
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str | None) -> str | None:
        """验证知识条目内容（更新时可选）.

        Args:
            v: 原始内容字符串

        Returns:
            str | None: 去除首尾空格后的内容

        Raises:
            ValueError: 内容长度不足或包含恶意代码
        """
        if v is not None:
            if not v.strip():
                msg = "知识条目内容不能为空"
                raise ValueError(msg)
            stripped = v.strip()
            if len(stripped) < _MAX_CONTENT_MIN_LENGTH:
                msg = f"知识条目内容不能少于{_MAX_CONTENT_MIN_LENGTH}个字符"
                raise ValueError(msg)
            if _MALICIOUS_PATTERN.search(stripped):
                msg = "知识条目内容包含潜在安全风险，请检查后重试"
                raise ValueError(msg)
            return stripped
        return v

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str | None) -> str | None:
        """验证知识条目摘要（更新时可选）.

        Args:
            v: 原始摘要字符串

        Returns:
            str | None: 去除首尾空格后的摘要

        Raises:
            ValueError: 摘要超过最大长度
        """
        if v is not None:
            stripped = v.strip()
            if len(stripped) > _MAX_SUMMARY_LENGTH:
                msg = f"知识条目摘要不能超过{_MAX_SUMMARY_LENGTH}个字符"
                raise ValueError(msg)
            return stripped
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float | None:
        """验证信心评分范围.

        Args:
            v: 信心评分值

        Returns:
            float | None: 验证后的信心评分

        Raises:
            ValueError: 信心评分不在0.0到1.0范围内
        """
        if v is not None and (v < 0.0 or v > 1.0):
            msg = "信心评分必须在0.0到1.0之间"
            raise ValueError(msg)
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """验证标签列表（更新时可选）.

        Args:
            v: 标签名称列表

        Returns:
            list[str] | None: 去除首尾空格后的标签列表

        Raises:
            ValueError: 标签名称长度不符合要求
        """
        if v is None:
            return v
        result: list[str] = []
        for tag in v:
            tag_stripped = tag.strip()
            if len(tag_stripped) < _MIN_TAG_NAME_LENGTH:
                msg = f"标签名称不能少于{_MIN_TAG_NAME_LENGTH}个字符"
                raise ValueError(msg)
            if len(tag_stripped) > _MAX_TAG_NAME_LENGTH:
                msg = f"标签名称不能超过{_MAX_TAG_NAME_LENGTH}个字符"
                raise ValueError(msg)
            result.append(tag_stripped)
        return result


class KnowledgeEntryResponse(BaseModel):
    """知识条目响应模型.

    用于返回知识条目的完整详情，支持从ORM模型实例直接创建。

    Attributes:
        id: 知识条目唯一标识
        title: 知识条目标题
        content: 知识条目正文内容
        category: 知识条目分类
        tags: 关联标签列表
        source_type: 知识来源类型
        created_at: 创建时间（ISO 8601格式）
        updated_at: 更新时间（ISO 8601格式）
    """

    model_config: ClassVar = {"from_attributes": True, "json_schema_extra": {
        "example": {
            "id": 1,
            "title": "如何申请法律援助",
            "content": "申请法律援助需要准备以下材料：身份证明、经济困难证明、案件相关证据等。"
                       "申请人需前往当地法律援助中心提交申请。",
            "category": "law",
            "tags": ["法律援助", "申请流程", "常见问题"],
            "source_type": "manual",
            "created_at": "2025-01-15T08:30:00Z",
            "updated_at": "2025-06-20T14:22:00Z",
        }
    }}

    id: int
    title: str
    content: str
    category: EntryCategory
    tags: list[str] | None = None
    source_type: SourceType | str = "manual"
    created_at: datetime
    updated_at: datetime


class PaginatedKnowledgeResponse(BaseModel):
    """知识条目分页响应模型.

    标准化知识条目分页查询的响应格式，包含当前页数据、总数统计
    及导航辅助属性。

    Attributes:
        items: 当前页知识条目数据列表
        total: 符合条件的记录总数（>= 0）
        page: 当前页码（>= 1）
        page_size: 每页记录数（1-100）
        total_pages: 总页数（派生属性，>= 0）
        has_next: 是否有下一页（派生属性）
        has_prev: 是否有上一页（派生属性）
    """

    items: list[KnowledgeEntryResponse]
    total: int
    page: int
    page_size: int

    @computed_field
    @property
    def total_pages(self) -> int:
        """计算总页数.

        Returns:
            int: 总页数，至少为0
        """
        if self.page_size <= 0:
            return 0
        return max(0, math.ceil(self.total / self.page_size))

    @computed_field
    @property
    def has_next(self) -> bool:
        """当前页之后是否还有数据.

        Returns:
            bool: 是否有下一页
        """
        return self.page < self.total_pages

    @computed_field
    @property
    def has_prev(self) -> bool:
        """当前页之前是否还有数据.

        Returns:
            bool: 是否有上一页
        """
        return self.page > 1

    @field_validator("total")
    @classmethod
    def validate_total(cls, v: int) -> int:
        """验证总条目数.

        Args:
            v: 总条目数值

        Returns:
            int: 验证后的总条目数

        Raises:
            ValueError: 总条目数为负数
        """
        if v < 0:
            msg = "总条目数不能为负数"
            raise ValueError(msg)
        return v

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        """验证当前页码.

        Args:
            v: 当前页码值

        Returns:
            int: 验证后的当前页码

        Raises:
            ValueError: 页码小于1
        """
        if v < 1:
            msg = "当前页码必须大于等于1"
            raise ValueError(msg)
        return v

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """验证每页条目数.

        Args:
            v: 每页条目数值

        Returns:
            int: 验证后的每页条目数

        Raises:
            ValueError: 每页条目数不在1到100范围内
        """
        if v <= 0:
            msg = "每页条目数必须大于0"
            raise ValueError(msg)
        if v > _MAX_PAGE_SIZE:
            msg = f"每页条目数不能超过{_MAX_PAGE_SIZE}"
            raise ValueError(msg)
        return v


class EntryRelationCreate(BaseModel):
    """创建条目关联关系请求模型.

    Attributes:
        target_entry_id: 目标知识条目ID
        relation_type: 关系类型
    """

    target_entry_id: int
    relation_type: RelationType

    @field_validator("target_entry_id")
    @classmethod
    def validate_target_entry_id(cls, v: int) -> int:
        """验证目标条目ID.

        Args:
            v: 目标条目ID

        Returns:
            int: 验证后的目标条目ID

        Raises:
            ValueError: ID为非正整数
        """
        if v <= 0:
            msg = "目标条目ID必须为正整数"
            raise ValueError(msg)
        return v


class KnowledgeTagCreate(BaseModel):
    """创建知识标签请求模型.

    Attributes:
        name: 标签名称（2-50字符，需确保唯一性）
    """

    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证标签名称.

        检查标签名称长度和格式，确保唯一性和规范性。

        Args:
            v: 原始标签名称

        Returns:
            str: 去除首尾空格后的标签名称

        Raises:
            ValueError: 标签名称长度不符合要求或包含非法字符
        """
        if not v or not v.strip():
            msg = "标签名称不能为空"
            raise ValueError(msg)
        stripped = v.strip()
        if len(stripped) < _MIN_TAG_NAME_LENGTH:
            msg = f"标签名称不能少于{_MIN_TAG_NAME_LENGTH}个字符"
            raise ValueError(msg)
        if len(stripped) > _MAX_TAG_NAME_LENGTH:
            msg = f"标签名称不能超过{_MAX_TAG_NAME_LENGTH}个字符"
            raise ValueError(msg)
        if _INVALID_TITLE_PATTERN.search(stripped):
            msg = "标签名称包含不允许的特殊字符"
            raise ValueError(msg)
        return stripped


class EntryRelationResponse(BaseModel):
    """条目关联关系响应模型.

    Attributes:
        id: 关联关系唯一标识
        source_entry_id: 源知识条目ID
        target_entry_id: 目标知识条目ID
        relation_type: 关系类型
        created_at: 创建时间（ISO 8601格式）
    """

    id: int
    source_entry_id: int
    target_entry_id: int
    relation_type: RelationType
    created_at: datetime


class KnowledgeTagResponse(BaseModel):
    """知识标签响应模型.

    Attributes:
        id: 标签唯一标识
        name: 标签名称
        created_at: 创建时间（ISO 8601格式）
        entry_count: 使用该标签的知识条目数量
    """

    id: int
    name: str
    created_at: datetime
    entry_count: int


class LegalRuleCreate(BaseModel):
    """创建法条规则请求模型."""

    rule_id: str
    name: str
    description: str | None = None
    source_law: str | None = None
    article: str | None = None
    conditions: str | None = None
    conclusion: str | None = None
    evidence_types: str | None = None
    weight: float | None = None

    @field_validator("rule_id")
    @classmethod
    def validate_rule_id(cls, v: str) -> str:
        """验证规则ID."""
        if not v or not v.strip():
            msg = "规则ID不能为空"
            raise ValueError(msg)
        stripped = v.strip()
        if len(stripped) > 50:  # noqa: PLR2004
            msg = "规则ID不能超过50个字符"
            raise ValueError(msg)
        return stripped

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证规则名称."""
        if not v or not v.strip():
            msg = "规则名称不能为空"
            raise ValueError(msg)
        stripped = v.strip()
        if len(stripped) > _MAX_RULE_NAME_LENGTH:
            msg = "规则名称不能超过200个字符"
            raise ValueError(msg)
        return stripped

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float | None) -> float | None:
        """验证规则权重."""
        if v is not None and (v < 0.0 or v > 1.0):
            msg = "规则权重必须在0.0到1.0之间"
            raise ValueError(msg)
        return v


class LegalRuleUpdate(BaseModel):
    """更新法条规则请求模型，所有字段可选."""

    name: str | None = None
    description: str | None = None
    source_law: str | None = None
    article: str | None = None
    conditions: str | None = None
    conclusion: str | None = None
    evidence_types: str | None = None
    weight: float | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """验证规则名称."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                msg = "规则名称不能为空"
                raise ValueError(msg)
            if len(stripped) > _MAX_RULE_NAME_LENGTH:
                msg = "规则名称不能超过200个字符"
                raise ValueError(msg)
            return stripped
        return v

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float | None) -> float | None:
        """验证规则权重."""
        if v is not None and (v < 0.0 or v > 1.0):
            msg = "规则权重必须在0.0到1.0之间"
            raise ValueError(msg)
        return v
