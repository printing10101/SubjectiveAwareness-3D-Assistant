"""案件数据模型.

定义案件表结构，存储案件基本信息及其状态流转。
"""
from __future__ import annotations
import enum
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship
from app.database import Base
from app.models.user import User
from app.utils.encryption import EncryptedText


class CaseStatus(enum.Enum):
    """案件状态枚举.

    定义案件从创建到归档的完整生命周期状态：

    - pending:     待处理，案件已创建但尚未开始分析
    - analyzing:   分析中，系统正在执行 LLM 分析
    - completed:   已完成，分析流程成功结束
    - closed:      已关闭，案件归档不再变更
    """
    pending = "pending"
    analyzing = "analyzing"
    completed = "completed"
    closed = "closed"


# 定义 Case 类
class Case(Base):
    """案件表.

    Attributes:
        id: 主键
        title: 案件标题
        description: 案件描述
        case_text: 案件事实文本（数据库中以密文存储）
        status: 案件状态（pending/analyzing/completed/closed），受枚举类型和数据库 CHECK 约束保护
        created_by: 创建者用户 ID
        created_at: 创建时间
        updated_at: 更新时间
        creator: 创建者 ORM 关系
    """
    __tablename__ = "cases"
    __table_args__ = (
        Index("ix_cases_status_created_at", "status", "created_at"),
        Index("ix_cases_judgment_no", "judgment_no"),
        Index("ix_cases_source", "source"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    case_text = Column(EncryptedText, nullable=False)
    status = Column(
        Enum(CaseStatus, name="case_status_enum", create_constraint=True),
        nullable=False,
        default=CaseStatus.pending,
        index=True,
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    source = Column(String(50), nullable=True)
    judgment_no = Column(String(100), nullable=True)

    creator: Mapped[User | None] = relationship("User", backref="cases")
    # 报告反向关系：与 Report.case 的 back_populates="reports" 对应，
    # 避免 SQLAlchemy 在刷新 mapper 时抛 KeyError: 'reports'。
    reports: Mapped[list["Report"]] = relationship(
        "Report",
        back_populates="case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
