"""change blog_posts.introduction from JSON to Text

Revision ID: 012_introduction_to_text
Revises: 011_add_sid
Create Date: 2026-06-14 15:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012_introduction_to_text"
down_revision: str | None = "011_add_sid"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # blog_posts.introduction: JSON → Text
    # 保留现有数据，尝试将 JSON 数组转换为纯文本（如果数据库支持）
    with op.batch_alter_table("blog_posts", schema=None) as batch_op:
        batch_op.alter_column(
            "introduction",
            type_=sa.Text(),
            existing_type=sa.JSON(),
            nullable=True,
        )


def downgrade() -> None:
    # Text → JSON（生产回滚时谨慎，JSON 可能无法转换回数组）
    with op.batch_alter_table("blog_posts", schema=None) as batch_op:
        batch_op.alter_column(
            "introduction",
            type_=sa.JSON(),
            existing_type=sa.Text(),
            nullable=True,
        )
