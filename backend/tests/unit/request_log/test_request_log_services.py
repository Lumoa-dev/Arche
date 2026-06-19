"""请求日志服务行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现
- classify_action 和 _get_client_ip 是纯函数，可直接测试
- _write_log_async 和 LogAggregationService 需要内存数据库
- 每个测试独立，不依赖执行顺序
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
# classify_action 单元测试（纯函数）
# =============================================================================


class TestClassifyAction:
    """测试请求行为分类逻辑。"""

    @pytest.mark.parametrize(
        "method, path, status_code, expected",
        [
            # 登录失败
            ("POST", "/api/auth/login", 401, "login_fail"),
            ("POST", "/api/auth/login", 400, "login_fail"),
            ("POST", "/api/auth/login", 403, "login_fail"),
            # 登录成功
            ("POST", "/api/auth/login", 200, "api_call"),
            # API 调用
            ("GET", "/api/blog/posts", 200, "api_call"),
            ("POST", "/api/admin/users", 201, "api_call"),
            ("DELETE", "/api/ip_ban/1", 204, "api_call"),
            # 页面浏览
            ("GET", "/about", 200, "page_view"),
            ("GET", "/", 200, "page_view"),
            ("GET", "/home", 200, "page_view"),
            # 其他
            ("POST", "/webhook/github", 200, "other"),
            ("PUT", "/callback", 200, "other"),
        ],
    )
    def test_classify_action(self, method, path, status_code, expected):
        assert classify_action(method, path, status_code) == expected


# =============================================================================
# _get_client_ip 单元测试
# =============================================================================


class TestGetClientIp:
    """测试客户端 IP 提取逻辑。

    优先级: X-Forwarded-For > X-Real-IP > request.client.host
    """

    def test_x_forwarded_for_takes_priority(self):
        """X-Forwarded-For 应优先于其他来源。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
        request.client = MagicMock(host="192.168.1.1")

        ip = _get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_x_real_ip_when_no_forwarded(self):
        """没有 X-Forwarded-For 时应使用 X-Real-IP。"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "203.0.113.5"}
        request.client = MagicMock(host="192.168.1.1")

        ip = _get_client_ip(request)
        assert ip == "203.0.113.5"

    def test_client_host_fallback(self):
        """没有代理头时应回退到 client.host。"""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="192.168.1.100")

        ip = _get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_empty_when_no_source(self):
        """没有任何来源时应返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None

        ip = _get_client_ip(request)
        assert ip == ""

    def test_forwarded_for_takes_first_ip(self):
        """X-Forwarded-For 应取第一个 IP。"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1, 172.16.0.1"}
        request.client = MagicMock(host="10.0.0.1")

        ip = _get_client_ip(request)
        assert ip == "10.0.0.1"


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    """测试日志聚合服务。"""

    @pytest.mark.asyncio
    async def test_start_creates_scheduler(self):
        """启动服务应创建 APScheduler 实例。"""
        service = LogAggregationService()
        service.start()
        assert service._scheduler is not None
        assert service._scheduler.running is True
        service.stop()

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """重复启动不应创建多个调度器。"""
        service = LogAggregationService()
        service.start()
        scheduler_id = id(service._scheduler)
        service.start()  # 再次启动
        assert id(service._scheduler) == scheduler_id
        service.stop()

    @pytest.mark.asyncio
    async def test_stop_shuts_down_scheduler(self):
        """停止服务应关闭调度器。"""
        service = LogAggregationService()
        service.start()
        service.stop()
        assert service._scheduler is None

    def test_stop_when_not_started(self):
        """未启动时停止不应报错。"""
        service = LogAggregationService()
        service.stop()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_aggregate_job_runs_without_error(self, db_container):
        """聚合任务在正常环境下运行不应抛出异常。"""
        service = LogAggregationService()
        # 使用 db_container 确保数据库可用
        try:
            await service._aggregate_job()
        except Exception as e:
            pytest.fail(f"聚合任务抛出了意外异常: {e}")

    @pytest.mark.asyncio
    async def test_cleanup_job_runs_without_error(self, db_container):
        """TTL 清理任务在正常环境下运行不应抛出异常。"""
        service = LogAggregationService()
        try:
            await service._cleanup_job()
        except Exception as e:
            pytest.fail(f"清理任务抛出了意外异常: {e}")


# =============================================================================
# _write_log_async 测试（需要模拟 FastAPI Request）
# =============================================================================


class TestWriteLogAsync:
    """测试异步日志写入。"""

    @pytest.mark.asyncio
    async def test_write_log_success(self, db_container):
        """写入请求日志应成功写入数据库。"""
        from unittest.mock import MagicMock

        from backend.plugins.request_log.models import RequestLog

        # 模拟 request 对象
        request = MagicMock()
        request.url.path = "/api/blog/posts"
        request.method = "GET"
        request.headers = {
            "User-Agent": "TestAgent/1.0",
            "Referer": "https://example.com",
        }
        request.client = MagicMock(host="10.0.0.1")

        # 注入 db_container 的 session_factory
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            from backend.plugins.request_log.services import _write_log_async

            # 模拟 get_current_user 返回 None
            with patch(
                "backend.plugins.request_log.services.get_current_user",
                return_value=None,
            ):
                await _write_log_async(request, 200, 15.5)

            # 验证日志已写入
            async with db_container.get("db")["session_factory"]() as session:
                from sqlalchemy import func, select

                result = await session.execute(select(func.count(RequestLog.id)))
                count = result.scalar_one()
                assert count >= 1

    @pytest.mark.asyncio
    async def test_write_log_with_user_id(self, db_container):
        """写入日志时如果存在用户信息应记录 user_id。"""
        from unittest.mock import MagicMock

        from backend.plugins.request_log.models import RequestLog

        request = MagicMock()
        request.url.path = "/api/auth/login"
        request.method = "POST"
        request.headers = {
            "User-Agent": "TestAgent/1.0",
            "Referer": "",
        }
        request.client = MagicMock(host="10.0.0.2")

        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            from backend.plugins.request_log.services import _write_log_async

            with patch(
                "backend.plugins.request_log.services.get_current_user",
                return_value={"id": "user-123"},
            ):
                await _write_log_async(request, 401, 5.0)

            # 验证
            async with db_container.get("db")["session_factory"]() as session:
                from sqlalchemy import select

                result = await session.execute(
                    select(RequestLog).where(RequestLog.user_id == "user-123")
                )
                log = result.scalar_one_or_none()
                assert log is not None
                assert log.user_id == "user-123"
                assert log.action == "login_fail"
