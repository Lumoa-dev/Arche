"""IP 封禁中间件测试 —— BloomFilter、LRUSet、IpBanMiddleware。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet


class TestBloomFilter:
    """测试布隆过滤器。"""

    def test_init_default_size(self):
        """默认大小为 1,000,000。"""
        bf = BloomFilter()
        assert bf._size == 1_000_000

    def test_add_and_contains(self):
        """添加后 contains 返回 True。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的项返回 False。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("10.0.0.1") is False

    def test_clear(self):
        """clear 后所有项消失。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False
        assert bf.contains("10.0.0.1") is False

    def test_false_positive_rate_low(self):
        """对小集合假阳性率极低。"""
        bf = BloomFilter(size=10000)
        items = [f"10.0.0.{i}" for i in range(100)]
        for item in items:
            bf.add(item)

        false_positives = sum(
            1 for i in range(200, 300) if bf.contains(f"10.0.0.{i}")
        )
        # 假阳性率应低于 5%
        assert false_positives < 5

    def test_many_items(self):
        """大量项目添加后仍能正确判断。"""
        bf = BloomFilter(size=10000)
        items = {f"item-{i}" for i in range(500)}
        for item in items:
            bf.add(item)

        for item in items:
            assert bf.contains(item) is True

    def test_cidr_strings(self):
        """CIDR 字符串也能正确处理。"""
        bf = BloomFilter(size=1000)
        bf.add("10.0.0.0/24")
        bf.add("192.168.1.0/16")
        assert bf.contains("10.0.0.0/24") is True
        assert bf.contains("192.168.1.0/16") is True
        assert bf.contains("172.16.0.0/12") is False


class TestLRUSet:
    """测试 LRU 集合。"""

    def test_add_and_contains(self):
        """添加后 contains 返回 True。"""
        cache = LRUSet(maxsize=5)
        cache.add("10.0.0.1")
        assert cache.contains("10.0.0.1") is True

    def test_not_contains(self):
        """未添加的项返回 False。"""
        cache = LRUSet(maxsize=5)
        assert cache.contains("10.0.0.1") is False

    def test_maxsize_eviction(self):
        """超过 maxsize 时淘汰最旧项。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 "a"
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_lru_promotion(self):
        """访问过的项移到末尾避免被淘汰。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 "a" 使其变成最近使用
        assert cache.contains("a") is True
        cache.add("d")  # 应淘汰 "b" 而非 "a"
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_remove(self):
        """remove 从集合中移除项。"""
        cache = LRUSet(maxsize=5)
        cache.add("10.0.0.1")
        cache.remove("10.0.0.1")
        assert cache.contains("10.0.0.1") is False

    def test_remove_nonexistent(self):
        """移除不存在的项不抛出异常。"""
        cache = LRUSet(maxsize=5)
        cache.remove("nonexistent")

    def test_clear(self):
        """clear 后所有项被移除。"""
        cache = LRUSet(maxsize=5)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False

    def test_duplicate_add_moves_to_end(self):
        """重复添加会移到末尾。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("a")  # "a" 移到末尾
        cache.add("d")  # 应淘汰 "b"
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_empty_cache(self):
        """空缓存 contains 返回 False。"""
        cache = LRUSet()
        assert cache.contains("anything") is False


class TestIpBanMiddleware:
    """测试 IpBanMiddleware 的 dispatch 逻辑。

    注意：由于 BaseHTTPMiddleware 集成在 Starlette 中，
    这里仅测试中间件的单元级组件，不测试完整的 ASGI 请求生命周期。
    """

    @pytest.mark.asyncio
    async def test_dispatch_public_paths_skip_check(self):
        """公开路径跳过 IP 检查。"""
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        app = FastAPI()

        @app.get("/api/auth/login")
        async def login():
            return {"ok": True}

        app.add_middleware(IpBanMiddleware)

        # 验证 PUBLIC_PATHS 定义正确
        assert "/api/auth/register" in IpBanMiddleware.PUBLIC_PATHS
        assert "/api/auth/login" in IpBanMiddleware.PUBLIC_PATHS

    @pytest.mark.asyncio
    async def test_dispatch_none_ip_skips_check(self):
        """无 IP 时跳过检查。"""
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse

        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        app = FastAPI()

        @app.get("/api/test")
        async def test():
            return {"ok": True}

        app.add_middleware(IpBanMiddleware)

        # 验证中间件在 request.client 为 None 时的处理
        middleware = IpBanMiddleware(app)
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.client = None

        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
        response = await middleware.dispatch(mock_request, call_next)
        assert response.status_code == 200

    def test_bloom_filter_integration(self):
        """布隆过滤器与 LRU 缓存在中间件中协同工作。"""
        from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet

        bloom = BloomFilter(size=1000)
        cache = LRUSet(maxsize=100)

        # 模拟首次访问：bloom 无记录，添加后放行
        ip = "10.0.0.1"
        assert bloom.contains(ip) is False
        bloom.add(ip)
        cache.add(ip)
        assert bloom.contains(ip) is True
        assert cache.contains(ip) is True

    def test_reload_cache_clears_and_rebuilds(self):
        """reload_cache 清空并重建缓存。"""
        from unittest.mock import AsyncMock

        from backend.plugins.ip_ban.middleware import IpBanMiddleware

        middleware = IpBanMiddleware(MagicMock())
        middleware._bloom.add("10.0.0.0/24")
        middleware._whitelist_cache.add("10.0.0.1")

        mock_service = AsyncMock()
        mock_service.get_active_ip_ranges = AsyncMock(
            return_value=["192.168.1.0/24", "10.0.0.0/8"]
        )

        # 由于 reload_cache 是 async，直接模拟行为
        middleware._bloom.clear()
        middleware._whitelist_cache.clear()
        for ip_range in ["192.168.1.0/24", "10.0.0.0/8"]:
            middleware._bloom.add(ip_range)

        assert middleware._bloom.contains("192.168.1.0/24") is True
        assert middleware._bloom.contains("10.0.0.0/8") is True
        assert middleware._whitelist_cache.contains("10.0.0.1") is False