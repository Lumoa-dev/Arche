"""IP 封禁服务单元测试。

测试覆盖：CIDR 匹配、CRUD 操作、自动封禁规则引擎、统计、批量操作。
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# ip_matches_cidr 工具函数
# =============================================================================


class TestIpMatchesCidr:
    """测试 CIDR 匹配逻辑。"""

    def test_ipv4_exact_match(self):
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv6_in_subnet(self):
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_invalid_ip_returns_false(self):
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_non_strict_cidr_allows_host_bits(self):
        """非严格模式允许主机位不为零的 CIDR 表示法。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.0/24") is True


# =============================================================================
# IpBanService — 基本 CRUD
# =============================================================================


@pytest.fixture
def ip_ban_service(db_container):
    """创建 IpBanService 实例，注入真实内存数据库。"""
    return IpBanService(db_container)


@pytest.mark.asyncio
class TestBanIp:
    """测试封禁操作。"""

    async def test_ban_ip_creates_ban_and_log(self, ip_ban_service):
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
            ban_type="manual",
            banned_by="admin",
        )
        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["reason"] == "测试封禁"

    async def test_ban_ip_with_expiry(self, ip_ban_service):
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            duration_minutes=30,
            banned_by="admin",
        )
        assert result["is_active"] is True
        assert result["expires_at"] is not None

    async def test_ban_ip_permanent_when_duration_zero(self, ip_ban_service):
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            duration_minutes=0,
        )
        assert result["expires_at"] is None

    async def test_ban_ip_permanent_when_duration_none(self, ip_ban_service):
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.3",
            duration_minutes=None,
        )
        assert result["expires_at"] is None

    async def test_ban_ip_updates_existing_ban(self, ip_ban_service):
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.100",
            reason="first",
            banned_by="admin",
        )
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.100",
            reason="updated",
            duration_minutes=60,
            banned_by="admin",
        )
        assert result["reason"] == "updated"
        assert result["expires_at"] is not None

    async def test_ban_ip_creates_ip_ban_log_entry(self, ip_ban_service):
        await ip_ban_service.ban_ip(
            ip_or_cidr="172.16.0.1",
            reason="test",
            banned_by="admin",
        )
        logs = await ip_ban_service.get_ban_logs(action="ban")
        assert logs["total"] == 1
        assert logs["list"][0]["action"] == "ban"
        assert logs["list"][0]["operator"] == "admin"


@pytest.mark.asyncio
class TestUnbanIp:
    """测试解封操作。"""

    async def test_unban_ip_deactivates_ban(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.10",
            reason="test",
            banned_by="admin",
        )
        result = await ip_ban_service.unban_ip(ban["id"], operator="admin")
        assert result["is_active"] is False

    async def test_unban_nonexistent_ban_raises_error(self, ip_ban_service):
        with pytest.raises(AppError) as excinfo:
            await ip_ban_service.unban_ip(9999, operator="admin")
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "ban_not_found"

    async def test_unban_creates_unban_log(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.11",
            reason="test",
            banned_by="admin",
        )
        await ip_ban_service.unban_ip(ban["id"], operator="admin")
        logs = await ip_ban_service.get_ban_logs(action="unban")
        assert logs["total"] == 1
        assert logs["list"][0]["action"] == "unban"


