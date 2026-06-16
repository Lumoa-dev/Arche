"""add ip_ban and request_log tables

Revision ID: 3a8f72c9d5e1
Revises: 2a7e91b3f5c0
Create Date: 2026-06-16 18:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.

revision: str = "3a8f72c9d5e1"
down_revision: str | None = "2a7e91b3f5c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- ip_ban 插件 ---
    op.create_table(
        "ip_bans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ip_or_cidr", sa.String(length=64), nullable=False),
        sa.Column(
            "ban_type", sa.String(length=16), nullable=False, server_default="manual"
        ),
        sa.Column("reason", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("rule_id", sa.String(length=64), nullable=True),
        sa.Column("banned_by", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ip_bans_is_active_expires", "ip_bans", ["is_active", "expires_at"]
    )
    op.create_index("ix_ip_bans_ip_or_cidr", "ip_bans", ["ip_or_cidr"])

    op.create_table(
        "ip_ban_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ban_id", sa.Integer(), nullable=True),
        sa.Column("ip_or_cidr", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column(
            "ban_type", sa.String(length=16), nullable=False, server_default="manual"
        ),
        sa.Column("reason", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("operator", sa.String(length=64), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ip_ban_logs_ban_id", "ip_ban_logs", ["ban_id"])
    op.create_index("ix_ip_ban_logs_created_at", "ip_ban_logs", ["created_at"])

    op.create_table(
        "auto_ban_rule_configs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "threshold", sa.Integer(), nullable=False, server_default=sa.text("10")
        ),
        sa.Column(
            "window_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("300"),
        ),
        sa.Column(
            "ban_duration_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("30"),
        ),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- request_log 插件 ---
    op.create_table(
        "request_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sid", sa.String(length=64), nullable=False),  # HasSID mixin
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("referer", sa.String(length=1024), nullable=True),
        sa.Column(
            "duration_ms", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("isp", sa.String(length=64), nullable=True),
        sa.Column(
            "action", sa.String(length=32), nullable=False, server_default="other"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_logs_sid", "request_logs", ["sid"], unique=True)
    op.create_index("ix_request_logs_ip", "request_logs", ["ip"])
    op.create_index("ix_request_logs_user_id", "request_logs", ["user_id"])
    op.create_index("ix_request_logs_action", "request_logs", ["action"])
    op.create_index("ix_request_logs_created_at", "request_logs", ["created_at"])

    op.create_table(
        "ip_action_counters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("action_date", sa.Date(), nullable=False),
        sa.Column("hour", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ip", "action", "action_date", "hour", name="uq_ip_action_window"
        ),
    )
    op.create_index("ix_ip_action_counters_ip", "ip_action_counters", ["ip"])
    op.create_index("ix_ip_action_counters_action", "ip_action_counters", ["action"])


def downgrade() -> None:
    op.drop_table("ip_action_counters")
    op.drop_table("request_logs")
    op.drop_table("auto_ban_rule_configs")
    op.drop_table("ip_ban_logs")
    op.drop_table("ip_bans")
