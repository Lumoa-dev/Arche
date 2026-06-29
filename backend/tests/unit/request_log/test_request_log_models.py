"""RequestLog 模型与工具函数单元测试。

测试原则：
- classify_action 为纯函数，无需数据库
- _get_client_ip 仅依赖 request.headers，可直接 mock
- 模型 to_dict 验证序列化格式
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.plugins.request_log.services import (
    _get_client_ip,
    classify_action,
)


# =============================================================================
# classify_action
# =============================================================================


class TestClassifyAction:
    """测试请求行为分类。"""

    def test_login_failure(self):
        """登录失败的请求应归类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"

    def test_login_success_not_login_fail(self):
        """登录成功不应归类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) != "login_fail"

    def test_api_call(self):
        """API 路径应归类为 api_call。"""
        assert classify_action("GET", "/api/posts", 200) == "api_call"
        assert classify_action("POST", "/api/posts", 201) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_page_view(self):
        """GET 非 API 请求应归类为 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_methods(self):
        """非 GET 且非 API 的请求应归类为 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/upload", 200) == "other"

    def test_edge_cases(self):
        """边界情况处理。"""
        # 空路径
        result = classify_action("GET", "", 200)
        assert result in ("page_view", "other")

        # 4xx 但非登录路径
        assert classify_action("GET", "/some-page", 404) == "page_view"


# =============================================================================
# _get_client_ip
# =============================================================================


class TestGetClientIp:
    """测试客户端 IP 提取。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 取第一个 IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1, 192.168.1.1"
        }
        request.client.host = "10.0.0.1"
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip_override(self):
        """X-Real-IP 应优先于 client.host。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "198.51.100.1"}
        request.client.host = "10.0.0.1"
        assert _get_client_ip(request) == "198.51.100.1"

    def test_x_forwarded_for_preferred_over_real_ip(self):
        """X-Forwarded-For 应优先于 X-Real-IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1",
            "X-Real-IP": "198.51.100.1",
        }
        assert _get_client_ip(request) == "203.0.113.1"

    def test_fallback_to_client_host(self):
        """无代理头时应退回到 client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client.host = "192.168.1.1"
        assert _get_client_ip(request) == "192.168.1.1"

    def test_empty_when_no_source(self):
        """没有任何来源时应返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""

    def test_ipv6_in_x_forwarded_for(self):
        """X-Forwarded-For 中的 IPv6 地址应正确提取。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "2001:db8::1, 10.0.0.1"
        }
        assert _get_client_ip(request) == "2001:db8::1"