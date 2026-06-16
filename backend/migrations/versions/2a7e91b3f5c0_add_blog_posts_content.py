"""add blog_posts.content

Revision ID: 2a7e91b3f5c0
Revises: 15b29d45b36c
Create Date: 2026-06-25 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.

revision: str = "2a7e91b3f5c0"
down_revision: str | None = "15b29d45b36c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("blog_posts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("content", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("blog_posts", schema=None) as batch_op:
        batch_op.drop_column("content")
