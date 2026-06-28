"""核心 — RateLimiter 单元测试。

覆盖滑动窗口限流的边界条件：窗口边界、精确计数、重置语义。
纯 mock，无数据库依赖。
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiterBasics:
    """基础功能测试。"""

    def test_init_defaults(self):
        limiter = RateLimiter()
        assert limiter.max_attempts == 5
        assert limiter.window_seconds == 60

    def test_init_custom(self):
        limiter = RateLimiter(max_attempts=3, window_seconds=10)
        assert limiter.max_attempts == 3
        assert limiter.window_seconds == 10

    def test_not_limited_under_threshold(self):
        """低于阈值时 is_limited 返回 False。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        assert limiter.is_limited("test-key") is False
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is False
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is False

    def test_limited_at_threshold(self):
        """达到阈值时 is_limited 返回 True。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_limited_exceeds_threshold(self):
        """超过阈值时仍然受限。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(5):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_record_attempt_returns_count(self):
        """record_attempt 返回窗口内的累计次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.record_attempt("key") == 1
        assert limiter.record_attempt("key") == 2
        assert limiter.record_attempt("key") == 3


class TestRateLimiterWindow:
    """滑动窗口行为测试。"""

    def test_window_slides_old_records_removed(self):
        """窗口外的旧记录不纳入计数。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=10)
        limiter.record_attempt("key")
        limiter.record_attempt("key")

        # 模拟时间前进 10 秒，旧记录过期
        fake_now = time.time() + 10
        with patch("time.time", return_value=fake_now):
            limiter.record_attempt("key")  # 此记录在窗口内
            # 前 2 条已过期，窗口内只有 1 条
            assert limiter.is_limited("key") is False

    def test_window_boundary_just_within(self):
        """恰好落在窗口边界的记录应计入。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=10)
        t0 = time.time()
        with patch("time.time", return_value=t0):
            limiter.record_attempt("key")

        # 前进 9.9 秒，仍在窗口内
        with patch("time.time", return_value=t0 + 9.9):
            limiter.record_attempt("key")
            assert limiter.is_limited("key") is True

    def test_window_boundary_just_outside(self):
        """窗口边界外的记录不计入。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=10)
        t0 = time.time()
        with patch("time.time", return_value=t0):
            limiter.record_attempt("key")

        # 前进 10 秒，旧记录过期
        with patch("time.time", return_value=t0 + 10):
            assert limiter.is_limited("key") is False
            limiter.record_attempt("key")
            assert limiter.is_limited("key") is False  # 只有 1 条


class TestRateLimiterReset:
    """重置功能测试。"""

    def test_reset_clears_count(self):
        """reset 后计数归零。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("key")
        assert limiter.is_limited("key") is True

        limiter.reset("key")
        assert limiter.is_limited("key") is False

    def test_reset_nonexistent_key(self):
        """重置不存在的 key 不抛异常。"""
        limiter = RateLimiter()
        limiter.reset("nonexistent")
        assert limiter.is_limited("nonexistent") is False

    def test_keys_independent(self):
        """不同 key 的计数互不影响。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")

        assert limiter.is_limited("key-a") is True
        assert limiter.is_limited("key-b") is False

        limiter.reset("key-a")
        assert limiter.is_limited("key-a") is False
        assert limiter.is_limited("key-b") is False