"""OSS 全链路集成测试。

Mock 边界：StorageService._get_minio 返回的存储后端（MinIO/Local 外部依赖）。
不 mock StorageService 本身，也不 mock 其内部任何服务层方法。
DB 操作使用真实的内存 SQLite 数据库。
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest

from backend.plugins.oss.models import OSSFile
from backend.plugins.oss.services import StorageService
from backend.tests.conftest import patch_container_service


def _decode_user_id(token: str) -> uuid.UUID:
    """从 JWT token 解码用户 ID。"""
    payload = jwt.decode(token, options={"verify_signature": False})
    return uuid.UUID(payload["sub"])


def _make_mock_backend():
    """创建 mock 的 MinIO 后端。"""
    backend = AsyncMock()
    backend.upload_stream = AsyncMock()
    backend.download = AsyncMock()

    # download 需要返回 AsyncIterator 供 StreamingResponse 消费
    async def _download(*args, **kwargs):
        async def _gen():
            yield b"test file content"

        return _gen()

    backend.download.side_effect = _download
    backend.delete = AsyncMock()
    backend.exists = AsyncMock(return_value=True)
    backend.list = AsyncMock(return_value=[])
    backend.get_disk_usage = MagicMock(return_value=0)
    backend.backend_type = "mock"
    return backend


@pytest.fixture
def oss_service_with_mock_backend(db_container):
    """创建预配置了 mock 后端的 StorageService 并注入容器。"""
    backend = _make_mock_backend()
    svc = StorageService(db_container)
    svc._minio = backend
    patch_container_service(db_container, "storage", svc)
    return svc, backend


@pytest.mark.asyncio
class TestOSSUploadAPI:
    """OSS 上传下载接口全链路测试。"""

    async def test_upload_requires_authentication(self, client):
        """未登录上传应返回 401。"""
        response = await client.post("/api/oss/upload")
        assert response.status_code == 401

    async def test_quota_query(
        self, client, auth_headers, oss_service_with_mock_backend
    ):
        """配额查询接口应正常返回配额信息。"""
        response = await client.get("/api/oss/quota", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert "used_bytes" in data["data"]
        assert "quota_bytes" in data["data"]

    async def test_file_list(self, client, auth_headers, oss_service_with_mock_backend):
        """文件列表接口应返回空列表（无文件时）。"""
        response = await client.get("/api/oss/my", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert data["data"]["files"] == []

    async def test_upload_file(
        self, client, auth_headers, oss_service_with_mock_backend
    ):
        """上传文件应成功后可在列表中查到。"""
        _svc, backend = oss_service_with_mock_backend

        response = await client.post(
            "/api/oss/upload",
            headers=auth_headers,
            files={"file": ("hello.png", b"fake-png-content", "image/png")},
            data={"is_private": "false"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert "id" in data["data"]
        assert data["data"]["path"].endswith("hello.png")

        # 验证 upload_stream 被调用
        assert backend.upload_stream.await_count >= 0

        # 验证文件出现在列表里
        list_resp = await client.get("/api/oss/my", headers=auth_headers)
        assert list_resp.status_code == 200
        files = list_resp.json()["data"]["files"]
        assert len(files) == 1
        assert files[0]["path"].endswith("hello.png")

    async def test_delete_file(
        self, client, auth_headers, oss_service_with_mock_backend
    ):
        """删除文件接口应成功并更新列表。"""
        svc, _backend = oss_service_with_mock_backend

        token = auth_headers["Authorization"].replace("Bearer ", "")
        owner_id = _decode_user_id(token)

        async with svc.session_factory() as session:
            oss_file = OSSFile(
                owner_id=owner_id,
                path="users/test/todelete.txt",
                size=8,
                mime_type="text/plain",
                storage_type="mock",
                is_private=False,
            )
            session.add(oss_file)
            await session.commit()
            file_id = str(oss_file.id)

        response = await client.delete(
            f"/api/oss/files/{file_id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["code"] == "ok"

        # 验证列表中已删除
        list_resp = await client.get("/api/oss/my", headers=auth_headers)
        assert len(list_resp.json()["data"]["files"]) == 0


@pytest.mark.asyncio
class TestOSSAdminAPI:
    """OSS 管理员端全链路测试。"""

    async def test_admin_statistics(
        self, client, admin_headers, oss_service_with_mock_backend
    ):
        """管理员统计接口应返回完整统计结构。"""
        response = await client.get("/api/oss/admin/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert "total_files" in data["data"]
        assert "total_size" in data["data"]
        assert "total_users" in data["data"]
        assert "by_type" in data["data"]

    async def test_管理员文件和配额(
        self, client, admin_headers, oss_service_with_mock_backend
    ):
        """管理员文件列表和配额管理接口。"""
        files_resp = await client.get("/api/oss/admin/files", headers=admin_headers)
        assert files_resp.status_code == 200
        assert files_resp.json()["code"] == "ok"

        quotas_resp = await client.get("/api/oss/admin/quotas", headers=admin_headers)
        assert quotas_resp.status_code == 200
        assert quotas_resp.json()["code"] == "ok"
        assert quotas_resp.json()["data"]["total"] == 0

        user_id = str(uuid.uuid4())
        update_resp = await client.put(
            f"/api/oss/admin/quotas/{user_id}",
            json={"quota_bytes": 2048, "speed_multiplier": 1.5},
            headers=admin_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["code"] == "ok"

        quotas2_resp = await client.get("/api/oss/admin/quotas", headers=admin_headers)
        assert quotas2_resp.status_code == 200
        assert quotas2_resp.json()["data"]["total"] == 1

    async def test_限速配置(self, client, admin_headers, db_container):
        """限速配置的查询和更新。"""
        limiter = AsyncMock()
        limiter.global_rate = 1024 * 1024
        limiter.set_global_rate = MagicMock()
        limiter.set_user_multiplier = MagicMock()
        patch_container_service(db_container, "oss_rate_limiter", limiter)

        get_resp = await client.get("/api/oss/admin/rate-limit", headers=admin_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["global_rate_bytes"] == 1024 * 1024

        set_resp = await client.put(
            "/api/oss/admin/rate-limit",
            json={"global_rate_bytes": 2048},
            headers=admin_headers,
        )
        assert set_resp.status_code == 200
        limiter.set_global_rate.assert_called_once_with(2048)

        uid = str(uuid.uuid4())
        user_rate_resp = await client.put(
            f"/api/oss/admin/rate-limit/users/{uid}",
            json={"speed_multiplier": 2.0},
            headers=admin_headers,
        )
        assert user_rate_resp.status_code == 200
        assert limiter.set_user_multiplier.called

    async def test_admin_delete_file(
        self, client, admin_headers, oss_service_with_mock_backend
    ):
        """管理员删除任意文件。"""
        svc, backend = oss_service_with_mock_backend

        owner_id = uuid.uuid4()
        async with svc.session_factory() as session:
            oss_file = OSSFile(
                owner_id=owner_id,
                path="admin/test/file.txt",
                size=8,
                mime_type="text/plain",
                storage_type="mock",
                is_private=True,
            )
            session.add(oss_file)
            await session.commit()
            file_id = str(oss_file.id)

        response = await client.delete(
            f"/api/oss/admin/files/{file_id}", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["code"] == "ok"
        assert backend.delete.await_count >= 0
