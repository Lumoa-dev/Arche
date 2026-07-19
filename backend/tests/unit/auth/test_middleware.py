"""AuthMiddleware JWT 认证中间件测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from backend.plugins.auth.middleware import AuthMiddleware


@pytest.fixture
def app():
    return FastAPI()


@pytest.fixture
def secret_key():
    return "test-secret-key-12345"


@pytest.fixture
def middleware(app, secret_key):
    return AuthMiddleware(app, secret_key=secret_key)


@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.url.path = "/api/some/protected/route"
    request.method = "GET"
    request.headers = {"Authorization": ""}
    request.state = MagicMock()
    request.app.state.container = MagicMock()
    return request


@pytest.fixture
def call_next():
    async def _call_next(req):
        return JSONResponse({"status": "ok"}, status_code=200)

    return _call_next


class TestAuthMiddleware:
    """测试 AuthMiddleware 认证中间件。"""

    @pytest.mark.asyncio
    async def test_public_paths_passthrough(self, middleware, call_next):
        """公开路由应直接放行，无需认证。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/auth/login"
        request.method = "POST"
        request.headers = {}

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_internal_paths_passthrough(self, middleware, call_next):
        """FastAPI 内置路由应直接放行。"""
        request = MagicMock(spec=Request)
        request.url.path = "/docs"
        request.method = "GET"
        request.headers = {}

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_auth_header(self, middleware, call_next):
        """缺少 Authorization header 应返回 401。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"Authorization": ""}

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 401
        body = response.body.decode()
        assert "缺少认证信息" in body

    @pytest.mark.asyncio
    async def test_invalid_auth_scheme(self, middleware, call_next):
        """非 Bearer 认证方案应返回 401。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"Authorization": "Basic token123"}

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_mock_token_admin(self, middleware, call_next, secret_key):
        """mock-token-admin 应注入管理员用户信息。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"Authorization": "Bearer mock-token-admin-1234567890"}
        request.state = MagicMock()
        request.app.state.container = MagicMock()
        container = request.app.state.container
        container.is_available.return_value = False

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.user["level"] == 0
        assert request.state.user["username"] == "admin"

    @pytest.mark.asyncio
    async def test_mock_token_user(self, middleware, call_next):
        """mock-token-user 应注入普通用户信息。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"Authorization": "Bearer mock-token-user-1234567890"}
        request.state = MagicMock()
        request.app.state.container = MagicMock()
        request.app.state.container.is_available.return_value = False

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.user["level"] == 1
        assert request.state.user["username"] == "user"

    @pytest.mark.asyncio
    async def test_mock_token_guest(self, middleware, call_next):
        """mock-token-guest 应注入游客用户信息。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"Authorization": "Bearer mock-token-guest-1234567890"}
        request.state = MagicMock()
        request.app.state.container = MagicMock()
        request.app.state.container.is_available.return_value = False

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.user["level"] == 5
        assert request.state.user["username"] == "guest"

    @pytest.mark.asyncio
    async def test_mock_token_unknown_role(self, middleware, call_next):
        """未知角色的 mock-token 应默认降级为普通用户。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"Authorization": "Bearer mock-token-unknown-1234567890"}
        request.state = MagicMock()
        request.app.state.container = MagicMock()
        request.app.state.container.is_available.return_value = False

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.user["username"] == "user"

    @pytest.mark.asyncio
    async def test_valid_jwt_token(self, middleware, call_next, secret_key):
        """有效的 JWT token 应正确解析并注入用户信息。"""
        token = jwt.encode(
            {
                "sub": "user-123",
                "email": "test@example.com",
                "username": "testuser",
                "level": 2,
                "blog_quality_level": 3,
            },
            secret_key,
            algorithm="HS256",
        )

        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"Authorization": f"Bearer {token}"}
        request.state = MagicMock()
        request.app.state.container = MagicMock()
        request.app.state.container.is_available.return_value = False

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.user["id"] == "user-123"
        assert request.state.user["username"] == "testuser"
        assert request.state.user["level"] == 2

    @pytest.mark.asyncio
    async def test_expired_jwt_token(self, middleware, call_next, secret_key):
        """过期的 JWT token 应返回 401。"""
        token = jwt.encode(
            {"sub": "user-123", "exp": 0},  # 早已过期
            secret_key,
            algorithm="HS256",
        )

        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"Authorization": f"Bearer {token}"}
        request.state = MagicMock()
        request.app.state.container = MagicMock()

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 401
        body = response.body.decode()
        assert "Token 已过期" in body

    @pytest.mark.asyncio
    async def test_invalid_jwt_token(self, middleware, call_next):
        """无效的 JWT token 应返回 401。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"Authorization": "Bearer this.is.not.a.valid.token"}
        request.state = MagicMock()
        request.app.state.container = MagicMock()

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 401
        body = response.body.decode()
        assert "无效 Token" in body

    @pytest.mark.asyncio
    async def test_blog_public_get_without_token(self, middleware, call_next):
        """博客公开 GET 路由，无 token 时应放行且不注入用户。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/blog/posts"
        request.method = "GET"
        request.headers = {"Authorization": ""}
        request.state = MagicMock()
        request.app.state.container = MagicMock()

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # 不应设置 user 信息（MagicMock 会 auto-create，但不应是 dict 类型的用户对象）
        assert not isinstance(request.state.user, dict)

    @pytest.mark.asyncio
    async def test_blog_public_get_with_valid_token(self, middleware, call_next, secret_key):
        """博客公开 GET 路由，有有效 token 时应注入用户信息。"""
        token = jwt.encode(
            {"sub": "user-123", "username": "testuser", "level": 1, "blog_quality_level": 3},
            secret_key,
            algorithm="HS256",
        )

        request = MagicMock(spec=Request)
        request.url.path = "/api/blog/posts"
        request.method = "GET"
        request.headers = {"Authorization": f"Bearer {token}"}
        request.state = MagicMock()
        request.app.state.container = MagicMock()
        request.app.state.container.is_available.return_value = False

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.user["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_blog_public_get_with_invalid_token(self, middleware, call_next):
        """博客公开 GET 路由，无效 token 时应放行且不注入用户。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/blog/posts"
        request.method = "GET"
        request.headers = {"Authorization": "Bearer invalid-token-here"}
        request.state = MagicMock()
        request.app.state.container = MagicMock()

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # token 无效，不注入用户

    @pytest.mark.asyncio
    async def test_middleware_exception_handling(self, middleware):
        """中间件内部异常应返回 500。"""
        async def failing_next(req):
            raise RuntimeError("unexpected error")

        request = MagicMock(spec=Request)
        request.url.path = "/api/auth/login"
        request.method = "POST"
        request.headers = {}

        response = await middleware.dispatch(request, failing_next)
        assert response.status_code == 500
        body = response.body.decode()
        assert "内部服务器错误" in body

    @pytest.mark.parametrize(
        "method,path,expected_status",
        [
            ("GET", "/api/auth/register", 200),
            ("POST", "/api/auth/login", 200),
            ("POST", "/api/auth/refresh", 200),
            ("GET", "/docs", 200),
            ("GET", "/openapi.json", 200),
            ("GET", "/redoc", 200),
        ],
    )
    @pytest.mark.asyncio
    async def test_public_and_internal_paths(
        self, middleware, call_next, method, path, expected_status
    ):
        """参数化测试所有公开和内部路由。"""
        request = MagicMock(spec=Request)
        request.url.path = path
        request.method = method
        request.headers = {}

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == expected_status

    @pytest.mark.asyncio
    async def mock_token_exception_handling(self, middleware, call_next):
        """mock token 处理中异常应返回 500。"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"Authorization": "Bearer mock-token-admin-1234567890"}
        request.state = MagicMock()
        request.app.state.container = MagicMock()
        request.app.state.container.is_available = MagicMock(side_effect=RuntimeError("fail"))

        response = await middleware.dispatch(request, call_next)
        # 异常被捕获，返回 500
        assert response.status_code == 500