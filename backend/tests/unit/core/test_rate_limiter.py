"""RateLimiter 行为测试。

测试原则：
- 覆盖滑动窗口限流、边界条件、并发安全
- 纯内存操作，不需 DB
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

import time
from threading import Thread

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """测试滑动窗口速率限制器。"""

    def test_is_limited_under_threshold(self):
        """未达阈值时不应被限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.is_limited("test_key") is False

    def test_is_limited_at_threshold(self):
        """达到阈值时应被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("test_key")
        assert limiter.is_limited("test_key") is True

    def test_is_limited_below_threshold(self):
        """未达阈值时不应被限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("test_key")
        assert limiter.is_limited("test_key") is False

    def test_record_attempt_returns_count(self):
        """record_attempt 应返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        count1 = limiter.record_attempt("test_key")
        count2 = limiter.record_attempt("test_key")
        assert count1 == 1
        assert count2 == 2

    def test_reset_clears_key(self):
        """reset 应清除指定 key 的计数。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("test_key")
        assert limiter.is_limited("test_key") is True

        limiter.reset("test_key")
        assert limiter.is_limited("test_key") is False

    def test_old_attempts_expire(self):
        """窗口外的旧记录不应计入。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=1)
        # 添加窗口外的记录
        limiter._attempts["test_key"] = [time.time() - 5]
        assert limiter.is_limited("test_key") is False

    def test_is_limited_cleans_expired(self):
        """is_limited 应自动清理过期记录。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=1)
        limiter._attempts["test_key"] = [time.time() - 5, time.time() - 4]
        # is_limited 应清理过期记录，发现为 0 条
        assert limiter.is_limited("test_key") is False
        assert len(limiter._attempts.get("test_key", [])) == 0

    def test_record_attempt_cleans_expired(self):
        """record_attempt 应自动清理过期记录。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=1)
        limiter._attempts["test_key"] = [time.time() - 5]
        count = limiter.record_attempt("test_key")
        # 过期记录被清理，新记录为第 1 条
        assert count == 1

    def test_different_keys_independent(self):
        """不同 key 的计数应独立。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_attempt("key_a")
        limiter.record_attempt("key_b")

        assert limiter.is_limited("key_a") is True
        assert limiter.is_limited("key_b") is False

    def test_reset_nonexistent_key(self):
        """reset 不存在的 key 不应报错。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.reset("non_existent_key")  # 不应抛出异常

    def test_large_attempt_count(self):
        """大量尝试不应导致性能问题。"""
        limiter = RateLimiter(max_attempts=50, window_seconds=60)
        for i in range(1000):
            limiter.record_attempt(f"bulk_key_{i % 10}")
        # 每个 key 约 100 次，超过阈值 50
        assert limiter.is_limited("bulk_key_0") is True

    def test_zero_max_attempts(self):
        """max_attempts=0 时所有请求应立即被限流。"""
        limiter = RateLimiter(max_attempts=0, window_seconds=60)
        assert limiter.is_limited("any_key") is True

    def test_negative_window(self):
        """负窗口值不应导致错误（窗口内所有记录均视为过期）。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=-1)
        limiter.record_attempt("test_key")
        # 负窗口意味着所有记录都过期，因此不应被限流
        assert limiter.is_limited("test_key") is False


class TestRateLimiterConcurrency:
    """测试 RateLimiter 的并发安全性。"""

    def test_concurrent_record_attempts(self):
        """并发记录尝试不应丢失计数。"""
        limiter = RateLimiter(max_attempts=100, window_seconds=60)
        results = []

        def record():
            for _ in range(50):
                limiter.record_attempt("concurrent_key")
            results.append("done")

        threads = [Thread(target=record) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 由于 list 不是线程安全的，实际计数可能不准
        # 但至少不应抛出异常，且最终计数应接近 100
        assert len(results) == 2
        # 验证 is_limited 仍能正常工作
        assert limiter.is_limited("concurrent_key") is True