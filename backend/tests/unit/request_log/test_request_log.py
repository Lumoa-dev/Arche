"""请求日志服务测试 —— 行为分类、IP 获取、中间件跳过逻辑。

测试策略：
- 纯函数和简单逻辑，使用 mock 隔离外部依赖
- 覆盖：行为分类、IP 获取、跳过路径、中间件 dispatch
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    classify_action,
    _get_client_ip,
    _SKIP_PATHS,
    _SKIP_PREFIXES,
)


class TestClassifyAction:
    """classify_action 行为分类测试。"""

    def test_login_fail(self):
        """登录失败路径返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_success(self):
        """登录成功返回 api_call 而非 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"
        assert classify_action("POST", "/api/auth/login", 302) == "api_call"

    def test_api_call(self):
        """API 前缀路径返回 api_call。"""
        assert classify_action("GET", "/api/posts", 200) == "api_call"
        assert classify_action("POST", "/api/posts", 201) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_page_view(self):
        """GET 非 API 路径返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_method(self):
        """非 GET 非 API 路径返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/callback", 200) == "other"
        assert classify_action("DELETE", "/hooks/1", 200) == "other"


class TestGetClientIp:
    """_get_client_ip 客户端 IP 获取测试。"""

    def test_x_forwarded_for_first(self):
        """X-Forwarded-For 首个 IP 被提取。"""
        request = MagicMock()
        request.headers.get = MagicMock(
            side_effect=lambda key, default="": {
                "X-Forwarded-For": "203.0.113.1, 10.0.0.1, 172.16.0.1",
            }.get(key, default)
        )
        request.client = MagicMock(host="10.0.0.1")
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip(self):
        """X-Real-IP 在 X-Forwarded-For 为空时生效。"""
        request = MagicMock()
        request.headers.get = MagicMock(
            side_effect=lambda key, default="": {
                "X-Real-IP": "198.51.100.1",
            }.get(key, default)
        )
        assert _get_client_ip(request) == "198.51.100.1"

    def test_x_forwarded_for_takes_precedence(self):
        """X-Forwarded-For 优先于 X-Real-IP。"""
        request = MagicMock()
        request.headers.get = MagicMock(
            side_effect=lambda key, default="": {
                "X-Real-IP": "198.51.100.1",
                "X-Forwarded-For": "203.0.113.1",
            }.get(key, default)
        )
        # _get_client_ip 先检查 X-Forwarded-For
        assert _get_client_ip(request) == "203.0.113.1"

    def test_fallback_to_client_host(self):
        """无代理头时回退到 client.host。"""
        request = MagicMock()
        request.headers.get = MagicMock(return_value="")
        request.client = MagicMock(host="192.168.1.1")
        assert _get_client_ip(request) == "192.168.1.1"

    def test_no_client(self):
        """无 client 时返回空字符串。"""
        request = MagicMock()
        request.headers.get = MagicMock(return_value="")
        request.client = None
        assert _get_client_ip(request) == ""

    def test_x_forwarded_for_single(self):
        """X-Forwarded-For 只有单个 IP。"""
        request = MagicMock()
        request.headers.get = MagicMock(
            side_effect=lambda key, default="": {
                "X-Forwarded-For": "203.0.113.1",
            }.get(key, default)
        )
        assert _get_client_ip(request) == "203.0.113.1"


class TestSkipPaths:
    """跳过路径测试。"""

    def test_skip_paths_contains_docs(self):
        """跳过的路径包含 /docs。"""
        assert "/docs" in _SKIP_PATHS

    def test_skip_paths_contains_openapi(self):
        """跳过的路径包含 /openapi.json。"""
        assert "/openapi.json" in _SKIP_PATHS

    def test_skip_paths_contains_redoc(self):
        """跳过的路径包含 /redoc。"""
        assert "/redoc" in _SKIP_PATHS

    def test_skip_paths_contains_favicon(self):
        """跳过的路径包含 /favicon.ico。"""
        assert "/favicon.ico" in _SKIP_PATHS

    def test_skip_prefixes_static(self):
        """跳过的前缀包含 /static/。"""
        assert "/static/" in _SKIP_PREFIXES

    def test_skip_prefixes_assets(self):
        """跳过的前缀包含 /assets/。"""
        assert "/assets/" in _SKIP_PREFIXES


class TestRequestLogMiddleware:
    """RequestLogMiddleware dispatch 逻辑测试。"""

    @pytest.mark.asyncio
    async def test_skip_docs_path(self):
        """/docs 路径被跳过，不记录日志。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        request = MagicMock()
        request.url.path = "/docs"
        call_next = AsyncMock(return_value=MagicMock())

        middleware = RequestLogMiddleware(MagicMock())
        # 跳过路径，直接调用 call_next 后返回
        with patch(
            "backend.plugins.request_log.services._write_log_async"
        ) as mock_write:
            await middleware.dispatch(request, call_next)
            mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_static_prefix(self):
        """/static/ 前缀路径被跳过。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        request = MagicMock()
        request.url.path = "/static/css/main.css"
        call_next = AsyncMock(return_value=MagicMock())

        middleware = RequestLogMiddleware(MagicMock())
        with patch(
            "backend.plugins.request_log.services._write_log_async"
        ) as mock_write:
            await middleware.dispatch(request, call_next)
            mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_api_request(self):
        """API 请求被记录。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        request = MagicMock()
        request.url.path = "/api/posts"
        request.method = "GET"
        response = MagicMock()
        response.status_code = 200
        call_next = AsyncMock(return_value=response)

        middleware = RequestLogMiddleware(MagicMock())
        with patch(
            "backend.plugins.request_log.services._write_log_async"
        ) as mock_write:
            result = await middleware.dispatch(request, call_next)
            mock_write.assert_called_once()
            assert result == response

    @pytest.mark.asyncio
    async def test_log_exception_as_500(self):
        """请求异常记录为 500。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        request = MagicMock()
        request.url.path = "/api/posts"
        request.method = "GET"
        call_next = AsyncMock(side_effect=ValueError("test error"))

        middleware = RequestLogMiddleware(MagicMock())
        with patch(
            "backend.plugins.request_log.services._write_log_async"
        ) as mock_write:
            with pytest.raises(ValueError):
                await middleware.dispatch(request, call_next)
            mock_write.assert_called_once()
            # 验证状态码为 500
            args = mock_write.call_args
            assert args[0][1] == 500