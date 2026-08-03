"""IP 封禁中间件 —— BloomFilter / LRUSet / IpBanMiddleware 行为测试。

测试原则：
- BloomFilter 和 LRUSet 是纯内存数据结构，同步测试
- IpBanMiddleware 用 mock 隔离外部依赖
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from backend.plugins.ip_ban.middleware import BloomFilter, IpBanMiddleware, LRUSet


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    """布隆过滤器行为测试。"""

    def test_add_and_contains(self):
        """添加的元素应能被检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的元素应返回 False。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("10.0.0.1") is False

    def test_clear_removes_all(self):
        """清空后所有元素应返回 False。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_multiple_items(self):
        """多个元素应都能正确检测。"""
        bf = BloomFilter(size=10000)
        ips = [f"10.0.0.{i}" for i in range(100)]
        for ip in ips:
            bf.add(ip)
        for ip in ips:
            assert bf.contains(ip) is True

    def test_false_positive_rate_acceptable(self):
        """小规模测试不应出现假阳性（100 元素，10000 位）。"""
        bf = BloomFilter(size=10000)
        added = {f"10.0.0.{i}" for i in range(100)}
        for ip in added:
            bf.add(ip)

        false_positives = 0
        for i in range(200, 300):
            if bf.contains(f"10.0.0.{i}"):
                false_positives += 1

        # 假阳性率应低于 5%
        assert false_positives < 5


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    """LRU 集合行为测试。"""

    def test_add_and_contains(self):
        """添加的元素应能被检测到。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_contains_moves_to_end(self):
        """访问已存在的元素应将其移到末尾。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.contains("a")  # 访问 a，将 a 移到末尾
        cache.add("d")  # 应淘汰 b（最久未访问）

        assert cache.contains("a") is True
        assert cache.contains("b") is False  # 被淘汰
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_eviction_removes_oldest(self):
        """超过 maxsize 时应淘汰最旧元素。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 a

        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("d") is True

    def test_remove(self):
        """移除元素后应返回 False。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        cache.remove("192.168.1.1")
        assert cache.contains("192.168.1.1") is False

    def test_remove_nonexistent(self):
        """移除不存在的元素不应抛出异常。"""
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")  # 不应抛出异常

    def test_clear(self):
        """清空后所有元素应返回 False。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False


# =============================================================================
# IpBanMiddleware 测试
# =============================================================================


@pytest.mark.asyncio
class TestIpBanMiddleware:
    """IpBanMiddleware 分发行为测试。"""

    async def _make_mock_request(
        self, path: str, client_ip: str = "10.0.0.1", container=None
    ):
        """创建测试用 Request（可选带 container 的 app）。"""
        scope = {
            "type": "http",
            "path": path,
            "url": {"path": path},
            "headers": [],
            "client": (client_ip, 12345),
        }
        if container:
            mock_state = MagicMock()
            mock_state.container = container
            mock_app = MagicMock()
            mock_app.state = mock_state
            scope["app"] = mock_app
        return Request(scope)

    async def _make_middleware(self):
        """创建 IpBanMiddleware 实例。"""
        return IpBanMiddleware(MagicMock())

    async def test_public_paths_are_skipped(self):
        """公开路径（/api/auth/login）应跳过检查。"""
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
        middleware = await self._make_middleware()
        request = await self._make_mock_request("/api/auth/login")

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        call_next.assert_awaited_once()

    async def test_docs_paths_are_skipped(self):
        """文档路径（/docs）应跳过检查。"""
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
        middleware = await self._make_middleware()
        request = await self._make_mock_request("/docs")

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        call_next.assert_awaited_once()

    async def test_no_client_ip_skips_check(self):
        """无客户端 IP 时应跳过检查。"""
        scope = {
            "type": "http",
            "path": "/api/admin",
            "url": {"path": "/api/admin"},
            "headers": [],
            "client": None,
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
        middleware = await self._make_middleware()

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    async def test_banned_ip_returns_403(self):
        """被封禁的 IP 应返回 403。"""
        mock_ban_service = AsyncMock()
        mock_ban_service.is_ip_banned = AsyncMock(return_value=True)
        mock_container = MagicMock()
        mock_container.is_available = MagicMock(return_value=True)
        mock_container.get = MagicMock(return_value=mock_ban_service)

        middleware = await self._make_middleware()
        # 先将 IP 添加到 Bloom 过滤器（模拟之前访问过）
        middleware._bloom.add("10.0.0.1")

        request = await self._make_mock_request(
            "/api/admin", "10.0.0.1", container=mock_container
        )
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 403
        body = response.body
        assert b"ip_banned" in body

    async def test_free_ip_passes_and_added_to_bloom(self):
        """未封禁的 IP 应通过检查并加入 Bloom 过滤器。"""
        mock_ban_service = AsyncMock()
        mock_ban_service.is_ip_banned = AsyncMock(return_value=False)
        mock_container = MagicMock()
        mock_container.is_available = MagicMock(return_value=True)
        mock_container.get = MagicMock(return_value=mock_ban_service)

        middleware = await self._make_middleware()
        request = await self._make_mock_request(
            "/api/admin", "10.0.0.1", container=mock_container
        )
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # IP 应被加入 Bloom 过滤器
        assert middleware._bloom.contains("10.0.0.1") is True
        assert middleware._whitelist_cache.contains("10.0.0.1") is True

    async def test_whitelist_cache_skips_db_query(self):
        """白名单缓存中的 IP 应跳过数据库查询。"""
        mock_ban_service = AsyncMock()
        mock_ban_service.is_ip_banned = AsyncMock(return_value=False)
        mock_container = MagicMock()
        mock_container.is_available = MagicMock(return_value=True)
        mock_container.get = MagicMock(return_value=mock_ban_service)

        middleware = await self._make_middleware()
        # 预先将 IP 加入白名单缓存
        middleware._whitelist_cache.add("10.0.0.1")

        request = await self._make_mock_request(
            "/api/admin", "10.0.0.1", container=mock_container
        )
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # is_ip_banned 不应被调用
        mock_ban_service.is_ip_banned.assert_not_called()

    async def test_container_not_available_skips_check(self):
        """ip_ban 服务不可用时跳过检查。"""
        mock_container = MagicMock()
        mock_container.is_available = MagicMock(return_value=False)

        middleware = await self._make_middleware()
        request = await self._make_mock_request(
            "/api/admin", "10.0.0.1", container=mock_container
        )
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    async def test_reload_cache_clears_and_reloads(self):
        """reload_cache 应清空并重新加载。"""
        mock_ban_service = AsyncMock()
        mock_ban_service.get_active_ip_ranges = AsyncMock(
            return_value=["192.168.1.0/24", "10.0.0.0/8"]
        )

        middleware = await self._make_middleware()
        middleware._bloom.add("old_entry")
        middleware._whitelist_cache.add("old_entry")

        await middleware.reload_cache(mock_ban_service)

        # 旧条目应被清除
        assert middleware._bloom.contains("old_entry") is False
        assert middleware._whitelist_cache.contains("old_entry") is False
        # 新 IP 段应被加载
        assert middleware._bloom.contains("192.168.1.0/24") is True
        assert middleware._bloom.contains("10.0.0.0/8") is True