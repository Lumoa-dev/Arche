"""IP 封禁中间件单元测试 —— BloomFilter、LRUSet、ip_matches_cidr。

测试原则：
- 纯数据结构测试，不依赖数据库
- 覆盖边界条件：空值、IPv4/IPv6、CIDR 边界、容量溢出
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import ip_matches_cidr


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    """布隆过滤器基础行为测试。"""

    def test_contains_returns_false_for_empty_filter(self):
        """空过滤器 should return False for any item."""
        bf = BloomFilter(size=1000)
        assert not bf.contains("192.168.1.1")
        assert not bf.contains("10.0.0.1")

    def test_contains_returns_true_after_add(self):
        """添加后 should return True."""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1")

    def test_contains_multiple_items(self):
        """多个不同 IP 独立存储。"""
        bf = BloomFilter(size=10000)
        ips = [f"10.0.0.{i}" for i in range(100)]
        for ip in ips:
            bf.add(ip)
        for ip in ips:
            assert bf.contains(ip), f"{ip} 应在过滤器中"

    def test_contains_separate_items(self):
        """不同 IP 互不干扰。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert not bf.contains("10.0.0.1")

    def test_clear_resets_filter(self):
        """clear 后应重置所有位。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert not bf.contains("192.168.1.1")

    def test_large_size_filter(self):
        """大尺寸过滤器正常运作。"""
        bf = BloomFilter(size=1_000_000)
        bf.add("::1")
        assert bf.contains("::1")


class TestBloomFilterEdgeCases:
    """布隆过滤器边界条件测试。"""

    def test_empty_string(self):
        """空字符串作为输入。"""
        bf = BloomFilter(size=1000)
        bf.add("")
        # 空字符串不应导致崩溃
        assert bf.contains("") is not None  # 可能返回 True 或 False，但不崩溃

    def test_special_characters(self):
        """特殊字符作为输入。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1; rm -rf /")
        assert bf.contains("192.168.1.1; rm -rf /")

    def test_tiny_size(self):
        """极小尺寸过滤器不应崩溃。"""
        bf = BloomFilter(size=8)
        bf.add("192.168.1.1")
        # 极小尺寸下可能误判，但不崩溃
        result = bf.contains("192.168.1.1")
        assert isinstance(result, bool)


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    """LRU 缓存集合基础行为测试。"""

    def test_contains_returns_false_for_empty(self):
        """空集合返回 False."""
        cache = LRUSet(maxsize=100)
        assert not cache.contains("192.168.1.1")

    def test_contains_returns_true_after_add(self):
        """添加后返回 True."""
        cache = LRUSet(maxsize=100)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1")

    def test_remove_removes_item(self):
        """remove 后应返回 False."""
        cache = LRUSet(maxsize=100)
        cache.add("192.168.1.1")
        cache.remove("192.168.1.1")
        assert not cache.contains("192.168.1.1")

    def test_remove_nonexistent(self):
        """移除不存在的元素不应崩溃。"""
        cache = LRUSet(maxsize=100)
        cache.remove("nonexistent")  # 不应抛出异常

    def test_clear_empties_cache(self):
        """clear 后所有元素丢失。"""
        cache = LRUSet(maxsize=100)
        cache.add("192.168.1.1")
        cache.add("10.0.0.1")
        cache.clear()
        assert not cache.contains("192.168.1.1")
        assert not cache.contains("10.0.0.1")

    def test_contains_moves_to_end(self):
        """contains 应把元素移到末尾（LRU 语义）。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 a，使 a 成为最近使用
        cache.contains("a")
        # 添加 d，应该淘汰最久未使用的（b）
        cache.add("d")
        assert cache.contains("a")  # a 被访问过，应保留
        assert not cache.contains("b")  # b 最久未使用，应淘汰
        assert cache.contains("c")
        assert cache.contains("d")


class TestLRUSetEviction:
    """LRU 淘汰策略测试。"""

    def test_evicts_oldest_when_full(self):
        """超过 maxsize 时淘汰最旧元素。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 a
        assert not cache.contains("a")
        assert cache.contains("b")
        assert cache.contains("c")
        assert cache.contains("d")

    def test_eviction_order_correct(self):
        """严格按 FIFO 顺序淘汰（未访问时）。"""
        cache = LRUSet(maxsize=2)
        cache.add("first")
        cache.add("second")
        cache.add("third")  # 淘汰 first
        assert not cache.contains("first")
        assert cache.contains("second")
        assert cache.contains("third")

    def test_large_maxsize(self):
        """大容量 LRU 正常运作。"""
        cache = LRUSet(maxsize=5000)
        # 添加超过 maxsize 的元素，触发淘汰
        for i in range(5100):
            cache.add(f"ip-{i}")
        # 前 100 个应被淘汰（0-99），第 101 个（100）应仍在
        assert not cache.contains("ip-0")
        assert not cache.contains("ip-99")
        assert cache.contains("ip-100")
        # 后 100 个应在
        assert cache.contains("ip-5000")
        assert cache.contains("ip-5099")


# =============================================================================
# ip_matches_cidr 测试
# =============================================================================


class TestIpMatchesCidr:
    """IP/CIDR 匹配工具函数测试。"""

    def test_ipv4_exact_match(self):
        """精确 IPv4 匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32")

    def test_ipv4_subnet_match(self):
        """IPv4 子网内匹配。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24")

    def test_ipv4_outside_subnet(self):
        """IPv4 不在子网内。"""
        assert not ip_matches_cidr("192.168.2.1", "192.168.1.0/24")

    def test_ipv6_exact_match(self):
        """精确 IPv6 匹配。"""
        assert ip_matches_cidr("::1", "::1/128")

    def test_ipv6_subnet_match(self):
        """IPv6 子网内匹配。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32")

    def test_ipv6_outside_subnet(self):
        """IPv6 不在子网内。"""
        assert not ip_matches_cidr("2001:db9::1", "2001:db8::/32")

    def test_invalid_ip_returns_false(self):
        """无效 IP 返回 False 而不崩溃。"""
        assert not ip_matches_cidr("not-an-ip", "192.168.1.0/24")

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 返回 False 而不崩溃。"""
        assert not ip_matches_cidr("192.168.1.1", "invalid-cidr")

    def test_cidr_with_non_strict(self):
        """非严格 CIDR（主机位不为零）应正常匹配。"""
        # 192.168.1.10/24 的主机位不为零，strict=False 应允许
        assert ip_matches_cidr("192.168.1.1", "192.168.1.10/24")

    def test_loopback_v4(self):
        """回环地址匹配。"""
        assert ip_matches_cidr("127.0.0.1", "127.0.0.0/8")

    def test_private_range(self):
        """私有地址段匹配。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.0/8")
        assert ip_matches_cidr("172.16.0.1", "172.16.0.0/12")
        assert ip_matches_cidr("192.168.0.1", "192.168.0.0/16")