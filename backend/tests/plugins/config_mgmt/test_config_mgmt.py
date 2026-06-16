"""配置管理插件测试。"""

from __future__ import annotations

import pytest

PREFIX = "/api/admin/config"


class TestConfigMgmt:
    @pytest.mark.asyncio
    async def test_list_configs(self, async_client, admin_headers):
        resp = await async_client.get(PREFIX, headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_requires_admin(self, async_client, auth_headers):
        resp = await async_client.get(PREFIX, headers=auth_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_requires_auth(self, async_client):
        resp = await async_client.get(PREFIX)
        assert resp.status_code == 401
