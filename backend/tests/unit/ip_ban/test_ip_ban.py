"""IpBanService 行为测试。

测试原则：
- 覆盖 CIDR 匹配、封禁管理、自动封禁引擎、边界条件
- 用内存数据库做真实交互
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.models import AutoBanRuleConfig, IpBan, IpBanLog
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr

# =============================================================================
# ip_matches_cidr 单元测试（纯函数，不需 DB）
# =============================================================================


class TestIpMatchesCidr:
    """测试 IP/CIDR 匹配逻辑。"""

    def test_ipv4_exact_match(self):
        """精确 IPv4 地址应匹配自身。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IPv4 地址在 CIDR 段内应匹配。"""
        assert ip_matches_cidr("192.168.1.50", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IPv4 地址不在 CIDR 段内不应匹配。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_single_ip(self):
        """不带掩码的纯 IP 地址应匹配自身。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.5") is True

    def test_ipv4_single_ip_non_match(self):
        """不带掩码的纯 IP 地址对不同 IP 应返回 False。"""
        assert ip_matches_cidr("10.0.0.6", "10.0.0.5") is False

    def test_ipv6_in_subnet(self):
        """IPv6 地址在 CIDR 段内应匹配。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_ipv6_outside_subnet(self):
        """IPv6 地址不在 CIDR 段内不应匹配。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db9::/32") is False
        )

    def test_invalid_ip_returns_false(self):
        """非法 IP 字符串应返回 False 而不是抛出异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """非法 CIDR 字符串应返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_ipv4_broadcast_address(self):
        """广播地址 (主机位全 1) 属于该子网。"""
        assert ip_matches_cidr("192.168.1.255", "192.168.1.0/24") is True

    def test_ipv4_network_address(self):
        """网络地址 (主机位全 0) 属于该子网。"""
        assert ip_matches_cidr("192.168.1.0", "192.168.1.0/24") is True

    def test_ipv4_large_cidr(self):
        """大段 CIDR（如 /8）应正确匹配。"""
        assert ip_matches_cidr("10.100.200.1", "10.0.0.0/8") is True

    def test_private_ip_not_in_public_range(self):
        """私有 IP 不应被误判为公网段。"""
        assert ip_matches_cidr("192.168.1.1", "172.16.0.0/12") is False


# =============================================================================
# IpBanService 封禁管理测试
# =============================================================================


