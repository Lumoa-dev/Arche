"""IpBanService 行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现
- 用内存数据库做真实交互（通过 db_container）
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# CIDR 匹配 行为测试
# =============================================================================


class TestIpMatchesCidr:
    """测试 CIDR 匹配工具函数。"""

    @pytest.mark.parametrize(
        "ip_str, cidr_str, expected",
        [
            ("192.168.1.1", "192.168.1.0/24", True),
            ("192.168.2.1", "192.168.1.0/24", False),
            ("10.0.0.5", "10.0.0.0/8", True),
            ("172.16.0.1", "10.0.0.0/8", False),
            ("::1", "::1/128", True),
            ("::2", "::1/128", False),
            ("2001:db8::1", "2001:db8::/32", True),
            ("2001:db9::1", "2001:db8::/32", False),
        ],
    )
    def test_cidr_matching(self, ip_str, cidr_str, expected):
        """IPv4 和 IPv6 的 CIDR 匹配应正确。"""
        assert ip_matches_cidr(ip_str, cidr_str) == expected

    @pytest.mark.parametrize(
        "ip_str, cidr_str",
        [
            ("not_an_ip", "192.168.1.0/24"),
            ("192.168.1.1", "invalid_cidr"),
            ("", "10.0.0.0/8"),
            ("999.999.999.999", "10.0.0.0/8"),
        ],
    )
    def test_invalid_input_returns_false(self, ip_str, cidr_str):
        """无效的 IP 或 CIDR 输入应返回 False。"""
        assert ip_matches_cidr(ip_str, cidr_str) is False


# =============================================================================
# BloomFilter 行为测试
# =============================================================================


class TestBloomFilter:
    """测试布隆过滤器的基本行为。"""

    def test_add_and_contains(self):
        """添加的元素应能被检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")
        assert bf.contains("192.168.1.1") is True
        assert bf.contains("10.0.0.1") is True

    def test_contains_unknown(self):
        """未添加的元素应返回 False。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("10.0.0.99") is False

    def test_clear_removes_all(self):
        """clear() 后所有元素应不可见。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_empty_filter_contains_nothing(self):
        """空过滤器对所有元素返回 False。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("any_ip") is False

    def test_large_filter_handles_many_items(self):
        """大容量过滤器应能处理大量元素。"""
        bf = BloomFilter(size=100_000)
        items = [f"10.0.0.{i}" for i in range(100)]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item) is True


# =============================================================================
# LRUSet 行为测试
# =============================================================================


class TestLRUSet:
    """测试 LRU 缓存集合行为。"""

    def test_add_and_contains(self):
        """添加的元素应能被检测到。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_contains_unknown(self):
        """未添加的元素应返回 False。"""
        cache = LRUSet(maxsize=10)
        assert cache.contains("10.0.0.1") is False

    def test_remove(self):
        """remove() 后元素应不可见。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        cache.remove("192.168.1.1")
        assert cache.contains("192.168.1.1") is False

    def test_eviction_when_full(self):
        """超过 maxsize 时应淘汰最旧元素。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 a
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_contains_moves_to_end(self):
        """contains() 命中应把元素移到末尾，防止被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 a，使它成为最近使用
        cache.contains("a")
        cache.add("d")  # 应淘汰 b（a 最近被访问过）
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("d") is True

    def test_clear_removes_all(self):
        """clear() 后所有元素应不可见。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False

    def test_remove_nonexistent_does_not_raise(self):
        """删除不存在的元素不应抛出异常。"""
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")  # 不应抛出


# =============================================================================
# IpBanService 行为测试
# =============================================================================


