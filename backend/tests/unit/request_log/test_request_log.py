"""请求日志插件 单元测试。

涵盖：
- 行为分类逻辑（classify_action）
- 客户端 IP 提取
- 异步日志写入
- 日志聚合服务（aggregation + cleanup）
- 中间件调度逻辑
- 边界条件和错误处理
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from backend.plugins.request_log.services import (
    LogAggregationService,
    RequestLogMiddleware,
    _get_client_ip,
    _write_log_async,
    classify_action,
)


# =============================================================================
# 行为分类测试
# =============================================================================


class TestClassifyAction:
    """测试 classify_action 函数。"""

    def test_classify_login_fail(self):
        """登录失败路径应分类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"

    def test_classify_login_success_not_fail(self):
        """登录成功不应分类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) != "login_fail"

    def test_classify_api_call(self):
        """API 路径应分类为 api_call。"""
        # login_fail 优先，所以 status_code 200 时走 api_call
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"
        assert classify_action("GET", "/api/posts", 200) == "api_call"
        assert classify_action("PUT", "/api/users/1", 200) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_classify_page_view(self):
        """GET 非 API 请求应分类为 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_classify_other(self):
        """非 GET 非 API 请求应分类为 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/upload", 200) == "other"
        assert classify_action("DELETE", "/temp", 200) == "other"

    def test_classify_login_fail_precedence(self):
        """login_fail 优先级高于其他分类。"""
        # 即使路径以 /api/ 开头，login 失败仍走 login_fail
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"


# =============================================================================
# 客户端 IP 提取测试
# =============================================================================


class TestGetClientIp:
    """测试 _get_client_ip 函数。"""

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
        """X-Real-IP 被正确提取。"""
        request = MagicMock()
        request.headers = {
            "X-Real-IP": "10.0.0.5",
        }
        request.client = MagicMock(host="192.168.1.1")

        ip = _get_client_ip(request)
        assert ip == "10.0.0.5"

    def test_direct_client_ip(self):
        """无代理头时使用 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="127.0.0.1")

        ip = _get_client_ip(request)
        assert ip == "127.0.0.1"

    def test_no_client_no_headers(self):
        """无客户端和代理头时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None

        ip = _get_client_ip(request)
        assert ip == ""

    def test_forwarded_for_precedence(self):
        """X-Forwarded-For 优先级高于 X-Real-IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1",
            "X-Real-IP": "10.0.0.5",
        }
        request.client = MagicMock(host="192.168.1.1")

        ip = _get_client_ip(request)
        assert ip == "203.0.113.1"


# =============================================================================
# 中间件测试
# =============================================================================


class TestRequestLogMiddleware:
    """测试 RequestLogMiddleware 调度逻辑。"""

    def test_skip_docs_path(self):
        """跳过文档路径。"""
        app = FastAPI()
        middleware = RequestLogMiddleware(app)

        request = MagicMock()
        request.url.path = "/docs"

        async def call_next(request):
            return MagicMock(status_code=200)

        import asyncio

        response = asyncio.run(middleware.dispatch(request, call_next))
        assert response.status_code == 200

    def test_skip_openapi_path(self):
        """跳过 OpenAPI 路径。"""
        app = FastAPI()
        middleware = RequestLogMiddleware(app)

        request = MagicMock()
        request.url.path = "/openapi.json"

        async def call_next(request):
            return MagicMock(status_code=200)

        import asyncio

        response = asyncio.run(middleware.dispatch(request, call_next))
        assert response.status_code == 200

    def test_skip_static_path(self):
        """跳过静态资源路径。"""
        app = FastAPI()
        middleware = RequestLogMiddleware(app)

        request = MagicMock()
        request.url.path = "/static/css/main.css"

        async def call_next(request):
            return MagicMock(status_code=200)

        import asyncio

        response = asyncio.run(middleware.dispatch(request, call_next))
        assert response.status_code == 200

    def test_skip_favicon(self):
        """跳过 favicon 路径。"""
        app = FastAPI()
        middleware = RequestLogMiddleware(app)

        request = MagicMock()
        request.url.path = "/favicon.ico"

        async def call_next(request):
            return MagicMock(status_code=200)

        import asyncio

        response = asyncio.run(middleware.dispatch(request, call_next))
        assert response.status_code == 200

    def test_log_api_request(self):
        """API 请求应被记录。"""
        app = FastAPI()
        middleware = RequestLogMiddleware(app)

        request = MagicMock()
        request.url.path = "/api/posts"
        request.method = "GET"
        request.headers = {}

        mock_response = MagicMock(status_code=200)

        async def call_next(request):
            return mock_response

        with patch(
            "backend.plugins.request_log.services._write_log_async",
            new_callable=AsyncMock,
        ) as mock_write:
            import asyncio

            response = asyncio.run(middleware.dispatch(request, call_next))
            assert response.status_code == 200
            mock_write.assert_called_once()

    def test_log_exception_request(self):
        """请求异常时应记录 500 日志。"""
        app = FastAPI()
        middleware = RequestLogMiddleware(app)

        request = MagicMock()
        request.url.path = "/api/error"
        request.method = "GET"
        request.headers = {}

        async def call_next(request):
            raise ValueError("test error")

        with patch(
            "backend.plugins.request_log.services._write_log_async",
            new_callable=AsyncMock,
        ) as mock_write:
            import asyncio

            with pytest.raises(ValueError):
                asyncio.run(middleware.dispatch(request, call_next))
            mock_write.assert_called_once()


