"""IP 封禁插件单元测试。

测试覆盖：
- ip_matches_cidr 工具函数（IPv4/IPv6/CIDR 匹配）
- BloomFilter 数据结构
- LRUSet 缓存结构
- IpBanService 核心业务逻辑（封禁/解封/批量/查询/自动规则引擎）
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr

# =============================================================================
# ip_matches_cidr 工具函数
# =============================================================================


class TestIpMatchesCidr:
    """测试 IP 匹配 CIDR 的各种场景。"""

    def test_ipv4_exact_match(self):
        """精确 IPv4 匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IPv4 在子网内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IPv4 不在子网内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_single_ip(self):
        """不带掩码的 CIDR 视为 /32。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1") is True
        assert ip_matches_cidr("10.0.0.2", "10.0.0.1") is False

    def test_ipv6_match(self):
        """IPv6 地址匹配。"""
        assert ip_matches_cidr("::1", "::1/128") is True
        assert ip_matches_cidr("::2", "::1/128") is False

    def test_ipv6_in_subnet(self):
        """IPv6 在子网内。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_invalid_ip_returns_false(self):
        """无效 IP 字符串返回 False 不抛异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 字符串返回 False 不抛异常。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_cidr_with_non_strict_mask(self):
        """非严格模式 CIDR（如 10.0.0.1/8 自动修正为 10.0.0.0/8）。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1/8") is True


# =============================================================================
# BloomFilter 数据结构
# =============================================================================


class TestBloomFilter:
    """测试布隆过滤器的基本操作。"""

    def test_contains_after_add(self):
        """添加后应能检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains_not_added(self):
        """未添加的项不应被检测到（允许假阳性但概率极低）。"""
        bf = BloomFilter(size=10000)
        bf.add("10.0.0.1")
        assert bf.contains("10.0.0.1") is True
        # 另一个未添加的项大概率返回 False
        assert bf.contains("192.168.1.1") is False

    def test_clear_removes_all(self):
        """clear 后所有项应丢失。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False
        assert bf.contains("10.0.0.1") is False

    def test_multiple_items(self):
        """多个不同项同时存在。"""
        bf = BloomFilter(size=10000)
        items = [f"10.0.0.{i}" for i in range(100)]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item) is True


# =============================================================================
# LRUSet 缓存结构
# =============================================================================


class TestLRUSet:
    """测试 LRU 集合的行为。"""

    def test_add_and_contains(self):
        """添加后应能检测到。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_contains_not_added(self):
        """未添加的项应返回 False。"""
        cache = LRUSet(maxsize=10)
        cache.add("10.0.0.1")
        assert cache.contains("192.168.1.1") is False

    def test_lru_eviction(self):
        """超过 maxsize 应淘汰最久未使用的项。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 "a"
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_recently_used_preserved(self):
        """最近访问的项应被保留。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 "a" 使其变为最近使用
        cache.contains("a")
        cache.add("d")  # 应淘汰 "b"
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_remove(self):
        """remove 应移除指定项。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.remove("a")
        assert cache.contains("a") is False
        assert cache.contains("b") is True

    def test_remove_nonexistent(self):
        """移除不存在的项不应抛异常。"""
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")  # 不抛异常即可

    def test_clear(self):
        """clear 应清空所有项。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False


# =============================================================================
# IpBanService 基础操作
# =============================================================================


class TestIpBanServiceBan:
    """测试封禁操作。"""

    @pytest.mark.asyncio
    async def test_ban_ip_success(self, db_container):
        """正常封禁应返回封禁记录并写入日志。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="恶意攻击",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=60,
        )

        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["reason"] == "恶意攻击"
        assert result["is_active"] is True
        assert result["expires_at"] is not None

        # 验证日志写入
        logs = await service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] == 1
        assert logs["list"][0]["action"] == "ban"

    @pytest.mark.asyncio
    async def test_ban_ip_permanent(self, db_container):
        """永久封禁（不传 duration_minutes）不应设置过期时间。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="永久封禁",
            ban_type="manual",
            banned_by="admin",
        )

        assert result["expires_at"] is None
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_duplicate_ban_updates_existing(self, db_container):
        """重复封禁同一 IP 应更新已有记录。"""
        service = IpBanService(db_container)
        result1 = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="首次封禁",
            ban_type="manual",
            duration_minutes=30,
        )
        result2 = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="更新封禁",
            ban_type="manual",
            duration_minutes=120,
        )

        # 应为同一记录（id 相同）
        assert result1["id"] == result2["id"]
        assert result2["reason"] == "更新封禁"

    @pytest.mark.asyncio
    async def test_ban_ip_with_cidr(self, db_container):
        """封禁 CIDR 段。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.0.0/16",
            reason="封禁整个段",
            ban_type="manual",
        )
        assert result["ip_or_cidr"] == "192.168.0.0/16"
        assert result["is_active"] is True


