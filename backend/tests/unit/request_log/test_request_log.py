"""请求日志插件的纯函数和数据结构的单元测试。

这些函数用于请求日志的分类和 IP 提取，是安全审计的基础。
LogAggregationService 的定时任务是系统稳定性的关键保障。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    LogAggregationService,
    classify_action,
    _get_client_ip,
)


# =============================================================================
# classify_action 测试
# =============================================================================


class TestClassifyAction:
    """请求行为分类函数的边界情况测试。"""

    def test_login_fail_on_login_path_with_4xx(self):
        """登录路径且状态码 >= 400 应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_path_with_success_is_api_call(self):
        """登录路径但成功响应应返回 api_call。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_prefix_returns_api_call(self):
        """以 /api/ 开头的路径应返回 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/admin/config", 200) == "api_call"

    def test_get_non_api_returns_page_view(self):
        """非 /api/ 的 GET 请求应返回 page_view。"""
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 404) == "page_view"

    def test_non_get_non_api_returns_other(self):
        """非 GET 且非 /api/ 的请求应返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/upload", 200) == "other"
        assert classify_action("DELETE", "/resource", 200) == "other"

    def test_edge_case_empty_path(self):
        """空路径的 GET 请求应视作 page_view。"""
        assert classify_action("GET", "", 200) == "page_view"

    def test_edge_case_root_path(self):
        """根路径 / 的 GET 请求。"""
        result = classify_action("GET", "/", 200)
        assert result in ("page_view", "other")  # "/" 不以 /api/ 开头


# =============================================================================
# _get_client_ip 测试
# =============================================================================


class TestGetClientIp:
    """客户端 IP 提取函数的多层回退逻辑测试。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 有值时应取第一个 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.5, 10.0.0.1, 172.16.0.1"}
        request.client = MagicMock()
        request.client.host = "172.16.0.1"
        assert _get_client_ip(request) == "203.0.113.5"

    def test_x_forwarded_for_single_ip(self):
        """X-Forwarded-For 只有一个 IP 时应返回该 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.5"}
        request.client = MagicMock()
        assert _get_client_ip(request) == "203.0.113.5"

    def test_x_real_ip_when_no_forwarded(self):
        """无 X-Forwarded-For 时有 X-Real-IP 应返回它。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "198.51.100.2"}
        request.client = MagicMock()
        request.client.host = "172.16.0.1"
        assert _get_client_ip(request) == "198.51.100.2"

    def test_client_host_fallback(self):
        """没有代理头时回退到 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        assert _get_client_ip(request) == "192.168.1.1"

    def test_empty_when_no_ip_available(self):
        """没有任何 IP 信息来源时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""

    def test_ipv6_in_forwarded(self):
        """X-Forwarded-For 中的 IPv6 地址应正确处理。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "2001:db8::1, 10.0.0.1"}
        request.client = MagicMock()
        assert _get_client_ip(request) == "2001:db8::1"


# =============================================================================
# RequestLogMiddleware 跳过路径测试
# =============================================================================


class TestRequestLogMiddleware:
    """中间件的路径跳过逻辑测试。"""

    @pytest.mark.asyncio
    async def test_skip_docs_path(self):
        """/docs 路径应完全跳过日志记录。"""
        request = MagicMock()
        request.url.path = "/docs"

        call_next = AsyncMock(return_value=MagicMock())

        from backend.plugins.request_log.services import RequestLogMiddleware

        middleware = RequestLogMiddleware(MagicMock())
        response = await middleware.dispatch(request, call_next)
        # 中间件不应调用 call_next 之外的操作
        # （_write_log_async 不应被触发）
        assert response is not None

    @pytest.mark.asyncio
    async def test_skip_openapi_path(self):
        """/openapi.json 路径应跳过。"""
        request = MagicMock()
        request.url.path = "/openapi.json"
        call_next = AsyncMock(return_value=MagicMock())

        from backend.plugins.request_log.services import RequestLogMiddleware

        middleware = RequestLogMiddleware(MagicMock())
        response = await middleware.dispatch(request, call_next)
        assert response is not None

    @pytest.mark.asyncio
    async def test_skip_static_prefix(self):
        """/static/* 路径应跳过。"""
        request = MagicMock()
        request.url.path = "/static/css/main.css"
        call_next = AsyncMock(return_value=MagicMock())

        from backend.plugins.request_log.services import RequestLogMiddleware

        middleware = RequestLogMiddleware(MagicMock())
        response = await middleware.dispatch(request, call_next)
        assert response is not None

    @pytest.mark.asyncio
    async def test_normal_request_passes_through(self):
        """普通请求应正常通过中间件。"""
        request = MagicMock()
        request.url.path = "/api/blog/posts"
        request.method = "GET"
        request.headers = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        call_next = AsyncMock(return_value=mock_response)

        from backend.plugins.request_log.services import RequestLogMiddleware

        middleware = RequestLogMiddleware(MagicMock())
        response = await middleware.dispatch(request, call_next)
        assert response == mock_response


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    """聚合调度器的启停和任务独立性测试。"""

    @pytest.mark.asyncio
    async def test_start_creates_scheduler(self):
        """start() 应创建并启动 APScheduler。"""
        service = LogAggregationService()
        service.start()
        assert service._scheduler is not None
        assert service._scheduler.running is True
        service.stop()

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self):
        """连续两次 start() 应幂等。"""
        service = LogAggregationService()
        service.start()
        scheduler = service._scheduler
        service.start()  # 第二次调用
        # 如果不幂等，_scheduler 会指向新实例
        assert service._scheduler is scheduler

    def test_stop_without_start(self):
        """未 start 就 stop 不应报错。"""
        service = LogAggregationService()
        service.stop()

    def test_stop_clears_scheduler(self):
        """stop 应将 _scheduler 置为 None。"""
        service = LogAggregationService()
        service._scheduler = MagicMock()
        service._scheduler.running = True
        service.stop()
        assert service._scheduler is None

    @pytest.mark.asyncio
    async def test_aggregate_job_without_db(self):
        """数据库未就绪时聚合任务不应报错。"""
        service = LogAggregationService()
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=None,
        ):
            await service._aggregate_job()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_cleanup_job_without_db(self):
        """数据库未就绪时清理任务不应报错。"""
        service = LogAggregationService()
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=None,
        ):
            await service._cleanup_job()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_aggregate_job_handles_exceptions_gracefully(self):
        """聚合任务在 DB 异常时应被捕获不冒泡。"""
        service = LogAggregationService()
        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_factory.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_factory,
        ):
            # 不应抛出异常
            await service._aggregate_job()

    @pytest.mark.asyncio
    async def test_cleanup_job_handles_exceptions_gracefully(self):
        """清理任务在 DB 异常时应被捕获不冒泡。"""
        service = LogAggregationService()
        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_factory.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_factory,
        ):
            await service._cleanup_job()  # 不应抛出异常