"""RateLimiter 滑动窗口速率限制器测试。

风险：登录等敏感端点的暴力破解防护，限流逻辑错误将导致安全漏洞。
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """测试滑动窗口速率限制器。"""

    def setup_method(self):
        self.limiter = RateLimiter(max_attempts=3, window_seconds=60)

    def test_is_limited_empty(self):
        """空的限制器不应该限制任何 key。"""
        assert not self.limiter.is_limited("test-key")

    def test_under_threshold_not_limited(self):
        """未达到阈值时不应被限流。"""
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        assert not self.limiter.is_limited("test-key")

    def test_at_threshold_is_limited(self):
        """达到阈值时应该被限流。"""
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        assert self.limiter.is_limited("test-key")

    def test_exceed_threshold(self):
        """超过阈值后所有尝试都应该被限流。"""
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")  # 第 4 次
        assert self.limiter.is_limited("test-key")

    def test_reset_clears_limit(self):
        """重置后限制应该被清除。"""
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        assert self.limiter.is_limited("test-key")

        self.limiter.reset("test-key")
        assert not self.limiter.is_limited("test-key")

    def test_reset_nonexistent_key(self):
        """重置不存在的 key 不应该抛出异常。"""
        self.limiter.reset("non-existent-key")  # 不应抛出异常

    def test_record_attempt_returns_count(self):
        """record_attempt 返回当前窗口内的尝试次数。"""
        count1 = self.limiter.record_attempt("test-key")
        assert count1 == 1

        count2 = self.limiter.record_attempt("test-key")
        assert count2 == 2

    def test_different_keys_independent(self):
        """不同 key 的限流状态应该独立。"""
        self.limiter.record_attempt("key-a")
        self.limiter.record_attempt("key-a")
        self.limiter.record_attempt("key-a")
        assert self.limiter.is_limited("key-a")
        assert not self.limiter.is_limited("key-b")

    def test_window_expiration(self):
        """窗口过期后旧记录应该被清除，不再限流。"""
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        assert self.limiter.is_limited("test-key")

        # 模拟窗口过期
        with patch.object(time, "time", return_value=time.time() + 61):
            assert not self.limiter.is_limited("test-key")

    def test_partial_window_expiration(self):
        """部分记录过期后，只有窗口内的记录被计数。"""
        now = time.time()

        # 前 3 次在"窗口内"（当前时间）
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")

        # 窗口移动到 30 秒后，此时 3 次记录都在窗口内
        with patch.object(time, "time", return_value=now + 30):
            assert self.limiter.is_limited("test-key")

        # 窗口移动到 61 秒后，所有记录都过期
        with patch.object(time, "time", return_value=now + 61):
            assert not self.limiter.is_limited("test-key")

    def test_custom_parameters(self):
        """自定义参数应该生效。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=120)
        for _ in range(9):
            limiter.record_attempt("test-key")
        assert not limiter.is_limited("test-key")

        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key")

    def test_is_limited_does_not_record(self):
        """is_limited 只检查不记录，多次调用不应增加计数。"""
        self.limiter.record_attempt("test-key")
        # 多次调用 is_limited 不应增加计数
        self.limiter.is_limited("test-key")
        self.limiter.is_limited("test-key")
        self.limiter.is_limited("test-key")

        # 仍然只有 1 次记录
        count = self.limiter.record_attempt("test-key")
        assert count == 2  # 再记录一次就变成 2

    def test_reset_after_record_attempt(self):
        """记录后重置再记录，计数应从 1 开始。"""
        self.limiter.record_attempt("test-key")
        self.limiter.record_attempt("test-key")
        self.limiter.reset("test-key")
        count = self.limiter.record_attempt("test-key")
        assert count == 1