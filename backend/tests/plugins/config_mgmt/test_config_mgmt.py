"""配置管理插件测试。"""

from __future__ import annotations

import pytest

PREFIX = "/api/admin/config"


class TestConfigMgmt:
    @pytest.mark.asyncio
    async def test_list_configs(self, async_client, admin_headers):
        resp = await async_client.get(PREFIX, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert "data" in data
        configs = data["data"]
        # 应至少包含种子配置项
        assert len(configs) > 0

    @pytest.mark.asyncio
    async def test_requires_admin(self, async_client, auth_headers):
        resp = await async_client.get(PREFIX, headers=auth_headers)
        assert resp.status_code == 403
        data = resp.json()
        assert "permission" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_requires_auth(self, async_client):
        resp = await async_client.get(PREFIX)
        assert resp.status_code == 401
        data = resp.json()
        assert "code" in data
