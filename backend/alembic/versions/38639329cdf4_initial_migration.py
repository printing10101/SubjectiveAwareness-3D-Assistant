"""Initial migration

Revision ID: 38639329cdf4
Revises:
Create Date: 2026-05-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "38639329cdf4"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("case_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cases_id"), "cases", ["id"], unique=False)
    op.create_index(op.f("ix_cases_status"), "cases", ["status"], unique=False)
    op.create_index(op.f("ix_cases_title"), "cases", ["title"], unique=False)

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("result_json", sa.String(), nullable=False),
        sa.Column("knowledge_score", sa.Float(), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analyses_id"), "analyses", ["id"], unique=False)

    with op.batch_alter_table("analyses") as batch_op:
        batch_op.create_check_constraint(
            "ck_analyses_knowledge_score",
            sa.text("knowledge_score IS NULL OR (knowledge_score >= 0.0 AND knowledge_score <= 10.0)"),
        )

    op.create_table(
        "legal_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_law", sa.String(length=300), nullable=True),
        sa.Column("article", sa.String(length=100), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("evidence_types", sa.Text(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_legal_rules_id"), "legal_rules", ["id"], unique=False)
    op.create_index(
        op.f("ix_legal_rules_rule_id"), "legal_rules", ["rule_id"], unique=True
    )

    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("log_level", sa.String(length=20), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("action", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_system_logs_id"), "system_logs", ["id"], unique=False)
    op.create_index(
        op.f("ix_system_logs_log_level"), "system_logs", ["log_level"], unique=False
    )

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("fine_tune_time", sa.DateTime(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_versions_id"), "model_versions", ["id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_model_versions_id"), table_name="model_versions")
    op.drop_table("model_versions")
    op.drop_index(op.f("ix_system_logs_log_level"), table_name="system_logs")
    op.drop_index(op.f("ix_system_logs_id"), table_name="system_logs")
    op.drop_table("system_logs")
    op.drop_index(op.f("ix_legal_rules_rule_id"), table_name="legal_rules")
    op.drop_index(op.f("ix_legal_rules_id"), table_name="legal_rules")
    op.drop_table("legal_rules")
    op.drop_index(op.f("ix_analyses_id"), table_name="analyses")
    op.drop_table("analyses")
    op.drop_index(op.f("ix_cases_title"), table_name="cases")
    op.drop_index(op.f("ix_cases_status"), table_name="cases")
    op.drop_index(op.f("ix_cases_id"), table_name="cases")
    op.drop_table("cases")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
