"""RateLimiter 滑动窗口速率限制器测试。

测试原则：
- 测试滑动窗口计数、窗口清理、重置行为
- 不依赖真实时间，使用 time.time 打桩（可控）
- 验证边界条件：刚好达到阈值、未达到阈值、窗口外过期
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """测试 RateLimiter 核心行为。"""

    def test_init_defaults(self):
        """默认参数正确。"""
        limiter = RateLimiter()
        assert limiter.max_attempts == 5
        assert limiter.window_seconds == 60

    def test_init_custom(self):
        """自定义参数正确。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=30)
        assert limiter.max_attempts == 3
        assert limiter.window_seconds == 30

    def test_is_limited_under_threshold(self):
        """未达到阈值时 is_limited 返回 False。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.is_limited("test-key") is False

    def test_is_limited_at_threshold(self):
        """达到阈值时 is_limited 返回 True。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_record_attempt_returns_count(self):
        """record_attempt 返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        assert limiter.record_attempt("test-key") == 1
        assert limiter.record_attempt("test-key") == 2
        assert limiter.record_attempt("test-key") == 3

    @patch("backend.core.rate_limiter.time")
    def test_window_expiry_clears_old_entries(self, mock_time):
        """窗口外的旧记录应被清理，不再计入限制。"""
        mock_time.time.return_value = 1000.0
        limiter = RateLimiter(max_attempts=2, window_seconds=60)

        # 在时间 1000 时记录 2 次（达到阈值）
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

        # 前进到 1061（已超窗口），旧记录应被清理
        mock_time.time.return_value = 1061.0
        assert limiter.is_limited("test-key") is False

    @patch("backend.core.rate_limiter.time")
    def test_window_boundary_preserves_in_window_entries(self, mock_time):
        """窗口内的记录应保留。"""
        mock_time.time.return_value = 1000.0
        limiter = RateLimiter(max_attempts=3, window_seconds=60)

        # 时间 1000 时记录 2 次
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")

        # 时间 1059（仍在窗口内）
        mock_time.time.return_value = 1059.0
        assert limiter.is_limited("test-key") is False
        limiter.record_attempt("test-key")
        # 现在 3 次，应该受限
        assert limiter.is_limited("test-key") is True

    def test_reset_clears_key(self):
        """reset 应清除指定 key 的计数。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

        limiter.reset("test-key")
        assert limiter.is_limited("test-key") is False

    def test_reset_nonexistent_key(self):
        """reset 不存在的 key 不应报错。"""
        limiter = RateLimiter()
        limiter.reset("nonexistent-key")  # 不应抛出异常

    def test_multiple_keys_independent(self):
        """不同 key 的计数应互相独立。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")

        # key-a 受限
        assert limiter.is_limited("key-a") is True
        # key-b 不受影响
        assert limiter.is_limited("key-b") is False

    @patch("backend.core.rate_limiter.time")
    def test_partial_window_expiry(self, mock_time):
        """部分记录过期后，只有窗口内的记录被保留。"""
        mock_time.time.return_value = 1000.0
        limiter = RateLimiter(max_attempts=3, window_seconds=60)

        limiter.record_attempt("test-key")  # t=1000
        mock_time.time.return_value = 1020.0
        limiter.record_attempt("test-key")  # t=1020
        mock_time.time.return_value = 1070.0
        limiter.record_attempt("test-key")  # t=1070 (t=1000 的记录已过期)

        # 此时窗口内只有 t=1020 和 t=1070 两条记录
        assert limiter.is_limited("test-key") is False  # 2 < 3
        limiter.record_attempt("test-key")  # t=1070
        assert limiter.is_limited("test-key") is True  # 3 >= 3