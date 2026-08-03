"""RequestLog 服务层 —— classify_action / RequestLogMiddleware / LogAggregationService 行为测试。

测试原则：
- classify_action 是纯函数，同步测试
- RequestLogMiddleware 用 mock 隔离 DB
- LogAggregationService 用 mock 隔离调度器和 DB
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from backend.plugins.request_log.services import (
    LogAggregationService,
    RequestLogMiddleware,
    classify_action,
    _get_client_ip,
    _write_log_async,
)


# =============================================================================
# classify_action 纯函数测试
# =============================================================================


class TestClassifyAction:
    """请求行为分类测试。"""

    def test_login_path_with_400_returns_login_fail(self):
        """登录路径 + 4xx 状态码应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"

    def test_login_path_with_200_returns_api_call(self):
        """登录路径 + 200 状态码应返回 api_call。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_path_returns_api_call(self):
        """API 路径应返回 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"

    def test_get_non_api_returns_page_view(self):
        """GET 非 API 路径应返回 page_view。"""
        assert classify_action("GET", "/about", 200) == "page_view"

    def test_post_non_api_returns_other(self):
        """POST 非 API 路径应返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"

    def test_put_non_api_returns_other(self):
        """PUT 非 API 路径应返回 other。"""
        assert classify_action("PUT", "/upload", 200) == "other"

    def test_delete_non_api_returns_other(self):
        """DELETE 非 API 路径应返回 other。"""
        assert classify_action("DELETE", "/temp", 200) == "other"


# =============================================================================
# _get_client_ip 工具函数测试
# =============================================================================


class TestGetClientIp:
    """获取客户端 IP 工具函数测试。"""

    def _make_request(self, headers: dict | None = None, client_host: str | None = None):
        scope = {
            "type": "http",
            "path": "/api/test",
            "method": "GET",
            "headers": [],
            "client": (client_host, 12345) if client_host else None,
        }
        if headers:
            scope["headers"] = [
                (k.lower().encode(), v.encode()) for k, v in headers.items()
            ]
        return Request(scope)

    def test_x_forwarded_for_is_used_first(self):
        """X-Forwarded-For 应优先使用。"""
        request = self._make_request(
            headers={
                "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
                "X-Real-IP": "198.51.100.1",
            },
            client_host="172.16.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip_is_fallback(self):
        """X-Real-IP 应作为 X-Forwarded-For 的 fallback。"""
        request = self._make_request(
            headers={"X-Real-IP": "198.51.100.1"},
            client_host="172.16.0.1",
        )
        assert _get_client_ip(request) == "198.51.100.1"

    def test_client_host_is_last_fallback(self):
        """request.client.host 应作为最后 fallback。"""
        request = self._make_request(client_host="172.16.0.1")
        assert _get_client_ip(request) == "172.16.0.1"

    def test_returns_empty_when_none_available(self):
        """没有任何 IP 信息时应返回空字符串。"""
        request = self._make_request()
        assert _get_client_ip(request) == ""


# =============================================================================
# RequestLogMiddleware 测试
# =============================================================================


@pytest.mark.asyncio
class TestRequestLogMiddleware:
    """RequestLogMiddleware 分发行为测试。"""

    async def _make_middleware(self):
        return RequestLogMiddleware(MagicMock())

    async def _make_request(self, path: str, method: str = "GET"):
        scope = {
            "type": "http",
            "path": path,
            "method": method,
            "headers": [],
            "client": ("10.0.0.1", 12345),
        }
        return Request(scope)

    async def test_skip_docs_path(self):
        """文档路径应跳过日志记录。"""
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
        middleware = await self._make_middleware()
        request = await self._make_request("/docs")

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        call_next.assert_awaited_once()

    async def test_skip_openapi_path(self):
        """OpenAPI 路径应跳过日志记录。"""
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
        middleware = await self._make_middleware()
        request = await self._make_request("/openapi.json")

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    async def test_skip_static_path(self):
        """静态资源路径应跳过日志记录。"""
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
        middleware = await self._make_middleware()
        request = await self._make_request("/static/css/main.css")

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    async def test_normal_api_path_records_log(self):
        """正常 API 路径应记录日志。"""
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
        middleware = await self._make_middleware()
        request = await self._make_request("/api/blog/posts")

        with patch(
            "backend.plugins.request_log.services._write_log_async",
            new=AsyncMock(),
        ) as mock_write:
            response = await middleware.dispatch(request, call_next)

        # asyncio.create_task 是 fire-and-forget，需要让事件循环执行它
        await asyncio.sleep(0)

        assert response.status_code == 200
        call_next.assert_awaited_once()
        mock_write.assert_awaited_once()

    async def test_exception_in_handler_still_calls_write_log(self):
        """handler 抛出异常时仍应调用 _write_log_async。"""
        call_next = AsyncMock(side_effect=RuntimeError("handler error"))
        middleware = await self._make_middleware()
        request = await self._make_request("/api/blog/posts")

        with patch(
            "backend.plugins.request_log.services._write_log_async",
            new=AsyncMock(),
        ) as mock_write:
            with pytest.raises(RuntimeError):
                await middleware.dispatch(request, call_next)

        # asyncio.create_task 是 fire-and-forget，需要让事件循环执行它
        await asyncio.sleep(0)

        # 即使 handler 异常，也应记录日志
        mock_write.assert_awaited_once()


# =============================================================================
# LogAggregationService 测试
# =============================================================================


@pytest.mark.asyncio
class TestLogAggregationService:
    """LogAggregationService 行为测试。"""

    async def test_start_creates_scheduler(self):
        """start() 应创建并启动调度器。"""
        service = LogAggregationService()

        # AsyncIOScheduler 是在 start() 内部导入的，需 patch 其原始路径
        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler_cls:
            mock_scheduler = MagicMock()
            mock_scheduler_cls.return_value = mock_scheduler

            service.start()

            assert service._scheduler is not None
            mock_scheduler.add_job.assert_called()
            mock_scheduler.start.assert_called_once()

    async def test_start_idempotent(self):
        """多次调用 start() 不应创建多个调度器。"""
        service = LogAggregationService()

        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler_cls:
            mock_scheduler = MagicMock()
            mock_scheduler_cls.return_value = mock_scheduler

            service.start()
            service.start()  # 第二次调用

            mock_scheduler_cls.assert_called_once()

    async def test_stop_shuts_down_scheduler(self):
        """stop() 应关闭调度器。"""
        service = LogAggregationService()

        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler_cls:
            mock_scheduler = MagicMock()
            mock_scheduler.running = True
            mock_scheduler_cls.return_value = mock_scheduler

            service.start()
            service.stop()

            mock_scheduler.shutdown.assert_called_once()
            assert service._scheduler is None

    async def test_aggregate_job_handles_empty_result(self):
        """聚合任务在无数据时不应抛出异常。"""
        service = LogAggregationService()

        # mock session_factory
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value = AsyncMock()
        mock_session.execute.return_value.all.return_value = []

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            # 不应抛出异常
            await service._aggregate_job()

    async def test_cleanup_job_handles_empty_result(self):
        """清理任务在无数据时不应抛出异常。"""
        service = LogAggregationService()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            # 不应抛出异常
            await service._cleanup_job()

    async def test_aggregate_job_exception_caught(self):
        """聚合任务异常应被捕获，不向上传播。"""
        service = LogAggregationService()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            side_effect=RuntimeError("DB unavailable"),
        ):
            # 不应抛出异常（内部已 catch）
            await service._aggregate_job()

    async def test_cleanup_job_exception_caught(self):
        """清理任务异常应被捕获，不向上传播。"""
        service = LogAggregationService()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            side_effect=RuntimeError("DB unavailable"),
        ):
            # 不应抛出异常（内部已 catch）
            await service._cleanup_job()


# =============================================================================
# _write_log_async 测试
# =============================================================================


@pytest.mark.asyncio
class TestWriteLogAsync:
    """_write_log_async 异步写日志行为测试。"""

    async def _make_request(self, path: str = "/api/test", method: str = "GET"):
        scope = {
            "type": "http",
            "path": path,
            "method": method,
            "headers": [],
            "client": ("10.0.0.1", 12345),
        }
        return Request(scope)

    async def test_write_log_creates_request_log_entry(self):
        """写入日志应创建 RequestLog 记录。"""
        request = await self._make_request()

        # 安排 mock 的 session_factory 和 session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

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
            await _write_log_async(request, 200, 15.5)

        # 验证 session.add 被调用（至少一次是 RequestLog，一次是 IpActionCounter）
        assert mock_session.add.call_count >= 1
        mock_session.commit.assert_awaited_once()

    async def test_write_log_handles_missing_session_factory(self):
        """session_factory 不可用时不应抛出异常。"""
        request = await self._make_request()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=None,
        ):
            # 不应抛出异常
            await _write_log_async(request, 200, 15.5)

    async def test_write_log_handles_exception_gracefully(self):
        """写入日志异常应被捕获，不向上传播。"""
        request = await self._make_request()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            side_effect=RuntimeError("DB error")
        )

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            # 不应抛出异常（内部已 catch）
            await _write_log_async(request, 200, 15.5)