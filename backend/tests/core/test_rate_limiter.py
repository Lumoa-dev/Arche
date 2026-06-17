"""RateLimiter 单元测试 —— 滑动窗口速率限制器。"""

from __future__ import annotations

import time

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_not_limited_below_max(self):
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        for _ in range(4):
            limiter.record_attempt("key1")
        assert not limiter.is_limited("key1")

    def test_limited_at_max(self):
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("key1")
        assert limiter.is_limited("key1")

    def test_limited_exceeds_max(self):
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        for _ in range(5):
            limiter.record_attempt("key1")
        assert limiter.is_limited("key1")

    def test_reset_clears_limit(self):
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1")
        limiter.reset("key1")
        assert not limiter.is_limited("key1")

    def test_isolation_by_key(self):
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("user-a")
        limiter.record_attempt("user-a")
        assert limiter.is_limited("user-a")
        assert not limiter.is_limited("user-b")

    def test_window_expiry(self):
        limiter = RateLimiter(max_attempts=2, window_seconds=0.1)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1")
        time.sleep(0.15)
        assert not limiter.is_limited("key1"), "窗口过期后应解除限制"

    def test_record_attempt_returns_count(self):
        limiter = RateLimiter(max_attempts=10, window_seconds=60)
        assert limiter.record_attempt("key1") == 1
        assert limiter.record_attempt("key1") == 2
        assert limiter.record_attempt("key1") == 3

    def test_reset_nonexistent_key(self):
        """重置不存在的 key 不应报错。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        limiter.reset("nonexistent")  # should not raise

    def test_is_limited_no_attempts(self):
        """无尝试记录时不应被限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert not limiter.is_limited("fresh_key")

    def test_window_cleans_old_entries(self):
        """record_attempt 和 is_limited 应清理窗口外的旧记录。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=0.05)
        limiter.record_attempt("key1")
        time.sleep(0.06)
        # 旧记录已过期，新记录应在窗口内
        limiter.record_attempt("key1")
        assert not limiter.is_limited("key1"), "旧记录过期后不应限流"
