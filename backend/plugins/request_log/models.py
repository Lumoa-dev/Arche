"""请求日志模型 —— RequestLog 明细表 + IpActionCounter 聚合表。"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base
from backend.core.models import HasSID


class RequestLog(Base, HasSID):
    """请求日志明细。"""

    __tablename__ = "request_logs"
    __allow_unmapped__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ip: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    referer: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    isp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(
        String(32), nullable=False, default="other", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "ip": self.ip,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "user_agent": self.user_agent,
            "referer": self.referer,
            "duration_ms": self.duration_ms,
            "user_id": self.user_id,
            "region": self.region,
            "isp": self.isp,
            "action": self.action,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class IpActionCounter(Base):
    """IP 行为聚合计数。"""

    __tablename__ = "ip_action_counters"
    __allow_unmapped__ = True
    __table_args__ = (
        UniqueConstraint(
            "ip",
            "action",
            "action_date",
            "hour",
            name="uq_ip_action_window",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_date: Mapped[date] = mapped_column(Date, nullable=False)
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ip": self.ip,
            "action": self.action,
            "action_date": self.action_date.isoformat() if self.action_date else None,
            "hour": self.hour,
            "count": self.count,
        }
