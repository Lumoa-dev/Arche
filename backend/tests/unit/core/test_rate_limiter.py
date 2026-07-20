"""RateLimiter 滑动窗口速率限制器测试。"""

from __future__ import annotations

import time

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """测试 RateLimiter 核心行为。"""

    def test_is_limited_returns_false_when_below_max(self):
        """未达上限时返回 False。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.is_limited("test-key") is False

    def test_is_limited_returns_true_when_at_max(self):
        """达到上限时返回 True。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_is_limited_returns_false_after_window_expires(self):
        """窗口过期后限流自动解除。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        # 用一个极短的窗口测试
        limiter = RateLimiter(max_attempts=2, window_seconds=0.01)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True
        time.sleep(0.02)
        assert limiter.is_limited("test-key") is False

    def test_record_attempt_returns_count(self):
        """record_attempt 返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=60)
        assert limiter.record_attempt("test-key") == 1
        assert limiter.record_attempt("test-key") == 2
        assert limiter.record_attempt("test-key") == 3

    def test_reset_clears_key(self):
        """reset 后该 key 不再受限。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True
        limiter.reset("test-key")
        assert limiter.is_limited("test-key") is False

    def test_different_keys_are_independent(self):
        """不同 key 的计数互不影响。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        assert limiter.is_limited("key-a") is True
        assert limiter.is_limited("key-b") is False

    def test_old_attempts_are_cleaned_on_check(self):
        """is_limited 自动清理窗口外的旧记录。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0.01)
        limiter.record_attempt("test-key")
        time.sleep(0.02)
        # 旧记录应在 is_limited 检查时被清理
        assert limiter.is_limited("test-key") is False
        # 再次记录一次，不应超过上限
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is False

    def test_reset_nonexistent_key_does_not_raise(self):
        """reset 不存在的 key 不抛异常。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        limiter.reset("nonexistent-key")  # 不应抛异常