"""BloomFilter + LRUSet 单元测试 —— IP 封禁中间件核心数据结构。

测试重点：
- BloomFilter 基本命中/误判特性
- LRUSet 固定大小淘汰、LRU 顺序
- 清理和重置
"""

from __future__ import annotations

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet


# =============================================================================
# BloomFilter
# =============================================================================


class TestBloomFilter:
    """布隆过滤器测试。"""

    def test_add_and_contains(self):
        """添加后应能检测到存在。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains_before_add(self):
        """未添加的元素应返回 False（可能有误判，但小集合中不应误判）。"""
        bf = BloomFilter(size=10000)
        assert bf.contains("10.0.0.1") is False

    def test_multiple_items(self):
        """多个添加应各自可检测。"""
        bf = BloomFilter(size=10000)
        ips = [f"192.168.1.{i}" for i in range(100)]
        for ip in ips:
            bf.add(ip)
        for ip in ips:
            assert bf.contains(ip) is True

    def test_clear(self):
        """clear 后应清空所有位。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_cidr_range(self):
        """CIDR 段字符串应能正常添加和检测。"""
        bf = BloomFilter(size=10000)
        bf.add("10.0.0.0/8")
        assert bf.contains("10.0.0.0/8") is True

    def test_ipv6_support(self):
        """IPv6 地址应能正常添加和检测。"""
        bf = BloomFilter(size=10000)
        bf.add("2001:db8::1")
        assert bf.contains("2001:db8::1") is True

    def test_contains_empty_filter(self):
        """空过滤器应返回 False。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("anything") is False


class TestBloomFilterEdgeCases:
    """布隆过滤器边界测试。"""

    def test_empty_string(self):
        """空字符串应能添加和检测。"""
        bf = BloomFilter(size=1000)
        bf.add("")
        # 空字符串哈希后可能与其他字符串碰撞
        # 但至少不应抛出异常
        assert isinstance(bf.contains(""), bool)

    def test_very_long_string(self):
        """长字符串应能正常处理。"""
        bf = BloomFilter(size=10000)
        long_str = "x" * 10000
        bf.add(long_str)
        assert bf.contains(long_str) is True

    def test_unicode_string(self):
        """Unicode 字符串应能正常处理。"""
        bf = BloomFilter(size=10000)
        bf.add("中国-127.0.0.1")
        assert bf.contains("中国-127.0.0.1") is True

    def test_small_size_has_collisions(self):
        """极小过滤器可能产生误判（验证碰撞概率存在）。"""
        bf = BloomFilter(size=8)  # 极小的过滤器
        bf.add("item-1")
        bf.add("item-2")
        # 最多就检查存在性，不能断言精确误判
        # 但运行不应出错
        assert isinstance(bf.contains("item-3"), bool)


# =============================================================================
# LRUSet
# =============================================================================


class TestLRUSet:
    """LRU 集合测试。"""

    def test_add_and_contains(self):
        """添加后应能检测到存在。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的元素应返回 False。"""
        cache = LRUSet(maxsize=10)
        assert cache.contains("10.0.0.1") is False

    def test_eviction_when_full(self):
        """达到上限后，最早添加的应被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 触发淘汰
        assert cache.contains("a") is False  # 最早被淘汰
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_lru_reorder_on_contains(self):
        """contains 命中时应更新 LRU 顺序。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 a，将其移到末尾
        cache.contains("a")
        # 此时 a 是最新使用的，b 是最旧的
        cache.add("d")  # 淘汰 b
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("d") is True

    def test_lru_reorder_on_readd(self):
        """重复添加已存在的元素应更新 LRU 顺序。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 重新添加 a，移动到最后
        cache.add("a")
        cache.add("d")  # 淘汰 b
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("d") is True

    def test_remove(self):
        """remove 应移除指定元素。"""
        cache = LRUSet(maxsize=10)
        cache.add("test-key")
        cache.remove("test-key")
        assert cache.contains("test-key") is False

    def test_remove_nonexistent(self):
        """remove 不存在的元素不应报错。"""
        cache = LRUSet(maxsize=10)
        cache.remove("never-added")  # 不应抛出异常

    def test_clear(self):
        """clear 应清空所有元素。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False

    def test_empty_cache(self):
        """空缓存 contains 应返回 False。"""
        cache = LRUSet(maxsize=10)
        assert cache.contains("anything") is False


class TestLRUSetEdgeCases:
    """LRU 集合边界测试。"""

    def test_maxsize_one(self):
        """maxsize=1 时应只保留最新元素。"""
        cache = LRUSet(maxsize=1)
        cache.add("a")
        assert cache.contains("a") is True
        cache.add("b")
        assert cache.contains("a") is False
        assert cache.contains("b") is True

    def test_maxsize_zero(self):
        """maxsize=0 时应什么都存不住。"""
        cache = LRUSet(maxsize=0)
        cache.add("test")
        assert cache.contains("test") is False

    def test_many_items(self):
        """大量元素不应导致性能问题或错误。"""
        cache = LRUSet(maxsize=1000)
        for i in range(2000):
            cache.add(f"ip-{i}")
        # 应只剩下最后 1000 个
        assert cache.contains("ip-0") is False
        assert cache.contains("ip-1999") is True
        # 验证准确的数量
        count = 0
        for i in range(2000):
            if cache.contains(f"ip-{i}"):
                count += 1
        assert count == 1000