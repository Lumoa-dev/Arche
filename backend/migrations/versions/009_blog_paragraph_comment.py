"""add source_url/source_name to blog_posts + paragraph_index to blog_comments

Revision ID: 009_blog_paragraph_comment
Revises: 5248c2a139f6
Create Date: 2026-06-06 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_blog_paragraph_comment"
down_revision: str | None = "5248c2a139f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # blog_posts 新增 source_url / source_name 列
    with op.batch_alter_table("blog_posts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("source_url", sa.String(length=1024), nullable=True)
        )
        batch_op.add_column(
            sa.Column("source_name", sa.String(length=256), nullable=True)
        )

    # blog_comments 新增 paragraph_index 列
    with op.batch_alter_table("blog_comments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("paragraph_index", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("blog_comments", schema=None) as batch_op:
        batch_op.drop_column("paragraph_index")

    with op.batch_alter_table("blog_posts", schema=None) as batch_op:
        batch_op.drop_column("source_name")
        batch_op.drop_column("source_url")
