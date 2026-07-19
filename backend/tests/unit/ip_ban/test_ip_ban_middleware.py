"""IP 封禁中间件 —— BloomFilter、LRUSet、IpBanMiddleware 测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from backend.plugins.ip_ban.middleware import BloomFilter, IpBanMiddleware, LRUSet


class TestBloomFilter:
    """测试简易布隆过滤器。"""

    def test_add_and_contains(self):
        """添加后应能检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的不应检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("10.0.0.1") is False

    def test_multiple_items(self):
        """多个项目添加后应都能检测到。"""
        bf = BloomFilter(size=10000)
        items = [f"192.168.1.{i}" for i in range(100)]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item) is True

    def test_clear(self):
        """清空后所有项目应不再检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_empty_filter(self):
        """空过滤器应返回 False。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("any") is False

    def test_cidr_format(self):
        """CIDR 格式字符串也应正确处理。"""
        bf = BloomFilter(size=10000)
        bf.add("192.168.0.0/16")
        assert bf.contains("192.168.0.0/16") is True
        assert bf.contains("10.0.0.0/8") is False

    def test_hashes_consistency(self):
        """同一字符串的哈希值应一致。"""
        bf = BloomFilter(size=10000)
        h1 = bf._hashes("test")
        h2 = bf._hashes("test")
        assert h1 == h2

    def test_different_items_different_hashes(self):
        """不同字符串的哈希值应不同。"""
        bf = BloomFilter(size=10000)
        h1 = bf._hashes("item-a")
        h2 = bf._hashes("item-b")
        assert h1 != h2


class TestLRUSet:
    """测试 LRU 集合。"""

    def test_add_and_contains(self):
        """添加后应能检测到。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的不应检测到。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("10.0.0.1") is False

    def test_eviction(self):
        """超过容量应淘汰最旧的项目。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 "a"
        assert cache.contains("a") is False
        assert cache.contains("d") is True
        assert cache.contains("b") is True
        assert cache.contains("c") is True

    def test_reorder_on_access(self):
        """访问已存在的项目应将其移到末尾。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 "a"，使其变为最近使用
        cache.contains("a")
        # 添加 "d" 应淘汰 "b"（最旧）
        cache.add("d")
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("d") is True

    def test_remove(self):
        """移除项目后不应再检测到。"""
        cache = LRUSet(maxsize=10)
        cache.add("test")
        cache.remove("test")
        assert cache.contains("test") is False

    def test_remove_nonexistent(self):
        """移除不存在的项目不应报错。"""
        cache = LRUSet(maxsize=10)
        cache.remove("nonexistent")

    def test_clear(self):
        """清空后所有项目不应再检测到。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False

    def test_maxsize_one(self):
        """容量为 1 时，新项目应淘汰旧项目。"""
        cache = LRUSet(maxsize=1)
        cache.add("a")
        cache.add("b")
        assert cache.contains("a") is False
        assert cache.contains("b") is True


class TestIpBanMiddleware:
    """测试 IpBanMiddleware 中间件。"""

    @pytest.mark.asyncio
    async def test_public_paths_passthrough(self):
        """公开路由应直接放行。"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = IpBanMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/auth/login"
        request.method = "POST"

        async def call_next(req):
            return JSONResponse({"status": "ok"}, status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_docs_paths_passthrough(self):
        """文档路由应直接放行。"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = IpBanMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/docs"

        async def call_next(req):
            return JSONResponse({"status": "ok"}, status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_no_client_ip(self):
        """无客户端 IP 时应放行。"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = IpBanMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.client = None

        async def call_next(req):
            return JSONResponse({"status": "ok"}, status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ip_not_banned_gets_added_to_bloom(self):
        """未封禁的 IP 应被添加到布隆过滤器和白名单缓存。"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = IpBanMiddleware(app)
        middleware._whitelist_cache = LRUSet(maxsize=100)

        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.client.host = "192.168.1.1"
        request.app.state.container = MagicMock()
        request.app.state.container.is_available.return_value = True

        # 模拟 ip_ban 服务
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=False)
        mock_service.get_active_ip_ranges = AsyncMock(return_value=[])
        request.app.state.container.get.return_value = mock_service

        async def call_next(req):
            return JSONResponse({"status": "ok"}, status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # IP 应被添加到布隆过滤器和白名单缓存
        assert middleware._bloom.contains("192.168.1.1") is True
        assert middleware._whitelist_cache.contains("192.168.1.1") is True

    @pytest.mark.asyncio
    async def test_banned_ip_returns_403(self):
        """被封禁的 IP 应返回 403。"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = IpBanMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.client.host = "192.168.1.1"
        request.app.state.container = MagicMock()
        request.app.state.container.is_available.return_value = True

        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=True)
        request.app.state.container.get.return_value = mock_service

        async def call_next(req):
            return JSONResponse({"status": "ok"}, status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 403
        body = response.body.decode()
        assert "ip_banned" in body

    @pytest.mark.asyncio
    async def test_whitelist_cache_hit(self):
        """白名单缓存命中时应直接放行，不查询数据库。"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = IpBanMiddleware(app)
        # 预先将 IP 加入白名单缓存
        middleware._whitelist_cache = LRUSet(maxsize=100)
        middleware._whitelist_cache.add("192.168.1.1")

        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.client.host = "192.168.1.1"
        request.app.state.container = MagicMock()

        mock_service = MagicMock()
        request.app.state.container.get.return_value = mock_service

        async def call_next(req):
            return JSONResponse({"status": "ok"}, status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        # 不应查询数据库
        mock_service.is_ip_banned.assert_not_called()

    @pytest.mark.asyncio
    async def test_container_not_available(self):
        """容器不可用时放行。"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = IpBanMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.client.host = "192.168.1.1"
        request.app.state.container = MagicMock()
        request.app.state.container.is_available.return_value = False

        async def call_next(req):
            return JSONResponse({"status": "ok"}, status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_container_exception(self):
        """容器访问异常时放行。"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = IpBanMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.client.host = "192.168.1.1"
        # 模拟 container 不可用抛出异常
        del request.app.state.container

        async def call_next(req):
            return JSONResponse({"status": "ok"}, status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_reload_cache(self):
        """重新加载缓存应清空并重新填充。"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = IpBanMiddleware(app)
        middleware._bloom.add("old")

        mock_service = AsyncMock()
        mock_service.get_active_ip_ranges = AsyncMock(return_value=["10.0.0.0/8", "192.168.1.1"])

        await middleware.reload_cache(mock_service)
        # 布隆过滤器应被清空并重新填充
        assert middleware._bloom.contains("old") is False
        assert middleware._bloom.contains("10.0.0.0/8") is True
        assert middleware._bloom.contains("192.168.1.1") is True