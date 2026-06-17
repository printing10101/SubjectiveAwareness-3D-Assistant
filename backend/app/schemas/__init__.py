"""__init__ - Pydantic 数据模式定义.

本模块定义 API 请求和响应的数据验证模式。
使用 Pydantic 进行数据序列化和验证。

主要职责：
    - 定义请求体数据结构
    - 定义响应体数据结构
    - 字段类型验证和约束
    - 数据转换和格式化
    - API 文档自动生成支持

验证框架：Pydantic v2
序列化：JSON Schema

# 应用装饰器: author 帮信罪智能分析系统开发团队
@author 帮信罪智能分析系统开发团队
# 应用装饰器: version 1.0.0
@version 1.0.0
"""

# 导入模块: from app.schemas.analysis
from app.schemas.analysis import AnalyzeRequest
# 导入模块: from app.schemas.case
from app.schemas.case import (
    CaseBase,
    CaseCreate,
    CaseResponse,
    CaseUpdate,
    PaginatedResponse,
)
# 导入模块: from app.schemas.knowledge
from app.schemas.knowledge import (
    EntryRelationCreate,
    EntryRelationResponse,
    KnowledgeEntryCreate,
    KnowledgeEntryResponse,
    KnowledgeEntryUpdate,
    KnowledgeTagCreate,
    KnowledgeTagResponse,
    PaginatedKnowledgeResponse,
)
# 导入模块: from app.schemas.user
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserResponse,
    UserUpdate,
)


__all__ = [
    "AnalyzeRequest",
    "CaseBase",
    "CaseCreate",
    "CaseResponse",
    "CaseUpdate",
    "EntryRelationCreate",
    "EntryRelationResponse",
    "KnowledgeEntryCreate",
    "KnowledgeEntryResponse",
    "KnowledgeEntryUpdate",
    "KnowledgeTagCreate",
    "KnowledgeTagResponse",
    "PaginatedKnowledgeResponse",
    "PaginatedResponse",
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
]
