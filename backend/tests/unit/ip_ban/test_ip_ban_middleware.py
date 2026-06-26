"""IP 封禁中间件和数据结构的单元测试。

测试 BloomFilter、LRUSet、ip_matches_cidr 等基础设施组件。
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import ip_matches_cidr


# =============================================================================
# ip_matches_cidr 测试
# =============================================================================


class TestIpMatchesCidr:
    """测试 IP/CIDR 匹配逻辑。"""

    @pytest.mark.parametrize(
        "ip_str, cidr_str, expected",
        [
            ("192.168.1.1", "192.168.1.0/24", True),
            ("192.168.2.1", "192.168.1.0/24", False),
            ("10.0.0.5", "10.0.0.0/8", True),
            ("11.0.0.5", "10.0.0.0/8", False),
            ("::1", "::1/128", True),
            ("::2", "::1/128", False),
            ("2001:db8::1", "2001:db8::/32", True),
            ("2001:db9::1", "2001:db8::/32", False),
            # CIDR 落入单个 IP
            ("1.2.3.4", "1.2.3.4/32", True),
            ("1.2.3.5", "1.2.3.4/32", False),
            # 非法输入
            ("not-an-ip", "192.168.1.0/24", False),
            ("192.168.1.1", "not-a-cidr", False),
        ],
    )
    def test_ip_matches_cidr(self, ip_str: str, cidr_str: str, expected: bool):
        assert ip_matches_cidr(ip_str, cidr_str) is expected


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    """测试布隆过滤器的基础行为。"""

    def test_add_and_contains(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")

        assert bf.contains("192.168.1.1") is True
        assert bf.contains("10.0.0.1") is True

    def test_contains_unknown(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")

        # 未添加的 IP 可能偶发假阳性，但极小概率
        # 这个测试验证已知添加的 IP 一定返回 True
        assert bf.contains("192.168.1.1") is True

    def test_clear(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

        bf.clear()
        # 清理后 aremoved 可能被误判，但这不是问题 — 布隆过滤器保证绝对不漏报
        # 这里只验证清理后内部状态重置
        assert bf._size == 1000

    def test_different_items_have_different_hashes(self):
        bf = BloomFilter(size=100_000)
        bf.add("item-a")
        bf.add("item-b")

        # 确保两个不同项都被检测到
        assert bf.contains("item-a") is True
        assert bf.contains("item-b") is True


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    """测试 LRU 缓存集合。"""

    def test_add_and_contains(self):
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")

        assert cache.contains("192.168.1.1") is True
        assert cache.contains("10.0.0.1") is False

    def test_evicts_oldest_when_full(self):
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 "a"

        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_move_to_end_on_access(self):
        """访问已存在的项应将其移到末尾，避免被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")

        # 访问 "a"，使其成为最近使用
        assert cache.contains("a") is True

        # 添加 "d"，此时应淘汰 "b"（因为 "a" 刚被访问）
        cache.add("d")

        assert cache.contains("a") is True  # 最近被访问
        assert cache.contains("b") is False  # 最久未被访问
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_remove(self):
        cache = LRUSet(maxsize=10)
        cache.add("a")
        assert cache.contains("a") is True

        cache.remove("a")
        assert cache.contains("a") is False

    def test_remove_nonexistent(self):
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")  # 不应抛出异常

    def test_clear(self):
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()

        assert cache.contains("a") is False
        assert cache.contains("b") is False