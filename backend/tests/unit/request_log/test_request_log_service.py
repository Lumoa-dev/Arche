"""请求日志插件 — 服务与中间件测试。

风险：RequestLogMiddleware 是全局中间件，记录每个请求的明细日志。
classify_action 逻辑错误会导致行为分类错误。LogAggregationService
的定时聚合和 TTL 清理逻辑错误会导致数据丢失或膨胀。
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    LogAggregationService,
    RequestLogMiddleware,
    _get_client_ip,
    _get_session_factory,
    classify_action,
)


class TestClassifyAction:
    """测试请求行为分类。"""

    def test_login_fail(self):
        """登录失败应分类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"

    def test_login_success(self):
        """登录成功应分类为 api_call。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_call(self):
        """API 路径应分类为 api_call。"""
        assert classify_action("GET", "/api/users", 200) == "api_call"
        assert classify_action("POST", "/api/posts", 201) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_page_view(self):
        """GET 非 API 请求应分类为 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_methods(self):
        """非 API 的非 GET 请求应分类为 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/webhook/config", 200) == "other"


class TestGetClientIP:
    """测试客户端 IP 获取。"""

    def test_x_forwarded_for(self):
        """X-Forwarded-For 优先。"""
        request = MagicMock()
        request.headers.get.side_effect = lambda key, default="": {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
            "X-Real-IP": "10.0.0.1",
        }.get(key, default)
        request.client.host = "10.0.0.1"
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip(self):
        """无 X-Forwarded-For 时使用 X-Real-IP。"""
        request = MagicMock()
        request.headers.get.side_effect = lambda key, default="": {
            "X-Real-IP": "203.0.113.1",
        }.get(key, default)
        request.client.host = "10.0.0.1"
        assert _get_client_ip(request) == "203.0.113.1"

    def test_client_host(self):
        """无代理头时使用 client.host。"""
        request = MagicMock()
        request.headers.get.return_value = ""
        request.client.host = "203.0.113.1"
        assert _get_client_ip(request) == "203.0.113.1"

    def test_no_client(self):
        """无任何信息时返回空字符串。"""
        request = MagicMock()
        request.headers.get.return_value = ""
        request.client = None
        assert _get_client_ip(request) == ""


class TestGetSessionFactory:
    """测试获取会话工厂。"""

    def test_get_session_factory_success(self):
        """成功获取会话工厂。"""
        mock_factory = MagicMock()
        with patch(
            "backend.core.container.container"
        ) as mock_container:
            mock_container.get.return_value = {"session_factory": mock_factory}
            result = _get_session_factory()
            assert result is mock_factory

    def test_get_session_factory_failure(self):
        """获取失败时返回 None。"""
        with patch(
            "backend.core.container.container"
        ) as mock_container:
            mock_container.get.side_effect = Exception("Not ready")
            result = _get_session_factory()
            assert result is None


class TestRequestLogMiddleware:
    """测试请求日志中间件。"""

    @pytest.fixture
    def middleware(self):
        app = MagicMock()
        return RequestLogMiddleware(app)

    @pytest.mark.asyncio
    async def test_skip_paths(self, middleware):
        """跳过路径应直接放行不记录日志。"""
        for skip_path in ("/docs", "/openapi.json", "/redoc", "/favicon.ico"):
            request = MagicMock()
            request.url.path = skip_path
            call_next = AsyncMock()
            with patch(
                "backend.plugins.request_log.services._write_log_async"
            ) as mock_write:
                await middleware.dispatch(request, call_next)
                call_next.assert_called()
                mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_prefixes(self, middleware):
        """跳过前缀应直接放行。"""
        for prefix_path in ("/static/style.css", "/assets/logo.png"):
            request = MagicMock()
            request.url.path = prefix_path
            call_next = AsyncMock()
            with patch(
                "backend.plugins.request_log.services._write_log_async"
            ) as mock_write:
                await middleware.dispatch(request, call_next)
                call_next.assert_called()
                mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_normal_request_logged(self, middleware):
        """正常请求应异步记录日志。"""
        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers.get.return_value = ""
        request.client.host = "192.168.1.1"

        call_next = AsyncMock()

        with patch(
            "backend.plugins.request_log.services._write_log_async"
        ) as mock_write:
            await middleware.dispatch(request, call_next)
            call_next.assert_called()
            # 验证异步写日志被调用
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_exception_still_logged(self, middleware):
        """请求异常时仍应记录日志。"""
        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers.get.return_value = ""
        request.client.host = "192.168.1.1"

        call_next = AsyncMock(side_effect=Exception("Test error"))

        with patch(
            "backend.plugins.request_log.services._write_log_async"
        ) as mock_write:
            with pytest.raises(Exception, match="Test error"):
                await middleware.dispatch(request, call_next)
            mock_write.assert_called_once()


class TestLogAggregationService:
    """测试日志聚合服务。"""

    @pytest.fixture
    def service(self):
        return LogAggregationService()

    def test_start_twice(self, service):
        """多次 start 不应重复创建调度器。"""
        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler_cls:
            mock_scheduler = MagicMock()
            mock_scheduler_cls.return_value = mock_scheduler

            service.start()
            service.start()  # 第二次调用
            # 只应创建一次调度器
            mock_scheduler_cls.assert_called_once()

    def test_stop_without_start(self, service):
        """未启动时 stop 不应抛出异常。"""
        service.stop()  # 不应抛出异常

    def test_stop_stops_scheduler(self, service):
        """stop 应关闭调度器。"""
        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler_cls:
            mock_scheduler = MagicMock()
            mock_scheduler.running = True
            mock_scheduler_cls.return_value = mock_scheduler

            service.start()
            service.stop()
            mock_scheduler.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_aggregate_job(self, service):
        """聚合任务应正确处理数据。"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.all.return_value = []
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            await service._aggregate_job()
            # 验证 execute 被调用（执行了查询）
            mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_cleanup_job(self, service):
        """清理任务应删除过期日志。"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar.return_value = 5
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            await service._cleanup_job()
            # 验证 commit 被调用
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_aggregate_job_exception_handled(self, service):
        """聚合任务异常不应传播。"""
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            side_effect=Exception("DB error"),
        ):
            # 不应抛出异常
            await service._aggregate_job()

    @pytest.mark.asyncio
    async def test_cleanup_job_exception_handled(self, service):
        """清理任务异常不应传播。"""
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            side_effect=Exception("DB error"),
        ):
            # 不应抛出异常
            await service._cleanup_job()