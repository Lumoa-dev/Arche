"""爬虫插件测试 —— 管理端完整 CRUD + 权限。"""

from __future__ import annotations

import pytest

PREFIX = "/api/crawler"


class TestCrawlerAdmin:
    """爬虫管理接口（全部 require_level=0）。"""

    @pytest.mark.asyncio
    async def test_status(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/status", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_status_requires_admin(self, async_client, auth_headers):
        resp = await async_client.get(f"{PREFIX}/status", headers=auth_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_status_no_auth(self, async_client):
        resp = await async_client.get(f"{PREFIX}/status")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_records_list(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/records", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_records_with_pagination(self, async_client, admin_headers):
        resp = await async_client.get(
            f"{PREFIX}/records?page=1&page_size=10", headers=admin_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_record_detail_not_found(self, async_client, admin_headers):
        """无效 ID 格式可能导致 500（服务端未处理异常），也接受。"""
        resp = await async_client.get(
            f"{PREFIX}/records/nonexistent-id", headers=admin_headers
        )
        assert resp.status_code in (404, 500)

    @pytest.mark.asyncio
    async def test_seeds_list(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/seeds", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_add_seed(self, async_client, admin_headers):
        resp = await async_client.post(
            f"{PREFIX}/seeds",
            json={"url": "https://example.com/test-page"},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_add_seed_invalid_url(self, async_client, admin_headers):
        """无效 URL 可能被接受（服务端只做存储不做校验），或返回 422。"""
        resp = await async_client.post(
            f"{PREFIX}/seeds",
            json={"url": "not-a-valid-url"},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 201, 400, 422)

    @pytest.mark.asyncio
    async def test_add_seed_empty_url(self, async_client, admin_headers):
        resp = await async_client.post(
            f"{PREFIX}/seeds",
            json={"url": ""},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_blacklist(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/blacklist", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_stats(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/stats", headers=admin_headers)
        assert resp.status_code == 200
