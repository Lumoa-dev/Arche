"""请求日志服务测试 —— classify_action / _get_client_ip。"""

from unittest.mock import MagicMock

import pytest

from backend.plugins.request_log.services import (
    classify_action,
    _get_client_ip,
)


class TestClassifyAction:
    """测试请求行为分类函数。"""

    def test_login_failure(self):
        """登录失败返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"

    def test_login_success_not_fail(self):
        """登录成功不返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) != "login_fail"

    def test_api_call(self):
        """API 路径返回 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/auth/register", 201) == "api_call"
        assert classify_action("DELETE", "/api/admin/users/1", 204) == "api_call"

    def test_page_view(self):
        """GET 请求非 API 路径返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_method(self):
        """非 GET 非 API 路径返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/custom", 200) == "other"
        assert classify_action("PATCH", "/resource", 200) == "other"

    def test_api_path_with_login_fail_status(self):
        """API 路径 + 登录失败状态码 ⇒ login_fail。"""
        result = classify_action("POST", "/api/auth/login", 401)
        assert result == "login_fail"

    def test_edge_cases(self):
        """边界情况。"""
        # 空方法
        assert classify_action("", "/api/test", 200) == "api_call"
        # 根路径
        assert classify_action("GET", "/", 200) == "page_view"
        # 带查询参数
        assert classify_action("GET", "/api/search?q=test", 200) == "api_call"


class TestGetClientIp:
    """测试客户端 IP 获取函数。"""

    def test_x_forwarded_for(self):
        """X-Forwarded-For 头部优先。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
            "X-Real-IP": "10.0.0.1",
        }
        request.client.host = "172.16.0.1"
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip(self):
        """无 X-Forwarded-For 时使用 X-Real-IP。"""
        request = MagicMock()
        request.headers = {
            "X-Real-IP": "10.0.0.1",
        }
        request.client.host = "172.16.0.1"
        assert _get_client_ip(request) == "10.0.0.1"

    def test_request_client_host(self):
        """无代理头部时使用 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client.host = "172.16.0.1"
        assert _get_client_ip(request) == "172.16.0.1"

    def test_empty_headers_and_no_client(self):
        """无任何 IP 信息时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""

    def test_malformed_forwarded_for(self):
        """X-Forwarded-For 格式异常时取第一段。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": " invalid-ip , 10.0.0.1"}
        request.client.host = "172.16.0.1"
        result = _get_client_ip(request)
        assert result == "invalid-ip"

    def test_x_real_ip_empty(self):
        """X-Real-IP 为空时跳过。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": ""}
        request.client.host = "172.16.0.1"
        assert _get_client_ip(request) == "172.16.0.1"

    def test_priority_order(self):
        """优先级顺序：X-Forwarded-For > X-Real-IP > client.host。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "1.1.1.1",
            "X-Real-IP": "2.2.2.2",
        }
        request.client.host = "3.3.3.3"
        assert _get_client_ip(request) == "1.1.1.1"

        request.headers = {"X-Real-IP": "2.2.2.2"}
        assert _get_client_ip(request) == "2.2.2.2"

        request.headers = {}
        assert _get_client_ip(request) == "3.3.3.3"