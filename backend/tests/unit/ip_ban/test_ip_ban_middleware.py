"""IP 封禁中间件单元测试 —— BloomFilter、LRUSet。

测试原则：
- 纯函数/类测试，无需数据库
- 覆盖边界条件和极端情况
- 测试数据结构核心行为
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet


class TestBloomFilter:
    """布隆过滤器行为测试。"""

    def test_add_and_contains(self):
        """添加元素后应能被检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_contains_absent_item(self):
        """未添加的元素应返回 False。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("10.0.0.1") is False

    def test_false_positive_possible(self):
        """布隆过滤器可能有假阳性（但不影响正确性——假阳性只导致多余 DB 查询）。"""
        bf = BloomFilter(size=100)
        # 填充大量元素增加假阳性概率
        for i in range(500):
            bf.add(f"192.168.1.{i}")
        # 假阳性是可以接受的——不 assert 具体值，只验证不崩溃
        for _ in range(10):
            bf.contains("10.0.0.999")

    def test_clear_resets_all_bits(self):
        """clear 后所有元素应不再被检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False
        assert bf.contains("10.0.0.1") is False

    def test_ipv6_support(self):
        """IPv6 地址应能被正常处理。"""
        bf = BloomFilter(size=1000)
        bf.add("2001:db8::1")
        assert bf.contains("2001:db8::1") is True

    def test_cidr_notatio_in_bloom(self):
        """CIDR 段字符串应能被正常处理。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.0.0/16")
        assert bf.contains("192.168.0.0/16") is True
        assert bf.contains("10.0.0.0/8") is False

    def test_empty_string_handling(self):
        """空字符串应不被错误标记。"""
        bf = BloomFilter(size=1000)
        bf.add("")
        assert bf.contains("") is True
        assert bf.contains(" ") is False

    def test_hashes_deterministic(self):
        """相同输入的哈希结果应一致。"""
        bf = BloomFilter(size=1000)
        hashes_1 = bf._hashes("192.168.1.1")
        hashes_2 = bf._hashes("192.168.1.1")
        assert hashes_1 == hashes_2


class TestLRUSet:
    """LRU 集合行为测试。"""

    def test_add_and_contains(self):
        """添加元素后应能被检测到。"""
        cache = LRUSet(maxsize=5)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_contains_absent_item(self):
        """未添加的元素应返回 False。"""
        cache = LRUSet(maxsize=5)
        assert cache.contains("10.0.0.1") is False

    def test_lru_eviction(self):
        """超过容量时，最久未访问的元素应被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 a

        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_access_refreshes_order(self):
        """访问已有元素应刷新其在 LRU 中的位置（不触发淘汰）。"""
        cache = LRUSet(maxsize=2)
        cache.add("a")
        cache.add("b")
        cache.contains("a")  # 刷新 a
        cache.add("c")  # 应淘汰 b，而不是 a

        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("c") is True

    def test_remove(self):
        """remove 应移除指定元素。"""
        cache = LRUSet(maxsize=5)
        cache.add("192.168.1.1")
        cache.add("10.0.0.1")

        cache.remove("192.168.1.1")
        assert cache.contains("192.168.1.1") is False
        assert cache.contains("10.0.0.1") is True

    def test_remove_nonexistent(self):
        """删除不存在的元素不应抛出异常。"""
        cache = LRUSet(maxsize=5)
        cache.remove("nonexistent")  # 不应抛异常

    def test_clear(self):
        """clear 应移除所有元素。"""
        cache = LRUSet(maxsize=5)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False
        assert len(cache._data) == 0

    def test_duplicate_add_does_not_consume_extra_slot(self):
        """重复添加同一元素不应消耗额外容量。"""
        cache = LRUSet(maxsize=2)
        cache.add("x")
        cache.add("x")
        cache.add("y")
        cache.add("z")  # 容量 2，应淘汰 x

        assert cache.contains("x") is False  # x 被淘汰
        assert cache.contains("y") is True
        assert cache.contains("z") is True

    def test_empty_cache(self):
        """空缓存应返回 False。"""
        cache = LRUSet(maxsize=5)
        assert cache.contains("anything") is False