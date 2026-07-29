"""用户在线会话追踪器 UserSessionTracker 测试。

测试原则：
- 覆盖上线/下线/刷新/查询/统计/超时清理
- 用 time.time 打桩控制时间流
- 不依赖 APScheduler 真实运行
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from backend.plugins.auth.session import UserSessionTracker


@pytest.fixture
def tracker():
    """创建带 mock container 的 UserSessionTracker。"""
    container = MagicMock()
    config = MagicMock()
    config.get.return_value = "900"
    container.get.return_value = config
    return UserSessionTracker(container)


class TestUserSessionTracker:
    """测试 UserSessionTracker 核心行为。"""

    def test_init_default_config(self, tracker):
        """初始化正确读取超时配置。"""
        assert tracker._timeout == 900
        assert tracker.get_online_count() == 0

    def test_init_with_invalid_config(self):
        """配置无效时使用默认超时。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "not-a-number"
        container.get.return_value = config
        t = UserSessionTracker(container)
        assert t._timeout == 900

    def test_init_with_empty_config(self):
        """配置为空字符串时使用默认超时。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = ""
        container.get.return_value = config
        t = UserSessionTracker(container)
        assert t._timeout == 900

    def test_user_online_new_user(self, tracker):
        """新用户上线后应出现在在线列表中。"""
        tracker.user_online("user-1", "Alice")
        assert tracker.get_online_count() == 1
        assert tracker.is_online("user-1") is True

    def test_user_online_multiple_users(self, tracker):
        """多个用户上线应正确计数。"""
        tracker.user_online("user-1", "Alice")
        tracker.user_online("user-2", "Bob")
        tracker.user_online("user-3", "Charlie")
        assert tracker.get_online_count() == 3

    def test_user_online_duplicate(self, tracker):
        """同一用户重复上线不应重复计数。"""
        tracker.user_online("user-1", "Alice")
        tracker.user_online("user-1", "Alice")
        assert tracker.get_online_count() == 1

    def test_user_offline_removes_user(self, tracker):
        """用户下线后应从在线列表中移除。"""
        tracker.user_online("user-1", "Alice")
        tracker.user_online("user-2", "Bob")
        tracker.user_offline("user-1")
        assert tracker.get_online_count() == 1
        assert tracker.is_online("user-1") is False

    def test_user_offline_nonexistent(self, tracker):
        """下线不存在的用户不应报错。"""
        tracker.user_offline("nonexistent")  # 不应抛出异常

    def test_refresh_updates_last_seen(self, tracker):
        """refresh 应更新用户的 last_seen。"""
        tracker.user_online("user-1", "Alice")
        old_last_seen = tracker._sessions["user-1"]["last_seen"]

        # wait a bit
        with patch.object(time, "time", return_value=old_last_seen + 10):
            tracker.refresh("user-1")
            assert tracker._sessions["user-1"]["last_seen"] == old_last_seen + 10

    def test_refresh_nonexistent_user(self, tracker):
        """refresh 不存在的用户不应报错。"""
        tracker.refresh("nonexistent")  # 不应抛出异常

    def test_get_online_users_list(self, tracker):
        """get_online_users 返回按登录时间倒序的列表。"""
        with patch.object(time, "time", return_value=1000.0):
            tracker.user_online("user-1", "Alice")
        with patch.object(time, "time", return_value=1005.0):
            tracker.user_online("user-2", "Bob")

        users = tracker.get_online_users()
        assert len(users) == 2
        # 按 login_at 倒序：Bob 先，Alice 后
        assert users[0]["username"] == "Bob"
        assert users[1]["username"] == "Alice"

    def test_get_online_users_idle_seconds(self, tracker):
        """get_online_users 应正确计算空闲秒数。"""
        with patch.object(time, "time", return_value=1000.0):
            tracker.user_online("user-1", "Alice")

        with patch.object(time, "time", return_value=1010.0):
            users = tracker.get_online_users()
            assert users[0]["idle_seconds"] == 10

    def test_get_stats(self, tracker):
        """get_stats 返回正确统计信息。"""
        with patch.object(time, "time", return_value=1000.0):
            tracker.user_online("user-1", "Alice")
            tracker.user_online("user-2", "Bob")

        stats = tracker.get_stats()
        assert stats["online_count"] == 2
        assert stats["peak_online"] == 2
        assert stats["peak_time"] == 1000.0
        assert stats["timeout_seconds"] == 900

    def test_peak_online_tracking(self, tracker):
        """峰值在线人数应正确记录。"""
        tracker.user_online("user-1", "Alice")
        tracker.user_online("user-2", "Bob")
        assert tracker._peak_online == 2

        tracker.user_offline("user-1")
        tracker.user_online("user-3", "Charlie")
        # 峰值仍为 2
        assert tracker._peak_online == 2

    def test_cleanup_stale_sessions(self, tracker):
        """超时会话应被清理。"""
        with patch.object(time, "time", return_value=1000.0):
            tracker.user_online("user-1", "Alice")
            tracker.user_online("user-2", "Bob")

        # 将 user-1 的 last_seen 设为很旧的时间（超出超时 900s）
        # user-2 的 last_seen 保持在 1000.0（仍在窗口内）
        tracker._sessions["user-1"]["last_seen"] = 100.0

        with patch.object(time, "time", return_value=1500.0):
            tracker._cleanup_stale_sessions()
            assert tracker.is_online("user-1") is False  # 100.0→1500.0, 间隔 1400s > 900s
            assert tracker.is_online("user-2") is True  # 1000.0→1500.0, 间隔 500s < 900s
            assert tracker.get_online_count() == 1

    def test_cleanup_no_stale_sessions(self, tracker):
        """无超时会话时清理不应移除任何用户。"""
        tracker.user_online("user-1", "Alice")
        tracker._cleanup_stale_sessions()
        assert tracker.is_online("user-1") is True

    @pytest.mark.asyncio
    async def test_start_stop_cleanup(self, tracker):
        """start_cleanup 和 stop_cleanup 应正确管理调度器。"""
        tracker.start_cleanup()
        assert tracker._scheduler is not None
        if hasattr(tracker._scheduler, "running"):
            assert tracker._scheduler.running is True

        tracker.stop_cleanup()
        assert tracker._scheduler is None

    @pytest.mark.asyncio
    async def test_double_start_cleanup(self, tracker):
        """重复 start_cleanup 不应创建多个调度器。"""
        tracker.start_cleanup()
        s1 = tracker._scheduler
        tracker.start_cleanup()
        assert tracker._scheduler is s1  # 同一实例

    def test_close_clears_sessions(self, tracker):
        """close 应清除所有会话并停止调度器。"""
        tracker.user_online("user-1", "Alice")
        tracker.user_online("user-2", "Bob")
        tracker.close()
        assert tracker.get_online_count() == 0