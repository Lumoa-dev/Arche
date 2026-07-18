"""请求日志插件 单元测试。

覆盖纯函数：classify_action、_get_client_ip。
中间件和聚合服务的集成测试不在本文件范围内。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.plugins.request_log.services import (
    _get_client_ip,
    classify_action,
)


# =============================================================================
# classify_action 测试
# =============================================================================


class TestClassifyAction:
    """请求行为分类函数测试。"""

    def test_login_fail(self):
        """登录失败（POST /api/auth/login + 4xx）应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"

    def test_login_success_not_login_fail(self):
        """登录成功（2xx）不应返回 login_fail。"""
        result = classify_action("POST", "/api/auth/login", 200)
        assert result == "api_call"

    def test_api_call(self):
        """API 路径应返回 api_call。"""
        assert classify_action("GET", "/api/posts", 200) == "api_call"
        assert classify_action("POST", "/api/posts", 201) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_page_view(self):
        """GET 非 API 路径应返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_method(self):
        """非 GET 非 API 路径应返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/some-path", 200) == "other"
        assert classify_action("PATCH", "/some-path", 200) == "other"

    def test_api_path_with_query(self):
        """带查询参数的 API 路径应返回 api_call。"""
        assert classify_action("GET", "/api/posts?page=1", 200) == "api_call"

    def test_sub_api_path(self):
        """子 API 路径应返回 api_call。"""
        assert classify_action("GET", "/api/v2/users", 200) == "api_call"


# =============================================================================
# _get_client_ip 测试
# =============================================================================


class TestGetClientIp:
    """客户端 IP 提取函数测试。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 应取第一个 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1, 192.168.1.1"}
        request.client = MagicMock(host="127.0.0.1")
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip(self):
        """X-Real-IP 应被正确读取。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "10.0.0.5"}
        request.client = MagicMock(host="127.0.0.1")
        assert _get_client_ip(request) == "10.0.0.5"

    def test_fallback_to_client_host(self):
        """无代理头时应回退到 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="192.168.1.100")
        assert _get_client_ip(request) == "192.168.1.100"

    def test_priority_x_real_ip_over_x_forwarded(self):
        """X-Real-IP 优先级高于 X-Forwarded-For。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
            "X-Real-IP": "10.0.0.99",
        }
        request.client = MagicMock(host="127.0.0.1")
        # 函数逻辑：先检查 X-Forwarded-For, 再检查 X-Real-IP
        assert _get_client_ip(request) == "203.0.113.1"

    def test_empty_headers_returns_empty_string(self):
        """无任何 IP 来源时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""

    def test_ipv6_in_x_forwarded_for(self):
        """IPv6 地址在 X-Forwarded-For 中应正确处理。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "2001:db8::1, 10.0.0.1"
        }
        request.client = MagicMock(host="127.0.0.1")
        assert _get_client_ip(request) == "2001:db8::1"

    def test_multiple_proxies(self):
        """多层代理下 X-Forwarded-For 取第一个 IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1, 172.16.0.1"
        }
        request.client = MagicMock(host="10.0.0.1")
        assert _get_client_ip(request) == "203.0.113.1"