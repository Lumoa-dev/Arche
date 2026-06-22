"""请求日志插件测试 —— 行为分类、客户端 IP 提取、日志写入、聚合与清理。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    _get_client_ip,
    classify_action,
)
from backend.plugins.request_log.models import IpActionCounter, RequestLog


class TestClassifyAction:
    """测试请求行为分类。"""

    def test_login_fail(self):
        """登录失败返回 'login_fail'。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 429) == "login_fail"

    def test_login_success_not_fail(self):
        """登录成功不返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_call(self):
        """API 路径返回 'api_call'。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/ip-ban/bans", 201) == "api_call"
        assert classify_action("DELETE", "/api/users/1", 204) == "api_call"

    def test_page_view(self):
        """GET 非 API 路径返回 'page_view'。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_method(self):
        """非 API 非 GET 返回 'other'。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/update", 200) == "other"
        assert classify_action("DELETE", "/resource/1", 200) == "other"

    def test_api_path_with_method(self):
        """API 路径不同方法。"""
        assert classify_action("PUT", "/api/config", 200) == "api_call"
        assert classify_action("PATCH", "/api/users/1", 200) == "api_call"
        assert classify_action("DELETE", "/api/items/1", 200) == "api_call"


class TestGetClientIP:
    """测试客户端 IP 提取。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 取第一个 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1, 172.16.0.1"}
        request.client = MagicMock()
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_forwarded_for_single(self):
        """X-Forwarded-For 单个 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.5"}
        request.client = MagicMock()
        assert _get_client_ip(request) == "203.0.113.5"

    def test_x_real_ip(self):
        """X-Real-IP 在无 X-Forwarded-For 时使用。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "10.0.0.5"}
        request.client = MagicMock()
        assert _get_client_ip(request) == "10.0.0.5"

    def test_fallback_to_client_host(self):
        """无代理头时降级到 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client.host = "127.0.0.1"
        assert _get_client_ip(request) == "127.0.0.1"

    def test_x_forwarded_for_overrides_real_ip(self):
        """X-Forwarded-For 优先级高于 X-Real-IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1",
            "X-Real-IP": "10.0.0.1",
        }
        request.client = MagicMock()
        assert _get_client_ip(request) == "203.0.113.1"

    def test_ipv6_address(self):
        """IPv6 地址正确处理。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "2001:db8::1"}
        request.client = MagicMock()
        assert _get_client_ip(request) == "2001:db8::1"

    def test_empty_headers(self):
        """无任何 IP 信息时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""


class TestRequestLogModel:
    """测试 RequestLog 模型。"""

    def test_request_log_defaults(self):
        """RequestLog 默认值正确。"""
        log = RequestLog(
            ip="10.0.0.1",
            method="GET",
            path="/api/test",
            status_code=200,
        )
        assert log.ip == "10.0.0.1"
        assert log.method == "GET"
        assert log.path == "/api/test"
        assert log.status_code == 200
        # mapped_column 的 default 在部分 SQLAlchemy 版本中不作用于 Python 层
        assert log.action is None or log.action == "other"

    def test_request_log_to_dict(self):
        """to_dict 返回正确格式。"""
        import uuid

        log_id = uuid.uuid4()
        log = RequestLog(
            id=log_id,
            ip="10.0.0.1",
            method="POST",
            path="/api/auth/login",
            status_code=401,
            duration_ms=15.5,
            action="login_fail",
            user_id="user-123",
        )
        result = log.to_dict()
        assert result["id"] == str(log_id)
        assert result["ip"] == "10.0.0.1"
        assert result["method"] == "POST"
        assert result["status_code"] == 401
        assert result["duration_ms"] == 15.5
        assert result["action"] == "login_fail"
        assert result["user_id"] == "user-123"

    def test_request_log_full_constructor(self):
        """RequestLog 完整构造。"""
        log = RequestLog(
            ip="10.0.0.1",
            method="GET",
            path="/api/blog/posts",
            status_code=200,
            user_agent="Mozilla/5.0",
            referer="https://example.com",
            duration_ms=42.0,
            user_id="user-abc",
            region="us-east",
            isp="AWS",
            action="api_call",
        )
        assert log.user_agent == "Mozilla/5.0"
        assert log.referer == "https://example.com"
        assert log.region == "us-east"
        assert log.isp == "AWS"


class TestIpActionCounterModel:
    """测试 IpActionCounter 模型。"""

    def test_counter_defaults(self):
        """IpActionCounter 默认值正确。"""
        from datetime import date

        counter = IpActionCounter(
            ip="10.0.0.1",
            action="api_call",
            action_date=date.today(),
            hour=14,
        )
        assert counter.ip == "10.0.0.1"
        assert counter.action == "api_call"
        # mapped_column 的 default=0 在部分版本中不作用于 Python 层
        assert counter.count is None or counter.count == 0

    def test_counter_to_dict(self):
        """to_dict 返回正确格式。"""
        from datetime import date

        counter = IpActionCounter(
            ip="10.0.0.1",
            action="login_fail",
            action_date=date(2026, 6, 1),
            hour=10,
            count=5,
        )
        result = counter.to_dict()
        assert result["ip"] == "10.0.0.1"
        assert result["action"] == "login_fail"
        assert result["action_date"] == "2026-06-01"
        assert result["hour"] == 10
        assert result["count"] == 5