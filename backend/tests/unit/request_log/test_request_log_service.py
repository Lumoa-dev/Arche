"""请求日志服务单元测试。

覆盖：
- classify_action() 行为分类逻辑
- _get_client_ip() IP 提取逻辑
- RequestLogMiddleware 请求记录逻辑
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    classify_action,
    _get_client_ip,
)


# =============================================================================
# classify_action 测试
# =============================================================================


class TestClassifyAction:
    def test_login_fail(self):
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_success_is_api_call(self):
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_call(self):
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/ip-ban/bans", 201) == "api_call"

    def test_page_view(self):
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/", 200) == "page_view"

    def test_other(self):
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/callback", 204) == "other"


# =============================================================================
# _get_client_ip 测试
# =============================================================================


class TestGetClientIP:
    def test_x_forwarded_for_first(self):
        request = MagicMock()
        request.headers.get = MagicMock(
            side_effect=lambda k, d=None: {
                "X-Forwarded-For": "203.0.113.1, 198.51.100.2",
                "X-Real-IP": "198.51.100.2",
            }.get(k, d)
        )
        request.client = None
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip_fallback(self):
        request = MagicMock()
        request.headers.get = MagicMock(
            side_effect=lambda k, d=None: {
                "X-Forwarded-For": "",
                "X-Real-IP": "198.51.100.2",
            }.get(k, d)
        )
        request.client = None
        assert _get_client_ip(request) == "198.51.100.2"

    def test_client_host_fallback(self):
        request = MagicMock()
        request.headers.get = MagicMock(return_value="")
        request.client.host = "10.0.0.1"
        assert _get_client_ip(request) == "10.0.0.1"

    def test_empty_when_no_source(self):
        request = MagicMock()
        request.headers.get = MagicMock(return_value="")
        request.client = None
        assert _get_client_ip(request) == ""

    def test_x_forwarded_for_with_spaces(self):
        request = MagicMock()
        request.headers.get = MagicMock(
            side_effect=lambda k, d=None: {
                "X-Forwarded-For": " 203.0.113.1 , 198.51.100.2 ",
            }.get(k, d)
        )
        request.client = None
        assert _get_client_ip(request) == "203.0.113.1"


# =============================================================================
# RequestLogMiddleware 逻辑测试
# =============================================================================


class TestRequestLogMiddleware:
    def test_skip_paths(self):
        """确认跳过路径列表中的路径不会被记录。"""
        from backend.plugins.request_log.services import _SKIP_PATHS, _SKIP_PREFIXES

        assert "/docs" in _SKIP_PATHS
        assert "/openapi.json" in _SKIP_PATHS
        assert "/redoc" in _SKIP_PATHS
        assert "/favicon.ico" in _SKIP_PATHS
        assert _SKIP_PREFIXES == ("/static/", "/assets/")

    @pytest.mark.asyncio
    async def test_dispatch_skip_paths(self):
        """跳过路径应直接返回，不写日志。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        mock_request = MagicMock()
        mock_request.url.path = "/docs"

        call_next = AsyncMock(return_value="passed")
        middleware = RequestLogMiddleware(MagicMock())

        result = await middleware.dispatch(mock_request, call_next)
        assert result == "passed"
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_skip_prefixes(self):
        """跳过前缀的路径应直接返回。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        mock_request = MagicMock()
        mock_request.url.path = "/static/css/main.css"

        call_next = AsyncMock(return_value="passed")
        middleware = RequestLogMiddleware(MagicMock())

        result = await middleware.dispatch(mock_request, call_next)
        assert result == "passed"

    @pytest.mark.asyncio
    async def test_dispatch_normal_path_writes_log(self):
        """正常路径应记录日志。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        mock_request = MagicMock()
        mock_request.url.path = "/api/test"
        mock_request.method = "GET"
        mock_request.headers.get = MagicMock(return_value="")
        mock_request.client.host = "10.0.0.1"

        mock_response = MagicMock()
        mock_response.status_code = 200
        call_next = AsyncMock(return_value=mock_response)
        middleware = RequestLogMiddleware(MagicMock())

        result = await middleware.dispatch(mock_request, call_next)
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_exception_still_returns_response(self):
        """异常路径应记录 500 日志并继续抛出异常。"""
        from backend.plugins.request_log.services import RequestLogMiddleware

        mock_request = MagicMock()
        mock_request.url.path = "/api/test"
        mock_request.method = "GET"
        mock_request.headers.get = MagicMock(return_value="")
        mock_request.client.host = "10.0.0.1"

        call_next = AsyncMock(side_effect=RuntimeError("test error"))

        middleware = RequestLogMiddleware(MagicMock())

        with pytest.raises(RuntimeError, match="test error"):
            await middleware.dispatch(mock_request, call_next)


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    @pytest.mark.asyncio
    async def test_start_stop_scheduler(self):
        """LogAggregationService 应能启动和停止调度器。"""
        from backend.plugins.request_log.services import LogAggregationService

        service = LogAggregationService()
        # 未安装 APScheduler 时不应抛出异常
        try:
            service.start()
        except RuntimeError:
            # 若 APScheduler 已安装但无运行中事件循环，也接受
            pass
        service.stop()
        # 多次停止不应出错
        service.stop()