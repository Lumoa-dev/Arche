"""IP 封禁中间件单元测试 —— 覆盖 BloomFilter、LRUSet 及中间件分发逻辑。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestBloomFilter:
    """布隆过滤器单元测试。"""

    @pytest.fixture
    def bf(self):
        from backend.plugins.ip_ban.middleware import BloomFilter
        return BloomFilter(size=1000)

    def test_add_and_contains(self, bf):
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains(self, bf):
        bf.add("192.168.1.1")
        assert bf.contains("10.0.0.1") is False

    def test_clear_removes_all(self, bf):
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False
        assert bf.contains("10.0.0.1") is False

    def test_multiple_items(self, bf):
        items = [f"10.0.0.{i}" for i in range(50)]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item) is True

    def test_empty_filter(self, bf):
        assert bf.contains("anything") is False

    def test_false_positive_rate_low(self, bf):
        """验证小数据量下误判率在可接受范围内。"""
        for i in range(100):
            bf.add(f"10.0.0.{i}")
        fp = sum(1 for i in range(100, 200) if bf.contains(f"10.0.0.{i}"))
        # 1000 bit 的布隆过滤器，100 个元素，误判率应 < 10%
        assert fp < 10


class TestLRUSet:
    """LRU 缓存集合单元测试。"""

    @pytest.fixture
    def lru(self):
        from backend.plugins.ip_ban.middleware import LRUSet
        return LRUSet(maxsize=5)

    def test_add_and_contains(self, lru):
        lru.add("192.168.1.1")
        assert lru.contains("192.168.1.1") is True

    def test_contains_moves_to_end(self, lru):
        lru.add("a")
        lru.add("b")
        lru.contains("a")  # a 被移到末尾
        lru.add("c")
        lru.add("d")
        lru.add("e")
        lru.add("f")  # 应淘汰 b（因为 a 被访问后顺序是 b, c, d, e, f）
        assert lru.contains("a") is True  # a 被保留
        assert lru.contains("b") is False  # b 被淘汰

    def test_eviction_oldest(self, lru):
        for i in range(5):
            lru.add(f"item_{i}")
        lru.add("new_item")  # 应淘汰 item_0
        assert lru.contains("item_0") is False
        assert lru.contains("new_item") is True

    def test_remove(self, lru):
        lru.add("a")
        lru.add("b")
        lru.remove("a")
        assert lru.contains("a") is False
        assert lru.contains("b") is True

    def test_remove_nonexistent(self, lru):
        lru.remove("nonexistent")  # 不应抛出异常

    def test_clear(self, lru):
        lru.add("a")
        lru.add("b")
        lru.clear()
        assert lru.contains("a") is False
        assert lru.contains("b") is False

    def test_not_contains(self, lru):
        assert lru.contains("anything") is False


class TestIpBanMiddleware:
    """IpBanMiddleware 分发逻辑测试。"""

    @pytest.mark.asyncio
    async def test_public_paths_skip_check(self):
        """PUBLIC_PATHS 中的路径应跳过封禁检查。"""
        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        app = MagicMock()
        mw = IpBanMiddleware(app)

        request = MagicMock()
        request.url.path = "/api/auth/login"
        call_next = AsyncMock(return_value="ok")

        result = await mw.dispatch(request, call_next)
        assert result == "ok"
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_docs_paths_skip_check(self):
        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        app = MagicMock()
        mw = IpBanMiddleware(app)

        for path in ("/docs", "/openapi.json", "/redoc"):
            request = MagicMock()
            request.url.path = path
            call_next = AsyncMock(return_value="ok")
            result = await mw.dispatch(request, call_next)
            assert result == "ok"

    @pytest.mark.asyncio
    async def test_no_client_ip_skips(self):
        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        app = MagicMock()
        mw = IpBanMiddleware(app)

        request = MagicMock()
        request.url.path = "/api/some"
        request.client = None
        call_next = AsyncMock(return_value="ok")

        result = await mw.dispatch(request, call_next)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_blocked_ip_returns_403(self):
        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        app = MagicMock()
        mw = IpBanMiddleware(app)

        request = MagicMock()
        request.url.path = "/api/some"
        request.client.host = "192.168.1.100"
        request.app.state.container.is_available.return_value = True

        ip_ban_service = AsyncMock()
        ip_ban_service.is_ip_banned.return_value = True
        request.app.state.container.get.return_value = ip_ban_service

        call_next = AsyncMock()
        response = await mw.dispatch(request, call_next)
        assert response.status_code == 403
        call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitelist_cache_bypasses_db(self):
        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        app = MagicMock()
        mw = IpBanMiddleware(app)

        # 先让 IP 进入白名单缓存
        mw._whitelist_cache.add("10.0.0.1")

        request = MagicMock()
        request.url.path = "/api/some"
        request.client.host = "10.0.0.1"
        request.app.state.container.is_available.return_value = True
        ip_ban_service = AsyncMock()
        request.app.state.container.get.return_value = ip_ban_service

        call_next = AsyncMock(return_value="ok")
        result = await mw.dispatch(request, call_next)
        assert result == "ok"
        # 不查询数据库
        ip_ban_service.is_ip_banned.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_container_not_available_skips(self):
        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        app = MagicMock()
        mw = IpBanMiddleware(app)

        request = MagicMock()
        request.url.path = "/api/some"
        request.client.host = "10.0.0.1"
        request.app.state.container.is_available.return_value = False

        call_next = AsyncMock(return_value="ok")
        result = await mw.dispatch(request, call_next)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_reload_cache_clears_and_rebuilds(self):
        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        app = MagicMock()
        mw = IpBanMiddleware(app)
        mw._bloom.add("old")
        mw._whitelist_cache.add("old")

        ip_ban_service = AsyncMock()
        ip_ban_service.get_active_ip_ranges.return_value = ["10.0.0.0/24", "192.168.1.0/24"]

        await mw.reload_cache(ip_ban_service)
        assert mw._bloom.contains("old") is False
        assert mw._whitelist_cache.contains("old") is False
        assert mw._bloom.contains("10.0.0.0/24") is True
        assert mw._bloom.contains("192.168.1.0/24") is True