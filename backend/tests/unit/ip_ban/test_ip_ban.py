"""IP 封禁插件 单元测试。

测试覆盖：
- BloomFilter 布隆过滤器：添加、包含、误判率、清空
- LRUSet 缓存：添加、包含、淘汰、移除、清空
- ip_matches_cidr：IPv4/IPv6 匹配、不匹配、非法输入
- IpBanService 自动封禁规则引擎：login_failure, high_4xx, rate_limit
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    def test_add_and_contains(self):
        """添加后应能检测到存在。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的项应返回 False。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("10.0.0.1") is False

    def test_clear(self):
        """清空后所有项应返回 False。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_multiple_items(self):
        """多个添加项应都能检测到。"""
        bf = BloomFilter(size=10000)
        items = [f"10.0.0.{i}" for i in range(100)]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item) is True

    def test_false_positive_rate_within_bound(self):
        """小布隆过滤器允许一定误判率，但不应全部误判。"""
        bf = BloomFilter(size=100)
        for i in range(50):
            bf.add(f"10.0.0.{i}")

        false_positives = sum(
            1 for i in range(50, 100) if bf.contains(f"10.0.0.{i}")
        )
        # 50 个未添加项，误判应少于 30 个
        assert false_positives < 30, f"误判率过高: {false_positives}/50"


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    def test_add_and_contains(self):
        """添加后应能检测到存在。"""
        cache = LRUSet(maxsize=5)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_contains_moves_to_end(self):
        """contains 应把已存在的项移到末尾（不触发淘汰）。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 a，使 a 成为最近使用
        cache.contains("a")
        # 添加 d，应淘汰最久未使用的 b
        cache.add("d")
        assert cache.contains("a") is True  # a 被访问过，应保留
        assert cache.contains("b") is False  # b 最久未使用，应被淘汰
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_eviction_when_full(self):
        """超过 maxsize 时应淘汰最久未使用的项。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 a
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_remove(self):
        """移除后应不再包含。"""
        cache = LRUSet(maxsize=5)
        cache.add("192.168.1.1")
        cache.remove("192.168.1.1")
        assert cache.contains("192.168.1.1") is False

    def test_remove_nonexistent(self):
        """移除不存在的项不应抛异常。"""
        cache = LRUSet(maxsize=5)
        cache.remove("nonexistent")  # should not raise

    def test_clear(self):
        """清空后应不包含任何项。"""
        cache = LRUSet(maxsize=5)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False


# =============================================================================
# ip_matches_cidr 测试
# =============================================================================


class TestIpMatchesCidr:
    def test_ipv4_match(self):
        """IPv4 地址在 CIDR 段内应返回 True。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_not_match(self):
        """IPv4 地址不在 CIDR 段内应返回 False。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_exact_match(self):
        """精确 IP 匹配应返回 True。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.5/32") is True

    def test_ipv6_match(self):
        """IPv6 地址在 CIDR 段内应返回 True。"""
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_ipv6_not_match(self):
        """IPv6 地址不在 CIDR 段内应返回 False。"""
        assert ip_matches_cidr("::2", "::1/128") is False

    def test_invalid_ip(self):
        """非法 IP 地址应返回 False 不抛异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr(self):
        """非法 CIDR 段应返回 False 不抛异常。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_cidr_large_network(self):
        """大段 CIDR 匹配（如 0.0.0.0/0 应匹配任何 IP）。"""
        assert ip_matches_cidr("1.2.3.4", "0.0.0.0/0") is True


# =============================================================================
# IpBanService 自动封禁规则引擎测试
# =============================================================================


