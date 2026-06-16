"""核心层测试 —— 错误处理中间件、认证错误、权限错误、安全头。"""

from __future__ import annotations

import pytest


class TestErrorHandlers:
    """测试统一错误处理中间件。"""

    @pytest.mark.asyncio
    async def test_validation_error_returns_422(self, async_client):
        """请求体验证失败返回 422。"""
        # 给 /api/auth/register 发送空 body
        resp = await async_client.post(
            "/api/auth/register", json={}, headers={"Content-Type": "application/json"}
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == "validation_error"

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, async_client):
        """未认证访问需要认证的端点返回 401。"""
        # /api/auth/users 需要认证
        resp = await async_client.get("/api/auth/users")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, async_client):
        """无效 JWT token 返回 401。"""
        resp = await async_client.get(
            "/api/auth/users",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_404_returns_json(self, async_client, auth_headers):
        """404 返回 JSON。"""
        resp = await async_client.get(
            "/api/nonexistent_route_xyz", headers=auth_headers
        )
        assert resp.status_code == 404
        assert "application/json" in resp.headers.get("content-type", "")


class TestSecurityHeaders:
    """测试安全响应头中间件。"""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, async_client):
        """每个响应都包含安全头。"""
        resp = await async_client.get("/api/ping")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-xss-protection") == "1; mode=block"
        assert resp.headers.get("referrer-policy") is not None
        assert resp.headers.get("permissions-policy") is not None


class TestAppError:
    """测试 AppError 异常类和响应格式。"""

    def test_app_error_defaults(self):
        """AppError 默认值。"""
        from backend.core.middleware import AppError

        err = AppError("出错了")
        assert err.message == "出错了"
        assert err.code == "error"
        assert err.status_code == 400
        assert err.data == {}

    def test_auth_error_defaults(self):
        """AuthError 默认值。"""
        from backend.core.middleware import AuthError

        err = AuthError()
        assert err.status_code == 401
        assert err.code == "auth_error"

    def test_permission_error_defaults(self):
        """PermissionError 默认值。"""
        from backend.core.middleware import PermissionError

        err = PermissionError()
        assert err.status_code == 403
        assert err.code == "permission_denied"

    def test_custom_error(self):
        """AppError 可以自定义所有字段。"""
        from backend.core.middleware import AppError

        err = AppError("自定义错误", code="custom", status_code=418, data={"key": "val"})
        assert err.message == "自定义错误"
        assert err.code == "custom"
        assert err.status_code == 418
        assert err.data == {"key": "val"}


class TestGetRealIP:
    """测试 get_real_ip() 三层检测。"""

    def test_x_real_ip_header(self):
        """X-Real-IP 优先级最高。"""
        from unittest.mock import MagicMock

        from backend.core.middleware import get_real_ip

        request = MagicMock()
        request.headers = {"X-Real-IP": "10.0.0.1", "X-Forwarded-For": "203.0.113.5"}
        request.client.host = "172.16.0.1"

        ip = get_real_ip(request)
        assert ip == "10.0.0.1"

    def test_x_forwarded_for_fallback(self):
        """无 X-Real-IP 时使用 X-Forwarded-For 首 IP。"""
        from unittest.mock import MagicMock

        from backend.core.middleware import get_real_ip

        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.5, 198.51.100.2"}
        request.client.host = "172.16.0.1"

        ip = get_real_ip(request)
        assert ip == "203.0.113.5"

    def test_client_host_fallback(self):
        """无任何代理头时使用 request.client.host。"""
        from unittest.mock import MagicMock

        from backend.core.middleware import get_real_ip

        request = MagicMock()
        request.headers = {}
        request.client.host = "192.168.1.1"

        ip = get_real_ip(request)
        assert ip == "192.168.1.1"

    def test_no_client_returns_empty(self):
        """没有 client 时返回空字符串。"""
        from unittest.mock import MagicMock

        from backend.core.middleware import get_real_ip

        request = MagicMock()
        request.headers = {}
        request.client = None

        ip = get_real_ip(request)
        assert ip == ""