# =============================================================================
# 异步日志写入测试
# =============================================================================


@pytest.mark.asyncio
class TestWriteLogAsync:
    """测试 _write_log_async 函数。"""

    async def test_write_log_basic(self):
        """基本日志写入。"""
        request = MagicMock()
        request.url.path = "/api/posts"
        request.url.hostname = "localhost"
        request.method = "GET"
        request.headers = {
            "User-Agent": "test-agent",
            "Referer": "https://example.com",
        }

        # 模拟 get_current_user
        with patch(
            "backend.plugins.request_log.services.get_current_user",
            return_value={"id": "user-1"},
        ):
            # 模拟 session_factory
            mock_session = MagicMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

            mock_session_factory = MagicMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            # 模拟 _get_session_factory
            with patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=mock_session_factory,
            ):
                result = await _write_log_async(request, 200, 15.5)
                assert result is None  # 不应抛异常
                mock_session.add.assert_called()
                mock_session.commit.assert_called()

    async def test_write_log_no_session_factory(self):
        """没有 session factory 时静默失败。"""
        request = MagicMock()
        request.url.path = "/api/posts"
        request.method = "GET"
        request.headers = {}

        with patch(
            "backend.plugins.request_log.services.get_current_user",
            return_value=None,
        ):
            with patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=None,
            ):
                result = await _write_log_async(request, 200, 15.5)
                assert result is None  # 静默忽略

    async def test_write_log_with_counter_update(self):
        """写入日志时同时更新计数器。"""
        request = MagicMock()
        request.url.path = "/api/posts"
        request.method = "GET"
        request.headers = {}

        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        # 模拟计数器不存在（新建）
        mock_session.execute = AsyncMock(return_value=MagicMock())
        mock_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services.get_current_user",
            return_value=None,
        ):
            with patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=mock_session_factory,
            ):
                result = await _write_log_async(request, 200, 10.0)
                assert result is None
                # 验证 add 被调用了两次：一次 log entry，一次 counter
                assert mock_session.add.call_count == 2


# =============================================================================
# 日志聚合服务测试
# =============================================================================


@pytest.mark.asyncio
class TestLogAggregationService:
    """测试 LogAggregationService。"""

    @pytest.fixture
    def aggregation_service(self):
        """创建聚合服务实例。"""
        return LogAggregationService()

    def test_start_stop(self, aggregation_service):
        """启动和停止调度器。"""
        service = aggregation_service

        # 模拟 APScheduler 可用
        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler:
            mock_scheduler_instance = MagicMock()
            mock_scheduler.return_value = mock_scheduler_instance

            service.start()
            assert service._scheduler is not None
            mock_scheduler_instance.add_job.assert_called()
            mock_scheduler_instance.start.assert_called_once()

            service.stop()
            mock_scheduler_instance.shutdown.assert_called_once()

    def test_start_idempotent(self, aggregation_service):
        """多次启动不应创建多个调度器。"""
        service = aggregation_service

        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler:
            mock_scheduler_instance = MagicMock()
            mock_scheduler.return_value = mock_scheduler_instance

            service.start()
            service.start()  # 第二次调用
            mock_scheduler_instance.start.assert_called_once()

    async def test_aggregate_job_empty(self, aggregation_service):
        """空数据聚合不应抛异常。"""
        service = aggregation_service

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.all.return_value = []
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
            result = await service._aggregate_job()
            assert result is None  # 不应抛异常

    async def test_aggregate_job_with_data(self, aggregation_service):
        """有数据时聚合。"""
        service = aggregation_service

        # 模拟聚合查询返回数据
        mock_row = MagicMock()
        mock_row.ip = "10.0.0.1"
        mock_row.action = "api_call"
        mock_row.yr = 2026
        mock_row.mo = 7
        mock_row.dy = 25
        mock_row.hr = 10
        mock_row.cnt = 5

        # 构造 execute 的 side_effect：第一次调用返回聚合数据，第二次调用返回 None（无已有 counter）
        agg_result = MagicMock()
        agg_result.all.return_value = [mock_row]

        counter_result = MagicMock()
        counter_result.scalar_one_or_none.return_value = None

        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[agg_result, counter_result])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            result = await service._aggregate_job()
            assert result is None
            mock_session.add.assert_called_once()  # 新建 counter
            mock_session.commit.assert_called()

    async def test_cleanup_job(self, aggregation_service):
        """TTL 清理任务。"""
        service = aggregation_service

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        # 模拟 count 查询返回 10
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_count_result
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
            result = await service._cleanup_job()
            assert result is None
            mock_session.commit.assert_called()

    async def test_cleanup_job_empty(self, aggregation_service):
        """TTL 清理空数据。"""
        service = aggregation_service

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_count_result
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
            result = await service._cleanup_job()
            assert result is None
            mock_session.commit.assert_called()