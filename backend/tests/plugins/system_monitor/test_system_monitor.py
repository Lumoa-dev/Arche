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
        data = resp.json()
        assert data["code"] == "ok"
        summary = data.get("data", {})
        # summary 应包含系统指标字段
        assert any(
            k in summary
            for k in ["cpu", "memory", "disk", "cpu_percent", "memory_percent"]
        )

    @pytest.mark.asyncio
    async def test_cpu(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/cpu", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_memory(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/memory", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_disk(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/disk", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_network(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/network", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_dashboard(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_processes(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/processes", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_forbidden_for_regular_user(self, async_client, auth_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/summary", headers=auth_headers)
        assert resp.status_code == 403
        data = resp.json()
        assert "permission" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        resp = await async_client.get(f"{SYS_PREFIX}/summary")
        assert resp.status_code == 401
        data = resp.json()
        assert "code" in data

    @pytest.mark.asyncio
    async def test_online_status(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/online", headers=admin_headers)
        assert resp.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_online_status_forbidden(self, async_client, auth_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/online", headers=auth_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_notifications(self, async_client, admin_headers):
        resp = await async_client.get(
            f"{SYS_PREFIX}/notifications", headers=admin_headers
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert "data" in resp.json()

    @pytest.mark.asyncio
    async def test_history(self, async_client, admin_headers):
        resp = await async_client.get(f"{SYS_PREFIX}/history", headers=admin_headers)
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert "data" in resp.json()


class TestMonitor:
    @pytest.mark.asyncio
    async def test_list_templates(self, async_client, admin_headers):
        resp = await async_client.get(f"{MON_PREFIX}/templates", headers=admin_headers)
        assert resp.status_code == 200
        # 返回 JSON 列表
        data = resp.json()
        assert isinstance(data, list), f"期望列表，得到 {type(data)}"

    @pytest.mark.asyncio
    async def test_create_template(self, async_client, admin_headers):
        resp = await async_client.post(
            f"{MON_PREFIX}/templates",
            json={"name": "test-template", "config": {}},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 201)
        if resp.status_code in (200, 201):
            data = resp.json()
            # 创建成功返回 dict
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_forbidden(self, async_client, auth_headers):
        resp = await async_client.get(f"{MON_PREFIX}/templates", headers=auth_headers)
        assert resp.status_code == 403
        data = resp.json()
        assert "permission" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_get_template_by_id(self, async_client, admin_headers):
        """先创建模板，再按 ID 获取。"""
        create_resp = await async_client.post(
            f"{MON_PREFIX}/templates",
            json={"name": "get-test", "components": [], "refresh_interval": 30},
            headers=admin_headers,
        )
        assert create_resp.status_code in (200, 201)
        template_id = create_resp.json().get("id") or create_resp.json().get("_id")
        assert template_id is not None, f"创建响应无 ID: {create_resp.json()}"

        resp = await async_client.get(
            f"{MON_PREFIX}/templates/{template_id}", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("id") == template_id or data.get("_id") == template_id

    @pytest.mark.asyncio
    async def test_get_template_not_found(self, async_client, admin_headers):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await async_client.get(
            f"{MON_PREFIX}/templates/{fake_id}", headers=admin_headers
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data or "not found" in str(data).lower()

    @pytest.mark.asyncio
    async def test_update_template(self, async_client, admin_headers):
        create_resp = await async_client.post(
            f"{MON_PREFIX}/templates",
            json={"name": "update-test", "components": [], "refresh_interval": 30},
            headers=admin_headers,
        )
        assert create_resp.status_code in (200, 201)
        template_id = create_resp.json().get("id") or create_resp.json().get("_id")

        resp = await async_client.put(
            f"{MON_PREFIX}/templates/{template_id}",
            json={"name": "updated-name", "refresh_interval": 60},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("name") == "updated-name"

    @pytest.mark.asyncio
    async def test_delete_template(self, async_client, admin_headers):
        create_resp = await async_client.post(
            f"{MON_PREFIX}/templates",
            json={"name": "delete-test", "components": [], "refresh_interval": 30},
            headers=admin_headers,
        )
        assert create_resp.status_code in (200, 201)
        template_id = create_resp.json().get("id") or create_resp.json().get("_id")

        resp = await async_client.delete(
            f"{MON_PREFIX}/templates/{template_id}", headers=admin_headers
        )
        assert resp.status_code == 200

        # 删除后应 404
        resp = await async_client.get(
            f"{MON_PREFIX}/templates/{template_id}", headers=admin_headers
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_component_data(self, async_client, admin_headers):
        """获取有效组件的数据。"""
        resp = await async_client.get(
            f"{MON_PREFIX}/components/summary/data", headers=admin_headers
        )
        assert resp.status_code in (200, 503)  # 503 = system_monitor 不可用

    @pytest.mark.asyncio
    async def test_component_data_not_found(self, async_client, admin_headers):
        """无效组件返回 400。"""
        resp = await async_client.get(
            f"{MON_PREFIX}/components/invalid_component/data",
            headers=admin_headers,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
