"""对象存储插件 —— 对象存储服务：MinIO（本地）/ 阿里云 OSS（远程）统一接口。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import urllib3
from fastapi import UploadFile
from sqlalchemy import func, select, true

from backend.core.middleware import AppError, PermissionError

if TYPE_CHECKING:
    from backend.core.container import ServiceContainer

logger = logging.getLogger(__name__)

# === 常量 ===
DEFAULT_QUOTA_BYTES = 500 * 1024**2  # 500MB 默认配额（对应 P5 普通用户）
DEFAULT_MAX_FILE_SIZE = 10 * 1024**2  # 10MB 单文件上限
CHUNK_SIZE = 64 * 1024  # 64KB 分块
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/webp",
}


def _get_default_quota_for_level(user_level: int) -> int:
    """根据用户等级返回默认配额字节数。"""
    level_quotas = {
        0: 0,  # P0 管理员：不限（0 表示不限制）
        1: 5 * 1024**3,  # P1: 5GB
        2: 5 * 1024**3,  # P2: 5GB
        3: 2 * 1024**3,  # P3: 2GB
        4: 1 * 1024**3,  # P4: 1GB
        5: 500 * 1024**2,  # P5: 500MB
    }
    return level_quotas.get(user_level, 500 * 1024**2)


class StorageError(AppError):
    def __init__(
        self,
        message: str = "存储操作失败",
        code: str = "storage_error",
        status_code: int = 500,
    ):
        super().__init__(message, code, status_code)


def _key(*parts: str) -> str:
    """拼接对象键。"""
    return "/".join(p.strip("/") for p in parts if p)


class StorageService:
    """对象存储服务：MinIO（本地）/ 阿里云 OSS（远程）统一接口。"""

    def __init__(self, container: ServiceContainer):
        self.container = container
        db = container.get("db")
        self.session_factory = db["session_factory"]
        self._rate_limiter = container.get("oss_rate_limiter")
        self._minio = None
        self._aliyun = None
        self._local = None
        self._unified_storage = None

    # --- 后端初始化 ---

    def _get_minio(self):
        """获取 MinIO 对象存储后端。连接失败时自动回退到本地文件系统。"""
        if self._minio is not None:
            return self._minio
        if getattr(self, "_minio_failed", False):
            return self._get_local()

        try:
            from minio import Minio

            from backend.plugins.oss.backends import MinIOBackend

            config = self.container.get("config")
            http_client = urllib3.PoolManager(
                timeout=urllib3.Timeout(connect=5, read=10)
            )
            client = Minio(
                config.get("MINIO_ENDPOINT", "localhost:9000"),
                access_key=config.get("MINIO_ROOT_USER", "veiladmin"),
                secret_key=config.get("MINIO_ROOT_PASSWORD", "veiladmin123"),
                secure=config.get("MINIO_SECURE", "false").lower() == "true",
                http_client=http_client,
            )
            # list_buckets 发起真实网络请求，验证连接可用性
            client.list_buckets()
            self._minio = MinIOBackend(client, bucket="veil-oss")
            return self._minio
        except Exception as e:
            logger.warning(f"[OSS] MinIO 不可用，回退到本地文件存储: {e}")
            self._minio_failed = True
            return self._get_local()

    def _get_aliyun(self):
        """获取阿里云 OSS 后端（冷存储/VIP）。"""
        if self._aliyun is not None:
            return self._aliyun

        config = self.container.get("config")
        if config.get("OSS_ACCESS_KEY_ID") and config.get("OSS_ACCESS_KEY_SECRET"):
            from backend.plugins.oss.aliyun import CloudStorageService
            from backend.plugins.oss.backends import AliyunBackend

            cloud = CloudStorageService(self.container)
            self._aliyun = AliyunBackend(cloud)
        return self._aliyun

    def _get_local(self):
        """获取本地文件系统存储后端（嵌入式，无需任何外部服务）。"""
        if self._local is not None:
            return self._local

        from backend.plugins.oss.backends import LocalBackend

        config = self.container.get("config")
        storage_dir = config.get("OSS_STORAGE_DIR", "data/storage")
        base_path = Path(storage_dir)
        self._local = LocalBackend(base_path)
        logger.info(f"[OSS] 本地文件存储已就绪: {base_path.resolve()}")
        return self._local

    def get_unified_storage(self) -> UnifiedStorage:
        """获取统一存储服务（OSS无感层）。"""
        if self._unified_storage is None:
            self._unified_storage = UnifiedStorage(self)  # type: ignore[assignment]
        return self._unified_storage  # type: ignore[return-value]

    # --- 配额 ---

    async def _get_quota_bytes(self, user_id: uuid.UUID, user_level: int = 5) -> int:
        from backend.plugins.oss.models import UserOSSQuota

        # P0 管理员不限
        if user_level == 0:
            return -1

        async with self.session_factory() as session:
            result = await session.execute(
                select(UserOSSQuota).where(UserOSSQuota.user_id == user_id)
            )
            record = result.scalar_one_or_none()
            if record:
                return record.quota_bytes
            return _get_default_quota_for_level(user_level)

    async def _get_used_bytes(self, user_id: uuid.UUID) -> int:
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            result = await session.execute(
                select(func.sum(OSSFile.size)).where(OSSFile.owner_id == user_id)
            )
            return result.scalar() or 0

    async def _check_quota(
        self, user_id: uuid.UUID, additional_bytes: int, user_level: int = 5
    ) -> None:
        quota = await self._get_quota_bytes(user_id, user_level=user_level)
        # -1 表示不限
        if quota == -1:
            return
        used = await self._get_used_bytes(user_id)
        if used + additional_bytes > quota:
            raise AppError(
                f"存储空间不足（已用 {used / 1024**3:.2f}GB / 配额 {quota / 1024**3:.2f}GB）",  # noqa: E501
                code="quota_exceeded",
                status_code=413,
            )

    async def _file_count(self, user_id: uuid.UUID) -> int:
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            result = await session.execute(
                select(func.count(OSSFile.id)).where(OSSFile.owner_id == user_id)
            )
            return result.scalar() or 0

    # --- 验证 ---

    def _validate_mime(self, file: UploadFile) -> None:
        mime = file.content_type or ""
        if mime and mime not in ALLOWED_MIME_TYPES:
            raise AppError(
                f"不支持的文件类型: {mime}",
                code="file_type_not_allowed",
                status_code=415,
            )

    def _validate_filename(self, filename: str) -> None:
        if ".." in filename or "/" in filename or "\\" in filename:
            raise AppError(
                "文件名包含非法字符", code="invalid_filename", status_code=400
            )

    # --- 上传：程序化写入（爬虫/系统数据） ---

    async def ingest_bytes(
        self,
        content: bytes,
        tenant_id: str,
        filename: str,
        mime_type: str = "application/octet-stream",
        is_private: bool = True,
    ) -> dict:
        from backend.plugins.oss.models import OSSFile

        key = _key(tenant_id, filename)
        backend = self._get_minio()

        async def stream():
            yield content

        await backend.upload_stream(key, stream(), len(content))

        async with self.session_factory() as session:
            oss_file = OSSFile(
                tenant_id=tenant_id,
                path=key,
                size=len(content),
                mime_type=mime_type,
                storage_type=backend.backend_type,
                is_private=is_private,
            )
            session.add(oss_file)
            await session.commit()
            await session.refresh(oss_file)

        return self._to_dict(oss_file)

    # --- 上传：用户文件 ---

    async def upload_file(
        self,
        file: UploadFile,
        owner_id: uuid.UUID,
        user_level: int = 5,
        is_private: bool = False,
    ) -> dict:
        from backend.plugins.oss.models import OSSFile

        self._validate_mime(file)
        filename = file.filename or "unnamed"
        self._validate_filename(filename)

        key = _key("p1" if user_level == 1 else "users", str(owner_id), filename)

        # 上传前先做一次配额检查
        await self._check_quota(owner_id, CHUNK_SIZE, user_level=user_level)

        total_bytes = 0

        async def byte_stream() -> AsyncIterator[bytes]:
            nonlocal total_bytes
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes + CHUNK_SIZE > DEFAULT_MAX_FILE_SIZE:
                    raise AppError(
                        f"文件大小超过限制 ({DEFAULT_MAX_FILE_SIZE // 1024 // 1024}MB)",
                        code="file_too_large",
                        status_code=413,
                    )
                # 所有用户执行配额检查
                quota = await self._get_quota_bytes(owner_id, user_level=user_level)
                if quota != -1:  # -1 表示不限
                    used = await self._get_used_bytes(owner_id)
                    if used + total_bytes > quota:
                        raise AppError(
                            "超出存储配额", code="quota_exceeded", status_code=413
                        )
                if self._rate_limiter:
                    await self._rate_limiter.consume(owner_id, len(chunk))
                yield chunk

        await self._get_minio().upload_stream(key, byte_stream(), total_bytes)

        backend = self._get_minio()

        async with self.session_factory() as session:
            oss_file = OSSFile(
                owner_id=owner_id,
                path=key,
                size=total_bytes,
                mime_type=file.content_type,
                storage_type=backend.backend_type,
                is_private=is_private,
            )
            session.add(oss_file)
            await session.commit()
            await session.refresh(oss_file)

        return self._to_dict(oss_file)

    # --- 外部租户写入 ---

    async def external_upload(self, file: UploadFile, tenant_id: str) -> dict:
        from backend.plugins.oss.models import OSSFile

        filename = file.filename or "unnamed"
        self._validate_filename(filename)
        key = _key("external", tenant_id, filename)

        total_bytes = 0

        async def byte_stream() -> AsyncIterator[bytes]:
            nonlocal total_bytes
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                yield chunk

        backend = self._get_minio()
        await backend.upload_stream(key, byte_stream(), 0)

        async with self.session_factory() as session:
            oss_file = OSSFile(
                tenant_id=tenant_id,
                path=key,
                size=total_bytes,
                mime_type=file.content_type,
                storage_type=backend.backend_type,
            )
            session.add(oss_file)
            await session.commit()
            await session.refresh(oss_file)

        return self._to_dict(oss_file)

    # --- 下载 ---

    async def download_file(
        self,
        file_id: uuid.UUID,
        requester_id: uuid.UUID | None,
        requester_level: int = 5,
    ) -> tuple[AsyncIterator[bytes], dict]:
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            result = await session.execute(select(OSSFile).where(OSSFile.id == file_id))
            oss_file = result.scalar_one_or_none()
            if not oss_file:
                raise AppError("文件不存在", code="file_not_found", status_code=404)
            if (
                oss_file.is_private
                and oss_file.owner_id != requester_id
                and requester_level > 0
            ):
                raise PermissionError("无权访问该文件")
            oss_file.last_accessed = datetime.now(timezone.utc)
            await session.commit()

        if oss_file.storage_type == "aliyun":
            aliyun = self._get_aliyun()
            if not aliyun:
                raise StorageError("阿里云 OSS 未配置")
            return aliyun.download(oss_file.path), self._to_dict(oss_file)

        return self._get_minio().download(oss_file.path), self._to_dict(oss_file)

    # --- 删除 ---

    async def delete_file(
        self,
        file_id: uuid.UUID,
        requester_id: uuid.UUID,
        requester_level: int = 5,
    ) -> None:
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            result = await session.execute(select(OSSFile).where(OSSFile.id == file_id))
            oss_file = result.scalar_one_or_none()
            if not oss_file:
                raise AppError("文件不存在", code="file_not_found", status_code=404)
            if oss_file.owner_id != requester_id and requester_level > 0:
                raise PermissionError("无权删除该文件")

            if oss_file.storage_type == "aliyun":
                aliyun = self._get_aliyun()
                if not aliyun:
                    raise StorageError("阿里云 OSS 未配置")
                await aliyun.delete(oss_file.path)
            else:
                await self._get_minio().delete(oss_file.path)

            await session.delete(oss_file)
            await session.commit()

    # --- 列表 ---

    async def list_my_files(
        self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            result = await session.execute(
                select(OSSFile)
                .where(OSSFile.owner_id == user_id)
                .order_by(OSSFile.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return [self._to_dict(f) for f in result.scalars().all()]

    async def list_external_files(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            result = await session.execute(
                select(OSSFile)
                .where(OSSFile.tenant_id == tenant_id)
                .order_by(OSSFile.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return [self._to_dict(f) for f in result.scalars().all()]

    # --- 冷热迁移 ---

    async def evict_cold_files(self, days: int = 7) -> int:
        """MinIO → 阿里云。"""
        from backend.plugins.oss.models import OSSFile

        aliyun = self._get_aliyun()
        if not aliyun:
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        async with self.session_factory() as session:
            result = await session.execute(
                select(OSSFile).where(
                    OSSFile.storage_type == "minio",
                    OSSFile.last_accessed < cutoff,
                    OSSFile.is_private,
                )
            )
            files = result.scalars().all()

        migrated = 0
        failed = 0
        for oss_file in files:
            try:
                minio = self._get_minio()
                if not await minio.exists(oss_file.path):
                    continue

                # MinIO → 阿里云
                chunks = [c async for c in minio.download(oss_file.path)]
                content = b"".join(chunks)

                async def content_stream() -> AsyncIterator[bytes]:
                    yield content  # noqa: B023

                await aliyun.upload_stream(
                    oss_file.path, content_stream(), len(content)
                )

                async with self.session_factory() as session:
                    result = await session.execute(
                        select(OSSFile).where(OSSFile.id == oss_file.id)
                    )
                    record = result.scalar_one()
                    record.storage_type = "aliyun"
                    await session.commit()

                await minio.delete(oss_file.path)
                migrated += 1
            except Exception as e:
                logger.warning(f"[OSS] 冷迁移失败 file_id={oss_file.id}: {e}")
                failed += 1

        if failed:
            logger.info(f"[OSS] 冷迁移: {migrated} 成功, {failed} 失败")
        return migrated

    # --- 统计 ---

    async def get_p1_quota_used(self, user_id: uuid.UUID) -> dict:
        quota_bytes = await self._get_quota_bytes(user_id)
        used = await self._get_used_bytes(user_id)
        return {
            "used_bytes": used,
            "used_gb": round(used / 1024**3, 2),
            "quota_bytes": quota_bytes,
            "quota_gb": round(quota_bytes / 1024**3, 2),
            "usage_percent": round(used / quota_bytes * 100, 1)
            if quota_bytes > 0
            else 0,
            "file_count": await self._file_count(user_id),
        }

    async def get_user_storage_used(self, user_id: uuid.UUID) -> dict:
        return {
            "total_bytes": await self._get_used_bytes(user_id),
            "file_count": await self._file_count(user_id),
        }

    async def get_storage_stats(self, user_id: uuid.UUID | None = None) -> dict:
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            filter_clause = OSSFile.owner_id == user_id if user_id else true()
            total_files = (
                await session.execute(
                    select(func.count(OSSFile.id)).where(filter_clause)
                )
            ).scalar() or 0
            total_size = (
                await session.execute(
                    select(func.sum(OSSFile.size)).where(filter_clause)
                )
            ).scalar() or 0
            type_result = await session.execute(
                select(
                    OSSFile.storage_type, func.count(OSSFile.id), func.sum(OSSFile.size)
                )
                .where(filter_clause)
                .group_by(OSSFile.storage_type)
            )
            by_type = {
                r[0]: {"count": r[1], "size": r[2] or 0} for r in type_result.all()
            }

        return {
            "total_files": total_files,
            "total_size": total_size,
            "by_type": by_type,
        }

    # --- 管理员 ---

    async def update_user_quota(
        self,
        user_id: uuid.UUID,
        quota_bytes: int | None = None,
        speed_multiplier: float | None = None,
    ) -> dict:
        from backend.plugins.oss.models import UserOSSQuota

        async with self.session_factory() as session:
            result = await session.execute(
                select(UserOSSQuota).where(UserOSSQuota.user_id == user_id)
            )
            record = result.scalar_one_or_none()
            if record:
                if quota_bytes is not None:
                    record.quota_bytes = quota_bytes
                if speed_multiplier is not None:
                    record.speed_multiplier = speed_multiplier
            else:
                record = UserOSSQuota(
                    user_id=user_id,
                    quota_bytes=quota_bytes or DEFAULT_QUOTA_BYTES,
                    speed_multiplier=speed_multiplier or 1.0,
                )
                session.add(record)
            await session.commit()
            await session.refresh(record)

            if speed_multiplier is not None and self._rate_limiter:
                self._rate_limiter.set_user_multiplier(user_id, speed_multiplier)

            return {
                "user_id": str(user_id),
                "quota_bytes": record.quota_bytes,
                "speed_multiplier": record.speed_multiplier,
            }

    async def list_user_quotas(self, limit: int = 50, offset: int = 0) -> dict:
        from backend.plugins.oss.models import OSSFile, UserOSSQuota

        async with self.session_factory() as session:
            result = await session.execute(
                select(UserOSSQuota)
                .order_by(UserOSSQuota.user_id)
                .limit(limit)
                .offset(offset)
            )
            quotas = result.scalars().all()
            items = []
            for q in quotas:
                used = (
                    await session.execute(
                        select(func.sum(OSSFile.size)).where(
                            OSSFile.owner_id == q.user_id
                        )
                    )
                ).scalar() or 0
                items.append(
                    {
                        "user_id": str(q.user_id),
                        "quota_bytes": q.quota_bytes,
                        "speed_multiplier": q.speed_multiplier,
                        "used_bytes": used,
                        "usage_percent": round(used / q.quota_bytes * 100, 1)
                        if q.quota_bytes > 0
                        else 0,
                    }
                )
            total = (
                await session.execute(select(func.count(UserOSSQuota.id)))
            ).scalar() or 0
            return {"items": items, "total": total}

    async def admin_list_files(
        self, user_id: uuid.UUID | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            query = (
                select(OSSFile)
                .order_by(OSSFile.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            if user_id:
                query = query.where(OSSFile.owner_id == user_id)
            return [
                self._to_dict(f) for f in (await session.execute(query)).scalars().all()
            ]

    async def admin_delete_file(self, file_id: uuid.UUID) -> None:
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            result = await session.execute(select(OSSFile).where(OSSFile.id == file_id))
            oss_file = result.scalar_one_or_none()
            if not oss_file:
                raise AppError("文件不存在", code="file_not_found", status_code=404)

            if oss_file.storage_type == "aliyun":
                aliyun = self._get_aliyun()
                if aliyun:
                    await aliyun.delete(oss_file.path)
            else:
                await self._get_minio().delete(oss_file.path)

            await session.delete(oss_file)
            await session.commit()

    async def get_admin_stats(self) -> dict:
        from backend.plugins.oss.models import OSSFile, UserOSSQuota

        async with self.session_factory() as session:
            total_files = (
                await session.execute(select(func.count(OSSFile.id)))
            ).scalar() or 0
            total_size = (
                await session.execute(select(func.sum(OSSFile.size)))
            ).scalar() or 0
            total_users = (
                await session.execute(select(func.count(UserOSSQuota.id)))
            ).scalar() or 0
            type_result = await session.execute(
                select(
                    OSSFile.storage_type, func.count(OSSFile.id), func.sum(OSSFile.size)
                ).group_by(OSSFile.storage_type)
            )
            by_type = {
                r[0]: {"count": r[1], "size": r[2] or 0} for r in type_result.all()
            }
            try:
                minio_usage = self._get_minio().get_disk_usage()
            except Exception:
                minio_usage = None

        return {
            "total_files": total_files,
            "total_size": total_size,
            "total_users": total_users,
            "by_type": by_type,
            "minio_usage": minio_usage,
        }

    async def get_top_users_by_storage(self, limit: int = 20) -> list[dict]:
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            result = await session.execute(
                select(
                    OSSFile.owner_id,
                    func.sum(OSSFile.size).label("total"),
                    func.count(OSSFile.id).label("count"),
                )
                .where(OSSFile.owner_id.isnot(None))
                .group_by(OSSFile.owner_id)
                .order_by(func.sum(OSSFile.size).desc())
                .limit(limit)
            )
            return [
                {"user_id": str(r[0]), "total_bytes": r[1] or 0, "file_count": r[2]}
                for r in result.all()
            ]

    # --- 序列化 ---

    def _to_dict(self, oss_file) -> dict:
        def _dt(dt):
            if dt is None:
                return None
            return dt.isoformat() if not isinstance(dt, str) else dt

        return {
            "id": str(oss_file.id),
            "owner_id": str(oss_file.owner_id) if oss_file.owner_id else None,
            "tenant_id": oss_file.tenant_id,
            "path": oss_file.path,
            "size": oss_file.size,
            "mime_type": oss_file.mime_type,
            "storage_type": oss_file.storage_type,
            "is_private": oss_file.is_private,
            "created_at": _dt(oss_file.created_at),
            "last_accessed": _dt(oss_file.last_accessed),
        }


class UnifiedStorage:
    """
    OSS无感层：虚拟路径系统，用户不感知实际存储位置。
    读写逻辑：
    - 写入：先写MinIO（热存储）→ 后台异步同步到阿里云（冷存储）
    - 读取：先查MinIO → 不存在则从阿里云拉回，同时写入MinIO缓存
    - 删除：同时删除MinIO和阿里云
    - 列表：合并两个存储的结果，去重，按最近访问时间排序
    """

    def __init__(self, storage_service: StorageService):
        self.storage = storage_service
        self._minio = storage_service._get_minio()
        self._aliyun = storage_service._get_aliyun()
        self._sync_queue = asyncio.Queue(maxsize=1000)  # type: ignore[var-annotated]
        self._sync_worker_task = None
        self._start_sync_worker()

    def _start_sync_worker(self):
        """启动后台同步 worker，处理MinIO→阿里云的异步同步。"""
        if self._sync_worker_task is None or self._sync_worker_task.done():
            self._sync_worker_task = asyncio.create_task(self._sync_worker())

    async def _sync_worker(self):
        """后台同步任务：处理队列中的同步请求。"""
        while True:
            try:
                virtual_path, content = await self._sync_queue.get()
                if self._aliyun:
                    try:

                        async def stream():
                            yield content  # noqa: B023

                        await self._aliyun.upload_stream(
                            virtual_path, stream(), len(content)
                        )
                        logger.debug(f"[UnifiedStorage] 同步成功: {virtual_path}")
                    except Exception as e:
                        logger.warning(f"[UnifiedStorage] 同步失败 {virtual_path}: {e}")
                        # 失败后重试最多3次
                        await asyncio.sleep(1)
                        try:

                            async def stream():
                                yield content  # noqa: B023

                            await self._aliyun.upload_stream(
                                virtual_path, stream(), len(content)
                            )
                        except Exception as e2:
                            logger.error(
                                f"[UnifiedStorage] 同步最终失败 {virtual_path}: {e2}"
                            )
                self._sync_queue.task_done()
            except Exception as e:
                logger.error(f"[UnifiedStorage] 同步worker异常: {e}")
                await asyncio.sleep(5)  # 异常后等待5秒再继续

    async def put(
        self, virtual_path: str, content: bytes, sync_to_aliyun: bool = True
    ) -> None:
        """
        写入文件到虚拟路径。
        :param virtual_path: 虚拟路径，如 "datasets/my_data/v1/train.csv"
        :param content: 文件内容字节
        :param sync_to_aliyun: 是否异步同步到阿里云（默认是）
        """

        # 1. 先写入MinIO热存储
        async def stream():
            yield content

        await self._minio.upload_stream(virtual_path, stream(), len(content))

        # 2. 异步同步到阿里云冷存储
        if sync_to_aliyun and self._aliyun:
            try:
                self._sync_queue.put_nowait((virtual_path, content))
            except asyncio.QueueFull:
                logger.warning(
                    f"[UnifiedStorage] 同步队列已满，跳过同步: {virtual_path}"
                )

    async def get(self, virtual_path: str) -> bytes:
        """
        从虚拟路径读取文件。
        :param virtual_path: 虚拟路径
        :return: 文件内容字节
        """
        # 1. 先查MinIO热存储
        try:
            chunks = [c async for c in self._minio.download(virtual_path)]
            return b"".join(chunks)
        except Exception:
            logger.debug(
                f"[UnifiedStorage] MinIO不存在，尝试从阿里云拉取: {virtual_path}"
            )

        # 2. MinIO不存在，尝试从阿里云拉取
        if not self._aliyun:
            raise StorageError(f"文件不存在: {virtual_path}")

        try:
            chunks = [c async for c in self._aliyun.download(virtual_path)]
            content = b"".join(chunks)

            # 拉取成功后，写入MinIO缓存
            async def stream():
                yield content

            await self._minio.upload_stream(virtual_path, stream(), len(content))

            return content
        except Exception:
            raise StorageError(f"文件不存在: {virtual_path}")  # noqa: B904

    async def delete(self, virtual_path: str) -> None:
        """
        删除虚拟路径的文件，同时删除MinIO和阿里云。
        :param virtual_path: 虚拟路径
        """
        # 删除MinIO中的文件（忽略不存在错误）
        with contextlib.suppress(Exception):
            await self._minio.delete(virtual_path)

        # 删除阿里云中的文件（忽略不存在错误）
        if self._aliyun:
            with contextlib.suppress(Exception):
                await self._aliyun.delete(virtual_path)

    async def exists(self, virtual_path: str) -> bool:
        """
        检查虚拟路径的文件是否存在（任意存储中存在即返回True）。
        :param virtual_path: 虚拟路径
        :return: 是否存在
        """
        # 先查MinIO
        if await self._minio.exists(virtual_path):
            return True

        # 再查阿里云
        return bool(self._aliyun and await self._aliyun.exists(virtual_path))

    async def list(self, prefix: str = "") -> list[str]:
        """
        列出指定前缀的所有文件，合并MinIO和阿里云的结果并去重。
        :param prefix: 路径前缀
        :return: 文件路径列表
        """
        # 获取MinIO的文件列表
        minio_files = await self._minio.list(prefix)

        # 获取阿里云的文件列表
        aliyun_files = []
        if self._aliyun:
            try:
                aliyun_files = await self._aliyun.list(prefix)
            except Exception as e:
                logger.warning(f"[UnifiedStorage] 获取阿里云文件列表失败: {e}")

        # 合并去重
        all_files = list(set(minio_files + aliyun_files))
        all_files.sort()

        return all_files

    async def get_disk_usage(self) -> dict:
        """
        获取存储使用统计。
        :return: 统计信息
        """
        minio_usage = self._minio.get_disk_usage()
        aliyun_usage = self._aliyun.get_disk_usage() if self._aliyun else 0

        return {
            "minio_bytes": minio_usage,
            "aliyun_bytes": aliyun_usage,
            "total_bytes": minio_usage + aliyun_usage,
            "sync_queue_size": self._sync_queue.qsize(),
        }
