"""统一权限等级：access_level → required_level

将 blog_posts.access_level（字符串 A0-A9）迁移为
required_level（整数 0-5），直接复用 P 等级体系。

Revision ID: 008_unify_permission_levels
Revises: 007_blog_favorites
Create Date: 2026-06-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# 版本标识符
revision: str = "008_unify_permission_levels"
down_revision: str | None = "007_blog_favorites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("blog_posts") as batch_op:
        # 1. 新增整数字段，允许为空（兼容旧数据迁移）
        batch_op.add_column(sa.Column("required_level", sa.Integer(), nullable=True))

    # 2. 数据迁移：将 access_level（A0-A9）转为对应数字
    #    A0→0, A1→1, ..., A5→5, A6→5, ..., A9→5
    op.execute(
        """
        UPDATE blog_posts
        SET required_level = CASE
            WHEN access_level IN ('A0', 'a0') THEN 0
            WHEN access_level IN ('A1', 'a1') THEN 1
            WHEN access_level IN ('A2', 'a2') THEN 2
            WHEN access_level IN ('A3', 'a3') THEN 3
            WHEN access_level IN ('A4', 'a4') THEN 4
            ELSE 5
        END
        """
    )

    # 3. 设置 NOT NULL 和默认值
    with op.batch_alter_table("blog_posts") as batch_op:
        batch_op.alter_column(
            "required_level",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="5",
        )
        # 4. 删除旧字段
        batch_op.drop_column("access_level")


def downgrade() -> None:
    with op.batch_alter_table("blog_posts") as batch_op:
        # 恢复旧字段
        batch_op.add_column(
            sa.Column("access_level", sa.String(8), nullable=False, server_default="A5")
        )

    # 数据回迁：数字转回 A 等级
    op.execute(
        """
        UPDATE blog_posts
        SET access_level = CASE
            WHEN required_level = 0 THEN 'A0'
            WHEN required_level = 1 THEN 'A1'
            WHEN required_level = 2 THEN 'A2'
            WHEN required_level = 3 THEN 'A3'
            WHEN required_level = 4 THEN 'A4'
            ELSE 'A5'
        END
        """
    )

    with op.batch_alter_table("blog_posts") as batch_op:
        batch_op.drop_column("required_level")
