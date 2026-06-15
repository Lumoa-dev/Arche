"""存储后端抽象 —— MinIO / 本地文件系统 / 阿里云 OSS 统一接口。"""

from __future__ import annotations

import io
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING

CHUNK_SIZE = 64 * 1024
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from minio import Minio as MinioClient

    from backend.plugins.oss.aliyun import CloudStorageService


class StorageBackend(ABC):
    """存储后端抽象接口。"""

    @abstractmethod
    async def upload_stream(
        self, key: str, stream: AsyncIterator[bytes], size: int
    ) -> None:
        """流式写入文件。"""
        ...

    @abstractmethod
    async def download(self, key: str) -> AsyncIterator[bytes]:
        """流式读取文件，返回字节生成器。"""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除文件。"""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查文件是否存在。"""
        ...

    @abstractmethod
    async def list(self, prefix: str = "") -> list[str]:
        """列出指定前缀的文件。"""
        ...

    @abstractmethod
    def get_disk_usage(self) -> int:
        """获取当前桶的总使用量（字节）。"""
        ...

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """返回后端类型标识，如 'minio' / 'aliyun'。"""
        ...


class MinIOBackend(StorageBackend):
    """本地 MinIO 对象存储后端（S3 兼容）。"""

    def __init__(self, client: MinioClient, bucket: str):
        self._client = client
        self._bucket = bucket

    def _ensure_bucket(self):
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    async def upload_stream(
        self,
        key: str,
        stream: AsyncIterator[bytes],
        size: int,  # noqa: ARG002
    ) -> None:
        self._ensure_bucket()

        # MinIO put_object 接受类文件对象，需要收集所有 chunk
        chunks = [chunk async for chunk in stream]
        data = b"".join(chunks)
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
        )

    async def download(self, key: str) -> AsyncIterator[bytes]:  # type: ignore
        response = self._client.get_object(self._bucket, key)
        try:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk
        finally:
            response.close()
            response.release_conn()

    async def delete(self, key: str) -> None:
        self._client.remove_object(self._bucket, key)

    async def exists(self, key: str) -> bool:
        try:
            self._client.stat_object(self._bucket, key)
            return True
        except Exception:
            return False

    async def list(self, prefix: str = "") -> list[str]:
        """列出指定前缀的文件。"""
        objects = self._client.list_objects(self._bucket, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects if obj.object_name is not None]

    def get_disk_usage(self) -> int:
        """统计桶中所有对象的总大小。"""
        total = 0
        for obj in self._client.list_objects(self._bucket, recursive=True):
            total += obj.size or 0
        return total

    @property
    def backend_type(self) -> str:
        return "minio"


class AliyunBackend(StorageBackend):
    """阿里云 OSS 存储后端（远程对象存储）。"""

    def __init__(self, cloud_service: CloudStorageService):
        self._cloud = cloud_service

    async def upload_stream(
        self,
        key: str,
        stream: AsyncIterator[bytes],
        size: int,  # noqa: ARG002
    ) -> None:
        chunks = [chunk async for chunk in stream]
        content = b"".join(chunks)
        await self._cloud.upload(key, content)

    async def upload_from_file(self, key: str, local_path: Path) -> str:
        """从本地文件上传到阿里云（用于冷热迁移）。"""
        return await self._cloud.upload(key, local_path)

    async def download(self, key: str) -> AsyncIterator[bytes]:  # type: ignore
        content = await self._cloud.download_bytes(key)
        for i in range(0, len(content), CHUNK_SIZE):
            yield content[i : i + CHUNK_SIZE]

    async def delete(self, key: str) -> None:
        await self._cloud.delete(key)

    async def exists(self, key: str) -> bool:
        return await self._cloud.object_exists(key)

    async def list(self, prefix: str = "") -> list[str]:
        """列出指定前缀的文件。"""
        result = await self._cloud.list_objects(prefix)
        return [str(key) for key in result if key is not None]

    def get_disk_usage(self) -> int:
        return 0

    @property
    def backend_type(self) -> str:
        return "aliyun"


class LocalBackend(StorageBackend):
    """本地文件系统存储后端（嵌入式，零依赖）。

    直接将文件存储在本地磁盘，无需任何外部服务（MinIO / 云 OSS）。
    适用于开发环境、单机部署或不方便单独部署 OSS 服务器场景。

    存储结构：base_path/prefix/key — 映射到文件系统目录。
    """

    def __init__(self, base_path: Path):
        self._base_path = base_path.resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """安全解析对象键为文件路径，防止路径穿越。"""
        clean = Path(key).as_posix().lstrip("/")
        resolved = (self._base_path / clean).resolve()
        if not str(resolved).startswith(str(self._base_path)):
            raise ValueError(f"非法路径（路径穿越）: {key}")
        return resolved

    async def upload_stream(
        self,
        key: str,
        stream: AsyncIterator[bytes],
        size: int,  # noqa: ARG002
    ) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        chunks = [chunk async for chunk in stream]
        path.write_bytes(b"".join(chunks))

    async def download(self, key: str) -> AsyncIterator[bytes]:  # type: ignore[override, misc]
        path = self._resolve(key)
        with open(path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()

    async def exists(self, key: str) -> bool:
        path = self._resolve(key)
        return path.exists()

    async def list(self, prefix: str = "") -> list[str]:
        base = self._base_path
        prefix_path = self._resolve(prefix) if prefix else base
        if not prefix_path.exists():
            return []
        if prefix_path.is_file():
            return [str(prefix_path.relative_to(base)).replace("\\", "/")]
        return [
            str(p.relative_to(base)).replace("\\", "/")
            for p in prefix_path.rglob("*")
            if p.is_file()
        ]

    def get_disk_usage(self) -> int:
        total = 0
        for p in self._base_path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
        return total

    @property
    def backend_type(self) -> str:
        return "local"
