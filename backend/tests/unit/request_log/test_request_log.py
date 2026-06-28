"""请求日志 — 服务层单元测试。

覆盖：
- classify_action 行为分类函数
- _get_client_ip IP 提取函数（纯函数部分）
- 跳过路径逻辑

纯 mock，无数据库依赖。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from backend.plugins.request_log.services import (
    _SKIP_PATHS,
    _get_client_ip,
    classify_action,
)


class TestClassifyAction:
    """行为分类函数测试。"""

    def test_login_fail_path_4xx(self):
        """登录路径 + 4xx → login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"

    def test_login_fail_path_5xx(self):
        """登录路径 + 5xx → login_fail。"""
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_fail_path_2xx(self):
        """登录路径 + 2xx → api_call（登录成功不算失败）。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_prefix(self):
        assert classify_action("GET", "/api/posts", 200) == "api_call"
        assert classify_action("POST", "/api/posts", 201) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_get_non_api(self):
        """GET 请求且非 /api/* → page_view。"""
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/", 200) == "page_view"

    def test_get_api_subpath(self):
        """GET /api/* 仍为 api_call。"""
        assert classify_action("GET", "/api/health", 200) == "api_call"

    def test_other_methods(self):
        """非 GET 且非 /api/* → other。"""
        assert classify_action("POST", "/upload", 200) == "other"
        assert classify_action("PUT", "/settings", 200) == "other"
        assert classify_action("PATCH", "/profile", 200) == "other"

    def test_login_fail_case_sensitive(self):
        """路径大小写敏感 — 大写路径不匹配。"""
        # /api/ 大小写敏感，/API/ 不匹配前缀，GET 以外的 method 则走 other
        assert classify_action("POST", "/API/AUTH/LOGIN", 401) == "other"
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"


class TestSkipPaths:
    """跳过路径常量验证。"""

    def test_skip_paths_contains_docs(self):
        assert "/docs" in _SKIP_PATHS

    def test_skip_paths_contains_openapi(self):
        assert "/openapi.json" in _SKIP_PATHS

    def test_skip_paths_contains_redoc(self):
        assert "/redoc" in _SKIP_PATHS

    def test_skip_paths_contains_favicon(self):
        assert "/favicon.ico" in _SKIP_PATHS


class TestGetClientIp:
    """_get_client_ip 函数测试。"""

    def _make_request(self, headers: dict | None = None, client_host: str | None = None):
        """构造一个 mock Request。"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "client": (client_host, 12345) if client_host else None,
        }
        req = Request(scope)
        # 模拟 headers（scope 外的另加）
        if headers:
            for k, v in headers.items():
                if v:
                    req.headers._list.append((k.lower().encode(), v.encode()))
        return req

    def test_x_forwarded_for_priority(self):
        """X-Forwarded-For 优先级最高。"""
        req = self._make_request(
            headers={
                "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
                "X-Real-IP": "10.0.0.2",
            },
            client_host="172.16.0.1",
        )
        ip = _get_client_ip(req)
        assert ip == "203.0.113.1"

    def test_x_real_ip_fallback(self):
        """无 X-Forwarded-For 时用 X-Real-IP。"""
        req = self._make_request(
            headers={"X-Real-IP": "10.0.0.5"},
            client_host="172.16.0.1",
        )
        ip = _get_client_ip(req)
        assert ip == "10.0.0.5"

    def test_client_host_fallback(self):
        """无代理头时用 client.host。"""
        req = self._make_request(
            headers={"X-Forwarded-For": "", "X-Real-IP": ""},
            client_host="192.168.1.10",
        )
        ip = _get_client_ip(req)
        assert ip == "192.168.1.10"

    def test_all_empty(self):
        """无任何 IP 信息时返回空字符串。"""
        req = self._make_request()
        ip = _get_client_ip(req)
        assert ip == ""

    def test_x_forwarded_for_multiple_ips(self):
        """多 IP 时应取第一个。"""
        req = self._make_request(
            headers={"X-Forwarded-For": "198.51.100.1, 198.51.100.2, 198.51.100.3"}
        )
        ip = _get_client_ip(req)
        assert ip == "198.51.100.1"

    def test_x_forwarded_for_with_spaces(self):
        """带空格的 IP 应 strip。"""
        req = self._make_request(
            headers={"X-Forwarded-For": "  198.51.100.1  ,  10.0.0.1  "}
        )
        ip = _get_client_ip(req)
        assert ip == "198.51.100.1"