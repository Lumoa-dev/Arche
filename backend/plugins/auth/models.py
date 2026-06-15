"""认证插件 —— 用户数据模型。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base
from backend.core.models import HasSID


class User(Base, HasSID):
    """用户表：核心用户信息。"""

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    avatar: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, default=None
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    links: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
    badges: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    blog_quality_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # ── 软删除字段 ──
    # deletion_status: active | deleted_by_admin | user_requested_deletion
    deletion_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", server_default=text("'active'")
    )
    # 删号原因: violation（违规删号）| user_request（用户主动注销）
    deletion_reason: Mapped[str | None] = mapped_column(
        String(32), nullable=True, default=None
    )
    # 永久清理过期时间
    deletion_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    # 删号操作时间
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # ── 审计字段 ──
    login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    last_login_ip: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PreviousName(Base):
    """用户曾用名记录（改名时追加，只读历史）。"""

    __tablename__ = "user_previous_names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserSettings(Base):
    """用户设置表：常用设置抽为列，扩展配置放 extras JSON。"""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    default_post_permission: Mapped[str] = mapped_column(
        String(16), nullable=False, default="public"
    )
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="zh-CN")
    theme: Mapped[str] = mapped_column(String(16), nullable=False, default="auto")
    # 通知偏好
    notify_comment_reply: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    notify_like: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 隐私偏好
    privacy_show_online: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    privacy_show_login_history: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    privacy_show_badges: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    # 内容偏好
    default_post_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft"
    )
    auto_save_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    # 兜底 JSON：前端新增设置项塞这里，零迁移
    extras: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)


class LoginHistory(Base):
    """登录历史表：只追加，不修改。"""

    __tablename__ = "login_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    device_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, default=None
    )
    location: Mapped[str | None] = mapped_column(
        String(128), nullable=True, default=None
    )
    login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class KnownDevice(Base):
    """用户已知设备表。"""

    __tablename__ = "user_known_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    device_name: Mapped[str] = mapped_column(String(128), nullable=False)
    device_mac: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ViolationRecord(Base):
    """用户违规记录表。"""

    __tablename__ = "user_violations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    violation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    ban_duration: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # 小时，0=永久
    banned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    unbanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class UserToken(Base, HasSID):
    """用户 Token 记录表（持久化，用于设备管理和吊销）。"""

    __tablename__ = "user_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    device_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, default=None
    )
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NicknameBlacklist(Base):
    """昵称黑名单表（注册/改名时校验）。"""

    __tablename__ = "nickname_blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PageComponentPermission(Base):
    """页面组件权限映射表。

    按 Level 分组存储，定义每个 level 能看到的页面及页面内各组件的可见性。
    数据结构语义：
      { page_name: { component_name: visible (bool) } }
    若某页面下任一组件 visible=True，则该页面可访问；
    全部组件 visible=False 时，该页面不可访问。
    """

    __tablename__ = "page_component_permissions"
    __table_args__ = (
        UniqueConstraint(
            "level",
            "page_name",
            "component_name",
            name="uq_level_page_component",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    page_name: Mapped[str] = mapped_column(String(128), nullable=False)
    component_name: Mapped[str] = mapped_column(String(128), nullable=False)
    visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
