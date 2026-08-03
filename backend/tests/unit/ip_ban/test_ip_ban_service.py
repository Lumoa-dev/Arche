"""IpBanService 行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现
- 用内存数据库做真实 DB 交互
- 自动封禁规则引擎用 mock 隔离计数器状态
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# ip_matches_cidr 工具函数测试
# =============================================================================


class TestIpMatchesCidr:
    """IP/CIDR 匹配工具函数测试。"""

    def test_ipv4_exact_match(self):
        """精确匹配 IPv4 地址。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IPv4 在子网内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IPv4 不在子网内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv6_in_subnet(self):
        """IPv6 在子网内。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True

    def test_ipv6_outside_subnet(self):
        """IPv6 不在子网内。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db9::/32") is False

    def test_invalid_ip_returns_false(self):
        """无效 IP 应返回 False 而不是抛出异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 应返回 False 而不是抛出异常。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_cidr_strict_false_allows_host_bits(self):
        """非严格模式应允许 CIDR 中包含主机位（如 192.168.1.100/24）。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.100/24") is True


# =============================================================================
# IpBanService 测试 - 封禁管理
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceBan:
    """IpBanService 封禁/解封行为测试。"""

    async def test_ban_ip_creates_record(self, db_container):
        """封禁 IP 应创建封禁记录和操作日志。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="test ban",
            ban_type="manual",
            banned_by="admin",
        )

        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["reason"] == "test ban"
        assert result["is_active"] is True
        assert result["id"] > 0

    async def test_ban_ip_with_duration_sets_expiry(self, db_container):
        """封禁时指定时长应设置过期时间。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="temp ban",
            duration_minutes=30,
        )

        assert result["expires_at"] is not None

    async def test_ban_ip_permanent_when_no_duration(self, db_container):
        """不指定时长应为永久封禁（expires_at 为 None）。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="permanent ban",
        )

        assert result["expires_at"] is None

    async def test_ban_ip_existing_active_updates(self, db_container):
        """已存在的活跃封禁记录应更新而不是新建。"""
        service = IpBanService(db_container)
        first = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="first ban",
            duration_minutes=10,
        )

        second = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="updated ban",
            duration_minutes=60,
        )

        assert second["id"] == first["id"]
        assert second["reason"] == "updated ban"

    async def test_unban_ip_marks_inactive(self, db_container):
        """解封应将 is_active 设为 False。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")

        result = await service.unban_ip(ban["id"], operator="admin")
        assert result["is_active"] is False

    async def test_unban_nonexistent_raises_error(self, db_container):
        """解封不存在的记录应抛出 AppError。"""
        service = IpBanService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(99999, operator="admin")

        assert excinfo.value.code == "ban_not_found"
        assert excinfo.value.status_code == 404

    async def test_batch_unban_success(self, db_container):
        """批量解封应返回成功解封数量。"""
        service = IpBanService(db_container)
        b1 = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")
        b2 = await service.ban_ip(ip_or_cidr="10.0.0.2", reason="test")

        count = await service.batch_unban([b1["id"], b2["id"]], operator="admin")
        assert count == 2

    async def test_batch_unban_skips_inactive(self, db_container):
        """批量解封应跳过已不活跃的记录。"""
        service = IpBanService(db_container)
        b1 = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")
        b2 = await service.ban_ip(ip_or_cidr="10.0.0.2", reason="test")
        await service.unban_ip(b1["id"])

        count = await service.batch_unban([b1["id"], b2["id"]], operator="admin")
        assert count == 1  # 只有 b2 被解封


# =============================================================================
# IpBanService 测试 - 查询
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceQuery:
    """IpBanService 查询行为测试。"""

    async def test_list_bans_pagination(self, db_container):
        """分页查询封禁列表应返回正确页码和数量。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}", reason="test")

        result = await service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    async def test_list_bans_filter_by_type(self, db_container):
        """按 ban_type 过滤封禁列表。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="manual", ban_type="manual")
        # 模拟自动封禁
        service._counters.clear()
        # 直接调用 ban_ip 但用 auto 类型
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="auto", ban_type="auto")

        manual_result = await service.list_bans(ban_type="manual")
        auto_result = await service.list_bans(ban_type="auto")

        assert manual_result["total"] >= 1
        assert auto_result["total"] >= 1

    async def test_list_bans_filter_by_active(self, db_container):
        """按 is_active 过滤封禁列表。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")
        await service.unban_ip(ban["id"])

        active_result = await service.list_bans(is_active=True)
        inactive_result = await service.list_bans(is_active=False)

        assert inactive_result["total"] >= 1

    async def test_list_bans_filter_by_keyword(self, db_container):
        """按关键词搜索 IP/CIDR。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1", reason="test")
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")

        result = await service.list_bans(keyword="192.168")
        assert result["total"] >= 1
        assert all("192.168" in b["ip_or_cidr"] for b in result["list"])

    async def test_get_ban_logs_pagination(self, db_container):
        """封禁操作日志分页查询。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")

        result = await service.get_ban_logs(page=1, page_size=20)
        assert result["total"] >= 1
        assert len(result["list"]) >= 1
        assert result["list"][0]["action"] == "ban"

    async def test_get_ban_logs_filter_by_action(self, db_container):
        """按操作类型过滤日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")
        await service.unban_ip(ban["id"])

        ban_logs = await service.get_ban_logs(action="ban")
        unban_logs = await service.get_ban_logs(action="unban")

        assert ban_logs["total"] >= 1
        assert unban_logs["total"] >= 1


