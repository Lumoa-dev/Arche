"""核心层测试 —— 应用创建、引导顺序、健康检查。"""

from __future__ import annotations

import pytest


class TestAppCreation:
    """测试 create_app() 引导顺序和基础功能。"""

    def test_app_created(self, app):
        """应用能被成功创建，返回 FastAPI 实例。"""
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)
        assert app.title == "Arche"

    def test_container_attached(self, app):
        """ServiceContainer 已挂载到 app.state。"""
        assert hasattr(app.state, "container")
        from backend.core.container import ServiceContainer

        assert isinstance(app.state.container, ServiceContainer)

    def test_core_services_registered(self, app):
        """核心服务已注册到容器。"""
        container = app.state.container

        # config
        assert container.is_available("config")
        config = container.get("config")
        assert config is not None

        # db
        assert container.is_available("db")
        db = container.get("db")
        assert "engine" in db
        assert "session_factory" in db


class TestHealthEndpoint:
    """健康检查端点测试。"""

    @pytest.mark.asyncio
    async def test_ping(self, async_client):
        """GET /api/ping 返回健康状态。"""
        resp = await async_client.get("/api/ping")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert data["data"]["status"] == "healthy"

    def test_ping_sync(self, client):
        """同步 TestClient 同样可以访问 ping。"""
        resp = client.get("/api/ping")
        assert resp.status_code == 200
        assert resp.json()["code"] == "ok"


class TestLifecycle:
    """应用生命周期测试。"""

    @pytest.mark.asyncio
    async def test_response_has_security_headers(self, async_client):
        """所有响应包含安全头。"""
        resp = await async_client.get("/api/ping")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-xss-protection") == "1; mode=block"

    @pytest.mark.asyncio
    async def test_404_returns_json(self, async_client, auth_headers):
        """不存在的路径在认证后返回 JSON 错误而非 HTML。"""
        resp = await async_client.get("/api/nonexistent", headers=auth_headers)
        assert resp.status_code == 404
        assert "application/json" in resp.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, async_client):
        """CORS 头已配置（发送 Origin 头触发 CORS 中间件）。"""
        resp = await async_client.get(
            "/api/ping",
            headers={"Origin": "http://testserver"},
        )
        assert resp.status_code == 200
        cors_origin = resp.headers.get("access-control-allow-origin")
        assert cors_origin is not None, f"CORS origin missing in {dict(resp.headers)}"
        # 配置的 origins 包含 testserver
        assert "testserver" in cors_origin
