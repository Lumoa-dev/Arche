"""速率限制器单元测试。"""

from unittest.mock import patch

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """测试 RateLimiter 滑动窗口速率限制器。"""

    def test_is_limited_under_limit(self):
        """未超过限制时 is_limited 返回 False。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        with patch("time.time", return_value=1000.0):
            for _ in range(3):
                limiter.record_attempt("test-key")
            assert limiter.is_limited("test-key") is False

    def test_is_limited_at_limit(self):
        """达到限制时 is_limited 返回 True。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        with patch("time.time", return_value=1000.0):
            for _ in range(5):
                limiter.record_attempt("test-key")
            assert limiter.is_limited("test-key") is True

    def test_record_attempt_increments(self):
        """record_attempt 返回正确的累计次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        with patch("time.time", return_value=1000.0):
            count1 = limiter.record_attempt("test-key")
            count2 = limiter.record_attempt("test-key")
            count3 = limiter.record_attempt("test-key")
            assert count1 == 1
            assert count2 == 2
            assert count3 == 3

    def test_reset_clears_key(self):
        """reset 清除指定 key 的计数记录。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        with patch("time.time", return_value=1000.0):
            for _ in range(5):
                limiter.record_attempt("test-key")
            assert limiter.is_limited("test-key") is True
            limiter.reset("test-key")
            assert limiter.is_limited("test-key") is False

    def test_window_sliding_expires_old_entries(self):
        """窗口滑动：超过 window_seconds 的旧记录自动过期。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        # 在 t=0 时记录 5 次，达到限制
        with patch("time.time", return_value=0.0):
            for _ in range(5):
                limiter.record_attempt("test-key")
            assert limiter.is_limited("test-key") is True

        # 在 t=61 时窗口已滑过，旧记录全部过期
        with patch("time.time", return_value=61.0):
            assert limiter.is_limited("test-key") is False

    def test_multiple_keys_independent(self):
        """多个 key 的计数互不影响。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        with patch("time.time", return_value=1000.0):
            for _ in range(5):
                limiter.record_attempt("key1")
            for _ in range(3):
                limiter.record_attempt("key2")

            assert limiter.is_limited("key1") is True
            assert limiter.is_limited("key2") is False

    def test_max_attempts_one(self):
        """max_attempts=1 时，一次尝试即触发限流。"""
        limiter = RateLimiter(max_attempts=1, window_seconds=60)
        with patch("time.time", return_value=1000.0):
            limiter.record_attempt("test-key")
            assert limiter.is_limited("test-key") is True

    def test_window_seconds_zero(self):
        """window_seconds=0 时窗口坍缩为时间点，记录立即过期。

        由于过滤条件是 t > window_start（严格大于），
        记录时间等于 window_start，所以被过滤掉，
        is_limited 始终返回 False。
        """
        limiter = RateLimiter(max_attempts=5, window_seconds=0)
        with patch("time.time", return_value=1000.0):
            limiter.record_attempt("test-key")
            # 记录时间 1000.0 不满足 > 1000.0 - 0 = 1000.0
            assert limiter.is_limited("test-key") is False

    def test_is_limited_at_max_attempts_minus_one(self):
        """恰好 max_attempts - 1 次尝试时 is_limited 返回 False。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        with patch("time.time", return_value=1000.0):
            for _ in range(4):
                limiter.record_attempt("test-key")
            assert limiter.is_limited("test-key") is False