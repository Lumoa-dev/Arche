"""请求日志服务单元测试 —— classify_action、_get_client_ip。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.plugins.request_log.services import (
    _get_client_ip,
    classify_action,
)


class TestClassifyAction:
    """测试请求行为分类函数。"""

    def test_login_fail_on_login_4xx(self):
        """登录路径且状态码 >=400 应分类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 429) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_success_not_login_fail(self):
        """登录成功（状态码 <400）不应分类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) != "login_fail"

    def test_api_call_for_api_paths(self):
        """以 /api/ 开头的路径应分类为 api_call。"""
        assert classify_action("GET", "/api/users", 200) == "api_call"
        assert classify_action("POST", "/api/posts", 201) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"
        # 登录失败优先于 api_call
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"

    def test_page_view_for_get_non_api(self):
        """非 API 的 GET 请求应分类为 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_for_non_get_non_api(self):
        """非 GET 且非 API 的请求应分类为 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/some-path", 200) == "other"
        assert classify_action("DELETE", "/resource", 200) == "other"

    def test_api_call_with_4xx(self):
        """API 路径 4xx 仍分类为 api_call（除非是登录）。"""
        assert classify_action("GET", "/api/users", 403) == "api_call"
        assert classify_action("GET", "/api/users", 404) == "api_call"
        assert classify_action("GET", "/api/users", 422) == "api_call"


class TestGetClientIp:
    """测试客户端 IP 提取函数。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 应取第一个 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
        request.client = MagicMock(host="10.0.0.1")
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip_used(self):
        """X-Real-IP 应在无 X-Forwarded-For 时使用。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "203.0.113.2"}
        request.client = MagicMock(host="10.0.0.1")
        assert _get_client_ip(request) == "203.0.113.2"

    def test_client_host_fallback(self):
        """无代理头时回退到 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="127.0.0.1")
        assert _get_client_ip(request) == "127.0.0.1"

    def test_x_forwarded_for_precedence(self):
        """X-Forwarded-For 优先于 X-Real-IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.3, 10.0.0.2",
            "X-Real-IP": "192.168.1.1",
        }
        request.client = MagicMock(host="10.0.0.2")
        assert _get_client_ip(request) == "203.0.113.3"

    def test_empty_headers_no_client(self):
        """无任何 IP 信息时应返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""

    def test_x_real_ip_no_client(self):
        """X-Real-IP 有值但无 client 时不回退到空。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "10.0.0.5"}
        request.client = None
        assert _get_client_ip(request) == "10.0.0.5"


class TestRequestLogMiddleware:
    """RequestLogMiddleware 基础验证。"""

    def test_skip_paths_are_configured(self):
        """跳过列表应包含文档和静态资源路径。"""
        from backend.plugins.request_log.services import _SKIP_PATHS, _SKIP_PREFIXES

        assert "/docs" in _SKIP_PATHS
        assert "/openapi.json" in _SKIP_PATHS
        assert "/redoc" in _SKIP_PATHS
        assert "/favicon.ico" in _SKIP_PATHS
        assert "/static/" in _SKIP_PREFIXES
        assert "/assets/" in _SKIP_PREFIXES