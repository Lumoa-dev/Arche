"""请求日志插件 单元测试。

测试 classify_action、_get_client_ip、_write_log_async 等核心函数，
以及 LogAggregationService 的定时任务逻辑。
所有测试使用纯 mock，不启动真实数据库。
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from backend.plugins.request_log.services import (
    LogAggregationService,
    _get_client_ip,
    _get_session_factory,
    classify_action,
)


class TestClassifyAction:
    """行为分类函数测试。"""

    def test_login_fail_when_login_path_with_4xx(self):
        """登录路径且状态码 >= 400 应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_fail_not_for_successful_login(self):
        """登录成功不应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) != "login_fail"

    def test_api_call_for_api_paths(self):
        """以 /api/ 开头的路径应返回 api_call。"""
        assert classify_action("GET", "/api/posts", 200) == "api_call"
        assert classify_action("POST", "/api/auth/register", 201) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_page_view_for_get_non_api(self):
        """GET 请求且非 /api/ 路径应返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"

    def test_other_for_non_get_non_api(self):
        """非 GET 请求且非 /api/ 路径应返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/profile", 200) == "other"


class TestGetClientIp:
    """客户端 IP 提取函数测试。"""

    def test_x_forwarded_for_takes_priority(self):
        """X-Forwarded-For 应优先于 X-Real-IP 和 client.host。"""
        scope = {
            "type": "http",
            "headers": [
                (b"x-forwarded-for", b"203.0.113.1, 198.51.100.2"),
                (b"x-real-ip", b"10.0.0.1"),
            ],
        }
        request = Request(scope)
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip_fallback(self):
        """无 X-Forwarded-For 时应回退到 X-Real-IP。"""
        scope = {
            "type": "http",
            "headers": [(b"x-real-ip", b"10.0.0.1")],
        }
        request = Request(scope)
        assert _get_client_ip(request) == "10.0.0.1"

    def test_remote_addr_fallback(self):
        """无代理头时应回退到 client.host。"""
        scope = {
            "type": "http",
            "headers": [],
            "client": ("192.168.1.1", 54321),
        }
        request = Request(scope)
        assert _get_client_ip(request) == "192.168.1.1"

    def test_empty_when_no_source(self):
        """没有任何可用 IP 源时应返回空字符串。"""
        scope = {"type": "http", "headers": []}
        request = Request(scope)
        assert _get_client_ip(request) == ""


class TestGetSessionFactory:
    """会话工厂获取函数测试。"""

    async def test_returns_none_when_db_not_available(self, monkeypatch):
        """数据库未初始化时应返回 None。"""
        mock_container = MagicMock()
        mock_container.get.return_value = None
        monkeypatch.setattr(
            "backend.core.container.container",
            mock_container,
        )
        assert _get_session_factory() is None

    async def test_returns_factory_on_success(self, monkeypatch):
        """正常时应返回 session_factory。"""
        mock_factory = MagicMock()
        mock_container = MagicMock()
        mock_container.get.return_value = {"session_factory": mock_factory}
        monkeypatch.setattr(
            "backend.core.container.container",
            mock_container,
        )
        assert _get_session_factory() == mock_factory


class TestLogAggregationService:
    """定时聚合服务测试。"""

    async def test_start_stop_lifecycle(self):
        """start 和 stop 应正确管理调度器生命周期。"""
        svc = LogAggregationService()
        assert svc._scheduler is None

        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler_cls:
            mock_scheduler = MagicMock()
            mock_scheduler.running = True
            mock_scheduler_cls.return_value = mock_scheduler

            svc.start()
            assert svc._scheduler is not None
            assert mock_scheduler.add_job.call_count == 2  # aggregate + cleanup

            svc.stop()
            assert svc._scheduler is None
            mock_scheduler.shutdown.assert_called_once_with(wait=False)

    async def test_start_idempotent(self):
        """多次调用 start 不应重复创建调度器。"""
        svc = LogAggregationService()
        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler_cls:
            mock_scheduler = MagicMock()
            mock_scheduler_cls.return_value = mock_scheduler

            svc.start()
            scheduler1 = svc._scheduler
            svc.start()  # 第二次调用
            assert svc._scheduler is scheduler1
            assert mock_scheduler.add_job.call_count == 2

    async def test_stop_does_not_crash_when_not_started(self):
        """未启动时调用 stop 不应报错。"""
        svc = LogAggregationService()
        svc.stop()  # 不应抛出异常

    async def test_aggregate_job_handles_empty_result(self, monkeypatch):
        """聚合任务在没有数据时不应报错。"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(
            "backend.plugins.request_log.services._get_session_factory",
            lambda: mock_factory,
        )

        svc = LogAggregationService()
        await svc._aggregate_job()  # 不应抛出异常

    async def test_cleanup_job_handles_empty_result(self, monkeypatch):
        """清理任务在没有数据时不应报错。"""
        mock_session = AsyncMock()
        # 第一次 count 查询返回 0
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        # 第二次 delete 不需要特殊结果
        mock_session.execute.return_value = mock_count_result
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(
            "backend.plugins.request_log.services._get_session_factory",
            lambda: mock_factory,
        )

        svc = LogAggregationService()
        await svc._cleanup_job()  # 不应抛出异常

    async def test_start_handles_missing_apscheduler(self):
        """APScheduler 未安装时 start 不应报错。"""
        with patch.dict(
            "sys.modules", {"apscheduler.schedulers.asyncio": None}
        ):
            svc = LogAggregationService()
            svc.start()  # 不应抛出异常
            assert svc._scheduler is None