"""核心领域模型 —— 横切关注点模型，不属于任何插件。"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


def _default_sid() -> str:
    """生成全局唯一的 sid 占位值。业务代码应调用 generate_sid() 生成规范 SID。"""
    return uuid.uuid4().hex


class HasSID:
    """为模型添加 sid（Searchable ID）列的 mixin。

    sid 格式：{prefix}-[{category}]-{32位hex-每4位一组用横杠分隔}
    示例：asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000
    """

    sid: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, default=_default_sid
    )

    def generate_sid(self, prefix: str, category: str | None = None) -> None:
        """根据当前模型的 UUID id 自动生成 sid。"""
        from backend.core.uid import make_sid

        if self.id is None:  # type: ignore[has-type]
            self.id = uuid.uuid4()
        self.sid = make_sid(prefix, self.id, category)


class ConfigEntry(Base):
    """运行时配置条目，替代 .env 中的业务配置。"""

    __tablename__ = "config_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    group: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, server_default="general"
    )
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
