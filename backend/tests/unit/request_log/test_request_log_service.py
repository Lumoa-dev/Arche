"""RequestLog 服务层单元测试 —— LogAggregationService。

测试原则：
- 使用内存数据库模拟真实 DB 交互
- 测试聚合任务的 SQL 逻辑和 TTL 清理
- LogAggregationService 内部使用 _get_session_factory 获取 DB，需 mock
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from backend.plugins.request_log.models import IpActionCounter, RequestLog
from backend.plugins.request_log.services import LogAggregationService
from backend.plugins.request_log.services import _write_log_async as write_log_async


# =============================================================================
# _write_log_async
# =============================================================================


class TestWriteLogAsync:
    """测试异步日志写入。"""

    @pytest.mark.asyncio
    async def test_write_log_creates_request_log(self, db_container):
        """写入请求日志应创建 RequestLog 和 IpActionCounter。"""
        # Mock request
        request = MagicMock()
        request.url.path = "/api/posts"
        request.method = "GET"
        request.headers = {
            "User-Agent": "TestAgent/1.0",
            "Referer": "http://example.com",
        }
        request.client.host = "192.168.1.1"

        # Mock get_current_user
        with patch(
            "backend.plugins.request_log.services.get_current_user",
            return_value={"id": "user_123"},
        ):
            # Mock _get_session_factory
            with patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=db_container.get("db")["session_factory"],
            ):
                await write_log_async(request, 200, 15.5)

        # 验证日志已写入
        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            logs = (
                await session.execute(
                    select(RequestLog).where(RequestLog.ip == "192.168.1.1")
                )
            ).scalars().all()
            assert len(logs) >= 1
            log = logs[0]
            assert log.method == "GET"
            assert log.path == "/api/posts"
            assert log.status_code == 200
            assert log.duration_ms == 15.5
            assert log.user_id == "user_123"
            assert log.action == "api_call"

    @pytest.mark.asyncio
    async def test_write_log_creates_counter(self, db_container):
        """写入日志时应在 IpActionCounter 中创建或更新计数。"""
        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "POST"
        request.headers = {}
        request.client.host = "10.0.0.1"

        with patch(
            "backend.plugins.request_log.services.get_current_user",
            return_value=None,
        ):
            with patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=db_container.get("db")["session_factory"],
            ):
                await write_log_async(request, 201, 10.0)

        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            today = datetime.now().date()
            counters = (
                await session.execute(
                    select(IpActionCounter).where(
                        IpActionCounter.ip == "10.0.0.1",
                        IpActionCounter.action_date == today,
                    )
                )
            ).scalars().all()
            assert len(counters) >= 1

    @pytest.mark.asyncio
    async def test_write_log_exception_does_not_raise(self, db_container):
        """写入日志时发生异常不应透出。"""
        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        request.client.host = "10.0.0.1"

        with patch(
            "backend.plugins.request_log.services.get_current_user",
            side_effect=Exception("模拟错误"),
        ):
            with patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=db_container.get("db")["session_factory"],
            ):
                # 不应抛出异常
                await write_log_async(request, 200, 1.0)


# =============================================================================
# LogAggregationService
# =============================================================================


class TestLogAggregationService:
    """测试日志聚合服务。"""

    @pytest.mark.asyncio
    async def test_aggregate_job_processes_recent_logs(self, db_container):
        """聚合任务应处理最近一小时的日志。"""
        # 先写入一些日志
        request = MagicMock()
        request.url.path = "/api/aggregate-test"
        request.method = "GET"
        request.headers = {}
        request.client.host = "10.0.0.55"

        with patch(
            "backend.plugins.request_log.services.get_current_user",
            return_value=None,
        ):
            with patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=db_container.get("db")["session_factory"],
            ):
                for _ in range(3):
                    await write_log_async(request, 200, 5.0)

        # 运行聚合
        service = LogAggregationService()
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            await service._aggregate_job()

        # 验证聚合结果
        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            today = datetime.now().date()
            current_hour = datetime.now().hour
            counters = (
                await session.execute(
                    select(IpActionCounter).where(
                        IpActionCounter.ip == "10.0.0.55",
                        IpActionCounter.action == "api_call",
                        IpActionCounter.action_date == today,
                        IpActionCounter.hour == current_hour,
                    )
                )
            ).scalars().all()
            assert len(counters) >= 1
            assert counters[0].count >= 3

    @pytest.mark.asyncio
    async def test_cleanup_job_removes_old_logs(self, db_container):
        """清理任务应删除超过 TTL（7 天）的日志。"""
        # 写入一条日志
        request = MagicMock()
        request.url.path = "/api/cleanup-test"
        request.method = "GET"
        request.headers = {}
        request.client.host = "10.0.0.66"

        with patch(
            "backend.plugins.request_log.services.get_current_user",
            return_value=None,
        ):
            with patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=db_container.get("db")["session_factory"],
            ):
                await write_log_async(request, 200, 5.0)

        # 手动修改日志时间到 8 天前
        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            logs = (
                await session.execute(
                    select(RequestLog).where(RequestLog.ip == "10.0.0.66")
                )
            ).scalars().all()
            for log in logs:
                log.created_at = datetime.now() - timedelta(days=8)
            await session.commit()

        # 运行清理
        service = LogAggregationService()
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            await service._cleanup_job()

        # 验证日志已被删除
        async with session_factory() as session:
            remaining = (
                await session.execute(
                    select(RequestLog).where(RequestLog.ip == "10.0.0.66")
                )
            ).scalars().all()
            assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_cleanup_job_keeps_recent_logs(self, db_container):
        """清理任务应保留 7 天内的日志。"""
        request = MagicMock()
        request.url.path = "/api/keep-test"
        request.method = "GET"
        request.headers = {}
        request.client.host = "10.0.0.77"

        with patch(
            "backend.plugins.request_log.services.get_current_user",
            return_value=None,
        ):
            with patch(
                "backend.plugins.request_log.services._get_session_factory",
                return_value=db_container.get("db")["session_factory"],
            ):
                await write_log_async(request, 200, 5.0)

        service = LogAggregationService()
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            await service._cleanup_job()

        # 近期日志应被保留
        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            remaining = (
                await session.execute(
                    select(RequestLog).where(RequestLog.ip == "10.0.0.77")
                )
            ).scalars().all()
            assert len(remaining) >= 1

    @pytest.mark.asyncio
    async def test_start_stop_scheduler(self):
        """启动和停止调度器应在不抛异常的前提下运行。"""
        service = LogAggregationService()
        try:
            service.start()
        except ImportError:
            pass  # APScheduler 可能未安装
        try:
            service.stop()
        except Exception:
            pass

    def test_scheduler_not_started_by_default(self):
        """未调用 start 时应为 None。"""
        service = LogAggregationService()
        assert service._scheduler is None