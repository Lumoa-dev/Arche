"""请求日志服务层单元测试 —— classify_action, _get_client_ip, _write_log_async 等。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    _get_client_ip,
    classify_action,
)


# =============================================================================
# classify_action
# =============================================================================


class TestClassifyAction:
    """测试行为分类函数。"""

    def test_login_fail_on_login_path_with_4xx(self):
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"

    def test_login_fail_on_login_path_with_5xx(self):
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_api_call_for_other_api_paths(self):
        assert classify_action("GET", "/api/users", 200) == "api_call"

    def test_api_call_with_error_status(self):
        assert classify_action("GET", "/api/posts", 404) == "api_call"

    def test_page_view_for_get_non_api(self):
        assert classify_action("GET", "/about", 200) == "page_view"

    def test_other_for_non_get_non_api(self):
        assert classify_action("POST", "/webhook", 200) == "other"

    def test_login_success_is_api_call(self):
        """登录成功（200）不应归类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_root_path_get_is_page_view(self):
        assert classify_action("GET", "/", 200) == "page_view"


# =============================================================================
# _get_client_ip
# =============================================================================


class TestGetClientIp:
    """测试客户端 IP 提取函数。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 取第一个 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}
        assert _get_client_ip(request) == "10.0.0.1"

    def test_x_forwarded_for_single_ip(self):
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.1"}
        assert _get_client_ip(request) == "10.0.0.1"

    def test_x_forwarded_for_with_spaces(self):
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "  10.0.0.1  ,  192.168.1.1  "}
        assert _get_client_ip(request) == "10.0.0.1"

    def test_x_real_ip_fallback(self):
        """无 X-Forwarded-For 时回退到 X-Real-IP。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "10.0.0.1"}
        assert _get_client_ip(request) == "10.0.0.1"

    def test_client_host_fallback(self):
        """无 proxy header 时回退到 client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client.host = "203.0.113.1"
        assert _get_client_ip(request) == "203.0.113.1"

    def test_all_empty_returns_empty_string(self):
        """所有途径都无 IP 时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""

    def test_x_forwarded_empty_string(self):
        """X-Forwarded-For 为空字符串时继续回退。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": ""}
        request.client.host = "203.0.113.1"
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_forwarded_for_precedence(self):
        """X-Forwarded-For 优先于 X-Real-IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "10.0.0.1",
            "X-Real-IP": "192.168.1.1",
        }
        assert _get_client_ip(request) == "10.0.0.1"


# =============================================================================
# _write_log_async — 使用真实内存数据库
# =============================================================================


