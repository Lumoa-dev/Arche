"""IP 封禁插件 —— 工具类单元测试。

测试 ip_matches_cidr、BloomFilter、LRUSet 等独立组件。
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import ip_matches_cidr


# =============================================================================
# ip_matches_cidr
# =============================================================================


class TestIpMatchesCidr:
    """IP/CIDR 匹配测试。"""

    def test_exact_ip_match(self):
        """精确 IP 匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ip_in_subnet(self):
        """IP 在子网内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ip_outside_subnet(self):
        """IP 不在子网内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv6_match(self):
        """IPv6 匹配。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_ipv6_no_match(self):
        """IPv6 不匹配。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db9::/32") is False
        )

    def test_invalid_ip_returns_false(self):
        """非法 IP 返回 False（不抛异常）。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """非法 CIDR 返回 False（不抛异常）。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_cidr_with_non_zero_host_bits(self):
        """非严格 CIDR（strict=False）也匹配。"""
        assert ip_matches_cidr("192.168.1.5", "192.168.1.0/24") is True

    def test_empty_string_returns_false(self):
        """空字符串不抛异常。"""
        assert ip_matches_cidr("", "") is False


# =============================================================================
# BloomFilter
# =============================================================================


class TestBloomFilter:
    """布隆过滤器测试。"""

    def test_add_and_contains(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("10.0.0.1") is False

    def test_multiple_items(self):
        bf = BloomFilter(size=10000)
        ips = [f"10.0.0.{i}" for i in range(100)]
        for ip in ips:
            bf.add(ip)
        for ip in ips:
            assert bf.contains(ip) is True

    def test_clear(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_empty_filter(self):
        """空过滤器不应包含任何内容。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("any.ip") is False

    def test_different_sizes(self):
        """不同大小的过滤器都应正常工作。"""
        bf = BloomFilter(size=100)
        bf.add("test")
        assert bf.contains("test") is True


# =============================================================================
# LRUSet
# =============================================================================


class TestLRUSet:
    """LRU 集合测试。"""

    def test_add_and_contains(self):
        cache = LRUSet(maxsize=5)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_not_contains(self):
        cache = LRUSet(maxsize=5)
        assert cache.contains("10.0.0.1") is False

    def test_eviction_when_full(self):
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰最旧的 "a"
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_reorder_on_re_add(self):
        """重新添加已存在的项应移动到末尾。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("a")  # "a" 移到末尾，"b" 变为最旧
        cache.add("d")  # 淘汰 "b"
        assert cache.contains("a") is True
        assert cache.contains("b") is False

    def test_remove(self):
        cache = LRUSet(maxsize=5)
        cache.add("a")
        cache.add("b")
        cache.remove("a")
        assert cache.contains("a") is False
        assert cache.contains("b") is True

    def test_remove_nonexistent(self):
        """删除不存在的元素不应报错。"""
        cache = LRUSet(maxsize=5)
        cache.remove("nonexistent")  # 不应抛异常

    def test_clear(self):
        cache = LRUSet(maxsize=5)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False

    def test_contains_updates_order(self):
        """contains() 应把命中项移到末尾。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        assert cache.contains("a") is True  # "a" 移到末尾
        cache.add("d")  # 淘汰 "b"
        assert cache.contains("a") is True
        assert cache.contains("b") is False

    def test_empty_cache(self):
        cache = LRUSet(maxsize=5)
        assert cache.contains("anything") is False