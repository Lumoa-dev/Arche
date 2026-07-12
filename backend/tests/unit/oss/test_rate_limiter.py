"""TokenBucket 和 RateLimiterManager 行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现细节
- 使用 time.monotonic mocking 控制时间，保证测试确定性
- 所有测试独立且可重复
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import patch

import pytest

from backend.plugins.oss.rate_limiter import RateLimiterManager, TokenBucket


class TestTokenBucket:
    """TokenBucket 行为测试。"""

    def test_initial_tokens_equal_capacity(self):
        """TokenBucket 初始化时 tokens 应等于 capacity。"""
        bucket = TokenBucket(rate=5, capacity=20)
        assert bucket._tokens == 20

    @pytest.mark.asyncio
    async def test_consume_reduces_tokens(self):
        """consume() 应减少可用 token 数量。"""
        with patch("backend.plugins.oss.rate_limiter.time.monotonic", return_value=100.0):
            bucket = TokenBucket(rate=1, capacity=10)
            await bucket.consume(3)
            assert bucket._tokens == 7

    @pytest.mark.asyncio
    async def test_consume_more_than_available_waits(self):
        """token 不足时 consume() 应阻塞等待。"""
        bucket = TokenBucket(rate=0.001, capacity=1)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(bucket.consume(10), timeout=0.01)

    @pytest.mark.asyncio
    async def test_refill_over_time(self):
        """随时间推移，tokens 应增加。"""
        with patch("backend.plugins.oss.rate_limiter.time.monotonic", return_value=100.0):
            bucket = TokenBucket(rate=10, capacity=100)
            # 初始 100 tokens
            assert bucket._tokens == 100
            # 消费 50 个
            await bucket.consume(50)
            assert bucket._tokens == 50

        # 时间前进 1 秒
        with patch("backend.plugins.oss.rate_limiter.time.monotonic", return_value=101.0):
            bucket._refill()
            # 应补充 10 个 token，达到 60
            assert bucket._tokens == 60

    @pytest.mark.asyncio
    async def test_capacity_not_exceeded(self):
        """refill 后 tokens 不应超过 capacity。"""
        with patch("backend.plugins.oss.rate_limiter.time.monotonic", return_value=100.0):
            bucket = TokenBucket(rate=100, capacity=50)
            # 初始 50 tokens
            assert bucket._tokens == 50

        # 时间前进 1000 秒（远超需要的补充量）
        with patch("backend.plugins.oss.rate_limiter.time.monotonic", return_value=1100.0):
            bucket._refill()
            # 不应超过 capacity
            assert bucket._tokens == 50


class TestRateLimiterManager:
    """RateLimiterManager 行为测试。"""

    @pytest.mark.asyncio
    async def test_consume_global(self):
        """不传 user_id 时应使用全局 bucket。"""
        with patch("backend.plugins.oss.rate_limiter.time.monotonic", return_value=100.0):
            manager = RateLimiterManager(global_rate=1000)
            tokens_before = manager._global_bucket._tokens
            # 全局 bucket 容量 = rate * 2 = 2000
            assert tokens_before == 2000

            await manager.consume(user_id=None, bytes_count=100)

            # 应消耗 100 token
            assert manager._global_bucket._tokens == 1900

    @pytest.mark.asyncio
    async def test_consume_with_multiplier_gt_1(self):
        """multiplier > 1 时等效消耗更少 token（加速）。"""
        with patch("backend.plugins.oss.rate_limiter.time.monotonic", return_value=100.0):
            manager = RateLimiterManager(global_rate=1000)
            user_id = uuid.uuid4()
            manager.set_user_multiplier(user_id, 2.0)

            # 带 multiplier=2 消费 100 字节，等效 100 / 2 = 50 token
            await manager.consume(user_id=user_id, bytes_count=100)

            # 应消耗 50 token
            assert manager._global_bucket._tokens == 2000 - 50

    @pytest.mark.asyncio
    async def test_consume_with_multiplier_lt_1(self):
        """multiplier < 1 时等效消耗更多 token（降速）。"""
        with patch("backend.plugins.oss.rate_limiter.time.monotonic", return_value=100.0):
            manager = RateLimiterManager(global_rate=1000)
            user_id = uuid.uuid4()
            manager.set_user_multiplier(user_id, 0.5)

            # 带 multiplier=0.5 消费 100 字节，等效 100 / 0.5 = 200 token
            await manager.consume(user_id=user_id, bytes_count=100)

            # 应消耗 200 token
            assert manager._global_bucket._tokens == 2000 - 200

    def test_set_user_multiplier(self):
        """set_user_multiplier() 应正确存储 multiplier。"""
        manager = RateLimiterManager()
        user_id = uuid.uuid4()
        manager.set_user_multiplier(user_id, 3.0)
        assert manager._user_multipliers[user_id] == 3.0

    def test_remove_user_multiplier(self):
        """remove_user_multiplier() 应移除 multiplier。"""
        manager = RateLimiterManager()
        user_id = uuid.uuid4()
        manager.set_user_multiplier(user_id, 3.0)
        manager.remove_user_multiplier(user_id)
        assert user_id not in manager._user_multipliers

    def test_get_user_multiplier(self):
        """get_user_multiplier() 应返回正确的 multiplier。"""
        manager = RateLimiterManager()
        user_id = uuid.uuid4()

        # 未设置时应返回 1.0
        assert manager.get_user_multiplier(user_id) == 1.0

        # 设置后应返回设置的值
        manager.set_user_multiplier(user_id, 2.5)
        assert manager.get_user_multiplier(user_id) == 2.5

        # 移除后应回退到 1.0
        manager.remove_user_multiplier(user_id)
        assert manager.get_user_multiplier(user_id) == 1.0

    def test_set_global_rate(self):
        """set_global_rate() 应改变 rate 和 capacity。"""
        manager = RateLimiterManager(global_rate=10 * 1024 * 1024)
        manager.set_global_rate(5 * 1024 * 1024)
        assert manager._global_bucket._rate == 5 * 1024 * 1024
        assert manager._global_bucket._capacity == 10 * 1024 * 1024

    def test_global_rate_property(self):
        """global_rate 属性应返回当前 rate。"""
        manager = RateLimiterManager(global_rate=10 * 1024 * 1024)
        assert manager.global_rate == 10 * 1024 * 1024

        manager.set_global_rate(5 * 1024 * 1024)
        assert manager.global_rate == 5 * 1024 * 1024