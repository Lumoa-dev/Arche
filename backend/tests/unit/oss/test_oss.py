"""StorageService 行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现
- Mock 掉 MinIO/阿里云后端，只测业务逻辑
- 数据库交互用内存 SQLite
"""

from __future__ import annotations

import io
import uuid
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi import UploadFile

from backend.core.middleware import AppError, PermissionError
from backend.plugins.oss.services import StorageService


@contextmanager
def mock_minio_env():
    """Mock MinIO 客户端和后端，避免真实网络连接。"""
    with (
        patch("backend.plugins.oss.backends.MinIOBackend", new=MockMinIOBackend),
        patch("minio.Minio.list_buckets", return_value=[]),
    ):
        yield


# =============================================================================
# Mock 辅助（从 conftest 复制，避免 import 问题）
# =============================================================================


def mock_subprocess_success(stdout: bytes = b'{"ok": true}', stderr: bytes = b""):
    """创建成功的 subprocess mock。"""

    class MockProc:
        returncode = 0

        async def communicate(self, input=None):
            return stdout, stderr

        async def wait(self):
            return 0

    return MockProc()


def mock_subprocess_failure(exit_code: int = 1, stderr: bytes = b"error"):
    """创建失败的 subprocess mock。"""

    class MockProc:
        returncode = exit_code

        async def communicate(self, input=None):
            return b"", stderr

    return MockProc()


# =============================================================================
# Mock 辅助
# =============================================================================


class MockMinIOBackend:
    def __init__(self, *args, **kwargs):
        self.stored = {}

    @property
    def backend_type(self) -> str:
        return "minio"

    async def upload_stream(self, key, stream, total_bytes):
        data = b""
        async for chunk in stream:
            data += chunk
        self.stored[key] = data

    def download(self, key):
        async def _stream():
            yield self.stored.get(key, b"")

        return _stream()

    async def delete(self, key):
        if key in self.stored:
            del self.stored[key]


def _make_upload_file(filename: str, content: bytes, content_type: str) -> UploadFile:
    from starlette.datastructures import Headers

    headers = Headers({"content-type": content_type})
    file = UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=headers,
    )
    return file


# =============================================================================
# 文件名验证 行为测试
# =============================================================================


class TestFilenameValidation:
    """测试文件名验证行为。"""

    @pytest.mark.asyncio
    async def test_filename_with_path_traversal_raises_error(self, db_container):
        """包含 ../ 或 / 的文件名应被拒绝。"""
        service = StorageService(db_container)

        with mock_minio_env():
            # 路径穿越攻击
            bad_file = _make_upload_file(
                "../../../etc/passwd", b"bad content", "image/png"
            )

            with pytest.raises(AppError) as excinfo:
                await service.upload_file(bad_file, owner_id=uuid.uuid4(), user_level=5)

            assert excinfo.value.code == "invalid_filename"

    @pytest.mark.asyncio
    async def test_filename_with_backslash_raises_error(self, db_container):
        """包含 \\ 的文件名应被拒绝。"""
        service = StorageService(db_container)

        with mock_minio_env():
            bad_file = _make_upload_file("path\\to\\file", b"bad content", "image/png")

            with pytest.raises(AppError) as excinfo:
                await service.upload_file(bad_file, owner_id=uuid.uuid4(), user_level=5)

            assert excinfo.value.code == "invalid_filename"

    @pytest.mark.asyncio
    async def test_normal_filename_passes(self, db_container):
        """正常文件名应通过验证。"""
        service = StorageService(db_container)

        with mock_minio_env():
            good_file = _make_upload_file("image.png", b"pdf content", "image/png")

            result = await service.upload_file(
                good_file, owner_id=uuid.uuid4(), user_level=5
            )

            assert result["size"] == len(b"pdf content")


# =============================================================================
# MIME 类型验证 行为测试
# =============================================================================


