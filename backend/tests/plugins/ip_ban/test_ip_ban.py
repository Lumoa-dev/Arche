"""IP 封禁插件测试（管理员功能）。"""

from __future__ import annotations

import pytest

PREFIX = "/api/ip-ban"


class TestIpBan:
    @pytest.mark.asyncio
    async def test_list_bans(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/bans", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ban_logs(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/logs", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ban_rules(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/rules", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ban_stats(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/stats", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_requires_auth(self, async_client):
        resp = await async_client.get(f"{PREFIX}/bans")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_regular_user_forbidden(self, async_client, auth_headers):
        resp = await async_client.get(f"{PREFIX}/bans", headers=auth_headers)
        assert resp.status_code == 403
