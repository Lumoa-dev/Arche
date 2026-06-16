"""请求日志插件测试（管理员功能）。"""

from __future__ import annotations

import pytest

PREFIX = "/api/request-log"


class TestRequestLog:
    @pytest.mark.asyncio
    async def test_query(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/query", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_top_ips(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/top-ips", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_trend(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/trend", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_requires_auth(self, async_client):
        resp = await async_client.get(f"{PREFIX}/query")
        assert resp.status_code == 401