class TestMimeValidation:
    """测试 MIME 类型白名单验证行为。"""

    @pytest.mark.asyncio
    async def test_allowed_mime_types_pass(self, db_container):
        """白名单内的 MIME 类型应通过。"""
        service = StorageService(db_container)

        allowed_types = [
            ("image.png", "image/png"),
            ("photo.jpg", "image/jpeg"),
            ("photo.jpg", "image/jpg"),
            ("photo.gif", "image/gif"),
            ("photo.webp", "image/webp"),
        ]

        with mock_minio_env():
            for filename, mime in allowed_types:
                file = _make_upload_file(filename, b"content", mime)
                result = await service.upload_file(
                    file, owner_id=uuid.uuid4(), user_level=5
                )
                assert result["mime_type"] == mime

    @pytest.mark.asyncio
    async def test_disallowed_mime_raises_error(self, db_container):
        """白名单外的 MIME 类型应被拒绝。"""
        service = StorageService(db_container)

        with mock_minio_env():
            # 可执行文件
            exe_file = _make_upload_file(
                "malware.exe", b"bad content", "application/x-msdownload"
            )

            with pytest.raises(AppError) as excinfo:
                await service.upload_file(exe_file, owner_id=uuid.uuid4(), user_level=5)

            assert excinfo.value.code == "file_type_not_allowed"
            assert excinfo.value.status_code == 415


# =============================================================================
# 上传 行为测试
# =============================================================================


class TestUpload:
    """测试上传行为。"""

    @pytest.mark.asyncio
    async def test_upload_creates_database_record(self, db_container):
        """上传成功应创建数据库记录。"""
        service = StorageService(db_container)
        user_id = uuid.uuid4()

        with mock_minio_env():
            file = _make_upload_file("test.png", b"hello world", "image/png")
            result = await service.upload_file(file, owner_id=user_id, user_level=5)

            assert "id" in result
            assert result["size"] == 11
            assert result["owner_id"] == str(user_id)
            assert result["storage_type"] == "minio"

    @pytest.mark.asyncio
    async def test_upload_creates_correct_object_key(self, db_container):
        """不同等级用户上传路径应不同。"""
        service = StorageService(db_container)
        p1_user = uuid.uuid4()
        p5_user = uuid.uuid4()

        with mock_minio_env():
            # P1 用户
            file1 = _make_upload_file("p1.png", b"p1 content", "image/png")
            r1 = await service.upload_file(file1, owner_id=p1_user, user_level=1)
            assert "p1" in r1["path"]

            # P5 用户
            file2 = _make_upload_file("p5.png", b"p5 content", "image/png")
            r2 = await service.upload_file(file2, owner_id=p5_user, user_level=5)
            assert "users" in r2["path"]

    @pytest.mark.asyncio
    async def test_ingest_bytes_for_system_data(self, db_container):
        """系统 ingest_bytes 接口应正常工作（无用户配额限制）。"""
        service = StorageService(db_container)

        with mock_minio_env():
            result = await service.ingest_bytes(
                content=b"system data",
                tenant_id="crawler",
                filename="data.bin",
                mime_type="application/octet-stream",
            )

            assert result["size"] == 11
            assert result["tenant_id"] == "crawler"


# =============================================================================
# 配额 行为测试
# =============================================================================


