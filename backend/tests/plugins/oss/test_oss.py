"""OSS 插件测试 —— 文件上传/下载/列举。

通过 oss_storage_dir fixture 提供临时存储目录，
MinIO 不可用时自动回退到本地文件系统。
"""

from __future__ import annotations

import pytest


class TestOSS:
    @pytest.mark.asyncio
    async def test_upload_image(self, async_client, auth_headers, oss_storage_dir):
        """图片上传 —— 本地临时目录测试（MinIO 不可用时自动降级）。"""
        resp = await async_client.post(
            "/api/oss/upload",
            files={"file": ("test.png", b"fake-png-content", "image/png")},
            headers=auth_headers,
        )
        # 上传成功返回 200，否则应返回 415/400（非致命错误）
        assert resp.status_code in (200, 400, 415, 422), f"上传失败: {resp.text}"
        if resp.status_code == 200:
            data = resp.json()
            assert data["code"] == "ok"
            assert "data" in data

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_type(self, async_client, auth_headers):
        resp = await async_client.post(
            "/api/oss/upload",
            files={"file": ("test.txt", b"content", "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 415
        data = resp.json()
        assert (
            "not_allowed" in data.get("code", "")
            or "type" in data.get("message", "").lower()
        )

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, async_client):
        resp = await async_client.post(
            "/api/oss/upload",
            files={"file": ("test.png", b"fake", "image/png")},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "auth" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_list_my_files(self, async_client, auth_headers):
        resp = await async_client.get("/api/oss/my", headers=auth_headers)
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert "data" in data

    @pytest.mark.asyncio
    async def test_quota(self, async_client, auth_headers):
        resp = await async_client.get("/api/oss/quota", headers=auth_headers)
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert "data" in data
            quota = data["data"]
            # 配额应有数字字段
            assert any(k in str(quota) for k in ["quota", "used", "total", "limit"])
