"""RateLimiter 滑动窗口限流器测试。"""

from __future__ import annotations

import time

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """测试 RateLimiter 滑动窗口速率限制器。"""

    def test_is_limited_under_threshold(self):
        """未超过阈值时 is_limited 返回 False。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        key = "test-key"
        for _ in range(4):
            limiter.record_attempt(key)
        assert limiter.is_limited(key) is False

    def test_is_limited_at_threshold(self):
        """达到阈值时 is_limited 返回 True。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        key = "test-key"
        for _ in range(5):
            limiter.record_attempt(key)
        assert limiter.is_limited(key) is True

    def test_is_limited_exceeds_threshold(self):
        """超过阈值时 is_limited 返回 True。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        key = "test-key"
        for _ in range(5):
            limiter.record_attempt(key)
        assert limiter.is_limited(key) is True

    def test_record_attempt_returns_count(self):
        """record_attempt 返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=60)
        key = "test-key"
        count = limiter.record_attempt(key)
        assert count == 1
        count = limiter.record_attempt(key)
        assert count == 2
        count = limiter.record_attempt(key)
        assert count == 3

    def test_reset_clears_key(self):
        """reset 后该 key 的计数清零，不再限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        key = "test-key"
        for _ in range(3):
            limiter.record_attempt(key)
        assert limiter.is_limited(key) is True

        limiter.reset(key)
        assert limiter.is_limited(key) is False

    def test_multiple_keys_independent(self):
        """多个 key 的计数相互独立。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("key-a")
        assert limiter.is_limited("key-a") is True
        assert limiter.is_limited("key-b") is False

    def test_window_expiration(self):
        """窗口过期后旧记录不计数。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=1)
        key = "test-key"
        limiter.record_attempt(key)
        limiter.record_attempt(key)
        # 等待窗口过期
        time.sleep(1.1)
        # 旧记录应被清理，此时只有 1 次新记录
        limiter.record_attempt(key)
        assert limiter.is_limited(key) is False

    def test_reset_nonexistent_key(self):
        """reset 不存在的 key 不会报错。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.reset("nonexistent-key")  # 不应抛出异常

    def test_default_parameters(self):
        """默认参数正确。"""
        limiter = RateLimiter()
        assert limiter.max_attempts == 5
        assert limiter.window_seconds == 60

    def test_custom_parameters(self):
        """自定义参数正确。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=300)
        assert limiter.max_attempts == 10
        assert limiter.window_seconds == 300

    def test_is_limited_empty_key(self):
        """未记录过任何尝试的 key 不受限。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        assert limiter.is_limited("never-recorded") is False