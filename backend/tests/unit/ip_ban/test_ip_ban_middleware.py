"""IP 封禁中间件测试 —— BloomFilter、LRUSet、IpBanMiddleware。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    """测试布隆过滤器核心行为。"""

    def test_contains_returns_false_for_new_item(self):
        """新添加前的元素返回 False。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("192.168.1.1") is False

    def test_contains_returns_true_after_add(self):
        """添加后该元素返回 True。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_contains_multiple_items(self):
        """多个元素各自独立判断。"""
        bf = BloomFilter(size=1000)
        bf.add("10.0.0.1")
        bf.add("10.0.0.2")
        assert bf.contains("10.0.0.1") is True
        assert bf.contains("10.0.0.2") is True
        assert bf.contains("10.0.0.3") is False

    def test_clear_resets_filter(self):
        """clear 后所有元素应返回 False。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_false_positive_rate_within_reasonable_range(self):
        """小规模下假阳性率应在合理范围内。"""
        bf = BloomFilter(size=10000)
        items = [f"10.0.0.{i}" for i in range(100)]
        for item in items:
            bf.add(item)

        # 所有已添加元素都应被检测到
        for item in items:
            assert bf.contains(item) is True

        # 假阳性率应 < 5%（10000 bits / 100 items 应足够低）
        false_positives = sum(
            1 for i in range(200, 300) if bf.contains(f"192.168.0.{i}")
        )
        assert false_positives < 5  # 允许少量假阳性

    def test_empty_filter_contains_returns_false(self):
        """空过滤器始终返回 False。"""
        bf = BloomFilter(size=100)
        assert bf.contains("anything") is False

    def test_ipv6_support(self):
        """IPv6 地址也能正常处理。"""
        bf = BloomFilter(size=1000)
        bf.add("2001:db8::1")
        assert bf.contains("2001:db8::1") is True


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    """测试 LRU 缓存集合行为。"""

    def test_contains_returns_false_for_new_item(self):
        """新元素不在缓存中。"""
        cache = LRUSet(maxsize=10)
        assert cache.contains("192.168.1.1") is False

    def test_contains_returns_true_after_add(self):
        """添加后元素在缓存中。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_add_evicts_oldest_when_full(self):
        """超过容量时淘汰最久未使用的元素。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 "a"
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_recently_used_items_are_kept(self):
        """最近使用的元素不被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.contains("a")  # 使用 "a" 使其变为最近
        cache.add("d")  # 应淘汰 "b" 而非 "a"
        assert cache.contains("a") is True
        assert cache.contains("d") is True

    def test_remove_removes_item(self):
        """remove 后元素不在缓存中。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        cache.remove("192.168.1.1")
        assert cache.contains("192.168.1.1") is False

    def test_remove_nonexistent_item_does_not_raise(self):
        """移除不存在的元素不抛异常。"""
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")

    def test_clear_empties_cache(self):
        """clear 后所有元素被移除。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False

    def test_maxsize_one(self):
        """容量为 1 时正常工作。"""
        cache = LRUSet(maxsize=1)
        cache.add("a")
        assert cache.contains("a") is True
        cache.add("b")
        assert cache.contains("a") is False
        assert cache.contains("b") is True

    def test_re_add_existing_item_moves_to_end(self):
        """重新添加已有元素应移到末尾（不淘汰）。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("a")  # "a" 已存在，移到末尾
        cache.add("d")  # 应淘汰 "b"
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("c") is True
        assert cache.contains("d") is True