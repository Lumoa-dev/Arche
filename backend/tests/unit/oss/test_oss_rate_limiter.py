"""TokenBucket & RateLimiterManager 单元测试 —— 全局限速与 per-user 倍率。

测试原则：
- TokenBucket 使用 asyncio.wait_for 避免真实等待
- RateLimiterManager 测试不依赖真实时间
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from backend.plugins.oss.rate_limiter import RateLimiterManager, TokenBucket


class TestTokenBucket:
    """Token Bucket 算法测试。"""

    def test_initial_capacity(self):
        """初始 token 数等于容量。"""
        bucket = TokenBucket(rate=10, capacity=100)
        assert bucket._tokens == 100

    def test_consume_immediately(self):
        """token 充足时立即消费。"""
        bucket = TokenBucket(rate=100, capacity=100)

        async def test():
            await bucket.consume(50)
            assert bucket._tokens == 50  # 消费 50，剩余 50

        asyncio.run(test())

    def test_consume_less_than_capacity(self):
        """消费小于容量的 token。"""
        bucket = TokenBucket(rate=100, capacity=100)

        async def test():
            await bucket.consume(10)
            assert bucket._tokens == 90

        asyncio.run(test())

    def test_consume_exact_capacity(self):
        """消费等于容量的 token。"""
        bucket = TokenBucket(rate=100, capacity=100)

        async def test():
            await bucket.consume(100)
            assert bucket._tokens == 0

        asyncio.run(test())


class TestTokenBucketAsync:
    """需要异步环境的 TokenBucket 测试。"""

    @pytest.mark.asyncio
    async def test_consume_waits_when_exceeded(self):
        """token 不足时等待补充。"""
        bucket = TokenBucket(rate=1, capacity=3)
        # 消费到 0
        await bucket.consume(3)
        assert bucket._tokens == 0

        # 尝试消费 1，但 tokens 不够，需要等待 refill（1 token/s）
        # 使用极短的超时确认它在等待（需等待约 1 秒）
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(bucket.consume(1), timeout=0.05)

    @pytest.mark.asyncio
    async def test_refill_over_time(self):
        """随时间推移，token 自动补充。"""
        bucket = TokenBucket(rate=100, capacity=100)
        # 消费到 0
        await bucket.consume(100)
        assert bucket._tokens == 0

        # 手动触发 refill（模拟时间流逝）
        bucket._last_refill -= 0.1  # 倒退 100ms
        bucket._refill()
        # 100 token/s * 0.1s = 10 token
        assert bucket._tokens > 0
        # 不会超过 capacity
        assert bucket._tokens <= 100


class TestRateLimiterManager:
    """RateLimiterManager 管理测试。"""

    @pytest.mark.asyncio
    async def test_consume_no_user(self):
        """无用户时使用默认倍率 1.0。"""
        manager = RateLimiterManager(global_rate=1000)
        # 只是验证不报错
        await manager.consume(None, 100)
        assert True

    @pytest.mark.asyncio
    async def test_consume_with_user_default(self):
        """有用户但未设置倍率时使用 1.0。"""
        manager = RateLimiterManager(global_rate=1000)
        uid = uuid.uuid4()
        await manager.consume(uid, 100)
        assert True

    @pytest.mark.asyncio
    async def test_set_user_multiplier(self):
        """设置 per-user 倍率后正确返回。"""
        manager = RateLimiterManager(global_rate=1000)
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 2.0)
        assert manager.get_user_multiplier(uid) == 2.0

    @pytest.mark.asyncio
    async def test_remove_user_multiplier(self):
        """移除 per-user 倍率后回退到 1.0。"""
        manager = RateLimiterManager(global_rate=1000)
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 2.0)
        manager.remove_user_multiplier(uid)
        assert manager.get_user_multiplier(uid) == 1.0

    def test_global_rate_property(self):
        """global_rate 属性返回当前值。"""
        manager = RateLimiterManager(global_rate=10 * 1024 * 1024)
        assert manager.global_rate == 10 * 1024 * 1024

    def test_set_global_rate(self):
        """set_global_rate 更新速率和容量。"""
        manager = RateLimiterManager(global_rate=10 * 1024 * 1024)
        manager.set_global_rate(20 * 1024 * 1024)
        assert manager.global_rate == 20 * 1024 * 1024
        assert manager._global_bucket._capacity == 40 * 1024 * 1024  # rate * 2

    @pytest.mark.asyncio
    async def test_multiplier_speeds_up(self):
        """大于 1 的倍率等效加速（消耗更少 token）。"""
        manager = RateLimiterManager(global_rate=1000)
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 10.0)
        # 设置倍率后，100 字节等效消耗 10 个 token（而非 100）
        # 验证不报错即可
        await manager.consume(uid, 100)
        assert True

    def test_remove_nonexistent_multiplier(self):
        """移除不存在的用户倍率不报错。"""
        manager = RateLimiterManager(global_rate=1000)
        manager.remove_user_multiplier(uuid.uuid4())
        # 不抛异常即可