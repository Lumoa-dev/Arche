"""内存速率限制器单元测试。"""

from __future__ import annotations

import time

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """测试 RateLimiter 滑动窗口限流核心逻辑。"""

    def setup_method(self):
        self.limiter = RateLimiter(max_attempts=3, window_seconds=60)

    def test_is_limited_below_threshold(self):
        """阈值内不应被限流。"""
        key = "test-127.0.0.1"
        assert not self.limiter.is_limited(key)
        self.limiter.record_attempt(key)
        assert not self.limiter.is_limited(key)
        self.limiter.record_attempt(key)
        assert not self.limiter.is_limited(key)

    def test_is_limited_at_threshold(self):
        """达到阈值时应被限流。"""
        key = "test-127.0.0.1"
        for _ in range(3):
            self.limiter.record_attempt(key)
        assert self.limiter.is_limited(key)

    def test_is_limited_exceeds_threshold(self):
        """超过阈值后持续限流。"""
        key = "test-127.0.0.1"
        for _ in range(5):
            self.limiter.record_attempt(key)
        assert self.limiter.is_limited(key)

    def test_record_attempt_increments(self):
        """record_attempt 返回当前窗口内的正确计数。"""
        key = "test-127.0.0.1"
        assert self.limiter.record_attempt(key) == 1
        assert self.limiter.record_attempt(key) == 2
        assert self.limiter.record_attempt(key) == 3
        assert self.limiter.record_attempt(key) == 4

    def test_reset_clears_key(self):
        """reset 应清除指定 key 的所有记录。"""
        key = "test-127.0.0.1"
        for _ in range(5):
            self.limiter.record_attempt(key)
        assert self.limiter.is_limited(key)

        self.limiter.reset(key)
        assert not self.limiter.is_limited(key)
        assert self.limiter.record_attempt(key) == 1

    def test_reset_nonexistent_key(self):
        """reset 不存在的 key 不抛异常。"""
        self.limiter.reset("nonexistent-key")
        # 正常通过即可

    def test_different_keys_independent(self):
        """不同 key 的计数互相独立。"""
        key1 = "user1-127.0.0.1"
        key2 = "user2-127.0.0.1"

        for _ in range(3):
            self.limiter.record_attempt(key1)

        assert self.limiter.is_limited(key1)
        assert not self.limiter.is_limited(key2)
        assert self.limiter.record_attempt(key2) == 1

    def test_window_sliding_expires_old_entries(self):
        """窗口滑动后，超出窗口的旧记录不再计入。"""
        key = "test-127.0.0.1"
        # 使用 0.01 秒窗口加速测试
        fast_limiter = RateLimiter(max_attempts=2, window_seconds=0.01)

        fast_limiter.record_attempt(key)
        fast_limiter.record_attempt(key)
        assert fast_limiter.is_limited(key)

        time.sleep(0.015)
        # 窗口已滑动，旧记录过期
        assert not fast_limiter.is_limited(key)
        assert fast_limiter.record_attempt(key) == 1

    def test_is_limited_cleans_expired_entries(self):
        """is_limited 调用时自动清理过期记录。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=0.01)

        limiter.record_attempt("key-a")
        limiter.record_attempt("key-b")

        time.sleep(0.015)

        # is_limited 会触发清理，不会把已过期的 key-b 记录错误累积
        assert not limiter.is_limited("key-b")
        assert limiter.record_attempt("key-b") == 1

    def test_default_parameters(self):
        """默认构造参数为 5 次 / 60 秒窗口。"""
        limiter = RateLimiter()
        assert limiter.max_attempts == 5
        assert limiter.window_seconds == 60

    def test_custom_parameters(self):
        """自定义构造参数正确生效。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=120)
        assert limiter.max_attempts == 10
        assert limiter.window_seconds == 120