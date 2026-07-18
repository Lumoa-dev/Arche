"""IP 封禁中间件组件测试 —— BloomFilter、LRUSet、ip_matches_cidr。

纯函数测试，无数据库依赖，运行极快。
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import ip_matches_cidr


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    """布隆过滤器行为测试。"""

    def test_add_and_contains(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")
        assert bf.contains("192.168.1.1") is True
        assert bf.contains("10.0.0.1") is True

    def test_contains_absent(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("10.0.0.2") is False

    def test_clear(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_empty_filter(self):
        bf = BloomFilter(size=1000)
        assert bf.contains("anything") is False

    def test_different_sizes_produce_consistent_results(self):
        bf_small = BloomFilter(size=100)
        bf_large = BloomFilter(size=100_000)
        items = [f"10.0.0.{i}" for i in range(50)]
        for item in items:
            bf_small.add(item)
            bf_large.add(item)
        # 小过滤器可能误报，但已添加的必须命中
        for item in items:
            assert bf_small.contains(item) is True
            assert bf_large.contains(item) is True


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    """LRU 缓存集合行为测试。"""

    def test_add_and_contains(self):
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_contains_absent(self):
        cache = LRUSet(maxsize=10)
        assert cache.contains("10.0.0.1") is False

    def test_eviction(self):
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 "a"
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_remove(self):
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.remove("a")
        assert cache.contains("a") is False
        assert cache.contains("b") is True

    def test_remove_nonexistent(self):
        """删除不存在的元素不应报错。"""
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")  # 不应抛出异常

    def test_clear(self):
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False
        assert len(cache._data) == 0

    def test_add_renews_item(self):
        """已存在的元素被重新添加应移到末尾。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 重新添加 "a" 使其变为最近使用
        cache.add("a")
        cache.add("d")  # 应淘汰 "b"（最久未使用）
        assert cache.contains("a") is True
        assert cache.contains("b") is False


# =============================================================================
# ip_matches_cidr 测试
# =============================================================================


class TestIpMatchesCidr:
    """IP/CIDR 匹配函数行为测试。"""

    def test_ipv4_exact_match(self):
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_cidr_whole_range(self):
        assert ip_matches_cidr("10.0.0.1", "0.0.0.0/0") is True

    def test_ipv6_match(self):
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_ipv6_no_match(self):
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db9::/32") is False
        )

    def test_invalid_ip_returns_false(self):
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_empty_string_returns_false(self):
        assert ip_matches_cidr("", "192.168.1.0/24") is False

    def test_localhost_match(self):
        assert ip_matches_cidr("127.0.0.1", "127.0.0.0/8") is True

    def test_private_range_match(self):
        assert ip_matches_cidr("10.0.0.50", "10.0.0.0/8") is True
        assert ip_matches_cidr("172.16.0.1", "172.16.0.0/12") is True