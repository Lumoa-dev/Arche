"""中间件补充测试 —— 覆盖未在现有测试中包含的函数。

现有测试 (test_middleware.py) 覆盖了：
- AppError / AuthError / PermissionError 异常处理
- error_response / get_real_ip / get_current_user / require_user
- 注册错误处理器

本文件补充覆盖：
- _format_validation_errors 格式化逻辑
- require_level 装饰器
- SecurityHeadersMiddleware
- get_real_ip 的边界情况
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response
from starlette.testclient import TestClient

from backend.core.middleware import (
    _format_validation_errors,
    get_real_ip,
    register_error_handlers,
    require_level,
    setup_cors,
    setup_security_headers,
)


# =============================================================================
# _format_validation_errors 测试
# =============================================================================


class TestFormatValidationErrors:
    """测试验证错误格式化逻辑。"""

    def test_single_field_error(self):
        """单个字段的错误应正确格式化。"""
        errors = [{"loc": ["body", "email"], "msg": "field required"}]
        result = _format_validation_errors(errors)
        assert "email: field required" in result

    def test_multiple_field_errors(self):
        """多个字段的错误应用分号连接。"""
        errors = [
            {"loc": ["body", "email"], "msg": "field required"},
            {"loc": ["body", "password"], "msg": "field required"},
        ]
        result = _format_validation_errors(errors)
        assert "email: field required" in result
        assert "password: field required" in result
        assert "；" in result  # 中文分号

    def test_error_without_loc(self):
        """没有 loc 字段的错误应使用默认值。"""
        errors = [{"msg": "unknown error"}]
        result = _format_validation_errors(errors)
        assert "unknown error" in result

    def test_error_with_query_param(self):
        """查询参数错误的 loc 解析。"""
        errors = [{"loc": ["query", "page"], "msg": "value is not a valid integer"}]
        result = _format_validation_errors(errors)
        assert "page: value is not a valid integer" in result

    def test_empty_errors_list(self):
        """空错误列表应返回空字符串。"""
        result = _format_validation_errors([])
        assert result == ""


# =============================================================================
# require_level 装饰器测试
# =============================================================================


class TestRequireLevel:
    """测试 require_level 权限装饰器。"""

    @pytest.mark.asyncio
    async def test_level_ok_passes(self):
        """用户等级满足要求时应通过。"""
        mock_request = MagicMock(spec=Request)
        mock_request.state.user = {
            "id": "test-user-id",
            "level": 0,
        }

        @require_level(min_level=1)
        async def test_handler(request):
            return "ok"

        result = await test_handler(request=mock_request)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_level_too_high_raises(self):
        """用户等级不满足要求时应抛出 PermissionError。"""
        from backend.core.middleware import PermissionError

        mock_request = MagicMock(spec=Request)
        mock_request.state.user = {
            "id": "test-user-id",
            "level": 5,
        }

        @require_level(min_level=1)
        async def test_handler(request):
            return "ok"

        with pytest.raises(PermissionError) as excinfo:
            await test_handler(request=mock_request)
        assert "需要等级 <= 1" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_unauthenticated_raises(self):
        """未认证用户应抛出 AuthError。"""
        from backend.core.middleware import AuthError

        mock_request = MagicMock(spec=Request)
        mock_request.state.user = None

        @require_level(min_level=1)
        async def test_handler(request):
            return "ok"

        with pytest.raises(AuthError) as excinfo:
            await test_handler(request=mock_request)
        assert "未认证" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_missing_request_arg_raises(self):
        """没有 request 参数时应抛出 AuthError。"""
        from backend.core.middleware import AuthError

        @require_level(min_level=1)
        async def test_handler():
            return "ok"

        with pytest.raises(AuthError) as excinfo:
            await test_handler()
        assert "必须传入 request 参数" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_level_zero_always_passes(self):
        """P0（level=0）应能访问任何等级要求的接口。"""
        mock_request = MagicMock(spec=Request)
        mock_request.state.user = {
            "id": "test-user-id",
            "level": 0,
        }

        # 即使是最高等级要求（min_level=0），P0 也应通过
        @require_level(min_level=0)
        async def test_handler(request):
            return "ok"

        result = await test_handler(request=mock_request)
        assert result == "ok"


# =============================================================================
# get_real_ip 边界情况测试
# =============================================================================


class TestGetRealIpEdgeCases:
    """测试 get_real_ip 的边界情况。"""

    def test_x_real_ip_empty_string(self):
        """X-Real-IP 为空字符串时应继续回退。"""
        scope = {
            "type": "http",
            "headers": [
                (b"x-real-ip", b""),
                (b"x-forwarded-for", b"203.0.113.1"),
            ],
            "client": ("172.16.0.1", 12345),
        }
        request = Request(scope)
        assert get_real_ip(request) == "203.0.113.1"

    def test_no_headers_no_client(self):
        """没有任何 IP 来源时应返回空字符串。"""
        scope = {
            "type": "http",
            "headers": [],
            "client": None,
        }
        request = Request(scope)
        assert get_real_ip(request) == ""

    def test_x_forwarded_for_with_spaces(self):
        """X-Forwarded-For 带空格时应正常解析。"""
        scope = {
            "type": "http",
            "headers": [
                (b"x-forwarded-for", b"  203.0.113.1 ,  198.51.100.1  "),
            ],
            "client": ("172.16.0.1", 12345),
        }
        request = Request(scope)
        assert get_real_ip(request) == "203.0.113.1"

    def test_ipv6_client_address(self):
        """IPv6 客户端地址应正常返回。"""
        scope = {
            "type": "http",
            "headers": [],
            "client": ("::1", 12345),
        }
        request = Request(scope)
        assert get_real_ip(request) == "::1"


# =============================================================================
# SecurityHeadersMiddleware 测试
# =============================================================================


class TestSecurityHeadersMiddleware:
    """测试安全响应头中间件。"""

    def test_security_headers_added(self):
        """所有响应应包含安全头。"""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        setup_security_headers(app)

        client = TestClient(app)
        response = client.get("/test")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert (
            response.headers.get("Referrer-Policy")
            == "strict-origin-when-cross-origin"
        )
        assert response.headers.get("Permissions-Policy") == (
            "camera=(), microphone=(), geolocation=()"
        )


# =============================================================================
# setup_cors 测试
# =============================================================================


class TestSetupCors:
    """测试 CORS 配置。"""

    def test_cors_headers_present(self):
        """CORS 中间件应正确配置。"""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        setup_cors(app, ["https://example.com"])

        client = TestClient(app)
        response = client.options(
            "/test",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"
        assert response.headers.get("Access-Control-Allow-Credentials") == "true"


# =============================================================================
# register_error_handlers 集成测试
# =============================================================================


class TestErrorHandlers:
    """测试错误处理器注册。"""

    def test_unhandled_exception_returns_500(self):
        """未处理异常应返回 500。"""
        app = FastAPI()

        @app.get("/crash")
        async def crash_endpoint():
            raise ValueError("test crash")

        register_error_handlers(app)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/crash")

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == "internal_error"
        assert data["message"] == "内部服务器错误"