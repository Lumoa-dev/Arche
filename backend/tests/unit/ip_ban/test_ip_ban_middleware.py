"""IP 封禁中间件单元测试。

覆盖 BloomFilter、LRUSet 和 IpBanMiddleware 的核心逻辑。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, IpBanMiddleware, LRUSet


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    def test_add_and_contains(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains(self):
        bf = BloomFilter(size=1000)
        assert bf.contains("10.0.0.1") is False

    def test_clear(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_multiple_items(self):
        bf = BloomFilter(size=10000)
        ips = [f"10.0.0.{i}" for i in range(100)]
        for ip in ips:
            bf.add(ip)
        for ip in ips:
            assert bf.contains(ip) is True

    def test_different_items(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.2") is False
        assert bf.contains("10.0.0.1") is False


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    def test_add_and_contains(self):
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_not_contains(self):
        cache = LRUSet(maxsize=10)
        assert cache.contains("10.0.0.1") is False

    def test_eviction(self):
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 a
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_remove(self):
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        cache.remove("192.168.1.1")
        assert cache.contains("192.168.1.1") is False

    def test_clear(self):
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False

    def test_add_moves_to_end(self):
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("a")  # 重添加 a，应移到末尾，不触发淘汰
        cache.add("d")  # 应淘汰 b
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("c") is True
        assert cache.contains("d") is True


# =============================================================================
# IpBanMiddleware 逻辑测试
# =============================================================================


class TestIpBanMiddleware:
    def test_public_paths_bypass(self):
        """公开路径不应被拦截。"""
        assert "/api/auth/login" in IpBanMiddleware.PUBLIC_PATHS
        assert "/api/auth/register" in IpBanMiddleware.PUBLIC_PATHS

    def test_public_paths_exact_match(self):
        """PUBLIC_PATHS 是精确匹配，不是前缀匹配。"""
        assert "/api/auth/login" in IpBanMiddleware.PUBLIC_PATHS
        # 确保没有多余路径
        assert len(IpBanMiddleware.PUBLIC_PATHS) == 2

    @pytest.mark.asyncio
    async def test_dispatch_public_path_skips_check(self):
        """公开路径绕过中间件检查。"""
        mock_request = MagicMock()
        mock_request.url.path = "/api/auth/login"
        mock_request.client = None

        call_next = AsyncMock(return_value="passed")
        middleware = IpBanMiddleware(MagicMock())

        result = await middleware.dispatch(mock_request, call_next)
        assert result == "passed"
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_docs_path_skips(self):
        """文档路径绕过中间件检查。"""
        mock_request = MagicMock()
        mock_request.url.path = "/docs"
        mock_request.client = None

        call_next = AsyncMock(return_value="passed")
        middleware = IpBanMiddleware(MagicMock())

        result = await middleware.dispatch(mock_request, call_next)
        assert result == "passed"

    @pytest.mark.asyncio
    async def test_dispatch_without_client_skips(self):
        """无客户端 IP 时跳过检查。"""
        mock_request = MagicMock()
        mock_request.url.path = "/api/some-path"
        mock_request.client = None

        call_next = AsyncMock(return_value="passed")
        middleware = IpBanMiddleware(MagicMock())

        result = await middleware.dispatch(mock_request, call_next)
        assert result == "passed"

    @pytest.mark.asyncio
    async def test_dispatch_container_unavailable_skips(self):
        """容器无 ip_ban 服务时跳过检查。"""
        mock_request = MagicMock()
        mock_request.url.path = "/api/some-path"
        mock_request.client.host = "10.0.0.1"

        mock_container = MagicMock()
        mock_container.is_available.return_value = False

        mock_app = MagicMock()
        mock_app.state.container = mock_container
        mock_request.app = mock_app

        call_next = AsyncMock(return_value="passed")
        middleware = IpBanMiddleware(MagicMock())

        result = await middleware.dispatch(mock_request, call_next)
        assert result == "passed"

    @pytest.mark.asyncio
    async def test_dispatch_banned_ip_returns_403(self):
        """被封禁的 IP 返回 403。"""
        mock_request = MagicMock()
        mock_request.url.path = "/api/some-path"
        mock_request.client.host = "10.0.0.1"

        mock_ban_service = AsyncMock()
        mock_ban_service.is_ip_banned = AsyncMock(return_value=True)

        mock_container = MagicMock()
        mock_container.is_available.return_value = True
        mock_container.get.return_value = mock_ban_service

        mock_app = MagicMock()
        mock_app.state.container = mock_container
        mock_request.app = mock_app

        call_next = AsyncMock(return_value="passed")
        middleware = IpBanMiddleware(MagicMock())

        response = await middleware.dispatch(mock_request, call_next)
        assert response.status_code == 403
        assert "ip_banned" in str(response.body)

    @pytest.mark.asyncio
    async def test_dispatch_unbanned_ip_passes(self):
        """未封禁的 IP 正常通过。"""
        mock_request = MagicMock()
        mock_request.url.path = "/api/some-path"
        mock_request.client.host = "10.0.0.1"

        mock_ban_service = AsyncMock()
        mock_ban_service.is_ip_banned = AsyncMock(return_value=False)

        mock_container = MagicMock()
        mock_container.is_available.return_value = True
        mock_container.get.return_value = mock_ban_service

        mock_app = MagicMock()
        mock_app.state.container = mock_container
        mock_request.app = mock_app

        call_next = AsyncMock(return_value="passed")
        middleware = IpBanMiddleware(MagicMock())

        result = await middleware.dispatch(mock_request, call_next)
        assert result == "passed"