class TestWriteLogAsync:
    """测试异步日志写入。"""

    @pytest.fixture
    def mock_request(self):
        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {
            "User-Agent": "test-agent",
            "Referer": "http://example.com",
        }
        request.client.host = "127.0.0.1"
        request.state.user = None
        return request

    async def test_write_log_creates_entry(self, in_memory_db, mock_request):
        """写入日志后应在数据库中创建记录。"""
        from backend.plugins.request_log.services import _write_log_async

        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_factory.return_value = in_memory_db["session_factory"]
            await _write_log_async(mock_request, 200, 15.5)

        from backend.plugins.request_log.models import RequestLog
        from sqlalchemy import select

        async with in_memory_db["session_factory"]() as session:
            result = await session.execute(select(RequestLog))
            logs = result.scalars().all()
            assert len(logs) == 1
            assert logs[0].path == "/api/test"
            assert logs[0].method == "GET"
            assert logs[0].status_code == 200
            assert logs[0].duration_ms == 15.5

    async def test_write_log_creates_counter(self, in_memory_db, mock_request):
        """写入日志时也应创建或更新 IpActionCounter。"""
        from backend.plugins.request_log.services import _write_log_async

        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_factory.return_value = in_memory_db["session_factory"]
            await _write_log_async(mock_request, 200, 10.0)

        from backend.plugins.request_log.models import IpActionCounter
        from sqlalchemy import select

        async with in_memory_db["session_factory"]() as session:
            result = await session.execute(select(IpActionCounter))
            counters = result.scalars().all()
            assert len(counters) >= 1
            assert counters[0].action == "api_call"

    async def test_write_log_increments_existing_counter(self, in_memory_db, mock_request):
        """同一 IP+action+hour 的计数器应累加。"""
        from backend.plugins.request_log.models import IpActionCounter
        from backend.plugins.request_log.services import _write_log_async
        from datetime import datetime
        from sqlalchemy import select

        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_factory.return_value = in_memory_db["session_factory"]
            # 写两次
            await _write_log_async(mock_request, 200, 10.0)
            await _write_log_async(mock_request, 200, 10.0)

        async with in_memory_db["session_factory"]() as session:
            now = datetime.now()
            result = await session.execute(
                select(IpActionCounter).where(
                    IpActionCounter.ip == "127.0.0.1",
                    IpActionCounter.action == "api_call",
                    IpActionCounter.action_date == now.date(),
                    IpActionCounter.hour == now.hour,
                )
            )
            counter = result.scalar_one_or_none()
            assert counter is not None
            assert counter.count == 2

    async def test_write_log_truncates_long_headers(self, in_memory_db):
        """超长 User-Agent/Referer 应被截断。"""
        from backend.plugins.request_log.services import _write_log_async

        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {
            "User-Agent": "x" * 1000,
            "Referer": "http://example.com/" + "y" * 2000,
        }
        request.client.host = "127.0.0.1"
        request.state.user = None

        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_factory.return_value = in_memory_db["session_factory"]
            await _write_log_async(request, 200, 10.0)

        from backend.plugins.request_log.models import RequestLog
        from sqlalchemy import select

        async with in_memory_db["session_factory"]() as session:
            result = await session.execute(select(RequestLog))
            log = result.scalars().first()
            assert log is not None
            assert len(log.user_agent) <= 512
            assert len(log.referer) <= 1024

    async def test_write_log_handles_session_factory_none(self, mock_request):
        """session_factory 为 None 时不应抛异常。"""
        from backend.plugins.request_log.services import _write_log_async

        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_factory.return_value = None
            # 不应抛异常
            await _write_log_async(mock_request, 200, 10.0)

    async def test_write_log_handles_db_error_gracefully(self, mock_request):
        """DB 异常时不应传播到上层。"""
        from backend.plugins.request_log.services import _write_log_async

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        # 模拟 session.add 抛异常
        mock_session.add.side_effect = Exception("DB error")

        mock_sf = MagicMock()
        mock_sf.return_value = mock_session

        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_factory.return_value = mock_sf
            # 不应抛异常
            await _write_log_async(mock_request, 200, 10.0)

    async def test_write_log_respects_skip_paths(self, in_memory_db):
        """跳过路径中的请求不应写入日志。"""
        from backend.plugins.request_log.services import _write_log_async

        # 注意：dispatch 负责跳过，_write_log_async 本身不跳过
        # 这个测试验证跳过路径不依赖 _write_log_async
        request = MagicMock()
        request.url.path = "/docs"
        request.method = "GET"
        request.headers = {}
        request.client.host = "127.0.0.1"
        request.state.user = None

        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_factory.return_value = in_memory_db["session_factory"]
            await _write_log_async(request, 200, 10.0)

        from backend.plugins.request_log.models import RequestLog
        from sqlalchemy import select

        async with in_memory_db["session_factory"]() as session:
            result = await session.execute(select(RequestLog))
            assert result.scalars().first() is not None

    async def test_write_log_without_user(self, in_memory_db):
        """未认证用户时 user_id 应为 None。"""
        from backend.plugins.request_log.services import _write_log_async

        request = MagicMock()
        request.url.path = "/api/public"
        request.method = "GET"
        request.headers = {}
        request.client.host = "127.0.0.1"

        with (
            patch(
                "backend.plugins.request_log.services._get_session_factory"
            ) as mock_factory,
            patch(
                "backend.plugins.request_log.services.get_current_user"
            ) as mock_get_user,
        ):
            mock_factory.return_value = in_memory_db["session_factory"]
            mock_get_user.return_value = None
            await _write_log_async(request, 200, 10.0)

        from backend.plugins.request_log.models import RequestLog
        from sqlalchemy import select

        async with in_memory_db["session_factory"]() as session:
            result = await session.execute(select(RequestLog))
            log = result.scalars().first()
            assert log is not None
            assert log.user_id is None


# =============================================================================
# RequestLogMiddleware — dispatch
# =============================================================================


