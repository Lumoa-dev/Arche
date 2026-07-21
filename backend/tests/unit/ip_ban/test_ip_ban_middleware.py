"""IP 封禁中间件单元测试 —— BloomFilter, LRUSet, IpBanMiddleware dispatch。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, IpBanMiddleware, LRUSet


# =============================================================================
# BloomFilter
# =============================================================================


class TestBloomFilter:
    """测试布隆过滤器的基本操作。"""

    def test_add_and_contains(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains(self):
        bf = BloomFilter(size=1000)
        assert bf.contains("10.0.0.1") is False

    def test_clear_removes_all(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False
        assert bf.contains("10.0.0.1") is False

    def test_false_positive_possible(self):
        """布隆过滤器允许误判，但不应漏判。"""
        bf = BloomFilter(size=100)
        # 添加大量不同 IP，部分可能会产生哈希碰撞
        for i in range(50):
            bf.add(f"10.0.0.{i}")
        # 已添加的 IP 必须都能 contains
        for i in range(50):
            assert bf.contains(f"10.0.0.{i}") is True

    def test_empty_filter(self):
        bf = BloomFilter(size=1000)
        assert bf.contains("") is False

    def test_unicode_ip(self):
        bf = BloomFilter(size=1000)
        bf.add("2001:db8::1")
        assert bf.contains("2001:db8::1") is True

    def test_hashes_consistent(self):
        """同一 item 的哈希值应始终一致。"""
        bf = BloomFilter(size=10000)
        h1 = bf._hashes("192.168.1.1")
        h2 = bf._hashes("192.168.1.1")
        assert h1 == h2

    def test_different_items_different_hashes(self):
        """不同 item 的哈希值应不同。"""
        bf = BloomFilter(size=10000)
        h1 = set(bf._hashes("192.168.1.1"))
        h2 = set(bf._hashes("192.168.1.2"))
        # 哈希碰撞概率极低，这里验证至少 1 个位置不同
        assert h1 != h2


# =============================================================================
# LRUSet
# =============================================================================


class TestLRUSet:
    """测试 LRU 集合的基本操作。"""

    def test_add_and_contains(self):
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_not_contains(self):
        cache = LRUSet(maxsize=10)
        assert cache.contains("10.0.0.1") is False

    def test_eviction_when_full(self):
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 "a"
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_lru_reorder_on_contains(self):
        """contains 操作应将被访问的项移到末尾。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 "a" 使其成为最近使用
        cache.contains("a")
        cache.add("d")  # 应淘汰 "b"（最久未使用）
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("d") is True

    def test_lru_reorder_on_add_existing(self):
        """重复添加应移动而非淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("a")  # "a" 已存在，move_to_end
        cache.add("d")  # 应淘汰 "b"
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("d") is True

    def test_remove(self):
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.remove("a")
        assert cache.contains("a") is False
        assert cache.contains("b") is True

    def test_remove_nonexistent_no_error(self):
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")  # 不应抛异常

    def test_clear(self):
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False

    def test_empty_cache(self):
        cache = LRUSet(maxsize=10)
        assert cache.contains("anything") is False

    def test_maxsize_zero(self):
        """maxsize=0 时，添加任何项都应立即淘汰。"""
        cache = LRUSet(maxsize=0)
        cache.add("a")
        assert cache.contains("a") is False


# =============================================================================
# IpBanMiddleware — dispatch 逻辑
# =============================================================================


class TestIpBanMiddlewareDispatch:
    """测试 IpBanMiddleware 的请求调度路径。"""

    @pytest.fixture
    def mock_app(self):
        """创建可被 call_next 调用的 mock app。"""
        app = MagicMock()
        app.state.container = MagicMock()
        return app

    @pytest.fixture
    def middleware(self, mock_app):
        return IpBanMiddleware(mock_app)

    async def test_public_paths_skip_check(self, middleware):
        """公开路径应直接放行，不检查 IP。"""
        request = MagicMock()
        request.url.path = "/api/auth/login"
        call_next = AsyncMock()
        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value
        call_next.assert_awaited_once_with(request)

    async def test_docs_paths_skip_check(self, middleware):
        """文档路径应直接放行。"""
        request = MagicMock()
        request.url.path = "/docs"
        call_next = AsyncMock()
        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value

    async def test_no_client_ip_skips_check(self, middleware):
        """无 client IP 时应直接放行。"""
        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client = None
        call_next = AsyncMock()
        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value

    async def test_empty_client_ip_skips_check(self, middleware):
        """client IP 为空字符串时应直接放行。"""
        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = ""
        call_next = AsyncMock()
        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value

    async def test_container_unavailable_skips_check(self, middleware):
        """容器不可用时（异常）应直接放行。"""
        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        request.app.state = MagicMock()
        # 模拟 container 访问异常
        del request.app.state.container
        call_next = AsyncMock()
        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value

    async def test_ip_ban_service_not_available_skips(self, middleware):
        """ip_ban service 不可用时应直接放行。"""
        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        container = MagicMock()
        container.is_available.return_value = False
        request.app.state.container = container
        call_next = AsyncMock()
        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value

    async def test_ip_in_whitelist_cache_skips_db_check(self, middleware):
        """IP 在 LRU 白名单缓存中时，应直接放行，不查 DB。"""
        middleware._whitelist_cache.add("10.0.0.1")

        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        container = MagicMock()
        container.is_available.return_value = True
        request.app.state.container = container
        call_next = AsyncMock()
        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value

    async def test_ip_in_bloom_filter_and_banned_returns_403(self, middleware):
        """IP 在布隆过滤器且被封禁时，应返回 403。"""
        middleware._bloom.add("10.0.0.1")

        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=True)

        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        container = MagicMock()
        container.is_available.return_value = True
        container.get.return_value = mock_service
        request.app.state.container = container
        call_next = AsyncMock()

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 403

        import json

        body = json.loads(response.body)
        assert body["code"] == "ip_banned"

    async def test_ip_in_bloom_filter_not_banned_adds_to_whitelist(self, middleware):
        """IP 在布隆过滤器中但未被封禁时，应加入白名单缓存并放行。"""
        middleware._bloom.add("10.0.0.1")

        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=False)

        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        container = MagicMock()
        container.is_available.return_value = True
        container.get.return_value = mock_service
        request.app.state.container = container
        call_next = AsyncMock()

        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value
        # 应加入白名单缓存
        assert middleware._whitelist_cache.contains("10.0.0.1") is True

    async def test_ip_not_in_bloom_banned_returns_403(self, middleware):
        """IP 不在布隆过滤器但实际被封禁时，应返回 403。"""
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=True)

        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        container = MagicMock()
        container.is_available.return_value = True
        container.get.return_value = mock_service
        request.app.state.container = container
        call_next = AsyncMock()

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 403

    async def test_ip_not_in_bloom_not_banned_adds_to_bloom_and_whitelist(
        self, middleware
    ):
        """IP 不在布隆过滤器且未被封禁时，应加入布隆过滤器和白名单。"""
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=False)

        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        container = MagicMock()
        container.is_available.return_value = True
        container.get.return_value = mock_service
        request.app.state.container = container
        call_next = AsyncMock()

        response = await middleware.dispatch(request, call_next)
        assert response == call_next.return_value
        assert middleware._bloom.contains("10.0.0.1") is True
        assert middleware._whitelist_cache.contains("10.0.0.1") is True


class TestIpBanMiddlewareReloadCache:
    """测试 reload_cache 方法。"""

    async def test_reload_cache_clears_and_reloads(self):
        middleware = IpBanMiddleware(MagicMock())
        middleware._bloom.add("10.0.0.1")
        middleware._whitelist_cache.add("192.168.1.1")

        mock_service = AsyncMock()
        mock_service.get_active_ip_ranges = AsyncMock(
            return_value=["10.0.0.0/24", "192.168.1.1"]
        )

        await middleware.reload_cache(mock_service)

        # Bloom 应包含活跃 IP 范围
        assert middleware._bloom.contains("10.0.0.0/24") is True
        assert middleware._bloom.contains("192.168.1.1") is True
        # 旧数据应被清除
        assert middleware._bloom.contains("10.0.0.1") is False
        # 白名单应被清空
        assert middleware._whitelist_cache.contains("192.168.1.1") is False

    async def test_reload_cache_empty_active_ips(self):
        """无活跃 IP 时，reload 后 bloom 应为空。"""
        middleware = IpBanMiddleware(MagicMock())
        middleware._bloom.add("10.0.0.1")

        mock_service = AsyncMock()
        mock_service.get_active_ip_ranges = AsyncMock(return_value=[])

        await middleware.reload_cache(mock_service)
        assert middleware._bloom.contains("10.0.0.1") is False