class TestIpBanServiceUnban:
    """测试解封操作。"""

    @pytest.mark.asyncio
    async def test_unban_ip_success(self, db_container):
        """正常解封应标记为非活跃并写入日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
        )

        result = await service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

        # 验证日志
        logs = await service.get_ban_logs(action="unban")
        assert logs["total"] == 1

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, db_container):
        """解封不存在的记录应抛异常。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(ban_id=9999, operator="admin")
        assert excinfo.value.code == "ban_not_found"
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_unban(self, db_container):
        """批量解封。"""
        service = IpBanService(db_container)
        ban1 = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试1")
        ban2 = await service.ban_ip(ip_or_cidr="10.0.0.2", reason="测试2")
        await service.ban_ip(ip_or_cidr="10.0.0.3", reason="测试3")

        count = await service.batch_unban(
            ban_ids=[ban1["id"], ban2["id"]], operator="admin"
        )
        assert count == 2

        # 验证已解封
        bans = await service.list_bans(page=1, page_size=10)
        active_count = sum(1 for b in bans["list"] if b["is_active"])
        assert active_count == 1  # 只有 10.0.0.3 仍活跃


class TestIpBanServiceQuery:
    """测试封禁查询。"""

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, db_container):
        """分页查询封禁列表。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(
                ip_or_cidr=f"10.0.0.{i}",
                reason=f"测试{i}",
            )

        page1 = await service.list_bans(page=1, page_size=2)
        assert page1["total"] == 5
        assert len(page1["list"]) == 2
        assert page1["page"] == 1
        assert page1["page_size"] == 2

        page2 = await service.list_bans(page=2, page_size=2)
        assert len(page2["list"]) == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, db_container):
        """按类型过滤封禁列表。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="手动", ban_type="manual")
        await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="自动",
            ban_type="auto",
            rule_id="rate_limit",
        )

        auto_bans = await service.list_bans(ban_type="auto")
        assert auto_bans["total"] == 1
        assert auto_bans["list"][0]["ban_type"] == "auto"

        manual_bans = await service.list_bans(ban_type="manual")
        assert manual_bans["total"] == 1
        assert manual_bans["list"][0]["ban_type"] == "manual"

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_keyword(self, db_container):
        """按关键词搜索 IP/CIDR。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1", reason="test")
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")

        result = await service.list_bans(keyword="192.168")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, db_container):
        """按操作类型过滤日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")
        await service.unban_ip(ban_id=ban["id"], operator="admin")

        ban_logs = await service.get_ban_logs(action="ban")
        assert ban_logs["total"] == 1
        assert ban_logs["list"][0]["action"] == "ban"

        unban_logs = await service.get_ban_logs(action="unban")
        assert unban_logs["total"] == 1
        assert unban_logs["list"][0]["action"] == "unban"


