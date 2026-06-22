"""IP 封禁插件测试 —— CIDR 匹配、封禁 CRUD、规则引擎、统计。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


class TestIpMatchesCIDR:
    """测试 CIDR 匹配工具函数。"""

    def test_ipv4_exact_match(self):
        """IPv4 精确匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IPv4 在子网内。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IPv4 不在子网内。"""
        assert ip_matches_cidr("10.0.1.5", "10.0.0.0/24") is False

    def test_ipv6_match(self):
        """IPv6 匹配。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True

    def test_ipv6_no_match(self):
        """IPv6 不匹配。"""
        assert ip_matches_cidr("2001:db9::1", "2001:db8::/32") is False

    def test_invalid_ip_returns_false(self):
        """无效 IP 返回 False。"""
        assert ip_matches_cidr("not-an-ip", "10.0.0.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 返回 False。"""
        assert ip_matches_cidr("10.0.0.1", "not-a-cidr") is False

    def test_cidr_with_host_bits(self):
        """CIDR 带主机位时 strict=False 仍可匹配。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.0/24") is True

    def test_broadcast_address(self):
        """广播地址匹配。"""
        assert ip_matches_cidr("10.0.0.255", "10.0.0.0/24") is True

    def test_network_address(self):
        """网络地址匹配。"""
        assert ip_matches_cidr("10.0.0.0", "10.0.0.0/24") is True


class TestIpBanServiceInit:
    """测试 IpBanService 初始化。"""

    def test_init_sets_up_counters(self):
        """初始化时计数器为空字典。"""
        container = MagicMock()
        container.get.return_value = MagicMock()
        service = IpBanService(container)
        assert service._counters == {}


class TestIpBanService:
    """测试 IpBanService 核心功能。"""

    @pytest.fixture
    def service(self, db_container):
        """创建带内存数据库的 IpBanService 实例。"""
        return IpBanService(db_container)

    @pytest.mark.asyncio
    async def test_is_ip_banned_empty(self):
        """无封禁记录时 is_ip_banned 返回 False。"""
        container = MagicMock()
        container.get.return_value = MagicMock()
        service = IpBanService(container)

        # 模拟 session_factory 返回空结果
        mock_session = AsyncMock()
        # session.execute 返回 AsyncResult → .scalars() 是 sync 方法 → .all() 返回 []
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__.return_value = mock_session

        db_mock = {"session_factory": MagicMock(return_value=mock_session)}
        service.session_factory = db_mock["session_factory"]

        result = await service.is_ip_banned("10.0.0.1")
        assert result is False

    @pytest.mark.asyncio
    async def test_ban_and_check_ip(self, service):
        """封禁 IP 后 is_ip_banned 返回 True。"""
        await service.ban_ip("10.0.0.55", reason="test ban")
        assert await service.is_ip_banned("10.0.0.55") is True

    @pytest.mark.asyncio
    async def test_ban_unban_ip(self, service):
        """解封后 is_ip_banned 返回 False。"""
        result = await service.ban_ip("10.0.0.66", reason="test ban")
        ban_id = result["id"]
        assert await service.is_ip_banned("10.0.0.66") is True

        await service.unban_ip(ban_id, operator="admin")
        assert await service.is_ip_banned("10.0.0.66") is False

    @pytest.mark.asyncio
    async def test_ban_with_cidr(self, service):
        """封禁 CIDR 段后段内 IP 被封禁。"""
        await service.ban_ip("192.168.1.0/24", reason="block subnet")
        assert await service.is_ip_banned("192.168.1.100") is True
        assert await service.is_ip_banned("192.168.2.1") is False

    @pytest.mark.asyncio
    async def test_duplicate_ban_updates_existing(self, service):
        """重复封禁同 IP 更新已有记录而非新建。"""
        await service.ban_ip("10.0.0.77", reason="first ban")
        await service.ban_ip("10.0.0.77", reason="second ban", duration_minutes=30)
        assert await service.is_ip_banned("10.0.0.77") is True

    @pytest.mark.asyncio
    async def test_ban_with_duration(self, service):
        """带有效期的封禁在过期后自动失效。"""
        await service.ban_ip(
            "10.0.0.88",
            reason="temporary ban",
            duration_minutes=0,
        )
        # duration=0 表示永久封禁（expires_at=None）
        assert await service.is_ip_banned("10.0.0.88") is True

    @pytest.mark.asyncio
    async def test_ban_with_expiry_in_past(self, service):
        """过期时间已过的封禁不影响 is_ip_banned。"""
        from backend.plugins.ip_ban.models import IpBan

        # 直接创建已过期的封禁记录
        async with service.session_factory() as session:
            ban = IpBan(
                ip_or_cidr="10.0.0.99",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            session.add(ban)
            await session.commit()

        assert await service.is_ip_banned("10.0.0.99") is False

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, service):
        """分页查询封禁列表。"""
        for i in range(5):
            await service.ban_ip(f"10.0.0.{i}", reason=f"ban {i}")

        result = await service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

        result2 = await service.list_bans(page=3, page_size=2)
        assert len(result2["list"]) == 1

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, service):
        """按封禁类型筛选。"""
        await service.ban_ip("10.0.1.1", reason="manual", ban_type="manual")

        # 模拟自动封禁（通过规则引擎直接操作）
        from backend.plugins.ip_ban.models import IpBan

        async with service.session_factory() as session:
            ban = IpBan(ip_or_cidr="10.0.2.1", ban_type="auto", reason="auto ban")
            session.add(ban)
            await session.commit()

        result = await service.list_bans(ban_type="manual")
        assert len(result["list"]) == 1
        assert result["list"][0]["ban_type"] == "manual"

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_keyword(self, service):
        """按关键词（IP/CIDR）筛选。"""
        await service.ban_ip("10.0.1.1", reason="spam attack")
        await service.ban_ip("10.0.2.1", reason="brute force")

        # 关键词匹配 ip_or_cidr 字段
        result = await service.list_bans(keyword="10.0.1")
        assert len(result["list"]) == 1

        result = await service.list_bans(keyword="10.0")
        assert len(result["list"]) == 2

    @pytest.mark.asyncio
    async def test_batch_unban(self, service):
        """批量解封返回正确数量。"""
        r1 = await service.ban_ip("10.0.3.1", reason="batch test")
        r2 = await service.ban_ip("10.0.3.2", reason="batch test")
        r3 = await service.ban_ip("10.0.3.3", reason="batch test")
        ban_ids = [r1["id"], r2["id"], r3["id"]]

        count = await service.batch_unban(ban_ids, operator="admin")
        assert count == 3

        assert await service.is_ip_banned("10.0.3.1") is False
        assert await service.is_ip_banned("10.0.3.2") is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises(self, service):
        """解封不存在记录抛出 AppError。"""
        from backend.core.middleware import AppError

        with pytest.raises(AppError, match="封禁记录不存在"):
            await service.unban_ip(9999, operator="admin")

    @pytest.mark.asyncio
    async def test_get_stats(self, service):
        """统计信息正确。"""
        await service.ban_ip("10.0.5.1", reason="auto", ban_type="auto")
        await service.ban_ip("10.0.5.2", reason="manual")

        stats = await service.get_stats()
        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 2

    @pytest.mark.asyncio
    async def test_get_ban_logs(self, service):
        """封禁日志查询正确。"""
        await service.ban_ip("10.0.6.1", reason="log test")
        await service.ban_ip("10.0.6.2", reason="log test 2")

        logs = await service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] == 2
        assert len(logs["list"]) == 2
        assert logs["list"][0]["action"] == "ban"

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, service):
        """按操作类型筛选封禁日志。"""
        r = await service.ban_ip("10.0.7.1", reason="unban log test")
        await service.unban_ip(r["id"], operator="admin")

        ban_logs = await service.get_ban_logs(action="ban")
        unban_logs = await service.get_ban_logs(action="unban")
        assert len(ban_logs["list"]) == 1
        assert len(unban_logs["list"]) == 1

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, service):
        """获取活跃 IP 段列表。"""
        await service.ban_ip("10.0.8.0/24", reason="range")
        await service.ban_ip("10.0.9.1", reason="single")

        ranges = await service.get_active_ip_ranges()
        assert "10.0.8.0/24" in ranges
        assert "10.0.9.1" in ranges

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges_excludes_expired(self, service):
        """已过期封禁不出现在活跃列表中。"""
        from backend.plugins.ip_ban.models import IpBan

        async with service.session_factory() as session:
            ban = IpBan(
                ip_or_cidr="10.0.10.1",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            session.add(ban)
            await session.commit()

        ranges = await service.get_active_ip_ranges()
        assert "10.0.10.1" not in ranges


class TestRuleEngine:
    """测试自动封禁规则引擎。"""

    @pytest.fixture
    def service(self, db_container):
        return IpBanService(db_container)

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, service):
        """首次获取规则配置时返回默认值并写入数据库。"""
        rules = await service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_update_rule_config(self, service):
        """更新规则配置后生效。"""
        await service.get_rule_configs()

        updated = await service.update_rule_config(
            "login_failure", {"threshold": 5, "enabled": False}
        )
        assert updated["threshold"] == 5
        assert updated["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises(self, service):
        """更新不存在规则抛出 AppError。"""
        from backend.core.middleware import AppError

        with pytest.raises(AppError, match="规则不存在"):
            await service.update_rule_config("nonexistent", {"threshold": 5})

    @pytest.mark.asyncio
    async def test_update_rule_ignores_invalid_fields(self, service):
        """更新时忽略不在白名单的字段。"""
        await service.get_rule_configs()
        updated = await service.update_rule_config(
            "login_failure", {"threshold": 3, "invalid_field": "should_ignore"}
        )
        assert updated["threshold"] == 3
        # invalid_field 不应出现在结果中
        assert "invalid_field" not in updated

    @pytest.mark.asyncio
    async def test_cleanup_counters(self, service):
        """清理过期计数器条目。"""
        import time

        service._counters["test:1.2.3.4"] = [
            (time.time() - 4000, 1),  # 超过 3600s 过期
            (time.time() - 100, 2),  # 不过期
        ]
        service._cleanup_counters()
        assert "test:1.2.3.4" in service._counters
        assert len(service._counters["test:1.2.3.4"]) == 1

    @pytest.mark.asyncio
    async def test_cleanup_removes_empty_keys(self, service):
        """清理后空 key 被删除。"""
        import time

        service._counters["expired:1.2.3.4"] = [(time.time() - 4000, 1)]
        service._cleanup_counters()
        assert "expired:1.2.3.4" not in service._counters

    @pytest.mark.asyncio
    async def test_record_event_triggers_rule_check(self, service):
        """record_event 触发规则检查并在达到阈值时自动封禁。"""
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"threshold": 3, "window_seconds": 60, "ban_duration_minutes": 10},
        )

        # 记录 3 次登录失败事件
        for _ in range(3):
            await service.record_event("login_failure", "10.0.100.1")

        assert await service.is_ip_banned("10.0.100.1") is True

    @pytest.mark.asyncio
    async def test_record_event_below_threshold(self, service):
        """事件数低于阈值不触发封禁。"""
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 10, "window_seconds": 60}
        )

        for _ in range(3):
            await service.record_event("login_failure", "10.0.100.2")

        assert await service.is_ip_banned("10.0.100.2") is False

    @pytest.mark.asyncio
    async def test_high_4xx_rule_triggers(self, service):
        """高频 4xx 规则在达到阈值时触发封禁。"""
        await service.get_rule_configs()
        await service.update_rule_config(
            "high_4xx",
            {"threshold": 3, "window_seconds": 60, "ban_duration_minutes": 10},
        )

        for _ in range(3):
            await service.record_event("high_4xx", "10.0.200.1", 403)

        assert await service.is_ip_banned("10.0.200.1") is True

    @pytest.mark.asyncio
    async def test_high_4xx_ignores_non_4xx(self, service):
        """高频 4xx 规则忽略非 4xx 状态码。"""
        await service.get_rule_configs()
        await service.update_rule_config(
            "high_4xx",
            {"threshold": 3, "window_seconds": 60},
        )

        for _ in range(3):
            await service.record_event("high_4xx", "10.0.200.2", 200)

        assert await service.is_ip_banned("10.0.200.2") is False

    @pytest.mark.asyncio
    async def test_disabled_rule_no_autoban(self, service):
        """禁用的规则不触发自动封禁。"""
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"threshold": 3, "enabled": False},
        )

        for _ in range(5):
            await service.record_event("login_failure", "10.0.100.3")

        assert await service.is_ip_banned("10.0.100.3") is False

    @pytest.mark.asyncio
    async def test_rate_limit_rule(self, service):
        """请求频率规则在达到阈值时触发封禁。"""
        await service.get_rule_configs()
        await service.update_rule_config(
            "rate_limit",
            {"threshold": 5, "window_seconds": 60, "ban_duration_minutes": 10},
        )

        for _ in range(5):
            await service.record_event("rate_limit", "10.0.200.3")

        assert await service.is_ip_banned("10.0.200.3") is True

    @pytest.mark.asyncio
    async def test_webhook_notification_skipped_without_url(self, service):
        """无 webhook URL 时不发送通知（不抛出异常）。"""
        service._webhook_url = ""
        # 不应抛出异常
        await service._send_webhook_notification("ip_banned", {"ip_or_cidr": "test"})