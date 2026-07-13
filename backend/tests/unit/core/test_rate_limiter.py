"""RateLimiter 滑动窗口速率限制器测试。

测试策略：
- 使用 time.time() mock 控制时间流逝，使测试确定且快速
- 覆盖：阈值边界、窗口过期、重置、并发安全
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """RateLimiter 核心功能测试。"""

    def test_init_default_params(self):
        """默认参数正确。"""
        limiter = RateLimiter()
        assert limiter.max_attempts == 5
        assert limiter.window_seconds == 60
        assert limiter._attempts == {}

    def test_init_custom_params(self):
        """自定义参数正确。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=30)
        assert limiter.max_attempts == 10
        assert limiter.window_seconds == 30

    def test_is_limited_under_threshold(self):
        """未达到阈值时返回 False。"""
        limiter = RateLimiter(max_attempts=3)
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is False

    def test_is_limited_at_threshold(self):
        """刚好达到阈值时返回 True。"""
        limiter = RateLimiter(max_attempts=3)
        for _ in range(3):
            limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

    def test_is_limited_above_threshold(self):
        """超过阈值时返回 True。"""
        limiter = RateLimiter(max_attempts=3)
        for _ in range(5):
            limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

    def test_record_attempt_returns_count(self):
        """record_attempt 返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=5)
        assert limiter.record_attempt("key1") == 1
        assert limiter.record_attempt("key1") == 2
        assert limiter.record_attempt("key1") == 3

    def test_isolation_between_keys(self):
        """不同 key 的计数互不影响。"""
        limiter = RateLimiter(max_attempts=2)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True
        assert limiter.is_limited("key2") is False

    def test_reset_clears_key(self):
        """reset 清除指定 key 的计数。"""
        limiter = RateLimiter(max_attempts=2)
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True
        limiter.reset("key1")
        assert limiter.is_limited("key1") is False

    def test_reset_nonexistent_key(self):
        """reset 不存在的 key 不报错。"""
        limiter = RateLimiter()
        limiter.reset("nonexistent")  # 不应抛出异常

    @patch("time.time")
    def test_window_expiration(self, mock_time):
        """窗口过期后旧记录被清除，限流自动解除。"""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(max_attempts=2, window_seconds=60)

        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True

        # 时间前进到窗口外
        mock_time.return_value = 1100.0  # 100 秒后 > 60 秒窗口
        assert limiter.is_limited("key1") is False

    @patch("time.time")
    def test_partial_window_expiration(self, mock_time):
        """部分记录过期后，只有窗口内的记录被计数。"""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(max_attempts=3, window_seconds=30)

        limiter.record_attempt("key1")  # t=1000
        mock_time.return_value = 1020.0
        limiter.record_attempt("key1")  # t=1020
        # 窗口 [990, 1020]，t=1000 和 t=1020 都在窗口内
        assert limiter.is_limited("key1") is False  # 2 < 3

        mock_time.return_value = 1035.0  # 窗口 [1005, 1035]
        limiter.record_attempt("key1")  # t=1035
        # t=1000 已过期，t=1020 和 t=1035 在窗口内
        assert limiter.is_limited("key1") is False  # 2 < 3

        mock_time.return_value = 1050.0  # 窗口 [1020, 1050]
        # t=1020 刚好在边界上（> 1020 为 False，因为 > 是严格大于）
        # 所以只有 t=1035 在窗口内，共 1 个
        assert limiter.is_limited("key1") is False  # 1 < 3

    @patch("time.time")
    def test_multiple_keys_independent_windows(self, mock_time):
        """多个 key 有独立的滑动窗口。"""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(max_attempts=2, window_seconds=60)

        limiter.record_attempt("user-a")
        limiter.record_attempt("user-a")
        assert limiter.is_limited("user-a") is True

        limiter.record_attempt("user-b")
        # user-b 只有 1 次记录，未达阈值
        assert limiter.is_limited("user-b") is False

        # user-a 窗口过期后解除限流
        mock_time.return_value = 1070.0  # 窗口 [1010, 1070]
        # user-a 的 t=1000 记录已过期，user-a 解除限流
        assert limiter.is_limited("user-a") is False
        # user-b 的 t=1000 记录也已过期，所以 user-b 也解除限流
        assert limiter.is_limited("user-b") is False

        # 重新记录 user-b
        limiter.record_attempt("user-b")  # t=1070
        assert limiter.is_limited("user-b") is False  # 1 < 2
        limiter.record_attempt("user-b")  # t=1070
        assert limiter.is_limited("user-b") is True  # 2 >= 2

    @patch("time.time")
    def test_is_limited_also_cleans_old_records(self, mock_time):
        """is_limited 调用也会触发旧记录清理。"""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(max_attempts=2, window_seconds=30)

        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        assert len(limiter._attempts["key1"]) == 2

        # 时间前进到窗口外
        mock_time.return_value = 1100.0
        limiter.is_limited("key1")  # 触发清理
        assert len(limiter._attempts["key1"]) == 0

    @patch("time.time")
    def test_threshold_boundary_behavior(self, mock_time):
        """阈值边界行为：刚好在阈值时被限流，少一次则通过。"""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(max_attempts=3, window_seconds=30)

        assert limiter.is_limited("key1") is False
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is False
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is False
        limiter.record_attempt("key1")
        assert limiter.is_limited("key1") is True  # 第 3 次刚好达到阈值

    def test_reset_missing_key_no_error(self):
        """reset 不存在的 key 不引发 KeyError。"""
        limiter = RateLimiter()
        limiter.reset("non-existent")  # 不抛异常