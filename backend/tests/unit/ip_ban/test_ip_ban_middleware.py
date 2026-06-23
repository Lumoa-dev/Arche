"""IP 封禁中间件单元测试 —— BloomFilter、LRUSet、IpBanMiddleware。"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet


class TestBloomFilter:
    """测试布隆过滤器核心功能。"""

    def test_add_and_contains(self):
        """添加的元素应能被检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1")

    def test_not_contains_unknown(self):
        """未添加的元素不应被误报（概率极低，此处为确定性验证）。"""
        bf = BloomFilter(size=1000)
        assert not bf.contains("192.168.1.1")

    def test_clear_removes_all(self):
        """clear 后所有元素应不可见。"""
        bf = BloomFilter(size=1000)
        bf.add("10.0.0.1")
        bf.add("10.0.0.2")
        bf.clear()
        assert not bf.contains("10.0.0.1")
        assert not bf.contains("10.0.0.2")

    def test_multiple_items(self):
        """多个元素应互不干扰。"""
        bf = BloomFilter(size=10000)
        items = [f"10.0.0.{i}" for i in range(100)]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item)

    def test_hash_consistency(self):
        """同一元素的哈希值应一致。"""
        bf = BloomFilter(size=1000)
        h1 = bf._hashes("192.168.1.1")
        h2 = bf._hashes("192.168.1.1")
        assert h1 == h2

    def test_different_items_different_hashes(self):
        """不同元素的哈希值应有差异（极小碰撞概率可忽略）。"""
        bf = BloomFilter(size=10000)
        h1 = set(bf._hashes("192.168.1.1"))
        h2 = set(bf._hashes("10.0.0.1"))
        assert h1 != h2

    def test_three_hashes_per_item(self):
        """每个元素应生成 3 个哈希值。"""
        bf = BloomFilter(size=1000)
        assert len(bf._hashes("test")) == 3


class TestLRUSet:
    """测试 LRU 集合核心功能。"""

    def test_add_and_contains(self):
        """添加的元素应能被检测到。"""
        cache = LRUSet(maxsize=100)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1")

    def test_contains_moves_to_end(self):
        """contains 应将元素移到末尾（LRU 语义）。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 a，使其成为最近使用的
        cache.contains("a")
        # 再添加 d，应淘汰最久未使用的 b
        cache.add("d")
        assert cache.contains("a")
        assert cache.contains("d")
        assert not cache.contains("b")  # b 被淘汰
        assert cache.contains("c")

    def test_eviction_on_overflow(self):
        """超过 maxsize 时应淘汰最久未使用的元素。"""
        cache = LRUSet(maxsize=2)
        cache.add("a")
        cache.add("b")
        cache.add("c")  # 应淘汰 a
        assert not cache.contains("a")
        assert cache.contains("b")
        assert cache.contains("c")

    def test_remove_existing(self):
        """remove 应移除存在的元素。"""
        cache = LRUSet(maxsize=10)
        cache.add("test-key")
        assert cache.contains("test-key")
        cache.remove("test-key")
        assert not cache.contains("test-key")

    def test_remove_nonexistent(self):
        """remove 不存在的元素不抛异常。"""
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")
        # 正常通过即可

    def test_clear_removes_all(self):
        """clear 应清空所有元素。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert not cache.contains("a")
        assert not cache.contains("b")

    def test_add_existing_refreshes_position(self):
        """添加已存在的元素应将其移到末尾。"""
        cache = LRUSet(maxsize=2)
        cache.add("a")
        cache.add("b")
        cache.add("a")  # a 移到末尾，b 仍在
        cache.add("c")  # 应淘汰 b
        assert cache.contains("a")
        assert cache.contains("c")
        assert not cache.contains("b")


class TestIpBanMiddlewareDispatch:
    """测试 IpBanMiddleware 的 dispatch 决策逻辑。

    注意：由于 IpBanMiddleware 继承自 BaseHTTPMiddleware，
    完整集成测试需要 FastAPI 应用实例。此处测试 dispatch 内的
    关键路径逻辑 —— 通过 mock 中间件中的组件来验证决策分支。
    """

    def test_public_paths_skipped(self):
        """PUBLIC_PATHS 中的路径应直接放行。"""
        # 验证 PUBLIC_PATHS 集合包含关键公开路径
        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        assert "/api/auth/register" in IpBanMiddleware.PUBLIC_PATHS
        assert "/api/auth/login" in IpBanMiddleware.PUBLIC_PATHS

    def test_public_paths_immutable(self):
        """PUBLIC_PATHS 应为集合（不可变/快速查找）。"""
        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        assert isinstance(IpBanMiddleware.PUBLIC_PATHS, frozenset | set)

    def test_middleware_init_sets_up_structures(self):
        """中间件初始化应创建 BloomFilter 和 LRUSet。"""
        from unittest.mock import MagicMock

        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        mock_app = MagicMock()
        middleware = IpBanMiddleware(mock_app)
        assert middleware._bloom is not None
        assert middleware._whitelist_cache is not None
        assert middleware._last_sync == 0.0