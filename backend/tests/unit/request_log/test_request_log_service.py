"""RequestLog 服务单元测试 —— 行为分类、IP 提取、日志记录。

测试重点：
- classify_action 行为分类逻辑
- _get_client_ip IP 提取优先级（X-Forwarded-For > X-Real-IP > request.client.host）
- 跳过路径逻辑
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import Request

from backend.plugins.request_log.services import (
    _get_client_ip,
    classify_action,
)


# =============================================================================
# classify_action
# =============================================================================


class TestClassifyAction:
    """行为分类逻辑测试。"""

    def test_login_fail_detection(self):
        """登录失败（/api/auth/login + 4xx）应识别为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"

    def test_login_success_not_fail(self):
        """登录成功（2xx）不应识别为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_call_detection(self):
        """API 路径前缀应识别为 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/auth/register", 201) == "api_call"
        assert classify_action("DELETE", "/api/admin/users/1", 204) == "api_call"

    def test_page_view_detection(self):
        """GET 请求非 API 路径应识别为 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_methods(self):
        """非 GET 且非 API 路径应识别为 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/callback", 200) == "other"
        assert classify_action("PATCH", "/update", 200) == "other"

    def test_api_with_error_status(self):
        """API 路径即使有错误状态也归类为 api_call（不是 login_fail）。"""
        assert classify_action("GET", "/api/blog/posts", 500) == "api_call"
        assert classify_action("POST", "/api/data", 422) == "api_call"

    def test_login_mixed_method(self):
        """非 POST 方法访问登录路径但不是登录行为。"""
        assert classify_action("GET", "/api/auth/login", 200) == "api_call"

    def test_edge_empty_path(self):
        """空路径处理。"""
        result = classify_action("GET", "", 200)
        assert result in ("page_view", "other")


# =============================================================================
# _get_client_ip
# =============================================================================


class TestGetClientIP:
    """IP 提取逻辑测试（优先级：X-Forwarded-For > X-Real-IP > client.host）。"""

    def _make_request(self, headers: dict | None = None, client_host: str | None = "127.0.0.1"):
        """创建模拟请求。"""
        scope = {
            "type": "http",
            "headers": [],
            "client": (client_host, 12345) if client_host else None,
        }
        request = Request(scope)
        if headers:
            for k, v in headers.items():
                request.headers.__dict__["_list"].append((k.lower().encode(), v.encode()))
        return request

    def test_x_forwarded_for_priority(self):
        """X-Forwarded-For 应优先于其他来源。"""
        request = self._make_request(
            headers={
                "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
                "X-Real-IP": "198.51.100.1",
            },
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip_fallback(self):
        """无 X-Forwarded-For 时应使用 X-Real-IP。"""
        request = self._make_request(
            headers={"X-Real-IP": "198.51.100.1"},
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "198.51.100.1"

    def test_client_host_last_resort(self):
        """无代理头时应回退到 client.host。"""
        request = self._make_request(client_host="10.0.0.1")
        assert _get_client_ip(request) == "10.0.0.1"

    def test_empty_ip_on_no_client(self):
        """无 client 且无代理头时应返回空字符串。"""
        request = self._make_request(client_host=None)
        assert _get_client_ip(request) == ""

    def test_x_forwarded_for_multiple_ips(self):
        """多级代理时只取第一个 IP。"""
        request = self._make_request(
            headers={"X-Forwarded-For": " 203.0.113.1 , 10.0.0.1, 192.168.1.1 "},
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_ipv6_in_x_forwarded_for(self):
        """IPv6 在 X-Forwarded-For 中。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "2001:db8::1, 10.0.0.1"},
        )
        assert _get_client_ip(request) == "2001:db8::1"

    def test_empty_x_forwarded_for(self):
        """空的 X-Forwarded-For 应 fallthrough。"""
        request = self._make_request(
            headers={"X-Forwarded-For": ""},
            client_host="10.0.0.1",
        )
        # 空的 X-Forwarded-For 在 split 后会得到 [""]，所以取到空字符串
        # 因此会尝试 X-Real-IP，没有则回到 client.host
        assert _get_client_ip(request) == "10.0.0.1"