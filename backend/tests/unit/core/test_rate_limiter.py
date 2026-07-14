"""RateLimiter 滑动窗口限流器测试。

测试原则：
- 只测公开方法输入输出
- 每个测试独立，不依赖执行顺序
- 使用 time 模拟控制时间窗口
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiterInit:
    """测试初始化。"""

    def test_default_params(self):
        """默认参数应正确设置。"""
        limiter = RateLimiter()
        assert limiter.max_attempts == 5
        assert limiter.window_seconds == 60

    def test_custom_params(self):
        """自定义参数应正确设置。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=30)
        assert limiter.max_attempts == 3
        assert limiter.window_seconds == 30


class TestRateLimiterIsLimited:
    """测试 is_limited 方法。"""

    def test_not_limited_initially(self):
        """初始状态不应被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        assert limiter.is_limited("test-key") is False

    def test_limited_after_max_attempts(self):
        """达到最大尝试次数后应被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_not_limited_below_max(self):
        """未达到最大尝试次数时不应被限流。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is False

    def test_different_keys_independent(self):
        """不同 key 的限流状态应独立。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        assert limiter.is_limited("key-a") is True
        assert limiter.is_limited("key-b") is False


class TestRateLimiterRecordAttempt:
    """测试 record_attempt 方法。"""

    def test_record_attempt_returns_count(self):
        """record_attempt 应返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.record_attempt("test-key") == 1
        assert limiter.record_attempt("test-key") == 2

    def test_record_attempt_beyond_limit(self):
        """超过限制后 record_attempt 仍应返回计数。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        count = limiter.record_attempt("test-key")
        assert count == 3


class TestRateLimiterReset:
    """测试 reset 方法。"""

    def test_reset_clears_attempts(self):
        """reset 后应清除该 key 的尝试记录。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

        limiter.reset("test-key")
        assert limiter.is_limited("test-key") is False
        assert limiter.record_attempt("test-key") == 1

    def test_reset_nonexistent_key(self):
        """reset 不存在的 key 不应抛出异常。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.reset("nonexistent")  # 不应报错

    def test_reset_does_not_affect_other_keys(self):
        """reset 某个 key 不应影响其他 key。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-b")

        limiter.reset("key-a")
        assert limiter.is_limited("key-a") is False
        assert limiter.record_attempt("key-b") == 2


class TestRateLimiterWindowExpiry:
    """测试滑动窗口过期行为。"""

    def test_old_attempts_expire(self):
        """窗口外的旧记录不应计入限流。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=10)

        with patch.object(time, "time", return_value=1000.0):
            limiter.record_attempt("test-key")
            limiter.record_attempt("test-key")
            assert limiter.is_limited("test-key") is True

        # 模拟时间前进 15 秒（超出窗口）
        with patch.object(time, "time", return_value=1015.0):
            assert limiter.is_limited("test-key") is False
            # 旧记录应该已被清理，这是新窗口内的第一次
            assert limiter.record_attempt("test-key") == 1