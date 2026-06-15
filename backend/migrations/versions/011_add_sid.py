"""add sid (Searchable ID) columns to all models

Revision ID: 011_add_sid
Revises: 010_add_user_soft_delete_fields
Create Date: 2026-06-07 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011_add_sid"
down_revision: str | None = "010_add_user_soft_delete_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ── 所有需要加 sid 的表 ──
_TABLES = [
    "users",
    "blog_posts",
    "blog_comments",
    "blog_likes",
    "blog_reports",
    "blog_tags",
    "blog_favorites",
    "blog_post_files",
    "oss_files",
    "user_oss_quotas",
    "asset_index",
    "training_jobs",
    "training_instances",
    "training_costs",
    "training_task_steps",
    "datasets",
    "code_repos",
    "artifacts",
    "crawl_records",
    "monitor_templates",
]


def _backfill_sid(table_name: str) -> None:
    """为存量数据回填唯一 sid。"""
    conn = op.get_bind()
    # 查出所有 sid IS NULL 的行，逐行分配唯一 sid
    meta = sa.MetaData()
    meta.reflect(bind=conn, only=[table_name])
    table = sa.Table(table_name, meta, autoload_with=conn)
    pk_col = table.primary_key.columns.keys()[0]
    rows = conn.execute(
        sa.text(f"SELECT {pk_col} FROM {table_name} WHERE sid IS NULL")
    ).fetchall()
    for (pk_val,) in rows:
        import uuid

        conn.execute(
            sa.text(f"UPDATE {table_name} SET sid = :sid WHERE {pk_col} = :pk"),
            {"sid": uuid.uuid4().hex, "pk": pk_val},
        )


def upgrade() -> None:
    for table_name in _TABLES:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            # 1. 先添加可空列
            batch_op.add_column(
                sa.Column(
                    "sid",
                    sa.String(length=64),
                    nullable=True,
                )
            )
        # 2. 回填唯一值（batch 外执行，避免 batch 模式下表名临时变化）
        _backfill_sid(table_name)
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            # 3. 收紧为 NOT NULL
            batch_op.alter_column(
                "sid", existing_type=sa.String(length=64), nullable=False
            )
            # 4. 创建唯一索引
            batch_op.create_index(f"ix_{table_name}_sid", ["sid"], unique=True)


def downgrade() -> None:
    for table_name in _TABLES:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_sid")
            batch_op.drop_column("sid")
