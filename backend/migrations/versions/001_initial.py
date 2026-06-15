"""初始 schema

Revision ID: 001_initial
Revises:
Create Date: 2026-04-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# 版本标识符
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 幂等保护：如果 users 表已存在，说明该迁移已执行过（可能因 alembic_version
    # 记录丢失导致重复执行），直接跳过避免 "table already exists" 错误。
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    if "users" in inspector.get_table_names():
        return

    # === auth ===
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "blog_quality_level", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    # === blog ===
    op.create_table(
        "blog_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(256), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("required_level", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "blog_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "blog_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "blog_likes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_blog_likes_post_user"),
    )

    op.create_table(
        "blog_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "blog_post_tags",
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("post_id", "tag_id"),
    )

    # === crawler ===
    op.create_table(
        "crawl_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("content_type", sa.String(64), nullable=True),
        sa.Column("status_code", sa.Integer(), server_default="0"),
        sa.Column("source", sa.String(256), nullable=True),
        sa.Column(
            "crawled_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("file_path", sa.String(1024), nullable=True),
        sa.Column("file_size", sa.Integer(), server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    # === oss ===
    op.create_table(
        "oss_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", sa.String(64), nullable=True),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column(
            "storage_type", sa.String(32), nullable=False, server_default="local"
        ),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "last_accessed", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("oss_files") as batch_op:
        batch_op.create_index("ix_oss_files_owner_id", ["owner_id"], unique=False)
        batch_op.create_index("ix_oss_files_tenant_id", ["tenant_id"], unique=False)
        batch_op.create_index(
            "ix_oss_files_storage_type", ["storage_type"], unique=False
        )
        batch_op.create_index("ix_oss_files_created_at", ["created_at"], unique=False)
        batch_op.create_index(
            "ix_oss_files_owner_storage", ["owner_id", "storage_type"], unique=False
        )

    op.create_table(
        "user_oss_quotas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "quota_bytes",
            sa.BigInteger(),
            nullable=False,
            server_default=str(1 * 1024**3),
        ),
        sa.Column("speed_multiplier", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    with op.batch_alter_table("user_oss_quotas") as batch_op:
        batch_op.create_index(
            batch_op.f("ix_user_oss_quotas_user_id"), ["user_id"], unique=False
        )

    # === cloud_integration ===
    op.create_table(
        "training_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("logs_path", sa.String(512), nullable=True),
        sa.Column("result_path", sa.String(512), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("gpu_hours", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("artifacts", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column(
            "artifact_verified", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "training_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False, server_default="mock"),
        sa.Column("provider_instance_id", sa.String(256), nullable=True),
        sa.Column("instance_name", sa.String(256), nullable=False),
        sa.Column("gpu_type", sa.String(64), nullable=False),
        sa.Column("gpu_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ssh_host", sa.String(256), nullable=True),
        sa.Column("ssh_port", sa.Integer(), nullable=False, server_default="22"),
        sa.Column("ssh_user", sa.String(128), nullable=True),
        sa.Column("ssh_key_path", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["job_id"], ["training_jobs.id"]),
    )

    op.create_table(
        "training_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("gpu_type", sa.String(64), nullable=False),
        sa.Column("hourly_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("duration_hours", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="CNY"),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["job_id"], ["training_jobs.id"]),
        sa.ForeignKeyConstraint(["instance_id"], ["training_instances.id"]),
    )

    # === asset_mgmt ===
    op.create_table(
        "asset_index",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(512), nullable=False, server_default=""),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("asset_index") as batch_op:
        batch_op.create_index(
            "ix_asset_index_owner_type", ["owner_id", "asset_type"], unique=False
        )
        batch_op.create_index(
            "ix_asset_index_source", ["asset_type", "source_id"], unique=True
        )


def downgrade() -> None:
    op.drop_table("asset_index")
    op.drop_table("training_costs")
    op.drop_table("training_instances")
    op.drop_table("training_jobs")
    op.drop_table("user_oss_quotas")
    op.drop_table("oss_files")
    op.drop_table("crawl_records")
    op.drop_table("blog_post_tags")
    op.drop_table("blog_reports")
    op.drop_table("blog_likes")
    op.drop_table("blog_comments")
    op.drop_table("blog_tags")
    op.drop_table("blog_posts")
    op.drop_table("users")
