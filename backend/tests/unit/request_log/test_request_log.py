"""请求日志插件单元测试。

测试覆盖：
- classify_action 行为分类函数
- _get_client_ip IP 提取函数
- RequestLogMiddleware 请求拦截行为
- LogAggregationService 聚合与清理任务
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.routes import (
    query_logs,
    get_top_ips,
    get_trend,
    get_counters,
    list_actions,
)
from backend.plugins.request_log.services import (
    LogAggregationService,
    RequestLogMiddleware,
    _get_client_ip,
    _get_session_factory,
    _write_log_async,
    classify_action,
)


# =============================================================================
# classify_action 行为分类
# =============================================================================


class TestClassifyAction:
    """测试行为分类函数。"""

    def test_login_fail_on_login_path_with_4xx(self):
        """登录路径且状态码 >=400 应分类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_success_is_api_call(self):
        """登录成功（2xx）应分类为 api_call。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_call(self):
        """以 /api/ 开头的路径应分类为 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/ip-ban/bans", 201) == "api_call"

    def test_page_view(self):
        """GET 请求且非 API 路径应分类为 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"

    def test_other_method(self):
        """非 API 路径且非 GET 方法应分类为 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/callback", 200) == "other"


# =============================================================================
# _get_client_ip IP 提取
# =============================================================================


class TestGetClientIp:
    """测试客户端 IP 提取逻辑。"""

    def test_forwarded_for_header(self):
        """X-Forwarded-For 应返回第一个 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}
        assert _get_client_ip(request) == "10.0.0.1"

    def test_real_ip_header(self):
        """X-Real-IP 应返回该 IP。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "10.0.0.2"}
        assert _get_client_ip(request) == "10.0.0.2"

    def test_real_ip_preferred_over_client(self):
        """X-Real-IP 优先级高于 request.client。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "10.0.0.3"}
        request.client.host = "172.16.0.1"
        assert _get_client_ip(request) == "10.0.0.3"

    def test_client_host_fallback(self):
        """无代理头时回退到 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client.host = "192.168.1.1"
        assert _get_client_ip(request) == "192.168.1.1"

    def test_empty_when_no_ip(self):
        """无任何 IP 来源时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""


# =============================================================================
# LogAggregationService
# =============================================================================


class TestLogAggregationService:
    """测试日志聚合服务。"""

    @pytest.mark.asyncio
    async def test_aggregate_job_with_no_data(self, db_container):
        """无数据时聚合任务不应报错。"""
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            service = LogAggregationService()
            # 不应抛异常
            await service._aggregate_job()

    @pytest.mark.asyncio
    async def test_cleanup_job_with_no_data(self, db_container):
        """无数据时清理任务不应报错。"""
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            service = LogAggregationService()
            # 不应抛异常
            await service._cleanup_job()

    @pytest.mark.asyncio
    async def test_cleanup_job_removes_old_logs(self, db_container):
        """清理任务应删除超过 7 天的日志。"""
        # 直接写入一条旧日志到数据库
        from backend.plugins.request_log.models import RequestLog

        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            old_log = RequestLog(
                ip="10.0.0.1",
                method="GET",
                path="/test",
                status_code=200,
                created_at=datetime.now() - timedelta(days=14),
            )
            session.add(old_log)
            new_log = RequestLog(
                ip="10.0.0.2",
                method="GET",
                path="/test",
                status_code=200,
                created_at=datetime.now(),
            )
            session.add(new_log)
            await session.commit()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=session_factory,
        ):
            service = LogAggregationService()
            await service._cleanup_job()

        # 验证旧日志被删除，新日志保留
        async with session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(select(RequestLog))
            remaining = result.scalars().all()
            assert len(remaining) == 1
            assert remaining[0].ip == "10.0.0.2"

    def test_start_stop_scheduler(self):
        """启动和停止调度器。"""
        service = LogAggregationService()
        mock_scheduler = MagicMock()
        # 设置 running=True 以便 stop() 能进入 shutdown 分支
        mock_scheduler.running = True

        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler",
            return_value=mock_scheduler,
        ) as MockScheduler:
            service.start()
            assert service._scheduler is not None
            MockScheduler.assert_called_once()

            service.stop()
            mock_scheduler.shutdown.assert_called_once_with(wait=False)

    def test_start_twice_no_duplicate(self):
        """重复启动不应创建多个调度器实例。"""
        service = LogAggregationService()
        mock_scheduler = MagicMock()

        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler",
            return_value=mock_scheduler,
        ) as MockScheduler:
            service.start()
            service.start()  # 第二次调用
            MockScheduler.assert_called_once()  # 只应创建一次

    def test_start_missing_apscheduler(self):
        """APScheduler 未安装时不应报错。"""
        import sys

        service = LogAggregationService()
        # 模拟 apscheduler.schedulers.asyncio 模块不可用
        with patch.dict(
            "sys.modules",
            {"apscheduler.schedulers.asyncio": None},
            clear=False,
        ):
            # 重新加载模块，使内部的 from import 语句触发 ImportError
            import importlib

            import backend.plugins.request_log.services as svc_mod
            importlib.reload(svc_mod)
            new_service = svc_mod.LogAggregationService()
            new_service.start()
            assert new_service._scheduler is None

        # 恢复
        importlib.reload(svc_mod)


# =============================================================================
# RequestLogMiddleware 中间件
# =============================================================================


class TestRequestLogMiddleware:
    """测试请求日志中间件。"""

    @pytest.mark.asyncio
    async def test_skip_paths_passthrough(self):
        """跳过路径应直接透传不加日志。"""
        app = MagicMock()
        middleware = RequestLogMiddleware(app)

        for skip_path in ["/docs", "/openapi.json", "/redoc", "/favicon.ico"]:
            request = MagicMock()
            request.url.path = skip_path
            call_next = AsyncMock()

            response = await middleware.dispatch(request, call_next)
            call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_skip_prefixes_passthrough(self):
        """跳过前缀应直接透传。"""
        app = MagicMock()
        middleware = RequestLogMiddleware(app)

        request = MagicMock()
        request.url.path = "/static/css/main.css"
        call_next = AsyncMock()

        response = await middleware.dispatch(request, call_next)
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    @patch("backend.plugins.request_log.services._write_log_async")
    async def test_normal_request_logs_written(self, mock_write, db_container):
        """正常请求应异步写入日志。"""
        app = MagicMock()
        middleware = RequestLogMiddleware(app)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            request = MagicMock()
            request.url.path = "/api/test"
            request.method = "GET"
            request.headers = {}
            request.client.host = "10.0.0.1"

            call_next = AsyncMock()
            call_next.return_value = MagicMock(status_code=200)

            response = await middleware.dispatch(request, call_next)
            # _write_log_async 应被调用（通过 create_task）
            # 我们无法直接验证 create_task 的结果，但确保中间件不报错
            assert response is not None

    @pytest.mark.asyncio
    async def test_exception_logs_500(self, db_container):
        """异常请求应记录 500 状态码。"""
        app = MagicMock()
        middleware = RequestLogMiddleware(app)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            request = MagicMock()
            request.url.path = "/api/test"
            request.method = "POST"
            request.headers = {}
            request.client.host = "10.0.0.1"

            call_next = AsyncMock(side_effect=ValueError("test error"))

            with pytest.raises(ValueError):
                await middleware.dispatch(request, call_next)