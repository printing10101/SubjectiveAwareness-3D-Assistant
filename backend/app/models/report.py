"""报告数据模型模块.

定义报告相关的数据表结构，包括报告主表和审查记录表。

# 应用装饰器: file: report.py
@file: report.py
"""
from datetime import datetime
from typing import Any
from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Report(Base):
    """报告主表模型.

    存储生成的分析报告内容及其导出文件路径。

    Attributes:
        id: 报告唯一标识符
        case_id: 关联案件ID
        analysis_id: 关联分析结果ID
        content_json: 报告内容（JSON格式，包含10章结构化内容）
        file_path_pdf: PDF导出文件路径
        file_path_docx: DOCX导出文件路径
        generated_at: 报告生成时间
        version: 报告版本号
    """
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="报告内容（JSON格式，包含10章结构化内容）",
    )
    file_path_pdf: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="PDF导出文件路径",
    )
    file_path_docx: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="DOCX导出文件路径",
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        comment="报告生成时间",
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="1.0.0",
        comment="报告版本号",
    )

    # 关系映射
    case = relationship("Case", back_populates="reports", lazy="selectin")
    analysis = relationship("Analysis", back_populates="reports", lazy="selectin")
    reviews = relationship(
        "ReportReview",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # 索引
    __table_args__ = (
        Index("idx_report_case_analysis", "case_id", "analysis_id"),
        Index("idx_report_generated_at", "generated_at"),
    )

    def __repr__(self) -> str:
        """返回报告模型的字符串表示."""
        return f"<Report(id={self.id}, case_id={self.case_id}, version={self.version})>"


# 定义 ReportReview 类
class ReportReview(Base):
    """报告审查记录表模型.

    存储人工审查清单的填写记录。

    Attributes:
        id: 审查记录唯一标识符
        report_id: 关联报告ID
        reviewer_id: 审查人ID（用户ID）
        items: 审查项勾选状态（JSON格式）
        comments: 审查意见
        completed_at: 审查完成时间
    """
    __tablename__ = "report_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="审查人ID",
    )
    items: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="审查项勾选状态（JSON格式）",
    )
    comments: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="审查意见",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="审查完成时间",
    )

    # 关系映射
    report = relationship("Report", back_populates="reviews", lazy="selectin")

    # 索引
    __table_args__ = (
        Index("idx_review_report_reviewer", "report_id", "reviewer_id"),
    )

    def __repr__(self) -> str:
        """返回审查记录模型的字符串表示."""
        return f"<ReportReview(id={self.id}, report_id={self.report_id})>"
