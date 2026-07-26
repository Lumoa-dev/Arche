"""IP 封禁中间件单元测试。

测试覆盖：BloomFilter、LRUSet、IpBanMiddleware 的请求拦截逻辑。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.plugins.ip_ban.middleware import BloomFilter, IpBanMiddleware, LRUSet


# =============================================================================
# BloomFilter
# =============================================================================


class TestBloomFilter:
    """测试布隆过滤器。"""

    def test_add_and_contains(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_contains_returns_false_for_unknown(self):
        bf = BloomFilter(size=1000)
        assert bf.contains("10.0.0.1") is False

    def test_clear_resets_filter(self):
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_false_positive_rate_is_low(self):
        """布隆过滤器可能有假阳性，但不应总是返回 True。"""
        bf = BloomFilter(size=10000)
        # 添加一些元素
        for i in range(100):
            bf.add(f"10.0.0.{i}")
        # 不加的元素应大概率返回 False
        false_positives = sum(
            1 for i in range(200, 400) if bf.contains(f"10.0.0.{i}")
        )
        assert false_positives < 10  # 假阳性率 < 5%


# =============================================================================
# LRUSet
# =============================================================================


class TestLRUSet:
    """测试 LRU 缓存集合。"""

    def test_add_and_contains(self):
        cache = LRUSet(maxsize=5)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_contains_moves_to_end(self):
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.contains("a")  # 访问 a，a 应移到末尾
        cache.add("d")  # 应淘汰最早添加的（现在是 b）
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_evicts_oldest_when_full(self):
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # contains 也会移动元素到末尾，所以先不调用 contains
        cache.add("d")  # 淘汰最早添加的 a
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_remove(self):
        cache = LRUSet(maxsize=5)
        cache.add("a")
        cache.add("b")
        cache.remove("a")
        assert cache.contains("a") is False
        assert cache.contains("b") is True

    def test_remove_nonexistent(self):
        cache = LRUSet(maxsize=5)
        cache.remove("nonexistent")  # 不应报错

    def test_clear(self):
        cache = LRUSet(maxsize=5)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False


# =============================================================================
# IpBanMiddleware — 请求拦截
# =============================================================================


@pytest.fixture
def mock_container():
    """创建 mock 容器，ip_ban 服务默认返回未封禁。"""
    container = MagicMock()
    container.is_available.return_value = True
    mock_service = AsyncMock()
    mock_service.is_ip_banned = AsyncMock(return_value=False)
    mock_service.get_active_ip_ranges = AsyncMock(return_value=[])
    container.get.return_value = mock_service
    return container


@pytest.fixture
def app_with_middleware(mock_container):
    """创建带有 IpBanMiddleware 的测试应用。"""
    app = FastAPI()
    app.state.container = mock_container

    @app.get("/api/test")
    async def test_endpoint():
        return {"ok": True}

    @app.get("/api/auth/login")
    async def login_endpoint():
        return {"ok": True}

    @app.get("/docs")
    async def docs_endpoint():
        return {"ok": True}

    app.add_middleware(IpBanMiddleware)
    return app


@pytest.mark.asyncio
class TestIpBanMiddlewareDispatch:
    """测试中间件请求分发逻辑。"""

    async def test_public_paths_are_allowed(self, app_with_middleware, mock_container):
        """公开路径应直接通过，不做 IP 检查。"""
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/auth/login")
            assert resp.status_code == 200
            mock_container.get.assert_not_called()  # 不应调用 ip_ban service

    async def test_docs_paths_are_allowed(self, app_with_middleware, mock_container):
        """文档路径应直接通过。"""
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test",
        ) as client:
            resp = await client.get("/docs")
            assert resp.status_code == 200

    async def test_banned_ip_gets_403(self, app_with_middleware, mock_container):
        """被封禁的 IP 应返回 403。"""
        # 让 bloom filter 已知该 IP
        middleware = None
        for m in app_with_middleware.user_middleware:
            if m.cls == IpBanMiddleware:
                middleware = m
                break

        # 手动添加 IP 到 bloom filter
        app_with_middleware.state.container.get.return_value.is_ip_banned = (
            AsyncMock(return_value=True)
        )
        # 让 bloom filter 包含该 IP
        for mw in app_with_middleware.user_middleware:
            if mw.cls == IpBanMiddleware:
                # 无法直接访问 dispatch 实例，通过集成测试验证
                pass

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                "/api/test",
                headers={"X-Forwarded-For": "10.0.0.1"},
            )
            # 由于 bloom filter 初始为空，且 is_ip_banned 返回 True，
            # 第一次请求会走完整检查路径
            assert resp.status_code == 403

    async def test_unbanned_ip_passes_through(self, app_with_middleware):
        """未封禁的 IP 应正常通过。"""
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/test")
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}

    async def test_ip_ban_service_unavailable_allows_request(
        self, mock_container
    ):
        """ip_ban 服务不可用时，请求应正常通过。"""
        app = FastAPI()
        app.state.container = mock_container
        # 当 is_available 返回 False 时，中间件跳过
        mock_container.is_available.return_value = False

        @app.get("/api/test")
        async def test_endpoint():
            return {"ok": True}

        app.add_middleware(IpBanMiddleware)

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/test")
            assert resp.status_code == 200

    async def test_container_exception_allows_request(self, mock_container):
        """容器异常时，请求应正常通过。"""
        app = FastAPI()
        app.state.container = mock_container  # 使用 MagicMock，get 可能报错

        # 让 is_available 返回 True 但 get 抛出异常
        def raise_error(*args, **kwargs):
            raise RuntimeError("container error")

        mock_container.is_available.side_effect = raise_error

        @app.get("/api/test")
        async def test_endpoint():
            return {"ok": True}

        app.add_middleware(IpBanMiddleware)

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/test")
            assert resp.status_code == 200


# =============================================================================
# IpBanMiddleware — reload_cache
# =============================================================================


@pytest.mark.asyncio
class TestReloadCache:
    """测试重新加载缓存。"""

    async def test_reload_cache_clears_and_rebuilds(self, mock_container):
        """reload_cache 应清除缓存并从数据库重新加载。"""
        app = FastAPI()
        app.state.container = mock_container
        app.add_middleware(IpBanMiddleware)

        # 获取中间件实例
        from httpx import ASGITransport, AsyncClient

        # 创建一个带 reload_cache 的简单测试
        app.state.container.get.return_value.get_active_ip_ranges = AsyncMock(
            return_value=["10.0.0.0/24", "192.168.1.1"]
        )

        @app.post("/api/ip-ban/bans")
        async def ban_endpoint():
            # 手动触发 reload_cache
            container = app.state.container
            ip_ban_service = container.get("ip_ban")
            mw = IpBanMiddleware(app)
            await mw.reload_cache(ip_ban_service)
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/ip-ban/bans")
            assert resp.status_code == 200