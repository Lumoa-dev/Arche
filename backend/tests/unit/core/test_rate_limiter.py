"""RateLimiter 滑动窗口速率限制器 —— 单元测试。

覆盖：
- 窗口内允许最大次数
- 超过阈值被限流
- 记录尝试后计数递增
- 重置后计数器清空
- 窗口过期后自动恢复
- 多 key 隔离
"""

from __future__ import annotations

import time

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """滑动窗口速率限制器行为测试。"""

    def test_not_limited_below_max(self):
        """未超过阈值时不应限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        assert limiter.is_limited("test-key") is False

    def test_limited_when_exceeds_max(self):
        """超过阈值时应限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True

    def test_exact_limit_not_limited(self):
        """恰好达到阈值但未超出时不应限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is False  # 2 < 3

    def test_record_attempt_returns_count(self):
        """record_attempt 应返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        count1 = limiter.record_attempt("test-key")
        assert count1 == 1
        count2 = limiter.record_attempt("test-key")
        assert count2 == 2

    def test_reset_clears_counter(self):
        """重置后应不再限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True
        limiter.reset("test-key")
        assert limiter.is_limited("test-key") is False

    def test_multiple_keys_isolated(self):
        """不同 key 的计数应隔离。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        limiter.record_attempt("key-a")
        limiter.record_attempt("key-a")
        assert limiter.is_limited("key-a") is True
        assert limiter.is_limited("key-b") is False

    def test_window_expiry_auto_recovers(self):
        """窗口过期后应自动恢复（使用极短窗口模拟）。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0.1)
        limiter.record_attempt("test-key")
        limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True
        time.sleep(0.15)
        assert limiter.is_limited("test-key") is False

    def test_old_attempts_pruned_in_window(self):
        """窗口外的旧记录应在 is_limited 调用时被清理。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=0.1)
        limiter.record_attempt("test-key")
        time.sleep(0.15)
        limiter.record_attempt("test-key")
        # 第一条已过期，窗口内只有1条
        assert limiter.is_limited("test-key") is False

    def test_reset_nonexistent_key_no_error(self):
        """重置不存在的 key 不应报错。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        limiter.reset("nonexistent-key")  # 不应抛出异常

    def test_custom_config(self):
        """自定义 max_attempts 和 window_seconds 应生效。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=5)
        for _ in range(10):
            limiter.record_attempt("test-key")
        assert limiter.is_limited("test-key") is True
