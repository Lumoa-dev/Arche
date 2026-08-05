"""IpBanService 行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现
- 数据库交互用内存 SQLite
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# IP 匹配工具函数 行为测试
# =============================================================================


class TestIpMatchesCidr:
    """测试 ip_matches_cidr 工具函数。"""

    def test_ipv4_in_cidr_matches(self):
        """IPv4 地址在 CIDR 段内应返回 True。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_cidr_returns_false(self):
        """IPv4 地址不在 CIDR 段内应返回 False。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_exact_match(self):
        """精确 IP 匹配应返回 True。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1") is True

    def test_invalid_ip_returns_false(self):
        """无效 IP 地址应返回 False 而不是抛出异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 段应返回 False 而不是抛出异常。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_ipv6_in_cidr_matches(self):
        """IPv6 地址在 CIDR 段内应返回 True。"""
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_single_host_cidr(self):
        """/32 精确匹配应正常工作。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.5/32") is True

    def test_cidr_with_zero_host(self):
        """网络地址本身应匹配。"""
        assert ip_matches_cidr("192.168.1.0", "192.168.1.0/24") is True

    def test_cidr_broadcast_address(self):
        """广播地址应匹配。"""
        assert ip_matches_cidr("192.168.1.255", "192.168.1.0/24") is True


# =============================================================================
# BloomFilter 行为测试
# =============================================================================


class TestBloomFilter:
    """测试布隆过滤器行为。"""

    def test_contains_returns_false_for_empty(self):
        """空过滤器应返回 False。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("192.168.1.1") is False

    def test_contains_returns_true_for_added(self):
        """添加过的元素应返回 True。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_contains_multiple_items(self):
        """多个元素应都能被检测到。"""
        bf = BloomFilter(size=10000)
        items = ["10.0.0.1", "10.0.0.2", "10.0.0.3", "192.168.1.0/24"]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item) is True

    def test_clear_resets_filter(self):
        """clear() 后 contains 应返回 False。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_false_positive_rate(self):
        """小容量过滤器的假阳性率应在可接受范围内。"""
        bf = BloomFilter(size=1000)
        # 添加 50 个元素
        for i in range(50):
            bf.add(f"10.0.0.{i}")
        # 用 100 个未添加的元素测试假阳性率
        false_positives = sum(
            1 for i in range(100, 200) if bf.contains(f"10.0.0.{i}")
        )
        # 假阳性率应低于 10%（实际小容量下约 5%）
        assert false_positives < 10


# =============================================================================
# LRUSet 行为测试
# =============================================================================


class TestLRUSet:
    """测试 LRU 缓存集合行为。"""

    def test_contains_returns_false_for_empty(self):
        """空缓存应返回 False。"""
        cache = LRUSet(maxsize=5)
        assert cache.contains("10.0.0.1") is False

    def test_contains_returns_true_for_added(self):
        """添加过的元素应返回 True。"""
        cache = LRUSet(maxsize=5)
        cache.add("10.0.0.1")
        assert cache.contains("10.0.0.1") is True

    def test_evicts_oldest_when_full(self):
        """超过 maxsize 应淘汰最旧元素。"""
        cache = LRUSet(maxsize=3)
        cache.add("A")
        cache.add("B")
        cache.add("C")
        cache.add("D")  # 应淘汰 A
        assert cache.contains("A") is False
        assert cache.contains("B") is True
        assert cache.contains("C") is True
        assert cache.contains("D") is True

    def test_recently_accessed_is_not_evicted(self):
        """最近访问的元素应被移到末尾，不被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("A")
        cache.add("B")
        cache.add("C")
        # 访问 A，使其成为最近使用的
        cache.contains("A")  # 移到末尾
        cache.add("D")  # 应淘汰 B
        assert cache.contains("A") is True
        assert cache.contains("B") is False
        assert cache.contains("D") is True

    def test_remove_works(self):
        """remove() 应移除元素。"""
        cache = LRUSet(maxsize=5)
        cache.add("10.0.0.1")
        cache.remove("10.0.0.1")
        assert cache.contains("10.0.0.1") is False

    def test_clear_works(self):
        """clear() 应清空所有元素。"""
        cache = LRUSet(maxsize=5)
        cache.add("A")
        cache.add("B")
        cache.clear()
        assert cache.contains("A") is False
        assert cache.contains("B") is False

    def test_remove_nonexistent_does_not_raise(self):
        """移除不存在的元素不应抛出异常。"""
        cache = LRUSet(maxsize=5)
        cache.remove("nonexistent")  # 不应抛出异常


