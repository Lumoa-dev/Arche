"""RequestLog 服务行为测试。

测试原则：
- 覆盖行为分类、日志写入、IP 提取、聚合清理
- 用内存数据库做真实交互
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from backend.plugins.request_log.services import (
    LogAggregationService,
    _get_client_ip,
    classify_action,
)


# =============================================================================
# classify_action 单元测试
# =============================================================================


class TestClassifyAction:
    """测试请求行为分类逻辑。"""

    def test_login_fail_detected(self):
        """登录失败（/api/auth/login + 4xx）应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"

    def test_login_success_not_login_fail(self):
        """登录成功不应标记为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) != "login_fail"

    def test_api_call_detected(self):
        """以 /api/ 开头的路径应返回 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/auth/register", 201) == "api_call"

    def test_get_request_is_page_view(self):
        """非 /api/ 的 GET 请求应返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"

    def test_other_methods(self):
        """非 GET 且非 /api/ 的请求应返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/profile", 200) == "other"

    def test_login_fail_takes_precedence(self):
        """登录失败分类应优先于 api_call。"""
        # /api/auth/login 即使以 /api/ 开头，失败时也应为 login_fail
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"


# =============================================================================
# _get_client_ip 单元测试
# =============================================================================


class TestGetClientIp:
    """测试客户端 IP 提取逻辑。"""

    def test_x_forwarded_for_takes_precedence(self):
        """X-Forwarded-For 应优先于 X-Real-IP（request_log 的 _get_client_ip 实现）。"""
        scope = {
            "type": "http",
            "headers": [
                (b"x-real-ip", b"203.0.113.1"),
                (b"x-forwarded-for", b"198.51.100.1, 10.0.0.1"),
            ],
            "client": ("172.16.0.1", 12345),
        }
        request = Request(scope)
        # _get_client_ip 中 X-Forwarded-For 优先级高于 X-Real-IP
        assert _get_client_ip(request) == "198.51.100.1"

    def test_x_forwarded_for_fallback(self):
        """无 X-Real-IP 时应回退到 X-Forwarded-For 首个 IP。"""
        scope = {
            "type": "http",
            "headers": [
                (b"x-forwarded-for", b"198.51.100.1, 10.0.0.1"),
            ],
            "client": ("172.16.0.1", 12345),
        }
        request = Request(scope)
        assert _get_client_ip(request) == "198.51.100.1"

    def test_client_host_fallback(self):
        """无代理头时应回退到 request.client.host。"""
        scope = {
            "type": "http",
            "headers": [],
            "client": ("203.0.113.5", 12345),
        }
        request = Request(scope)
        assert _get_client_ip(request) == "203.0.113.5"

    def test_no_ip_available(self):
        """没有任何 IP 信息时应返回空字符串。"""
        scope = {
            "type": "http",
            "headers": [],
            "client": None,
        }
        request = Request(scope)
        assert _get_client_ip(request) == ""


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    """测试日志聚合服务。"""

    @pytest.mark.asyncio
    async def test_start_stop_scheduler(self):
        """start/stop 调度器应正常启动和停止。"""
        service = LogAggregationService()
        # 首次 start 应创建调度器
        service.start()
        assert service._scheduler is not None

        # 重复 start 不应创建新调度器
        old_scheduler = service._scheduler
        service.start()
        assert service._scheduler is old_scheduler

        # stop 应关闭调度器
        service.stop()
        assert service._scheduler is None

    @pytest.mark.asyncio
    async def test_aggregate_job_handles_no_data(self, db_container):
        """无数据时聚合任务不应报错。"""
        service = LogAggregationService()

        # 模拟 session_factory
        mock_session_factory = db_container.get("db")["session_factory"]

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            # 不应抛出异常
            await service._aggregate_job()

    @pytest.mark.asyncio
    async def test_cleanup_job_handles_no_data(self, db_container):
        """无数据时清理任务不应报错。"""
        service = LogAggregationService()

        mock_session_factory = db_container.get("db")["session_factory"]

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=mock_session_factory,
        ):
            # 不应抛出异常
            await service._cleanup_job()

    @pytest.mark.asyncio
    async def test_aggregate_job_handles_exception(self):
        """聚合任务遇到异常不应向外传播。"""
        service = LogAggregationService()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            side_effect=Exception("DB connection failed"),
        ):
            # 异常应被内部捕获，不向外传播
            await service._aggregate_job()

    @pytest.mark.asyncio
    async def test_cleanup_job_handles_exception(self):
        """清理任务遇到异常不应向外传播。"""
        service = LogAggregationService()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            side_effect=Exception("DB connection failed"),
        ):
            await service._cleanup_job()

    def test_stop_when_not_running(self):
        """未启动时 stop 不应报错。"""
        service = LogAggregationService()
        service.stop()  # 不应抛出异常


# =============================================================================
# RequestLogMiddleware 跳过逻辑测试
# =============================================================================


class TestMiddlewareSkipPaths:
    """测试请求日志中间件的跳过路径逻辑。"""

    @pytest.mark.asyncio
    async def test_skip_docs_path(self):
        """/docs 路径应被跳过。"""
        from backend.plugins.request_log.services import _SKIP_PATHS

        assert "/docs" in _SKIP_PATHS

    @pytest.mark.asyncio
    async def test_skip_static_prefix(self):
        """/static/ 前缀应被跳过。"""
        from backend.plugins.request_log.services import _SKIP_PREFIXES

        assert any("/static/" in p for p in _SKIP_PREFIXES)


# =============================================================================
# _write_log_async 错误处理测试
# =============================================================================


class TestWriteLogAsync:
    """测试异步日志写入的错误处理。"""

    @pytest.mark.asyncio
    async def test_write_log_async_handles_session_failure(self):
        """session_factory 获取失败时不报错。"""
        from backend.plugins.request_log.services import _write_log_async

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.method = "GET"
        mock_request.headers = {}

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=None,
        ):
            await _write_log_async(mock_request, 200, 10.5)


# =============================================================================
# 边界条件测试
# =============================================================================


class TestEdgeCases:
    """测试边界条件。"""

    def test_empty_forwarded_for(self):
        """X-Forwarded-For 为空时应继续回退。"""
        scope = {
            "type": "http",
            "headers": [
                (b"x-forwarded-for", b""),
            ],
            "client": ("203.0.113.5", 12345),
        }
        request = Request(scope)
        # 空字符串 split 后为 [""]，strip 后为 ""，继续回退到 client
        assert _get_client_ip(request) == "203.0.113.5"

    def test_multiple_forwarded_for(self):
        """X-Forwarded-For 有多个 IP 时应取第一个。"""
        scope = {
            "type": "http",
            "headers": [
                (b"x-forwarded-for", b"203.0.113.1, 198.51.100.1, 10.0.0.1"),
            ],
            "client": ("172.16.0.1", 12345),
        }
        request = Request(scope)
        assert _get_client_ip(request) == "203.0.113.1"

    def test_classify_edge_cases(self):
        """边界情况的行为分类。"""
        # 空路径（非 /api/ 前缀，GET 方法 → page_view）
        assert classify_action("GET", "", 200) == "page_view"
        # 根路径
        assert classify_action("GET", "/", 200) == "page_view"
        # 未知方法
        assert classify_action("OPTIONS", "/api/test", 200) == "api_call"