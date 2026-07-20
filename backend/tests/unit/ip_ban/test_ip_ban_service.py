"""IpBanService 测试 —— 封禁管理、CIDR 匹配、自动封禁规则引擎。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# CIDR 匹配工具函数测试
# =============================================================================


class TestIpMatchesCidr:
    """测试 IP / CIDR 匹配逻辑。"""

    def test_ipv4_exact_match(self):
        """精确匹配 IPv4 地址。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IPv4 在子网内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IPv4 不在子网内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv6_match(self):
        """IPv6 地址匹配。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_ipv6_no_match(self):
        """IPv6 地址不匹配。"""
        assert (
            ip_matches_cidr("2001:db9::1", "2001:db8::/32") is False
        )

    def test_invalid_ip_returns_false(self):
        """无效 IP 返回 False 不抛异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 返回 False 不抛异常。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_cidr_without_prefix(self):
        """不带掩码的 CIDR 视作 /32。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1") is True


# =============================================================================
# IpBanService 单元测试
# =============================================================================


@pytest.fixture
def ban_service(in_memory_db):
    """创建带内存数据库的 IpBanService 实例。"""
    container = MagicMock()
    container.get.side_effect = lambda name: {
        "db": in_memory_db,
        "config": MagicMock(
            get=lambda key, default=None: (
                "https://hooks.example.com/webhook" if key == "IP_BAN_WEBHOOK_URL" else default
            )
        ),
    }.get(name)
    return IpBanService(container)


@pytest.mark.asyncio
class TestBanOperations:
    """测试封禁/解封核心操作。"""

    async def test_ban_ip_creates_ban_record(self, ban_service):
        """封禁 IP 后应创建封禁记录和日志。"""
        result = await ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="恶意扫描",
            ban_type="manual",
            banned_by="admin",
        )
        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["reason"] == "恶意扫描"

    async def test_ban_ip_with_expiry(self, ban_service):
        """封禁时可设置过期时间。"""
        result = await ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            duration_minutes=30,
        )
        assert result["expires_at"] is not None

    async def test_ban_ip_without_expiry_is_permanent(self, ban_service):
        """不设过期时间为永久封禁。"""
        result = await ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="永久封禁",
        )
        assert result["expires_at"] is None

    async def test_ban_ip_duplicate_updates_existing(self, ban_service):
        """重复封禁同一 IP 应更新已有记录。"""
        await ban_service.ban_ip(ip_or_cidr="10.0.0.3", reason="首次")
        result = await ban_service.ban_ip(
            ip_or_cidr="10.0.0.3", reason="更新原因", duration_minutes=60
        )
        assert result["reason"] == "更新原因"

    async def test_unban_ip_marks_inactive(self, ban_service):
        """解封后 is_active 应为 False。"""
        ban = await ban_service.ban_ip(ip_or_cidr="10.0.0.4", reason="测试")
        result = await ban_service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

    async def test_unban_nonexistent_raises(self, ban_service):
        """解封不存在的记录应抛异常。"""
        with pytest.raises(AppError) as exc:
            await ban_service.unban_ip(ban_id=99999, operator="admin")
        assert exc.value.status_code == 404

    async def test_batch_unban(self, ban_service):
        """批量解封应返回解封数量。"""
        b1 = await ban_service.ban_ip(ip_or_cidr="10.0.0.5", reason="测试")
        b2 = await ban_service.ban_ip(ip_or_cidr="10.0.0.6", reason="测试")
        count = await ban_service.batch_unban(
            ban_ids=[b1["id"], b2["id"]], operator="admin"
        )
        assert count == 2

    async def test_is_ip_banned_returns_true(self, ban_service):
        """被封禁的 IP 应被检测到。"""
        await ban_service.ban_ip(ip_or_cidr="10.0.0.7", reason="测试")
        assert await ban_service.is_ip_banned("10.0.0.7") is True

    async def test_is_ip_banned_returns_false_for_unknown(self, ban_service):
        """未封禁的 IP 返回 False。"""
        assert await ban_service.is_ip_banned("10.0.0.99") is False

    async def test_is_ip_banned_with_cidr(self, ban_service):
        """CIDR 封禁的段内 IP 应被检测到。"""
        await ban_service.ban_ip(ip_or_cidr="192.168.2.0/24", reason="段封禁")
        assert await ban_service.is_ip_banned("192.168.2.50") is True
        assert await ban_service.is_ip_banned("192.168.3.1") is False

    async def test_expired_ban_not_active(self, ban_service):
        """过期的封禁记录不应被视为活跃。"""
        await ban_service.ban_ip(
            ip_or_cidr="10.0.0.8",
            reason="短封禁",
            duration_minutes=0,  # 立即过期
        )
        # 手动将封禁记录的 expires_at 设为过去
        from backend.plugins.ip_ban.models import IpBan
        from sqlalchemy import select

        async with ban_service.session_factory() as session:
            result = await session.execute(
                select(IpBan).where(IpBan.ip_or_cidr == "10.0.0.8")
            )
            ban = result.scalar_one()
            ban.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            ban.is_active = True
            await session.commit()

        assert await ban_service.is_ip_banned("10.0.0.8") is False

    async def test_list_bans_pagination(self, ban_service):
        """分页查询封禁列表。"""
        for i in range(5):
            await ban_service.ban_ip(ip_or_cidr=f"10.0.0.{i+10}", reason="测试")
        result = await ban_service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    async def test_list_bans_with_keyword(self, ban_service):
        """按关键词搜索封禁列表。"""
        await ban_service.ban_ip(ip_or_cidr="10.0.0.20", reason="test")
        await ban_service.ban_ip(ip_or_cidr="10.0.0.30", reason="test")
        result = await ban_service.list_bans(keyword="10.0.0.20")
        assert result["total"] == 1

    async def test_get_ban_logs(self, ban_service):
        """封禁后应有操作日志。"""
        await ban_service.ban_ip(ip_or_cidr="10.0.0.50", reason="test")
        logs = await ban_service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] >= 1
        assert logs["list"][0]["action"] == "ban"

    async def test_get_stats(self, ban_service):
        """封禁统计应返回正确计数。"""
        stats = await ban_service.get_stats()
        assert "total_bans" in stats
        assert "active_bans" in stats
        assert "auto_bans" in stats
        assert "manual_bans" in stats
        assert "today_bans" in stats


@pytest.mark.asyncio
class TestAutoBanRuleEngine:
    """测试自动封禁规则引擎。"""

    async def test_get_rule_configs_returns_defaults(self, ban_service):
        """未配置时返回默认规则。"""
        rules = await ban_service.get_rule_configs()
        assert len(rules) >= 4
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    async def test_record_event_login_failure_triggers_ban(self, ban_service, monkeypatch):
        """登录失败超过阈值触发自动封禁。"""
        # 模拟 _check_login_failure_rule 能独立测试
        triggered = []

        async def mock_ban(*args, **kwargs):
            triggered.append(kwargs.get("ip_or_cidr"))

        monkeypatch.setattr(ban_service, "ban_ip", mock_ban)

        # 模拟计数器累积到阈值
        from backend.plugins.ip_ban.models import AutoBanRuleConfig
        async with ban_service.session_factory() as session:
            rule = AutoBanRuleConfig(
                id="login_failure",
                name="登录失败封禁",
                enabled=True,
                threshold=3,
                window_seconds=60,
                ban_duration_minutes=30,
            )
            session.add(rule)
            await session.commit()

        # 触发 3 次登录失败事件
        for _ in range(3):
            await ban_service.record_event("login_failure", "10.0.0.100")

        await ban_service._check_login_failure_rule("10.0.0.100")
        assert "10.0.0.100" in triggered

    async def test_record_event_rate_limit_triggers_ban(self, ban_service, monkeypatch):
        """请求频率超过阈值触发自动封禁。"""
        triggered = []

        async def mock_ban(*args, **kwargs):
            triggered.append(kwargs.get("ip_or_cidr"))

        monkeypatch.setattr(ban_service, "ban_ip", mock_ban)

        from backend.plugins.ip_ban.models import AutoBanRuleConfig
        async with ban_service.session_factory() as session:
            rule = AutoBanRuleConfig(
                id="rate_limit",
                name="请求频率封禁",
                enabled=True,
                threshold=3,
                window_seconds=60,
                ban_duration_minutes=10,
            )
            session.add(rule)
            await session.commit()

        for _ in range(3):
            await ban_service.record_event("rate_limit", "10.0.0.101")

        await ban_service._check_rate_limit_rule("10.0.0.101")
        assert "10.0.0.101" in triggered

    async def test_auto_ban_disabled_rule_does_not_trigger(self, ban_service, monkeypatch):
        """禁用的规则不应触发封禁。"""
        triggered = []

        async def mock_ban(*args, **kwargs):
            triggered.append(kwargs.get("ip_or_cidr"))

        monkeypatch.setattr(ban_service, "ban_ip", mock_ban)

        from backend.plugins.ip_ban.models import AutoBanRuleConfig
        async with ban_service.session_factory() as session:
            rule = AutoBanRuleConfig(
                id="login_failure",
                name="登录失败封禁",
                enabled=False,
                threshold=1,
                window_seconds=60,
                ban_duration_minutes=30,
            )
            session.add(rule)
            await session.commit()

        await ban_service.record_event("login_failure", "10.0.0.102")
        assert not triggered  # 不应触发封禁

    async def test_update_rule_config(self, ban_service):
        """更新规则配置应生效。"""
        # 先获取默认规则
        rules = await ban_service.get_rule_configs()
        rule_id = "login_failure"

        updated = await ban_service.update_rule_config(
            rule_id, {"threshold": 20, "enabled": False}
        )
        assert updated["threshold"] == 20
        assert updated["enabled"] is False

    async def test_update_nonexistent_rule_raises(self, ban_service):
        """更新不存在的规则应抛异常。"""
        with pytest.raises(AppError) as exc:
            await ban_service.update_rule_config("nonexistent", {"enabled": True})
        assert exc.value.status_code == 404

    async def test_get_active_ip_ranges(self, ban_service):
        """获取活跃的 IP/CIDR 段列表。"""
        await ban_service.ban_ip(ip_or_cidr="10.0.0.200", reason="test")
        ranges = await ban_service.get_active_ip_ranges()
        assert "10.0.0.200" in ranges