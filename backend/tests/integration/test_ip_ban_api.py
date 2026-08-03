"""IP 封禁模块 API 集成测试。

测试真实 HTTP 请求-响应链路（HTTP → 中间件 → IpBanService → 真实数据库）。
不 mock IpBanService，使用真实 DB。
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.services import IpBanService
from backend.tests.conftest import patch_container_service


@pytest.fixture(autouse=True)
def real_ip_ban_service(db_container):
    """用真实 IpBanService 替换容器中的 mock 服务。"""
    ip_ban_service = IpBanService(db_container)
    patch_container_service(db_container, "ip_ban", ip_ban_service)


@pytest.mark.asyncio
class TestIpBanAPI:
    """IP 封禁 API 集成测试。"""

    async def test_list_bans_requires_auth(self, client):
        """未登录用户无法查询封禁列表。"""
        response = await client.get("/api/ip-ban/bans")
        assert response.status_code == 401

    async def test_ban_and_list(self, client, admin_headers):
        """手动封禁 IP 后应在封禁列表中出现。"""
        ban_resp = await client.post(
            "/api/ip-ban/bans",
            json={"ip_or_cidr": "10.0.0.55", "reason": "API test ban"},
            headers=admin_headers,
        )
        assert ban_resp.status_code == 200
        ban_data = ban_resp.json()
        assert ban_data["code"] == "ok"
        assert ban_data["data"]["ip_or_cidr"] == "10.0.0.55"

        list_resp = await client.get(
            "/api/ip-ban/bans",
            headers=admin_headers,
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["code"] == "ok"
        assert list_data["data"]["total"] >= 1

    async def test_ban_with_duration(self, client, admin_headers):
        """封禁带时长应返回 expires_at。"""
        response = await client.post(
            "/api/ip-ban/bans",
            json={
                "ip_or_cidr": "10.0.0.56",
                "reason": "temporary ban",
                "duration_minutes": 30,
            },
            headers=admin_headers,
        )
        data = response.json()
        assert data["data"]["expires_at"] is not None

    async def test_ban_invalid_ip_format(self, client, admin_headers):
        """无效 IP 格式应仍可封禁（封禁的是字符串本身）。"""
        response = await client.post(
            "/api/ip-ban/bans",
            json={"ip_or_cidr": "not-an-ip", "reason": "test"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["ip_or_cidr"] == "not-an-ip"

    async def test_unban(self, client, admin_headers):
        """解封 IP 后应标记为不活跃。"""
        ban_resp = await client.post(
            "/api/ip-ban/bans",
            json={"ip_or_cidr": "10.0.0.57", "reason": "to unban"},
            headers=admin_headers,
        )
        ban_id = ban_resp.json()["data"]["id"]

        unban_resp = await client.post(
            f"/api/ip-ban/bans/{ban_id}/unban",
            headers=admin_headers,
        )
        assert unban_resp.status_code == 200
        assert unban_resp.json()["data"]["is_active"] is False

    async def test_batch_unban(self, client, admin_headers):
        """批量解封多个 IP。"""
        b1 = await client.post(
            "/api/ip-ban/bans",
            json={"ip_or_cidr": "10.0.0.58", "reason": "batch1"},
            headers=admin_headers,
        )
        b2 = await client.post(
            "/api/ip-ban/bans",
            json={"ip_or_cidr": "10.0.0.59", "reason": "batch2"},
            headers=admin_headers,
        )

        batch_resp = await client.post(
            "/api/ip-ban/bans/batch-unban",
            json={
                "ban_ids": [
                    b1.json()["data"]["id"],
                    b2.json()["data"]["id"],
                ]
            },
            headers=admin_headers,
        )
        assert batch_resp.status_code == 200
        assert batch_resp.json()["data"]["count"] == 2

    async def test_get_ban_logs(self, client, admin_headers):
        """封禁操作日志应包含操作记录。"""
        await client.post(
            "/api/ip-ban/bans",
            json={"ip_or_cidr": "10.0.0.60", "reason": "log test"},
            headers=admin_headers,
        )

        logs_resp = await client.get(
            "/api/ip-ban/logs",
            headers=admin_headers,
        )
        assert logs_resp.status_code == 200
        logs_data = logs_resp.json()
        assert logs_data["code"] == "ok"
        assert logs_data["data"]["total"] >= 1

    async def test_get_rules_returns_defaults(self, client, admin_headers):
        """获取规则配置应返回默认规则。"""
        response = await client.get(
            "/api/ip-ban/rules",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        rule_ids = {r["id"] for r in data["data"]}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids

    async def test_update_rule(self, client, admin_headers):
        """更新规则配置应生效。"""
        # 先获取规则（触发默认规则创建）
        await client.get("/api/ip-ban/rules", headers=admin_headers)

        update_resp = await client.put(
            "/api/ip-ban/rules/login_failure",
            json={"threshold": 15},
            headers=admin_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["threshold"] == 15

    async def test_get_stats(self, client, admin_headers):
        """获取封禁统计信息。"""
        response = await client.get(
            "/api/ip-ban/stats",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "total_bans" in data
        assert "active_bans" in data
        assert "auto_bans" in data

    async def test_filter_bans_by_type(self, client, admin_headers):
        """按封禁类型过滤封禁列表。"""
        await client.post(
            "/api/ip-ban/bans",
            json={"ip_or_cidr": "10.0.0.61", "reason": "manual test"},
            headers=admin_headers,
        )

        response = await client.get(
            "/api/ip-ban/bans",
            params={"ban_type": "manual"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] >= 1
        for ban in data["list"]:
            assert ban["ban_type"] == "manual"

    async def test_filter_bans_by_keyword(self, client, admin_headers):
        """按关键词搜索封禁列表。"""
        await client.post(
            "/api/ip-ban/bans",
            json={"ip_or_cidr": "10.0.0.62", "reason": "keyword test"},
            headers=admin_headers,
        )

        response = await client.get(
            "/api/ip-ban/bans",
            params={"keyword": "10.0.0.62"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] >= 1