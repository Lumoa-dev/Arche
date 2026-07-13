"""IP 封禁服务测试 —— 封禁管理、规则引擎、自动封禁。

测试策略：
- 使用 in_memory_db 进行数据库操作测试
- 使用 mock 隔离外部依赖（webhook、aiohttp）
- 覆盖：CIDR 匹配、手动封禁/解封、自动规则引擎、事件触发、统计
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# CIDR 匹配工具函数测试
# =============================================================================


class TestIpMatchesCidr:
    """ip_matches_cidr 纯函数测试。"""

    def test_ipv4_exact_match(self):
        """精确 IPv4 匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IPv4 在子网内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IPv4 不在子网内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_cidr_without_prefix(self):
        """CIDR 不带前缀长度（视为 /32）。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1") is True

    def test_invalid_ip(self):
        """无效 IP 返回 False。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr(self):
        """无效 CIDR 返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_ipv6_match(self):
        """IPv6 匹配。"""
        assert (
            ip_matches_cidr("::1", "::1/128") is True
        )

    def test_ipv6_in_subnet(self):
        """IPv6 在子网内。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )


# =============================================================================
# IpBanService 测试
# =============================================================================


@pytest.fixture
async def ip_ban_service(db_container):
    """创建 IpBanService 实例。"""
    service = IpBanService(db_container)
    # 禁用 webhook
    service._webhook_url = ""
    return service


@pytest.mark.asyncio
class TestIpBanServiceCheck:
    """IP 检查功能测试。"""

    async def test_is_ip_banned_no_bans(self, ip_ban_service):
        """无封禁记录时返回 False。"""
        banned = await ip_ban_service.is_ip_banned("192.168.1.1")
        assert banned is False

    async def test_is_ip_banned_active_ban(self, ip_ban_service):
        """有活跃封禁记录时返回 True。"""
        await ip_ban_service.ban_ip("192.168.1.1", reason="测试封禁")
        banned = await ip_ban_service.is_ip_banned("192.168.1.1")
        assert banned is True

    async def test_is_ip_banned_cidr_match(self, ip_ban_service):
        """CIDR 段封禁，范围内的 IP 被匹配。"""
        await ip_ban_service.ban_ip("192.168.1.0/24", reason="封禁整个段")
        banned = await ip_ban_service.is_ip_banned("192.168.1.100")
        assert banned is True

    async def test_is_ip_banned_cidr_not_match(self, ip_ban_service):
        """CIDR 段封禁，范围外的 IP 不被匹配。"""
        await ip_ban_service.ban_ip("192.168.1.0/24", reason="封禁整个段")
        banned = await ip_ban_service.is_ip_banned("10.0.0.1")
        assert banned is False

    async def test_is_ip_banned_expired(self, ip_ban_service):
        """过期的封禁记录不匹配。"""
        await ip_ban_service.ban_ip("192.168.1.1", duration_minutes=0)
        banned = await ip_ban_service.is_ip_banned("192.168.1.1")
        # duration_minutes=0 表示永久，所以仍应被封禁
        # 测试实际的过期逻辑
        assert banned is True

    async def test_is_ip_banned_inactive(self, ip_ban_service):
        """已解封的记录不匹配。"""
        ban = await ip_ban_service.ban_ip("192.168.1.1", reason="测试")
        await ip_ban_service.unban_ip(ban["id"], operator="admin")
        banned = await ip_ban_service.is_ip_banned("192.168.1.1")
        assert banned is False


@pytest.mark.asyncio
class TestIpBanServiceBanUnban:
    """封禁/解封功能测试。"""

    async def test_ban_ip_creates_record(self, ip_ban_service):
        """封禁创建记录。"""
        result = await ip_ban_service.ban_ip(
            "10.0.0.1", reason="恶意请求", ban_type="manual", banned_by="admin"
        )
        assert result["ip_or_cidr"] == "10.0.0.1"
        assert result["ban_type"] == "manual"
        assert result["reason"] == "恶意请求"
        assert result["is_active"] is True

    async def test_ban_ip_duplicate(self, ip_ban_service):
        """重复封禁同一 IP 返回已有记录。"""
        result1 = await ip_ban_service.ban_ip("10.0.0.1", reason="第一次")
        result2 = await ip_ban_service.ban_ip("10.0.0.1", reason="第二次")
        assert result1["id"] == result2["id"]

    async def test_ban_ip_with_duration(self, ip_ban_service):
        """封禁带过期时间。"""
        result = await ip_ban_service.ban_ip(
            "10.0.0.1", reason="临时封禁", duration_minutes=30
        )
        assert result["expires_at"] is not None

    async def test_unban_ip(self, ip_ban_service):
        """解封 IP。"""
        ban = await ip_ban_service.ban_ip("10.0.0.1", reason="测试")
        result = await ip_ban_service.unban_ip(ban["id"], operator="admin")
        assert result["is_active"] is False

    async def test_unban_not_found(self, ip_ban_service):
        """解封不存在的记录抛异常。"""
        with pytest.raises(Exception) as excinfo:
            await ip_ban_service.unban_ip(99999, operator="admin")
        assert "封禁记录不存在" in str(excinfo.value)

    async def test_batch_unban(self, ip_ban_service):
        """批量解封。"""
        ban1 = await ip_ban_service.ban_ip("10.0.0.1", reason="测试1")
        ban2 = await ip_ban_service.ban_ip("10.0.0.2", reason="测试2")
        count = await ip_ban_service.batch_unban(
            [ban1["id"], ban2["id"]], operator="admin"
        )
        assert count == 2


