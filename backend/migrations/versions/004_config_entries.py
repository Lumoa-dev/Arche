"""create config_entries table

Revision ID: 004_config_entries
Revises: 003_orchestration
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_config_entries"
down_revision: str | None = "003_orchestration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "config_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "group", sa.String(length=64), server_default="general", nullable=False
        ),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("config_entries", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_config_entries_group"), ["group"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_config_entries_key"), ["key"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("config_entries", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_config_entries_key"))
        batch_op.drop_index(batch_op.f("ix_config_entries_group"))
    op.drop_table("config_entries")
