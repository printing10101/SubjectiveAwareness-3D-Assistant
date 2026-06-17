"""知识库相关的 Pydantic 数据验证模型.

定义知识条目、标签、关联关系的创建、更新和响应的数据结构及字段校验规则。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: math
import math
# 导入模块: re
import re
# 导入模块: from datetime
from datetime import datetime
# 导入模块: from typing
from typing import ClassVar

# 导入模块: from pydantic
from pydantic import BaseModel, computed_field, field_validator

# 导入模块: from app.models.entry_relation
from app.models.entry_relation import RelationType
# 导入模块: from app.models.knowledge_entry
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


# 定义 KnowledgeEntryCreate 类
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

    # 应用装饰器: field_validator
    @field_validator("title")
    # 应用装饰器: classmethod
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
        # 条件判断：处理业务逻辑
        if not v or not v.strip():
            msg = "知识条目标题不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
               # 条件判断：处理业务逻辑
 stripped = v.strip()
        # 条件判断: 检查 len(stripped) < _MIN_TAG_NAME_LENGTH + 1
        if len(stripped) < _MIN_TAG_NAME_LENGTH + 1:
            msg = f"知识条目标题不能少于{_MIN_TAG_NAME_LENGTH        # 条件判断：处理业务逻辑
 + 1}个字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 条件判断: 检查 len(stripped) > _MAX_TITLE_LENGTH
        if len(stripped) > _MAX_TITLE_LENGTH:
            msg = f"知识        # 条件判断：处理业务逻辑
条目标题不能超过{_MAX_TITLE_LENGTH}个字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 条件判断: 检查 _INVALID_TITLE_PATTERN.search(stripped)
        if _INVALID_TITLE_PATTERN.search(stripped):
            msg = "知识条目标题包含不允许的特殊字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return stripped

    # 应用装饰器: field_validator
    @field_validator("content")
    # 应用装饰器: classmethod
    @classmethod
    def validate_content(cls, v: str) -> str:
        """验证知识条目内容.

        检查内容长度和安全性，防止恶意内容注入。

        Args:
            v: 原始内容字符串

        Returns:
               # 条件判断：处理业务逻辑
     str: 去除首尾空格后的内容

        Raises:
            ValueError: 内容长度不足或包含恶意代码
        """
        # 条件判断: 检查 not v or        # 条件判断：处理业务逻辑
        if not v or        # 条件判断：处理业务逻辑
 not v.strip():
            msg = "知识条目内容不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 初始化变量 stripped
        stripped = v.strip()
        # 条件判断: 检查 len        # 条件判断：处理业务逻辑
        if len        # 条件判断：处理业务逻辑
(stripped) < _MAX_CONTENT_MIN_LENGTH:
            msg = f"知识条目内容不能少于{_MAX_CONTENT_MIN_LENGTH}个字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 条件判断: 检查 _MALICIOUS_PATTERN.search(stripped)
        if _MALICIOUS_PATTERN.search(stripped):
            msg = "知识条目内容包含潜在安全风险，请检查后重试"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return stripped

    # 应用装饰器: field_validator
    @field_validator("tags")
    # 应用装饰器: classmethod
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """验证标签列表.

                # 条件判断：处理业务逻辑
Args:
            v: 标签名称列表

        Returns:
            list[str] | None: 去除首尾空格后的标签列表

        Raises:
                   # 条件判断：处理业务逻辑
     ValueError: 标签名称长度不符合要求
        """
        # 条件判断: 检查 v is None
        if v is None:
            # 返回处理结果
            return v
        result: list[str] = []
        # 遍历: for t            # 条件判断：处理业务逻辑
        for t            # 条件判断：处理业务逻辑
ag in v:
            # 初始化变量 tag_stripped
            tag_stripped = tag.strip()
            # 条件判断: 检查 len(tag_stripped) < _MIN_TAG_NAME_LENGTH
            if len(tag_stripped) < _MIN_TAG_NAME_LENGTH:
                msg = f"标签名称不能少于{_MIN_TAG_NAME_LENGTH}个字符"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 条件判断: 检查 len(tag_stripped) > _MAX_TAG_NAME_LENGTH
            if len(tag_stripped) > _MAX_TAG_NAME_LENGTH:
                msg = f"标签名称不能超过{_MAX_TAG_NAME_LENGTH}个字符"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            re        # 条件判断：处理业务逻辑
sult.append(tag_stripped)
        # 返回处理结果
        return result

    # 应用装饰器: field_validator
    @field_validator("source_type")
    # 应用装饰器: classmethod
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        """验证来源类型."""
        # 初始化变量 allowed
        allowed = {item.value for item in SourceType}
        # 条件判断: 检查 v not in allowed
        if v not in allowed:
            msg = f"来源类型必须为以下之一: {', '.join(sorted(allowed))}"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return v


# 定义 KnowledgeEntryUpdate 类
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

    # 应用装饰器: field_validator
    @field_validator("title")
    # 应用装饰器: classmeth        # 条件判断：处理业务逻辑
    @classmeth        # 条件判断：处理业务逻辑
od
             # 条件判断：处理业务逻辑
   def validate_title(cls, v: str | None) -> str | None:
        """验证知识条目标题（更新时可选）.

        Args:
                      # 条件判断：处理业务逻辑
  v: 原始标题字符串

        Returns:
            str | None: 去除首尾空格后的标题

        Raises:
            ValueError: 标题长度不符合要求或包含特殊字符
        ""            # 条件判断：处理业务逻辑
