"""添加监控模板表

Revision ID: 006_monitor_templates
Revises: 005_cloud_workspace
Create Date: 2026-04-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# 版本标识符
revision: str = "006_monitor_templates"
down_revision: str | None = "005_cloud_workspace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monitor_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("components", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "refresh_interval", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    with op.batch_alter_table("monitor_templates") as batch_op:
        batch_op.create_index("ix_monitor_templates_user_id", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("monitor_templates")
