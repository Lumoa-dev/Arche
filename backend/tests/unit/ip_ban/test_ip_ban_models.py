"""BloomFilter、LRUSet、ip_matches_cidr 等底层结构的单元测试。

这些数据结构被 IpBanMiddleware 用于高性能 IP 封禁检查，
错误的实现可能导致封禁失效或误封。
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import ip_matches_cidr


# =============================================================================
# ip_matches_cidr 测试
# =============================================================================


class TestIpMatchesCidr:
    """CIDR 匹配函数的边界情况测试。"""

    def test_ipv4_exact_match(self):
        """精确 IP 应该匹配自身。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32")

    def test_ipv4_in_subnet(self):
        """IP 在子网内应匹配。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.0/24")

    def test_ipv4_outside_subnet(self):
        """IP 在子网外不应匹配。"""
        assert not ip_matches_cidr("10.0.1.5", "10.0.0.0/24")

    def test_cidr_without_prefix(self):
        """不带前缀的 CIDR 应被 strict=False 兼容。"""
        assert ip_matches_cidr("192.168.1.10", "192.168.1.0/24")

    def test_invalid_ip_returns_false(self):
        """无效 IP 字符串应返回 False。"""
        assert not ip_matches_cidr("not-an-ip", "192.168.1.0/24")

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 字符串应返回 False。"""
        assert not ip_matches_cidr("192.168.1.1", "not-a-cidr")

    def test_ipv6_match(self):
        """IPv6 地址应正确匹配。"""
        assert ip_matches_cidr("::1", "::1/128")
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32")

    def test_ipv6_no_match(self):
        """IPv6 地址不在子网内不应匹配。"""
        assert not ip_matches_cidr("2001:db8::1", "2001:db8:1::/48")

    def test_zero_width_subnet(self):
        """0.0.0.0/0 应匹配所有 IPv4。"""
        assert ip_matches_cidr("1.2.3.4", "0.0.0.0/0")
        assert ip_matches_cidr("255.255.255.255", "0.0.0.0/0")

    def test_empty_string_returns_false(self):
        """空字符串应返回 False。"""
        assert not ip_matches_cidr("", "192.168.1.0/24")
        assert not ip_matches_cidr("192.168.1.1", "")


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    """布隆过滤器核心行为测试。"""

    def test_new_filter_contains_nothing(self):
        """新建的过滤器不应包含任何元素。"""
        bf = BloomFilter(size=1000)
        assert not bf.contains("anything")
        assert not bf.contains("")

    def test_added_item_is_found(self):
        """添加后的元素应能被检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1")

    def test_multiple_items(self):
        """多个元素添加后都应被检测到。"""
        bf = BloomFilter(size=10000)
        items = [f"10.0.0.{i}" for i in range(100)]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item)

    def test_false_positive_rate_within_reasonable(self):
        """在适当大小下，误判率应控制在合理范围。"""
        bf = BloomFilter(size=100000)
        # 添加 1000 个元素
        added = {f"10.0.0.{i}" for i in range(1000)}
        for item in added:
            bf.add(item)
        # 检查 1000 个未添加的元素
        false_positives = sum(
            1 for i in range(1000, 2000) if bf.contains(f"10.0.0.{i}")
        )
        # 100000 bits / 1000 items = 100 bits per item, 3 hashes
        # 理论上误判率约 0.6%，允许 5% 作为安全阈值
        assert false_positives < 50, (
            f"False positive count too high: {false_positives}/1000"
        )

    def test_clear_removes_all(self):
        """清空后应不再包含任何元素。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")
        bf.clear()
        assert not bf.contains("192.168.1.1")
        assert not bf.contains("10.0.0.1")

    def test_very_small_size_still_works(self):
        """极小过滤器仍应正常工作（虽然误判率会高）。"""
        bf = BloomFilter(size=8)
        bf.add("test")
        assert bf.contains("test")

    def test_empty_string_handling(self):
        """空字符串应能被正确处理。"""
        bf = BloomFilter(size=1000)
        bf.add("")
        assert bf.contains("")


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    """LRU 集合的容量控制和淘汰行为测试。"""

    def test_new_set_is_empty(self):
        """新建集合应不包含任何元素。"""
        cache = LRUSet(maxsize=5)
        assert not cache.contains("anything")

    def test_added_item_is_found(self):
        """添加后的元素应能被查找到。"""
        cache = LRUSet(maxsize=5)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1")

    def test_contains_updates_order(self):
        """contains 调用应将元素移到末尾（LRU 语义）。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 a，使其成为最近使用的
        cache.contains("a")
        # 再添加一个，应淘汰 b（最久未使用的）
        cache.add("d")
        assert cache.contains("a")  # a 刚被访问过
        assert not cache.contains("b")  # b 应被淘汰
        assert cache.contains("c")
        assert cache.contains("d")

    def test_eviction_oldest_when_full(self):
        """达到最大容量时，应淘汰最久未使用的元素。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 此时 [a, b, c] (a 最旧)
        cache.add("d")
        # 应为 [b, c, d]
        assert not cache.contains("a")
        assert cache.contains("b")
        assert cache.contains("c")
        assert cache.contains("d")

    def test_re_add_moves_to_end(self):
        """重新添加已有元素应将其移到末尾。"""
        cache = LRUSet(maxsize=2)
        cache.add("a")
        cache.add("b")
        # 再次添加 a，a 应移到末尾
        cache.add("a")
        # 添加 c，应淘汰 b
        cache.add("c")
        assert not cache.contains("b")
        assert cache.contains("a")
        assert cache.contains("c")

    def test_remove_existing(self):
        """移除已存在的元素应成功。"""
        cache = LRUSet(maxsize=5)
        cache.add("test")
        cache.remove("test")
        assert not cache.contains("test")

    def test_remove_nonexistent(self):
        """移除不存在的元素不应报错。"""
        cache = LRUSet(maxsize=5)
        cache.remove("nonexistent")  # 不应抛异常

    def test_clear(self):
        """清空后应不包含任何元素。"""
        cache = LRUSet(maxsize=5)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert not cache.contains("a")
        assert not cache.contains("b")

    def test_zero_maxsize_creates_ephemeral_set(self):
        """maxsize=0 的集合立即淘汰所有元素。"""
        cache = LRUSet(maxsize=0)
        cache.add("test")
        assert not cache.contains("test")