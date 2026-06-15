"""IP 封禁插件 —— 数据模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class IpBan(Base):
    """IP 封禁记录表。"""

    __tablename__ = "ip_bans"
    __table_args__ = (
        Index("ix_ip_bans_is_active_expires", "is_active", "expires_at"),
        Index("ix_ip_bans_ip_or_cidr", "ip_or_cidr"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_or_cidr: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ban_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="manual"
    )  # auto | manual
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    rule_id: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    banned_by: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class IpBanLog(Base):
    """IP 封禁操作日志表（封禁/解封操作记录）。"""

    __tablename__ = "ip_ban_logs"
    __table_args__ = (
        Index("ix_ip_ban_logs_ban_id", "ban_id"),
        Index("ix_ip_ban_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ban_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True, default=None
    )
    ip_or_cidr: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # ban | unban
    ban_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="manual"
    )  # auto | manual
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    operator: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AutoBanRuleConfig(Base):
    """自动封禁规则配置表。"""

    __tablename__ = "auto_ban_rule_configs"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True
    )  # rule_id: login_failure | high_4xx | rate_limit | geo_surge
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10
    )  # 触发阈值
    window_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300
    )  # 统计窗口（秒）
    ban_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )  # 封禁时长（分钟）
    description: Mapped[str | None] = mapped_column(
        String(256), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
