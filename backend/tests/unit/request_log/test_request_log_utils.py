"""请求日志插件 —— 工具函数单元测试。

测试 classify_action、_get_client_ip 等独立函数。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.plugins.request_log.services import (
    _get_client_ip,
    _SKIP_PATHS,
    _SKIP_PREFIXES,
    classify_action,
)


# =============================================================================
# classify_action
# =============================================================================


class TestClassifyAction:
    """请求行为分类测试。"""

    def test_login_failure(self):
        """登录失败（/api/auth/login + status >= 400）。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_success_is_api_call(self):
        """登录成功（status < 400）归为 api_call。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_call(self):
        """其他 /api/ 路径归为 api_call。"""
        assert classify_action("POST", "/api/posts", 201) == "api_call"
        assert classify_action("GET", "/api/posts", 200) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_page_view(self):
        """非 API 路径的 GET 请求归为 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 404) == "page_view"

    def test_other(self):
        """非 GET 且非 API 路径归为 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/custom", 200) == "other"

    def test_edge_empty_path(self):
        """空路径。"""
        assert classify_action("GET", "", 200) == "page_view"


# =============================================================================
# _get_client_ip
# =============================================================================


class TestGetClientIp:
    """客户端 IP 提取测试。"""

    def _make_request(self, headers=None, client_host=None):
        request = MagicMock()
        request.headers = headers or {}
        request.client = MagicMock()
        request.client.host = client_host
        return request

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 取第一个 IP。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "203.0.113.1, 198.51.100.2, 10.0.0.1"},
            client_host="10.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip(self):
        """X-Real-IP 优先于 client.host。"""
        request = self._make_request(
            headers={"X-Real-IP": "203.0.113.5"},
            client_host="10.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.5"

    def test_x_forwarded_for_precedes_x_real_ip(self):
        """X-Forwarded-For 优先于 X-Real-IP。"""
        request = self._make_request(
            headers={
                "X-Forwarded-For": "203.0.113.1",
                "X-Real-IP": "198.51.100.1",
            },
            client_host="10.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_fallback_to_client_host(self):
        """无代理头时回退到 client.host。"""
        request = self._make_request(headers={}, client_host="192.168.1.1")
        assert _get_client_ip(request) == "192.168.1.1"

    def test_empty_when_nothing_available(self):
        """没有任何可用 IP 时返回空字符串。"""
        request = self._make_request(headers={})
        request.client = None
        assert _get_client_ip(request) == ""

    def test_single_ip_in_forwarded_for(self):
        """X-Forwarded-For 单个 IP。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "203.0.113.1"},
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_forwarded_for_with_whitespace(self):
        """X-Forwarded-For 带空格。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "  203.0.113.1  ,  198.51.100.2  "},
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_ipv6_in_forwarded_for(self):
        """X-Forwarded-For 中的 IPv6。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "2001:db8::1, 10.0.0.1"},
        )
        assert _get_client_ip(request) == "2001:db8::1"


# =============================================================================
# 跳过路径常量
# =============================================================================


class TestSkipPaths:
    """跳过路径常量验证。"""

    def test_skip_paths_match(self):
        """确认跳过路径集合包含预期的路径。"""
        assert "/docs" in _SKIP_PATHS
        assert "/openapi.json" in _SKIP_PATHS
        assert "/redoc" in _SKIP_PATHS
        assert "/favicon.ico" in _SKIP_PATHS

    def test_skip_prefixes_match(self):
        """确认跳过前缀包含预期的前缀。"""
        assert "/static/" in _SKIP_PREFIXES
        assert "/assets/" in _SKIP_PREFIXES

    def test_skip_prefix_not_skip_path(self):
        """确认 /api/ 不在跳过列表中。"""
        assert "/api/" not in _SKIP_PREFIXES