"""RateLimiter 行为测试。

内存速率限制器，用于登录等敏感端点的暴力破解防护。
纯函数测试，无数据库依赖。
"""

from __future__ import annotations

import time

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """滑动窗口速率限制器行为测试。"""

    def test_is_limited_under_threshold(self):
        """未达阈值不应被限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        for _ in range(4):
            assert limiter.is_limited("test-key") is False

    def test_is_limited_at_threshold(self):
        """达到阈值应被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_record_attempt_increases_count(self):
        """record_attempt 应返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        count = limiter.record_attempt("test-key")
        assert count == 1
        count = limiter.record_attempt("test-key")
        assert count == 2

    def test_record_attempt_triggers_is_limited(self):
        """record_attempt 后 is_limited 应正确反映状态。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_reset_clears_count(self):
        """reset 应清除指定 key 的计数。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        limiter.reset("test-key")
        assert limiter.is_limited("test-key") is False

    def test_reset_nonexistent_key(self):
        """reset 不存在的 key 不应报错。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.reset("nonexistent-key")  # 不应抛出异常

    def test_different_keys_independent(self):
        """不同 key 的计数应独立。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("key-a")
        # key-a 已达上限
        assert limiter.is_limited("key-a") is True
        # key-b 应不受影响
        assert limiter.is_limited("key-b") is False

    def test_window_expiry(self):
        """窗口过期后应重置计数。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0.1)  # 100ms 窗口
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True
        # 等待窗口过期
        time.sleep(0.15)
        assert limiter.is_limited("test-key") is False

    def test_max_attempts_zero(self):
        """max_attempts=0 时所有请求都应被限流。"""
        limiter = RateLimiter(max_attempts=0, window_seconds=60)
        assert limiter.is_limited("test-key") is True

    def test_max_attempts_one(self):
        """max_attempts=1 时第一次记录后即被限流。"""
        limiter = RateLimiter(max_attempts=1, window_seconds=60)
        assert limiter.is_limited("test-key") is False
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_is_limited_does_not_increment_count(self):
        """is_limited 不应修改计数。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        # 多次调用 is_limited 不应增加计数
        limiter.is_limited("test-key")
        limiter.is_limited("test-key")
        count = limiter.record_attempt("test-key")
        assert count == 2  # 仍是第二次

    def test_large_number_of_attempts(self):
        """大量尝试应正确计数。"""
        limiter = RateLimiter(max_attempts=100, window_seconds=60)
        for i in range(100):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True