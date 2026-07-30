"""请求日志服务单元测试 —— 覆盖行为分类、客户端 IP 提取及日志写入逻辑。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestClassifyAction:
    """classify_action 纯函数测试。"""

    @pytest.fixture
    def classify_action(self):
        from backend.plugins.request_log.services import classify_action
        return classify_action

    def test_login_fail(self, classify_action):
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_success_not_fail(self, classify_action):
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_call(self, classify_action):
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/ip-ban/bans", 201) == "api_call"

    def test_page_view(self, classify_action):
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/", 200) == "page_view"

    def test_other(self, classify_action):
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/data", 200) == "other"


class TestGetClientIp:
    """_get_client_ip 纯函数测试。"""

    @pytest.fixture
    def get_client_ip(self):
        from backend.plugins.request_log.services import _get_client_ip
        return _get_client_ip

    def test_x_forwarded_for_first(self, get_client_ip):
        request = MagicMock()
        request.headers.get.side_effect = lambda key, default=None: (
            "203.0.113.1, 10.0.0.1" if key == "X-Forwarded-For" else
            "" if key == "X-Real-IP" else default
        )
        request.client = None
        ip = get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_x_real_ip_fallback(self, get_client_ip):
        request = MagicMock()
        request.headers.get.side_effect = lambda key, default=None: (
            "" if key == "X-Forwarded-For" else
            "198.51.100.1" if key == "X-Real-IP" else default
        )
        request.client = None
        ip = get_client_ip(request)
        assert ip == "198.51.100.1"

    def test_client_host_fallback(self, get_client_ip):
        request = MagicMock()
        request.headers.get.side_effect = lambda key, default=None: ""
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        ip = get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_no_ip_available(self, get_client_ip):
        request = MagicMock()
        request.headers.get.side_effect = lambda key, default=None: ""
        request.client = None
        ip = get_client_ip(request)
        assert ip == ""


class TestRequestLogMiddleware:
    """RequestLogMiddleware 分发逻辑测试。"""

    @pytest.fixture
    def middleware(self):
        from backend.plugins.request_log.services import RequestLogMiddleware
        app = MagicMock()
        return RequestLogMiddleware(app)

    @pytest.mark.asyncio
    async def test_skip_paths(self, middleware):
        """_SKIP_PATHS 中的路径应跳过。"""
        for path in ("/docs", "/openapi.json", "/redoc", "/favicon.ico"):
            request = MagicMock()
            request.url.path = path
            call_next = AsyncMock(return_value="ok")
            result = await middleware.dispatch(request, call_next)
            assert result == "ok"

    @pytest.mark.asyncio
    async def test_skip_prefixes(self, middleware):
        """_SKIP_PREFIXES 开头的路径应跳过。"""
        for path in ("/static/test.js", "/assets/logo.png"):
            request = MagicMock()
            request.url.path = path
            call_next = AsyncMock(return_value="ok")
            result = await middleware.dispatch(request, call_next)
            assert result == "ok"

    @pytest.mark.asyncio
    async def test_normal_path_writes_log(self, middleware):
        """正常路径应触发日志写入。"""
        with patch("backend.plugins.request_log.services._write_log_async") as mock_write:
            request = MagicMock()
            request.url.path = "/api/test"
            request.method = "GET"
            request.headers = {}
            request.client = MagicMock()
            request.client.host = "127.0.0.1"
            response = MagicMock()
            response.status_code = 200
            call_next = AsyncMock(return_value=response)

            result = await middleware.dispatch(request, call_next)
            assert result == response
            # 给 create_task 机会执行
            await asyncio.sleep(0)
            mock_write.assert_awaited_once()


class TestLogAggregationService:
    """LogAggregationService 定时任务测试。"""

    @pytest.fixture
    def service(self):
        from backend.plugins.request_log.services import LogAggregationService
        return LogAggregationService()

    def test_start_no_apscheduler(self, service):
        """APScheduler 未安装时，start 应静默跳过。"""
        with patch.dict("sys.modules", {"apscheduler.schedulers.asyncio": None}):
            service.start()
            assert service._scheduler is None

    def test_stop_without_start(self, service):
        """未启动时 stop 不应抛出异常。"""
        service.stop()  # 不应抛出异常

    def test_start_twice(self, service):
        """重复启动应被忽略。"""
        with patch("apscheduler.schedulers.asyncio.AsyncIOScheduler") as mock_scheduler:
            mock_instance = MagicMock()
            mock_scheduler.return_value = mock_instance

            service.start()
            scheduler1 = service._scheduler
            service.start()
            assert service._scheduler is scheduler1  # 同一实例
            mock_scheduler.assert_called_once()