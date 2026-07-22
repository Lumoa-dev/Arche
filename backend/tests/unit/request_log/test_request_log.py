"""请求日志插件 单元测试。

测试覆盖：
- classify_action: 行为分类逻辑（login_fail, api_call, page_view, other）
- _get_client_ip: IP 提取（X-Forwarded-For, X-Real-IP, client.host, 空值）
- LogAggregationService: 定时聚合和 TTL 清理（启动/停止/任务异常处理）
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    LogAggregationService,
    _get_client_ip,
    classify_action,
)


# =============================================================================
# classify_action 测试
# =============================================================================


class TestClassifyAction:
    def test_login_path_with_4xx_returns_login_fail(self):
        """登录路径且状态码 >= 400 应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_path_with_2xx_returns_api_call(self):
        """登录路径且状态码 < 400 应返回 api_call。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_prefix_returns_api_call(self):
        """以 /api/ 开头的路径应返回 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/admin/config", 200) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_get_non_api_returns_page_view(self):
        """非 API 的 GET 请求应返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_methods_return_other(self):
        """非 GET 且非 API 的请求应返回 other。"""
        assert classify_action("POST", "/upload", 200) == "other"
        assert classify_action("PUT", "/profile", 200) == "other"
        assert classify_action("DELETE", "/item", 200) == "other"


# =============================================================================
# _get_client_ip 测试
# =============================================================================


class TestGetClientIp:
    def test_x_forwarded_for_returns_first_ip(self, monkeypatch):
        """X-Forwarded-For 存在时应返回第一个 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}
        request.client = MagicMock(host="unused")
        result = _get_client_ip(request)
        assert result == "1.2.3.4"

    def test_x_real_ip_returns_ip(self, monkeypatch):
        """X-Real-IP 存在时应返回其值。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "10.0.0.1"}
        request.client = MagicMock(host="unused")
        result = _get_client_ip(request)
        assert result == "10.0.0.1"

    def test_fallback_to_client_host(self):
        """无代理头时应回退到 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="127.0.0.1")
        result = _get_client_ip(request)
        assert result == "127.0.0.1"

    def test_no_client_returns_empty_string(self):
        """无 client 且无代理头时应返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        result = _get_client_ip(request)
        assert result == ""

    def test_priority_x_forwarded_for_over_x_real_ip(self):
        """X-Forwarded-For 优先级高于 X-Real-IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "1.1.1.1, 2.2.2.2",
            "X-Real-IP": "9.9.9.9",
        }
        request.client = MagicMock(host="unused")
        result = _get_client_ip(request)
        assert result == "1.1.1.1"

    def test_empty_forwarded_for_falls_through(self, monkeypatch):
        """X-Forwarded-For 为空时回退到 X-Real-IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "", "X-Real-IP": "8.8.8.8"}
        request.client = MagicMock(host="unused")
        result = _get_client_ip(request)
        assert result == "8.8.8.8"


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    @pytest.fixture
    def service(self):
        return LogAggregationService()

    @pytest.mark.asyncio
    async def test_start_stop_no_scheduler(self, service):
        """start/stop 应正常工作。"""
        service.start()
        # 再次调用 start 不应重复创建
        service.start()
        service.stop()
        # 停止后再次 stop 不应抛异常
        service.stop()

    def test_start_without_apscheduler(self, service):
        """APScheduler 未安装时 start 不应抛异常。"""
        with patch.dict("sys.modules", {"apscheduler.schedulers.asyncio": None}):
            # 重新 import 会触发 ImportError 处理
            service.start()
            # 不抛异常即为通过

    @pytest.mark.asyncio
    async def test_aggregate_job_exception_handled(self, service):
        """聚合任务异常应被捕获不抛到外层。"""
        import backend.plugins.request_log.services as rl_services

        with patch.object(
            rl_services, "_get_session_factory", side_effect=Exception("db error")
        ):
            # 不应抛异常
            await service._aggregate_job()

    @pytest.mark.asyncio
    async def test_cleanup_job_exception_handled(self, service):
        """清理任务异常应被捕获不抛到外层。"""
        import backend.plugins.request_log.services as rl_services

        with patch.object(
            rl_services, "_get_session_factory", side_effect=Exception("db error")
        ):
            # 不应抛异常
            await service._cleanup_job()

    @pytest.mark.asyncio
    async def test_aggregate_job_empty_result(self, service):
        """无数据时聚合任务应正常完成不报错。"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value.all.return_value = []
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            # 不应抛异常
            await service._aggregate_job()