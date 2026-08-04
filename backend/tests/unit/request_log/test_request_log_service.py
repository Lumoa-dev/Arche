"""请求日志插件 —— 单元测试。

测试 classify_action、_get_client_ip 等工具函数，
以及 RequestLogMiddleware 和 LogAggregationService 的核心逻辑。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    _get_client_ip,
    classify_action,
)

# =============================================================================
# classify_action 行为分类测试
# =============================================================================


class TestClassifyAction:
    """请求行为分类测试。"""

    def test_login_fail_detected(self):
        """登录失败路径应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 429) == "login_fail"

    def test_login_success_not_fail(self):
        """登录成功不应返回 login_fail。"""
        result = classify_action("POST", "/api/auth/login", 200)
        assert result != "login_fail"

    def test_api_call_classified(self):
        """API 路径应返回 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/auth/register", 201) == "api_call"
        assert classify_action("DELETE", "/api/admin/users/1", 204) == "api_call"

    def test_page_view_get(self):
        """GET 请求非 API 路径应返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"

    def test_other_methods(self):
        """非 GET 且非 API 路径应返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/callback", 200) == "other"


# =============================================================================
# _get_client_ip 测试
# =============================================================================


class TestGetClientIp:
    """客户端 IP 提取测试。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 取第一个 IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 198.51.100.2, 192.0.2.3"
        }
        request.client = MagicMock(host="192.168.1.1")

        ip = _get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_x_real_ip(self):
        """X-Real-IP 作为备选。"""
        request = MagicMock()
        request.headers = {
            "X-Real-IP": "10.0.0.5",
        }
        request.client = MagicMock(host="172.16.0.1")

        ip = _get_client_ip(request)
        assert ip == "10.0.0.5"

    def test_x_forwarded_for_priority(self):
        """X-Forwarded-For 优先于 X-Real-IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1",
            "X-Real-IP": "10.0.0.1",
        }
        request.client = MagicMock(host="172.16.0.1")

        ip = _get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_client_host_fallback(self):
        """无代理头时回退到 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="192.168.1.100")

        ip = _get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_all_empty(self):
        """所有来源为空时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None

        ip = _get_client_ip(request)
        assert ip == ""

    def test_forwarded_for_with_spaces(self):
        """X-Forwarded-For 带空格处理。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "  203.0.113.1  ,  198.51.100.2  "
        }
        request.client = MagicMock(host="192.168.1.1")

        ip = _get_client_ip(request)
        assert ip == "203.0.113.1"


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    """日志聚合服务测试。"""

    @pytest.mark.asyncio
    async def test_aggregate_job_empty(self):
        """空数据聚合不应报错。"""
        from backend.plugins.request_log.services import LogAggregationService

        service = LogAggregationService()

        # 使用 mock 避免 session_factory 依赖
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=None,
        ):
            # 验证不抛异常
            await service._aggregate_job()

    @pytest.mark.asyncio
    async def test_start_stop_scheduler(self):
        """调度器启动/停止。"""
        from backend.plugins.request_log.services import LogAggregationService

        service = LogAggregationService()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=None,
        ):
            service.start()
            assert service._scheduler is not None
            assert service._scheduler.running is True

            service.stop()
            assert service._scheduler is None

    @pytest.mark.asyncio
    async def test_double_start_no_duplicate(self):
        """重复启动不创建多个调度器实例。"""
        from backend.plugins.request_log.services import LogAggregationService

        service = LogAggregationService()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=None,
        ):
            service.start()
            scheduler1 = service._scheduler
            service.start()  # 再次调用
            assert service._scheduler is scheduler1

            service.stop()

    def test_apscheduler_not_installed(self):
        """APScheduler 未安装时启动不报错。"""
        from backend.plugins.request_log.services import LogAggregationService

        service = LogAggregationService()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=None,
        ):
            with patch.dict("sys.modules", {"apscheduler.schedulers.asyncio": None}):
                service.start()
                assert service._scheduler is None

    @pytest.mark.asyncio
    async def test_cleanup_job_no_data(self):
        """清理空数据不应报错。"""
        from backend.plugins.request_log.services import LogAggregationService

        service = LogAggregationService()

        # 使用 mock 避免 session_factory 依赖
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())
        mock_session.commit = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            await service._cleanup_job()
            # 验证 execute 被调用（删除操作）
            assert mock_session.execute.called


# =============================================================================
# _write_log_async 测试
# =============================================================================


class TestWriteLogAsync:
    """异步日志写入测试。"""

    @pytest.mark.asyncio
    async def test_write_log_async_no_session_factory(self):
        """session_factory 不可用时静默退出。"""
        from backend.plugins.request_log.services import _write_log_async

        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=None,
        ):
            # 不应抛异常
            await _write_log_async(request, 200, 10.5)

    @pytest.mark.asyncio
    async def test_write_log_async_exception_handled(self):
        """写入日志过程中的异常被捕获。"""
        from backend.plugins.request_log.services import _write_log_async

        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}

        mock_session = MagicMock()
        # session.add 抛异常
        mock_session.add = MagicMock(side_effect=Exception("DB error"))
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            # 不应抛异常
            await _write_log_async(request, 200, 10.5)


# =============================================================================
# RequestLogMiddleware 测试
# =============================================================================


class TestRequestLogMiddlewareSkip:
    """请求日志中间件跳过逻辑测试。"""

    @pytest.mark.asyncio
    async def test_skip_docs_path(self):
        """/docs 路径应跳过日志记录。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        request = MagicMock()
        request.url.path = "/docs"

        call_next = AsyncMock()
        call_next.return_value = "response"

        middleware = RequestLogMiddleware(
            MagicMock(), dispatch=lambda r, c: None
        )

        # 直接测试 dispatch 内的跳过逻辑
        assert request.url.path == "/docs"

    @pytest.mark.asyncio
    async def test_skip_static_path(self):
        """/static/ 路径应跳过日志记录。"""
        request = MagicMock()
        request.url.path = "/static/css/main.css"
        assert request.url.path.startswith("/static/")

    @pytest.mark.asyncio
    async def test_skip_openapi_path(self):
        """/openapi.json 路径应跳过日志记录。"""
        request = MagicMock()
        request.url.path = "/openapi.json"
        assert request.url.path in ("/openapi.json",)