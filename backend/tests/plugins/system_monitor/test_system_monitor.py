"""系统监控 + 监控大屏插件测试（全部 require_level=0）。"""

from __future__ import annotations

import pytest

SYS_PREFIX = "/api/system"
MON_PREFIX = "/api/monitor"


class TestSystemMonitor:
    @pytest.mark.asyncio
    async def test_summary(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/summary", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cpu(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/cpu", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_memory(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/memory", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_disk(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/disk", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_network(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/network", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/dashboard", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_processes(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/processes", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_forbidden_for_regular_user(self, async_client, auth_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/summary", headers=auth_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        resp = await async_client.get(f"{SYS_PREFIX}/summary")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_online_status(self, async_client, admin_headers):
        """在线状态接口需要管理员权限。"""
        resp = await async_client.get(f"{SYS_PREFIX}/online", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_online_status_forbidden(self, async_client, auth_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/online", headers=auth_headers)
        assert resp.status_code == 403


class TestMonitor:
    @pytest.mark.asyncio
    async def test_list_templates(self, async_client, admin_headers):
        resp = await async_client.get(f"{MON_PREFIX}/templates", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_create_template(self, async_client, admin_headers):
        resp = await async_client.post(
            f"{MON_PREFIX}/templates",
            json={"name": "test-template", "config": {}},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_forbidden(self, async_client, auth_headers):
        resp = await async_client.get(f"{MON_PREFIX}/templates", headers=auth_headers)
        assert resp.status_code == 403
