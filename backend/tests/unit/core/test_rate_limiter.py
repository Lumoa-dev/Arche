"""RateLimiter 滑动窗口速率限制器测试。

测试原则：
- 纯内存数据结构测试，无外部依赖
- 验证滑动窗口的正确性
- 覆盖边界条件和竞态边缘情况
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """滑动窗口速率限制器行为测试。"""

    def test_is_limited_under_threshold(self):
        """阈值内的请求不应被限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        key = "test-user-127.0.0.1"

        for _ in range(4):
            limiter.record_attempt(key)

        assert limiter.is_limited(key) is False

    def test_is_limited_at_threshold(self):
        """达到阈值应被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        key = "test-user-127.0.0.1"

        for _ in range(3):
            limiter.record_attempt(key)

        assert limiter.is_limited(key) is True

    def test_is_limited_exceeds_threshold(self):
        """超过阈值后应继续被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        key = "test-user-127.0.0.1"

        for _ in range(5):
            limiter.record_attempt(key)

        assert limiter.is_limited(key) is True

    def test_record_attempt_returns_count(self):
        """record_attempt 应返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        key = "test-user-127.0.0.1"

        count1 = limiter.record_attempt(key)
        count2 = limiter.record_attempt(key)
        count3 = limiter.record_attempt(key)

        assert count1 == 1
        assert count2 == 2
        assert count3 == 3

    def test_reset_clears_counter(self):
        """reset 后该 key 不应再被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        key = "test-user-127.0.0.1"

        for _ in range(5):
            limiter.record_attempt(key)
        assert limiter.is_limited(key) is True

        limiter.reset(key)
        assert limiter.is_limited(key) is False
        assert limiter.record_attempt(key) == 1

    def test_reset_nonexistent_key(self):
        """重置不存在的 key 不应抛出异常。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.reset("nonexistent")  # 不应抛异常

    def test_old_records_expire(self):
        """窗口外的旧记录应被自动清理。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=1)
        key = "test-user-127.0.0.1"

        limiter.record_attempt(key)
        limiter.record_attempt(key)

        # 等待窗口过期
        time.sleep(1.1)

        # 新请求应复用同一窗口（旧记录已过期）
        count = limiter.record_attempt(key)
        assert count == 1  # 旧记录已被清理
        assert limiter.is_limited(key) is False

    def test_multiple_keys_independent(self):
        """不同 key 的限流状态应相互独立。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)

        limiter.record_attempt("user-a")
        limiter.record_attempt("user-a")
        assert limiter.is_limited("user-a") is True
        assert limiter.is_limited("user-b") is False

        limiter.record_attempt("user-b")
        assert limiter.is_limited("user-b") is False
        limiter.record_attempt("user-b")
        assert limiter.is_limited("user-b") is True

    def test_is_limited_does_not_mutate_state(self):
        """is_limited 不应改变计数器状态。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        key = "test-user-127.0.0.1"

        limiter.record_attempt(key)
        limiter.is_limited(key)  # 不应影响状态
        limiter.is_limited(key)

        assert limiter.record_attempt(key) == 2

    def test_different_window_sizes(self):
        """不同窗口大小的限流器应独立工作。"""
        short = RateLimiter(max_attempts=2, window_seconds=1)
        long = RateLimiter(max_attempts=10, window_seconds=60)

        for _ in range(5):
            short.record_attempt("key")
            long.record_attempt("key")

        assert short.is_limited("key") is True
        assert long.is_limited("key") is False

    def test_empty_window_zero_attempts(self):
        """从未尝试过的 key 不应被限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.is_limited("never-seen") is False

    def test_high_frequency_burst(self):
        """突发高频请求应被准确计数并限流。"""
        limiter = RateLimiter(max_attempts=100, window_seconds=60)
        key = "burst-key"

        for _ in range(100):
            limiter.record_attempt(key)

        assert limiter.is_limited(key) is True
        assert limiter.record_attempt(key) == 101

    def test_partial_window_expiry(self):
        """部分记录过期后限流状态应更新。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        key = "partial-expiry"

        limiter.record_attempt(key)
        limiter.record_attempt(key)
        limiter.record_attempt(key)
        assert limiter.is_limited(key) is True

        # 手动让部分记录过期（通过 mock time 或直接操作内部数据结构）
        # 这里我们直接验证内部清理逻辑
        now = time.time()
        limiter._attempts[key] = [
            now - 61,  # 已过期
            now - 30,  # 仍在窗口内
        ]
        assert limiter.is_limited(key) is False
        assert limiter.record_attempt(key) == 2  # 只有 1 条有效 + 当前请求

    def test_threshold_zero_or_one(self):
        """阈值为 1 时，第一次请求后就限流。"""
        limiter = RateLimiter(max_attempts=1, window_seconds=60)
        key = "strict-key"

        assert limiter.is_limited(key) is False
        limiter.record_attempt(key)
        assert limiter.is_limited(key) is True