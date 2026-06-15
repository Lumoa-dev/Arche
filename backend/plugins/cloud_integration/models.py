"""云集成插件 —— 数据模型。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    func,
)
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base
from backend.core.models import HasSID


class JSON(TypeDecorator):
    """跨数据库 JSON 类型：PostgreSQL 使用 JSON，其他数据库使用 TEXT。"""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSON())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.loads(value) if isinstance(value, str) else value


class ArrayAsJSON(TypeDecorator):
    """跨数据库数组类型：PostgreSQL 使用 ARRAY，其他数据库使用 JSON TEXT。"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return (
            json.dumps(value, ensure_ascii=False)
            if isinstance(value, (list, tuple))
            else value
        )

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.loads(value) if isinstance(value, str) else value


class UUIDString(TypeDecorator):
    """跨数据库 UUID 类型：PostgreSQL 使用 UUID，其他数据库使用 String。"""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID

            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: Any, dialect):  # noqa: ARG002
        if value is None:
            return None
        return str(value) if isinstance(value, uuid.UUID) else value

    def process_result_value(self, value: Any, dialect):  # noqa: ARG002
        if value is None:
            return None
        return uuid.UUID(value) if isinstance(value, str) else value


class TrainingJob(Base, HasSID):
    """训练任务表。"""

    __tablename__ = "training_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    creator_id: Mapped[uuid.UUID] = mapped_column(UUIDString, nullable=False)
    model_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    logs_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    result_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    gpu_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    artifacts: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    artifact_verified: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)

    # 仓库与编排字段
    repo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    repo_branch: Mapped[str | None] = mapped_column(
        String(256), nullable=True, server_default="main"
    )
    repo_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    dataset_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    training_script: Mapped[str | None] = mapped_column(String(512), nullable=True)
    log_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    log_pattern: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        server_default=r"epoch\s+(\d+).*?loss\s*[:=]\s*([\d.]+)",
    )
    requirements_file: Mapped[str | None] = mapped_column(
        String(512), nullable=True, server_default="requirements.txt"
    )
    progress_info: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    orchestrator_step: Mapped[str | None] = mapped_column(
        String(64), nullable=True, server_default="idle"
    )
    orchestrator_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TrainingInstance(Base, HasSID):
    """训练实例表。"""

    __tablename__ = "training_instances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, ForeignKey("training_jobs.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="mock")
    provider_instance_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    instance_name: Mapped[str] = mapped_column(String(256), nullable=False)
    gpu_type: Mapped[str] = mapped_column(String(64), nullable=False)
    gpu_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ssh_host: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ssh_port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    ssh_user: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ssh_key_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ssh_password: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TrainingCost(Base, HasSID):
    """训练费用记录表。"""

    __tablename__ = "training_costs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, ForeignKey("training_jobs.id"), nullable=False
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, ForeignKey("training_instances.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    gpu_type: Mapped[str] = mapped_column(String(64), nullable=False)
    hourly_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TrainingTaskStep(Base, HasSID):
    """训练任务编排步骤记录表。"""

    __tablename__ = "training_task_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, ForeignKey("training_jobs.id"), nullable=False
    )
    step_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Dataset(Base, HasSID):
    """数据集表。"""

    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)  # 虚拟路径
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="local"
    )  # "local", "modelscope", "aliyun"
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[list[str] | None] = mapped_column(
        ArrayAsJSON, nullable=True, default=list
    )
    config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )  # { modelscope_id, token_key }
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDString, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CodeRepo(Base, HasSID):
    """代码仓库表。"""

    __tablename__ = "code_repos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    git_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    git_branch: Mapped[str] = mapped_column(
        String(256), nullable=False, server_default="main"
    )
    git_token: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )  # 加密存储
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDString, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Artifact(Base, HasSID):
    """训练产物表。"""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUIDString, ForeignKey("training_jobs.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)  # 虚拟路径
    artifact_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="checkpoint"
    )  # "checkpoint", "log", "config"
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_location: Mapped[str] = mapped_column(
        String(32), nullable=False, default="minio"
    )  # "minio" or "aliyun"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
