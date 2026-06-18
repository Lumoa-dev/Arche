"""请求日志插件 —— 服务层单元测试。

使用真实内存数据库测试 RequestLog 模型的写入、查询和路由逻辑。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from backend.plugins.request_log.models import IpActionCounter, RequestLog
from backend.plugins.request_log.services import (
    _write_log_async,
    classify_action,
)


@pytest.fixture
def log_container(db_container):
    """基于 db_container 的请求日志测试环境。"""
    return db_container


# =============================================================================
# RequestLog 模型写入测试
# =============================================================================


@pytest.mark.asyncio
class TestRequestLogWrite:
    async def _mock_request(self, method="GET", path="/api/test", headers=None,
                            status_code=200, user=None, client_ip="10.0.0.1"):
        """创建模拟请求对象。"""
        from unittest.mock import AsyncMock, MagicMock

        request = MagicMock()
        request.method = method
        request.url.path = path
        request.headers = headers or {}
        request.client = MagicMock()
        request.client.host = client_ip

        # mock state.user
        if user:
            request.state.user = user
        else:
            request.state = MagicMock()
            request.state.user = None

        return request

    async def test_write_log_creates_entry(self, log_container, monkeypatch):
        """_write_log_async 应创建 RequestLog 记录。"""
        # 替换 _get_session_factory 返回测试容器的 session_factory
        async def mock_get_session_factory():
            return log_container.get("db")["session_factory"]

        monkeypatch.setattr(
            "backend.plugins.request_log.services._get_session_factory",
            lambda: log_container.get("db")["session_factory"],
        )

        request = await self._mock_request(
            method="POST",
            path="/api/auth/login",
            status_code=200,
        )
        await _write_log_async(request, 200, 100.5)

        # 验证写入
        session_factory = log_container.get("db")["session_factory"]
        async with session_factory() as session:
            result = await session.execute(select(RequestLog))
            logs = result.scalars().all()

        assert len(logs) == 1
        assert logs[0].method == "POST"
        assert logs[0].path == "/api/auth/login"
        assert logs[0].status_code == 200
        assert logs[0].duration_ms == 100.5
        assert logs[0].action == "api_call"

    async def test_write_log_creates_counter(self, log_container, monkeypatch):
        """_write_log_async 应创建/更新 IpActionCounter。"""
        monkeypatch.setattr(
            "backend.plugins.request_log.services._get_session_factory",
            lambda: log_container.get("db")["session_factory"],
        )

        request = await self._mock_request(method="GET", path="/api/items")
        await _write_log_async(request, 200, 50.0)
        await _write_log_async(request, 200, 50.0)

        session_factory = log_container.get("db")["session_factory"]
        async with session_factory() as session:
            result = await session.execute(
                select(IpActionCounter).where(
                    IpActionCounter.action == "api_call",
                )
            )
            counters = result.scalars().all()

        assert len(counters) == 1
        assert counters[0].count == 2

    async def test_write_log_login_failure(self, log_container, monkeypatch):
        """登录失败应记录为 login_fail。"""
        monkeypatch.setattr(
            "backend.plugins.request_log.services._get_session_factory",
            lambda: log_container.get("db")["session_factory"],
        )

        request = await self._mock_request(
            method="POST", path="/api/auth/login", status_code=401,
        )
        await _write_log_async(request, 401, 30.0)

        session_factory = log_container.get("db")["session_factory"]
        async with session_factory() as session:
            result = await session.execute(select(RequestLog))
            log = result.scalars().first()

        assert log.action == "login_fail"

    async def test_write_log_with_user_id(self, log_container, monkeypatch):
        """已登录用户的请求应记录 user_id。"""
        monkeypatch.setattr(
            "backend.plugins.request_log.services._get_session_factory",
            lambda: log_container.get("db")["session_factory"],
        )

        user = {"id": "user-123", "username": "testuser"}
        request = await self._mock_request(user=user)
        await _write_log_async(request, 200, 15.0)

        session_factory = log_container.get("db")["session_factory"]
        async with session_factory() as session:
            result = await session.execute(select(RequestLog))
            log = result.scalars().first()

        assert log.user_id == "user-123"

    async def test_write_log_exception_caught(self, log_container, monkeypatch):
        """异常不应传播（被 try/except 捕获）。"""
        def broken_factory():
            raise RuntimeError("DB unavailable")

        monkeypatch.setattr(
            "backend.plugins.request_log.services._get_session_factory",
            broken_factory,
        )

        request = await self._mock_request()
        # 不应抛出异常
        await _write_log_async(request, 200, 10.0)
        # 成功到达说明异常被吞掉了


# =============================================================================
# IpActionCounter 模型测试
# =============================================================================


@pytest.mark.asyncio
class TestIpActionCounter:
    async def test_unique_constraint_enforced(self, module_db):
        """唯一约束 (ip, action, action_date, hour) 应生效。"""
        from sqlalchemy.ext.asyncio import async_sessionmaker

        session_factory = async_sessionmaker(module_db["engine"], expire_on_commit=False)
        today = datetime.now().date()
        now = datetime.now()

        async with session_factory() as session:
            session.add(
                IpActionCounter(
                    ip="10.0.0.1",
                    action="api_call",
                    action_date=today,
                    hour=now.hour,
                    count=1,
                )
            )
            await session.commit()

        # 重复插入应失败
        from sqlalchemy.exc import IntegrityError

        async with session_factory() as session:
            session.add(
                IpActionCounter(
                    ip="10.0.0.1",
                    action="api_call",
                    action_date=today,
                    hour=now.hour,
                    count=1,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()

    async def test_multiple_actions_same_ip(self, module_db):
        """同一 IP 的不同 action 应分别计数。"""
        from sqlalchemy.ext.asyncio import async_sessionmaker

        session_factory = async_sessionmaker(module_db["engine"], expire_on_commit=False)
        today = datetime.now().date()
        now = datetime.now()

        async with session_factory() as session:
            session.add_all([
                IpActionCounter(ip="10.0.0.1", action="api_call",
                                action_date=today, hour=now.hour, count=5),
                IpActionCounter(ip="10.0.0.1", action="page_view",
                                action_date=today, hour=now.hour, count=3),
            ])
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(
                select(IpActionCounter).where(IpActionCounter.ip == "10.0.0.1")
            )
            counters = result.scalars().all()

        assert len(counters) == 2
        assert {c.action for c in counters} == {"api_call", "page_view"}