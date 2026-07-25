"""请求日志插件 单元测试。

覆盖范围：
- classify_action() 行为分类函数
- _get_client_ip() 客户端 IP 提取
- RequestLogMiddleware 中间件跳过逻辑
- LogAggregationService 聚合和清理服务

所有测试使用纯 mock，不启动真实数据库。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
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
    """行为分类函数测试。"""

    def test_login_fail(self):
        """登录失败返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"

    def test_login_success_not_login_fail(self):
        """登录成功（非 4xx）不返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_call(self):
        """API 路径返回 api_call。"""
        assert classify_action("GET", "/api/ip-ban/bans", 200) == "api_call"
        assert classify_action("POST", "/api/blog/posts", 201) == "api_call"
        assert classify_action("DELETE", "/api/users/1", 204) == "api_call"

    def test_page_view(self):
        """GET 非 API 路径返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"

    def test_other_method(self):
        """非 GET 非 API 路径返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"

    def test_api_path_different_method(self):
        """API 路径即使非 GET 也返回 api_call。"""
        assert classify_action("PUT", "/api/ip-ban/rules/1", 200) == "api_call"


# =============================================================================
# _get_client_ip 测试
# =============================================================================


class TestGetClientIP:
    """客户端 IP 提取函数测试。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 取第一个 IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1, 192.168.1.1"
        }
        request.client = None
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip(self):
        """X-Real-IP 优先于 request.client。"""
        request = MagicMock()
        request.headers = {
            "X-Real-IP": "198.51.100.1",
        }
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        assert _get_client_ip(request) == "198.51.100.1"

    def test_client_host_fallback(self):
        """无代理头时回退到 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        assert _get_client_ip(request) == "192.168.1.1"

    def test_empty_when_no_client(self):
        """无任何 IP 信息时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""

    def test_forwarded_for_with_spaces(self):
        """X-Forwarded-For 带空格也能正确提取。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": " 203.0.113.1 , 10.0.0.1 "
        }
        request.client = None
        assert _get_client_ip(request) == "203.0.113.1"

    def test_ipv6_in_forwarded_for(self):
        """IPv6 地址在 X-Forwarded-For 中。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "2001:db8::1, 10.0.0.1"
        }
        request.client = None
        assert _get_client_ip(request) == "2001:db8::1"


# =============================================================================
# RequestLogMiddleware 跳过逻辑测试
# =============================================================================


