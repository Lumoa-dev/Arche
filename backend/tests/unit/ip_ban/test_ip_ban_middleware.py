"""IP 封禁中间件单元测试 —— BloomFilter、LRUSet、Middleware 调度。

测试原则：
- BloomFilter 和 LRUSet 为纯内存结构，无需数据库
- Middleware dispatch 逻辑通过单元验证边界条件
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, IpBanMiddleware, LRUSet


# =============================================================================
# BloomFilter
# =============================================================================


class TestBloomFilter:
    """测试布隆过滤器。"""

    def test_add_and_contains(self):
        """添加后应能检测到元素存在。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")
        assert bf.contains("192.168.1.1") is True
        assert bf.contains("10.0.0.1") is True

    def test_not_contains(self):
        """未添加的元素应返回 False。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("8.8.8.8") is False

    def test_clear_resets_filter(self):
        """清除后应不再包含任何元素。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_empty_filter(self):
        """空过滤器对任何元素都应返回 False。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("any.ip") is False

    def test_hashes_consistent(self):
        """同一元素的哈希结果应稳定一致。"""
        bf = BloomFilter(size=1000)
        h1 = bf._hashes("test")
        h2 = bf._hashes("test")
        assert h1 == h2


# =============================================================================
# LRUSet
# =============================================================================


class TestLRUSet:
    """测试 LRU 缓存集合。"""

    def test_add_and_contains(self):
        """添加后应能查询到。"""
        cache = LRUSet(maxsize=5)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的元素应返回 False。"""
        cache = LRUSet(maxsize=5)
        assert cache.contains("8.8.8.8") is False

    def test_eviction_when_full(self):
        """超过最大容量时最久未使用的元素应被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("A")
        cache.add("B")
        cache.add("C")
        cache.add("D")  # 应淘汰 A
        assert cache.contains("A") is False
        assert cache.contains("D") is True

    def test_recent_use_prevents_eviction(self):
        """最近使用的元素不应被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("A")
        cache.add("B")
        cache.add("C")
        cache.contains("A")  # A 被移到末尾
        cache.add("D")  # 应淘汰 B
        assert cache.contains("A") is True
        assert cache.contains("B") is False

    def test_remove(self):
        """移除后元素应不再存在。"""
        cache = LRUSet(maxsize=5)
        cache.add("192.168.1.1")
        cache.remove("192.168.1.1")
        assert cache.contains("192.168.1.1") is False

    def test_remove_nonexistent(self):
        """移除不存在的元素不应抛异常。"""
        cache = LRUSet(maxsize=5)
        cache.remove("nonexistent")  # 不应抛异常

    def test_clear(self):
        """清除后应为空。"""
        cache = LRUSet(maxsize=5)
        cache.add("A")
        cache.add("B")
        cache.clear()
        assert cache.contains("A") is False
        assert cache.contains("B") is False


# =============================================================================
# IpBanMiddleware Dispatch
# =============================================================================


class TestIpBanMiddlewareDispatch:
    """测试中间件调度逻辑（白名单、布隆过滤器、封禁拦截）。"""

    @pytest.mark.asyncio
    async def test_public_paths_skip_check(self):
        """公开路径（login/register）应跳过 IP 检查。"""
        mock_app = MagicMock()
        middleware = IpBanMiddleware(mock_app)

        for path in ["/api/auth/register", "/api/auth/login"]:
            request = MagicMock()
            request.url.path = path
            request.client.host = "10.0.0.1"

            call_next = AsyncMock()
            await middleware.dispatch(request, call_next)
            call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_docs_paths_skip_check(self):
        """文档路径应跳过 IP 检查。"""
        mock_app = MagicMock()
        middleware = IpBanMiddleware(mock_app)

        for path in ["/docs", "/openapi.json", "/redoc"]:
            request = MagicMock()
            request.url.path = path
            request.client.host = "10.0.0.1"

            call_next = AsyncMock()
            await middleware.dispatch(request, call_next)
            call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_client_ip_passes_through(self):
        """无客户端 IP 时应放行。"""
        mock_app = MagicMock()
        middleware = IpBanMiddleware(mock_app)

        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client = None

        call_next = AsyncMock()
        await middleware.dispatch(request, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_service_unavailable_passes_through(self):
        """ip_ban 服务不可用时应放行。"""
        mock_app = MagicMock()
        middleware = IpBanMiddleware(mock_app)

        container = MagicMock()
        container.is_available.return_value = False
        mock_app.state.container = container

        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        request.app = mock_app

        call_next = AsyncMock()
        await middleware.dispatch(request, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_whitelist_cache_bypasses_check(self):
        """在白名单缓存中的 IP 应跳过封禁检查直接放行。"""
        mock_app = MagicMock()
        middleware = IpBanMiddleware(mock_app)

        # 将 IP 放入白名单缓存
        middleware._whitelist_cache.add("10.0.0.1")

        container = MagicMock()
        container.is_available.return_value = True
        container.get.return_value = MagicMock()
        mock_app.state.container = container

        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        request.app = mock_app

        call_next = AsyncMock()
        await middleware.dispatch(request, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_banned_ip_returns_403(self):
        """被封禁的 IP 应返回 403。"""
        mock_app = MagicMock()
        middleware = IpBanMiddleware(mock_app)

        ip_ban_service = AsyncMock()
        ip_ban_service.is_ip_banned = AsyncMock(return_value=True)

        container = MagicMock()
        container.is_available.return_value = True
        container.get.return_value = ip_ban_service
        mock_app.state.container = container

        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        request.app = mock_app

        call_next = AsyncMock()
        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 403
        call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_not_banned_ip_passes_through_and_adds_to_bloom(self):
        """未被封禁的 IP 应放行并加入布隆过滤器。"""
        mock_app = MagicMock()
        middleware = IpBanMiddleware(mock_app)

        ip_ban_service = AsyncMock()
        ip_ban_service.is_ip_banned = AsyncMock(return_value=False)

        container = MagicMock()
        container.is_available.return_value = True
        container.get.return_value = ip_ban_service
        mock_app.state.container = container

        request = MagicMock()
        request.url.path = "/api/some-path"
        request.client.host = "10.0.0.1"
        request.app = mock_app

        call_next = AsyncMock(return_value=MagicMock(status_code=200))
        response = await middleware.dispatch(request, call_next)

        call_next.assert_awaited_once()
        assert response.status_code == 200
        # IP 应加入布隆过滤器
        assert middleware._bloom.contains("10.0.0.1") is True
        assert middleware._whitelist_cache.contains("10.0.0.1") is True