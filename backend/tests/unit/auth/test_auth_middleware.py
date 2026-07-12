"""认证中间件行为测试。

测试 AuthMiddleware 的路径匹配策略、token 解析、用户注入、mock token 等行为。
所有依赖均通过 mock 隔离，不依赖真实数据库。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from backend.plugins.auth.middleware import AuthMiddleware

# 测试密钥，与 conftest.py 中的 SECRET_KEY 保持一致
SECRET_KEY = "test_secret_key_12345"


# =============================================================================
# 辅助函数
# =============================================================================


def _make_request(
    path: str,
    method: str = "GET",
    headers: list | None = None,
    container: MagicMock | None = None,
) -> Request:
    """创建 FastAPI Request 对象，包含指定路径、方法和请求头。

    参数：
        path: 请求路径（如 /api/auth/login）
        method: HTTP 方法（如 GET, POST）
        headers: 请求头列表，格式为 [(b"header-name", b"header-value"), ...]
        container: 可选的 mock container；不传则用默认 MagicMock
    """
    mock_app = MagicMock()
    if container is not None:
        mock_app.state.container = container
    else:
        mock_app.state.container = MagicMock()
    # 确保 session_tracker 不可用，避免 _refresh_session 干扰
    mock_app.state.container.is_available.return_value = False

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers or [],
        "scheme": "http",
        "server": ("testserver", 80),
        "root_path": "",
        "query_string": b"",
        "app": mock_app,
    }
    return Request(scope)


def _make_jwt_token(
    secret_key: str = SECRET_KEY,
    sub: str | None = None,
    email: str = "test@example.com",
    username: str = "testuser",
    level: int = 1,
    blog_quality_level: int = 3,
    jti: str | None = None,
    expired: bool = False,
) -> str:
    """创建 JWT token，支持自定义 payload 和过期状态。"""
    if sub is None:
        sub = str(uuid.uuid4())
    if jti is None:
        jti = str(uuid.uuid4())

    exp = (
        datetime.now(timezone.utc) - timedelta(hours=1)
        if expired
        else datetime.now(timezone.utc) + timedelta(hours=1)
    )
    payload = {
        "sub": sub,
        "email": email,
        "username": username,
        "level": level,
        "blog_quality_level": blog_quality_level,
        "jti": jti,
        "exp": exp,
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def _make_container_with_auth(
    is_token_blacklisted: bool = False,
) -> MagicMock:
    """创建带有 mock auth service 的容器，用于黑名单测试。"""
    container = MagicMock()
    auth_service = MagicMock()
    auth_service.is_token_blacklisted.return_value = is_token_blacklisted

    def _get_service(name: str):
        if name == "auth":
            return auth_service
        return MagicMock()

    container.get = _get_service
    container.is_available.return_value = False
    return container


def _assert_json_error_response(response: Response, status_code: int, code: str) -> None:
    """断言返回的是 JSON 错误响应，包含指定的 status_code 和 code。"""
    assert response.status_code == status_code
    body = json.loads(response.body)
    assert body["code"] == code


# =============================================================================
# Fixture
# =============================================================================


@pytest.fixture
def middleware():
    """创建 AuthMiddleware 实例，所有测试共享。"""
    app = MagicMock()
    return AuthMiddleware(app, secret_key=SECRET_KEY)


@pytest.fixture
def call_next():
    """创建模拟的 call_next 函数，返回 200 OK。"""
    async def _call_next(request: Request) -> Response:
        return Response(status_code=200, content="OK")
    return _call_next


# =============================================================================
# 公开路径测试
# =============================================================================


@pytest.mark.asyncio
class TestAuthMiddlewarePublicPaths:
    """测试 PUBLIC_PATHS 和 INTERNAL_PREFIXES 跳过认证的行为。"""

    async def test_public_paths_skip_auth(self, middleware, call_next):
        """PUBLIC_PATHS 路由应直接放行，无需任何认证头。"""
        public_paths = [
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/refresh",
        ]
        for path in public_paths:
            request = _make_request(path=path, method="POST")
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == 200, f"路径 {path} 未被放行"

    async def test_internal_prefixes_skip_auth(self, middleware, call_next):
        """FastAPI 内置路由（/docs, /openapi.json, /redoc）应直接放行。"""
        internal_paths = [
            "/docs",
            "/openapi.json",
            "/redoc",
            "/docs/some-page",
        ]
        for path in internal_paths:
            request = _make_request(path=path)
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == 200, f"路径 {path} 未被放行"


# =============================================================================
# 博客公开路径测试
# =============================================================================


@pytest.mark.asyncio
class TestAuthMiddlewareBlogPublicPaths:
    """测试 BLOG_PUBLIC_PREFIXES 的 GET 请求行为。"""

    async def test_blog_public_get_without_token(self, middleware, call_next):
        """GET /api/blog/posts 不带 token 应正常工作。"""
        request = _make_request(path="/api/blog/posts")
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # 匿名用户不应有 user 信息
        assert not hasattr(request.state, "user")

    async def test_blog_public_get_with_valid_token(self, middleware, call_next):
        """GET /api/blog/tags 带有效 Bearer token 应注入用户信息。"""
        container = _make_container_with_auth()
        token = _make_jwt_token()
        headers = [(b"authorization", f"Bearer {token}".encode())]
        request = _make_request(
            path="/api/blog/tags",
            headers=headers,
            container=container,
        )
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # 验证用户信息被注入
        assert hasattr(request.state, "user")
        assert request.state.user["email"] == "test@example.com"
        assert request.state.user["username"] == "testuser"
        assert request.state.user["level"] == 1

    async def test_blog_public_get_with_invalid_token(self, middleware, call_next):
        """GET /api/blog/posts 带无效 token 应仍放行（匿名访问）。"""
        headers = [(b"authorization", b"Bearer invalid.token.here")]
        request = _make_request(path="/api/blog/posts", headers=headers)
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # 无效 token 不应注入用户信息
        assert not hasattr(request.state, "user")

    async def test_blog_public_get_with_mock_token(self, middleware, call_next):
        """GET /api/blog/posts 带 mock-token-admin 应注入 admin 用户。"""
        headers = [(b"authorization", b"Bearer mock-token-admin-1234567890")]
        request = _make_request(path="/api/blog/posts", headers=headers)
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # 验证注入的是 admin 用户
        assert hasattr(request.state, "user")
        assert request.state.user["level"] == 0
        assert request.state.user["username"] == "admin"
        assert request.state.user["email"] == "admin@example.com"


# =============================================================================
# 受保护路由测试
# =============================================================================


@pytest.mark.asyncio
class TestAuthMiddlewareProtectedRoutes:
    """测试受保护路由的认证校验行为。"""

    async def test_no_auth_header_returns_401(self, middleware, call_next):
        """不带 Authorization header 请求受保护路由应返回 401。"""
        request = _make_request(path="/api/protected/resource")
        response = await middleware.dispatch(request, call_next)
        _assert_json_error_response(response, 401, "auth_error")

    async def test_invalid_auth_header_returns_401(self, middleware, call_next):
        """非 Bearer 类型的 Authorization header 应返回 401。"""
        headers = [(b"authorization", b"Basic dXNlcjpwYXNz")]
        request = _make_request(path="/api/protected/resource", headers=headers)
        response = await middleware.dispatch(request, call_next)
        _assert_json_error_response(response, 401, "auth_error")

    async def test_expired_token_returns_401(self, middleware, call_next):
        """过期的 JWT token 应返回 401 且 code 为 token_expired。"""
        container = _make_container_with_auth()
        token = _make_jwt_token(expired=True)
        headers = [(b"authorization", f"Bearer {token}".encode())]
        request = _make_request(
            path="/api/protected/resource",
            headers=headers,
            container=container,
        )
        response = await middleware.dispatch(request, call_next)
        _assert_json_error_response(response, 401, "token_expired")

    async def test_invalid_token_returns_401(self, middleware, call_next):
        """格式错误的 JWT token 应返回 401 且 code 为 invalid_token。"""
        container = _make_container_with_auth()
        headers = [(b"authorization", b"Bearer not.a.valid.token")]
        request = _make_request(
            path="/api/protected/resource",
            headers=headers,
            container=container,
        )
        response = await middleware.dispatch(request, call_next)
        _assert_json_error_response(response, 401, "invalid_token")

    async def test_valid_token_injects_user(self, middleware, call_next):
        """有效 token 应正确解析并注入用户信息到 request.state。"""
        container = _make_container_with_auth()
        user_id = str(uuid.uuid4())
        token = _make_jwt_token(
            sub=user_id,
            email="user@example.com",
            username="testuser",
            level=2,
            blog_quality_level=4,
        )
        headers = [(b"authorization", f"Bearer {token}".encode())]
        request = _make_request(
            path="/api/protected/resource",
            headers=headers,
            container=container,
        )
        response = await middleware.dispatch(request, call_next)
        # 成功时应返回 call_next 的结果（200）
        assert response.status_code == 200
        # 验证用户信息
        assert hasattr(request.state, "user")
        assert request.state.user["id"] == user_id
        assert request.state.user["email"] == "user@example.com"
        assert request.state.user["username"] == "testuser"
        assert request.state.user["level"] == 2
        assert request.state.user["blog_quality_level"] == 4

    async def test_blacklisted_token_returns_401(self, middleware, call_next):
        """被列入黑名单的 JWT token 应返回 401。"""
        # 创建容器，auth_service 返回黑名单命中
        container = _make_container_with_auth(is_token_blacklisted=True)
        token = _make_jwt_token()
        headers = [(b"authorization", f"Bearer {token}".encode())]
        request = _make_request(
            path="/api/protected/resource",
            headers=headers,
            container=container,
        )
        response = await middleware.dispatch(request, call_next)
        _assert_json_error_response(response, 401, "auth_error")


# =============================================================================
# Mock Token 测试
# =============================================================================


@pytest.mark.asyncio
class TestAuthMiddlewareMockToken:
    """测试开发模式 mock token 的用户注入行为。"""

    async def test_mock_token_admin(self, middleware, call_next):
        """mock-token-admin-xxx 应注入 admin 用户（level=0）。"""
        headers = [(b"authorization", b"Bearer mock-token-admin-1234567890")]
        request = _make_request(path="/api/admin/dashboard", headers=headers)
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.user["level"] == 0
        assert request.state.user["username"] == "admin"

    async def test_mock_token_user(self, middleware, call_next):
        """mock-token-user-xxx 应注入普通用户（level=1）。"""
        headers = [(b"authorization", b"Bearer mock-token-user-1234567890")]
        request = _make_request(path="/api/protected/resource", headers=headers)
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.user["level"] == 1
        assert request.state.user["username"] == "user"

    async def test_mock_token_guest(self, middleware, call_next):
        """mock-token-guest-xxx 应注入访客用户（level=5）。"""
        headers = [(b"authorization", b"Bearer mock-token-guest-1234567890")]
        request = _make_request(path="/api/protected/resource", headers=headers)
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert request.state.user["level"] == 5
        assert request.state.user["username"] == "guest"

    async def test_mock_token_unknown_role_falls_back_to_user(self, middleware, call_next):
        """未知角色在 mock-token 中应回退到 'user'。"""
        headers = [(b"authorization", b"Bearer mock-token-editor-1234567890")]
        request = _make_request(path="/api/protected/resource", headers=headers)
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # 未知角色应回退到 user
        assert request.state.user["level"] == 1
        assert request.state.user["username"] == "user"