class TestIpBanService:
    """测试封禁服务的基本操作。"""

    @pytest.mark.asyncio
    async def test_ban_ip_creates_active_ban(self, db_container):
        """封禁 IP 应创建一条活跃的封禁记录。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
            ban_type="manual",
            banned_by="admin",
        )
        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["banned_by"] == "admin"

    @pytest.mark.asyncio
    async def test_ban_ip_with_duration_sets_expiry(self, db_container):
        """带时长的封禁应设置过期时间。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            duration_minutes=30,
        )
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_ip_without_duration_is_permanent(self, db_container):
        """不带时长的封禁应没有过期时间。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="永久封禁",
        )
        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_ban_existing_active_updates(self, db_container):
        """再次封禁已活跃的 IP 应更新记录而非新建。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1", reason="首次封禁")
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1", reason="再次封禁", duration_minutes=60
        )
        # 只应有一条记录
        assert result["reason"] == "再次封禁"
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_true_for_banned_ip(self, db_container):
        """被封禁的 IP 应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1")
        assert await service.is_ip_banned("192.168.1.1") is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_for_unknown_ip(self, db_container):
        """未封禁的 IP 应返回 False。"""
        service = IpBanService(db_container)
        assert await service.is_ip_banned("10.0.0.99") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_matches_cidr(self, db_container):
        """CIDR 封禁应匹配段内所有 IP。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.0/24")
        assert await service.is_ip_banned("192.168.1.100") is True
        assert await service.is_ip_banned("192.168.2.1") is False

    @pytest.mark.asyncio
    async def test_unban_ip_marks_inactive(self, db_container):
        """解封后记录应标记为 inactive。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="192.168.1.1")
        result = await service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, db_container):
        """解封不存在的记录应抛出 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(ban_id=99999, operator="admin")
        assert excinfo.value.code == "ban_not_found"
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_unban_multiple(self, db_container):
        """批量解封应正确解封多条记录。"""
        service = IpBanService(db_container)
        b1 = await service.ban_ip(ip_or_cidr="10.0.0.1")
        b2 = await service.ban_ip(ip_or_cidr="10.0.0.2")
        b3 = await service.ban_ip(ip_or_cidr="10.0.0.3")

        count = await service.batch_unban(
            ban_ids=[b1["id"], b2["id"]], operator="admin"
        )
        assert count == 2

        # 验证解封后不再活跃
        assert await service.is_ip_banned("10.0.0.1") is False
        assert await service.is_ip_banned("10.0.0.2") is False
        assert await service.is_ip_banned("10.0.0.3") is True

    @pytest.mark.asyncio
    async def test_batch_unban_skips_already_inactive(self, db_container):
        """批量解封应跳过已 inactive 的记录。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.unban_ip(ban_id=ban["id"])

        count = await service.batch_unban(ban_ids=[ban["id"]])
        assert count == 0

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, db_container):
        """分页查询应正确返回。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}")

        result = await service.list_bans(page=1, page_size=2)
        assert len(result["list"]) == 2
        assert result["total"] == 5
        assert result["page"] == 1
        assert result["page_size"] == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, db_container):
        """按 ban_type 筛选应正确。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.3", ban_type="auto")

        result = await service.list_bans(ban_type="manual")
        assert len(result["list"]) == 2

        result = await service.list_bans(ban_type="auto")
        assert len(result["list"]) == 1

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_keyword(self, db_container):
        """按关键词搜索应正确。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1")
        await service.ban_ip(ip_or_cidr="10.0.0.1")

        result = await service.list_bans(keyword="192.168")
        assert len(result["list"]) == 1
        assert result["list"][0]["ip_or_cidr"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_ban_logs_after_ban(self, db_container):
        """封禁后应生成操作日志。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test", banned_by="admin")

        logs = await service.get_ban_logs()
        assert logs["total"] >= 1
        assert logs["list"][0]["action"] == "ban"
        assert logs["list"][0]["ip_or_cidr"] == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, db_container):
        """按 action 筛选日志应正确。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.unban_ip(ban_id=ban["id"])

        ban_logs = await service.get_ban_logs(action="ban")
        assert all(log["action"] == "ban" for log in ban_logs["list"])

        unban_logs = await service.get_ban_logs(action="unban")
        assert all(log["action"] == "unban" for log in unban_logs["list"])

    @pytest.mark.asyncio
    async def test_get_stats_counts(self, db_container):
        """统计信息应正确。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto")
        await service.ban_ip(ip_or_cidr="10.0.0.3", ban_type="auto")

        stats = await service.get_stats()
        assert stats["total_bans"] == 3
        assert stats["manual_bans"] == 1
        assert stats["auto_bans"] == 2
        assert stats["active_bans"] == 3

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, db_container):
        """活跃 IP 范围列表应返回所有活跃 CIDR。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.0/24")
        await service.ban_ip(ip_or_cidr="192.168.1.1")

        ranges = await service.get_active_ip_ranges()
        assert len(ranges) == 2
        assert "10.0.0.0/24" in ranges
        assert "192.168.1.1" in ranges


# =============================================================================
# 自动封禁规则引擎 行为测试
# =============================================================================


class TestAutoBanRules:
    """测试自动封禁规则引擎。"""

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
    async def test_update_rule_config_persists(self, db_container):
        """更新规则配置应持久化。"""
        service = IpBanService(db_container)
        # 先调用 get_rule_configs 确保默认规则已写入数据库
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 5, "enabled": False}
        )
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 5
        assert login_rule["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises_error(self, db_container):
        """更新不存在的规则应抛出 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("nonexistent_rule", {"threshold": 5})
        assert excinfo.value.code == "rule_not_found"

    @pytest.mark.asyncio
    async def test_record_event_triggers_login_failure_ban(self, db_container):
        """登录失败次数超阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        # 先确保默认规则写入数据库，再降低阈值
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure", {"threshold": 3, "ban_duration_minutes": 10}
        )

        # 模拟 3 次登录失败
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.1")

        # 应触发自动封禁
        assert await service.is_ip_banned("10.0.0.1") is True

    @pytest.mark.asyncio
    async def test_record_event_below_threshold_no_ban(self, db_container):
        """登录失败次数低于阈值不应封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config("login_failure", {"threshold": 5})

        # 只失败 2 次
        for _ in range(2):
            await service.record_event("login_failure", "10.0.0.2")

        assert await service.is_ip_banned("10.0.0.2") is False

    @pytest.mark.asyncio
    async def test_record_event_rate_limit_ban(self, db_container):
        """请求频率超阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "rate_limit", {"threshold": 3, "ban_duration_minutes": 5}
        )

        for _ in range(3):
            await service.record_event("rate_limit", "10.0.0.3")

        assert await service.is_ip_banned("10.0.0.3") is True

    @pytest.mark.asyncio
    async def test_record_event_high_4xx_ban(self, db_container):
        """4xx 高频超阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "high_4xx", {"threshold": 3, "ban_duration_minutes": 30}
        )

        for _ in range(3):
            await service.record_event("high_4xx", "10.0.0.4", status_code=404)

        assert await service.is_ip_banned("10.0.0.4") is True

    @pytest.mark.asyncio
    async def test_disabled_rule_does_not_ban(self, db_container):
        """禁用的规则不应触发封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config("login_failure", {"enabled": False})

        for _ in range(20):
            await service.record_event("login_failure", "10.0.0.5")

        assert await service.is_ip_banned("10.0.0.5") is False

    @pytest.mark.asyncio
    async def test_cleanup_counters_removes_old_entries(self, db_container):
        """清理过期计数器应移除过期条目。"""
        service = IpBanService(db_container)
        # 直接注入过期计数器
        old_time = time.time() - 7200  # 2小时前
        service._counters["test:10.0.0.1"] = [(old_time, 0)]

        service._cleanup_counters()
        assert "test:10.0.0.1" not in service._counters


# =============================================================================
# Webhook 通知 行为测试
# =============================================================================


class TestWebhookNotification:
    """测试 Webhook 通知行为。"""

    @pytest.mark.asyncio
    async def test_webhook_skipped_when_no_url(self, db_container):
        """未配置 webhook URL 时不应发送通知。"""
        service = IpBanService(db_container)
        service._webhook_url = ""
        # 不应抛出异常
        await service._send_webhook_notification("ip_banned", {"ip_or_cidr": "test"})

    @pytest.mark.asyncio
    async def test_webhook_skipped_without_aiohttp(self, db_container):
        """未安装 aiohttp 时不应发送通知。"""
        service = IpBanService(db_container)
        service._webhook_url = "http://example.com/webhook"
        with patch("backend.plugins.ip_ban.services._HAS_AIOHTTP", False):
            await service._send_webhook_notification("ip_banned", {"ip_or_cidr": "test"})