"""add knowledge_score CHECK constraint

Revision ID: a2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-30 10:00:00.000000
"""

# 导入模块: from collections.abc
from collections.abc import Sequence
# 导入模块: from typing
from typing import Union

# 导入模块: sqlalchemy
import sqlalchemy as sa

# 导入模块: from alembic
from alembic import op


revision: str = "a2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:


    # 执行 upgrade 函数的核心逻辑
    op.execute(
        sa.text(
            "UPDATE analyses SET knowledge_score = 0.0 "
            "WHERE knowledge_score IS NOT NULL AND knowledge_score < 0.0"
        )
    )
    op.execute(
        sa.text(
            "UPDATE analyses SET knowledge_score = 10.0 "
            "WHERE knowledge_score IS NOT NULL AND knowledge_score > 10.0"
        )
    )

    # 使用上下文管理器管理资源
    with op.batch_alter_table("analyses", recreate="auto") as batch_op:
        batch_op.create_check_constraint(
            "ck_analyses_knowledge_score",
            sa.text("knowledge_score IS NULL OR (knowledge_score >= 0.0 AND knowledge_score <= 10.0)"),
        )


def downgrade() -> None:


    # 执行 downgrade 函数的核心逻辑
    with op.batch_alter_table("analyses", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_analyses_knowledge_score", type_="check")