class TestBanIp:
    """测试 ban_ip 方法。"""

    @pytest.mark.asyncio
    async def test_ban_ip_success(self, db_container):
        """正常封禁应返回封禁记录并写入日志。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="恶意扫描",
            banned_by="admin",
        )

        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["expires_at"] is None  # 永久封禁

        # 验证日志写入
        async with db_container.get("db")["session_factory"]() as session:
            logs = (await session.execute(__import__("sqlalchemy").select(IpBanLog))).scalars().all()  # noqa: E501
            assert len(logs) == 1
            assert logs[0].action == "ban"
            assert logs[0].ip_or_cidr == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_ban_ip_with_duration(self, db_container):
        """带时长的封禁应记录过期时间。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            duration_minutes=30,
        )

        assert result["expires_at"] is not None
        # 过期时间应在未来 30 分钟左右
        expires = datetime.fromisoformat(result["expires_at"])
        # SQLite 存储的 timezone-aware datetime 读取后可能丢失 tzinfo
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        assert expires.replace(tzinfo=None) > now

    @pytest.mark.asyncio
    async def test_ban_ip_duplicate_updates_existing(self, db_container):
        """重复封禁同一 IP 应更新已有记录而不是新建。"""
        service = IpBanService(db_container)
        result1 = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="首次封禁",
        )
        result2 = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="再次封禁（更新原因）",
        )

        assert result1["id"] == result2["id"]
        assert result2["reason"] == "再次封禁（更新原因）"

    @pytest.mark.asyncio
    async def test_ban_ip_cidr_range(self, db_container):
        """封禁整个 CIDR 段应正常工作。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.0/24",
            reason="封禁整个段",
            ban_type="auto",
            rule_id="test_rule",
        )

        assert result["ban_type"] == "auto"
        assert result["rule_id"] == "test_rule"


class TestUnbanIp:
    """测试 unban_ip 方法。"""

    @pytest.mark.asyncio
    async def test_unban_ip_success(self, db_container):
        """解封应标记 is_active=False 并写入日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="误封",
        )

        result = await service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

        # 验证日志
        async with db_container.get("db")["session_factory"]() as session:
            logs = (await session.execute(
                __import__("sqlalchemy").select(IpBanLog).where(IpBanLog.action == "unban")
            )).scalars().all()
            assert len(logs) == 1
            assert logs[0].operator == "admin"

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, db_container):
        """解封不存在的记录应抛出 404。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(ban_id=99999, operator="admin")
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "ban_not_found"


class TestBatchUnban:
    """测试 batch_unban 方法。"""

    @pytest.mark.asyncio
    async def test_batch_unban_multiple(self, db_container):
        """批量解封应正确解封多个 IP。"""
        service = IpBanService(db_container)
        ban1 = await service.ban_ip(ip_or_cidr="10.0.0.1")
        ban2 = await service.ban_ip(ip_or_cidr="10.0.0.2")
        ban3 = await service.ban_ip(ip_or_cidr="10.0.0.3")

        count = await service.batch_unban(
            ban_ids=[ban1["id"], ban2["id"], ban3["id"]],
            operator="admin",
        )
        assert count == 3

    @pytest.mark.asyncio
    async def test_batch_unban_partial(self, db_container):
        """批量解封中不存在的 ID 应被跳过。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")

        count = await service.batch_unban(
            ban_ids=[ban["id"], 99999],
            operator="admin",
        )
        assert count == 1  # 只有存在的被解封


class TestIsIpBanned:
    """测试 is_ip_banned 方法。"""

    @pytest.mark.asyncio
    async def test_banned_ip_returns_true(self, db_container):
        """被封禁的 IP 应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.100")
        assert await service.is_ip_banned("192.168.1.100") is True

    @pytest.mark.asyncio
    async def test_unbanned_ip_returns_false(self, db_container):
        """未被封禁的 IP 应返回 False。"""
        service = IpBanService(db_container)
        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_cidr_matches_banned_ip(self, db_container):
        """封禁 CIDR 段后，段内 IP 应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.0/24")
        assert await service.is_ip_banned("10.0.0.50") is True
        assert await service.is_ip_banned("10.0.0.100") is True

    @pytest.mark.asyncio
    async def test_expired_ban_returns_false(self, db_container):
        """过期的封禁记录不应被匹配。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="192.168.1.100",
            duration_minutes=-1,  # 负值立即过期（实际不会生效）
        )
        # 手动将封禁记录过期
        from sqlalchemy import select

        async with db_container.get("db")["session_factory"]() as session:
            result = await session.execute(select(IpBan).where(IpBan.ip_or_cidr == "192.168.1.100"))  # noqa: E501
            ban = result.scalar_one()
            ban.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        assert await service.is_ip_banned("192.168.1.100") is False

    @pytest.mark.asyncio
    async def test_inactive_ban_returns_false(self, db_container):
        """非活跃的封禁记录不应被匹配。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="192.168.1.100")
        await service.unban_ip(ban_id=ban["id"])
        assert await service.is_ip_banned("192.168.1.100") is False