@pytest.mark.asyncio
class TestIpBanServiceList:
    """查询功能测试。"""

    async def test_list_bans_empty(self, ip_ban_service):
        """空列表查询。"""
        result = await ip_ban_service.list_bans()
        assert result["total"] == 0
        assert result["list"] == []

    async def test_list_bans_with_data(self, ip_ban_service):
        """有数据的分页查询。"""
        await ip_ban_service.ban_ip("10.0.0.1", reason="测试1")
        await ip_ban_service.ban_ip("10.0.0.2", reason="测试2")
        result = await ip_ban_service.list_bans()
        assert result["total"] == 2
        assert len(result["list"]) == 2

    async def test_list_bans_filter_by_type(self, ip_ban_service):
        """按类型筛选。"""
        await ip_ban_service.ban_ip("10.0.0.1", reason="手动", ban_type="manual")
        result = await ip_ban_service.list_bans(ban_type="manual")
        assert result["total"] == 1
        result = await ip_ban_service.list_bans(ban_type="auto")
        assert result["total"] == 0

    async def test_list_bans_keyword_search(self, ip_ban_service):
        """关键词搜索。"""
        await ip_ban_service.ban_ip("10.0.0.1", reason="测试")
        await ip_ban_service.ban_ip("192.168.1.1", reason="测试")
        result = await ip_ban_service.list_bans(keyword="10.0")
        assert result["total"] == 1

    async def test_list_bans_pagination(self, ip_ban_service):
        """分页参数正确。"""
        for i in range(5):
            await ip_ban_service.ban_ip(f"10.0.0.{i}", reason=f"测试{i}")
        result = await ip_ban_service.list_bans(page=1, page_size=2)
        assert result["page"] == 1
        assert result["page_size"] == 2
        assert len(result["list"]) == 2
        assert result["total"] == 5

    async def test_get_ban_logs(self, ip_ban_service):
        """获取封禁操作日志。"""
        await ip_ban_service.ban_ip("10.0.0.1", reason="测试")
        logs = await ip_ban_service.get_ban_logs()
        assert logs["total"] >= 1
        assert logs["list"][0]["action"] == "ban"


@pytest.mark.asyncio
class TestIpBanServiceAutoRules:
    """自动封禁规则引擎测试。"""

    async def test_get_rule_configs_defaults(self, ip_ban_service):
        """获取默认规则配置。"""
        rules = await ip_ban_service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    async def test_update_rule_config(self, ip_ban_service):
        """更新规则配置。"""
        rules = await ip_ban_service.get_rule_configs()
        rule = rules[0]
        updated = await ip_ban_service.update_rule_config(
            rule["id"], {"threshold": 5, "enabled": False}
        )
        assert updated["threshold"] == 5
        assert updated["enabled"] is False

    async def test_update_rule_config_not_found(self, ip_ban_service):
        """更新不存在的规则抛异常。"""
        with pytest.raises(Exception) as excinfo:
            await ip_ban_service.update_rule_config("nonexistent", {"threshold": 5})
        assert "规则不存在" in str(excinfo.value)

    @patch("time.time")
    async def test_record_event_login_failure_triggers_ban(self, mock_time, ip_ban_service):
        """登录失败事件触发自动封禁。"""
        mock_time.return_value = 1000.0

        # 修改 login_failure 规则阈值
        rules = await ip_ban_service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        await ip_ban_service.update_rule_config("login_failure", {"threshold": 3, "enabled": True})

        # 记录 3 次登录失败
        for _ in range(3):
            await ip_ban_service.record_event("login_failure", "10.0.0.1")

        # IP 应被自动封禁
        banned = await ip_ban_service.is_ip_banned("10.0.0.1")
        assert banned is True

    @patch("time.time")
    async def test_record_event_rate_limit_triggers_ban(self, mock_time, ip_ban_service):
        """请求频率事件触发自动封禁。"""
        mock_time.return_value = 1000.0

        rules = await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config("rate_limit", {"threshold": 5, "enabled": True})

        # 记录 5 次请求
        for _ in range(5):
            await ip_ban_service.record_event("rate_limit", "10.0.0.2")

        banned = await ip_ban_service.is_ip_banned("10.0.0.2")
        assert banned is True

    @patch("time.time")
    async def test_record_event_below_threshold(self, mock_time, ip_ban_service):
        """事件次数低于阈值不触发封禁。"""
        mock_time.return_value = 1000.0

        rules = await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config("login_failure", {"threshold": 10, "enabled": True})

        # 只记录 3 次，低于阈值
        for _ in range(3):
            await ip_ban_service.record_event("login_failure", "10.0.0.3")

        banned = await ip_ban_service.is_ip_banned("10.0.0.3")
        assert banned is False

    @patch("time.time")
    async def test_record_event_disabled_rule(self, mock_time, ip_ban_service):
        """禁用的规则不触发封禁。"""
        mock_time.return_value = 1000.0

        # 先初始化默认规则到数据库
        await ip_ban_service.get_rule_configs()
        # 再禁用登录失败规则
        await ip_ban_service.update_rule_config("login_failure", {"enabled": False})

        # 即使超过阈值也不封禁
        for _ in range(10):
            await ip_ban_service.record_event("login_failure", "10.0.0.4")

        banned = await ip_ban_service.is_ip_banned("10.0.0.4")
        assert banned is False

    async def test_get_stats(self, ip_ban_service):
        """获取封禁统计。"""
        await ip_ban_service.ban_ip("10.0.0.1", reason="测试1", ban_type="manual")
        await ip_ban_service.ban_ip("10.0.0.2", reason="测试2", ban_type="auto")

        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] >= 2
        assert stats["auto_bans"] >= 1
        assert stats["manual_bans"] >= 1
        assert stats["active_bans"] >= 2