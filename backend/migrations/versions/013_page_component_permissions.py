"""add page_component_permissions table for level-based page/component visibility

Revision ID: 013_page_component_permissions
Revises: 012_introduction_to_text
Create Date: 2026-06-15 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013_page_component_permissions"
down_revision: str | None = "012_introduction_to_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "page_component_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, index=True),
        sa.Column("page_name", sa.String(length=128), nullable=False),
        sa.Column("component_name", sa.String(length=128), nullable=False),
        sa.Column(
            "visible", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "level",
            "page_name",
            "component_name",
            name="uq_level_page_component",
        ),
    )

    # 为现有 level 0 插入默认配置：所有已知页面和组件默认可见
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=conn, only=["page_component_permissions"])
    table = sa.Table("page_component_permissions", meta, autoload_with=conn)

    # level 0（管理员）：所有页面组件全量可见
    rows = [
        {
            "level": 0,
            "page_name": "home",
            "component_name": "post_card",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "home",
            "component_name": "tag_cloud",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "home",
            "component_name": "search_bar",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "explore",
            "component_name": "post_list",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "explore",
            "component_name": "filter_panel",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "create",
            "component_name": "post_editor",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "create",
            "component_name": "draft_list",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "assets",
            "component_name": "asset_manager",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "scheduler",
            "component_name": "task_list",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "profile",
            "component_name": "user_info",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "profile",
            "component_name": "settings_panel",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "posts",
            "component_name": "post_manager",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "creator",
            "component_name": "dashboard",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "tasks",
            "component_name": "task_center",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "tasks",
            "component_name": "crawler_config",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "tasks",
            "component_name": "cloud_training",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "console",
            "component_name": "console_dashboard",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "admin_users",
            "component_name": "user_list",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "admin_content",
            "component_name": "content_moderation",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "admin_ops",
            "component_name": "system_monitor",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "admin_ops",
            "component_name": "storage_quota",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "admin_ops",
            "component_name": "runtime_config",
            "visible": True,
        },
        {
            "level": 0,
            "page_name": "admin_permissions",
            "component_name": "permission_editor",
            "visible": True,
        },
    ]
    conn.execute(table.insert(), rows)

    # level 5（普通用户）：页面和组件部分可见
    rows_5 = [
        {
            "level": 5,
            "page_name": "home",
            "component_name": "post_card",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "home",
            "component_name": "tag_cloud",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "home",
            "component_name": "search_bar",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "explore",
            "component_name": "post_list",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "explore",
            "component_name": "filter_panel",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "create",
            "component_name": "post_editor",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "create",
            "component_name": "draft_list",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "assets",
            "component_name": "asset_manager",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "scheduler",
            "component_name": "task_list",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "profile",
            "component_name": "user_info",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "profile",
            "component_name": "settings_panel",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "posts",
            "component_name": "post_manager",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "creator",
            "component_name": "dashboard",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "tasks",
            "component_name": "task_center",
            "visible": True,
        },
        {
            "level": 5,
            "page_name": "tasks",
            "component_name": "crawler_config",
            "visible": False,
        },
        {
            "level": 5,
            "page_name": "tasks",
            "component_name": "cloud_training",
            "visible": False,
        },
        {
            "level": 5,
            "page_name": "console",
            "component_name": "console_dashboard",
            "visible": True,
        },
    ]
    conn.execute(table.insert(), rows_5)


def downgrade() -> None:
    op.drop_table("page_component_permissions")
