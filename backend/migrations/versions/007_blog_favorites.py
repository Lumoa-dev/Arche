"""添加博客收藏表

Revision ID: 007_blog_favorites
Revises: 006_monitor_templates
Create Date: 2026-04-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# 版本标识符
revision: str = "007_blog_favorites"
down_revision: str | None = "006_monitor_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blog_favorites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("post_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    with op.batch_alter_table("blog_favorites") as batch_op:
        batch_op.create_index("ix_blog_favorites_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_blog_favorites_post_id", ["post_id"], unique=False)
        batch_op.create_index(
            "ix_blog_favorites_user_post", ["user_id", "post_id"], unique=True
        )


def downgrade() -> None:
    op.drop_table("blog_favorites")
