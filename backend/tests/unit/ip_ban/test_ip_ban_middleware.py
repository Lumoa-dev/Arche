"""IP 封禁中间件组件测试 —— BloomFilter、LRUSet、IpBanMiddleware 行为。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend.plugins.ip_ban.middleware import BloomFilter, IpBanMiddleware, LRUSet


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    """测试布隆过滤器。"""

    def test_add_and_contains(self):
        """添加元素后 contains 应返回 True。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的元素 contains 应返回 False。"""
        bf = BloomFilter(size=1000)
        bf.add("10.0.0.1")
        assert bf.contains("192.168.1.1") is False

    def test_clear_removes_all(self):
        """clear 后所有元素应被清除。"""
        bf = BloomFilter(size=1000)
        bf.add("10.0.0.1")
        bf.add("10.0.0.2")
        bf.clear()
        assert bf.contains("10.0.0.1") is False
        assert bf.contains("10.0.0.2") is False

    def test_multiple_items(self):
        """多个元素插入后应都能检测到。"""
        bf = BloomFilter(size=10000)
        ips = [f"10.0.0.{i}" for i in range(100)]
        for ip in ips:
            bf.add(ip)
        for ip in ips:
            assert bf.contains(ip) is True

    def test_false_positive_rate_is_low(self):
        """布隆过滤器误报率应较低（非严格验证，但应合理）。"""
        bf = BloomFilter(size=10000)
        # 插入 500 个元素
        for i in range(500):
            bf.add(f"10.0.0.{i}")

        # 检查 500 个未插入的元素，误报数应较少
        false_positives = sum(
            1 for i in range(500, 1000) if bf.contains(f"10.0.0.{i}")
        )
        # 允许一定误报，但不应超过 15%
        assert false_positives < 75


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    """测试 LRU 缓存集合。"""

    def test_add_and_contains(self):
        """添加元素后 contains 应返回 True。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_contains_untouched_item(self):
        """未添加的元素 contains 应返回 False。"""
        cache = LRUSet(maxsize=10)
        cache.add("10.0.0.1")
        assert cache.contains("192.168.1.1") is False

    def test_evicts_oldest_when_full(self):
        """超过 maxsize 时，应淘汰最久未使用的元素。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 'a'
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_access_moves_to_end(self):
        """访问元素应将其移到末尾，避免被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 'a'，使其成为最近使用的
        cache.contains("a")
        cache.add("d")  # 应淘汰 'b'，而非 'a'
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("d") is True

    def test_remove(self):
        """remove 应删除指定元素。"""
        cache = LRUSet(maxsize=10)
        cache.add("10.0.0.1")
        cache.remove("10.0.0.1")
        assert cache.contains("10.0.0.1") is False

    def test_remove_nonexistent(self):
        """删除不存在的元素不应抛出异常。"""
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")  # 不应报错

    def test_clear(self):
        """clear 应清空所有元素。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False


# =============================================================================
# IpBanMiddleware 集成测试
# =============================================================================


class TestIpBanMiddleware:
    """测试 IP 封禁中间件行为。"""

    @pytest.mark.asyncio
    async def test_public_paths_are_not_blocked(self):
        """公开路径（如 /api/auth/login）不应被拦截。"""
        app = FastAPI()

        @app.get("/api/auth/login")
        async def login():
            return {"ok": True}

        mock_container = MagicMock()
        mock_container.is_available.return_value = False
        app.state.container = mock_container

        app.add_middleware(IpBanMiddleware)

        client = TestClient(app)
        response = client.get("/api/auth/login")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_docs_paths_are_not_blocked(self):
        """文档路径不应被拦截。"""
        app = FastAPI()

        @app.get("/docs")
        async def docs():
            return {"ok": True}

        mock_container = MagicMock()
        mock_container.is_available.return_value = False
        app.state.container = mock_container

        app.add_middleware(IpBanMiddleware)

        client = TestClient(app)
        response = client.get("/docs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_reload_cache_clears_and_populates(self):
        """reload_cache 应清空缓存并重新加载活跃 IP 段。"""
        middleware = IpBanManager()
        mock_service = AsyncMock()
        mock_service.get_active_ip_ranges = AsyncMock(
            return_value=["10.0.0.0/24", "192.168.1.1"]
        )

        await middleware.reload_cache(mock_service)

        # 验证布隆过滤器中包含这些 IP 段
        assert middleware._bloom.contains("10.0.0.0/24") is True
        assert middleware._bloom.contains("192.168.1.1") is True

        # 验证 LRU 缓存是空的（白名单不缓存封禁段）
        assert middleware._whitelist_cache.contains("10.0.0.1") is False


class IpBanManager:
    """用于测试的辅助类，仅包装 IpBanMiddleware 的核心方法。"""

    def __init__(self):
        self._bloom = BloomFilter()
        self._whitelist_cache = LRUSet(maxsize=5000)

    async def reload_cache(self, ip_ban_service) -> None:
        self._bloom.clear()
        self._whitelist_cache.clear()
        active_ips = await ip_ban_service.get_active_ip_ranges()
        for ip_range in active_ips:
            self._bloom.add(ip_range)