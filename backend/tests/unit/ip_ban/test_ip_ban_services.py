"""IpBanService 行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现
- 用内存数据库做真实交互
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# ip_matches_cidr 工具函数测试
# =============================================================================


class TestIpMatchesCidr:
    """测试 IP/CIDR 匹配工具函数。"""

    def test_ipv4_exact_match(self):
        """精确 IP 匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IPv4 在子网内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IPv4 不在子网内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv6_in_subnet(self):
        """IPv6 在子网内。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_ipv6_outside_subnet(self):
        """IPv6 不在子网内。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db9::/32") is False
        )

    def test_invalid_ip_returns_false(self):
        """无效 IP 返回 False 而非抛出异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 返回 False 而非抛出异常。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_cidr_with_non_strict_network(self):
        """非严格 CIDR 段（如 10.0.0.1/24）自动转为网络地址。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1/24") is True


# =============================================================================
# IpBanService 核心行为测试
# =============================================================================


class TestIpBanService:
    """测试 IpBanService 核心功能。"""

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_initially(self, db_container):
        """初始状态，任何 IP 都不在封禁列表中。"""
        service = IpBanService(db_container)
        result = await service.is_ip_banned("192.168.1.1")
        assert result is False

    @pytest.mark.asyncio
    async def test_ban_ip_creates_ban_record(self, db_container):
        """封禁 IP 后，该 IP 应被标记为已封禁。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="恶意访问",
            ban_type="manual",
            banned_by="admin",
        )
        assert result["ip_or_cidr"] == "10.0.0.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["reason"] == "恶意访问"
        assert result["banned_by"] == "admin"

    @pytest.mark.asyncio
    async def test_ban_ip_then_check_is_banned(self, db_container):
        """封禁后检查 is_ip_banned 应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="攻击",
            ban_type="manual",
            banned_by="admin",
        )
        assert await service.is_ip_banned("10.0.0.1") is True

    @pytest.mark.asyncio
    async def test_ban_ip_with_cidr(self, db_container):
        """封禁 CIDR 段后，段内 IP 应被标记为已封禁。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="192.168.1.0/24",
            reason="扫描",
            ban_type="auto",
            rule_id="high_4xx",
        )
        assert await service.is_ip_banned("192.168.1.50") is True
        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_ban_ip_with_expiry(self, db_container):
        """带过期时间的封禁应正确设置过期时间。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="临时封禁",
            duration_minutes=30,
        )
        assert result["is_active"] is True
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_ip_permanent_when_no_expiry(self, db_container):
        """不设置过期时间应为永久封禁（expires_at=None）。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.3",
            reason="永久封禁",
        )
        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_unban_ip_marks_inactive(self, db_container):
        """解封后 is_active 应为 False。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="10.0.0.4",
            reason="已解决",
            banned_by="admin",
        )
        unbanned = await service.unban_ip(ban["id"], operator="admin")
        assert unbanned["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_ip_not_found_raises_error(self, db_container):
        """解封不存在的记录应抛出 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(9999, operator="admin")
        assert excinfo.value.code == "ban_not_found"
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_unban_ip_removes_from_active_check(self, db_container):
        """解封后 is_ip_banned 应返回 False。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="10.0.0.5",
            reason="测试",
            banned_by="admin",
        )
        await service.unban_ip(ban["id"], operator="admin")
        assert await service.is_ip_banned("10.0.0.5") is False

    @pytest.mark.asyncio
    async def test_batch_unban_multiple_ips(self, db_container):
        """批量解封多个 IP 应返回正确的解封数量。"""
        service = IpBanService(db_container)
        ban1 = await service.ban_ip("10.0.0.10", reason="r1")
        ban2 = await service.ban_ip("10.0.0.11", reason="r2")
        ban3 = await service.ban_ip("10.0.0.12", reason="r3")

        count = await service.batch_unban(
            [ban1["id"], ban2["id"], ban3["id"]], operator="admin"
        )
        assert count == 3

        # 验证所有都已解封
        assert await service.is_ip_banned("10.0.0.10") is False
        assert await service.is_ip_banned("10.0.0.11") is False
        assert await service.is_ip_banned("10.0.0.12") is False

    @pytest.mark.asyncio
    async def test_batch_unban_skips_inactive(self, db_container):
        """批量解封时，已非活跃的记录应跳过。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip("10.0.0.20", reason="r1")
        await service.unban_ip(ban["id"], operator="admin")

        count = await service.batch_unban([ban["id"]], operator="admin")
        assert count == 0

    @pytest.mark.asyncio
    async def test_ban_ip_duplicate_updates_existing(self, db_container):
        """重复封禁同一 IP 应更新现有记录而非新建。"""
        service = IpBanService(db_container)
        r1 = await service.ban_ip("10.0.0.30", reason="首次")
        r2 = await service.ban_ip("10.0.0.30", reason="再次封禁")
        assert r1["id"] == r2["id"]
        assert r2["reason"] == "再次封禁"


# =============================================================================
# 封禁列表查询测试
# =============================================================================


class TestListBans:
    """测试封禁列表查询。"""

    @pytest.mark.asyncio
    async def test_list_bans_empty(self, db_container):
        """初始状态封禁列表为空。"""
        service = IpBanService(db_container)
        result = await service.list_bans()
        assert result["total"] == 0
        assert result["list"] == []

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, db_container):
        """分页查询应正确返回指定页数据。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(f"10.0.0.{i}", reason=f"test-{i}")

        result = await service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, db_container):
        """按封禁类型过滤应正确返回。"""
        service = IpBanService(db_container)
        await service.ban_ip("10.0.0.1", reason="manual", ban_type="manual")
        await service.ban_ip("10.0.0.2", reason="auto", ban_type="auto")

        result = await service.list_bans(ban_type="auto")
        assert result["total"] == 1
        assert result["list"][0]["ban_type"] == "auto"

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_keyword(self, db_container):
        """按关键词搜索应正确返回。"""
        service = IpBanService(db_container)
        await service.ban_ip("10.0.0.1", reason="攻击")
        await service.ban_ip("192.168.1.1", reason="扫描")

        result = await service.list_bans(keyword="10.0")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "10.0.0.1"