class TestListBans:
    """测试 list_bans 方法。"""

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, db_container):
        """分页查询应返回正确数量和分页信息。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}")

        result = await service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, db_container):
        """按 ban_type 过滤应只返回对应类型的记录。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto")

        result = await service.list_bans(ban_type="manual")
        assert result["total"] == 1
        assert result["list"][0]["ban_type"] == "manual"

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_active(self, db_container):
        """按 is_active 过滤应只返回活跃/非活跃记录。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.ban_ip(ip_or_cidr="10.0.0.2")
        await service.unban_ip(ban_id=ban["id"])

        active = await service.list_bans(is_active=True)
        inactive = await service.list_bans(is_active=False)
        assert active["total"] == 1
        assert inactive["total"] == 1

    @pytest.mark.asyncio
    async def test_list_bans_keyword_search(self, db_container):
        """按关键词搜索应匹配 IP 或 CIDR 段。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1")
        await service.ban_ip(ip_or_cidr="10.0.0.1")

        result = await service.list_bans(keyword="192.168")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "192.168.1.1"


class TestGetBanLogs:
    """测试 get_ban_logs 方法。"""

    @pytest.mark.asyncio
    async def test_get_ban_logs_pagination(self, db_container):
        """操作日志应支持分页查询。"""
        service = IpBanService(db_container)
        for i in range(3):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}")

        result = await service.get_ban_logs(page=1, page_size=2)
        assert result["total"] == 3
        assert len(result["list"]) == 2

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, db_container):
        """按 action 过滤应只返回对应操作类型的日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.unban_ip(ban_id=ban["id"])

        ban_logs = await service.get_ban_logs(action="ban")
        unban_logs = await service.get_ban_logs(action="unban")
        assert ban_logs["total"] == 1
        assert unban_logs["total"] == 1


# =============================================================================
# 自动封禁规则引擎测试
# =============================================================================


class TestAutoBanRules:
    """测试自动封禁规则管理。"""

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, db_container):
        """未配置时 get_rule_configs 应返回默认规则。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()

        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_get_rule_configs_persists_defaults(self, db_container):
        """默认规则应在首次查询后持久化到数据库。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()

        # 再次查询，验证数据来自 DB
        async with db_container.get("db")["session_factory"]() as session:
            result = await session.execute(
                __import__("sqlalchemy").select(AutoBanRuleConfig).where(AutoBanRuleConfig.id == "login_failure")  # noqa: E501
            )
            rule = result.scalar_one_or_none()
            assert rule is not None
            assert rule.threshold == 10

    @pytest.mark.asyncio
    async def test_update_rule_config(self, db_container):
        """更新规则配置应生效。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()

        updated = await service.update_rule_config(
            "login_failure",
            {"threshold": 20, "ban_duration_minutes": 60},
        )
        assert updated["threshold"] == 20
        assert updated["ban_duration_minutes"] == 60

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises_error(self, db_container):
        """更新不存在的规则应抛出 404。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("non_existent_rule", {"threshold": 5})
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "rule_not_found"

    @pytest.mark.asyncio
    async def test_update_rule_ignores_unknown_fields(self, db_container):
        """更新规则时不应处理未允许的字段。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()

        updated = await service.update_rule_config(
            "login_failure",
            {"threshold": 15, "unknown_field": "should_be_ignored"},
        )
        assert updated["threshold"] == 15
        # 不应包含未知字段
        assert "unknown_field" not in updated


# =============================================================================
# 自动封禁事件触发测试
# =============================================================================