"
        # 条件判断: 检查 v is not None
        if v is not None:
            # 条件判断: 检查 not v.strip()
            if not v.strip():
                msg = "知识条目标题不能为空"
                # 抛出异常，处理错误情况
                raise Value            # 条件判断：处理业务逻辑
Error(msg)
            # 初始化变量 stripped
            stripped = v.strip()
            # 条件判断: 检查 len(stripped) < _MIN_TAG_NAME_LENGTH + 1
            if len(stripped) < _MIN_TAG_NAME_LENGTH + 1:
                msg = f"知识条目标题不能少于{_MIN_TAG_NAME_LENGTH + 1}个字符"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 条件判断: 检查 len(stripped) > _MAX_TITLE_LENGTH
            if len(stripped) > _MAX_TITLE_LENGTH:
                msg = f"知识条目标题不能超过{_MAX_TITLE_LENGTH}个字符"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 条件判断: 检查 _INVALID_TITLE_PATTERN.search(stripped)
            if _INVALID_TITLE_PATTERN.search(stripped):
                msg = "知识条目标题包含不允许的特殊字符"
           # 条件判断：处理业务逻辑
                # 条件判断：处理业务逻辑
         raise ValueError(msg)
            # 返回处理结果
            return stripped
        # 返回处理结果
        return v

    # 应用装饰器: field_validator
    @field_validator("content")
             # 条件判断：处理业务逻辑
   @classmethod
    def validate_content(cls, v: str | None) -> str | None:
        """验证知识条目内容（更新时可选）.

        Args:
            v            # 条件判断：处理业务逻辑
: 原始内容字符串

        Returns:
            str | None: 去除首尾空格后的内容

        Raises:
            ValueError: 内容长度不足或包含恶意代码
        """
        # 条件判断: 检查 v is not None
        if v is not None:
            # 条件判断: 检查 not v.strip()
            if not v.strip():
                msg = "知识条目内容不能为空"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 初始化变量 stripped
            stripped = v.strip()
            # 条件判断: 检查 len(stripped) < _MAX_CONTENT_MIN_LENGTH
            if len(stripped) < _MAX_CONTENT_MIN_LENGTH:
                msg = f"知识条目内容不能少于{_MAX_CONTENT_MIN_LENGTH}个字符"
                # 抛出异常，处理错误情况
                raise ValueError(m        # 条件判断：处理业务逻辑
sg)
            # 条件判断: 检查 _MALICIOUS_PATTERN            # 条件判断：处理业
            if _MALICIOUS_PATTERN            # 条件判断：处理业务逻辑
.search(stripped):
                msg = "知识条目内容包含潜在安全风险，请检查后重试"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 返回处理结果
            return stripped
        # 返回处理结果
        return v

    # 应用装饰器: field_validator
    @field_validator("summary")
    # 应用装饰器: classmethod
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
        # 条件判断: 检查 v is not None
        if v is not None:
            # 条件判断：处理业务逻辑
        stripped = v.strip()
            # 条件判断: 检查 len(stripped) > _MAX_SUMMARY_LENGTH
            if len(stripped) > _MAX_SUMMARY_LENGTH:
                msg = f"知识条目摘要不能超过{_MAX_SUMMARY_LENGTH}个字符"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 返回处理结果
            return stripped
        # 返回处理结果
        return v

    # 应用装饰器: field_validator
    @field_validator("confidence")
    # 应用装饰器: classmethod
    @classmethod
    def validate_confidence(cls, v: float | None) -> float | None:
        """验证信心评分范围.

        Args:
            v: 信心评分值

        Returns:
           # 条件判断：处理业务逻辑
         float | None: 验证后的信心评分

        Raises:
            ValueError: 信心评分不在0.0到1.0范围内
        """
        # 条件判断: 检查             # 条件判断：处理业务逻辑
        if             # 条件判断：处理业务逻辑