class TestIpBanServiceAutoBanEngine:
    """测试自动封禁规则引擎的核心逻辑。

    使用 mock 绕过数据库，直接测试规则检查逻辑。
    """

    @pytest.fixture
    def service(self):
        """创建带 mock 数据库的 IpBanService。"""
        container = MagicMock()
        mock_session_factory = MagicMock()
        container.get.return_value = {"session_factory": mock_session_factory}
        svc = IpBanService(container)
        # 覆盖 _counters 为可控的 dict
        svc._counters = {}
        return svc

    @pytest.fixture
    def enabled_rule(self):
        """返回一个启用的 login_failure 规则配置。"""
        return {
            "id": "login_failure",
            "enabled": True,
            "threshold": 5,
            "window_seconds": 60,
            "ban_duration_minutes": 30,
            "name": "登录失败封禁",
            "description": "test",
        }

    @pytest.mark.asyncio
    async def test_login_failure_rule_disabled_skips(self, service):
        """规则禁用时不应触发封禁。"""
        with patch.object(
            service, "get_rule_configs", return_value=[{"id": "login_failure", "enabled": False}]
        ):
            with patch.object(service, "ban_ip") as mock_ban:
                await service._check_login_failure_rule("1.2.3.4")
                mock_ban.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_login_failure_below_threshold_no_ban(self, service):
        """未达阈值时不应触发封禁。"""
        service._counters = {"login_failure:1.2.3.4": [(100.0, 0)]}
        with patch.object(
            service, "get_rule_configs", return_value=[{
                "id": "login_failure",
                "enabled": True,
                "threshold": 5,
                "window_seconds": 60,
                "ban_duration_minutes": 30,
                "name": "登录失败封禁",
                "description": "test",
            }]
        ):
            with patch.object(service, "ban_ip") as mock_ban:
                await service._check_login_failure_rule("1.2.3.4")
                mock_ban.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_login_failure_at_threshold_triggers_ban(self, service):
        """达到阈值时应触发自动封禁。"""
        import time
        now = time.time()
        service._counters = {
            "login_failure:1.2.3.4": [(now - 10, 0) for _ in range(5)]
        }
        with patch.object(
            service, "get_rule_configs", return_value=[{
                "id": "login_failure",
                "enabled": True,
                "threshold": 5,
                "window_seconds": 60,
                "ban_duration_minutes": 30,
                "name": "登录失败封禁",
                "description": "test",
            }]
        ):
            with patch.object(service, "ban_ip") as mock_ban:
                await service._check_login_failure_rule("1.2.3.4")
                mock_ban.assert_awaited_once_with(
                    ip_or_cidr="1.2.3.4",
                    reason=mock_ban.call_args[1]["reason"],
                    ban_type="auto",
                    rule_id="login_failure",
                    duration_minutes=30,
                )

    @pytest.mark.asyncio
    async def test_high_4xx_count_below_threshold(self, service):
        """4xx 请求未达阈值时不应触发封禁。"""
        service._counters = {"high_4xx:1.2.3.4": [(100.0, 404)]}
        with patch.object(
            service, "get_rule_configs", return_value=[{
                "id": "high_4xx",
                "enabled": True,
                "threshold": 10,
                "window_seconds": 3600,
                "ban_duration_minutes": 60,
                "name": "4xx 高频封禁",
                "description": "test",
            }]
        ):
            with patch.object(service, "ban_ip") as mock_ban:
                await service._check_high_4xx_rule("1.2.3.4")
                mock_ban.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_high_4xx_only_counts_4xx_status(self, service):
        """4xx 规则只统计 4xx 状态码，不应计入 200。"""
        import time
        now = time.time()
        # 5 个 200 + 5 个 404，但阈值是 10，只应统计 404 的 5 次
        service._counters = {
            "high_4xx:1.2.3.4": [(now - 10, 200) for _ in range(5)] + [(now - 10, 404) for _ in range(5)]
        }
        with patch.object(
            service, "get_rule_configs", return_value=[{
                "id": "high_4xx",
                "enabled": True,
                "threshold": 10,
                "window_seconds": 3600,
                "ban_duration_minutes": 60,
                "name": "4xx 高频封禁",
                "description": "test",
            }]
        ):
            with patch.object(service, "ban_ip") as mock_ban:
                await service._check_high_4xx_rule("1.2.3.4")
                # 只有 5 个 404，不到 10 个阈值
                mock_ban.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_high_4xx_at_threshold_triggers_ban(self, service):
        """4xx 请求达到阈值时应触发自动封禁。"""
        import time
        now = time.time()
        service._counters = {
            "high_4xx:1.2.3.4": [(now - 10, 404) for _ in range(10)]
        }
        with patch.object(
            service, "get_rule_configs", return_value=[{
                "id": "high_4xx",
                "enabled": True,
                "threshold": 10,
                "window_seconds": 3600,
                "ban_duration_minutes": 60,
                "name": "4xx 高频封禁",
                "description": "test",
            }]
        ):
            with patch.object(service, "ban_ip") as mock_ban:
                await service._check_high_4xx_rule("1.2.3.4")
                mock_ban.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rate_limit_rule_triggers_ban(self, service):
        """请求频率达到阈值时应触发自动封禁。"""
        import time
        now = time.time()
        service._counters = {
            "rate_limit:1.2.3.4": [(now - 5, 0) for _ in range(200)]
        }
        with patch.object(
            service, "get_rule_configs", return_value=[{
                "id": "rate_limit",
                "enabled": True,
                "threshold": 200,
                "window_seconds": 60,
                "ban_duration_minutes": 10,
                "name": "请求频率封禁",
                "description": "test",
            }]
        ):
            with patch.object(service, "ban_ip") as mock_ban:
                await service._check_rate_limit_rule("1.2.3.4")
                mock_ban.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cleanup_counters_removes_expired(self, service):
        """清理过期计数器应移除超过 1 小时的条目。"""
        import time
        now = time.time()
        service._counters = {
            "login_failure:1.2.3.4": [(now - 4000, 0)],  # 超过 1 小时
            "login_failure:5.6.7.8": [(now - 100, 0)],   # 1 小时内
        }
        service._cleanup_counters()
        assert "login_failure:1.2.3.4" not in service._counters
        assert "login_failure:5.6.7.8" in service._counters

    @pytest.mark.asyncio
    async def test_record_event_delegates_to_correct_rule(self, service):
        """record_event 应根据事件类型分派到对应的规则检查。"""
        # 确保 _counters 使用 defaultdict(list) 以避免 KeyError
        from collections import defaultdict
        service._counters = defaultdict(list)

        with (
            patch.object(service, "_check_login_failure_rule") as mock_login,
            patch.object(service, "_check_high_4xx_rule") as mock_4xx,
            patch.object(service, "_check_rate_limit_rule") as mock_rate,
        ):
            await service.record_event("login_failure", "1.2.3.4")
            mock_login.assert_awaited_once_with("1.2.3.4")

            await service.record_event("high_4xx", "1.2.3.4", 404)
            mock_4xx.assert_awaited_once_with("1.2.3.4")

            await service.record_event("rate_limit", "1.2.3.4")
            mock_rate.assert_awaited_once_with("1.2.3.4")