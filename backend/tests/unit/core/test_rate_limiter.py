"""速率限制器测试 —— 滑动窗口、边界条件、并发安全。"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """测试滑动窗口速率限制器核心功能。"""

    def test_init_default_values(self):
        """默认参数正确。"""
        limiter = RateLimiter()
        assert limiter.max_attempts == 5
        assert limiter.window_seconds == 60

    def test_init_custom_values(self):
        """自定义参数正确。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=10)
        assert limiter.max_attempts == 3
        assert limiter.window_seconds == 10

    def test_record_attempt_increments_count(self):
        """record_attempt 正确递增计数。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        assert limiter.record_attempt("key1") == 1
        assert limiter.record_attempt("key1") == 2
        assert limiter.record_attempt("key1") == 3

    def test_record_attempt_separate_keys(self):
        """不同 key 的计数互不影响。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        assert limiter.record_attempt("key-a") == 1
        assert limiter.record_attempt("key-b") == 1
        assert limiter.record_attempt("key-a") == 2
        assert limiter.record_attempt("key-b") == 2

    def test_is_limited_below_threshold(self):
        """未达到阈值时返回 False。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is False

    def test_is_limited_at_threshold(self):
        """达到阈值时返回 True。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

    def test_is_limited_above_threshold(self):
        """超过阈值时返回 True。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

    def test_window_expiry_clears_old_records(self):
        """窗口过期后旧记录被清理，不再受限。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=10)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

        # 模拟时间跳过窗口
        with patch("time.time", return_value=time.time() + 11):
            assert limiter.is_limited("key1") is False
            assert limiter.record_attempt("key1") == 1

    def test_mixed_records_within_window(self):
        """窗口内新旧记录混合时计数正确。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=10)
        limiter.record_attempt("key1")

        with patch("time.time", return_value=time.time() + 5):
            limiter.record_attempt("key1")
            assert limiter.is_limited("key1") is False

        with patch("time.time", return_value=time.time() + 9):
            limiter.record_attempt("key1")
            assert limiter.is_limited("key1") is True

        # 第 2 条记录已过期，仅剩 2 条
        with patch("time.time", return_value=time.time() + 15):
            assert limiter.is_limited("key1") is False

    def test_reset_clears_key(self):
        """reset 后 key 不再受限。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

        limiter.reset("key1")
        assert limiter.is_limited("key1") is False
        assert limiter.record_attempt("key1") == 1

    def test_reset_nonexistent_key(self):
        """reset 不存在的 key 不抛出异常。"""
        limiter = RateLimiter()
        limiter.reset("nonexistent")  # 不应抛出异常

    def test_multiple_keys_independent_limiting(self):
        """多个 key 独立限流。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("user-a")
        limiter.record_attempt("user-b")
        limiter.record_attempt("user-a")
        assert limiter.is_limited("user-a") is True
        assert limiter.is_limited("user-b") is False

    def test_window_boundary_zero_seconds(self):
        """window_seconds 为 0 时所有记录立即过期。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        # window_start = now - 0 = now，旧记录 t > now 不成立
        assert limiter.is_limited("key1") is False

    def test_large_number_of_records(self):
        """大量记录的计数性能正确。"""
        limiter = RateLimiter(max_attempts=100, window_seconds=60)
        for _ in range(50):
            limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is False
        for _ in range(50):
            limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

    def test_is_limited_without_record(self):
        """从未记录的 key 不受限。"""
        limiter = RateLimiter()
        assert limiter.is_limited("never-recorded") is False

    def test_window_cleanup_on_record(self):
        """record_attempt 自动清理旧记录。"""
        limiter = RateLimiter(max_attempts=1, window_seconds=1)
        limiter.record_attempt("key1")

        with patch("time.time", return_value=time.time() + 2):
            # 旧记录已过期，record_attempt 应清理后返回 1
            assert limiter.record_attempt("key1") == 1