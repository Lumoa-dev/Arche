"""IP 封禁中间件单元测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.responses import JSONResponse
from starlette.responses import Response

from backend.plugins.ip_ban.middleware import BloomFilter, IpBanMiddleware, LRUSet


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    """布隆过滤器单元测试。"""

    def test_add_and_contains(self):
        """添加后的项能被 contains 找到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_contains_never_added(self):
        """从未添加的项返回 False。"""
        bf = BloomFilter(size=1000)
        bf.add("10.0.0.1")
        # 未添加的 IP
        assert bf.contains("10.0.0.2") is False

    def test_clear_resets_filter(self):
        """clear 后之前添加的项不再被 contains 找到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_multiple_insertions_no_false_negative(self):
        """多次插入后所有已添加项都能被找到（无假阴性）。"""
        bf = BloomFilter(size=10_000)
        ips = [f"10.0.0.{i}" for i in range(100)]
        for ip in ips:
            bf.add(ip)
        for ip in ips:
            assert bf.contains(ip) is True, f"False negative for {ip}"

    def test_different_items_no_collision_false_positive(self):
        """不同项之间不会互相污染。"""
        bf = BloomFilter(size=1000)
        bf.add("item_a")
        assert bf.contains("item_b") is False


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    """LRU 集合单元测试。"""

    def test_add_and_contains(self):
        """添加后的项能被 contains 找到。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_contains_returns_false_for_missing(self):
        """未添加的项返回 False。"""
        cache = LRUSet(maxsize=10)
        cache.add("10.0.0.1")
        assert cache.contains("10.0.0.2") is False

    def test_lru_eviction(self):
        """超过最大容量时淘汰最久未使用的项。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 此时容量已满，添加 d 会淘汰 a
        cache.add("d")
        assert cache.contains("a") is False
        assert cache.contains("d") is True

    def test_remove_works(self):
        """remove 删除指定项。"""
        cache = LRUSet(maxsize=10)
        cache.add("192.168.1.1")
        cache.remove("192.168.1.1")
        assert cache.contains("192.168.1.1") is False

    def test_remove_nonexistent(self):
        """remove 不存在的项不报错。"""
        cache = LRUSet(maxsize=10)
        # 不应抛出异常
        cache.remove("nonexistent")

    def test_clear_works(self):
        """clear 清空所有项。"""
        cache = LRUSet(maxsize=10)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False

    def test_contains_promotes_item(self):
        """contains 会提升项的访问时间，使其在淘汰时被保留。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 a，使其成为最近使用
        cache.contains("a")
        # 添加 d，此时应淘汰最久未使用的 b（而不是 a）
        cache.add("d")
        assert cache.contains("a") is True, "a 被访问过，应被保留"
        assert cache.contains("b") is False, "b 最久未使用，应被淘汰"
        assert cache.contains("d") is True

    def test_add_existing_item_moves_to_end(self):
        """添加已存在的项会将其移到末尾（最近使用）。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 重新添加 a，使其成为最近使用
        cache.add("a")
        # 添加 d，此时应淘汰 b（而不是 a）
        cache.add("d")
        assert cache.contains("a") is True
        assert cache.contains("b") is False
        assert cache.contains("d") is True


# =============================================================================
# IpBanMiddleware dispatch 测试
# =============================================================================


class TestIpBanMiddlewareDispatch:
    """IP 封禁中间件 dispatch 方法单元测试。"""

    @pytest.fixture
    def mock_app(self):
        """创建模拟的 ASGI 应用。"""
        return MagicMock()

    @pytest.fixture
    def mock_call_next(self):
        """创建模拟的 call_next 函数，返回一个普通响应。"""

        async def _call_next(request):
            return Response(status_code=200, content="OK")

        return _call_next

    @pytest.fixture
    def middleware(self, mock_app):
        """创建 IpBanMiddleware 实例。"""
        return IpBanMiddleware(mock_app)

    def _make_request(self, path: str, client_host: str | None = None):
        """创建模拟的 Request 对象。"""
        request = MagicMock()
        request.url.path = path
        if client_host is not None:
            request.client.host = client_host
        else:
            request.client = None
        # 默认设置一个空的 app.state.container
        request.app.state.container = MagicMock()
        return request

    # ── 跳过路径 ──

    async def test_skip_login_path(self, middleware, mock_call_next):
        """登录路径 /api/auth/login 应跳过封禁检查直接放行。"""
        request = self._make_request("/api/auth/login", client_host="1.2.3.4")
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    async def test_skip_register_path(self, middleware, mock_call_next):
        """注册路径 /api/auth/register 应跳过封禁检查直接放行。"""
        request = self._make_request("/api/auth/register", client_host="1.2.3.4")
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    async def test_skip_docs_path(self, middleware, mock_call_next):
        """文档路径 /docs 应跳过封禁检查直接放行。"""
        request = self._make_request("/docs", client_host="1.2.3.4")
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    async def test_skip_openapi_path(self, middleware, mock_call_next):
        """OpenAPI 路径 /openapi.json 应跳过封禁检查直接放行。"""
        request = self._make_request("/openapi.json", client_host="1.2.3.4")
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    async def test_skip_redoc_path(self, middleware, mock_call_next):
        """Redoc 路径 /redoc 应跳过封禁检查直接放行。"""
        request = self._make_request("/redoc", client_host="1.2.3.4")
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    async def test_skip_docs_subpath(self, middleware, mock_call_next):
        """文档子路径（如 /docs/extra）也应跳过检查。"""
        request = self._make_request("/docs/extra/page", client_host="1.2.3.4")
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    # ── 缺少客户端 IP ──

    async def test_skip_when_no_client(self, middleware, mock_call_next):
        """没有客户端 IP 信息时应跳过封禁检查直接放行。"""
        request = self._make_request("/api/test", client_host=None)
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    async def test_skip_when_empty_client_ip(self, middleware, mock_call_next):
        """客户端 IP 为空字符串时应跳过封禁检查直接放行。"""
        request = self._make_request("/api/test", client_host="")
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    # ── 服务容器异常 ──

    async def test_skip_when_container_unavailable(self, middleware, mock_call_next):
        """容器不可用时跳过中间件。"""
        request = self._make_request("/api/test", client_host="1.2.3.4")
        # 让 container 访问抛出异常
        delattr(request.app.state, "container")
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    async def test_skip_when_ip_ban_service_unavailable(self, middleware, mock_call_next):
        """ip_ban 服务不可用时跳过中间件。"""
        request = self._make_request("/api/test", client_host="1.2.3.4")
        container = request.app.state.container
        container.is_available.return_value = False
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    async def test_skip_when_container_get_raises(self, middleware, mock_call_next):
        """container.get 抛出异常时跳过中间件。"""
        request = self._make_request("/api/test", client_host="1.2.3.4")
        container = request.app.state.container
        container.is_available.return_value = True
        container.get.side_effect = Exception("container error")
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    # ── 已封禁 IP ──

    async def test_banned_ip_returns_403(self, middleware, mock_call_next):
        """已封禁的 IP 返回 403 JSON 响应。"""
        request = self._make_request("/api/test", client_host="1.2.3.4")
        container = request.app.state.container
        container.is_available.return_value = True
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=True)
        container.get.return_value = mock_service

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 403
        assert response.media_type == "application/json"

    async def test_banned_ip_response_content(self, middleware, mock_call_next):
        """已封禁 IP 的 403 响应包含正确字段。"""
        request = self._make_request("/api/test", client_host="1.2.3.4")
        container = request.app.state.container
        container.is_available.return_value = True
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=True)
        container.get.return_value = mock_service

        response = await middleware.dispatch(request, mock_call_next)
        body = response.body.decode()
        assert '"code":"ip_banned"' in body
        assert '"message":"您的 IP 已被封禁"' in body

    # ── 未封禁 IP ──

    async def test_non_banned_ip_passes_through(self, middleware, mock_call_next):
        """未封禁的 IP 正常放行。"""
        request = self._make_request("/api/test", client_host="1.2.3.4")
        container = request.app.state.container
        container.is_available.return_value = True
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=False)
        container.get.return_value = mock_service

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    async def test_non_banned_ip_added_to_bloom_and_cache(self, middleware, mock_call_next):
        """未封禁的 IP 被加入布隆过滤器和白名单缓存。"""
        request = self._make_request("/api/test", client_host="1.2.3.4")
        container = request.app.state.container
        container.is_available.return_value = True
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=False)
        container.get.return_value = mock_service

        await middleware.dispatch(request, mock_call_next)

        # IP 应被加入布隆过滤器和白名单缓存
        assert middleware._bloom.contains("1.2.3.4") is True
        assert middleware._whitelist_cache.contains("1.2.3.4") is True

    async def test_banned_ip_not_cached(self, middleware, mock_call_next):
        """已封禁的 IP 不应该被加入白名单缓存。"""
        request = self._make_request("/api/test", client_host="1.2.3.4")
        container = request.app.state.container
        container.is_available.return_value = True
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=True)
        container.get.return_value = mock_service

        await middleware.dispatch(request, mock_call_next)

        # IP 不应被加入白名单缓存
        assert middleware._whitelist_cache.contains("1.2.3.4") is False

    async def test_whitelist_cache_skips_db_check(self, middleware, mock_call_next):
        """白名单缓存中的 IP 跳过数据库查询。"""
        request = self._make_request("/api/test", client_host="1.2.3.4")
        container = request.app.state.container
        container.is_available.return_value = True
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=False)
        container.get.return_value = mock_service

        # 第一次请求：走数据库查询
        await middleware.dispatch(request, mock_call_next)
        assert mock_service.is_ip_banned.call_count == 1

        # 第二次请求：被白名单缓存命中，不再查数据库
        await middleware.dispatch(request, mock_call_next)
        assert mock_service.is_ip_banned.call_count == 1, "缓存命中后不应再次查询数据库"

    async def test_bloom_filter_skips_db_for_banned_ip(self, middleware, mock_call_next):
        """布隆过滤器命中后走数据库验证，已封禁则返回 403。"""
        # 先手动将 IP 加入 bloom 过滤器（模拟 reload_cache 后的状态）
        middleware._bloom.add("1.2.3.4")

        request = self._make_request("/api/test", client_host="1.2.3.4")
        container = request.app.state.container
        container.is_available.return_value = True
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=True)
        container.get.return_value = mock_service

        # 请求：bloom 命中，数据库返回已封禁 → 403
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 403

    async def test_multiple_ips_independent(self, middleware, mock_call_next):
        """多个不同 IP 互不影响。"""
        container = MagicMock()
        container.is_available.return_value = True
        mock_service = AsyncMock()
        mock_service.is_ip_banned = AsyncMock(return_value=False)
        container.get.return_value = mock_service

        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        for ip in ips:
            request = self._make_request("/api/test", client_host=ip)
            request.app.state.container = container
            response = await middleware.dispatch(request, mock_call_next)
            assert response.status_code == 200

        # 所有 IP 都应被缓存
        for ip in ips:
            assert middleware._whitelist_cache.contains(ip) is True

    # ── reload_cache ──

    async def test_reload_cache_clears_and_reloads(self, middleware):
        """reload_cache 清空缓存并从服务重新加载。"""
        # 先添加一些数据
        middleware._bloom.add("old_ip")
        middleware._whitelist_cache.add("old_ip")

        mock_service = AsyncMock()
        mock_service.get_active_ip_ranges = AsyncMock(
            return_value=["10.0.0.1", "10.0.0.2"]
        )

        await middleware.reload_cache(mock_service)

        # 旧数据应被清空
        assert middleware._bloom.contains("old_ip") is False
        assert middleware._whitelist_cache.contains("old_ip") is False

        # 新数据应被加载到 bloom 过滤器
        assert middleware._bloom.contains("10.0.0.1") is True
        assert middleware._bloom.contains("10.0.0.2") is True

        # 白名单缓存应被清空（但不加载封禁 IP）
        assert middleware._whitelist_cache.contains("10.0.0.1") is False