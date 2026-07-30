"""Token Bucket 限速器单元测试 —— 覆盖 TokenBucket 和 RateLimiterManager。"""

from __future__ import annotations

import asyncio
import uuid

import pytest


class TestTokenBucket:
    """Token Bucket 算法单元测试。"""

    @pytest.fixture
    def bucket(self):
        from backend.plugins.oss.rate_limiter import TokenBucket
        return TokenBucket(rate=10, capacity=10)

    def test_initial_capacity(self, bucket):
        assert bucket._tokens == 10

    def test_consume_immediate(self, bucket):
        """消费不超过当前 token 数量应立即返回。"""
        asyncio.run(bucket.consume(5))
        assert bucket._tokens == 5

    def test_consume_exact_capacity(self, bucket):
        asyncio.run(bucket.consume(10))
        assert bucket._tokens == 0

    def test_consume_zero(self, bucket):
        """消费 0 个 token 不应改变状态。"""
        asyncio.run(bucket.consume(0))
        assert bucket._tokens == 10

    async def test_consume_wait_refills(self):
        """消费超过当前容量时应等待补充。"""
        from backend.plugins.oss.rate_limiter import TokenBucket

        bucket = TokenBucket(rate=100, capacity=10)
        # 清空 bucket
        await bucket.consume(10)
        assert bucket._tokens == 0

        start = asyncio.get_running_loop().time()
        await bucket.consume(5)
        elapsed = asyncio.get_running_loop().time() - start
        # 5 个 token 需要 5/100 = 0.05s
        assert elapsed >= 0.04
        assert bucket._tokens >= 0

    def test_refill_does_not_exceed_capacity(self, bucket):
        bucket._tokens = 5
        bucket._last_refill -= 10  # 模拟 10 秒前
        bucket._refill()
        # 补充 10*10 = 100，但容量上限为 10
        assert bucket._tokens == 10

    def test_high_rate_bucket(self):
        """高吞吐场景验证。"""
        from backend.plugins.oss.rate_limiter import TokenBucket

        bucket = TokenBucket(rate=1000, capacity=1000)
        asyncio.run(bucket.consume(1000))
        assert bucket._tokens < 1


class TestRateLimiterManager:
    """RateLimiterManager 单元测试。"""

    @pytest.fixture
    def manager(self):
        from backend.plugins.oss.rate_limiter import RateLimiterManager
        return RateLimiterManager(global_rate=100)

    def test_consume_no_user(self, manager):
        """无 user_id 时使用默认 multiplier=1。"""
        asyncio.run(manager.consume(None, 50))
        assert manager._global_bucket._tokens == 150  # 200 - 50

    def test_consume_with_multiplier(self, manager):
        """multiplier > 1 时消耗更少 token。"""
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 2.0)
        asyncio.run(manager.consume(uid, 100))
        # 有效消耗 = 100/2 = 50
        assert manager._global_bucket._tokens == 150  # 200 - 50

    def test_consume_with_multiplier_less_than_one(self, manager):
        """multiplier < 1 时消耗更多 token（降速）。"""
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 0.5)
        asyncio.run(manager.consume(uid, 50))
        # 有效消耗 = 50/0.5 = 100
        assert manager._global_bucket._tokens == 100  # 200 - 100

    def test_set_and_get_user_multiplier(self, manager):
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 3.0)
        assert manager.get_user_multiplier(uid) == 3.0

    def test_remove_user_multiplier(self, manager):
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 3.0)
        manager.remove_user_multiplier(uid)
        assert manager.get_user_multiplier(uid) == 1.0  # 默认

    def test_remove_nonexistent(self, manager):
        uid = uuid.uuid4()
        manager.remove_user_multiplier(uid)  # 不应抛出异常

    def test_global_rate_property(self, manager):
        assert manager.global_rate == 100

    def test_set_global_rate(self, manager):
        manager.set_global_rate(200)
        assert manager.global_rate == 200
        assert manager._global_bucket._capacity == 400

    def test_consume_with_unknown_user(self, manager):
        """未设置 multiplier 的 user 应使用默认值 1.0。"""
        uid = uuid.uuid4()
        asyncio.run(manager.consume(uid, 50))
        assert manager._global_bucket._tokens == 150