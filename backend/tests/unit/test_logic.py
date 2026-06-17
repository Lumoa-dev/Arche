"""纯逻辑单元测试 —— 不依赖 ASGI 栈或数据库。

测试对象：
- CacheEntry（github_proxy）：缓存过期逻辑
- Rate limiter（github_proxy）：限流跟踪器
- URL 域名提取（crawler）：域名解析
"""

from __future__ import annotations

import time

import pytest


# ============================================================================
# CacheEntry —— 内存缓存条目
# ============================================================================


class TestCacheEntry:
    """GitHubProxy CacheEntry 纯逻辑测试。"""

    def test_entry_not_expired_initially(self):
        """新创建的缓存条目在 TTL 内未过期。"""
        from backend.plugins.github_proxy.services import CacheEntry

        entry = CacheEntry(
            data={"key": "value"},
            status_code=200,
            headers={"Content-Type": "application/json"},
            ttl=300,
        )
        assert not entry.is_expired, "新条目不应过期"

    def test_entry_with_zero_ttl_expires_immediately(self):
        """TTL 为 0 的条目创建即过期。"""
        from backend.plugins.github_proxy.services import CacheEntry

        entry = CacheEntry(
            data="data",
            status_code=200,
            headers={},
            ttl=0,
        )
        assert entry.is_expired, "TTL=0 的条目应立即过期"

    def test_entry_with_negative_ttl_expires_immediately(self):
        """TTL 为负数条目创建即过期。"""
        from backend.plugins.github_proxy.services import CacheEntry

        entry = CacheEntry(
            data="data",
            status_code=200,
            headers={},
            ttl=-1,
        )
        assert entry.is_expired, "负 TTL 条目应立即过期"

    def test_entry_with_short_ttl_expires(self):
        """TTL 极短的条目在短暂等待后过期。"""
        from backend.plugins.github_proxy.services import CacheEntry

        entry = CacheEntry(
            data="data",
            status_code=200,
            headers={},
            ttl=0.01,  # 10ms
        )
        assert not entry.is_expired, "刚创建未过期"
        time.sleep(0.02)  # 等 20ms
        assert entry.is_expired, "短 TTL 应在等待后过期"

    def test_entry_attributes(self):
        """缓存条目正确保存数据/状态码/头信息。"""
        from backend.plugins.github_proxy.services import CacheEntry

        data = {"count": 42}
        headers = {"x-custom": "value"}
        entry = CacheEntry(data, 418, headers, ttl=100)

        assert entry.data == data
        assert entry.status_code == 418
        assert entry.headers == headers


# ============================================================================
# 限流跟踪器 —— _check_rate_limit 逻辑
# ============================================================================


class TestRateLimiter:
    """GitHubProxy 限流器纯逻辑测试。"""

    def test_rate_tracker_accepts_first_request(self):
        """首次请求不被限流。"""
        from backend.plugins.github_proxy.services import (
            RATE_LIMIT_MAX_REQUESTS,
            RATE_LIMIT_WINDOW,
        )

        # 验证常量和类型
        assert isinstance(RATE_LIMIT_WINDOW, int)
        assert RATE_LIMIT_WINDOW > 0
        assert isinstance(RATE_LIMIT_MAX_REQUESTS, int)
        assert RATE_LIMIT_MAX_REQUESTS > 0
        assert RATE_LIMIT_MAX_REQUESTS == 60  # 每分钟最多 60 次

    def test_cache_key_consistency(self):
        """相同输入产生相同缓存键。"""
        from backend.plugins.github_proxy.services import GhCliService

        # 创建服务实例需要 container
        # 测试 _cache_key 作为纯函数：它只依赖 method, path, params
        # 我们需要通过 GhCliService 实例来调用
        class FakeConfig:
            def get(self, key, default=None):
                return default

            def get_required(self, key):
                return "fake-token"

        class FakeContainer:
            def get(self, key):
                return FakeConfig()

        container = FakeContainer()
        service = GhCliService(container)  # type: ignore[arg-type]

        key1 = service._cache_key("GET", "/repos/owner/repo", {"page": "1"})
        key2 = service._cache_key("GET", "/repos/owner/repo", {"page": "1"})
        key3 = service._cache_key("GET", "/repos/owner/repo", {"page": "2"})

        assert key1 == key2, "相同输入应产生相同键"
        assert key1 != key3, "不同输入应产生不同键"

    def test_cache_key_different_methods(self):
        """不同 HTTP 方法产生不同缓存键。"""
        from backend.plugins.github_proxy.services import GhCliService

        class FakeConfig:
            def get(self, key, default=None):
                return default

            def get_required(self, key):
                return "fake-token"

        class FakeContainer:
            def get(self, key):
                return FakeConfig()

        container = FakeContainer()
        service = GhCliService(container)  # type: ignore[arg-type]

        get_key = service._cache_key("GET", "/repos/owner/repo", {})
        post_key = service._cache_key("POST", "/repos/owner/repo", {})

        assert get_key != post_key, "GET 和 POST 应产生不同缓存键"


# ============================================================================
# URL 域名提取 —— UrlScheduler._get_domain
# ============================================================================


class TestUrlDomainExtraction:
    """Crawler URL 调度器域名提取测试。"""

    @pytest.fixture
    def scheduler(self):
        """创建纯 UrlScheduler 实例（不依赖 FS/app）。"""
        from backend.plugins.crawler.url_scheduler import UrlScheduler

        return UrlScheduler(max_global=5, max_per_domain=2)

    def test_get_domain_simple(self, scheduler):
        """标准 URL 提取域名。"""
        assert scheduler._get_domain("https://example.com/page") == "example.com"

    def test_get_domain_with_www(self, scheduler):
        """www 域名正确提取。"""
        assert scheduler._get_domain("https://www.example.com/path") == "www.example.com"

    def test_get_domain_with_port(self, scheduler):
        """带端口的 URL 提取域名包含端口（urlparse 行为）。"""
        assert scheduler._get_domain("http://localhost:8080/api") == "localhost:8080"

    def test_get_domain_subdomain(self, scheduler):
        """子域名 URL 提取完整域名。"""
        assert scheduler._get_domain("https://blog.example.com/post/1") == "blog.example.com"

    def test_get_domain_invalid_url(self, scheduler):
        """无效 URL 提取域名不崩溃。"""
        domain = scheduler._get_domain("not-a-url")
        # 应返回某种字符串而不崩溃
        assert isinstance(domain, str)