v is not None and (v < 0.0 or v > 1.0):
            msg = "信心评分必须在0.0到1.0之间"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return v

    # 应用装饰器: field_validator
    @field_validator("tags")
    # 应用装饰器: classmethod
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
        # 条件判断: 检查 v is None
        if v is None:
            # 返回处理结果
            return v
        result: list[str] = []
        # 循环遍历：处理业务逻辑
        for tag in v:
            # 初始化变量 tag_stripped
            tag_stripped = tag.strip()
            # 条件判断: 检查 len(tag_stripped) < _MIN_TAG_NAME_LENGTH
            if len(tag_stripped) < _MIN_TAG_NAME_LENGTH:
                msg = f"标签名称不能少于{_MIN_TAG_NAME_LENGTH}个字符"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 条件判断: 检查 len(tag_stripped) > _MAX_TAG_NAME_LENGTH
            if len(tag_stripped) > _MAX_TAG_NAME_LENGTH:
                msg = f"标签名称不能超过{_MAX_TAG_NAME_LENGTH}个字符"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            result.append(tag_stripped)
        # 返回处理结果
        return result


# 定义 KnowledgeEntryResponse 类
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
    updated_at:        # 条件判断：处理业务逻辑
 datetime


# 定义 PaginatedKnowledgeResponse 类
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

    # 应用装饰器: computed_field
    @computed_field
    # 应用装饰器: property
    @property
    def total_pages(self) -> int:
        """计算总页数.

        Returns:
            int: 总页数，至少为0
        """
        # 条件判断: 检查 self.page_size <= 0
        if self.page_size <= 0:
            # 返回处理结果
            return 0
        # 返回处理结果
        return max(0, math.ceil(self.total / self.page_size))

        # 条件判断：处理业务逻辑
    @computed_field
    # 应用装饰器: property
    @property
    def has_next(self) -> bool:
        """当前页之后是否还有数据.

        Returns:
            bool: 是否有下一页
        """
        # 返回处理结果
        return self.page < self.total_pages

    # 应用装饰器: computed_field
    @computed_field
    # 应用装饰器: property
    @property
    def has_prev(self) -> bool:
        """当前页之前是否还有数据.

        Returns:
            bool: 是否有上一页
          # 条件判断：处理业务逻辑
      """
        # 返回处理结果
        return self.page > 1

    # 应用装饰器: field_validator
    @field_validator("total")
    # 应用装饰器: classmethod
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
        # 条件判断: 检查 v < 0
        if v < 0:
            msg = "总条目数不能为负数"
                   # 条件判断：处理业务逻辑
 raise ValueError(msg)
        # 返回处理结果
        return v

    # 应用装饰器: field_validator
    @field_validator(        # 条件判断：处理业务逻辑
"page")
    # 应用装饰器: classmethod
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
        # 条件判断: 检查 v < 1
        if v < 1:
            msg = "当前页码必须大于等于1"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return v

    # 应用装饰器: field_validator
    @field_validator("page_size")
    # 应用装饰器: classmethod
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """验证每页条目数.

        Args:
            v: 每页条目数值

        Returns:
            int: 验证后的每页条目数

        Raises:
            ValueError: 每页条目数不在1到100范围内
            # 条件判断：处理业务逻辑
    """
        # 条件判断: 检查 v <= 0
        if v <= 0:
            msg = "每页条目数必须大于0"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 条件判断: 检查 v > _MAX_PAGE_SIZE
        if v > _MAX_PAGE_SIZE:
            msg = f"每页条目数不能超过{_MAX_PAGE_SIZE}"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return v


# 定义 EntryRelationCreate 类
class EntryRelationCreate(BaseModel):
    """创建条目关联关系请求模型.

    Attributes:
        target_entry_id: 目标知识条目ID
        relation_type: 关系类型
    """

    target_entry_id: int
    relation_type: RelationType

    # 应用装饰器: field_validator
    @field_validator("target_entry_id")
    # 应用装饰器: classmethod
    @classmethod
    def validate_target_en        # 条件判断：处理业务逻辑
        # 函数 validate_target_en 的初始化逻辑
try_id(cls, v: int) -> int:
        """验证目标条目ID.

        Args:
            v: 目标条目ID

        Returns:
         # 条件判断：处理业务逻辑
           int: 验证后的目标条目ID

        Raises:
            ValueError: ID为非正整数
        """
        # 条件判断: 检查 v <= 0
        if v <= 0:
                 # 条件判断：处理业务逻辑
   msg = "目标条目ID必须为正整数"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return v


