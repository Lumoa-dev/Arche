"""IP 封禁中间件测试 —— BloomFilter / LRUSet / ip_matches_cidr。"""

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import ip_matches_cidr


class TestBloomFilter:
    """测试布隆过滤器。"""

    def setup_method(self):
        self.bloom = BloomFilter(size=1000)

    def test_add_and_contains(self):
        """添加后元素应被检测到。"""
        self.bloom.add("192.168.1.1")
        assert self.bloom.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的元素不应被检测到（可能有误报，但概率低）。"""
        self.bloom.add("192.168.1.1")
        # 不同元素大概率不被检测到
        assert self.bloom.contains("10.0.0.1") is False

    def test_clear(self):
        """清空后所有元素消失。"""
        self.bloom.add("192.168.1.1")
        self.bloom.clear()
        assert self.bloom.contains("192.168.1.1") is False

    def test_multiple_items(self):
        """多个元素添加后都能检测到。"""
        items = [f"10.0.0.{i}" for i in range(100)]
        for item in items:
            self.bloom.add(item)
        for item in items:
            assert self.bloom.contains(item) is True

    def test_empty_bloom(self):
        """空过滤器不包含任何元素。"""
        assert self.bloom.contains("any") is False

    def test_different_sizes(self):
        """不同大小的过滤器正常工作。"""
        small = BloomFilter(size=100)
        large = BloomFilter(size=100_000)
        small.add("test")
        large.add("test")
        assert small.contains("test") is True
        assert large.contains("test") is True


class TestLRUSet:
    """测试 LRU 缓存集合。"""

    def setup_method(self):
        self.cache = LRUSet(maxsize=5)

    def test_add_and_contains(self):
        """添加后元素可被检测到。"""
        self.cache.add("192.168.1.1")
        assert self.cache.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的元素返回 False。"""
        self.cache.add("192.168.1.1")
        assert self.cache.contains("10.0.0.1") is False

    def test_eviction(self):
        """超过最大容量时淘汰最早的元素。"""
        # 注意：contains() 会调用 move_to_end 更新 LRU 顺序
        for i in range(5):
            self.cache.add(f"item-{i}")
        # 此时缓存已满，item-0 是最早的
        # 添加新元素，淘汰最早的元素（item-0）
        self.cache.add("item-5")
        assert self.cache.contains("item-0") is False  # 被淘汰
        assert self.cache.contains("item-5") is True

    def test_recently_used_preserved(self):
        """最近使用的元素不会被淘汰。"""
        for i in range(5):
            self.cache.add(f"item-{i}")
        # 访问 item-0，使其成为最近使用
        self.cache.contains("item-0")
        # 添加新元素
        self.cache.add("item-5")
        # item-0 因最近使用而保留
        assert self.cache.contains("item-0") is True
        # item-1 被淘汰
        assert self.cache.contains("item-1") is False

    def test_remove(self):
        """移除元素后不再包含。"""
        self.cache.add("test-item")
        assert self.cache.contains("test-item") is True
        self.cache.remove("test-item")
        assert self.cache.contains("test-item") is False

    def test_remove_nonexistent(self):
        """移除不存在的元素不报错。"""
        self.cache.remove("nonexistent")  # 不应抛出异常

    def test_clear(self):
        """清空后所有元素消失。"""
        self.cache.add("item-1")
        self.cache.add("item-2")
        self.cache.clear()
        assert self.cache.contains("item-1") is False
        assert self.cache.contains("item-2") is False

    def test_duplicate_add(self):
        """重复添加同一元素更新 LRU 顺序。"""
        self.cache.add("item-1")
        self.cache.add("item-2")
        self.cache.add("item-3")
        self.cache.add("item-4")
        self.cache.add("item-5")
        # 重新添加 item-1，使其成为最近使用
        self.cache.add("item-1")
        # 添加新元素，item-2 被淘汰（item-1 最近使用）
        self.cache.add("item-6")
        assert self.cache.contains("item-1") is True
        assert self.cache.contains("item-2") is False


class TestIpMatchesCidr:
    """测试 IP/CIDR 匹配函数。"""

    def test_ipv4_exact_match(self):
        """精确 IPv4 地址匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1") is True

    def test_ipv4_in_cidr(self):
        """IPv4 在 CIDR 段内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_cidr(self):
        """IPv4 不在 CIDR 段内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_single_host_cidr(self):
        """/32 精确匹配。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1/32") is True
        assert ip_matches_cidr("10.0.0.2", "10.0.0.1/32") is False

    def test_ipv6_in_cidr(self):
        """IPv6 在 CIDR 段内。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_invalid_ip_format(self):
        """无效 IP 格式返回 False。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_format(self):
        """无效 CIDR 格式返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_empty_strings(self):
        """空字符串返回 False。"""
        assert ip_matches_cidr("", "") is False

    def test_private_ip_range(self):
        """私有 IP 范围匹配。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.0/8") is True
        assert ip_matches_cidr("172.16.0.1", "172.16.0.0/12") is True
        assert ip_matches_cidr("192.168.0.1", "192.168.0.0/16") is True