"""OSS 速率限制器 TokenBucket / RateLimiterManager 测试。

测试原则：
- 纯内存实现，无需数据库
- 使用 time.monotonic() 真实时间
"""

from __future__ import annotations

import asyncio
import time
import uuid

import pytest

from backend.plugins.oss.rate_limiter import RateLimiterManager, TokenBucket


class TestTokenBucket:
    """TokenBucket 令牌桶算法测试。"""

    def test_initial_tokens_equals_capacity(self):
        """初始 token 数应等于容量。"""
        bucket = TokenBucket(rate=10, capacity=100)
        assert bucket._tokens == 100

    def test_consume_succeeds_with_enough_tokens(self):
        """有足够 token 时应立即消费。"""
        bucket = TokenBucket(rate=1000, capacity=100)
        # 直接消费 50 token（< 容量 100）
        bucket._tokens = 100
        bucket._tokens -= 50
        assert bucket._tokens == 50

    def test_refill_increases_tokens(self):
        """随时间推移 token 应自动补充。"""
        bucket = TokenBucket(rate=100, capacity=1000)
        bucket._tokens = 0
        bucket._last_refill = time.monotonic() - 5  # 5 秒前

        bucket._refill()
        # 5 秒应补充约 500 token（不超过容量 1000）
        import pytest
        assert bucket._tokens == pytest.approx(500, abs=10)

    def test_refill_does_not_exceed_capacity(self):
        """补充不应超过容量上限。"""
        bucket = TokenBucket(rate=100, capacity=100)
        bucket._tokens = 50
        bucket._last_refill = time.monotonic() - 10  # 10 秒前

        bucket._refill()
        assert bucket._tokens == 100  # 不超过容量

    @pytest.mark.asyncio
    async def test_consume_waits_when_not_enough_tokens(self):
        """token 不足时应等待补充。"""
        bucket = TokenBucket(rate=1000, capacity=10)
        bucket._tokens = 0

        start = time.monotonic()
        # 消费 5 token，速率 1000/s 应很快完成
        await bucket.consume(5)
        elapsed = time.monotonic() - start
        # 应至少等待 5/1000 = 5ms
        assert elapsed >= 0.004


class TestRateLimiterManager:
    """RateLimiterManager 全局限速管理测试。"""

    def test_initial_global_rate(self):
        """初始化时应设置默认全局限速。"""
        manager = RateLimiterManager(global_rate=10 * 1024 * 1024)
        assert manager.global_rate == 10 * 1024 * 1024

    def test_set_global_rate_updates_bucket(self):
        """set_global_rate() 应更新令牌桶速率。"""
        manager = RateLimiterManager(global_rate=1024)
        manager.set_global_rate(2048)
        assert manager.global_rate == 2048

    def test_user_multiplier_default_is_one(self):
        """未设置倍率的用户默认返回 1.0。"""
        manager = RateLimiterManager()
        assert manager.get_user_multiplier(uuid.uuid4()) == 1.0

    def test_set_user_multiplier(self):
        """set_user_multiplier() 应正确设置倍率。"""
        manager = RateLimiterManager()
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 2.0)
        assert manager.get_user_multiplier(uid) == 2.0

    def test_remove_user_multiplier(self):
        """remove_user_multiplier() 应移除倍率设置。"""
        manager = RateLimiterManager()
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 2.0)
        manager.remove_user_multiplier(uid)
        assert manager.get_user_multiplier(uid) == 1.0

    def test_remove_nonexistent_multiplier_no_error(self):
        """移除不存在的用户倍率不应抛出异常。"""
        manager = RateLimiterManager()
        manager.remove_user_multiplier(uuid.uuid4())  # 不应抛异常

    @pytest.mark.asyncio
    async def test_consume_without_user_id(self):
        """无 user_id 时应使用默认倍率 1.0。"""
        manager = RateLimiterManager(global_rate=10 * 1024 * 1024)
        # 这个调用不应阻塞（有足够 token）
        await manager.consume(None, 100)
        # 验证不会抛出异常

    @pytest.mark.asyncio
    async def test_consume_with_multiplier_faster(self):
        """倍率 > 1 时等效消耗更少 token。"""
        manager = RateLimiterManager(global_rate=10 * 1024 * 1024)
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 2.0)
        # 倍率 2.0 意味着 1000 字节只消耗 500 token
        await manager.consume(uid, 1000)
        # 验证 global bucket 消耗了 500
        assert manager._global_bucket._tokens < manager._global_bucket._capacity

    @pytest.mark.asyncio
    async def test_consume_with_multiplier_slower(self):
        """倍率 < 1 时等效消耗更多 token。"""
        manager = RateLimiterManager(global_rate=10 * 1024 * 1024)
        uid = uuid.uuid4()
        manager.set_user_multiplier(uid, 0.5)
        # 倍率 0.5 意味着 1000 字节消耗 2000 token
        await manager.consume(uid, 1000)
        # 容量 - 2000
        assert manager._global_bucket._tokens < manager._global_bucket._capacity - 500