class TestRecordEvent:
    """测试 record_event 方法引发的自动封禁。"""

    @pytest.mark.asyncio
    async def test_record_event_counter_cleanup(self, db_container):
        """record_event 应触发计数器清理。"""
        service = IpBanService(db_container)
        # 直接写入过期计数器条目
        service._counters["login_failure:10.0.0.1"] = [(time.time() - 4000, 0)]
        service._last_cleanup = time.time() - 120  # 强制触发清理

        await service.record_event("login_failure", "10.0.0.1")
        assert "login_failure:10.0.0.1" in service._counters

    @pytest.mark.asyncio
    async def test_auto_ban_after_repeated_login_failures(self, db_container):
        """连续登录失败应触发自动封禁。"""
        service = IpBanService(db_container)
        # 先确保规则存在
        await service.get_rule_configs()

        # 模拟 10 次登录失败（阈值以上）
        ip = "10.0.0.99"
        for _ in range(12):
            await service.record_event("login_failure", ip)

        # 验证是否被自动封禁
        assert await service.is_ip_banned(ip) is True

    @pytest.mark.asyncio
    async def test_auto_ban_not_triggered_below_threshold(self, db_container):
        """登录失败次数未达阈值不应触发封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()

        ip = "10.0.0.98"
        # 仅 5 次失败（低于默认阈值 10）
        for _ in range(5):
            await service.record_event("login_failure", ip)

        assert await service.is_ip_banned(ip) is False

    @pytest.mark.asyncio
    async def test_high_4xx_auto_ban(self, db_container):
        """高频 4xx 请求应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()

        ip = "10.0.0.97"
        for _ in range(55):
            await service.record_event("high_4xx", ip, status_code=404)

        assert await service.is_ip_banned(ip) is True

    @pytest.mark.asyncio
    async def test_high_4xx_ignores_non_4xx(self, db_container):
        """4xx 规则应忽略非 4xx 状态码。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()

        ip = "10.0.0.96"
        # 200 状态码不应被 4xx 规则计数
        for _ in range(55):
            await service.record_event("high_4xx", ip, status_code=200)

        assert await service.is_ip_banned(ip) is False

    @pytest.mark.asyncio
    async def test_rate_limit_auto_ban(self, db_container):
        """请求频率过高应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()

        ip = "10.0.0.95"
        for _ in range(205):
            await service.record_event("rate_limit", ip)

        assert await service.is_ip_banned(ip) is True


# =============================================================================
# 统计信息测试
# =============================================================================


class TestGetStats:
    """测试 get_stats 方法。"""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, db_container):
        """无封禁记录时统计应全为零。"""
        service = IpBanService(db_container)
        stats = await service.get_stats()
        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0
        assert stats["today_bans"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, db_container):
        """有封禁记录时统计应正确。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto")
        await service.ban_ip(ip_or_cidr="10.0.0.3", ban_type="auto")

        stats = await service.get_stats()
        assert stats["total_bans"] == 3
        assert stats["auto_bans"] == 2
        assert stats["manual_bans"] == 1
        assert stats["today_bans"] == 3  # 今日新增


# =============================================================================
# 边界条件测试
# =============================================================================


class TestEdgeCases:
    """测试边界条件和异常场景。"""

    @pytest.mark.asyncio
    async def test_ban_ipv6_address(self, db_container):
        """IPv6 地址封禁应正常工作。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="2001:db8::1",
            reason="IPv6 恶意请求",
        )
        assert result["ip_or_cidr"] == "2001:db8::1"
        assert await service.is_ip_banned("2001:db8::1") is True

    @pytest.mark.asyncio
    async def test_ban_ipv6_cidr(self, db_container):
        """IPv6 CIDR 段封禁应正常工作。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="2001:db8::/32")
        assert await service.is_ip_banned("2001:db8::1") is True
        assert await service.is_ip_banned("2001:db8:ffff::1") is True

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, db_container):
        """get_active_ip_ranges 应返回所有活跃 IP/CIDR 段。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.0/24")
        await service.ban_ip(ip_or_cidr="192.168.1.1")

        ranges = await service.get_active_ip_ranges()
        assert "10.0.0.0/24" in ranges
        assert "192.168.1.1" in ranges

    @pytest.mark.asyncio
    async def test_counter_cleanup_removes_expired_entries(self, db_container):
        """计数器清理应移除过期条目。"""
        service = IpBanService(db_container)
        # 添加过期条目
        old_time = time.time() - 4000  # 超过 1 小时
        service._counters["old_key:10.0.0.1"] = [(old_time, 0)]
        service._last_cleanup = time.time() - 120  # 强制清理

        service._cleanup_counters()
        assert "old_key:10.0.0.1" not in service._counters