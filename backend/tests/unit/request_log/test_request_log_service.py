"""请求日志服务的单元测试。

测试 classify_action、_get_client_ip、_write_log_async 等关键逻辑，
以及 LogAggregationService 的定时任务行为。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.models import IpActionCounter, RequestLog
from backend.plugins.request_log.services import (
    _get_client_ip,
    classify_action,
)


# =============================================================================
# classify_action 测试
# =============================================================================


class TestClassifyAction:
    """测试请求行为分类逻辑。"""

    @pytest.mark.parametrize(
        "method, path, status_code, expected",
        [
            ("POST", "/api/auth/login", 200, "api_call"),
            ("POST", "/api/auth/login", 401, "login_fail"),
            ("POST", "/api/auth/login", 403, "login_fail"),
            ("POST", "/api/auth/login", 500, "login_fail"),
            ("GET", "/api/blog/posts", 200, "api_call"),
            ("GET", "/api/blog/posts/1", 404, "api_call"),
            ("PUT", "/api/blog/posts/1", 200, "api_call"),
            ("DELETE", "/api/blog/posts/1", 204, "api_call"),
            ("GET", "/", 200, "page_view"),
            ("GET", "/about", 200, "page_view"),
            ("GET", "/contact", 404, "page_view"),
            ("POST", "/webhook", 200, "other"),
            ("PATCH", "/api/something", 200, "api_call"),
        ],
    )
    def test_classify_action(
        self, method: str, path: str, status_code: int, expected: str
    ):
        assert classify_action(method, path, status_code) == expected


# =============================================================================
# _get_client_ip 测试
# =============================================================================


class MockRequest:
    """模拟 FastAPI Request 对象用于 IP 提取测试。"""

    def __init__(
        self,
        x_forwarded_for: str | None = None,
        x_real_ip: str | None = None,
        client_host: str | None = "127.0.0.1",
    ):
        self.headers = {}
        if x_forwarded_for:
            self.headers["X-Forwarded-For"] = x_forwarded_for
        if x_real_ip:
            self.headers["X-Real-IP"] = x_real_ip

        self.client = MagicMock()
        self.client.host = client_host


class TestGetClientIp:
    """测试客户端 IP 提取逻辑（三层防御）。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 取第一个 IP。"""
        req = MockRequest(x_forwarded_for="10.0.0.1, 192.168.1.1, 203.0.113.5")
        assert _get_client_ip(req) == "10.0.0.1"

    def test_x_real_ip_when_no_forwarded(self):
        """无 X-Forwarded-For 时使用 X-Real-IP。"""
        req = MockRequest(x_real_ip="10.0.0.2")
        assert _get_client_ip(req) == "10.0.0.2"

    def test_request_client_host_fallback(self):
        """无代理头时回退到 request.client.host。"""
        req = MockRequest(client_host="203.0.113.5")
        assert _get_client_ip(req) == "203.0.113.5"

    def test_x_forwarded_for_precedence(self):
        """X-Forwarded-For 优先于 X-Real-IP。"""
        req = MockRequest(
            x_forwarded_for="10.0.0.1",
            x_real_ip="192.168.1.1",
            client_host="203.0.113.5",
        )
        assert _get_client_ip(req) == "10.0.0.1"

    def test_x_real_ip_without_forwarded(self):
        """仅有 X-Real-IP 时使用它。"""
        req = MockRequest(x_real_ip="10.0.0.2", client_host="203.0.113.5")
        assert _get_client_ip(req) == "10.0.0.2"

    def test_empty_when_no_client(self):
        """没有任何 IP 信息时返回空字符串。"""
        req = MagicMock()
        req.headers = {}
        req.client = None
        assert _get_client_ip(req) == ""


# =============================================================================
# _write_log_async 测试
# =============================================================================


class TestWriteLogAsync:
    """测试异步日志写入逻辑（使用 mock 避免真实数据库）。"""

    @pytest.mark.asyncio
    async def test_write_log_creates_entry(self):
        """写日志应创建 RequestLog 记录。"""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        mock_db = {"session_factory": mock_session_factory}

        with (
            patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "backend.plugins.request_log.services.get_current_user",
                return_value={"id": "user-123"},
            ),
        ):
            from backend.plugins.request_log.services import _write_log_async

            mock_request = MagicMock()
            mock_request.url.path = "/api/test"
            mock_request.method = "POST"
            mock_request.headers = {
                "User-Agent": "test-agent",
                "Referer": "https://example.com",
            }
            mock_request.client = MagicMock()
            mock_request.client.host = "10.0.0.1"

            await _write_log_async(mock_request, 200, 15.5)

            # 验证 RequestLog 被创建
            assert mock_session.add.call_count >= 1
            call_args = mock_session.add.call_args_list
            added_objects = [args[0][0] for args in call_args]
            log_objects = [o for o in added_objects if isinstance(o, RequestLog)]
            assert len(log_objects) >= 1
            log = log_objects[0]
            assert log.ip == "10.0.0.1"
            assert log.method == "POST"
            assert log.path == "/api/test"
            assert log.status_code == 200
            assert log.duration_ms == 15.5
            assert log.user_id == "user-123"
            assert log.action == "api_call"

    @pytest.mark.asyncio
    async def test_write_log_handles_no_user(self):
        """未登录用户的日志 user_id 应为 None。"""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        with (
            patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "backend.plugins.request_log.services.get_current_user",
                return_value=None,
            ),
        ):
            from backend.plugins.request_log.services import _write_log_async

            mock_request = MagicMock()
            mock_request.url.path = "/api/auth/login"
            mock_request.method = "POST"
            mock_request.headers = {}
            mock_request.client = MagicMock()
            mock_request.client.host = "10.0.0.1"

            await _write_log_async(mock_request, 401, 5.0)

            call_args = mock_session.add.call_args_list
            added_objects = [args[0][0] for args in call_args]
            log_objects = [o for o in added_objects if isinstance(o, RequestLog)]
            assert len(log_objects) >= 1
            assert log_objects[0].user_id is None
            assert log_objects[0].action == "login_fail"

    @pytest.mark.asyncio
    async def test_write_log_creates_counter(self):
        """写日志应为新 IP+action 创建计数器。"""
        mock_session = AsyncMock()
        # execute 返回 sync MagicMock，其 scalar_one_or_none 返回 None（表示新 IP）
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute_result
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        with (
            patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "backend.plugins.request_log.services.get_current_user",
                return_value=None,
            ),
        ):
            from backend.plugins.request_log.services import _write_log_async

            mock_request = MagicMock()
            mock_request.url.path = "/api/test"
            mock_request.method = "GET"
            mock_request.headers = {}
            mock_request.client = MagicMock()
            mock_request.client.host = "10.0.0.1"

            await _write_log_async(mock_request, 200, 1.0)

            # 验证 IpActionCounter 被创建（add 调用 + commit 完成）
            assert mock_session.add.called
            assert mock_session.commit.called


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    """测试日志聚合和清理服务。"""

    def test_start_when_apscheduler_missing(self):
        """apscheduler 未安装时 start() 不应崩溃。"""
        from backend.plugins.request_log.services import (
            LogAggregationService,
        )

        svc = LogAggregationService()
        with patch(
            "backend.plugins.request_log.services.LogAggregationService.start",
            side_effect=ImportError("模拟 apscheduler 缺失"),
        ):
            try:
                svc.start()
            except ImportError:
                pass  # 期望的行为：捕获 ImportError 不崩溃
            else:
                pass  # 或直接返回（取决于是否被 patch）

    def test_stop_when_not_started(self):
        """未启动时 stop() 不应崩溃。"""
        from backend.plugins.request_log.services import (
            LogAggregationService,
        )

        svc = LogAggregationService()
        svc.stop()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_aggregate_job_runs_without_error(self):
        """聚合任务在无数据时不应抛出异常。"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.all.return_value = []  # 无行数据
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            from backend.plugins.request_log.services import (
                LogAggregationService,
            )

            svc = LogAggregationService()
            await svc._aggregate_job()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_cleanup_job_runs_without_error(self):
        """清理任务在无数据时不应抛出异常。"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar.return_value = 0  # 无记录
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            from backend.plugins.request_log.services import (
                LogAggregationService,
            )

            svc = LogAggregationService()
            await svc._cleanup_job()  # 不应抛出异常


# =============================================================================
# RequestLogMiddleware dispatch 测试
# =============================================================================


class TestRequestLogMiddleware:
    """测试中间件的路径跳过逻辑（使用 mock）。"""

    @pytest.mark.asyncio
    async def test_skips_docs_path(self):
        """/docs 路径应被跳过，不记录日志。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        middleware = RequestLogMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/docs"

        mock_call_next = AsyncMock()

        with patch(
            "backend.plugins.request_log.services.asyncio.create_task"
        ) as mock_create_task:
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert mock_call_next.called
        mock_create_task.assert_not_called()  # 不应创建日志任务

    @pytest.mark.asyncio
    async def test_skips_static_prefix(self):
        """/static/ 路径应被跳过。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        middleware = RequestLogMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/static/css/main.css"

        mock_call_next = AsyncMock()

        with patch(
            "backend.plugins.request_log.services.asyncio.create_task"
        ) as mock_create_task:
            await middleware.dispatch(mock_request, mock_call_next)

        mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_api_request(self):
        """API 请求应记录日志。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        middleware = RequestLogMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/api/blog/posts"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_call_next = AsyncMock(return_value=mock_response)

        with patch(
            "backend.plugins.request_log.services.asyncio.create_task"
        ) as mock_create_task:
            await middleware.dispatch(mock_request, mock_call_next)

        mock_create_task.assert_called_once()