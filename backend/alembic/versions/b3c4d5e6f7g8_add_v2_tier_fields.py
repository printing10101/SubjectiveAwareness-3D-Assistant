"""add v2 tier-based analysis fields

Revision ID: b3c4d5e6f7g8
Revises: a2c3d4e5f6g7
Create Date: 2026-06-12 12:00:00.000000

阶段 4：推理引擎重构（核心）
============================

把"0-10 平均分"打切到"三维度 × 四档"，为 ``analyses`` 表增加：

- ``version``              ：协议版本（"v1" / "v2"），默认 v1（向后兼容）
- ``dimension1_tier``      ：维度 1（构成要件）档级
- ``dimension2_tier``      ：维度 2（情节模式）档级
- ``dimension3_tier``      ：维度 3（矛盾分析）档级
- ``final_tier``           ：组合后最终档级
- ``triggered_rule_ids``   ：JSON 数组，触发的规则 ID（兼容 SQLite 用 TEXT）
- ``matched_tag_ids``      ：JSON 数组，命中的标签 ID
- ``conflicts``            ：JSON 数组，冲突检测结果
- ``pipeline_meta``        ：JSON，记录各阶段耗时

并把 ``knowledge_score`` 的含义从"0-10 分数"改为"0-1 置信度"，
同时将其约束由 ``<= 10.0`` 改为 ``<= 1.0``，以及列名重命名（保留旧名作
deprecated alias 以保证 v1 数据仍能通过 ORM 读取——实际由应用层 model
处理；本迁移只负责 schema 层）。

注：为兼容老数据，已存在的 ``knowledge_score`` 值若 > 1.0，会被
等比缩放到 0-1 区间（score / 10.0）。这是 v1 → v2 语义变更的合理近似。
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7g8"
down_revision: Union[str, None] = "a2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增 v2 档级相关列 + 知识评分语义变更."""
    # 1) 新增列
    with op.batch_alter_table("analyses", recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column(
                "version",
                sa.String(length=4),
                nullable=False,
                server_default="v1",
            )
        )
        batch_op.add_column(sa.Column("dimension1_tier", sa.String(length=4), nullable=True))
        batch_op.add_column(sa.Column("dimension2_tier", sa.String(length=4), nullable=True))
        batch_op.add_column(sa.Column("dimension3_tier", sa.String(length=4), nullable=True))
        batch_op.add_column(sa.Column("final_tier", sa.String(length=4), nullable=True))
        batch_op.add_column(sa.Column("triggered_rule_ids", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("matched_tag_ids", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("conflicts", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("pipeline_meta", sa.Text(), nullable=True))

        # 索引
        batch_op.create_index("ix_analyses_version", ["version"])
        batch_op.create_index("ix_analyses_final_tier", ["final_tier"])

    # 2) 知识评分语义变更：0-10 → 0-1 置信度
    #    对历史数据做等比缩放（score / 10.0）
    op.execute(
        sa.text(
            "UPDATE analyses "
            "SET knowledge_score = knowledge_score / 10.0 "
            "WHERE knowledge_score IS NOT NULL AND knowledge_score > 1.0"
        )
    )
    op.execute(
        sa.text(
            "UPDATE analyses "
            "SET knowledge_score = 1.0 "
            "WHERE knowledge_score IS NOT NULL AND knowledge_score > 1.0"
        )
    )

    # 3) 重建 CHECK 约束以匹配 0-1
    with op.batch_alter_table("analyses", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_analyses_knowledge_score", type_="check")
        batch_op.create_check_constraint(
            "ck_analyses_knowledge_score",
            sa.text(
                "knowledge_score IS NULL OR (knowledge_score >= 0.0 AND knowledge_score <= 1.0)"
            ),
        )


def downgrade() -> None:
    """回滚档级列与约束."""
    # 1) 还原知识评分为 0-10：乘 10
    op.execute(
        sa.text(
            "UPDATE analyses "
            "SET knowledge_score = knowledge_score * 10.0 "
            "WHERE knowledge_score IS NOT NULL"
        )
    )

    with op.batch_alter_table("analyses", recreate="auto") as batch_op:
        # 2) 重建 CHECK 约束
        batch_op.drop_constraint("ck_analyses_knowledge_score", type_="check")
        batch_op.create_check_constraint(
            "ck_analyses_knowledge_score",
            sa.text(
                "knowledge_score IS NULL OR (knowledge_score >= 0.0 AND knowledge_score <= 10.0)"
            ),
        )

        # 3) 删索引
        batch_op.drop_index("ix_analyses_final_tier")
        batch_op.drop_index("ix_analyses_version")

        # 4) 删列
        batch_op.drop_column("pipeline_meta")
        batch_op.drop_column("conflicts")
        batch_op.drop_column("matched_tag_ids")
        batch_op.drop_column("triggered_rule_ids")
        batch_op.drop_column("final_tier")
        batch_op.drop_column("dimension3_tier")
        batch_op.drop_column("dimension2_tier")
        batch_op.drop_column("dimension1_tier")
        batch_op.drop_column("version")
