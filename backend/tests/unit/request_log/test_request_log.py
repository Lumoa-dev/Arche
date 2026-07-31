"""请求日志单元测试 —— classify_action、_get_client_ip、LogAggregationService。

测试原则：
- 纯函数测试不依赖数据库
- 模拟 FastAPI Request 对象测试 IP 提取
- 覆盖边界条件：空头、代理链、异常路径
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    LogAggregationService,
    _get_client_ip,
    classify_action,
)


# =============================================================================
# classify_action 测试
# =============================================================================


class TestClassifyAction:
    """行为分类函数测试。"""

    def test_login_fail(self):
        """登录失败（POST /api/auth/login + 4xx）应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 429) == "login_fail"

    def test_login_success_not_login_fail(self):
        """登录成功（2xx）不应返回 login_fail。"""
        result = classify_action("POST", "/api/auth/login", 200)
        assert result == "api_call"  # 200 时走 api_call 分支

    def test_api_call(self):
        """API 路径返回 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/auth/register", 201) == "api_call"

    def test_page_view(self):
        """非 API 的 GET 请求返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"

    def test_other(self):
        """非 API 的非 GET 请求返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/webhook/callback", 200) == "other"
        assert classify_action("DELETE", "/some-resource", 204) == "other"

    def test_sub_paths(self):
        """API 子路径也应归类为 api_call。"""
        assert classify_action("GET", "/api/admin/users", 200) == "api_call"
        assert classify_action("POST", "/api/ip-ban/bans", 200) == "api_call"

    def test_login_fail_with_different_errors(self):
        """各种 4xx 状态码都应归类为 login_fail。"""
        for status in (400, 401, 403, 404, 422, 429):
            assert classify_action("POST", "/api/auth/login", status) == "login_fail"


# =============================================================================
# _get_client_ip 测试
# =============================================================================


class TestGetClientIp:
    """客户端 IP 提取函数测试。"""

    def _make_request(self, headers: dict | None = None, client_host: str | None = "127.0.0.1"):
        """创建模拟 FastAPI Request。"""
        mock = MagicMock()
        mock.headers = headers or {}
        mock.client = MagicMock()
        mock.client.host = client_host
        return mock

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 取第一个 IP。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1, 192.168.1.1"},
            client_host="10.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip(self):
        """X-Real-IP 头。"""
        request = self._make_request(
            headers={"X-Real-IP": "203.0.113.5"},
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.5"

    def test_x_forwarded_for_precedence(self):
        """X-Forwarded-For 优先于 X-Real-IP。"""
        request = self._make_request(
            headers={
                "X-Forwarded-For": "203.0.113.1",
                "X-Real-IP": "10.0.0.1",
            },
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_fallback_to_client_host(self):
        """无代理头时回退到 request.client.host。"""
        request = self._make_request(headers={}, client_host="192.168.1.1")
        assert _get_client_ip(request) == "192.168.1.1"

    def test_empty_forwarded_for(self):
        """空 X-Forwarded-For 应回退。"""
        request = self._make_request(
            headers={"X-Forwarded-For": ""},
            client_host="10.0.0.1",
        )
        assert _get_client_ip(request) == "10.0.0.1"

    def test_no_client(self):
        """request.client 为 None 时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""

    def test_ipv6_in_forwarded_for(self):
        """IPv6 地址在代理链中。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "2001:db8::1, 10.0.0.1"},
        )
        assert _get_client_ip(request) == "2001:db8::1"


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    """日志聚合服务测试。"""

    @pytest.mark.asyncio
    async def test_start_creates_scheduler(self):
        """start 应创建 APScheduler 实例。"""
        service = LogAggregationService()
        service.start()
        assert service._scheduler is not None
        assert service._scheduler.running

        # 验证任务已注册
        jobs = service._scheduler.get_jobs()
        job_ids = [j.id for j in jobs]
        assert "request_log_aggregate" in job_ids
        assert "request_log_cleanup" in job_ids
        assert len(jobs) == 2

        service.stop()

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """多次 start 应只创建一个 scheduler。"""
        service = LogAggregationService()
        service.start()
        s1 = service._scheduler
        service.start()  # 第二次调用
        assert service._scheduler is s1  # 同一个实例

        service.stop()

    @pytest.mark.asyncio
    async def test_stop_shuts_down_scheduler(self):
        """stop 应关闭 scheduler。"""
        service = LogAggregationService()
        service.start()
        assert service._scheduler.running
        service.stop()
        assert service._scheduler is None

    def test_stop_without_start(self):
        """未 start 时 stop 不应崩溃。"""
        service = LogAggregationService()
        service.stop()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_aggregate_job_handles_empty_db(self):
        """空数据库时聚合任务不应崩溃。"""
        service = LogAggregationService()
        # 直接调用异步方法，不依赖 scheduler
        await service._aggregate_job()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_cleanup_job_handles_empty_db(self):
        """空数据库时清理任务不应崩溃。"""
        service = LogAggregationService()
        await service._cleanup_job()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_aggregate_job_logs_on_exception(self):
        """聚合任务异常应记录日志而非崩溃。"""
        with patch("backend.plugins.request_log.services._get_session_factory", return_value=None):
            service = LogAggregationService()
            # session_factory 为 None 时，_aggregate_job 应捕获异常
            await service._aggregate_job()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_cleanup_job_logs_on_exception(self):
        """清理任务异常应记录日志而非崩溃。"""
        with patch("backend.plugins.request_log.services._get_session_factory", return_value=None):
            service = LogAggregationService()
            await service._cleanup_job()  # 不应抛出异常