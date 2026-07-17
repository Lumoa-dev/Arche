"""RateLimiter 滑动窗口速率限制器测试。

覆盖：
- 基本限流逻辑（未超限 / 超限 / 重置）
- 滑动窗口过期行为
- 多 key 隔离
- 边界条件（大窗口 / 零窗口 / 高并发 key）
"""

from __future__ import annotations

import time

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """RateLimiter 核心行为测试。"""

    def test_init_with_defaults(self):
        """默认构造参数正确。"""
        limiter = RateLimiter()
        assert limiter.max_attempts == 5
        assert limiter.window_seconds == 60

    def test_init_with_custom_params(self):
        """自定义参数构造正确。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=30)
        assert limiter.max_attempts == 10
        assert limiter.window_seconds == 30

    def test_not_limited_below_threshold(self):
        """未超过阈值时 is_limited 返回 False。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        assert not limiter.is_limited("key-a")
        limiter.record_attempt("key-a")
        assert not limiter.is_limited("key-a")
        limiter.record_attempt("key-a")
        assert not limiter.is_limited("key-a")

    def test_limited_when_at_threshold(self):
        """达到阈值时 is_limited 返回 True。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        assert limiter.is_limited("key-a")

    def test_limited_exceeds_threshold(self):
        """超过阈值后仍返回 True。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")  # 第三次
        assert limiter.is_limited("key-a")

    def test_record_attempt_returns_count(self):
        """record_attempt 返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.record_attempt("key-a") == 1
        assert limiter.record_attempt("key-a") == 2
        assert limiter.record_attempt("key-a") == 3

    def test_reset_clears_key(self):
        """reset 后该 key 的计数清零，不再限流。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        assert limiter.is_limited("key-a")
        limiter.reset("key-a")
        assert not limiter.is_limited("key-a")

    def test_reset_nonexistent_key_does_not_raise(self):
        """reset 不存在的 key 不抛异常。"""
        limiter = RateLimiter()
        limiter.reset("nonexistent-key")  # 不应抛异常

    def test_multiple_keys_isolated(self):
        """不同 key 的计数器互不干扰。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        assert limiter.is_limited("key-a")
        assert not limiter.is_limited("key-b")
        limiter.record_attempt("key-b")
        assert not limiter.is_limited("key-b")

    def test_window_slides_after_time(self):
        """窗口滑动后旧记录失效，不再限流。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0.1)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        assert limiter.is_limited("key-a")
        time.sleep(0.15)
        assert not limiter.is_limited("key-a")

    def test_is_limited_also_cleans_expired(self):
        """is_limited 调用时也会清理过期记录。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0.1)
        limiter.record_attempt("key-a")
        time.sleep(0.15)
        # 过期记录应被清理，此时 is_limited 返回 False
        assert not limiter.is_limited("key-a")

    def test_large_window_does_not_overflow(self):
        """大窗口内大量尝试不导致性能问题。"""
        limiter = RateLimiter(max_attempts=10000, window_seconds=3600)
        for i in range(5000):
            limiter.record_attempt("key-a")
        assert not limiter.is_limited("key-a")

    def test_zero_window_seconds(self):
        """window_seconds=0 时所有记录立即过期。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        # 窗口为 0，记录的 timestamp > now - 0 永远为 False，所以永远不计入
        assert not limiter.is_limited("key-a")

    def test_empty_key_does_not_raise(self):
        """空字符串作为 key 不抛异常。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("")
        assert not limiter.is_limited("")
        limiter.record_attempt("")
        assert limiter.is_limited("")