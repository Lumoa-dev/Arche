"""爬虫插件 —— 数据模型：漫游爬虫抓取记录。"""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from backend.core.db import Base
from backend.core.models import HasSID


class CrawlRecord(Base, HasSID):
    """漫游爬虫抓取记录（用于资产聚合查询和前端展示）。"""

    __tablename__ = "crawl_records"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore[assignment]
    url = Column(String(2048), nullable=False)
    title = Column(String(512), nullable=True)
    content_type = Column(
        String(64), nullable=True
    )  # article/post/nav/ad/functional/other
    status_code = Column(Integer, default=0)
    source = Column(String(256), nullable=True)  # 来源域名/页面
    crawled_at = Column(DateTime(timezone=True), server_default=func.now())
    file_path = Column(String(1024), nullable=True)  # OSS 中文件路径
    file_size = Column(Integer, default=0)  # 文件大小（字节）
