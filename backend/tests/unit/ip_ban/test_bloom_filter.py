"""BloomFilter 布隆过滤器测试。

覆盖：
- 添加和检查元素
- 不存在元素的假阴性率为 0
- 清空操作
- 边界条件（空字符串、大量元素）
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter


class TestBloomFilter:
    """BloomFilter 行为测试。"""

    def test_add_and_contains(self):
        """添加后元素应被检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1")

    def test_not_contains_unadded(self):
        """未添加的元素不应被检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("10.0.0.1")
        assert not bf.contains("192.168.1.1")

    def test_multiple_items(self):
        """多个元素都能正确添加和检测。"""
        bf = BloomFilter(size=10000)
        items = [f"10.0.0.{i}" for i in range(100)]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item)

    def test_clear(self):
        """清空后无元素被检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert not bf.contains("192.168.1.1")

    def test_empty_string(self):
        """空字符串可被添加和检测。"""
        bf = BloomFilter(size=1000)
        bf.add("")
        assert bf.contains("")

    def test_large_size(self):
        """大尺寸布隆过滤器正常工作。"""
        bf = BloomFilter(size=1_000_000)
        bf.add("10.0.0.1")
        assert bf.contains("10.0.0.1")

    def test_zero_false_negative(self):
        """已添加的元素不应有假阴性（对有限集合成立）。"""
        bf = BloomFilter(size=100_000)
        items = [f"10.0.0.{i}" for i in range(1000)]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item), f"假阴性: {item}"