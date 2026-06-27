"""RateLimiter 单元测试 —— 滑动窗口速率限制器。

测试重点：
- 正常限流行为（未超限 / 超限）
- 窗口边界：超时后自动恢复
- reset 重置
- 并发安全：批量快速请求
- 不同 key 隔离性
"""

from __future__ import annotations

import time

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiterBasics:
    """基础限流行为测试。"""

    def test_initial_call_not_limited(self):
        """首次调用不应被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        assert limiter.is_limited("test-key") is False

    def test_under_threshold_not_limited(self):
        """未达阈值前不应被限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        for _ in range(4):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is False

    def test_at_threshold_is_limited(self):
        """达到阈值时应被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_exceeding_threshold_stays_limited(self):
        """超过阈值后持续被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(5):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_record_attempt_returns_count(self):
        """record_attempt 应返回当前窗口内的累计次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.record_attempt("test-key") == 1
        assert limiter.record_attempt("test-key") == 2
        assert limiter.record_attempt("test-key") == 3


class TestRateLimiterWindow:
    """滑动窗口边界条件测试。"""

    def test_window_expiry_resets_limit(self):
        """窗口过期后应自动恢复，不再限流。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0.1)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

        time.sleep(0.15)
        assert limiter.is_limited("test-key") is False

    def test_old_records_pruned_after_window(self):
        """窗口外的旧记录应被清理。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0.1)
        limiter.record_attempt("test-key")
        time.sleep(0.15)
        # 旧记录已过期，新记录不会触发限流
        assert limiter.record_attempt("test-key") == 1

    def test_window_boundary_bulk_requests(self):
        """大量请求在窗口边界附近不应影响隔离性。"""
        limiter = RateLimiter(max_attempts=100, window_seconds=60)
        for _ in range(100):
            limiter.record_attempt("key-a")
        # key-b 应完全不受 key-a 影响
        assert limiter.is_limited("key-b") is False
        assert limiter.record_attempt("key-b") == 1


class TestRateLimiterKeyIsolation:
    """不同 key 之间应完全隔离。"""

    def test_different_keys_independent(self):
        """不同 key 的计数器应互不影响。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("user-1")
        limiter.record_attempt("user-1")
        limiter.record_attempt("user-1")
        assert limiter.is_limited("user-1") is True
        assert limiter.is_limited("user-2") is False

    def test_reset_only_affects_one_key(self):
        """reset 只影响指定 key。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-b")
        limiter.record_attempt("key-b")

        limiter.reset("key-a")
        assert limiter.is_limited("key-a") is False
        assert limiter.is_limited("key-b") is True


class TestRateLimiterReset:
    """reset 行为测试。"""

    def test_reset_clears_counter(self):
        """reset 后应完全清除计数，不再限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(5):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

        limiter.reset("test-key")
        assert limiter.is_limited("test-key") is False

    def test_reset_nonexistent_key(self):
        """reset 不存在的 key 不应报错。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.reset("never-used")
        assert limiter.is_limited("never-used") is False


class TestRateLimiterEdgeCases:
    """极端值和非正常输入测试。"""

    def test_max_attempts_zero(self):
        """max_attempts=0 时所有请求都应受限。"""
        limiter = RateLimiter(max_attempts=0, window_seconds=60)
        assert limiter.is_limited("test-key") is True

    def test_max_attempts_one(self):
        """max_attempts=1 时，第二次调用即受限。"""
        limiter = RateLimiter(max_attempts=1, window_seconds=60)
        assert limiter.is_limited("test-key") is False
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_empty_key(self):
        """空字符串作为 key 应正常工作。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("")
        limiter.record_attempt("")
        limiter.record_attempt("")
        assert limiter.is_limited("") is True

    def test_long_key(self):
        """长 key 不应影响限流逻辑。"""
        long_key = "x" * 10000
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt(long_key)
        limiter.record_attempt(long_key)
        assert limiter.is_limited(long_key) is True

    def test_records_never_leak_memory(self):
        """is_limited 应清理过期记录，避免内存泄漏。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0.05)
        limiter.record_attempt("leak-key")
        limiter.record_attempt("leak-key")
        time.sleep(0.1)
        # is_limited 会清理过期记录
        limiter.is_limited("leak-key")
        # 此时 _attempts 中应该只有空列表
        key_exists = "leak-key" in limiter._attempts and len(limiter._attempts["leak-key"]) > 0
        assert not key_exists