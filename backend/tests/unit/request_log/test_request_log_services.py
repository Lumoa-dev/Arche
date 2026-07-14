"""请求日志服务测试 —— classify_action、_get_client_ip、LogAggregationService。

测试原则：
- 只测公开方法输入输出，不测内部实现
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    classify_action,
)


# =============================================================================
# classify_action 行为分类测试
# =============================================================================


class TestClassifyAction:
    """测试请求行为分类函数。"""

    def test_login_fail_on_login_path_with_4xx(self):
        """登录路径且状态码 >= 400 应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_success_is_api_call(self):
        """登录成功（状态码 < 400）应返回 api_call。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_path_is_api_call(self):
        """以 /api/ 开头的路径应返回 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/ip-ban/bans", 201) == "api_call"

    def test_get_non_api_is_page_view(self):
        """非 API 的 GET 请求应返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"

    def test_non_get_non_api_is_other(self):
        """非 API 的非 GET 请求应返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/settings", 200) == "other"

    def test_api_path_with_4xx_still_api_call(self):
        """API 路径的 4xx 响应仍应返回 api_call（非 login 路径）。"""
        assert classify_action("GET", "/api/blog/posts", 404) == "api_call"
        assert classify_action("POST", "/api/ip-ban/bans", 403) == "api_call"


# =============================================================================
# _get_client_ip 测试
# =============================================================================


class TestGetClientIp:
    """测试客户端 IP 提取函数。"""

    def _make_request(self, headers: dict | None = None, client_host: str | None = "127.0.0.1"):
        """创建模拟 Request 对象。"""
        request = MagicMock()
        request.headers = headers or {}
        request.client = MagicMock()
        request.client.host = client_host
        return request

    def test_x_forwarded_for_takes_priority(self):
        """X-Forwarded-For 应优先于 X-Real-IP 和 client.host。"""
        request = self._make_request(
            headers={
                "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
                "X-Real-IP": "192.168.1.1",
            },
            client_host="127.0.0.1",
        )
        from backend.plugins.request_log.services import _get_client_ip

        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip_second_priority(self):
        """无 X-Forwarded-For 时，X-Real-IP 应被使用。"""
        request = self._make_request(
            headers={"X-Real-IP": "192.168.1.100"},
            client_host="127.0.0.1",
        )
        from backend.plugins.request_log.services import _get_client_ip

        assert _get_client_ip(request) == "192.168.1.100"

    def test_client_host_as_fallback(self):
        """无代理头时，应使用 client.host。"""
        request = self._make_request(headers={}, client_host="203.0.113.50")
        from backend.plugins.request_log.services import _get_client_ip

        assert _get_client_ip(request) == "203.0.113.50"

    def test_empty_when_no_ip_available(self):
        """没有任何 IP 信息时应返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        from backend.plugins.request_log.services import _get_client_ip

        assert _get_client_ip(request) == ""


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    """测试日志聚合服务。"""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """start/stop 不应抛出异常。"""
        from backend.plugins.request_log.services import LogAggregationService

        svc = LogAggregationService()
        # 未安装 APScheduler 时，start 应静默跳过
        svc.start()
        svc.stop()  # 不应报错

    @pytest.mark.asyncio
    async def test_double_start_does_not_crash(self):
        """重复 start 不应创建多个调度器。"""
        from backend.plugins.request_log.services import LogAggregationService

        svc = LogAggregationService()
        svc.start()
        scheduler = svc._scheduler
        svc.start()  # 第二次 start，应无操作
        assert svc._scheduler is scheduler
        svc.stop()


# =============================================================================
# 跳过路径测试
# =============================================================================


class TestSkipPaths:
    """测试请求日志跳过路径逻辑。"""

    def test_skip_docs_path(self):
        """/docs 路径应被跳过。"""
        from backend.plugins.request_log.services import _SKIP_PATHS

        assert "/docs" in _SKIP_PATHS

    def test_skip_favicon(self):
        """/favicon.ico 应被跳过。"""
        from backend.plugins.request_log.services import _SKIP_PATHS

        assert "/favicon.ico" in _SKIP_PATHS

    def test_skip_static_prefix(self):
        """/static/ 前缀应被跳过。"""
        from backend.plugins.request_log.services import _SKIP_PREFIXES

        assert any("/static/" in p for p in _SKIP_PREFIXES)