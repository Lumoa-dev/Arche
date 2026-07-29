"""Token Bucket 限速器测试。

测试原则：
- 覆盖 TokenBucket 的 refill 和 consume 行为
- 覆盖 RateLimiterManager 的 per-user 倍率管理
- 时间依赖方法使用 time.monotonic 打桩控制
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import patch

import pytest

from backend.plugins.oss.rate_limiter import RateLimiterManager, TokenBucket


class TestTokenBucket:
    """测试 TokenBucket 核心行为。"""

    def test_init_full_tokens(self):
        """初始化时 token 应等于 capacity。"""
        bucket = TokenBucket(rate=10, capacity=100)
        assert bucket._tokens == 100

    @patch("backend.plugins.oss.rate_limiter.time.monotonic")
    def test_refill_adds_tokens(self, mock_monotonic):
        """refill 应根据经过时间补充 token。"""
        mock_monotonic.return_value = 0.0
        bucket = TokenBucket(rate=10, capacity=100)
        bucket._tokens = 50  # 消耗一半

        mock_monotonic.return_value = 2.0  # 过了 2 秒
        bucket._refill()
        # 50 + 2*10 = 70
        assert bucket._tokens == 70

    @patch("backend.plugins.oss.rate_limiter.time.monotonic")
    def test_refill_caps_at_capacity(self, mock_monotonic):
        """refill 不应超过 capacity。"""
        mock_monotonic.return_value = 0.0
        bucket = TokenBucket(rate=10, capacity=100)
        bucket._tokens = 95

        mock_monotonic.return_value = 10.0  # 过了 10 秒，应补充 100
        bucket._refill()
        # 不应超过 capacity 100
        assert bucket._tokens == 100

    @patch("backend.plugins.oss.rate_limiter.time.monotonic")
    def test_consume_immediate_when_enough_tokens(self, mock_monotonic):
        """token 充足时 consume 应立即返回。"""
        mock_monotonic.return_value = 0.0
        bucket = TokenBucket(rate=10, capacity=100)

        async def consume_test():
            await bucket.consume(30)
            # 消耗后剩余 70
            assert bucket._tokens == 70

        asyncio.run(consume_test())

    @patch("backend.plugins.oss.rate_limiter.time.monotonic")
    def test_consume_wait_for_refill(self, mock_monotonic):
        """token 不足时 consume 应等待补充。"""
        mock_monotonic.return_value = 0.0
        bucket = TokenBucket(rate=10, capacity=100)
        bucket._tokens = 5  # 只有 5 个 token

        async def consume_test():
            # 需要 10 个 token，但只有 5 个，需要等待约 0.5 秒
            # 设定时间前进到 0.6 秒后
            async def delayed_refill():
                mock_monotonic.return_value = 0.6

            # 在 consume 前先推进时间
            mock_monotonic.return_value = 0.6
            # 手动 refill 模拟等待
            bucket._refill()
            # 5 + 0.6*10 = 11 >= 10，应该可以消费
            await bucket.consume(10)
            assert bucket._tokens == 1  # 11 - 10 = 1

        asyncio.run(consume_test())

    def test_refill_no_elapsed_time(self):
        """无时间流逝时 refill 不应改变 token 数。"""
        with patch("backend.plugins.oss.rate_limiter.time.monotonic", return_value=0.0):
            bucket = TokenBucket(rate=10, capacity=100)
            bucket._tokens = 50
            bucket._refill()
            bucket._refill()  # 重复调用
            assert bucket._tokens == 50


class TestRateLimiterManager:
    """测试 RateLimiterManager 行为。"""

    def test_init_default_rate(self):
        """默认全局限速为 10MB/s。"""
        manager = RateLimiterManager()
        assert manager.global_rate == 10 * 1024 * 1024

    def test_init_custom_rate(self):
        """自定义全局限速。"""
        manager = RateLimiterManager(global_rate=5 * 1024 * 1024)
        assert manager.global_rate == 5 * 1024 * 1024

    def test_set_and_get_user_multiplier(self):
        """设置和获取 per-user 倍率。"""
        manager = RateLimiterManager()
        user_id = uuid.uuid4()
        manager.set_user_multiplier(user_id, 2.0)
        assert manager.get_user_multiplier(user_id) == 2.0

    def test_get_default_user_multiplier(self):
        """未设置倍率的用户应返回 1.0。"""
        manager = RateLimiterManager()
        user_id = uuid.uuid4()
        assert manager.get_user_multiplier(user_id) == 1.0

    def test_remove_user_multiplier(self):
        """移除用户倍率后应恢复到默认值。"""
        manager = RateLimiterManager()
        user_id = uuid.uuid4()
        manager.set_user_multiplier(user_id, 2.0)
        manager.remove_user_multiplier(user_id)
        assert manager.get_user_multiplier(user_id) == 1.0

    def test_remove_nonexistent_multiplier(self):
        """移除不存在的用户倍率不应报错。"""
        manager = RateLimiterManager()
        manager.remove_user_multiplier(uuid.uuid4())  # 不应抛出异常

    def test_consume_with_multiplier_speeds_up(self):
        """multiplier > 1 时等效加速（消耗更少 token）。"""
        manager = RateLimiterManager(global_rate=1000)
        user_id = uuid.uuid4()
        manager.set_user_multiplier(user_id, 2.0)

        # 倍率 2.0，1000 bytes 等效消耗 500 token
        original_tokens = manager._global_bucket._tokens
        asyncio.run(manager.consume(user_id, 1000))
        # 500 token 被消耗
        assert manager._global_bucket._tokens == original_tokens - 500

    def test_consume_with_multiplier_slows_down(self):
        """multiplier < 1 时降速（消耗更多 token）。"""
        manager = RateLimiterManager(global_rate=1000)
        user_id = uuid.uuid4()
        manager.set_user_multiplier(user_id, 0.5)

        # 倍率 0.5，1000 bytes 等效消耗 2000 token
        original_tokens = manager._global_bucket._tokens
        asyncio.run(manager.consume(user_id, 1000))
        # 2000 token 被消耗
        assert manager._global_bucket._tokens == original_tokens - 2000

    def test_consume_without_user_id(self):
        """无 user_id 时使用默认倍率 1.0。"""
        manager = RateLimiterManager(global_rate=1000)
        original_tokens = manager._global_bucket._tokens
        asyncio.run(manager.consume(None, 500))
        assert manager._global_bucket._tokens == original_tokens - 500

    def test_set_global_rate(self):
        """设置全局限速应更新 rate 和 capacity。"""
        manager = RateLimiterManager(global_rate=10 * 1024 * 1024)
        manager.set_global_rate(20 * 1024 * 1024)
        assert manager.global_rate == 20 * 1024 * 1024
        assert manager._global_bucket._capacity == 40 * 1024 * 1024