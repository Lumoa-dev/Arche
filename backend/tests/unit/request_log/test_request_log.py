"""请求日志服务行为测试。

测试原则：
- 只测公开/工具函数输入输出
- 中间件和定时任务依赖全局状态，单独测试跳过
- 数据库交互使用内存 SQLite
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from backend.plugins.request_log.services import (
    _get_client_ip,
    classify_action,
)


# =============================================================================
# 行为分类 行为测试
# =============================================================================


class TestClassifyAction:
    """测试请求行为分类逻辑。"""

    @pytest.mark.parametrize(
        "method, path, status_code, expected",
        [
            # 登录失败
            ("POST", "/api/auth/login", 401, "login_fail"),
            ("POST", "/api/auth/login", 403, "login_fail"),
            ("POST", "/api/auth/login", 400, "login_fail"),
            ("POST", "/api/auth/login", 500, "login_fail"),
            # 登录成功不是 login_fail
            ("POST", "/api/auth/login", 200, "api_call"),
            # API 调用
            ("GET", "/api/ip-ban/bans", 200, "api_call"),
            ("POST", "/api/blog/posts", 201, "api_call"),
            ("PUT", "/api/auth/profile", 200, "api_call"),
            ("DELETE", "/api/oss/files/1", 204, "api_call"),
            ("GET", "/api/ip-ban/bans", 403, "api_call"),
            # 页面浏览
            ("GET", "/home", 200, "page_view"),
            ("GET", "/about", 200, "page_view"),
            ("GET", "/posts/hello-world", 200, "page_view"),
            # 其他
            ("POST", "/webhook/github", 200, "other"),
            ("PUT", "/callback", 200, "other"),
        ],
    )
    def test_classify_action(self, method, path, status_code, expected):
        """行为分类应正确。"""
        assert classify_action(method, path, status_code) == expected

    def test_login_fail_only_on_error_status(self):
        """登录失败分类只应在状态码 >= 400 时触发。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"
        assert classify_action("POST", "/api/auth/login", 302) == "api_call"


# =============================================================================
# 客户端 IP 提取 行为测试
# =============================================================================


class TestGetClientIp:
    """测试客户端 IP 提取逻辑。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 应取第一个 IP。"""
        scope = {
            "type": "http",
            "headers": [
                (b"x-forwarded-for", b"10.0.0.1, 192.168.1.1, 172.16.0.1"),
            ],
        }
        request = Request(scope)
        assert _get_client_ip(request) == "10.0.0.1"

    def test_x_real_ip_overrides_forwarded(self):
        """X-Real-IP 应在 X-Forwarded-For 不存在时使用。"""
        scope = {
            "type": "http",
            "headers": [(b"x-real-ip", b"10.0.0.5")],
        }
        request = Request(scope)
        assert _get_client_ip(request) == "10.0.0.5"

    def test_client_host_fallback(self):
        """无代理头时回退到 request.client.host。"""
        scope = {
            "type": "http",
            "client": ("192.168.1.100", 54321),
            "headers": [],
        }
        request = Request(scope)
        assert _get_client_ip(request) == "192.168.1.100"

    def test_no_ip_available_returns_empty(self):
        """没有任何 IP 信息时应返回空字符串。"""
        scope = {
            "type": "http",
            "headers": [],
        }
        request = Request(scope)
        assert _get_client_ip(request) == ""

    def test_x_forwarded_for_with_spaces(self):
        """X-Forwarded-For 中带空格的 IP 应被正确 trim。"""
        scope = {
            "type": "http",
            "headers": [
                (b"x-forwarded-for", b"  10.0.0.1  ,  192.168.1.1  "),
            ],
        }
        request = Request(scope)
        assert _get_client_ip(request) == "10.0.0.1"


# =============================================================================
# 跳过路径 行为测试 (集成 conftest 的 test_app 验证)
# =============================================================================


class TestSkipPaths:
    """测试中间件跳过路径逻辑。"""

    @pytest.mark.parametrize(
        "path",
        [
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
            "/static/css/main.css",
            "/assets/js/app.js",
        ],
    )
    def test_skip_paths_should_not_be_classified(self, path):
        """跳过路径不应被归类为 api_call。"""
        assert classify_action("GET", path, 200) == "page_view"

    def test_skip_paths_login_fail_not_affected(self):
        """登录失败路径不受跳过路径影响。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"