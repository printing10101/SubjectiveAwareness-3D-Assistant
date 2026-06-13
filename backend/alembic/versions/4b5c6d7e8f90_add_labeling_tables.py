"""add_labeling_tables

创建 case_labels 与 case_dedup 两张标注/去重数据表：
- case_labels：用于存储对案件的标准化结构化标签
- case_dedup：用于记录案例之间的重复关系与相似度

Revision ID: 4b5c6d7e8f90
Revises: 7a8b9c0d1e2f
Create Date: 2026-06-12
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "4b5c6d7e8f90"
down_revision: Union[str, None] = "7a8b9c0d1e2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 case_labels 与 case_dedup 两张表."""
    op.create_table(
        "case_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "case_id",
            sa.Integer(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label_type", sa.String(length=64), nullable=False),
        sa.Column("label_value", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "label_type", name="uq_case_labels_case_id_label_type"),
    )
    op.create_index(op.f("ix_case_labels_id"), "case_labels", ["id"], unique=False)
    op.create_index(op.f("ix_case_labels_case_id"), "case_labels", ["case_id"], unique=False)
    op.create_index(op.f("ix_case_labels_label_type"), "case_labels", ["label_type"], unique=False)

    op.create_table(
        "case_dedup",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "canonical_case_id",
            sa.Integer(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "duplicate_case_id",
            sa.Integer(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("similarity", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "canonical_case_id", "duplicate_case_id", name="uq_case_dedup_pair"
        ),
    )
    op.create_index(op.f("ix_case_dedup_id"), "case_dedup", ["id"], unique=False)
    op.create_index(
        op.f("ix_case_dedup_canonical_case_id"),
        "case_dedup",
        ["canonical_case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_case_dedup_duplicate_case_id"),
        "case_dedup",
        ["duplicate_case_id"],
        unique=False,
    )

    with op.batch_alter_table("case_dedup", recreate="auto") as batch_op:
        batch_op.create_check_constraint(
            "ck_case_dedup_similarity_range",
            sa.text("similarity >= 0.0 AND similarity <= 1.0"),
        )


def downgrade() -> None:
    """删除 case_labels 与 case_dedup 两张表."""
    with op.batch_alter_table("case_dedup", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_case_dedup_similarity_range", type_="check")

    op.drop_index(op.f("ix_case_dedup_duplicate_case_id"), table_name="case_dedup")
    op.drop_index(op.f("ix_case_dedup_canonical_case_id"), table_name="case_dedup")
    op.drop_index(op.f("ix_case_dedup_id"), table_name="case_dedup")
    op.drop_table("case_dedup")

    op.drop_index(op.f("ix_case_labels_label_type"), table_name="case_labels")
    op.drop_index(op.f("ix_case_labels_case_id"), table_name="case_labels")
    op.drop_index(op.f("ix_case_labels_id"), table_name="case_labels")
    op.drop_table("case_labels")
