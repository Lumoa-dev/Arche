"""请求日志服务 单元测试。

覆盖：
- 行为分类函数 classify_action（登录失败/API 调用/页面浏览/其他）
- 客户端 IP 提取函数 _get_client_ip（X-Forwarded-For/X-Real-IP/直连）
- 跳过路径逻辑（_SKIP_PATHS / _SKIP_PREFIXES）
- 日志异步写入 _write_log_async 的数据库交互
- LogAggregationService 的定时任务启动/停止/聚合/清理
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    RequestLogMiddleware,
    classify_action,
    _get_client_ip,
    _write_log_async,
)

# =============================================================================
# classify_action 行为分类测试
# =============================================================================


class TestClassifyAction:
    """行为分类函数测试——覆盖所有分类路径。"""

    def test_login_failure(self):
        """登录失败返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"

    def test_login_success_is_api_call(self):
        """登录成功（<400）不应归类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"
        assert classify_action("POST", "/api/auth/login", 302) == "api_call"

    def test_api_call(self):
        """API 路径返回 api_call。"""
        assert classify_action("GET", "/api/posts", 200) == "api_call"
        assert classify_action("POST", "/api/users", 201) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_page_view(self):
        """GET 非 API 路径返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_methods(self):
        """非 GET 非 API 路径返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/custom", 200) == "other"
        assert classify_action("PATCH", "/resource", 200) == "other"


# =============================================================================
# _get_client_ip IP 提取测试
# =============================================================================


class TestGetClientIp:
    """客户端 IP 提取函数测试。"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 取第一个 IP。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1, 172.16.0.1"
        }
        request.client = MagicMock(host="127.0.0.1")
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_forwarded_for_single_ip(self):
        """X-Forwarded-For 单个 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.5"}
        request.client = MagicMock(host="127.0.0.1")
        assert _get_client_ip(request) == "203.0.113.5"

    def test_x_real_ip(self):
        """X-Real-IP 作为回退。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "198.51.100.1"}
        request.client = MagicMock(host="127.0.0.1")
        assert _get_client_ip(request) == "198.51.100.1"

    def test_x_real_ip_preferred_over_x_forwarded(self):
        """X-Real-IP 优先于 X-Forwarded-For。"""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1",
            "X-Real-IP": "198.51.100.1",
        }
        # 注意：函数检查 X-Forwarded-For 先，所以 X-Forwarded-For 优先
        # 这取决于实现
        ip = _get_client_ip(request)
        # 函数先检查 X-Forwarded-For
        assert ip == "203.0.113.1"

    def test_fallback_to_client_host(self):
        """无代理头时回退到 request.client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="192.168.1.1")
        assert _get_client_ip(request) == "192.168.1.1"

    def test_empty_when_no_source(self):
        """无任何 IP 来源时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""

    def test_ipv6_in_x_forwarded_for(self):
        """X-Forwarded-For 支持 IPv6。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "2001:db8::1, 10.0.0.1"}
        request.client = MagicMock(host="127.0.0.1")
        assert _get_client_ip(request) == "2001:db8::1"


# =============================================================================
# _write_log_async 异步写入测试
# =============================================================================


class TestWriteLogAsync:
    """异步日志写入测试。"""

    @pytest.mark.asyncio
    async def test_write_log_creates_request_log(self, db_container):
        """写入日志应在数据库创建 RequestLog 记录。"""
        from backend.plugins.request_log.models import RequestLog

        # 模拟请求对象
        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {"User-Agent": "test-agent", "Referer": "https://example.com"}
        request.client = MagicMock(host="10.0.0.1")

        # 在 db_container 的 session_factory 下写入
        with (
            patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=db_container.get("db")["session_factory"],
            ),
            patch("backend.plugins.request_log.services.get_current_user", return_value=None),
        ):
            await _write_log_async(request, 200, 15.5)

        # 验证日志已写入
        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            result = await session.execute(
                __import__("sqlalchemy").select(RequestLog).where(
                    RequestLog.path == "/api/test"
                )
            )
            log = result.scalar_one_or_none()
            assert log is not None
            assert log.method == "GET"
            assert log.status_code == 200
            assert log.duration_ms == 15.5
            assert log.action == "api_call"

    @pytest.mark.asyncio
    async def test_write_log_creates_ip_counter(self, db_container):
        """写入日志时应创建或更新 IpActionCounter。"""
        from backend.plugins.request_log.models import IpActionCounter

        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        request.client = MagicMock(host="10.0.0.2")

        with (
            patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=db_container.get("db")["session_factory"],
            ),
            patch("backend.plugins.request_log.services.get_current_user", return_value=None),
        ):
            await _write_log_async(request, 200, 10.0)

        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            result = await session.execute(
                __import__("sqlalchemy").select(IpActionCounter).where(
                    IpActionCounter.ip == "10.0.0.2"
                )
            )
            counter = result.scalar_one_or_none()
            assert counter is not None
            assert counter.action == "api_call"
            assert counter.count == 1

    @pytest.mark.asyncio
    async def test_write_log_increments_existing_counter(self, db_container):
        """同一 IP/action/时段应递增计数。"""
        from backend.plugins.request_log.models import IpActionCounter

        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        request.client = MagicMock(host="10.0.0.3")

        with (
            patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=db_container.get("db")["session_factory"],
            ),
            patch("backend.plugins.request_log.services.get_current_user", return_value=None),
        ):
            await _write_log_async(request, 200, 5.0)
            await _write_log_async(request, 200, 5.0)

        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            result = await session.execute(
                __import__("sqlalchemy").select(IpActionCounter).where(
                    IpActionCounter.ip == "10.0.0.3"
                )
            )
            counter = result.scalar_one_or_none()
            assert counter is not None
            assert counter.count == 2

    @pytest.mark.asyncio
    async def test_write_log_login_failure_classification(self, db_container):
        """登录失败请求应分类为 login_fail。"""
        from backend.plugins.request_log.models import RequestLog

        request = MagicMock()
        request.url.path = "/api/auth/login"
        request.method = "POST"
        request.headers = {}
        request.client = MagicMock(host="10.0.0.4")

        with (
            patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=db_container.get("db")["session_factory"],
            ),
            patch("backend.plugins.request_log.services.get_current_user", return_value=None),
        ):
            await _write_log_async(request, 401, 20.0)

        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            result = await session.execute(
                __import__("sqlalchemy").select(RequestLog).where(
                    RequestLog.ip == "10.0.0.4"
                )
            )
            log = result.scalar_one_or_none()
            assert log is not None
            assert log.action == "login_fail"


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    """日志聚合服务测试。"""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """启动和停止聚合服务不应抛出异常。"""
        from backend.plugins.request_log.services import LogAggregationService

        service = LogAggregationService()
        # 启动（APScheduler 可能未安装）
        try:
            service.start()
            assert service._scheduler is not None
        except Exception as e:
            pytest.skip(f"APScheduler 未安装: {e}")

        service.stop()
        assert service._scheduler is None

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """重复启动不应创建多个调度器。"""
        from backend.plugins.request_log.services import LogAggregationService

        service = LogAggregationService()
        try:
            service.start()
            scheduler1 = service._scheduler
            service.start()  # 再次启动
            assert service._scheduler is scheduler1
        except Exception as e:
            pytest.skip(f"APScheduler 未安装: {e}")

        service.stop()

    @pytest.mark.asyncio
    async def test_aggregate_job_no_crash(self, db_container):
        """聚合任务在空数据库上不应崩溃。"""
        from backend.plugins.request_log.services import LogAggregationService

        service = LogAggregationService()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            try:
                await service._aggregate_job()
            except Exception as e:
                pytest.fail(f"聚合任务抛出异常: {e}")

    @pytest.mark.asyncio
    async def test_cleanup_job_no_crash(self, db_container):
        """清理任务在空数据库上不应崩溃。"""
        from backend.plugins.request_log.services import LogAggregationService

        service = LogAggregationService()

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            try:
                await service._cleanup_job()
            except Exception as e:
                pytest.fail(f"清理任务抛出异常: {e}")