class TestRequestLogMiddlewareSkip:
    """请求日志中间件跳过逻辑测试。"""

    def test_skip_paths(self):
        """跳过路径列表中的路径不应记录。"""
        from backend.plugins.request_log.services import _SKIP_PATHS, _SKIP_PREFIXES

        assert "/docs" in _SKIP_PATHS
        assert "/openapi.json" in _SKIP_PATHS
        assert "/redoc" in _SKIP_PATHS
        assert "/favicon.ico" in _SKIP_PATHS

    def test_skip_prefixes(self):
        """跳过前缀匹配的路径不应记录。"""
        from backend.plugins.request_log.services import _SKIP_PREFIXES

        assert "/static/" in _SKIP_PREFIXES
        assert "/assets/" in _SKIP_PREFIXES

    @pytest.mark.asyncio
    async def test_middleware_skips_docs_path(self):
        """中间件应跳过 /docs 路径。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        request = MagicMock()
        request.url.path = "/docs"
        request.method = "GET"

        mock_call_next = AsyncMock(return_value=MagicMock())

        middleware = RequestLogMiddleware.__new__(RequestLogMiddleware)
        response = await middleware.dispatch(request, mock_call_next)
        mock_call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_skips_static_prefix(self):
        """中间件应跳过 /static/ 前缀。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        request = MagicMock()
        request.url.path = "/static/css/main.css"
        request.method = "GET"

        mock_call_next = AsyncMock(return_value=MagicMock())

        middleware = RequestLogMiddleware.__new__(RequestLogMiddleware)
        response = await middleware.dispatch(request, mock_call_next)
        mock_call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_processes_api_path(self):
        """中间件应处理 API 路径。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        request = MagicMock()
        request.url.path = "/api/blog/posts"
        request.method = "GET"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        response = MagicMock()
        response.status_code = 200
        mock_call_next = AsyncMock(return_value=response)

        middleware = RequestLogMiddleware.__new__(RequestLogMiddleware)
        with patch(
            "backend.plugins.request_log.services._write_log_async",
            AsyncMock(),
        ) as mock_write:
            result = await middleware.dispatch(request, mock_call_next)
            mock_write.assert_called_once()
            assert result == response

    @pytest.mark.asyncio
    async def test_middleware_logs_exception_as_500(self):
        """中间件应将异常记录为 500 状态码。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        request = MagicMock()
        request.url.path = "/api/blog/posts"
        request.method = "GET"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        mock_call_next = AsyncMock(side_effect=ValueError("test error"))

        middleware = RequestLogMiddleware.__new__(RequestLogMiddleware)
        with patch(
            "backend.plugins.request_log.services._write_log_async",
            AsyncMock(),
        ) as mock_write:
            with pytest.raises(ValueError):
                await middleware.dispatch(request, mock_call_next)
            # 异常时也应记录日志，状态码为 500
            mock_write.assert_called_once()
            # 验证 status_code 为 500
            args, _ = mock_write.call_args
            assert args[1] == 500


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    """日志聚合服务测试。"""

    def test_start_stop_scheduler(self):
        """启动和停止定时任务。"""
        service = LogAggregationService()

        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as MockScheduler:
            mock_scheduler = MagicMock()
            MockScheduler.return_value = mock_scheduler

            service.start()
            assert service._scheduler is not None
            mock_scheduler.add_job.assert_called()
            mock_scheduler.start.assert_called_once()

            service.stop()
            assert service._scheduler is None
            mock_scheduler.shutdown.assert_called_once_with(wait=False)

    def test_idempotent_start(self):
        """重复启动不应创建多个调度器。"""
        service = LogAggregationService()

        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as MockScheduler:
            mock_scheduler = MagicMock()
            MockScheduler.return_value = mock_scheduler

            service.start()
            service.start()  # 再次启动
            mock_scheduler.start.assert_called_once()

    def test_stop_without_start(self):
        """未启动时停止不应报错。"""
        service = LogAggregationService()
        service.stop()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_aggregate_job_success(self):
        """聚合任务成功执行。"""
        from backend.plugins.request_log.services import _get_session_factory

        service = LogAggregationService()

        # mock session_factory
        mock_session = MagicMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            # mock execute 返回空结果
            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)

            await service._aggregate_job()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_aggregate_job_with_data(self):
        """聚合任务处理有数据的情况。"""
        service = LogAggregationService()

        # 创建一个模拟的行对象
        MockRow = MagicMock()
        MockRow.ip = "10.0.0.1"
        MockRow.action = "api_call"
        MockRow.yr = 2026
        MockRow.mo = 7
        MockRow.dy = 26
        MockRow.hr = 10
        MockRow.cnt = 5

        mock_session = MagicMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            # 第一次 execute 返回聚合数据
            aggregate_result = MagicMock()
            aggregate_result.all.return_value = [MockRow]
            # 第二次 execute 检查 counter 是否存在
            counter_result = MagicMock()
            counter_result.scalar_one_or_none.return_value = None

            mock_session.execute = AsyncMock(
                side_effect=[aggregate_result, counter_result]
            )

            await service._aggregate_job()
            # 应添加新的 counter
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_job_success(self):
        """清理任务成功执行。"""
        service = LogAggregationService()

        mock_session = MagicMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            count_result = MagicMock()
            count_result.scalar.return_value = 100
            mock_session.execute = AsyncMock(return_value=count_result)

            await service._cleanup_job()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_job_handles_exception(self):
        """清理任务异常不应抛出。"""
        service = LogAggregationService()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("DB error")
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            # 不应抛出异常
            await service._cleanup_job()


# =============================================================================
# _write_log_async 测试
# =============================================================================


class TestWriteLogAsync:
    """异步写入日志测试。"""

    @pytest.mark.asyncio
    async def test_write_log_creates_entry(self):
        """写入日志应创建 RequestLog 条目。"""
        from backend.plugins.request_log.services import _write_log_async

        request = MagicMock()
        request.url.path = "/api/blog/posts"
        request.method = "GET"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        mock_session = MagicMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            with patch(
                "backend.plugins.request_log.services.get_current_user",
                return_value={"id": "user-123"},
            ):
                # 第一次 execute 查询 counter，返回 None（新建）
                counter_result = MagicMock()
                counter_result.scalar_one_or_none.return_value = None
                mock_session.execute = AsyncMock(return_value=counter_result)

                await _write_log_async(request, 200, 15.5)
                # 应添加 log entry 和 counter
                assert mock_session.add.call_count >= 2
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_log_handles_exception(self):
        """写入日志异常不应抛出。"""
        from backend.plugins.request_log.services import _write_log_async

        request = MagicMock()
        request.url.path = "/api/blog/posts"
        request.method = "GET"

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            side_effect=Exception("DB error"),
        ):
            # 不应抛出异常
            await _write_log_async(request, 200, 15.5)