"""内存速率限制器 单元测试。

测试覆盖：
- 限流阈值判定（未达 / 达到 / 超过阈值）
- 滑动窗口：窗口外旧记录不计数
- record_attempt 计数递增
- 重置后限流状态清除
"""

from __future__ import annotations

import time

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_is_limited_below_threshold(self):
        """未达阈值时 is_limited 应返回 False。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        for _ in range(4):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is False

    def test_is_limited_at_threshold(self):
        """达到阈值时 is_limited 应返回 True。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        for _ in range(5):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_is_limited_above_threshold(self):
        """超过阈值时 is_limited 应返回 True。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(5):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_sliding_window_expired(self):
        """窗口外的旧记录不应计入限流计数。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=1)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        # 在窗口内，应限流
        assert limiter.is_limited("test-key") is True

        # 等待窗口过期
        time.sleep(1.1)
        assert limiter.is_limited("test-key") is False

    def test_record_attempt_returns_count(self):
        """record_attempt 应返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=60)
        assert limiter.record_attempt("test-key") == 1
        assert limiter.record_attempt("test-key") == 2
        assert limiter.record_attempt("test-key") == 3

    def test_reset_clears_state(self):
        """reset 后应清除计数，不再限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

        limiter.reset("test-key")
        assert limiter.is_limited("test-key") is False

    def test_reset_nonexistent_key(self):
        """重置不存在的 key 不应抛异常。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.reset("nonexistent-key")  # should not raise

    def test_different_keys_independent(self):
        """不同 key 的限流状态应相互独立。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        # key-a 已达阈值
        assert limiter.is_limited("key-a") is True
        # key-b 未操作，不应限流
        assert limiter.is_limited("key-b") is False

    def test_zero_max_attempts(self):
        """max_attempts=0 时立即限流。"""
        limiter = RateLimiter(max_attempts=0, window_seconds=60)
        # 即使没有记录，也立即限流
        assert limiter.is_limited("any-key") is True

    def test_large_window(self):
        """大窗口不应影响基本行为。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=3600)
        assert limiter.record_attempt("key") == 1
        assert limiter.is_limited("key") is False
        assert limiter.record_attempt("key") == 2
        assert limiter.is_limited("key") is True