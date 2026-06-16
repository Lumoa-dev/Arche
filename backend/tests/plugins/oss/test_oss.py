"""OSS 插件测试 —— 文件上传/下载/列举。"""

from __future__ import annotations

import pytest


class TestOSS:
    @pytest.mark.asyncio
    async def test_upload_image(self, async_client, auth_headers):
        minimal_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
            b"\x00\x00\x00\xff\xff\x03\x00\x00\x00\x01\x18\x00\x00\x00\x00\x00IEND"
            b"\xaeB`\x82"
        )
        resp = await async_client.post(
            "/api/oss/upload",
            files={"file": ("test.png", minimal_png, "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_type(self, async_client, auth_headers):
        resp = await async_client.post(
            "/api/oss/upload",
            files={"file": ("test.txt", b"content", "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 415

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, async_client):
        resp = await async_client.post(
            "/api/oss/upload",
            files={"file": ("test.png", b"fake", "image/png")},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_my_files(self, async_client, auth_headers):
        resp = await async_client.get("/api/oss/my", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_quota(self, async_client, auth_headers):
        resp = await async_client.get("/api/oss/quota", headers=auth_headers)
        assert resp.status_code == 200
