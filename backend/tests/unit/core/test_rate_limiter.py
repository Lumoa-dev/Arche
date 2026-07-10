"""RateLimiter 滑动窗口速率限制器测试。"""

import time
from unittest.mock import patch

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """测试 RateLimiter 核心功能。"""

    def setup_method(self):
        self.limiter = RateLimiter(max_attempts=3, window_seconds=60)

    def test_init_default_params(self):
        """默认参数初始化正确。"""
        limiter = RateLimiter()
        assert limiter.max_attempts == 5
        assert limiter.window_seconds == 60

    def test_init_custom_params(self):
        """自定义参数初始化正确。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=30)
        assert limiter.max_attempts == 10
        assert limiter.window_seconds == 30

    def test_is_limited_under_threshold(self):
        """未超过阈值时不受限。"""
        assert not self.limiter.is_limited("test-key")

    def test_is_limited_at_threshold(self):
        """达到阈值后受限。"""
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        assert self.limiter.is_limited("test-key")

    def test_record_attempt_returns_count(self):
        """record_attempt 返回当前窗口内尝试次数。"""
        count1 = self.limiter.record_attempt("test-key")
        assert count1 == 1

        count2 = self.limiter.record_attempt("test-key")
        assert count2 == 2

    def test_different_keys_isolated(self):
        """不同 key 的计数互不影响。"""
        self.limiter.record_attempt("key-a")
        self.limiter.record_attempt("key-a")
        self.limiter.record_attempt("key-a")

        assert self.limiter.is_limited("key-a")
        assert not self.limiter.is_limited("key-b")

    def test_reset_clears_count(self):
        """reset 后计数清零。"""
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        self.limiter.reset("test-key")

        assert not self.limiter.is_limited("test-key")
        assert self.limiter.record_attempt("test-key") == 1

    def test_reset_nonexistent_key(self):
        """重置不存在的 key 不报错。"""
        self.limiter.reset("nonexistent-key")  # 不应抛出异常

    def test_window_expiration(self):
        """窗口过期后旧记录被清理，不再受限。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=1)

        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key")

        # 等待窗口过期
        time.sleep(1.1)

        # 窗口过期后，旧记录被清理，不再受限
        assert not limiter.is_limited("test-key")
        # 新记录从 1 开始计数
        assert limiter.record_attempt("test-key") == 1

    @patch("time.time")
    def test_is_limited_cleans_expired(self, mock_time):
        """is_limited 在检查时清理过期记录。"""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(max_attempts=2, window_seconds=10)

        limiter.record_attempt("test-key")  # time=1000
        limiter.record_attempt("test-key")  # time=1000
        assert limiter.is_limited("test-key")  # 窗口内

        # 推进到窗口外
        mock_time.return_value = 1011.0
        assert not limiter.is_limited("test-key")
        # 验证旧记录已被清理
        assert len(limiter._attempts["test-key"]) == 0

    def test_high_frequency_no_crash(self):
        """高频调用不崩溃。"""
        for i in range(1000):
            self.limiter.record_attempt(f"key-{i % 10}")
        for i in range(10):
            self.limiter.is_limited(f"key-{i}")

    def test_empty_key_handling(self):
        """空字符串作为 key 也能正常处理。"""
        self.limiter.record_attempt("")
        assert self.limiter.record_attempt("") == 2

    def test_large_window(self):
        """大窗口参数正常工作。"""
        limiter = RateLimiter(max_attempts=100, window_seconds=86400)
        for _ in range(50):
            limiter.record_attempt("test-key")
        assert not limiter.is_limited("test-key")
        for _ in range(50):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key")