@pytest.mark.asyncio
class TestBatchUnban:
    """测试批量解封。"""

    async def test_batch_unban_multiple_bans(self, ip_ban_service):
        ban1 = await ip_ban_service.ban_ip("10.0.0.20", banned_by="admin")
        ban2 = await ip_ban_service.ban_ip("10.0.0.21", banned_by="admin")
        ban3 = await ip_ban_service.ban_ip("10.0.0.22", banned_by="admin")

        count = await ip_ban_service.batch_unban(
            [ban1["id"], ban2["id"], ban3["id"]], operator="admin"
        )
        assert count == 3

    async def test_batch_unban_skips_already_inactive(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip("10.0.0.30", banned_by="admin")
        await ip_ban_service.unban_ip(ban["id"], operator="admin")

        count = await ip_ban_service.batch_unban([ban["id"]], operator="admin")
        assert count == 0

    async def test_batch_unban_skips_nonexistent_ids(self, ip_ban_service):
        count = await ip_ban_service.batch_unban([999, 1000], operator="admin")
        assert count == 0


@pytest.mark.asyncio
class TestListBans:
    """测试封禁列表查询。"""

    async def test_list_bans_pagination(self, ip_ban_service):
        for i in range(5):
            await ip_ban_service.ban_ip(f"10.0.0.{100 + i}", banned_by="admin")

        page1 = await ip_ban_service.list_bans(page=1, page_size=2)
        assert page1["total"] == 5
        assert len(page1["list"]) == 2
        assert page1["page"] == 1
        assert page1["page_size"] == 2

    async def test_list_bans_filter_by_type(self, ip_ban_service):
        await ip_ban_service.ban_ip("10.0.0.50", ban_type="manual", banned_by="admin")
        await ip_ban_service.ban_ip("10.0.0.51", ban_type="auto", banned_by="admin")

        manual = await ip_ban_service.list_bans(ban_type="manual")
        auto = await ip_ban_service.list_bans(ban_type="auto")
        assert manual["total"] == 1
        assert auto["total"] == 1

    async def test_list_bans_filter_by_keyword(self, ip_ban_service):
        await ip_ban_service.ban_ip("192.168.1.1", banned_by="admin")
        await ip_ban_service.ban_ip("10.0.0.1", banned_by="admin")

        result = await ip_ban_service.list_bans(keyword="192.168")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "192.168.1.1"

    async def test_list_bans_filter_by_active(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip("10.0.0.60", banned_by="admin")
        await ip_ban_service.ban_ip("10.0.0.61", banned_by="admin")
        await ip_ban_service.unban_ip(ban["id"], operator="admin")

        active = await ip_ban_service.list_bans(is_active=True)
        inactive = await ip_ban_service.list_bans(is_active=False)
        assert active["total"] == 1
        assert inactive["total"] == 1


@pytest.mark.asyncio
class TestGetBanLogs:
    """测试封禁日志查询。"""

    async def test_get_ban_logs_pagination(self, ip_ban_service):
        for i in range(5):
            await ip_ban_service.ban_ip(f"10.0.0.{200 + i}", banned_by="admin")

        page1 = await ip_ban_service.get_ban_logs(page=1, page_size=2)
        assert page1["total"] == 5
        assert len(page1["list"]) == 2

    async def test_get_ban_logs_filter_by_action(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip("10.0.0.70", banned_by="admin")
        await ip_ban_service.unban_ip(ban["id"], operator="admin")

        bans = await ip_ban_service.get_ban_logs(action="ban")
        unbans = await ip_ban_service.get_ban_logs(action="unban")
        assert bans["total"] == 1
        assert unbans["total"] == 1

    async def test_get_ban_logs_serializes_datetime(self, ip_ban_service):
        await ip_ban_service.ban_ip("10.0.0.80", banned_by="admin")
        logs = await ip_ban_service.get_ban_logs()
        assert logs["list"][0]["created_at"] is not None
        assert "T" in logs["list"][0]["created_at"]


# =============================================================================
# IpBanService — 自动封禁规则引擎
# =============================================================================


@pytest.mark.asyncio
class TestAutoBanRules:
    """测试自动封禁规则引擎。"""

    async def test_get_rule_configs_returns_defaults(self, ip_ban_service):
        rules = await ip_ban_service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert rule_ids == {"login_failure", "high_4xx", "rate_limit", "geo_surge"}

    async def test_get_rule_configs_persists_defaults_to_db(self, ip_ban_service):
        await ip_ban_service.get_rule_configs()
        rules = await ip_ban_service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 10
        assert login_rule["window_seconds"] == 300
        assert login_rule["ban_duration_minutes"] == 30

    async def test_update_rule_config_updates_fields(self, ip_ban_service):
        await ip_ban_service.get_rule_configs()
        updated = await ip_ban_service.update_rule_config(
            "login_failure",
            {"threshold": 5, "ban_duration_minutes": 15},
        )
        assert updated["threshold"] == 5
        assert updated["ban_duration_minutes"] == 15

    async def test_update_rule_config_rejects_unknown_fields(self, ip_ban_service):
        await ip_ban_service.get_rule_configs()
        updated = await ip_ban_service.update_rule_config(
            "login_failure",
            {"unknown_field": "value", "threshold": 20},
        )
        assert updated["threshold"] == 20

    async def test_update_nonexistent_rule_raises_error(self, ip_ban_service):
        with pytest.raises(AppError) as excinfo:
            await ip_ban_service.update_rule_config("nonexistent", {"threshold": 5})
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "rule_not_found"

    async def test_record_event_login_failure_triggers_ban(self, ip_ban_service):
        """登录失败次数超过阈值应触发自动封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 3, "ban_duration_minutes": 10}
        )

        for _ in range(3):
            await ip_ban_service.record_event("login_failure", "10.0.0.200")

        is_banned = await ip_ban_service.is_ip_banned("10.0.0.200")
        assert is_banned is True

    async def test_record_event_login_failure_below_threshold(self, ip_ban_service):
        """低于阈值的登录失败不应触发封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 10, "ban_duration_minutes": 10}
        )

        for _ in range(3):
            await ip_ban_service.record_event("login_failure", "10.0.0.201")

        is_banned = await ip_ban_service.is_ip_banned("10.0.0.201")
        assert is_banned is False

    async def test_record_event_login_failure_rule_disabled(self, ip_ban_service):
        """规则禁用时不应触发封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config("login_failure", {"enabled": False})

        for _ in range(20):
            await ip_ban_service.record_event("login_failure", "10.0.0.202")

        is_banned = await ip_ban_service.is_ip_banned("10.0.0.202")
        assert is_banned is False

    async def test_record_event_high_4xx_triggers_ban(self, ip_ban_service):
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "high_4xx", {"threshold": 3, "ban_duration_minutes": 10}
        )

        for _ in range(3):
            await ip_ban_service.record_event("high_4xx", "10.0.0.210", status_code=404)

        is_banned = await ip_ban_service.is_ip_banned("10.0.0.210")
        assert is_banned is True

    async def test_record_event_rate_limit_triggers_ban(self, ip_ban_service):
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "rate_limit", {"threshold": 3, "ban_duration_minutes": 10}
        )

        for _ in range(3):
            await ip_ban_service.record_event("rate_limit", "10.0.0.220")

        is_banned = await ip_ban_service.is_ip_banned("10.0.0.220")
        assert is_banned is True

    async def test_counters_cleanup_after_expiry(self, ip_ban_service):
        """过期计数器应被清理，不影响后续计数。"""
        # 直接操作内部计数器，模拟过期数据
        old_time = time.time() - 4000  # 超过 1 小时
        ip_ban_service._counters["login_failure:10.0.0.230"] = [
            (old_time, 0),
        ]
        ip_ban_service._cleanup_counters()
        assert "login_failure:10.0.0.230" not in ip_ban_service._counters


# =============================================================================
# IpBanService — is_ip_banned 检查
# =============================================================================


@pytest.mark.asyncio
class TestIsIpBanned:
    """测试 IP 封禁状态检查。"""

    async def test_is_ip_banned_returns_true_for_banned_ip(self, ip_ban_service):
        await ip_ban_service.ban_ip("10.0.0.100", banned_by="admin")
        assert await ip_ban_service.is_ip_banned("10.0.0.100") is True

    async def test_is_ip_banned_returns_false_for_free_ip(self, ip_ban_service):
        assert await ip_ban_service.is_ip_banned("10.0.0.101") is False

    async def test_is_ip_banned_returns_false_after_unban(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip("10.0.0.102", banned_by="admin")
        await ip_ban_service.unban_ip(ban["id"], operator="admin")
        assert await ip_ban_service.is_ip_banned("10.0.0.102") is False

    async def test_is_ip_banned_matches_cidr_range(self, ip_ban_service):
        await ip_ban_service.ban_ip("192.168.1.0/24", banned_by="admin")
        assert await ip_ban_service.is_ip_banned("192.168.1.50") is True
        assert await ip_ban_service.is_ip_banned("192.168.2.1") is False

    async def test_is_ip_banned_respects_expiry(self, ip_ban_service):
        """已过期的封禁不应再被检查到。"""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await ip_ban_service.ban_ip(
            "10.0.0.110",
            duration_minutes=0,  # 永久封禁
            banned_by="admin",
        )

        # 获取刚创建的 ban 记录，手动修改 expires_at 为过去
        bans = await ip_ban_service.list_bans(is_active=True)
        ban_id = bans["list"][0]["id"]

        from backend.plugins.ip_ban.models import IpBan
        from sqlalchemy import select

        async with ip_ban_service.session_factory() as session:
            ban = await session.execute(select(IpBan).where(IpBan.id == ban_id))
            ban = ban.scalar_one()
            ban.expires_at = past
            await session.commit()

        assert await ip_ban_service.is_ip_banned("10.0.0.110") is False

    async def test_get_active_ip_ranges_returns_cidr_list(self, ip_ban_service):
        await ip_ban_service.ban_ip("10.0.0.0/24", banned_by="admin")
        await ip_ban_service.ban_ip("192.168.1.1", banned_by="admin")

        ranges = await ip_ban_service.get_active_ip_ranges()
        assert "10.0.0.0/24" in ranges
        assert "192.168.1.1" in ranges


# =============================================================================
# IpBanService — 统计
# =============================================================================


@pytest.mark.asyncio
class TestGetStats:
    """测试统计功能。"""

    async def test_get_stats_returns_counts(self, ip_ban_service):
        for i in range(3):
            await ip_ban_service.ban_ip(f"10.0.0.{200 + i}", banned_by="admin")

        await ip_ban_service.ban_ip(
            "10.0.0.210", ban_type="auto", banned_by="admin"
        )

        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] == 4
        assert stats["active_bans"] == 4
        assert stats["manual_bans"] == 3
        assert stats["auto_bans"] == 1
        assert stats["today_bans"] >= 4

    async def test_get_stats_after_unban(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip("10.0.0.220", banned_by="admin")
        await ip_ban_service.unban_ip(ban["id"], operator="admin")

        stats = await ip_ban_service.get_stats()
        assert stats["active_bans"] == 0
        assert stats["total_bans"] == 1


# =============================================================================
# IpBanService — Webhook 通知
# =============================================================================


@pytest.mark.asyncio
class TestWebhookNotification:
    """测试 Webhook 通知（aiohttp 不可用时不应报错）。"""

    async def test_webhook_silent_when_no_url(self, ip_ban_service):
        """没有配置 webhook URL 时，ban_ip 不应报错。"""
        result = await ip_ban_service.ban_ip("10.0.0.240", banned_by="admin")
        assert result["is_active"] is True

    @patch("backend.plugins.ip_ban.services._HAS_AIOHTTP", False)
    async def test_webhook_silent_when_aiohttp_missing(self, ip_ban_service):
        """aiohttp 不可用时，ban_ip 不应报错。"""
        ip_ban_service._webhook_url = "https://example.com/webhook"
        result = await ip_ban_service.ban_ip("10.0.0.241", banned_by="admin")
        assert result["is_active"] is True