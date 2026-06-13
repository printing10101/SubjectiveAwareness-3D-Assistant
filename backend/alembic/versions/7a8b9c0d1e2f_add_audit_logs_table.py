"""add_audit_logs_table

Revision ID: 7a8b9c0d1e2f
Revises: 34beb1e17e08
Create Date: 2026-06-12 10:00:00.000000

新增 audit_logs 表用于记录对核心 API（/api/cases/* 与 /api/analyses/*）
的访问行为，包含操作者、目标资源、HTTP 方法、客户端 IP、响应状态码、
User-Agent 等字段，并附带多种索引以加速审计查询。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a8b9c0d1e2f"
down_revision: Union[str, None] = "34beb1e17e08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 audit_logs 表与相关索引.

    表字段设计：
        - id: 主键
        - user_id: 操作用户 ID（外键到 users.id，匿名访问时为 NULL）
        - username: 操作用户名（冗余存储，便于审计追踪）
        - action: HTTP 方法（GET/POST/PUT/DELETE/PATCH）
        - method: HTTP 方法冗余字段（与 action 保持一致，便于查询）
        - target_type: 目标资源类型（case/analysis/other）
        - target_id: 目标资源 ID（字符串形式以兼容复合 ID）
        - path: 请求路径
        - ip: 客户端 IP 地址
        - status_code: HTTP 响应状态码
        - user_agent: 客户端 User-Agent 字符串
        - extra: 扩展信息（查询参数摘要、请求体摘要等）
        - timestamp: 操作时间戳

    索引设计：
        - 主键索引：id
        - 单列索引：user_id、action、timestamp、ip
        - 复合索引：(target_type, target_id) 加速按资源类型审计查询
    """
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("extra", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 单列索引（与模型 __table_args__ 中的 Index 声明保持一致）
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"], unique=False)
    op.create_index("ix_audit_logs_ip", "audit_logs", ["ip"], unique=False)

    # 复合索引：按资源类型 + 资源 ID 加速审计查询
    op.create_index(
        "ix_audit_logs_target",
        "audit_logs",
        ["target_type", "target_id"],
        unique=False,
    )

    # 外键约束：user_id 引用 users.id，删除用户时保留审计日志（SET NULL）
    # 注意：使用 batch_alter_table 以兼容 SQLite（不支持 ALTER TABLE ADD CONSTRAINT）
    with op.batch_alter_table("audit_logs", recreate="always") as batch_op:
        batch_op.create_foreign_key(
            "fk_audit_logs_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """删除 audit_logs 表.

    操作顺序：
        1. 删除外键约束
        2. 删除所有索引
        3. 删除表
    """
    with op.batch_alter_table("audit_logs", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_audit_logs_user_id", type_="foreignkey")

    op.drop_index("ix_audit_logs_target", table_name="audit_logs")
    op.drop_index("ix_audit_logs_ip", table_name="audit_logs")
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
