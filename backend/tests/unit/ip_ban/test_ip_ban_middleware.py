"""IP 封禁 — BloomFilter 和 LRUSet 单元测试。

覆盖布隆过滤器和 LRU 缓存的全部路径：
插入、查询、边界条件、并发语义。
纯 mock，无数据库依赖。
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet


class TestBloomFilter:
    """布隆过滤器测试。"""

    def test_contains_after_add(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains_before_add(self):
        bf = BloomFilter(size=1000)
        assert bf.contains("10.0.0.1") is False

    def test_contains_multiple_items(self):
        bf = BloomFilter(size=10000)
        ips = [f"10.0.0.{i}" for i in range(100)]
        for ip in ips:
            bf.add(ip)
        for ip in ips:
            assert bf.contains(ip) is True

    def test_false_positive_probability_low(self):
        """小规模测试：200 个插入项中不应出现太多误报。"""
        bf = BloomFilter(size=100000)
        inserted = [f"10.0.0.{i}" for i in range(200)]
        not_inserted = [f"10.0.1.{i}" for i in range(200, 400)]

        for ip in inserted:
            bf.add(ip)

        false_positives = sum(1 for ip in not_inserted if bf.contains(ip))
        # 误报率应低于 5%（100000 bits / 200 items -> 500 bits/item）
        assert false_positives <= 10

    def test_clear_resets_filter(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_empty_filter_returns_false(self):
        bf = BloomFilter(size=1000)
        assert bf.contains("any") is False

    def test_different_sizes(self):
        bf_small = BloomFilter(size=100)
        bf_large = BloomFilter(size=100000)
        bf_small.add("test")
        bf_large.add("test")
        assert bf_small.contains("test") is True
        assert bf_large.contains("test") is True


class TestLRUSet:
    """LRU 缓存集合测试。"""

    def test_contains_after_add(self):
        cache = LRUSet(maxsize=100)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_not_contains_before_add(self):
        cache = LRUSet(maxsize=100)
        assert cache.contains("10.0.0.1") is False

    def test_maxsize_eviction(self):
        """超过 maxsize 时淘汰最早的元素。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 "a"

        assert cache.contains("a") is False  # 被淘汰
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_lru_refresh(self):
        """访问元素会将其移到末尾，不被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.contains("a")  # 刷新 "a"
        cache.add("d")  # 应淘汰 "b"

        assert cache.contains("a") is True  # 被刷新，保留
        assert cache.contains("b") is False  # 被淘汰
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_remove_existing(self):
        cache = LRUSet(maxsize=100)
        cache.add("item")
        cache.remove("item")
        assert cache.contains("item") is False

    def test_remove_nonexistent(self):
        """删除不存在的元素不抛异常。"""
        cache = LRUSet(maxsize=100)
        cache.remove("nonexistent")  # 不应抛出异常

    def test_clear(self):
        cache = LRUSet(maxsize=100)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False

    def test_duplicate_add_moves_to_end(self):
        """重复添加同一元素应将其移到末尾。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("a")  # 重复，应移到末尾
        cache.add("d")  # 应淘汰 "b"

        assert cache.contains("a") is True
        assert cache.contains("b") is False  # 被淘汰
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_empty_after_init(self):
        cache = LRUSet(maxsize=100)
        assert cache.contains("anything") is False