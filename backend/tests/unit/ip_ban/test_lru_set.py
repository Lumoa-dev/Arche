"""LRUSet 测试 — 固定大小 LRU 集合。

覆盖：
- 基本添加和检查
- LRU 淘汰行为
- contains 更新访问顺序
- remove / clear 操作
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.middleware import LRUSet


class TestLRUSet:
    """LRUSet 行为测试。"""

    def test_add_and_contains(self):
        """添加后元素可被检测到。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1")

    def test_not_contains_unadded(self):
        """未添加的元素不应被检测到。"""
        cache = LRUSet(maxsize=10)
        cache.add("10.0.0.1")
        assert not cache.contains("192.168.1.1")

    def test_evicts_oldest_when_full(self):
        """超过 maxsize 时淘汰最久未访问的元素。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 "a"
        assert not cache.contains("a")
        assert cache.contains("b")
        assert cache.contains("c")
        assert cache.contains("d")

    def test_contains_updates_access_order(self):
        """contains 调用更新访问顺序，防止被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 "a"，使其成为最近使用的
        assert cache.contains("a")
        cache.add("d")  # 应淘汰 "b"（最久未访问）
        assert cache.contains("a")
        assert not cache.contains("b")
        assert cache.contains("c")
        assert cache.contains("d")

    def test_remove(self):
        """remove 移除元素。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.remove("a")
        assert not cache.contains("a")

    def test_remove_nonexistent(self):
        """remove 不存在的元素不抛异常。"""
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")  # 不应抛异常

    def test_clear(self):
        """clear 清空所有元素。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert not cache.contains("a")
        assert not cache.contains("b")

    def test_add_duplicate_moves_to_end(self):
        """重复添加更新访问顺序。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 重复添加 "a"，使其成为最近使用的
        cache.add("a")
        cache.add("d")  # 应淘汰 "b"（最久未访问）
        assert cache.contains("a")
        assert not cache.contains("b")
        assert cache.contains("c")
        assert cache.contains("d")

    def test_maxsize_one(self):
        """maxsize=1 时正常工作。"""
        cache = LRUSet(maxsize=1)
        cache.add("a")
        assert cache.contains("a")
        cache.add("b")
        assert not cache.contains("a")
        assert cache.contains("b")

    def test_empty_cache_contains_false(self):
        """空缓存 contains 返回 False。"""
        cache = LRUSet(maxsize=10)
        assert not cache.contains("anything")