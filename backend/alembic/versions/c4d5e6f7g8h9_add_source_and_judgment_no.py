"""add source and judgment_no fields to cases

Revision ID: c4d5e6f7g8h9
Revises: b3c4d5e6f7g8
Create Date: 2026-06-15 23:58:00.000000

阶段 5：真实判决书数据入库支持
====================================

为支持 25 个真实贵州判决书数据的入库，为 ``cases`` 表增加：

- ``source``        ：数据来源标识（如 "real_gz2023" 表示真实贵州 2023 年案件）
- ``judgment_no``   ：判决书编号（如 "GZ2023BX001"），用于唯一标识和快速查询

这两个字段将用于区分合成数据与真实数据，并支持按判决书编号进行高效检索。
"""

# 导入模块: from collections.abc
from collections.abc import Sequence
# 导入模块: from typing
from typing import Union

# 导入模块: sqlalchemy
import sqlalchemy as sa

# 导入模块: from alembic
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7g8h9"
down_revision: Union[str, None] = "b3c4d5e6f7g8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增 source 和 judgment_no 列."""
    # 使用上下文管理器管理资源
    with op.batch_alter_table("cases", recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column("source", sa.String(length=50), nullable=True)
        )
        batch_op.add_column(
            sa.Column("judgment_no", sa.String(length=100), nullable=True)
        )
        
        # 创建索引以优化查询性能
        batch_op.create_index("ix_cases_source", ["source"])
        batch_op.create_index("ix_cases_judgment_no", ["judgment_no"])


def downgrade() -> None:
    """回滚 source 和 judgment_no 列."""
    # 使用上下文管理器管理资源
    with op.batch_alter_table("cases", recreate="auto") as batch_op:
        # 删除索引
        batch_op.drop_index("ix_cases_judgment_no")
        batch_op.drop_index("ix_cases_source")
        
        # 删除列
        batch_op.drop_column("judgment_no")
        batch_op.drop_column("source")