class TestQuota:
    """测试配额验证行为。"""

    @pytest.mark.asyncio
    async def test_p1_user_has_quota_check(self, db_container):
        """P1 用户上传应检查配额。"""
        service = StorageService(db_container)
        user_id = uuid.uuid4()

        with mock_minio_env():
            # 默认配额 1GB，小文件应成功
            small_file = _make_upload_file("small.txt", b"small content", "image/png")
            result = await service.upload_file(
                small_file, owner_id=user_id, user_level=1
            )
            assert result["size"] > 0

    @pytest.mark.asyncio
    async def test_p5_user_no_quota_check(self, db_container):
        """P5 用户没有配额检查（P1 才有）。"""
        service = StorageService(db_container)
        user_id = uuid.uuid4()

        with mock_minio_env():
            file = _make_upload_file("test.txt", b"content", "image/png")
            result = await service.upload_file(file, owner_id=user_id, user_level=5)
            assert result["size"] > 0

    @pytest.mark.asyncio
    async def test_get_used_bytes_sums_correctly(self, db_container):
        """已用空间计算应正确。"""
        service = StorageService(db_container)
        user_id = uuid.uuid4()

        with mock_minio_env():
            # 上传 3 个文件
            for i in range(3):
                file = _make_upload_file(f"{i}.txt", b"a" * 100, "image/png")
                await service.upload_file(file, owner_id=user_id, user_level=1)

            used = await service._get_used_bytes(user_id)
            assert used == 3 * 100

    @pytest.mark.asyncio
    async def test_file_count_correct(self, db_container):
        """文件数量计算应正确。"""
        service = StorageService(db_container)
        user_id = uuid.uuid4()

        with mock_minio_env():
            for i in range(5):
                file = _make_upload_file(f"{i}.txt", b"a", "image/png")
                await service.upload_file(file, owner_id=user_id, user_level=1)

            count = await service._file_count(user_id)
            assert count == 5


# =============================================================================
# 下载 行为测试
# =============================================================================


class TestDownload:
    """测试下载行为。"""

    @pytest.mark.asyncio
    async def test_download_nonexistent_file_raises_error(self, db_container):
        """下载不存在的文件应抛出 404。"""
        service = StorageService(db_container)

        with mock_minio_env():
            fake_id = uuid.uuid4()

            with pytest.raises(AppError) as excinfo:
                await service.download_file(
                    fake_id, requester_id=uuid.uuid4(), requester_level=5
                )

            assert excinfo.value.code == "file_not_found"
            assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_download_own_public_file_succeeds(self, db_container):
        """下载自己的公开文件应成功。"""
        service = StorageService(db_container)
        user_id = uuid.uuid4()

        with mock_minio_env():
            file = _make_upload_file("test.txt", b"hello", "image/png")
            uploaded = await service.upload_file(
                file, owner_id=user_id, user_level=5, is_private=False
            )

            _stream, info = await service.download_file(
                uuid.UUID(uploaded["id"]), requester_id=user_id, requester_level=5
            )

            assert info["id"] == uploaded["id"]

    @pytest.mark.asyncio
    async def test_download_others_private_file_raises_error(self, db_container):
        """下载别人的私有文件应抛出权限错误。"""
        service = StorageService(db_container)
        owner_id = uuid.uuid4()
        other_id = uuid.uuid4()

        with mock_minio_env():
            file = _make_upload_file("secret.txt", b"secret", "image/png")
            uploaded = await service.upload_file(
                file, owner_id=owner_id, user_level=5, is_private=True
            )

            with pytest.raises(PermissionError):
                await service.download_file(
                    uuid.UUID(uploaded["id"]),
                    requester_id=other_id,
                    requester_level=5,
                )

    @pytest.mark.asyncio
    async def test_admin_can_download_any_private_file(self, db_container):
        """P0 管理员可以下载任何私有文件。"""
        service = StorageService(db_container)
        owner_id = uuid.uuid4()
        admin_id = uuid.uuid4()

        with mock_minio_env():
            file = _make_upload_file("secret.txt", b"secret", "image/png")
            uploaded = await service.upload_file(
                file, owner_id=owner_id, user_level=5, is_private=True
            )

            # P0 管理员应该能下载
            _stream, info = await service.download_file(
                uuid.UUID(uploaded["id"]),
                requester_id=admin_id,
                requester_level=0,  # P0
            )

            assert info["id"] == uploaded["id"]


# =============================================================================
# 删除 行为测试
# =============================================================================


