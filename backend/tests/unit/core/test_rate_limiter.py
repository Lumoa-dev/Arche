"""RateLimiter 限流器单元测试。

覆盖基于滑动窗口的速率限制器，用于登录等敏感端点的暴力破解防护。
"""

from __future__ import annotations

import time

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiterIsLimited:
    """RateLimiter is_limited 检测测试。"""

    def test_not_limited_under_max(self):
        """未达到上限时返回 False。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        for _ in range(4):
            limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is False

    def test_limited_at_max(self):
        """达到上限时返回 True。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

    def test_not_limited_different_keys(self):
        """不同 key 不互相影响。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True
        assert limiter.is_limited("key2") is False

    def test_limited_exceeds_max(self):
        """超出上限时仍返回 True。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        for _ in range(5):
            limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

    def test_not_limited_after_reset(self):
        """重置后不再限流。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True
        limiter.reset("key1")
        assert limiter.is_limited("key1") is False

    def test_window_expiry(self):
        """窗口过期后应自动解除限流。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=1)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

        time.sleep(1.1)
        assert limiter.is_limited("key1") is False

    def test_new_key_not_limited(self):
        """新 key 不受限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.is_limited("new_key") is False

    def test_empty_attempts(self):
        """无任何记录时不受限。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.is_limited("nonexistent") is False

    def test_high_max_attempts(self):
        """高上限测试。"""
        limiter = RateLimiter(max_attempts=1000, window_seconds=60)
        for _ in range(999):
            limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is False
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

    def test_window_does_not_affect_other_keys(self):
        """一个 key 的窗口过期不影响其他 key。"""
        limiter = RateLimiter(max_attempts=1, window_seconds=60)
        limiter.record_attempt("key_a")
        assert limiter.is_limited("key_a") is True
        assert limiter.is_limited("key_b") is False


class TestRateLimiterRecordAttempt:
    """RateLimiter record_attempt 记录测试。"""

    def test_record_first_attempt(self):
        """首次记录返回 1。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.record_attempt("key1") == 1

    def test_record_multiple_attempts(self):
        """多次记录返回递增计数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.record_attempt("key1") == 1
        assert limiter.record_attempt("key1") == 2
        assert limiter.record_attempt("key1") == 3

    def test_record_separate_keys(self):
        """不同 key 独立计数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.record_attempt("key1") == 1
        assert limiter.record_attempt("key2") == 1
        assert limiter.record_attempt("key1") == 2

    def test_record_after_window_expiry(self):
        """窗口过期后重新计数。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=1)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        time.sleep(1.1)
        assert limiter.record_attempt("key1") == 1

    def test_record_after_reset(self):
        """重置后计数归 1。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        limiter.reset("key1")
        assert limiter.record_attempt("key1") == 1


class TestRateLimiterReset:
    """RateLimiter reset 重置测试。"""

    def test_reset_existing_key(self):
        """重置已有 key 不应报错。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.reset("key1")
        assert limiter.is_limited("key1") is False

    def test_reset_nonexistent_key(self):
        """重置不存在的 key 不应报错。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        limiter.reset("nonexistent")  # 不应抛出异常

    def test_reset_then_record(self):
        """重置后可继续记录。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        limiter.reset("key1")
        assert limiter.record_attempt("key1") == 1

    def test_reset_only_affects_one_key(self):
        """重置只影响指定 key。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key1")
        limiter.record_attempt("key2")
        limiter.record_attempt("key1")
        limiter.reset("key1")
        assert limiter.is_limited("key1") is False
        assert limiter.is_limited("key2") is False


class TestRateLimiterEdgeCases:
    """RateLimiter 边界情况测试。"""

    def test_max_attempts_1(self):
        """max_attempts=1 时立即限流。"""
        limiter = RateLimiter(max_attempts=1, window_seconds=60)
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

    def test_max_attempts_0(self):
        """max_attempts=0 时始终限流。"""
        limiter = RateLimiter(max_attempts=0, window_seconds=60)
        assert limiter.is_limited("key1") is True

    def test_window_0(self):
        """window_seconds=0 时所有记录立即过期，不限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=0)
        for _ in range(10):
            limiter.record_attempt("key1")
        # 窗口为 0，now - 0 = now，只有 t > now 的记录才保留
        # 所有记录的时间戳 <= now，所以全部过期
        assert limiter.is_limited("key1") is False

    def test_is_limited_without_recording(self):
        """没有记录的 key 不应受限。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.is_limited("no_records") is False

    def test_shared_state(self):
        """同一个 limiter 实例共享状态。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("shared_key")
        limiter.record_attempt("shared_key")
        assert limiter.is_limited("shared_key") is True

    def test_large_window(self):
        """大窗口不应影响限流逻辑。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=3600)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

    def test_default_params(self):
        """默认参数为 max_attempts=5, window_seconds=60。"""
        limiter = RateLimiter()
        assert limiter.max_attempts == 5
        assert limiter.window_seconds == 60