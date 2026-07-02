"""RateLimiter 核心速率限制器测试。

测试原则：
- 纯内存实现，无需数据库或外部依赖
- 每个测试独立，不依赖执行顺序
- time.time() 通过 freezegun 控制（但 RateLimiter 使用真实 time，因此用 sleep 替代）
"""

from __future__ import annotations

import time
from unittest.mock import ANY, patch

import pytest

from backend.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """RateLimiter 行为测试。"""

    def test_not_limited_within_max_attempts(self):
        """在 max_attempts 范围内不应被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        key = "test-user-127.0.0.1"

        assert limiter.is_limited(key) is False
        limiter.record_attempt(key)
        assert limiter.is_limited(key) is False
        limiter.record_attempt(key)
        assert limiter.is_limited(key) is False

    def test_limited_when_exceeding_max_attempts(self):
        """超过 max_attempts 后应被限流。"""
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        key = "brute-force-user"

        limiter.record_attempt(key)
        limiter.record_attempt(key)
        limiter.record_attempt(key)
        # 第 4 次应在窗口内被限流
        assert limiter.is_limited(key) is True

    def test_window_expiry_resets_limit(self):
        """窗口过期后限流应自动重置。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=1)
        key = "ephemeral-user"

        limiter.record_attempt(key)
        limiter.record_attempt(key)
        assert limiter.is_limited(key) is True

        # 等待窗口过期
        time.sleep(1.1)
        assert limiter.is_limited(key) is False

    def test_different_keys_independent(self):
        """不同 key 的限流状态应相互独立。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)

        limiter.record_attempt("user-a")
        limiter.record_attempt("user-a")

        # user-a 已用完额度
        assert limiter.is_limited("user-a") is True
        # user-b 不受影响
        assert limiter.is_limited("user-b") is False

    def test_reset_clears_attempts(self):
        """reset() 应清除指定 key 的所有记录。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=60)
        key = "resettable-user"

        limiter.record_attempt(key)
        limiter.record_attempt(key)
        assert limiter.is_limited(key) is True

        limiter.reset(key)
        assert limiter.is_limited(key) is False

    def test_reset_nonexistent_key_no_error(self):
        """reset() 不存在的 key 不应抛出异常。"""
        limiter = RateLimiter(max_attempts=5, window_seconds=60)
        limiter.reset("never-recorded")  # 不应抛异常

    def test_record_attempt_returns_count(self):
        """record_attempt() 应返回当前窗口内的尝试次数。"""
        limiter = RateLimiter(max_attempts=10, window_seconds=60)
        key = "counter-check"

        assert limiter.record_attempt(key) == 1
        assert limiter.record_attempt(key) == 2
        assert limiter.record_attempt(key) == 3

    def test_old_attempts_expire(self):
        """窗口外的旧记录不应影响限流判断。"""
        limiter = RateLimiter(max_attempts=2, window_seconds=1)
        key = "old-attempts"

        limiter.record_attempt(key)
        time.sleep(1.1)
        limiter.record_attempt(key)  # 旧记录已过期，这是第 1 条有效记录
        assert limiter.is_limited(key) is False

        limiter.record_attempt(key)  # 第 2 条
        assert limiter.is_limited(key) is True