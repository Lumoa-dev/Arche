"""为云训练表添加编排字段

Revision ID: 003_orchestration
Revises: 002_auth_and_roles
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003_orchestration"
down_revision = "002_add_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # training_jobs 新增编排字段
    with op.batch_alter_table("training_jobs") as batch_op:
        batch_op.add_column(sa.Column("repo_url", sa.String(1024), nullable=True))
        batch_op.add_column(
            sa.Column(
                "repo_branch",
                sa.String(256),
                nullable=True,
                server_default="main",
            )
        )
        batch_op.add_column(sa.Column("repo_token", sa.String(512), nullable=True))
        batch_op.add_column(
            sa.Column("dataset_config", sa.JSON(), nullable=True, server_default="{}")
        )
        batch_op.add_column(sa.Column("training_script", sa.String(512), nullable=True))
        batch_op.add_column(sa.Column("log_file_path", sa.String(512), nullable=True))
        batch_op.add_column(
            sa.Column(
                "log_pattern",
                sa.String(256),
                nullable=True,
                server_default=r"epoch\s+(\d+).*?loss\s*[:=]\s*([\d.]+)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "requirements_file",
                sa.String(512),
                nullable=True,
                server_default="requirements.txt",
            )
        )
        batch_op.add_column(
            sa.Column("progress_info", sa.JSON(), nullable=True, server_default="{}")
        )
        batch_op.add_column(
            sa.Column(
                "orchestrator_step",
                sa.String(64),
                nullable=True,
                server_default="idle",
            )
        )
        batch_op.add_column(sa.Column("orchestrator_error", sa.Text(), nullable=True))

    # training_instances 新增字段
    with op.batch_alter_table("training_instances") as batch_op:
        batch_op.add_column(sa.Column("ssh_password", sa.String(256), nullable=True))
        batch_op.add_column(
            sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True)
        )

    # 新建 training_task_steps 表
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("""
            CREATE TABLE training_task_steps (
                id UUID NOT NULL,
                job_id UUID NOT NULL,
                step_name VARCHAR(64) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                started_at TIMESTAMP WITH TIME ZONE,
                completed_at TIMESTAMP WITH TIME ZONE,
                error_message TEXT,
                result_data JSON DEFAULT '{}',
                retry_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                PRIMARY KEY (id),
                FOREIGN KEY(job_id) REFERENCES training_jobs(id)
            )
        """)
    else:
        op.create_table(
            "training_task_steps",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("step_name", sa.String(64), nullable=False),
            sa.Column(
                "status", sa.String(32), nullable=False, server_default="pending"
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("result_data", sa.JSON(), nullable=True, server_default="{}"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["job_id"], ["training_jobs.id"]),
        )
    op.create_index(
        "ix_training_task_steps_job_id",
        "training_task_steps",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_training_task_steps_job_id", table_name="training_task_steps")
    op.drop_table("training_task_steps")

    with op.batch_alter_table("training_instances") as batch_op:
        batch_op.drop_column("last_heartbeat")
        batch_op.drop_column("ssh_password")

    with op.batch_alter_table("training_jobs") as batch_op:
        batch_op.drop_column("orchestrator_error")
        batch_op.drop_column("orchestrator_step")
        batch_op.drop_column("progress_info")
        batch_op.drop_column("requirements_file")
        batch_op.drop_column("log_pattern")
        batch_op.drop_column("log_file_path")
        batch_op.drop_column("training_script")
        batch_op.drop_column("dataset_config")
        batch_op.drop_column("repo_token")
        batch_op.drop_column("repo_branch")
        batch_op.drop_column("repo_url")