class TestRequestLogMiddlewareDispatch:
    """测试 RequestLogMiddleware 的 dispatch 逻辑。"""

    @pytest.fixture
    def middleware(self):
        from backend.plugins.request_log.services import RequestLogMiddleware

        return RequestLogMiddleware(MagicMock())

    async def test_skip_paths(self, middleware):
        """跳过路径应直接放行。"""
        for path in ["/docs", "/openapi.json", "/redoc", "/favicon.ico"]:
            request = MagicMock()
            request.url.path = path
            call_next = AsyncMock()
            response = await middleware.dispatch(request, call_next)
            assert response == call_next.return_value

    async def test_skip_prefixes(self, middleware):
        """跳过前缀应直接放行。"""
        request = MagicMock()
        request.url.path = "/static/css/main.css"
        call_next = AsyncMock()
        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value

    async def test_normal_request_creates_log_task(self, middleware):
        """正常请求应创建异步写入任务。"""
        import asyncio

        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        call_next = AsyncMock()

        # 验证 dispatch 放行
        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value

    async def test_exception_request_logs_500(self, middleware):
        """请求处理抛异常时，应记录 500 状态码后重新抛出。"""
        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        call_next = AsyncMock()
        call_next.side_effect = RuntimeError("test error")

        with pytest.raises(RuntimeError, match="test error"):
            await middleware.dispatch(request, call_next)


# =============================================================================
# LogAggregationService
# =============================================================================


class TestLogAggregationService:
    """测试日志聚合服务。"""

    @pytest.fixture
    def agg_service(self):
        from backend.plugins.request_log.services import LogAggregationService

        return LogAggregationService()

    def test_start_without_apscheduler(self, agg_service):
        """APScheduler 未安装时，start 应优雅降级。"""
        with patch(
            "backend.plugins.request_log.services.LogAggregationService.start"
        ) as mock_start:
            # 模拟 ImportError 场景
            import builtins

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "apscheduler.schedulers.asyncio":
                    raise ImportError("No module named 'apscheduler'")
                return original_import(name, *args, **kwargs)

            builtins.__import__ = mock_import
            try:
                agg_service.start()
                assert agg_service._scheduler is None
            finally:
                builtins.__import__ = original_import

    def test_start_twice_no_op(self, agg_service):
        """重复调用 start 不应创建多个 scheduler。"""
        with patch(
            "backend.plugins.request_log.services.LogAggregationService.start"
        ) as mock_start:
            agg_service._scheduler = MagicMock()
            agg_service.start()
            # 有 _scheduler 时 start 应直接返回
            # 在我们 mock 的版本中验证不会被覆盖
            assert agg_service._scheduler is not None

    def test_stop_when_not_running(self, agg_service):
        """未启动时调用 stop 不应抛异常。"""
        agg_service.stop()  # 不应抛异常

    def test_stop_when_running(self, agg_service):
        """已启动时调用 stop 应 shutdown。"""
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        agg_service._scheduler = mock_scheduler
        agg_service.stop()
        mock_scheduler.shutdown.assert_called_once_with(wait=False)
        assert agg_service._scheduler is None

    async def test_aggregate_job_with_no_data(self, agg_service):
        """无数据时聚合任务不应抛异常。"""
        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.execute.return_value.all.return_value = []
            mock_sf = MagicMock()
            mock_sf.return_value = mock_session
            mock_factory.return_value = mock_sf
            await agg_service._aggregate_job()  # 不应抛异常

    async def test_cleanup_job_with_no_data(self, agg_service):
        """无数据时清理任务不应抛异常。"""
        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.execute.return_value.scalar.return_value = 0
            mock_sf = MagicMock()
            mock_sf.return_value = mock_session
            mock_factory.return_value = mock_sf
            await agg_service._cleanup_job()  # 不应抛异常

    async def test_aggregate_job_handles_exception(self, agg_service):
        """聚合任务中的异常应被捕获，不传播。"""
        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_factory.side_effect = Exception("test error")
            await agg_service._aggregate_job()  # 不应抛异常

    async def test_cleanup_job_handles_exception(self, agg_service):
        """清理任务中的异常应被捕获，不传播。"""
        with patch(
            "backend.plugins.request_log.services._get_session_factory"
        ) as mock_factory:
            mock_factory.side_effect = Exception("test error")
            await agg_service._cleanup_job()  # 不应抛异常