# =============================================================================
# 自动封禁规则引擎测试
# =============================================================================


class TestAutoBanRuleEngine:
    """测试自动封禁规则引擎。"""

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, db_container):
        """未配置时，get_rule_configs 应返回默认规则。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_update_rule_config_changes_threshold(self, db_container):
        """更新规则阈值应生效。"""
        service = IpBanService(db_container)
        # 先触发默认规则种子
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 5, "enabled": True}
        )
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 5

    @pytest.mark.asyncio
    async def test_update_rule_config_not_found(self, db_container):
        """更新不存在的规则应抛出 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("non_existent", {"threshold": 5})
        assert excinfo.value.code == "rule_not_found"

    @pytest.mark.asyncio
    async def test_update_rule_ignores_unknown_fields(self, db_container):
        """更新规则时，未知字段应被忽略。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 3, "unknown_field": "value"}
        )
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 3
        # 不存在的字段不应出现在结果中
        assert "unknown_field" not in login_rule

    @pytest.mark.asyncio
    async def test_record_event_login_failure_triggers_auto_ban(self, db_container):
        """登录失败超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        # 先触发默认规则种子，再将阈值降到 3
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 3, "enabled": True, "ban_duration_minutes": 10}
        )

        # 记录 3 次登录失败
        await service.record_event("login_failure", "10.0.0.100", 401)
        await service.record_event("login_failure", "10.0.0.100", 401)
        await service.record_event("login_failure", "10.0.0.100", 401)

        # 验证已被自动封禁
        assert await service.is_ip_banned("10.0.0.100") is True

    @pytest.mark.asyncio
    async def test_record_event_below_threshold_no_ban(self, db_container):
        """登录失败未达阈值不应触发封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 5, "enabled": True}
        )

        await service.record_event("login_failure", "10.0.0.101", 401)
        await service.record_event("login_failure", "10.0.0.101", 401)

        assert await service.is_ip_banned("10.0.0.101") is False

    @pytest.mark.asyncio
    async def test_auto_ban_disabled_rule_does_not_trigger(self, db_container):
        """禁用的规则不应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 3, "enabled": False}
        )

        await service.record_event("login_failure", "10.0.0.102", 401)
        await service.record_event("login_failure", "10.0.0.102", 401)
        await service.record_event("login_failure", "10.0.0.102", 401)

        assert await service.is_ip_banned("10.0.0.102") is False


# =============================================================================
# 封禁统计测试
# =============================================================================


class TestBanStats:
    """测试封禁统计功能。"""

    @pytest.mark.asyncio
    async def test_get_stats_initial_zero(self, db_container):
        """初始状态统计应为零。"""
        service = IpBanService(db_container)
        stats = await service.get_stats()
        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_after_ban(self, db_container):
        """封禁后统计应正确计数。"""
        service = IpBanService(db_container)
        await service.ban_ip("10.0.0.1", reason="test", ban_type="manual")
        await service.ban_ip("10.0.0.2", reason="test", ban_type="auto")
        await service.ban_ip("10.0.0.3", reason="test", ban_type="auto")

        stats = await service.get_stats()
        assert stats["total_bans"] == 3
        assert stats["active_bans"] == 3
        assert stats["auto_bans"] == 2
        assert stats["manual_bans"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_after_unban(self, db_container):
        """解封后活跃封禁数应减少。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip("10.0.0.1", reason="test", ban_type="manual")
        await service.ban_ip("10.0.0.2", reason="test", ban_type="auto")

        await service.unban_ip(ban["id"], operator="admin")

        stats = await service.get_stats()
        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 1


# =============================================================================
# 操作日志测试
# =============================================================================


class TestBanLogs:
    """测试封禁操作日志。"""

    @pytest.mark.asyncio
    async def test_get_ban_logs_empty(self, db_container):
        """初始状态日志为空。"""
        service = IpBanService(db_container)
        result = await service.get_ban_logs()
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_ban_creates_log(self, db_container):
        """封禁操作应产生日志。"""
        service = IpBanService(db_container)
        await service.ban_ip("10.0.0.1", reason="test", banned_by="admin")
        result = await service.get_ban_logs()
        assert result["total"] == 1
        assert result["list"][0]["action"] == "ban"
        assert result["list"][0]["operator"] == "admin"

    @pytest.mark.asyncio
    async def test_unban_creates_log(self, db_container):
        """解封操作应产生日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip("10.0.0.2", reason="test")
        await service.unban_ip(ban["id"], operator="admin")

        logs = await service.get_ban_logs(action="unban")
        assert logs["total"] == 1
        assert logs["list"][0]["action"] == "unban"

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, db_container):
        """按操作类型过滤日志应正确返回。"""
        service = IpBanService(db_container)
        await service.ban_ip("10.0.0.3", reason="test")
        ban = await service.ban_ip("10.0.0.4", reason="test")
        await service.unban_ip(ban["id"], operator="admin")

        ban_logs = await service.get_ban_logs(action="ban")
        assert ban_logs["total"] == 2

        unban_logs = await service.get_ban_logs(action="unban")
        assert unban_logs["total"] == 1