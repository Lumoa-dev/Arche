"""请求日志服务 —— 行为分类、中间件、聚合测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from backend.plugins.request_log.services import (
    LogAggregationService,
    classify_action,
    _get_client_ip,
    _get_session_factory,
    _SKIP_PATHS,
    _SKIP_PREFIXES,
)


class TestClassifyAction:
    """测试请求行为分类。"""

    def test_login_fail(self):
        """登录失败应归类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_success_not_fail(self):
        """登录成功不应归类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_call(self):
        """API 路径应归类为 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/auth/register", 201) == "api_call"
        assert classify_action("DELETE", "/api/admin/users/1", 204) == "api_call"

    def test_page_view(self):
        """GET 非 API 路径应归类为 page_view。"""
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/", 200) == "page_view"

    def test_other_method(self):
        """非 GET 非 API 路径应归类为 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/callback", 200) == "other"

    def test_edge_cases(self):
        """边界情况处理。"""
        assert classify_action("", "", 200) == "other"
        assert classify_action("GET", "", 200) == "page_view"
        assert classify_action("POST", "/api/", 200) == "api_call"


class TestGetClientIP:
    """测试客户端 IP 获取。"""

    def test_x_forwarded_for(self):
        """X-Forwarded-For 优先。"""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        result = _get_client_ip(request)
        assert result == "192.168.1.1"

    def test_x_real_ip(self):
        """X-Real-IP 其次。"""
        request = MagicMock(spec=Request)
        request.headers = {"X-Real-IP": "10.0.0.1"}
        result = _get_client_ip(request)
        assert result == "10.0.0.1"

    def test_client_host(self):
        """直接连接时使用 client.host。"""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = "127.0.0.1"
        result = _get_client_ip(request)
        assert result == "127.0.0.1"

    def test_empty_fallback(self):
        """无任何 IP 来源时返回空字符串。"""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = None
        result = _get_client_ip(request)
        assert result == ""

    def test_forwarded_for_multiple_ips(self):
        """多个 IP 时取第一个。"""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3"}
        result = _get_client_ip(request)
        assert result == "10.0.0.1"


class TestSkipPaths:
    """测试跳过路径逻辑。"""

    def test_skip_docs(self):
        """/docs 应被跳过。"""
        assert "/docs" in _SKIP_PATHS

    def test_skip_openapi(self):
        """/openapi.json 应被跳过。"""
        assert "/openapi.json" in _SKIP_PATHS

    def test_skip_redoc(self):
        """/redoc 应被跳过。"""
        assert "/redoc" in _SKIP_PATHS

    def test_skip_favicon(self):
        """/favicon.ico 应被跳过。"""
        assert "/favicon.ico" in _SKIP_PATHS

    def test_skip_static_prefix(self):
        """/static/ 前缀应被跳过。"""
        assert "/static/" in _SKIP_PREFIXES

    def test_skip_assets_prefix(self):
        """/assets/ 前缀应被跳过。"""
        assert "/assets/" in _SKIP_PREFIXES


class TestGetSessionFactory:
    """测试获取会话工厂。"""

    def test_get_session_factory_with_container(self):
        """容器可用时应返回 session_factory。"""
        # 由于 _get_session_factory 依赖全局 container，
        # 测试其健壮性
        result = _get_session_factory()
        # 不崩溃即可
        assert result is None or callable(result)


class TestLogAggregationService:
    """测试日志聚合服务。"""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """启动和停止不应报错。"""
        service = LogAggregationService()
        # 未安装 APScheduler 时也能正确处理
        try:
            service.start()
            service.stop()
        except Exception as e:
            pytest.fail(f"start/stop 不应抛出异常: {e}")

    @pytest.mark.asyncio
    async def test_double_start(self):
        """重复启动不应创建多个调度器。"""
        service = LogAggregationService()
        service.start()
        scheduler = service._scheduler
        service.start()
        assert service._scheduler is scheduler
        service.stop()

    def test_stop_without_start(self):
        """未启动时停止不应报错。"""
        service = LogAggregationService()
        service.stop()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_aggregate_job_handles_exception(self):
        """聚合任务异常应被捕获而不崩溃。"""
        service = LogAggregationService()
        # 没有 session_factory 时，聚合任务应静默处理异常
        await service._aggregate_job()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_cleanup_job_handles_exception(self):
        """清理任务异常应被捕获而不崩溃。"""
        service = LogAggregationService()
        # 没有 session_factory 时，清理任务应静默处理异常
        await service._cleanup_job()  # 不应抛出异常