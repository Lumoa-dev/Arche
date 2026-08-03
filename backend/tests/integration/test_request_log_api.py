"""请求日志模块 API 集成测试。

测试真实 HTTP 请求-响应链路（HTTP → RequestLogMiddleware → 真实数据库）。
注意：请求日志的中间件在 test_app 中已自动注册。
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestRequestLogQueryAPI:
    """请求日志查询 API 集成测试。"""

    async def test_query_requires_auth(self, client):
        """未登录用户无法查询请求日志。"""
        response = await client.get("/api/request-log/query")
        assert response.status_code == 401

    async def test_query_returns_empty_initially(self, client, admin_headers):
        """初始状态查询请求日志应返回空列表。"""
        response = await client.get(
            "/api/request-log/query",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_query_with_date_filter(self, client, admin_headers):
        """按日期范围过滤请求日志。"""
        response = await client.get(
            "/api/request-log/query",
            params={
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_query_invalid_date_format(self, client, admin_headers):
        """无效日期格式应返回 400。"""
        response = await client.get(
            "/api/request-log/query",
            params={"start_date": "not-a-date"},
            headers=admin_headers,
        )
        assert response.status_code == 400

    async def test_query_pagination(self, client, admin_headers):
        """分页参数应正确传递。"""
        response = await client.get(
            "/api/request-log/query",
            params={"page": 1, "page_size": 5},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    async def test_top_ips_requires_auth(self, client):
        """未登录用户无法获取 TOP IP。"""
        response = await client.get("/api/request-log/top-ips")
        assert response.status_code == 401

    async def test_top_ips_returns_empty_list(self, client, admin_headers):
        """初始状态 TOP IP 应返回空列表。"""
        response = await client.get(
            "/api/request-log/top-ips",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_top_ips_with_params(self, client, admin_headers):
        """TOP IP 支持 action 过滤和参数限制。"""
        response = await client.get(
            "/api/request-log/top-ips",
            params={"action": "api_call", "days": 7, "limit": 10},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_trend_requires_auth(self, client):
        """未登录用户无法获取趋势数据。"""
        response = await client.get("/api/request-log/trend")
        assert response.status_code == 401

    async def test_trend_returns_empty_list(self, client, admin_headers):
        """初始状态趋势数据应返回空列表。"""
        response = await client.get(
            "/api/request-log/trend",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_trend_with_action_filter(self, client, admin_headers):
        """趋势数据支持 action 过滤。"""
        response = await client.get(
            "/api/request-log/trend",
            params={"action": "api_call", "days": 7},
            headers=admin_headers,
        )
        assert response.status_code == 200

    async def test_counters_requires_auth(self, client):
        """未登录用户无法查询计数器。"""
        response = await client.get("/api/request-log/counters")
        assert response.status_code == 401

    async def test_counters_returns_empty_initially(self, client, admin_headers):
        """初始状态计数器应返回空列表。"""
        response = await client.get(
            "/api/request-log/counters",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_counters_with_ip_filter(self, client, admin_headers):
        """按 IP 过滤计数器。"""
        response = await client.get(
            "/api/request-log/counters",
            params={"ip": "10.0.0.1"},
            headers=admin_headers,
        )
        assert response.status_code == 200

    async def test_counters_invalid_date_format(self, client, admin_headers):
        """计数器无效日期格式应返回 400。"""
        response = await client.get(
            "/api/request-log/counters",
            params={"start_date": "bad-date"},
            headers=admin_headers,
        )
        assert response.status_code == 400

    async def test_actions_requires_auth(self, client):
        """未登录用户无法获取行为分类列表。"""
        response = await client.get("/api/request-log/actions")
        assert response.status_code == 401

    async def test_actions_returns_empty_list(self, client, admin_headers):
        """初始状态行为分类列表应返回空列表。"""
        response = await client.get(
            "/api/request-log/actions",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)