class TestDelete:
    """测试删除行为。"""

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file_raises_error(self, db_container):
        """删除不存在的文件应抛出 404。"""
        service = StorageService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.delete_file(
                uuid.uuid4(), requester_id=uuid.uuid4(), requester_level=5
            )

        assert excinfo.value.code == "file_not_found"

    @pytest.mark.asyncio
    async def test_delete_own_file_succeeds(self, db_container):
        """删除自己的文件应成功。"""
        service = StorageService(db_container)
        user_id = uuid.uuid4()

        with mock_minio_env():
            file = _make_upload_file("test.txt", b"content", "image/png")
            uploaded = await service.upload_file(file, owner_id=user_id, user_level=5)

            # 删除
            await service.delete_file(
                uuid.UUID(uploaded["id"]), requester_id=user_id, requester_level=5
            )

            # 删除后应找不到
            with pytest.raises(AppError):
                await service.download_file(
                    uuid.UUID(uploaded["id"]), requester_id=user_id, requester_level=5
                )

    @pytest.mark.asyncio
    async def test_delete_others_file_raises_error(self, db_container):
        """删除别人的文件应抛出权限错误。"""
        service = StorageService(db_container)
        owner_id = uuid.uuid4()
        other_id = uuid.uuid4()

        with mock_minio_env():
            file = _make_upload_file("test.txt", b"content", "image/png")
            uploaded = await service.upload_file(file, owner_id=owner_id, user_level=5)

            with pytest.raises(PermissionError):
                await service.delete_file(
                    uuid.UUID(uploaded["id"]),
                    requester_id=other_id,
                    requester_level=5,
                )

    @pytest.mark.asyncio
    async def test_admin_can_delete_any_file(self, db_container):
        """P0 管理员可以删除任何文件。"""
        service = StorageService(db_container)
        owner_id = uuid.uuid4()
        admin_id = uuid.uuid4()

        with mock_minio_env():
            file = _make_upload_file("test.txt", b"content", "image/png")
            uploaded = await service.upload_file(file, owner_id=owner_id, user_level=5)

            # P0 管理员应该能删除
            await service.delete_file(
                uuid.UUID(uploaded["id"]),
                requester_id=admin_id,
                requester_level=0,  # P0
            )


# =============================================================================
# 文件列表 行为测试
# =============================================================================


class TestListFiles:
    """测试文件列表行为。"""

    @pytest.mark.asyncio
    async def test_list_my_files_returns_only_own_files(self, db_container):
        """列表应只返回自己的文件。"""
        service = StorageService(db_container)
        user1 = uuid.uuid4()
        user2 = uuid.uuid4()

        with mock_minio_env():
            # user1 上传 3 个文件
            for i in range(3):
                file = _make_upload_file(f"u1_{i}.txt", b"a", "image/png")
                await service.upload_file(file, owner_id=user1, user_level=5)

            # user2 上传 2 个文件
            for i in range(2):
                file = _make_upload_file(f"u2_{i}.txt", b"a", "image/png")
                await service.upload_file(file, owner_id=user2, user_level=5)

            # user1 列表应该只有 3 个
            files1 = await service.list_my_files(user1)
            assert len(files1) == 3

            # user2 列表应该只有 2 个
            files2 = await service.list_my_files(user2)
            assert len(files2) == 2

    @pytest.mark.asyncio
    async def test_list_limit_and_offset_work(self, db_container):
        """分页 limit/offset 应正确工作。"""
        service = StorageService(db_container)
        user_id = uuid.uuid4()

        with mock_minio_env():
            for i in range(10):
                file = _make_upload_file(f"{i}.txt", b"a", "image/png")
                await service.upload_file(file, owner_id=user_id, user_level=5)

            # 第一页 5 个
            page1 = await service.list_my_files(user_id, limit=5, offset=0)
            assert len(page1) == 5

            # 第二页 5 个
            page2 = await service.list_my_files(user_id, limit=5, offset=5)
            assert len(page2) == 5