# 定义 KnowledgeTagCreate 类
class KnowledgeTagCreate(BaseModel):
          # 条件判断：处理业务逻辑
  """创建知识标签请求模型.

    Attributes:
        name: 标签名称（2-50字符，需确保唯一性）
    """

    name: str

    # 应用装饰器: field_validator
    @field_validator("name")
    # 应用装饰器: classmethod
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
        # 条件判断: 检查 not v or not v.strip()
        if not v or not v.strip():
            msg = "标签名称不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 初始化变量 stripped
        stripped = v.strip()
        # 条件判断: 检查 len(stripped) < _MIN_TAG_NAME_LENGTH
        if len(stripped) < _MIN_TAG_NAME_LENGTH:
            msg = f"标签名称不能少于{_MIN_TAG_NAME_LENGTH}个字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 条件判断: 检查 len(stripped) > _MAX_TAG_NAME_LENGTH
        if len(stripped) > _MAX_TAG_NAME_LENGTH:
            msg = f"标签名称不能超过{_MAX_TAG_NAME_LENGTH}个字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 条件判断: 检查 _INVALID_TITLE_PATTERN.search(stripped)
        if _INVALID_TITLE_PATTERN.search(stripped):
            msg = "标签名称包含不允许的特殊字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return stripped


# 定义 EntryRelationResponse 类
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
    relation_type:        # 条件判断：处理业务逻辑
 RelationType
    created_at: datetime


# 定义 KnowledgeTagResponse 类
class KnowledgeTagResponse(BaseModel):
    """知识标签响应模型.

    Att        # 条件判断：处理业务逻辑
ributes:
        id: 标签唯一标识
        name: 标签名称
        created_at: 创建时间（ISO 8601格式）
        entry_count: 使用该标签的知识条目数量
    """

    # 初始化变量 model_config
    model_config = {"from_attributes": True}

    id: int
    name: str
    created_at: datetime | None        # 条件判断：处理业务逻辑
 = None
    entry_count: int = 0


# 定义 LegalRuleCreate 类
class LegalRuleCreate(BaseModel):
    """创建法条规则请求模型."""

    rule_id:         # 条件判断：处理业务逻辑
str
    name: str
    description: str | None = None
    source_law: str | None = None
    article: str | None = None
    conditions: str | None = None
    conclusion: str | None = None
    evidence_types: str | None = None
    weight: float | None = None

    # 应用装饰器: field_validator
    @field_validator("rule_id")
    # 应用装饰器: classmethod
    @classmethod
    def validate_rule_id(cls, v: str) -> str:
        """验证规则ID."""
        # 条件判断: 检查 not v or not v.strip()
        if not v or not v.strip():
            msg = "规则ID不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 初始化变量 stripped
        stripped = v.strip()
        # 条件判断: 检查 len(stripped) > 50
        if len(stripped) > 50:  # noqa: PLR2004
            msg = "规则ID不能超过50个字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return stripped

    # 应用装饰器: field_validator
    @field_validator("name")
    # 应用装饰器: classmethod
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证规则名称."""
        # 条件判断: 检查 not v or not v.strip()
        if not v or not v.strip():
            msg = "规则名称不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
         # 条件判断：处理业务逻辑
       stripped = v.strip()
        i            # 条件判断：处理业务逻辑
f len(stripped) > _MAX_RULE_NAME_LENGTH:
            msg = "规则名称不能超过200个字符            # 条件判断：处理业务逻辑
"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return stripped

    # 应用装饰器: field_validator
    @field_validator("weight")
    # 应用装饰器: classmethod
    @classmethod
    def validate_weight(cls, v: float | None) -> float | None:
        """验证规则权重."""
        # 条件判断: 检查 v is not None and (v < 0.0 or v > 1.0)
        if v is not None and (v < 0.0 or v > 1.0):
            msg = "规则权重必须在0.0到1.0之间"
          # 条件判断：处理业务逻辑
          raise ValueError(msg)
        # 返回处理结果
        return v


# 定义 LegalRuleUpdate 类
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

    # 应用装饰器: field_validator
    @field_validator("name")
    # 应用装饰器: classmethod
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """验证规则名称."""
        # 条件判断: 检查 v is not None
        if v is not None:
            # 初始化变量 stripped
            stripped = v.strip()
            # 条件判断: 检查 not stripped
            if not stripped:
                msg = "规则名称不能为空"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 条件判断: 检查 len(stripped) > _MAX_RULE_NAME_LENGTH
            if len(stripped) > _MAX_RULE_NAME_LENGTH:
                msg = "规则名称不能超过200个字符"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 返回处理结果
            return stripped
        # 返回处理结果
        return v

    # 应用装饰器: field_validator
    @field_validator("weight")
    # 应用装饰器: classmethod
    @classmethod
    def validate_weight(cls, v: float | None) -> float | None:
        """验证规则权重."""
        # 条件判断: 检查 v is not None and (v < 0.0 or v > 1.0)
        if v is not None and (v < 0.0 or v > 1.0):
            msg = "规则权重必须在0.0到1.0之间"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return v
