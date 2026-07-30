"""IP 封禁服务单元测试 —— 覆盖核心业务逻辑及自动封禁规则引擎。"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


class TestIpMatchesCidr:
    """ip_matches_cidr 纯函数测试 —— 覆盖 IPv4/IPv6 及边界情况。"""

    def test_ipv4_exact_match(self):
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv6_match(self):
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_invalid_ip_returns_false(self):
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_empty_string_returns_false(self):
        assert ip_matches_cidr("", "192.168.1.0/24") is False


class TestIpBanService:
    """IpBanService 核心业务逻辑测试 —— 使用 mock 数据库。"""

    @pytest.fixture
    def container(self):
        c = MagicMock()
        c.get.return_value = {"session_factory": MagicMock()}
        return c

    @pytest.fixture
    def service(self, container):
        return IpBanService(container)

    # ── _ban_to_dict ──

    def test_ban_to_dict(self, service):
        ban = MagicMock()
        ban.id = 1
        ban.ip_or_cidr = "192.168.1.1"
        ban.ban_type = "manual"
        ban.reason = "test"
        ban.rule_id = None
        ban.banned_by = "admin"
        ban.created_at = None
        ban.expires_at = None
        ban.is_active = True

        d = service._ban_to_dict(ban)
        assert d["id"] == 1
        assert d["ip_or_cidr"] == "192.168.1.1"
        assert d["ban_type"] == "manual"
        assert d["is_active"] is True

    # ── _cleanup_counters ──

    def test_cleanup_counters_removes_expired(self, service):
        import time
        service._counters["test:1.1.1.1"] = [(time.time() - 4000, 200)]
        service._cleanup_counters()
        assert "test:1.1.1.1" not in service._counters

    def test_cleanup_counters_keeps_recent(self, service):
        import time
        service._counters["test:1.1.1.1"] = [(time.time() - 10, 200)]
        service._cleanup_counters()
        assert "test:1.1.1.1" in service._counters

    # ── _get_default_rules ──

    def test_get_default_rules_contains_all_rules(self, service):
        rules = service._get_default_rules()
        assert "login_failure" in rules
        assert "high_4xx" in rules
        assert "rate_limit" in rules
        assert "geo_surge" in rules
        assert rules["login_failure"]["threshold"] == 10
        assert rules["rate_limit"]["window_seconds"] == 60

    # ── record_event 路由逻辑 ──

    @pytest.mark.asyncio
    async def test_record_event_login_failure_triggers_check(self, service):
        service._check_login_failure_rule = AsyncMock()
        await service.record_event("login_failure", "1.1.1.1")
        service._check_login_failure_rule.assert_awaited_once_with("1.1.1.1")

    @pytest.mark.asyncio
    async def test_record_event_high_4xx_triggers_check(self, service):
        service._check_high_4xx_rule = AsyncMock()
        await service.record_event("high_4xx", "1.1.1.1", status_code=403)
        service._check_high_4xx_rule.assert_awaited_once_with("1.1.1.1")

    @pytest.mark.asyncio
    async def test_record_event_rate_limit_triggers_check(self, service):
        service._check_rate_limit_rule = AsyncMock()
        await service.record_event("rate_limit", "1.1.1.1")
        service._check_rate_limit_rule.assert_awaited_once_with("1.1.1.1")

    @pytest.mark.asyncio
    async def test_record_event_unknown_type_no_check(self, service):
        service._check_login_failure_rule = AsyncMock()
        service._check_high_4xx_rule = AsyncMock()
        service._check_rate_limit_rule = AsyncMock()
        await service.record_event("unknown", "1.1.1.1")
        service._check_login_failure_rule.assert_not_awaited()
        service._check_high_4xx_rule.assert_not_awaited()
        service._check_rate_limit_rule.assert_not_awaited()

    # ── 自动封禁规则检查：规则禁用时不触发封禁 ──

    @pytest.mark.asyncio
    async def test_check_login_failure_rule_disabled(self, service):
        service.get_rule_configs = AsyncMock(return_value=[
            {"id": "login_failure", "enabled": False, "threshold": 10, "window_seconds": 300, "ban_duration_minutes": 30}
        ])
        service.ban_ip = AsyncMock()
        await service._check_login_failure_rule("1.1.1.1")
        service.ban_ip.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_check_login_failure_rule_below_threshold(self, service):
        service.get_rule_configs = AsyncMock(return_value=[
            {"id": "login_failure", "enabled": True, "threshold": 10, "window_seconds": 300, "ban_duration_minutes": 30}
        ])
        service.ban_ip = AsyncMock()
        service._counters["login_failure:1.1.1.1"] = [(0, 0)]  # 1 count < 10
        await service._check_login_failure_rule("1.1.1.1")
        service.ban_ip.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_check_login_failure_rule_triggers_ban(self, service):
        import time
        now = time.time()
        service.get_rule_configs = AsyncMock(return_value=[
            {"id": "login_failure", "enabled": True, "threshold": 3, "window_seconds": 300, "ban_duration_minutes": 30}
        ])
        service.ban_ip = AsyncMock()
        service._counters["login_failure:1.1.1.1"] = [(now - 10, 0)] * 5
        await service._check_login_failure_rule("1.1.1.1")
        service.ban_ip.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_high_4xx_rule_only_counts_4xx(self, service):
        import time
        now = time.time()
        service.get_rule_configs = AsyncMock(return_value=[
            {"id": "high_4xx", "enabled": True, "threshold": 3, "window_seconds": 3600, "ban_duration_minutes": 60}
        ])
        service.ban_ip = AsyncMock()
        # 2 次 4xx + 2 次 200 = 仅 2 次 4xx < 3
        service._counters["high_4xx:1.1.1.1"] = [(now - 10, 403), (now - 20, 404), (now - 30, 200), (now - 40, 200)]
        await service._check_high_4xx_rule("1.1.1.1")
        service.ban_ip.assert_not_awaited()

    # ── _send_webhook_notification ──

    @pytest.mark.asyncio
    async def test_send_webhook_no_url_skips(self, service):
        service._webhook_url = ""
        # 不会抛出异常
        await service._send_webhook_notification("test", {})

    @pytest.mark.asyncio
    async def test_ban_ip_existing_updates(self, service):
        """重复封禁同 IP 时更新已有记录而非新建。"""
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import StaticPool
        from backend.core.db import Base
        from backend.plugins.ip_ban import models as _m  # noqa: F401

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        container = MagicMock()
        container.get.side_effect = lambda name: (
            {"session_factory": session_factory} if name == "db"
            else {"IP_BAN_WEBHOOK_URL": ""} if name == "config"
            else MagicMock()
        )
        svc = IpBanService(container)
        svc._send_webhook_notification = AsyncMock()

        # 首次封禁
        r1 = await svc.ban_ip("10.0.0.1", reason="test", banned_by="admin")
        assert r1["is_active"] is True
        assert r1["ip_or_cidr"] == "10.0.0.1"

        # 再次封禁同一 IP —— 应更新原记录
        r2 = await svc.ban_ip("10.0.0.1", reason="updated", duration_minutes=60)
        assert r2["id"] == r1["id"]
        assert r2["reason"] == "updated"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_unban_ip_not_found(self, service):
        """解封不存在的记录应抛出 AppError。"""
        from backend.core.middleware import AppError
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import StaticPool
        from backend.core.db import Base
        from backend.plugins.ip_ban import models as _m  # noqa: F401

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        container = MagicMock()
        container.get.side_effect = lambda name: (
            {"session_factory": session_factory} if name == "db" else MagicMock()
        )
        svc = IpBanService(container)
        svc._send_webhook_notification = AsyncMock()

        with pytest.raises(AppError) as exc:
            await svc.unban_ip(9999)
        assert exc.value.status_code == 404

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_batch_unban_partial(self, service):
        """批量解封时，仅解封活跃的记录。"""
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import StaticPool
        from backend.core.db import Base
        from backend.plugins.ip_ban import models as _m  # noqa: F401

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        container = MagicMock()
        container.get.side_effect = lambda name: (
            {"session_factory": session_factory} if name == "db"
            else {"IP_BAN_WEBHOOK_URL": ""} if name == "config"
            else MagicMock()
        )
        svc = IpBanService(container)
        svc._send_webhook_notification = AsyncMock()

        # 创建 2 条封禁
        b1 = await svc.ban_ip("10.0.0.1", reason="test")
        b2 = await svc.ban_ip("10.0.0.2", reason="test")

        # 解封其中一条
        await svc.unban_ip(b1["id"], operator="admin")

        # 批量解封两条
        count = await svc.batch_unban([b1["id"], b2["id"]], operator="admin")
        assert count == 1  # 仅 b2 是活跃的

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_get_stats(self, service):
        """get_stats 返回正确的统计汇总。"""
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import StaticPool
        from backend.core.db import Base
        from backend.plugins.ip_ban import models as _m  # noqa: F401

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        container = MagicMock()
        container.get.side_effect = lambda name: (
            {"session_factory": session_factory} if name == "db"
            else {"IP_BAN_WEBHOOK_URL": ""} if name == "config"
            else MagicMock()
        )
        svc = IpBanService(container)
        svc._send_webhook_notification = AsyncMock()

        await svc.ban_ip("10.0.0.1", reason="auto", ban_type="auto")
        await svc.ban_ip("10.0.0.2", reason="manual", ban_type="manual")

        stats = await svc.get_stats()
        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 2
        assert stats["auto_bans"] == 1
        assert stats["manual_bans"] == 1

        await engine.dispose()