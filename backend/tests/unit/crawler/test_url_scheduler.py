"""URL 调度器单元测试 —— 覆盖队列管理、域名并发控制及边界情况。"""

from __future__ import annotations

import pytest

from backend.plugins.crawler.url_scheduler import UrlScheduler


class TestUrlScheduler:
    """UrlScheduler 单元测试。"""

    @pytest.fixture
    def scheduler(self):
        return UrlScheduler(max_global=5, max_per_domain=2)

    def test_get_domain(self, scheduler):
        assert scheduler._get_domain("https://example.com/page") == "example.com"
        assert scheduler._get_domain("http://sub.example.com/path") == "sub.example.com"
        assert scheduler._get_domain("https://example.com:8080/page") == "example.com:8080"

    def test_get_domain_invalid_url(self, scheduler):
        """无效 URL 返回空字符串。"""
        assert scheduler._get_domain("not-a-url") == ""

    @pytest.mark.asyncio
    async def test_enqueue_and_dequeue(self, scheduler):
        await scheduler.enqueue("https://example.com/page1")
        await scheduler.enqueue("https://example.com/page2")
        assert scheduler.queue_size == 2

        url = await scheduler.dequeue()
        assert url == "https://example.com/page1"
        assert scheduler.queue_size == 1

    @pytest.mark.asyncio
    async def test_dequeue_empty(self, scheduler):
        url = await scheduler.dequeue()
        assert url is None

    @pytest.mark.asyncio
    async def test_dequeue_respects_domain_limit(self, scheduler):
        """dequeue 应跳过已达域名并发上限的 URL。"""
        # 模拟 2 个域名已占满并发
        scheduler._domain_active["example.com"] = 2
        scheduler._domain_active["other.com"] = 1  # 未超限

        await scheduler.enqueue("https://example.com/page3")
        await scheduler.enqueue("https://other.com/page2")

        # 应返回 other.com 的 URL
        url = await scheduler.dequeue()
        assert url == "https://other.com/page2"

    @pytest.mark.asyncio
    async def test_acquire_and_release(self, scheduler):
        await scheduler.acquire("https://example.com/page")
        assert scheduler.active_count == 1
        assert scheduler._domain_active["example.com"] == 1

        await scheduler.release("https://example.com/page")
        assert scheduler.active_count == 0
        assert scheduler._domain_active["example.com"] == 0

    @pytest.mark.asyncio
    async def test_domain_active_count(self, scheduler):
        await scheduler.acquire("https://example.com/a")
        await scheduler.acquire("https://example.com/b")
        assert scheduler._domain_active["example.com"] == 2

        # 第三个请求应被 domain semaphore 阻塞
        # 这里不测试具体的阻塞，只验证 active_count
        assert scheduler.domains_active == {"example.com": 2}

    @pytest.mark.asyncio
    async def test_can_fetch(self, scheduler):
        assert await scheduler.can_fetch("https://example.com/page") is True
        scheduler._domain_active["example.com"] = 2
        assert await scheduler.can_fetch("https://example.com/page") is False
        scheduler._domain_active["example.com"] = 1
        assert await scheduler.can_fetch("https://example.com/page") is True

    @pytest.mark.asyncio
    async def test_release_unknown_domain(self, scheduler):
        """释放未记录的域名不应抛出异常。"""
        await scheduler.release("https://unknown.com/page")
        assert scheduler.active_count == 0

    @pytest.mark.asyncio
    async def test_global_semaphore_limit(self, scheduler):
        """全局并发限制测试。"""
        for i in range(5):
            await scheduler.acquire(f"https://example{i}.com/page")
        assert scheduler.active_count == 5

        # 第 6 个应被 global semaphore 阻塞
        import asyncio
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                scheduler.acquire("https://extra.com/page"),
                timeout=0.1,
            )

    @pytest.mark.asyncio
    async def test_queue_size_property(self, scheduler):
        assert scheduler.queue_size == 0
        await scheduler.enqueue("https://example.com/page")
        assert scheduler.queue_size == 1

    @pytest.mark.asyncio
    async def test_active_count_property(self, scheduler):
        assert scheduler.active_count == 0
        await scheduler.acquire("https://example.com/page")
        assert scheduler.active_count == 1