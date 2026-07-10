"""OSS 速率限制器测试 —— TokenBucket / RateLimiterManager。"""

import asyncio
import uuid
from unittest.mock import patch

import pytest

from backend.plugins.oss.rate_limiter import TokenBucket, RateLimiterManager


class TestTokenBucket:
    """测试 Token Bucket 算法。"""

    def setup_method(self):
        self.bucket = TokenBucket(rate=10, capacity=100)

    def test_init(self):
        """初始化后 token 数等于容量。"""
        assert self.bucket._tokens == 100
        assert self.bucket._rate == 10
        assert self.bucket._capacity == 100

    def test_consume_immediate(self):
        """token 充足时立即消费。"""
        asyncio.run(self._test_consume_immediate())

    async def _test_consume_immediate(self):
        await self.bucket.consume(10)
        assert self.bucket._tokens == 90

    def test_consume_exact_capacity(self):
        """消费全部 token。"""
        asyncio.run(self._test_consume_exact())

    async def _test_consume_exact(self):
        await self.bucket.consume(100)
        assert self.bucket._tokens == 0

    def test_consume_zero(self):
        """消费 0 个 token。"""
        asyncio.run(self._test_consume_zero())

    async def _test_consume_zero(self):
        await self.bucket.consume(0)
        assert self.bucket._tokens == 100

    def test_refill_over_time(self):
        """随时间推移 token 补充。"""
        # 手动设置 _last_refill 和 _tokens 来模拟消耗后的状态
        self.bucket._tokens = 0
        self.bucket._last_refill = 0.0

        with patch("time.monotonic", return_value=2.0):
            self.bucket._refill()
            # 2 秒补充了 20 个 token（rate=10）
            assert self.bucket._tokens == 20

    def test_consume_waits_for_refill(self):
        """token 不足时等待补充。"""
        small_bucket = TokenBucket(rate=1, capacity=1)
        small_bucket._tokens = 0  # 直接消耗完
        small_bucket._last_refill = 0.0

        # 模拟时间推进并验证异步等待
        with patch("time.monotonic", return_value=1.0):
            with patch("asyncio.sleep", return_value=None):
                asyncio.run(small_bucket.consume(1))
                # 1 秒后补充了 1 个 token（rate=1）
                assert small_bucket._tokens >= 0


class TestRateLimiterManager:
    """测试全局限速管理。"""

    def setup_method(self):
        self.manager = RateLimiterManager(global_rate=1000)

    def test_init_global_rate(self):
        """全局限速初始值正确。"""
        assert self.manager.global_rate == 1000
        assert self.manager._global_bucket._capacity == 2000

    def test_set_global_rate(self):
        """设置全局限速。"""
        self.manager.set_global_rate(2000)
        assert self.manager.global_rate == 2000
        assert self.manager._global_bucket._capacity == 4000

    def test_consume_without_user(self):
        """无用户时使用默认倍率 1.0。"""
        asyncio.run(self._test_consume_no_user())

    async def _test_consume_no_user(self):
        with patch.object(self.manager._global_bucket, "consume", return_value=None) as mock:
            await self.manager.consume(None, 100)
            mock.assert_called_once_with(100.0)

    def test_consume_with_user_no_multiplier(self):
        """有用户但无倍率设置时使用默认倍率 1.0。"""
        asyncio.run(self._test_consume_user_default())

    async def _test_consume_user_default(self):
        uid = uuid.uuid4()
        with patch.object(self.manager._global_bucket, "consume", return_value=None) as mock:
            await self.manager.consume(uid, 100)
            mock.assert_called_once_with(100.0)

    def test_consume_with_user_multiplier(self):
        """用户倍率影响有效字节数。"""
        asyncio.run(self._test_consume_multiplier())

    async def _test_consume_multiplier(self):
        uid = uuid.uuid4()
        self.manager.set_user_multiplier(uid, 2.0)  # 2x 加速
        with patch.object(self.manager._global_bucket, "consume", return_value=None) as mock:
            await self.manager.consume(uid, 100)
            # 有效字节 = 100 / 2.0 = 50
            mock.assert_called_once_with(50.0)

    def test_set_user_multiplier(self):
        """设置用户倍率。"""
        uid = uuid.uuid4()
        self.manager.set_user_multiplier(uid, 0.5)
        assert self.manager.get_user_multiplier(uid) == 0.5

    def test_remove_user_multiplier(self):
        """移除用户倍率后恢复默认。"""
        uid = uuid.uuid4()
        self.manager.set_user_multiplier(uid, 2.0)
        self.manager.remove_user_multiplier(uid)
        assert self.manager.get_user_multiplier(uid) == 1.0

    def test_remove_nonexistent_user(self):
        """移除不存在的用户倍率不报错。"""
        uid = uuid.uuid4()
        self.manager.remove_user_multiplier(uid)  # 不应抛出异常

    def test_get_nonexistent_user_multiplier(self):
        """获取不存在的用户倍率返回 1.0。"""
        assert self.manager.get_user_multiplier(uuid.uuid4()) == 1.0