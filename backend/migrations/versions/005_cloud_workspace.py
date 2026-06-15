"""添加云工作空间表：数据集、代码仓库、制品

Revision ID: 005_cloud_workspace
Revises: 004_config_entries
Create Date: 2026-04-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import String, TypeDecorator


class _UUIDString(TypeDecorator):
    """跨数据库 UUID：PostgreSQL 用 UUID，SQLite 用 String(36)。"""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))


revision: str = "005_cloud_workspace"
down_revision: str | None = "004_config_entries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 创建 datasets 表 - 使用跨数据库兼容类型
    # SQLite 不支持 UUID 和 ARRAY，使用 String 替代
    op.create_table(
        "datasets",
        sa.Column("id", _UUIDString(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column(
            "source", sa.String(length=64), nullable=False, server_default="local"
        ),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tags", sa.Text(), nullable=True),  # JSON 序列化的标签数组
        sa.Column("config", sa.JSON(), nullable=True, server_default="{}"),
        sa.Column("created_by", _UUIDString(), nullable=False),
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
    )
    with op.batch_alter_table("datasets", schema=None) as batch_op:
        batch_op.create_index("ix_datasets_created_by", ["created_by"], unique=False)
        batch_op.create_index("ix_datasets_source", ["source"], unique=False)
        batch_op.create_index("ix_datasets_created_at", ["created_at"], unique=False)

    # 创建 code_repos 表
    op.create_table(
        "code_repos",
        sa.Column("id", _UUIDString(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("git_url", sa.String(length=1024), nullable=False),
        sa.Column(
            "git_branch", sa.String(length=256), nullable=False, server_default="main"
        ),
        sa.Column("git_token", sa.String(length=512), nullable=True),
        sa.Column("created_by", _UUIDString(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("code_repos", schema=None) as batch_op:
        batch_op.create_index("ix_code_repos_created_by", ["created_by"], unique=False)
        batch_op.create_index("ix_code_repos_git_url", ["git_url"], unique=True)

    # 创建 artifacts 表
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("""
            CREATE TABLE artifacts (
                id UUID NOT NULL,
                job_id UUID NOT NULL,
                name VARCHAR(256) NOT NULL,
                path VARCHAR(1024) NOT NULL,
                artifact_type VARCHAR(64) NOT NULL DEFAULT 'checkpoint',
                size_bytes INTEGER NOT NULL DEFAULT 0,
                storage_location VARCHAR(32) NOT NULL DEFAULT 'minio',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                PRIMARY KEY (id),
                FOREIGN KEY(job_id) REFERENCES training_jobs(id)
            )
        """)
    else:
        op.create_table(
            "artifacts",
            sa.Column("id", _UUIDString(), nullable=False),
            sa.Column("job_id", _UUIDString(), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("path", sa.String(length=1024), nullable=False),
            sa.Column(
                "artifact_type",
                sa.String(length=64),
                nullable=False,
                server_default="checkpoint",
            ),
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "storage_location",
                sa.String(length=32),
                nullable=False,
                server_default="minio",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["job_id"], ["training_jobs.id"]),
        )
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.create_index("ix_artifacts_job_id", ["job_id"], unique=False)
        batch_op.create_index(
            "ix_artifacts_artifact_type", ["artifact_type"], unique=False
        )
        batch_op.create_index("ix_artifacts_created_at", ["created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.drop_index("ix_artifacts_created_at")
        batch_op.drop_index("ix_artifacts_artifact_type")
        batch_op.drop_index("ix_artifacts_job_id")
    op.drop_table("artifacts")

    with op.batch_alter_table("code_repos", schema=None) as batch_op:
        batch_op.drop_index("ix_code_repos_git_url")
        batch_op.drop_index("ix_code_repos_created_by")
    op.drop_table("code_repos")

    with op.batch_alter_table("datasets", schema=None) as batch_op:
        batch_op.drop_index("ix_datasets_created_at")
        batch_op.drop_index("ix_datasets_source")
        batch_op.drop_index("ix_datasets_created_by")
    op.drop_table("datasets")