class TestIpBanServiceIsBanned:
    """测试 IP 封禁检查。"""

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_true_for_banned_ip(self, db_container):
        """被封禁的 IP 应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="test",
            duration_minutes=60,
        )

        assert await service.is_ip_banned("192.168.1.1") is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_for_clean_ip(self, db_container):
        """未封禁的 IP 应返回 False。"""
        service = IpBanService(db_container)
        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_cidr_match(self, db_container):
        """CIDR 段内的 IP 应被匹配。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="192.168.0.0/16",
            reason="封禁段",
        )

        assert await service.is_ip_banned("192.168.1.1") is True
        assert await service.is_ip_banned("192.168.2.100") is True
        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_expired_ban_not_active(self, db_container):
        """已过期的封禁不应匹配。"""
        service = IpBanService(db_container)
        # 使用已过期的封禁
        await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="短期封禁",
            duration_minutes=0,  # 立即过期
        )

        # 手动将 expires_at 设为过去
        from backend.plugins.ip_ban.models import IpBan
        from sqlalchemy import select

        async with db_container.get("db")["session_factory"]() as session:
            result = await session.execute(select(IpBan).where(IpBan.ip_or_cidr == "10.0.0.1"))
            ban = result.scalar_one()
            ban.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, db_container):
        """获取活跃 IP 段列表。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test", duration_minutes=60)
        await service.ban_ip(ip_or_cidr="192.168.0.0/24", reason="test", duration_minutes=60)

        ranges = await service.get_active_ip_ranges()
        assert len(ranges) == 2
        assert "10.0.0.1" in ranges
        assert "192.168.0.0/24" in ranges


class TestIpBanServiceStats:
    """测试封禁统计。"""

    @pytest.mark.asyncio
    async def test_get_stats(self, db_container):
        """统计应准确反映封禁状态。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="手动", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="手动", ban_type="manual")
        ban3 = await service.ban_ip(
            ip_or_cidr="10.0.0.3",
            reason="自动",
            ban_type="auto",
            rule_id="rate_limit",
        )
        # 解封一个
        await service.unban_ip(ban_id=ban3["id"], operator="admin")

        stats = await service.get_stats()
        assert stats["total_bans"] == 3
        assert stats["active_bans"] == 2  # 10.0.0.3 被解封
        assert stats["auto_bans"] == 1
        assert stats["manual_bans"] == 2


class TestIpBanServiceAutoBanRules:
    """测试自动封禁规则引擎。"""

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, db_container):
        """未配置规则时应返回默认规则。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()

        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_update_rule_config(self, db_container):
        """更新规则配置应持久化。"""
        service = IpBanService(db_container)
        # 先触发默认规则创建
        await service.get_rule_configs()

        updated = await service.update_rule_config(
            "login_failure",
            {"threshold": 20, "ban_duration_minutes": 60},
        )
        assert updated["threshold"] == 20
        assert updated["ban_duration_minutes"] == 60

        # 验证持久化
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 20
        assert login_rule["ban_duration_minutes"] == 60

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises_error(self, db_container):
        """更新不存在的规则应抛异常。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("nonexistent_rule", {"threshold": 10})
        assert excinfo.value.code == "rule_not_found"

    @pytest.mark.asyncio
    async def test_record_event_triggers_login_failure_ban(self, db_container):
        """登录失败事件超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)

        # 设置低阈值以便测试
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"threshold": 3, "window_seconds": 60, "ban_duration_minutes": 30},
        )

        # 模拟 3 次登录失败
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.1", 401)

        # 验证 IP 已被自动封禁
        is_banned = await service.is_ip_banned("10.0.0.1")
        assert is_banned is True

        # 验证封禁记录类型为 auto
        bans = await service.list_bans(ban_type="auto")
        assert len(bans["list"]) >= 1

    @pytest.mark.asyncio
    async def test_record_event_triggers_rate_limit_ban(self, db_container):
        """高频请求超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)

        await service.get_rule_configs()
        await service.update_rule_config(
            "rate_limit",
            {"threshold": 5, "window_seconds": 60, "ban_duration_minutes": 10},
        )

        # 模拟 5 次请求
        for _ in range(5):
            await service.record_event("rate_limit", "10.0.0.2", 200)

        is_banned = await service.is_ip_banned("10.0.0.2")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_triggers_high_4xx_ban(self, db_container):
        """高频 4xx 超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)

        await service.get_rule_configs()
        await service.update_rule_config(
            "high_4xx",
            {"threshold": 3, "window_seconds": 60, "ban_duration_minutes": 60},
        )

        # 模拟 3 次 4xx 错误
        for _ in range(3):
            await service.record_event("high_4xx", "10.0.0.3", 404)

        is_banned = await service.is_ip_banned("10.0.0.3")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_below_threshold_no_ban(self, db_container):
        """未达阈值不应触发封禁。"""
        service = IpBanService(db_container)

        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"threshold": 10, "window_seconds": 60, "ban_duration_minutes": 30},
        )

        # 仅 3 次失败，低于阈值
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.4", 401)

        is_banned = await service.is_ip_banned("10.0.0.4")
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_disabled_rule_does_not_trigger(self, db_container):
        """禁用的规则不应触发自动封禁。"""
        service = IpBanService(db_container)

        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"enabled": False, "threshold": 1, "window_seconds": 60},
        )

        # 即使超过阈值，但规则禁用
        await service.record_event("login_failure", "10.0.0.5", 401)

        is_banned = await service.is_ip_banned("10.0.0.5")
        assert is_banned is False