"""博客插件 —— 数据模型。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base
from backend.core.models import HasSID


class BlogPost(Base, HasSID):
    """博客文章表（metadata + 引言 + 段落索引）。"""

    __tablename__ = "blog_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    cover_url: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, default=None
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    required_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    # 副标题（JSON 数组，如 ["副标题1", "副标题2"]）
    subtitles: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
    # 引言区域（结构化 JSON，KV 数组，如 [{"key": "摘要", "value": "..."}]）
    introduction: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
    # 段落顺序（JSON 数组，如 ["PID_001", "PID_002"]，控制渲染顺序）
    paragraph_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    # 功能标记
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    category_id: Mapped[str | None] = mapped_column(
        String(32), nullable=True, default=None
    )
    # 反范式计数（避免频繁 COUNT 查询）
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class BlogParagraph(Base, HasSID):
    """博客段落表（每段一行，通过 paragraph_ids 控制顺序）。"""

    __tablename__ = "blog_paragraphs"

    pid: Mapped[str] = mapped_column(String(64), primary_key=True)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heading: Mapped[str | None] = mapped_column(
        String(256), nullable=True, default=None
    )
    media_url: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, default=None
    )
    caption: Mapped[str | None] = mapped_column(
        String(512), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BlogComment(Base, HasSID):
    """博客评论表。"""

    __tablename__ = "blog_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # 关联到段落 PID（null 表示全局评论，非段落级评论）
    paragraph_pid: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="visible"
    )  # visible / hidden / deleted
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BlogLike(Base, HasSID):
    """博客点赞表。"""

    __tablename__ = "blog_likes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_blog_likes_post_user"),
    )


class BlogReport(Base, HasSID):
    """博客举报表。"""

    __tablename__ = "blog_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reporter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BlogTag(Base, HasSID):
    """博客标签表。"""

    __tablename__ = "blog_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    color: Mapped[str | None] = mapped_column(
        String(8), nullable=True, default=None
    )  # 十六进制，如 #FF6B6B
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BlogPostTag(Base):
    """帖子-标签关联表（多对多）。"""

    __tablename__ = "blog_post_tags"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, nullable=False
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, nullable=False
    )


class BlogFavorite(Base, HasSID):
    """博客收藏表。"""

    __tablename__ = "blog_favorites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_blog_favorites_post_user"),
    )


class PostFile(Base, HasSID):
    """帖子关联文件表：记录帖子临时上传的文件及其引用状态。"""

    __tablename__ = "blog_post_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    oss_file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    file_index: Mapped[int] = mapped_column(Integer, nullable=False)  # #N 编号
    # temp: 临时上传，persisted: 已持久化（被引用），orphaned: 未被引用待清理
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="temp")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ModerationRecord(Base, HasSID):
    """审核记录表：追踪内容审核全流程。"""

    __tablename__ = "moderation_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    target_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # post / comment / user
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    submitter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, default=None
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )  # pending / approved / rejected
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class ChangeLog(Base, HasSID):
    """变更审计日志表：记录字段级别的改前/改后。"""

    __tablename__ = "change_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    target_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # post / comment / user
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # create / update / delete / review
    changes: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )  # {"field": {"old": "", "new": ""}}
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
