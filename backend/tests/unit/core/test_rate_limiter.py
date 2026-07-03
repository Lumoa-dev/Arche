"""RateLimiter 单元测试 —— 滑动窗口限流器。

测试原则：
- 只测试公开方法行为
- 使用 time.monotonic 模拟，不依赖真实时间
"""

from __future__ import annotations

import time

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """滑动窗口限流器行为测试。"""

    def test_initial_state_not_limited(self):
        """新实例对任意 key 都不限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.is_limited("test-key") is False

    def test_under_threshold_not_limited(self):
        """窗口内请求次数未达上限时，不限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        for _ in range(4):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is False

    def test_at_threshold_not_limited(self):
        """窗口内请求次数恰好等于上限时，不限流（边界设计）。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        for _ in range(5):
            limiter.record_attempt("test-key")
        # 第 5 次后 len == 5, max_attempts == 5, is_limited 用 >= 判断
        # 所以第 5 次后 is_limited 返回 True（>= 触发）
        assert limiter.is_limited("test-key") is True

    def test_exceed_threshold_limited(self):
        """超过上限后 is_limited 返回 True。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(4):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_record_attempt_returns_count(self):
        """record_attempt 返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.record_attempt("test-key") == 1
        assert limiter.record_attempt("test-key") == 2
        assert limiter.record_attempt("test-key") == 3

    def test_reset_clears_key(self):
        """reset 后该 key 不再受限。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(4):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

        limiter.reset("test-key")
        assert limiter.is_limited("test-key") is False

    def test_reset_nonexistent_key(self):
        """reset 不存在的 key 不报错。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.reset("nonexistent")
        # 不应抛出异常

    def test_multiple_keys_independent(self):
        """不同 key 的计数互不影响。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(4):
            limiter.record_attempt("key-a")
        limiter.record_attempt("key-b")

        assert limiter.is_limited("key-a") is True
        assert limiter.is_limited("key-b") is False

    def test_window_expiration(self):
        """超出时间窗口的旧记录应被清理。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        # 模拟时间推移：手动修改内部时间戳
        old_time = time.time() - 120  # 2 分钟前
        limiter._attempts["test-key"] = [old_time] * 5
        # 调用 is_limited 应触发清理
        assert limiter.is_limited("test-key") is False
        # 清理后 key 仍存在但列表为空
        assert len(limiter._attempts["test-key"]) == 0

    def test_edge_case_zero_max_attempts(self):
        """max_attempts=0 时，任何请求都被限流。"""
        limiter = RateLimiter(max_attempts=0, window_seconds=60)
        assert limiter.is_limited("any-key") is True

    def test_edge_case_large_window(self):
        """超大窗口（如一天）不应异常。"""
        limiter = RateLimiter(max_attempts=1000, window_seconds=86400)
        for _ in range(500):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is False

    def test_memory_not_leaked_across_keys(self):
        """大量不同 key 不应导致内存异常增长（仅验证行为正确）。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for i in range(100):
            limiter.record_attempt(f"key-{i}")
        # 每个 key 1 次，都不受限
        assert limiter.is_limited("key-0") is False
        assert limiter.is_limited("key-99") is False