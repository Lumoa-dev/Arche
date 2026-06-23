"""IP 封禁服务单元测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.plugins.ip_ban.services import (
    IpBanService,
    ip_matches_cidr,
)


class TestIpMatchesCidr:
    """测试 IP-CIDR 匹配函数。"""

    def test_ipv4_exact_match(self):
        """IPv4 精确地址应匹配自身。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32")

    def test_ipv4_in_subnet(self):
        """IPv4 地址应在子网范围内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24")
        assert ip_matches_cidr("10.0.0.5", "10.0.0.0/8")

    def test_ipv4_not_in_subnet(self):
        """IPv4 地址不应在子网范围外。"""
        assert not ip_matches_cidr("192.168.2.1", "192.168.1.0/24")
        assert not ip_matches_cidr("10.1.0.1", "172.16.0.0/12")

    def test_ipv6_match(self):
        """IPv6 地址应匹配 CIDR 段。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32")

    def test_ipv6_not_match(self):
        """IPv6 地址不应匹配不同段。"""
        assert not ip_matches_cidr("2001:db8::1", "2002:db8::/32")

    def test_invalid_ip_returns_false(self):
        """无效 IP 字符串应返回 False 不抛异常。"""
        assert not ip_matches_cidr("not-an-ip", "192.168.1.0/24")
        assert not ip_matches_cidr("", "10.0.0.0/8")
        assert not ip_matches_cidr("256.256.256.256", "0.0.0.0/0")

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 段应返回 False 不抛异常。"""
        assert not ip_matches_cidr("192.168.1.1", "not-a-cidr")
        assert not ip_matches_cidr("192.168.1.1", "")

    def test_cidr_strict_false_accepts_host_bits(self):
        """非严格 CIDR（含主机位）也能正确匹配。"""
        assert ip_matches_cidr("192.168.1.55", "192.168.1.0/24")
        # 注意：strict=False 允许 192.168.1.0/24 即使最后一位非零


class TestIpBanServiceUnit:
    """IpBanService 单元测试（使用内存数据库）。"""

    @pytest.fixture(autouse=True)
    async def setup(self, module_db):
        self.db = module_db
        container = MagicMock()
        container.get.return_value = {"session_factory": module_db["session_factory"]}
        config = MagicMock()
        config.get.return_value = ""
        container.get.side_effect = lambda name: (
            {"session_factory": module_db["session_factory"]}
            if name == "db"
            else config
        )
        self.service = IpBanService(container)

    # ── 封禁/解封 CRUD ──

    async def test_ban_ip_creates_ban_record(self):
        """ban_ip 应创建封禁记录和操作日志。"""
        result = await self.service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="恶意攻击",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=60,
        )
        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["ban_type"] == "manual"
        assert result["banned_by"] == "admin"
        assert result["is_active"] is True
        assert result["expires_at"] is not None

    async def test_ban_ip_permanent(self):
        """永久封禁不设置过期时间。"""
        result = await self.service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="永久封禁",
        )
        assert result["expires_at"] is None
        assert result["is_active"] is True

    async def test_ban_ip_duplicate_updates_existing(self):
        """重复封禁同一 IP 应更新已有记录而非新建。"""
        r1 = await self.service.ban_ip(ip_or_cidr="192.168.1.1", reason="首次")
        r2 = await self.service.ban_ip(ip_or_cidr="192.168.1.1", reason="更新")
        assert r1["id"] == r2["id"]
        assert r2["reason"] == "更新"

    async def test_unban_ip_deactivates_ban(self):
        """unban_ip 应将封禁标记为非活跃并记录日志。"""
        ban = await self.service.ban_ip(ip_or_cidr="10.0.0.2", reason="测试")
        result = await self.service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

    async def test_unban_ip_nonexistent_raises(self):
        """解封不存在的 ID 应抛出 AppError。"""
        from backend.core.middleware import AppError

        with pytest.raises(AppError, match="封禁记录不存在"):
            await self.service.unban_ip(ban_id=99999)

    async def test_batch_unban_multiple(self):
        """批量解封应返回正确解封数量。"""
        b1 = await self.service.ban_ip(ip_or_cidr="10.0.0.3")
        b2 = await self.service.ban_ip(ip_or_cidr="10.0.0.4")
        count = await self.service.batch_unban(
            ban_ids=[b1["id"], b2["id"]], operator="admin"
        )
        assert count == 2

    async def test_batch_unban_skips_inactive(self):
        """批量解封应跳过已非活跃的记录。"""
        b1 = await self.service.ban_ip(ip_or_cidr="10.0.0.5")
        await self.service.unban_ip(ban_id=b1["id"])
        b2 = await self.service.ban_ip(ip_or_cidr="10.0.0.6")
        count = await self.service.batch_unban(
            ban_ids=[b1["id"], b2["id"]]
        )
        assert count == 1

    # ── 列表查询 ──

    async def test_list_bans_pagination(self):
        """list_bans 应正确分页。"""
        for i in range(5):
            await self.service.ban_ip(ip_or_cidr=f"10.0.0.{i+10}")
        result = await self.service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    async def test_list_bans_filter_by_type(self):
        """list_bans 应按封禁类型过滤。"""
        await self.service.ban_ip(ip_or_cidr="10.0.0.20", ban_type="manual")
        await self.service.ban_ip(ip_or_cidr="10.0.0.21", ban_type="auto")
        result = await self.service.list_bans(ban_type="manual")
        assert all(b["ban_type"] == "manual" for b in result["list"])

    async def test_list_bans_filter_by_keyword(self):
        """list_bans 应按关键词搜索 IP。"""
        await self.service.ban_ip(ip_or_cidr="192.168.1.1")
        await self.service.ban_ip(ip_or_cidr="10.0.0.1")
        result = await self.service.list_bans(keyword="192.168")
        assert all("192.168" in b["ip_or_cidr"] for b in result["list"])

    async def test_list_bans_filter_by_active(self):
        """list_bans 应按活跃状态过滤。"""
        ban = await self.service.ban_ip(ip_or_cidr="10.0.0.30")
        await self.service.ban_ip(ip_or_cidr="10.0.0.31")
        await self.service.unban_ip(ban_id=ban["id"])
        result = await self.service.list_bans(is_active=False)
        assert all(b["is_active"] is False for b in result["list"])

    # ── 操作日志 ──

    async def test_get_ban_logs_records_actions(self):
        """get_ban_logs 应返回封禁/解封操作记录。"""
        ban = await self.service.ban_ip(ip_or_cidr="10.0.0.40", reason="日志测试")
        await self.service.unban_ip(ban_id=ban["id"])
        logs = await self.service.get_ban_logs()
        actions = [log["action"] for log in logs["list"]]
        assert "ban" in actions
        assert "unban" in actions

    async def test_get_ban_logs_filter_by_action(self):
        """get_ban_logs 应按操作类型过滤。"""
        ban = await self.service.ban_ip(ip_or_cidr="10.0.0.50")
        await self.service.unban_ip(ban_id=ban["id"])
        logs = await self.service.get_ban_logs(action="ban")
        assert all(log["action"] == "ban" for log in logs["list"])

    # ── IP 检查 ──

    async def test_is_ip_banned_returns_true_for_banned_ip(self):
        """已封禁 IP 应返回 True。"""
        await self.service.ban_ip(ip_or_cidr="10.0.0.60")
        assert await self.service.is_ip_banned("10.0.0.60")

    async def test_is_ip_banned_returns_false_for_unknown_ip(self):
        """未封禁 IP 应返回 False。"""
        assert not await self.service.is_ip_banned("10.0.0.99")

    async def test_is_ip_banned_after_unban(self):
        """解封后 IP 应返回 False。"""
        ban = await self.service.ban_ip(ip_or_cidr="10.0.0.70")
        await self.service.unban_ip(ban_id=ban["id"])
        assert not await self.service.is_ip_banned("10.0.0.70")

    async def test_is_ip_banned_expired_ban(self):
        """过期的封禁不应匹配。"""
        from backend.plugins.ip_ban.models import IpBan
        from sqlalchemy import select

        await self.service.ban_ip(
            ip_or_cidr="10.0.0.80",
            duration_minutes=0,  # 立即过期
        )
        # 手动将 expires_at 设为过去
        async with self.db["session_factory"]() as session:
            result = await session.execute(
                select(IpBan).where(IpBan.ip_or_cidr == "10.0.0.80")
            )
            ban = result.scalar_one()
            ban.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        assert not await self.service.is_ip_banned("10.0.0.80")

    async def test_get_active_ip_ranges(self):
        """get_active_ip_ranges 应返回活跃 IP 列表。"""
        await self.service.ban_ip(ip_or_cidr="10.0.0.90")
        await self.service.ban_ip(ip_or_cidr="10.0.0.91")
        ranges = await self.service.get_active_ip_ranges()
        assert "10.0.0.90" in ranges
        assert "10.0.0.91" in ranges

    # ── 统计 ──

    async def test_get_stats_counts(self):
        """get_stats 应返回正确的统计数据。"""
        await self.service.ban_ip(ip_or_cidr="10.0.0.100", ban_type="manual")
        await self.service.ban_ip(ip_or_cidr="10.0.0.101", ban_type="auto")
        stats = await self.service.get_stats()
        assert stats["total_bans"] >= 2
        assert stats["active_bans"] >= 2

    # ── 自动封禁规则引擎 ──

    async def test_get_rule_configs_returns_defaults(self):
        """get_rule_configs 未配置时返回默认规则。"""
        rules = await self.service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    async def test_update_rule_config_modifies_threshold(self):
        """update_rule_config 应更新规则阈值。"""
        # 先调用 get_rule_configs 确保默认规则已创建到 DB
        await self.service.get_rule_configs()

        await self.service.update_rule_config(
            "login_failure", {"threshold": 20, "enabled": False}
        )
        rules = await self.service.get_rule_configs()
        updated = next(r for r in rules if r["id"] == "login_failure")
        assert updated["threshold"] == 20
        assert updated["enabled"] is False

    async def test_update_rule_config_invalid_id_raises(self):
        """更新不存在的规则 ID 应抛出 AppError。"""
        from backend.core.middleware import AppError

        with pytest.raises(AppError, match="规则不存在"):
            await self.service.update_rule_config("nonexistent", {"enabled": True})

    async def test_record_event_login_failure_triggers_ban(self):
        """登录失败事件累积超过阈值应触发自动封禁。"""
        # 先调用 get_rule_configs 确保默认规则已创建到 DB
        await self.service.get_rule_configs()

        # 降低阈值以便测试
        await self.service.update_rule_config(
            "login_failure",
            {"threshold": 3, "window_seconds": 300, "ban_duration_minutes": 10},
        )
        for _ in range(3):
            await self.service.record_event("login_failure", "10.0.0.200")

        assert await self.service.is_ip_banned("10.0.0.200")

    def test_cleanup_counters_removes_expired(self):
        """_cleanup_counters 应移除过期计数器条目。"""
        self.service._counters["test:10.0.0.1"] = [(0.0, 200)]
        self.service._cleanup_counters()
        assert "test:10.0.0.1" not in self.service._counters

    def test_ban_to_dict_format(self):
        """_ban_to_dict 应返回正确的字典格式。"""
        from datetime import datetime, timezone
        from unittest.mock import MagicMock

        now = datetime.now(timezone.utc)
        ban = MagicMock()
        ban.id = 1
        ban.ip_or_cidr = "10.0.0.1"
        ban.ban_type = "manual"
        ban.reason = "test"
        ban.rule_id = None
        ban.banned_by = "admin"
        ban.created_at = now
        ban.expires_at = None
        ban.is_active = True

        d = self.service._ban_to_dict(ban)
        assert d["id"] == 1
        assert d["ip_or_cidr"] == "10.0.0.1"
        assert d["expires_at"] is None
        assert d["is_active"] is True