# =============================================================================
# IpBanService 封禁/解封行为测试
# =============================================================================


class TestBanAndUnban:
    """测试封禁和解封行为。"""

    @pytest.mark.asyncio
    async def test_ban_ip_creates_active_ban(self, db_container):
        """封禁 IP 应创建活跃封禁记录。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="Test ban",
            ban_type="manual",
            banned_by="admin",
        )
        assert result["ip_or_cidr"] == "10.0.0.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_ip_with_duration_sets_expiry(self, db_container):
        """带时长的封禁应设置过期时间。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="Temporary ban",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=30,
        )
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_ip_duplicate_returns_existing(self, db_container):
        """重复封禁同一 IP 应返回已有记录。"""
        service = IpBanService(db_container)
        result1 = await service.ban_ip(
            ip_or_cidr="10.0.0.3", reason="First ban", banned_by="admin"
        )
        result2 = await service.ban_ip(
            ip_or_cidr="10.0.0.3", reason="Second ban", banned_by="admin"
        )
        assert result1["id"] == result2["id"]

    @pytest.mark.asyncio
    async def test_unban_ip_deactivates_ban(self, db_container):
        """解封应使封禁记录变为非活跃。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="10.0.0.4", reason="To be unbanned", banned_by="admin"
        )
        result = await service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, db_container):
        """解封不存在的记录应抛出错误。"""
        service = IpBanService(db_container)
        from backend.core.middleware import AppError

        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(ban_id=99999, operator="admin")
        assert excinfo.value.code == "ban_not_found"
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_unban_returns_count(self, db_container):
        """批量解封应返回实际解封数量。"""
        service = IpBanService(db_container)
        ban1 = await service.ban_ip(ip_or_cidr="10.0.0.5", banned_by="admin")
        ban2 = await service.ban_ip(ip_or_cidr="10.0.0.6", banned_by="admin")
        await service.ban_ip(ip_or_cidr="10.0.0.7", banned_by="admin")

        count = await service.batch_unban(
            ban_ids=[ban1["id"], ban2["id"]], operator="admin"
        )
        assert count == 2


# =============================================================================
# IpBanService 查询行为测试
# =============================================================================


class TestListBans:
    """测试封禁列表查询行为。"""

    @pytest.mark.asyncio
    async def test_list_bans_returns_paginated_results(self, db_container):
        """分页查询应返回正确结构。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}", banned_by="admin")

        result = await service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, db_container):
        """按封禁类型过滤应正确。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.1", ban_type="manual", banned_by="admin"
        )
        await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            ban_type="auto",
            reason="auto",
            banned_by="system",
        )

        result = await service.list_bans(ban_type="auto")
        assert result["total"] == 1
        assert result["list"][0]["ban_type"] == "auto"

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_keyword(self, db_container):
        """按关键词搜索应正确。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", banned_by="admin")
        await service.ban_ip(ip_or_cidr="192.168.1.1", banned_by="admin")

        result = await service.list_bans(keyword="192.168")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_active_status(self, db_container):
        """按活跃状态过滤应正确。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", banned_by="admin")
        await service.unban_ip(ban_id=ban["id"], operator="admin")

        result = await service.list_bans(is_active=False)
        assert result["total"] == 1


# =============================================================================
# IpBanService 自动封禁规则引擎 行为测试
# =============================================================================


class TestAutoBanRules:
    """测试自动封禁规则引擎。"""

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, db_container):
        """未配置时获取规则应返回默认值。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_update_rule_config_updates_threshold(self, db_container):
        """更新规则阈值应生效。"""
        service = IpBanService(db_container)
        # 先调用 get_rule_configs 确保默认规则已写入数据库
        await service.get_rule_configs()
        result = await service.update_rule_config(
            "login_failure", {"threshold": 20}
        )
        assert result["threshold"] == 20

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises_error(self, db_container):
        """更新不存在的规则应抛出错误。"""
        service = IpBanService(db_container)
        from backend.core.middleware import AppError

        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("nonexistent_rule", {"threshold": 5})
        assert excinfo.value.code == "rule_not_found"
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_record_event_does_not_raise(self, db_container):
        """记录事件不应抛出异常。"""
        service = IpBanService(db_container)
        # 先确保规则已写入数据库
        await service.get_rule_configs()
        # 记录少量事件，不应触发封禁
        await service.record_event("login_failure", "10.0.0.1")
        await service.record_event("rate_limit", "10.0.0.2")
        # 无异常即通过

    @pytest.mark.asyncio
    async def test_record_event_triggers_auto_ban(self, db_container):
        """超过阈值的事件应触发自动封禁。"""
        service = IpBanService(db_container)

        # 先确保默认规则写入数据库，再调低阈值
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 3, "ban_duration_minutes": 10}
        )

        # 记录 3 次登录失败，应触发自动封禁
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.99")

        # 验证 IP 已被封禁
        is_banned = await service.is_ip_banned("10.0.0.99")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_high_4xx_triggers_auto_ban(self, db_container):
        """高频 4xx 事件应触发自动封禁。"""
        service = IpBanService(db_container)

        await service.get_rule_configs()
        await service.update_rule_config(
            "high_4xx", {"threshold": 3, "ban_duration_minutes": 10}
        )

        # 记录 3 次 4xx 事件
        for _ in range(3):
            await service.record_event("high_4xx", "10.0.0.88", status_code=404)

        is_banned = await service.is_ip_banned("10.0.0.88")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_disabled_rule_does_not_trigger(self, db_container):
        """禁用的规则不应触发自动封禁。"""
        service = IpBanService(db_container)

        # 先确保默认规则写入数据库，再禁用规则
        await service.get_rule_configs()
        await service.update_rule_config("login_failure", {"enabled": False})

        # 记录 20 次登录失败
        for _ in range(20):
            await service.record_event("login_failure", "10.0.0.77")

        is_banned = await service.is_ip_banned("10.0.0.77")
        assert is_banned is False


