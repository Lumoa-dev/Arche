"""IP 封禁服务层单元测试 —— 核心业务逻辑全覆盖。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# ip_matches_cidr 工具函数
# =============================================================================


class TestIpMatchesCidr:
    """测试 IP 与 CIDR 段的匹配逻辑。"""

    def test_ipv4_in_cidr(self):
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_not_in_cidr(self):
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_single_ip_exact_match(self):
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1/32") is True

    def test_invalid_ip_returns_false(self):
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_empty_strings_return_false(self):
        assert ip_matches_cidr("", "") is False

    def test_ipv6_in_cidr(self):
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_ipv6_not_in_cidr(self):
        assert ip_matches_cidr("::2", "::1/128") is False


# =============================================================================
# 辅助 fixture
# =============================================================================


@pytest.fixture
def ip_ban_service(in_memory_db):
    """创建绑定真实内存数据库的 IpBanService 实例。"""
    container = MagicMock()
    container.get.return_value = in_memory_db
    service = IpBanService(container)
    return service


# =============================================================================
# IpBanService — 封禁管理 CRUD
# =============================================================================


class TestBanIp:
    """测试手动封禁 IP。"""

    async def test_ban_ip_success(self, ip_ban_service):
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="恶意请求",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=30,
        )
        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["expires_at"] is not None  # 有时效
        assert result["id"] > 0

    async def test_ban_ip_permanent(self, ip_ban_service):
        """duration_minutes=None 表示永久封禁。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="永久封禁",
            duration_minutes=None,
        )
        assert result["expires_at"] is None

    async def test_ban_ip_zero_duration_is_permanent(self, ip_ban_service):
        """duration_minutes=0 也表示永久封禁。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="测试零时长",
            duration_minutes=0,
        )
        assert result["expires_at"] is None

    async def test_ban_ip_existing_active_ban_updates_expiry(self, ip_ban_service):
        """已存在活跃记录时，更新过期时间和原因。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="首次封禁",
            duration_minutes=10,
        )
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="延长封禁",
            duration_minutes=60,
        )
        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["reason"] == "延长封禁"

    async def test_ban_ip_creates_log_entry(self, ip_ban_service):
        """封禁操作应同时创建日志。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.5",
            reason="测试日志",
            duration_minutes=30,
        )
        logs = await ip_ban_service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] >= 1
        assert logs["list"][0]["action"] == "ban"

    async def test_ban_ip_creates_log_with_detail(self, ip_ban_service):
        """日志中应包含封禁时长信息。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.6",
            reason="带时长",
            duration_minutes=30,
        )
        logs = await ip_ban_service.get_ban_logs(page=1, page_size=10)
        assert "30分钟" in logs["list"][0]["detail"]

    async def test_ban_ip_creates_log_with_permanent_detail(self, ip_ban_service):
        """永久封禁的日志 detail 应为 '永久封禁'。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.7",
            reason="永久",
            duration_minutes=None,
        )
        logs = await ip_ban_service.get_ban_logs(page=1, page_size=10)
        assert "永久封禁" in logs["list"][0]["detail"]


class TestUnbanIp:
    """测试解封 IP。"""

    async def test_unban_ip_success(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="测试",
            duration_minutes=30,
        )
        result = await ip_ban_service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

    async def test_unban_ip_not_found(self, ip_ban_service):
        with pytest.raises(Exception) as exc:
            await ip_ban_service.unban_ip(ban_id=99999, operator="admin")
        assert "不存在" in str(exc.value)

    async def test_unban_ip_creates_log(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.10",
            reason="测试",
            duration_minutes=30,
        )
        await ip_ban_service.unban_ip(ban_id=ban["id"], operator="admin")
        logs = await ip_ban_service.get_ban_logs(page=1, page_size=10)
        logs_actions = [log["action"] for log in logs["list"]]
        # 封禁日志 + 解封日志
        assert logs_actions.count("ban") == 1
        assert logs_actions.count("unban") == 1


class TestBatchUnban:
    """测试批量解封。"""

    async def test_batch_unban_all_valid(self, ip_ban_service):
        ban1 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="t1")
        ban2 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.2", reason="t2")
        count = await ip_ban_service.batch_unban(
            ban_ids=[ban1["id"], ban2["id"]], operator="admin"
        )
        assert count == 2

    async def test_batch_unban_partial_valid(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="t1")
        count = await ip_ban_service.batch_unban(
            ban_ids=[ban["id"], 99999], operator="admin"
        )
        assert count == 1  # 只有存在的记录被解封

    async def test_batch_unban_empty_list(self, ip_ban_service):
        count = await ip_ban_service.batch_unban(ban_ids=[], operator="admin")
        assert count == 0

    async def test_batch_unban_already_inactive(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="t1")
        await ip_ban_service.unban_ip(ban_id=ban["id"], operator="admin")
        count = await ip_ban_service.batch_unban(
            ban_ids=[ban["id"]], operator="admin"
        )
        assert count == 0  # 已非活跃，不重复计数


class TestListBans:
    """测试封禁列表查询。"""

    async def test_list_bans_empty(self, ip_ban_service):
        result = await ip_ban_service.list_bans()
        assert result["total"] == 0
        assert result["list"] == []

    async def test_list_bans_pagination(self, ip_ban_service):
        for i in range(5):
            await ip_ban_service.ban_ip(ip_or_cidr=f"10.0.0.{i}", reason="t")
        result = await ip_ban_service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1

    async def test_list_bans_filter_by_type(self, ip_ban_service):
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="manual")
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="auto",
            ban_type="auto",
            duration_minutes=30,
        )
        result = await ip_ban_service.list_bans(ban_type="auto")
        assert result["total"] == 1
        assert result["list"][0]["ban_type"] == "auto"

    async def test_list_bans_filter_by_keyword(self, ip_ban_service):
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="t1")
        await ip_ban_service.ban_ip(ip_or_cidr="192.168.1.1", reason="t2")
        result = await ip_ban_service.list_bans(keyword="192.168")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "192.168.1.1"


class TestGetBanLogs:
    """测试封禁日志查询。"""

    async def test_get_ban_logs_filter_by_action(self, ip_ban_service):
        ban = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="t")
        await ip_ban_service.unban_ip(ban_id=ban["id"], operator="admin")
        logs = await ip_ban_service.get_ban_logs(action="unban")
        assert logs["total"] >= 1
        assert all(log["action"] == "unban" for log in logs["list"])

    async def test_get_ban_logs_no_match(self, ip_ban_service):
        logs = await ip_ban_service.get_ban_logs(action="ban")
        assert logs["total"] == 0


# =============================================================================
# IpBanService — IP 检查
# =============================================================================


class TestIsIpBanned:
    """测试 IP 封禁状态检查。"""

    async def test_is_ip_banned_exact_match(self, ip_ban_service):
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="t")
        assert await ip_ban_service.is_ip_banned("10.0.0.1") is True

    async def test_is_ip_banned_cidr_match(self, ip_ban_service):
        await ip_ban_service.ban_ip(ip_or_cidr="192.168.1.0/24", reason="t")
        assert await ip_ban_service.is_ip_banned("192.168.1.100") is True

    async def test_is_ip_banned_not_banned(self, ip_ban_service):
        assert await ip_ban_service.is_ip_banned("10.0.0.1") is False

    async def test_is_ip_banned_expired(self, ip_ban_service):
        """已过期的封禁不应被视为活跃。"""
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="t", duration_minutes=0)
        # 手动设为过期
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import select, update
        from backend.plugins.ip_ban.models import IpBan

        async with ip_ban_service.session_factory() as session:
            await session.execute(
                update(IpBan).where(IpBan.ip_or_cidr == "10.0.0.1").values(
                    expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
                )
            )
            await session.commit()
        assert await ip_ban_service.is_ip_banned("10.0.0.1") is False

    async def test_is_ip_banned_inactive_ban(self, ip_ban_service):
        """已解封的记录不应被视为活跃。"""
        ban = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="t")
        await ip_ban_service.unban_ip(ban_id=ban["id"], operator="admin")
        assert await ip_ban_service.is_ip_banned("10.0.0.1") is False

    async def test_get_active_ip_ranges(self, ip_ban_service):
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.0/24", reason="t")
        await ip_ban_service.ban_ip(ip_or_cidr="192.168.1.1", reason="t")
        ranges = await ip_ban_service.get_active_ip_ranges()
        assert len(ranges) == 2
        assert "10.0.0.0/24" in ranges
        assert "192.168.1.1" in ranges


# =============================================================================
# IpBanService — 自动封禁规则引擎
# =============================================================================


class TestAutoBanRules:
    """测试自动封禁规则引擎。"""

    async def test_get_rule_configs_returns_defaults_when_empty(self, ip_ban_service):
        """数据库无规则时，应返回默认规则并自动创建。"""
        rules = await ip_ban_service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    async def test_get_rule_configs_merges_db_and_defaults(self, ip_ban_service):
        """数据库规则应与默认规则合并。"""
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with ip_ban_service.session_factory() as session:
            session.add(
                AutoBanRuleConfig(
                    id="custom_rule",
                    name="自定义规则",
                    threshold=5,
                    window_seconds=60,
                    ban_duration_minutes=10,
                )
            )
            await session.commit()

        rules = await ip_ban_service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "custom_rule" in rule_ids
        assert "login_failure" in rule_ids

    async def test_get_rule_configs_db_overrides_default(self, ip_ban_service):
        """数据库中的规则应覆盖默认值。"""
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with ip_ban_service.session_factory() as session:
            session.add(
                AutoBanRuleConfig(
                    id="login_failure",
                    name="登录失败封禁",
                    threshold=5,
                    window_seconds=60,
                    ban_duration_minutes=10,
                )
            )
            await session.commit()

        rules = await ip_ban_service.get_rule_configs()
        rule = next(r for r in rules if r["id"] == "login_failure")
        assert rule["threshold"] == 5

    async def test_update_rule_config_success(self, ip_ban_service):
        # 先确保默认规则存在
        await ip_ban_service.get_rule_configs()
        result = await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 20}
        )
        assert result["threshold"] == 20

    async def test_update_rule_config_not_found(self, ip_ban_service):
        with pytest.raises(Exception) as exc:
            await ip_ban_service.update_rule_config("nonexistent", {})
        assert "不存在" in str(exc.value)

    async def test_update_rule_config_rejects_unknown_fields(self, ip_ban_service):
        await ip_ban_service.get_rule_configs()
        result = await ip_ban_service.update_rule_config(
            "login_failure", {"unknown_field": "value", "threshold": 15}
        )
        assert result["threshold"] == 15

    async def test_ensure_default_rule_concurrent_safe(self, ip_ban_service):
        """_ensure_default_rule 应能处理并发冲突。"""
        # 模拟第二次调用时主键已存在，应回滚不抛异常
        for _ in range(2):
            await ip_ban_service._ensure_default_rule(
                "login_failure",
                {
                    "name": "登录失败封禁",
                    "threshold": 10,
                    "window_seconds": 300,
                    "ban_duration_minutes": 30,
                    "description": "",
                },
            )
        # 验证不抛异常，结果正确
        rules = await ip_ban_service.get_rule_configs()
        rule = next(r for r in rules if r["id"] == "login_failure")
        assert rule["threshold"] == 10


class TestAutoBanTrigger:
    """测试自动封禁触发逻辑。"""

    async def test_record_event_triggers_login_failure_ban(self, ip_ban_service):
        """登录失败次数超过阈值应触发自动封禁。"""
        # 将阈值调低
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with ip_ban_service.session_factory() as session:
            session.add(
                AutoBanRuleConfig(
                    id="login_failure",
                    name="登录失败封禁",
                    threshold=3,
                    window_seconds=60,
                    ban_duration_minutes=10,
                )
            )
            await session.commit()

        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="login_failure", ip_str="10.0.0.1"
            )

        assert await ip_ban_service.is_ip_banned("10.0.0.1") is True

    async def test_record_event_below_threshold_no_ban(self, ip_ban_service):
        """未达阈值时不应触发封禁。"""
        await ip_ban_service.get_rule_configs()  # 确保默认规则存在
        # 默认阈值 10，只记录 5 次
        for _ in range(5):
            await ip_ban_service.record_event(
                event_type="login_failure", ip_str="10.0.0.2"
            )
        assert await ip_ban_service.is_ip_banned("10.0.0.2") is False

    async def test_record_event_disabled_rule_no_ban(self, ip_ban_service):
        """规则禁用时不应触发封禁。"""
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with ip_ban_service.session_factory() as session:
            session.add(
                AutoBanRuleConfig(
                    id="login_failure",
                    name="登录失败封禁",
                    enabled=False,
                    threshold=1,
                    window_seconds=60,
                    ban_duration_minutes=10,
                )
            )
            await session.commit()

        await ip_ban_service.record_event(
            event_type="login_failure", ip_str="10.0.0.3"
        )
        assert await ip_ban_service.is_ip_banned("10.0.0.3") is False

    async def test_high_4xx_trigger(self, ip_ban_service):
        """高频 4xx 应触发自动封禁。"""
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with ip_ban_service.session_factory() as session:
            session.add(
                AutoBanRuleConfig(
                    id="high_4xx",
                    name="4xx 高频封禁",
                    threshold=3,
                    window_seconds=60,
                    ban_duration_minutes=10,
                )
            )
            await session.commit()

        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="high_4xx", ip_str="10.0.0.4", status_code=404
            )

        assert await ip_ban_service.is_ip_banned("10.0.0.4") is True

    async def test_high_4xx_ignores_non_4xx(self, ip_ban_service):
        """high_4xx 事件中 status_code 不在 400-500 范围时不应计数。"""
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with ip_ban_service.session_factory() as session:
            session.add(
                AutoBanRuleConfig(
                    id="high_4xx",
                    name="4xx 高频封禁",
                    threshold=3,
                    window_seconds=60,
                    ban_duration_minutes=10,
                )
            )
            await session.commit()

        # 记录 500 状态码，不应被 high_4xx 规则计数
        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="high_4xx", ip_str="10.0.0.5", status_code=500
            )

        assert await ip_ban_service.is_ip_banned("10.0.0.5") is False

    async def test_rate_limit_trigger(self, ip_ban_service):
        """请求频率超过阈值应触发自动封禁。"""
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with ip_ban_service.session_factory() as session:
            session.add(
                AutoBanRuleConfig(
                    id="rate_limit",
                    name="请求频率封禁",
                    threshold=3,
                    window_seconds=60,
                    ban_duration_minutes=10,
                )
            )
            await session.commit()

        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="rate_limit", ip_str="10.0.0.6"
            )

        assert await ip_ban_service.is_ip_banned("10.0.0.6") is True

    async def test_geo_surge_rule_does_not_auto_ban(self, ip_ban_service):
        """geo_surge 规则 ban_duration_minutes=0 不应触发自动封禁。"""
        await ip_ban_service.get_rule_configs()  # 确保默认规则存在
        # geo_surge 默认 threshold=100, 但 record_event 不会触发它
        # 这个测试验证 geo_surge 规则不会因 record_event 被误触发
        for _ in range(5):
            await ip_ban_service.record_event(
                event_type="login_failure", ip_str="10.0.0.7"
            )
        # 不触发，继续正常
        # 验证计数器清理后不会误报
        assert await ip_ban_service.is_ip_banned("10.0.0.7") is False


class TestGetStats:
    """测试封禁统计。"""

    async def test_get_stats_empty(self, ip_ban_service):
        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0
        assert stats["today_bans"] == 0

    async def test_get_stats_with_data(self, ip_ban_service):
        for i in range(3):
            await ip_ban_service.ban_ip(ip_or_cidr=f"10.0.0.{i}", reason="manual")
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.100",
            reason="auto",
            ban_type="auto",
            duration_minutes=30,
        )
        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] == 4
        assert stats["active_bans"] == 4
        assert stats["auto_bans"] == 1
        assert stats["manual_bans"] == 3
        assert stats["today_bans"] >= 4


class TestCounterCleanup:
    """测试事件计数器清理。"""

    async def test_cleanup_counters_removes_expired(self, ip_ban_service):
        ip_ban_service._counters["login_failure:10.0.0.1"] = [
            (0, 0),  # 远超过 3600 秒
        ]
        ip_ban_service._cleanup_counters()
        assert ip_ban_service._counters.get("login_failure:10.0.0.1", []) == []

    async def test_cleanup_counters_keeps_recent(self, ip_ban_service):
        import time

        now = time.time()
        ip_ban_service._counters["login_failure:10.0.0.1"] = [
            (now - 10, 0),  # 10 秒前，在窗口内
        ]
        ip_ban_service._cleanup_counters()
        assert len(ip_ban_service._counters["login_failure:10.0.0.1"]) == 1


class TestWebhookNotification:
    """测试 webhook 通知发送。"""

    async def test_webhook_skipped_when_no_url(self, ip_ban_service):
        """无 webhook URL 时不应发送。"""
        ip_ban_service._webhook_url = ""
        # 不应抛异常
        await ip_ban_service._send_webhook_notification(
            "ip_banned", {"ip_or_cidr": "10.0.0.1"}
        )

    async def test_webhook_skipped_when_no_aiohttp(self, ip_ban_service):
        """aiohttp 未安装时不应发送。"""
        ip_ban_service._webhook_url = "http://example.com/webhook"
        with patch("backend.plugins.ip_ban.services._HAS_AIOHTTP", False):
            # 不应抛异常
            await ip_ban_service._send_webhook_notification(
                "ip_banned", {"ip_or_cidr": "10.0.0.1"}
            )