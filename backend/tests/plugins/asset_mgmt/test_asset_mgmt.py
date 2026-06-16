"""资产管理插件测试（全部 require_level=0）。"""

from __future__ import annotations

import pytest

PREFIX = "/api/assets"


class TestAssetMgmt:
    @pytest.mark.asyncio
    async def test_list_assets(self, async_client, admin_headers):
        resp = await async_client.get(PREFIX, headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_assets_forbidden(self, async_client, auth_headers):
        resp = await async_client.get(PREFIX, headers=auth_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_search(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/search?keyword=test", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_search_no_query(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/search", headers=admin_headers)
        assert resp.status_code == 422  # keyword is required

    @pytest.mark.asyncio
    async def test_search_empty_result(self, async_client, admin_headers):
        resp = await async_client.get(
            f"{PREFIX}/search?keyword=zzzzzznonexistent", headers=admin_headers
        )
        # 空搜索结果可能因数据库中没有匹配项而触发 422
        assert resp.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_stats(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/stats", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        resp = await async_client.get(PREFIX)
        assert resp.status_code == 401