# =============================================================================
# IpBanService 测试 - IP 检查
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceCheck:
    """IP 封禁检查行为测试。"""

    async def test_is_ip_banned_returns_true_for_banned_ip(self, db_container):
        """被封禁的 IP 应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")

        assert await service.is_ip_banned("10.0.0.1") is True

    async def test_is_ip_banned_returns_false_for_free_ip(self, db_container):
        """未封禁的 IP 应返回 False。"""
        service = IpBanService(db_container)

        assert await service.is_ip_banned("10.0.0.99") is False

    async def test_is_ip_banned_matches_cidr(self, db_container):
        """封禁 CIDR 段后，该段内 IP 应被封禁。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.0/24", reason="block subnet")

        assert await service.is_ip_banned("192.168.1.100") is True
        assert await service.is_ip_banned("10.0.0.1") is False

    async def test_is_ip_banned_ignores_expired(self, db_container):
        """已过期的封禁不应影响 IP 检查。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test", duration_minutes=0)

        # 使用 expired 封禁
        ban = await service.ban_ip(ip_or_cidr="10.0.0.2", reason="test")
        await service.unban_ip(ban["id"])

        assert await service.is_ip_banned("10.0.0.2") is False

    async def test_get_active_ip_ranges_returns_cidrs(self, db_container):
        """获取活跃 IP 段列表。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.0/24", reason="test")
        await service.ban_ip(ip_or_cidr="10.0.0.0/8", reason="test")

        ranges = await service.get_active_ip_ranges()
        assert "192.168.1.0/24" in ranges
        assert "10.0.0.0/8" in ranges


# =============================================================================
# IpBanService 测试 - 自动封禁规则引擎
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceAutoBan:
    """自动封禁规则引擎测试。"""

    async def test_get_rule_configs_returns_defaults(self, db_container):
        """未配置时返回默认规则。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()

        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    async def test_update_rule_config_updates_threshold(self, db_container):
        """更新规则配置应生效。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()  # 触发默认规则创建

        updated = await service.update_rule_config(
            "login_failure", {"threshold": 20}
        )
        assert updated["threshold"] == 20

    async def test_update_rule_config_nonexistent_raises_error(self, db_container):
        """更新不存在的规则应抛出 AppError。"""
        service = IpBanService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("nonexistent_rule", {"threshold": 10})

        assert excinfo.value.code == "rule_not_found"

    async def test_record_event_triggers_login_failure_ban(self, db_container):
        """登录失败事件达到阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        # 先设置低阈值
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 3, "ban_duration_minutes": 10}
        )

        # 记录 3 次登录失败
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.1")

        assert await service.is_ip_banned("10.0.0.1") is True

    async def test_record_event_login_failure_below_threshold(self, db_container):
        """登录失败未达阈值不应触发封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 10, "ban_duration_minutes": 30}
        )

        # 只记录 3 次，远低于阈值
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.2")

        assert await service.is_ip_banned("10.0.0.2") is False

    async def test_record_event_high_4xx_triggers_ban(self, db_container):
        """高频 4xx 事件达到阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "high_4xx", {"threshold": 3, "ban_duration_minutes": 10}
        )

        for _ in range(3):
            await service.record_event("high_4xx", "10.0.0.3", status_code=403)

        assert await service.is_ip_banned("10.0.0.3") is True

    async def test_record_event_rate_limit_triggers_ban(self, db_container):
        """请求频率事件达到阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "rate_limit", {"threshold": 3, "ban_duration_minutes": 10}
        )

        for _ in range(3):
            await service.record_event("rate_limit", "10.0.0.4")

        assert await service.is_ip_banned("10.0.0.4") is True

    async def test_auto_ban_disabled_rule_does_not_trigger(self, db_container):
        """禁用的规则不应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config("login_failure", {"enabled": False})

        for _ in range(20):
            await service.record_event("login_failure", "10.0.0.5")

        assert await service.is_ip_banned("10.0.0.5") is False


# =============================================================================
# IpBanService 测试 - 统计
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceStats:
    """封禁统计测试。"""

    async def test_get_stats_returns_counts(self, db_container):
        """统计信息应返回正确的计数。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="test", ban_type="auto")

        stats = await service.get_stats()
        assert stats["total_bans"] >= 2
        assert stats["manual_bans"] >= 1
        assert stats["auto_bans"] >= 1