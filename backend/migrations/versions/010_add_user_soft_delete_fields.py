"""add soft delete fields to users table

Revision ID: 010_add_user_soft_delete_fields
Revises: 5248c2a139f6
Create Date: 2026-06-07 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_add_user_soft_delete_fields"
down_revision: str | None = "009_blog_paragraph_comment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "deletion_status",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'active'"),
            )
        )
        batch_op.add_column(
            sa.Column("deletion_reason", sa.String(length=32), nullable=True)
        )
        batch_op.add_column(
            sa.Column("deletion_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("deletion_expires_at")
        batch_op.drop_column("deletion_reason")
        batch_op.drop_column("deletion_status")
