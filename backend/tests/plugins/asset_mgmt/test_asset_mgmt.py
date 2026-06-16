"""资产管理插件测试（全部 require_level=0）。"""

from __future__ import annotations

import pytest

PREFIX = "/api/assets"


class TestAssetMgmt:
    @pytest.mark.asyncio
    async def test_list_assets(self, async_client, admin_headers):
        resp = await async_client.get(PREFIX, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert "data" in data

    @pytest.mark.asyncio
    async def test_list_assets_forbidden(self, async_client, auth_headers):
        resp = await async_client.get(PREFIX, headers=auth_headers)
        assert resp.status_code == 403
        data = resp.json()
        assert "permission" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_search(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/search?keyword=test", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert "items" in data.get("data", {})

    @pytest.mark.asyncio
    async def test_search_no_query(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/search", headers=admin_headers)
        assert resp.status_code == 422  # keyword is required

    @pytest.mark.asyncio
    async def test_search_empty_result(self, async_client, admin_headers):
        resp = await async_client.get(
            f"{PREFIX}/search?keyword=zzzzzznonexistent", headers=admin_headers
        )
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            assert resp.json()["data"]["items"] == []

    @pytest.mark.asyncio
    async def test_stats(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert "data" in data

    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        resp = await async_client.get(PREFIX)
        assert resp.status_code == 401
        data = resp.json()
        assert "auth" in data.get("code", "").lower()
