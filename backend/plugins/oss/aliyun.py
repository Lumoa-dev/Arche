"""阿里云 OSS 云存储服务 —— 冷存储后端。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import oss2

from backend.core.middleware import AppError

if TYPE_CHECKING:
    from backend.core.container import ServiceContainer


class CloudStorageError(AppError):
    def __init__(
        self,
        message: str = "阿里云 OSS 操作失败",
        code: str = "cloud_storage_error",
        status_code: int = 500,
    ):
        super().__init__(message, code, status_code)


class CloudStorageService:
    """阿里云 OSS 操作封装，通过 asyncio.to_thread 包装同步 SDK。"""

    def __init__(self, container: ServiceContainer):
        config = container.get("config")
        endpoint = config.get_required("OSS_ENDPOINT")
        access_key_id = config.get_required("OSS_ACCESS_KEY_ID")
        access_key_secret = config.get_required("OSS_ACCESS_KEY_SECRET")
        bucket_name = config.get("OSS_BUCKET_NAME", "veil-cold")

        auth = oss2.Auth(access_key_id, access_key_secret)
        self._bucket = oss2.Bucket(auth, endpoint, bucket_name)

    async def upload(self, object_key: str, file_path: Path | bytes) -> str:
        """上传文件到阿里云 OSS。

        Args:
            object_key: OSS 对象键
            file_path: 本地文件路径或字节内容

        Returns:
            对象键
        """

        def _do_upload():
            if isinstance(file_path, Path):
                with open(file_path, "rb") as f:
                    self._bucket.put_object(object_key, f.read())
            else:
                self._bucket.put_object(object_key, file_path)
            return object_key

        try:
            return await asyncio.to_thread(_do_upload)
        except oss2.exceptions.OssError as e:
            raise CloudStorageError(f"阿里云 OSS 上传失败: {e}")  # noqa: B904

    async def download(self, object_key: str, local_path: Path) -> Path:
        """从阿里云 OSS 下载文件到本地。

        Args:
            object_key: OSS 对象键
            local_path: 本地保存路径

        Returns:
            本地文件路径
        """

        def _do_download():
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self._bucket.get_object_to_file(object_key, str(local_path))
            return local_path

        try:
            return await asyncio.to_thread(_do_download)
        except oss2.exceptions.NoSuchKey:
            raise AppError(  # noqa: B904
                "阿里云 OSS 文件不存在", code="cloud_file_not_found", status_code=404
            )
        except oss2.exceptions.OssError as e:
            raise CloudStorageError(f"阿里云 OSS 下载失败: {e}")  # noqa: B904

    async def download_bytes(self, object_key: str) -> bytes:
        """从阿里云 OSS 下载文件为字节。"""

        def _do_download():
            result = self._bucket.get_object(object_key)
            data = result.read()
            if isinstance(data, bytes):
                return data
            if isinstance(data, str):
                return data.encode("utf-8")
            return bytes(data)

        try:
            return await asyncio.to_thread(_do_download)
        except oss2.exceptions.NoSuchKey:
            raise AppError(  # noqa: B904
                "阿里云 OSS 文件不存在", code="cloud_file_not_found", status_code=404
            )
        except oss2.exceptions.OssError as e:
            raise CloudStorageError(f"阿里云 OSS 下载失败: {e}")  # noqa: B904

    async def delete(self, object_key: str) -> None:
        """从阿里云 OSS 删除文件。"""

        def _do_delete():
            self._bucket.delete_object(object_key)

        try:
            await asyncio.to_thread(_do_delete)
        except oss2.exceptions.OssError as e:
            raise CloudStorageError(f"阿里云 OSS 删除失败: {e}")  # noqa: B904

    async def object_exists(self, object_key: str) -> bool:
        """检查 OSS 对象是否存在（HEAD 请求，不下载内容）。"""

        def _do_check():
            try:
                self._bucket.head_object(object_key)
                return True
            except oss2.exceptions.NoSuchKey:
                return False
            except oss2.exceptions.OssError:
                return False

        return await asyncio.to_thread(_do_check)

    async def list_objects(self, prefix: str = "") -> list[str]:
        """列举指定前缀的所有对象键。"""

        def _do_list():
            keys = []
            for obj in oss2.ObjectIterator(self._bucket, prefix=prefix):
                keys.append(obj.key)
            return keys

        try:
            return await asyncio.to_thread(_do_list)
        except oss2.exceptions.OssError as e:
            raise CloudStorageError(f"阿里云 OSS 列举失败: {e}")  # noqa: B904
