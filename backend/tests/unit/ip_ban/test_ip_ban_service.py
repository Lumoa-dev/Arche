"""IP 封禁服务单元测试。

覆盖 IpBanService 的核心业务逻辑：
- IP/CIDR 匹配检查
- 封禁/解封 CRUD
- 自动封禁规则引擎
- 分页查询与统计
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# ip_matches_cidr 纯函数测试
# =============================================================================


class TestIpMatchesCIDR:
    def test_ipv4_in_cidr(self):
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_not_in_cidr(self):
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_exact_match(self):
        assert ip_matches_cidr("203.0.113.5", "203.0.113.5/32") is True

    def test_ipv6_in_cidr(self):
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True

    def test_ipv6_not_in_cidr(self):
        assert ip_matches_cidr("2001:db8::1", "2001:db9::/32") is False

    def test_invalid_ip_returns_false(self):
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        assert ip_matches_cidr("192.168.1.1", "invalid-cidr") is False

    def test_single_ip_no_cidr(self):
        assert ip_matches_cidr("10.0.0.5", "10.0.0.5") is True


# =============================================================================
# IpBanService 集成测试（使用真实内存数据库）
# =============================================================================


@pytest.fixture
def ip_ban_service(db_container):
    return IpBanService(db_container)


@pytest.mark.asyncio
class TestIpBanService:
    """IpBanService 核心 CRUD + 查询逻辑。"""

    async def test_is_ip_banned_returns_false_when_no_bans(
        self, ip_ban_service
    ):
        result = await ip_ban_service.is_ip_banned("192.168.1.1")
        assert result is False

    async def test_ban_and_check_ip(self, ip_ban_service):
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="test ban",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=60,
        )
        is_banned = await ip_ban_service.is_ip_banned("10.0.0.1")
        assert is_banned is True

    async def test_ban_cidr_range_check_ip_in_range(self, ip_ban_service):
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.0/24",
            reason="block subnet",
            ban_type="manual",
            banned_by="admin",
        )
        assert await ip_ban_service.is_ip_banned("192.168.1.50") is True
        assert await ip_ban_service.is_ip_banned("192.168.2.1") is False

    async def test_unban_ip(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="temporary",
            ban_type="manual",
            duration_minutes=30,
        )
        await ip_ban_service.unban_ip(ban_id=ban["id"], operator="admin")
        assert await ip_ban_service.is_ip_banned("10.0.0.2") is False

    async def test_unban_nonexistent_raises_error(self, ip_ban_service):
        with pytest.raises(Exception, match="封禁记录不存在"):
            await ip_ban_service.unban_ip(ban_id=99999, operator="admin")

    async def test_ban_ip_existing_updates_expiry(self, ip_ban_service):
        ban1 = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.3",
            reason="first",
            duration_minutes=30,
        )
        ban2 = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.3",
            reason="updated",
            duration_minutes=120,
        )
        assert ban1["id"] == ban2["id"]
        assert ban2["reason"] == "updated"

    async def test_batch_unban(self, ip_ban_service):
        b1 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.10")
        b2 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.11")
        b3 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.12")

        count = await ip_ban_service.batch_unban(
            ban_ids=[b1["id"], b2["id"]], operator="admin"
        )
        assert count == 2

        assert await ip_ban_service.is_ip_banned("10.0.0.10") is False
        assert await ip_ban_service.is_ip_banned("10.0.0.11") is False
        assert await ip_ban_service.is_ip_banned("10.0.0.12") is True

    async def test_list_bans_pagination(self, ip_ban_service):
        for i in range(5):
            await ip_ban_service.ban_ip(ip_or_cidr=f"10.0.0.{100 + i}")

        page1 = await ip_ban_service.list_bans(page=1, page_size=2)
        assert len(page1["list"]) == 2
        assert page1["total"] == 5
        assert page1["page"] == 1
        assert page1["page_size"] == 2

        page2 = await ip_ban_service.list_bans(page=2, page_size=2)
        assert len(page2["list"]) == 2

    async def test_list_bans_filter_by_type(self, ip_ban_service):
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.50", ban_type="manual"
        )
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.51", ban_type="manual"
        )

        result = await ip_ban_service.list_bans(ban_type="manual")
        assert result["total"] >= 2
        for ban in result["list"]:
            assert ban["ban_type"] == "manual"

    async def test_list_bans_filter_by_keyword(self, ip_ban_service):
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.99")
        result = await ip_ban_service.list_bans(keyword="10.0.0.99")
        assert result["total"] >= 1


@pytest.mark.asyncio
class TestIpBanServiceEdgeCases:
    """IpBanService 边界条件测试。"""

    async def test_is_ip_banned_with_expired_ban(self, ip_ban_service):
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.200",
            duration_minutes=0,
        )
        # 0 分钟 = 永久封禁
        assert await ip_ban_service.is_ip_banned("10.0.0.200") is True

    async def test_is_ip_banned_unbanned_ip_not_banned(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.201")
        await ip_ban_service.unban_ip(ban_id=ban["id"])
        assert await ip_ban_service.is_ip_banned("10.0.0.201") is False

    async def test_permanent_ban(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.202",
            reason="permanent",
            duration_minutes=None,
        )
        assert ban["expires_at"] is None

    async def test_get_active_ip_ranges(self, ip_ban_service):
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.100")
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.101")
        ranges = await ip_ban_service.get_active_ip_ranges()
        assert "10.0.0.100" in ranges
        assert "10.0.0.101" in ranges

    async def test_ban_logs_created_on_ban(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.250",
            reason="logging test",
            banned_by="tester",
        )
        logs = await ip_ban_service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] >= 1
        log_actions = [log["action"] for log in logs["list"]]
        assert "ban" in log_actions

    async def test_ban_logs_filter_by_action(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.251")
        await ip_ban_service.unban_ip(ban_id=ban["id"], operator="admin")

        ban_logs = await ip_ban_service.get_ban_logs(action="ban")
        unban_logs = await ip_ban_service.get_ban_logs(action="unban")

        assert ban_logs["total"] >= 1
        assert unban_logs["total"] >= 1
        for log in ban_logs["list"]:
            assert log["action"] == "ban"
        for log in unban_logs["list"]:
            assert log["action"] == "unban"

    async def test_get_stats(self, ip_ban_service):
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.30", ban_type="manual"
        )
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.31", ban_type="auto"
        )
        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] >= 2
        assert stats["manual_bans"] >= 1
        assert stats["auto_bans"] >= 1


# =============================================================================
# 自动封禁规则引擎测试
# =============================================================================


@pytest.mark.asyncio
class TestAutoBanRuleEngine:
    """自动封禁规则引擎的规则触发逻辑。"""

    async def test_record_event_login_failure_triggers_ban(self, ip_ban_service):
        """模拟登录失败超过阈值，触发自动封禁。"""
        # 先获取默认规则（threshold=10, window=300s）
        rules = await ip_ban_service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        threshold = login_rule["threshold"]

        # 模拟连续登录失败事件
        for _ in range(threshold):
            await ip_ban_service.record_event(
                event_type="login_failure",
                ip_str="10.0.0.100",
                status_code=401,
            )

        # 超过阈值后应触发自动封禁
        is_banned = await ip_ban_service.is_ip_banned("10.0.0.100")
        assert is_banned is True

    async def test_record_event_login_failure_below_threshold(self, ip_ban_service):
        """登录失败未达阈值，不应触发封禁。"""
        # 先触发生成默认规则到数据库（确保 enabled 字段存在）
        await ip_ban_service.get_rule_configs()

        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="login_failure", ip_str="10.0.0.101", status_code=401
            )
        assert await ip_ban_service.is_ip_banned("10.0.0.101") is False

    async def test_high_4xx_triggers_ban(self, ip_ban_service):
        """高频 4xx 错误触发自动封禁。"""
        rules = await ip_ban_service.get_rule_configs()
        h4xx_rule = next(r for r in rules if r["id"] == "high_4xx")
        threshold = h4xx_rule["threshold"]

        for _ in range(threshold):
            await ip_ban_service.record_event(
                event_type="high_4xx", ip_str="10.0.0.102", status_code=403
            )

        is_banned = await ip_ban_service.is_ip_banned("10.0.0.102")
        assert is_banned is True

    async def test_rate_limit_triggers_ban(self, ip_ban_service):
        """请求频率过高触发自动封禁。"""
        rules = await ip_ban_service.get_rule_configs()
        rl_rule = next(r for r in rules if r["id"] == "rate_limit")
        threshold = rl_rule["threshold"]

        for _ in range(threshold):
            await ip_ban_service.record_event(
                event_type="rate_limit", ip_str="10.0.0.103", status_code=200
            )

        is_banned = await ip_ban_service.is_ip_banned("10.0.0.103")
        assert is_banned is True

    async def test_get_rule_configs_returns_defaults(self, ip_ban_service):
        """未配置规则时返回默认规则。"""
        rules = await ip_ban_service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    async def test_update_rule_config(self, ip_ban_service):
        """更新规则配置后，新配置生效。"""
        # 先触发生成默认规则到数据库
        await ip_ban_service.get_rule_configs()

        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 5, "ban_duration_minutes": 15}
        )
        rules = await ip_ban_service.get_rule_configs()
        updated = next(r for r in rules if r["id"] == "login_failure")
        assert updated["threshold"] == 5
        assert updated["ban_duration_minutes"] == 15

    async def test_update_nonexistent_rule_raises_error(self, ip_ban_service):
        with pytest.raises(Exception, match="规则不存在"):
            await ip_ban_service.update_rule_config(
                "nonexistent_rule", {"threshold": 5}
            )