# =============================================================================
# IpBanService IP 检查行为测试
# =============================================================================


class TestIsIpBanned:
    """测试 IP 封禁检查行为。"""

    @pytest.mark.asyncio
    async def test_unbanned_ip_returns_false(self, db_container):
        """未封禁的 IP 应返回 False。"""
        service = IpBanService(db_container)
        is_banned = await service.is_ip_banned("10.0.0.1")
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_banned_ip_returns_true(self, db_container):
        """已封禁的 IP 应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", banned_by="admin")
        is_banned = await service.is_ip_banned("10.0.0.1")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_banned_cidr_matches_subnet(self, db_container):
        """封禁 CIDR 段后，段内 IP 应被匹配。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.0/24", banned_by="admin")
        assert await service.is_ip_banned("192.168.1.50") is True
        assert await service.is_ip_banned("192.168.2.1") is False

    @pytest.mark.asyncio
    async def test_unbanned_ip_no_longer_banned(self, db_container):
        """解封后 IP 应返回 False。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", banned_by="admin")
        await service.unban_ip(ban_id=ban["id"], operator="admin")
        is_banned = await service.is_ip_banned("10.0.0.1")
        assert is_banned is False


# =============================================================================
# IpBanService 统计行为测试
# =============================================================================


class TestGetStats:
    """测试封禁统计行为。"""

    @pytest.mark.asyncio
    async def test_get_stats_returns_correct_counts(self, db_container):
        """统计应返回正确的计数。"""
        service = IpBanService(db_container)

        # 手动封禁 2 个
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual", banned_by="admin")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="manual", banned_by="admin")

        stats = await service.get_stats()
        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 2
        assert stats["manual_bans"] == 2
        assert stats["auto_bans"] == 0


# =============================================================================
# IpBanService 操作日志行为测试
# =============================================================================


class TestGetBanLogs:
    """测试封禁操作日志查询行为。"""

    @pytest.mark.asyncio
    async def test_ban_and_unban_create_logs(self, db_container):
        """封禁和解封应创建操作日志。"""
        service = IpBanService(db_container)

        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", banned_by="admin")
        await service.unban_ip(ban_id=ban["id"], operator="admin")

        logs = await service.get_ban_logs()
        assert logs["total"] == 2  # 一条 ban 日志 + 一条 unban 日志

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, db_container):
        """按操作类型过滤日志应正确。"""
        service = IpBanService(db_container)

        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", banned_by="admin")
        await service.unban_ip(ban_id=ban["id"], operator="admin")

        ban_logs = await service.get_ban_logs(action="ban")
        unban_logs = await service.get_ban_logs(action="unban")
        assert ban_logs["total"] == 1
        assert unban_logs["total"] == 1


# =============================================================================
# IpBanService 活跃 IP 范围行为测试
# =============================================================================


class TestGetActiveIpRanges:
    """测试获取活跃 IP 范围行为。"""

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, db_container):
        """应返回所有活跃的 IP/CIDR。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", banned_by="admin")
        await service.ban_ip(ip_or_cidr="192.168.1.0/24", banned_by="admin")

        ranges = await service.get_active_ip_ranges()
        assert "10.0.0.1" in ranges
        assert "192.168.1.0/24" in ranges
        assert len(ranges) == 2