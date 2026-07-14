"""请求日志路由测试 —— 测试 query_logs、get_top_ips、get_trend、get_counters、list_actions。

使用内存数据库 + 真实 HTTP 客户端测试路由层行为。
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def request_log_app(db_container):
    """创建仅包含 request_log 路由的测试应用。"""
    app = FastAPI()
    app.state.container = db_container

    from backend.core.middleware import register_error_handlers
    register_error_handlers(app)

    from backend.plugins.request_log.routes import router
    app.include_router(router)
    return app


@pytest.fixture
async def request_log_client(request_log_app):
    async with AsyncClient(
        transport=ASGITransport(app=request_log_app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
class TestQueryLogs:
    """测试请求日志查询路由。"""

    async def test_query_logs_requires_auth(self, request_log_client):
        """未认证用户查询日志应返回 401。"""
        response = await request_log_client.get("/api/request-log/query")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestTopIps:
    """测试 TOP IP 排行路由。"""

    async def test_top_ips_requires_auth(self, request_log_client):
        """未认证用户查询 TOP IP 应返回 401。"""
        response = await request_log_client.get("/api/request-log/top-ips")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestTrend:
    """测试趋势分析路由。"""

    async def test_trend_requires_auth(self, request_log_client):
        """未认证用户查询趋势应返回 401。"""
        response = await request_log_client.get("/api/request-log/trend")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestCounters:
    """测试聚合计数路由。"""

    async def test_counters_requires_auth(self, request_log_client):
        """未认证用户查询计数器应返回 401。"""
        response = await request_log_client.get("/api/request-log/counters")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestActions:
    """测试行为分类列表路由。"""

    async def test_actions_requires_auth(self, request_log_client):
        """未认证用户查询行为分类应返回 401。"""
        response = await request_log_client.get("/api/request-log/actions")
        assert response.status_code == 401