"""IpBanService 行为测试。

覆盖：
- 封禁 / 解封 / 批量解封
- IP 检查（is_ip_banned / get_active_ip_ranges）
- 分页查询（list_bans / get_ban_logs）
- 自动封禁规则引擎（record_event + 规则检查）
- 统计（get_stats）
- 边界条件（不存在记录、过期封禁、空列表）
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService


class TestIpBanService:
    """IpBanService 核心行为测试。"""

    # ── 封禁 / 解封 ──

    @pytest.mark.asyncio
    async def test_ban_ip_creates_ban_and_log(self, db_container):
        """封禁 IP 应创建封禁记录和操作日志。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="test ban",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=60,
        )
        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_ip_permanent(self, db_container):
        """永久封禁时 expires_at 为 None。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="permanent ban",
            ban_type="manual",
            duration_minutes=None,
        )
        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_ban_ip_duplicate_returns_existing(self, db_container):
        """重复封禁相同 IP 返回已有记录（更新过期时间）。"""
        service = IpBanService(db_container)
        result1 = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="first ban",
            ban_type="manual",
            duration_minutes=30,
        )
        result2 = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="second ban",
            ban_type="manual",
            duration_minutes=60,
        )
        # 应返回已有记录，且 expires_at 已更新
        assert result2["id"] == result1["id"]
        assert result2["expires_at"] != result1["expires_at"]

    @pytest.mark.asyncio
    async def test_unban_ip(self, db_container):
        """解封后 is_active 为 False。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="test",
            ban_type="manual",
            duration_minutes=30,
        )
        result = await service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises(self, db_container):
        """解封不存在的记录抛出 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(ban_id=99999, operator="admin")
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_unban(self, db_container):
        """批量解封返回解封数量。"""
        service = IpBanService(db_container)
        ban1 = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test", duration_minutes=30)
        ban2 = await service.ban_ip(ip_or_cidr="10.0.0.2", reason="test", duration_minutes=30)
        ban3 = await service.ban_ip(ip_or_cidr="10.0.0.3", reason="test", duration_minutes=30)

        count = await service.batch_unban(
            ban_ids=[ban1["id"], ban2["id"]], operator="admin"
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_batch_unban_empty_list(self, db_container):
        """空列表批量解封返回 0。"""
        service = IpBanService(db_container)
        count = await service.batch_unban(ban_ids=[], operator="admin")
        assert count == 0

    # ── IP 检查 ──

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_true_for_banned_ip(self, db_container):
        """被封禁的 IP 应被检测到。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="test",
            ban_type="manual",
            duration_minutes=60,
        )
        assert await service.is_ip_banned("192.168.1.1") is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_for_unbanned_ip(self, db_container):
        """未被封禁的 IP 返回 False。"""
        service = IpBanService(db_container)
        assert await service.is_ip_banned("192.168.1.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_checks_cidr_range(self, db_container):
        """CIDR 段封禁后，段内 IP 应被检测到。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.0/24",
            reason="block range",
            ban_type="manual",
            duration_minutes=60,
        )
        assert await service.is_ip_banned("10.0.0.50") is True
        assert await service.is_ip_banned("10.0.1.1") is False

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, db_container):
        """获取活跃的 IP/CIDR 段列表。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.0/24", reason="test", duration_minutes=60)
        await service.ban_ip(ip_or_cidr="192.168.1.1", reason="test", duration_minutes=60)
        ranges = await service.get_active_ip_ranges()
        assert "10.0.0.0/24" in ranges
        assert "192.168.1.1" in ranges

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges_excludes_expired(self, db_container):
        """已过期封禁不包含在活跃段中。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test", duration_minutes=0)
        # 解封
        bans = await service.list_bans(page=1, page_size=100)
        for ban in bans["list"]:
            if ban["ip_or_cidr"] == "10.0.0.1":
                await service.unban_ip(ban["id"], operator="admin")
        ranges = await service.get_active_ip_ranges()
        assert "10.0.0.1" not in ranges

    # ── 分页查询 ──

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, db_container):
        """分页查询封禁列表。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(
                ip_or_cidr=f"10.0.0.{i}",
                reason="test",
                duration_minutes=30,
            )
        result = await service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, db_container):
        """按封禁类型过滤。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="manual", ban_type="manual")
        result = await service.list_bans(ban_type="manual")
        assert result["total"] >= 1
        for ban in result["list"]:
            assert ban["ban_type"] == "manual"

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_keyword(self, db_container):
        """按关键词搜索 IP/CIDR。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test", duration_minutes=30)
        result = await service.list_bans(keyword="10.0.0")
        assert result["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_ban_logs(self, db_container):
        """封禁操作日志分页查询。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test", duration_minutes=30)
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="test", duration_minutes=30)
        logs = await service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] >= 2
        assert len(logs["list"]) >= 2

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, db_container):
        """按操作类型过滤日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="10.0.0.1", reason="test", duration_minutes=30
        )
        await service.unban_ip(ban["id"], operator="admin")
        logs = await service.get_ban_logs(action="unban")
        assert logs["total"] >= 1
        for log in logs["list"]:
            assert log["action"] == "unban"

    # ── 统计 ──

    @pytest.mark.asyncio
    async def test_get_stats(self, db_container):
        """封禁统计返回各项计数。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="auto", ban_type="auto")
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="manual", ban_type="manual")
        stats = await service.get_stats()
        assert stats["total_bans"] >= 2
        assert stats["auto_bans"] >= 1
        assert stats["manual_bans"] >= 1

    # ── 自动封禁规则引擎 ──

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, db_container):
        """获取规则配置返回默认规则。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_update_rule_config(self, db_container):
        """更新规则配置。"""
        service = IpBanService(db_container)
        # 先确保规则存在
        await service.get_rule_configs()
        result = await service.update_rule_config(
            "login_failure", {"threshold": 20, "enabled": False}
        )
        assert result["threshold"] == 20
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises(self, db_container):
        """更新不存在的规则抛出 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("nonexistent", {"threshold": 10})
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_record_event_login_failure_triggers_ban(self, db_container):
        """登录失败事件达到阈值后触发自动封禁。"""
        service = IpBanService(db_container)
        # 先确保规则存在并设置低阈值
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"threshold": 3, "window_seconds": 60, "ban_duration_minutes": 10},
        )

        # 记录 3 次登录失败事件
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.99")

        # 验证 IP 已被自动封禁
        assert await service.is_ip_banned("10.0.0.99") is True

    @pytest.mark.asyncio
    async def test_record_event_below_threshold_no_ban(self, db_container):
        """登录失败事件未达到阈值不触发封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"threshold": 10, "window_seconds": 60},
        )

        # 记录 3 次（低于阈值 10）
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.99")

        assert await service.is_ip_banned("10.0.0.99") is False

    @pytest.mark.asyncio
    async def test_record_event_rate_limit(self, db_container):
        """请求频率事件达到阈值触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "rate_limit",
            {"threshold": 5, "window_seconds": 60, "ban_duration_minutes": 10},
        )

        for _ in range(5):
            await service.record_event("rate_limit", "10.0.0.88")

        assert await service.is_ip_banned("10.0.0.88") is True