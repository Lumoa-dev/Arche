"""IP 封禁插件 — BloomFilter、LRUSet、Middleware 测试。

风险：布隆过滤器是 IP 封禁检查的第一道防线，假阴性会导致封禁绕过。
LRU 缓存错误会导致频繁查库或白名单污染。中间件 dispatch 逻辑错误
会导致误拦或漏放。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, IpBanMiddleware, LRUSet


class TestBloomFilter:
    """测试布隆过滤器。"""

    def setup_method(self):
        self.bf = BloomFilter(size=1000)

    def test_add_and_contains(self):
        """添加的元素应能被检测到。"""
        self.bf.add("192.168.1.1")
        assert self.bf.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的元素不应被检测到（可能有假阳性，但不应有假阴性）。"""
        assert self.bf.contains("10.0.0.1") is False

    def test_clear(self):
        """清除后所有元素不应被检测到。"""
        self.bf.add("192.168.1.1")
        self.bf.clear()
        assert self.bf.contains("192.168.1.1") is False

    def test_multiple_items(self):
        """多个元素应正确存储。"""
        ips = [f"10.0.0.{i}" for i in range(50)]
        for ip in ips:
            self.bf.add(ip)
        for ip in ips:
            assert self.bf.contains(ip) is True

    def test_no_false_negative(self):
        """布隆过滤器的核心保证：不应有假阴性。"""
        ips = [f"192.168.1.{i}" for i in range(10)]
        for ip in ips:
            self.bf.add(ip)
        for ip in ips:
            assert self.bf.contains(ip) is True

    def test_hashes_consistency(self):
        """相同输入的哈希值应一致。"""
        h1 = self.bf._hashes("test-ip")
        h2 = self.bf._hashes("test-ip")
        assert h1 == h2

    def test_different_inputs_different_hashes(self):
        """不同输入的哈希值应不同。"""
        h1 = self.bf._hashes("ip-a")
        h2 = self.bf._hashes("ip-b")
        assert h1 != h2


