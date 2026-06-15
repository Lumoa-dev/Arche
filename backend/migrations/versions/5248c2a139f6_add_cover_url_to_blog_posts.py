"""add cover_url to blog_posts + create blog_post_files

Revision ID: 5248c2a139f6
Revises: 008_unify_permission_levels
Create Date: 2026-06-06 13:57:52.632146
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5248c2a139f6"
down_revision: str | None = "008_unify_permission_levels"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # blog_posts 新增 cover_url 列
    with op.batch_alter_table("blog_posts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("cover_url", sa.String(length=1024), nullable=True)
        )

    # 创建 blog_post_files 表（帖子文件生命周期管理）
    op.create_table(
        "blog_post_files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("post_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("oss_file_id", sa.UUID(), nullable=False),
        sa.Column("file_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("blog_post_files", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_blog_post_files_post_id"), ["post_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("blog_post_files", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_blog_post_files_post_id"))
    op.drop_table("blog_post_files")

    with op.batch_alter_table("blog_posts", schema=None) as batch_op:
        batch_op.drop_column("cover_url")
