"""add enum check constraints for case status and analysis mode

Revision ID: a1b2c3d4e5f6
Revises: 38639329cdf4
Create Date: 2026-05-29 10:00:00.000000
"""

# ruff: noqa: S608

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "38639329cdf4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CASE_STATUS_VALUES = ("pending", "analyzing", "completed", "closed")
_ANALYSIS_MODE_VALUES = ("auto", "single", "multi")


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE cases SET status = 'pending' "
            "WHERE status IS NULL "
            f"OR status NOT IN {_CASE_STATUS_VALUES}"
        )
    )

    op.execute(
        sa.text(
            "UPDATE analyses SET mode = 'auto' "
            "WHERE mode IS NULL "
            f"OR mode NOT IN {_ANALYSIS_MODE_VALUES}"
        )
    )

    with op.batch_alter_table("cases") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=20),
            type_=sa.String(length=20),
            nullable=False,
            server_default="pending",
        )

    with op.batch_alter_table("analyses") as batch_op:
        batch_op.alter_column(
            "mode",
            existing_type=sa.String(length=20),
            type_=sa.String(length=20),
            nullable=False,
            server_default="auto",
        )

    with op.batch_alter_table("cases", recreate="auto") as batch_op:
        batch_op.create_check_constraint(
            "ck_cases_status",
            sa.text(f"status IN {_CASE_STATUS_VALUES}"),
        )

    with op.batch_alter_table("analyses", recreate="auto") as batch_op:
        batch_op.create_check_constraint(
            "ck_analyses_mode",
            sa.text(f"mode IN {_ANALYSIS_MODE_VALUES}"),
        )


def downgrade() -> None:
    with op.batch_alter_table("analyses", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_analyses_mode", type_="check")

    with op.batch_alter_table("cases", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_cases_status", type_="check")

    with op.batch_alter_table("analyses") as batch_op:
        batch_op.alter_column(
            "mode",
            existing_type=sa.String(length=20),
            type_=sa.String(length=20),
            nullable=True,
            server_default=None,
        )

    with op.batch_alter_table("cases") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=20),
            type_=sa.String(length=20),
            nullable=True,
            server_default=None,
        )