class TestLRUSet:
    """测试 LRU 集合。"""

    def setup_method(self):
        self.lru = LRUSet(maxsize=5)

    def test_add_and_contains(self):
        """添加的元素应能被检测到。"""
        self.lru.add("192.168.1.1")
        assert self.lru.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的元素应返回 False。"""
        assert self.lru.contains("10.0.0.1") is False

    def test_maxsize_eviction(self):
        """超过最大容量时应淘汰最久未使用的元素。"""
        for i in range(5):
            self.lru.add(f"10.0.0.{i}")

        # 此时已满，再次添加应淘汰最早的元素
        self.lru.add("10.0.0.99")
        assert self.lru.contains("10.0.0.0") is False  # 被淘汰
        assert self.lru.contains("10.0.0.99") is True  # 新加入

    def test_lru_promotion(self):
        """访问过的元素应被提升到最近使用位置。"""
        for i in range(5):
            self.lru.add(f"10.0.0.{i}")

        # 访问 10.0.0.0，使其变为最近使用
        self.lru.contains("10.0.0.0")

        # 添加新元素，应淘汰 10.0.0.1（最久未使用）
        self.lru.add("10.0.0.99")
        assert self.lru.contains("10.0.0.0") is True  # 被提升，未被淘汰
        assert self.lru.contains("10.0.0.1") is False  # 被淘汰

    def test_remove(self):
        """移除元素后应返回 False。"""
        self.lru.add("192.168.1.1")
        self.lru.remove("192.168.1.1")
        assert self.lru.contains("192.168.1.1") is False

    def test_remove_nonexistent(self):
        """移除不存在的元素不应抛出异常。"""
        self.lru.remove("non-existent")  # 不应抛出异常

    def test_clear(self):
        """清除后所有元素应返回 False。"""
        self.lru.add("192.168.1.1")
        self.lru.clear()
        assert self.lru.contains("192.168.1.1") is False

    def test_contains_promotes(self):
        """contains 调用应提升元素的 LRU 位置。"""
        self.lru = LRUSet(maxsize=3)
        self.lru.add("a")
        self.lru.add("b")
        self.lru.add("c")

        # 访问 a，使其变为最近使用
        self.lru.contains("a")
        self.lru.add("d")  # 应淘汰 b（最久未使用）

        assert self.lru.contains("a") is True
        assert self.lru.contains("b") is False
        assert self.lru.contains("d") is True


class TestIpBanMiddleware:
    """测试 IpBanMiddleware dispatch 逻辑。"""

    @pytest.fixture
    def mock_request(self):
        """创建模拟请求。"""
        request = MagicMock()
        request.url.path = "/api/some/resource"
        request.client.host = "192.168.1.100"
        request.app.state.container = MagicMock()
        request.app.state.container.is_available.return_value = True
        return request

    @pytest.fixture
    def mock_call_next(self):
        """创建模拟 next 处理器。"""
        return AsyncMock()

    @pytest.fixture
    def middleware(self):
        """创建中间件实例。"""
        app = MagicMock()
        return IpBanMiddleware(app)

    @pytest.mark.asyncio
    async def test_public_paths_bypass(self, middleware, mock_call_next):
        """公开路径应绕过 IP 封禁检查。"""
        for path in IpBanMiddleware.PUBLIC_PATHS:
            request = MagicMock()
            request.url.path = path
            await middleware.dispatch(request, mock_call_next)
            mock_call_next.assert_called()

    @pytest.mark.asyncio
    async def test_docs_paths_bypass(self, middleware, mock_call_next):
        """文档路径应绕过 IP 封禁检查。"""
        for prefix in ("/docs", "/openapi.json", "/redoc"):
            request = MagicMock()
            request.url.path = prefix
            await middleware.dispatch(request, mock_call_next)
            mock_call_next.assert_called()

    @pytest.mark.asyncio
    async def test_no_client_ip(self, middleware, mock_call_next):
        """无客户端 IP 时应放行。"""
        request = MagicMock()
        request.url.path = "/api/test"
        request.client = None
        await middleware.dispatch(request, mock_call_next)
        mock_call_next.assert_called()

    @pytest.mark.asyncio
    async def test_service_not_available(self, middleware, mock_call_next):
        """IP 封禁服务不可用时放行。"""
        request = MagicMock()
        request.url.path = "/api/test"
        request.client.host = "192.168.1.1"
        request.app.state.container.is_available.return_value = False
        await middleware.dispatch(request, mock_call_next)
        mock_call_next.assert_called()

    @pytest.mark.asyncio
    async def test_ip_in_whitelist_cache(self, middleware, mock_call_next):
        """白名单缓存中的 IP 应直接放行。"""
        request = MagicMock()
        request.url.path = "/api/test"
        request.client.host = "192.168.1.1"
        request.app.state.container.is_available.return_value = True

        # 先加入白名单
        middleware._whitelist_cache.add("192.168.1.1")

        await middleware.dispatch(request, mock_call_next)
        mock_call_next.assert_called()

    @pytest.mark.asyncio
    async def test_ip_banned_in_bloom(self, middleware, mock_call_next):
        """布隆过滤器命中的 IP 应调用服务检查。"""
        ip_service = AsyncMock()
        ip_service.is_ip_banned.return_value = True

        request = MagicMock()
        request.url.path = "/api/test"
        request.client.host = "192.168.1.1"
        request.app.state.container.is_available.return_value = True
        request.app.state.container.get.return_value = ip_service

        # 加入布隆过滤器
        middleware._bloom.add("192.168.1.1")

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_ip_not_banned_adds_to_cache(self, middleware, mock_call_next):
        """未封禁的 IP 应加入白名单缓存。"""
        ip_service = AsyncMock()
        ip_service.is_ip_banned.return_value = False

        request = MagicMock()
        request.url.path = "/api/test"
        request.client.host = "192.168.1.1"
        request.app.state.container.is_available.return_value = True
        request.app.state.container.get.return_value = ip_service

        await middleware.dispatch(request, mock_call_next)
        # IP 应加入布隆过滤器和白名单缓存
        assert middleware._bloom.contains("192.168.1.1") is True
        assert middleware._whitelist_cache.contains("192.168.1.1") is True

    @pytest.mark.asyncio
    async def test_reload_cache(self, middleware):
        """重新加载缓存应清空并重新填充。"""
        ip_service = AsyncMock()
        ip_service.get_active_ip_ranges.return_value = [
            "192.168.1.0/24", "10.0.0.0/8"
        ]

        # 先添加一些脏数据
        middleware._bloom.add("old-ip")
        middleware._whitelist_cache.add("old-ip")

        await middleware.reload_cache(ip_service)

        # 应清空
        assert middleware._bloom.contains("old-ip") is False
        # 应重新填充
        assert middleware._bloom.contains("192.168.1.0/24") is True
        assert middleware._bloom.contains("10.0.0.0/8") is True