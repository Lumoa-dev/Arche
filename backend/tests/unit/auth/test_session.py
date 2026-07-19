"""UserSessionTracker 在线会话追踪器测试。"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from backend.plugins.auth.session import DEFAULT_ONLINE_TIMEOUT, UserSessionTracker


@pytest.fixture
def tracker():
    """创建一个带 mock config 的 UserSessionTracker。"""
    container = MagicMock()
    config = MagicMock()
    config.get.return_value = "900"
    container.get.return_value = config
    return UserSessionTracker(container)


class TestUserSessionTracker:
    """测试用户在线会话追踪器。"""

    def test_user_online_new_user(self, tracker):
        """新用户上线应正确记录。"""
        tracker.user_online("user-1", "alice")
        assert tracker.is_online("user-1") is True
        assert tracker.get_online_count() == 1

    def test_user_online_duplicate(self, tracker):
        """重复上线不应增加计数。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-1", "alice")
        assert tracker.get_online_count() == 1

    def test_user_offline(self, tracker):
        """用户下线应移除记录。"""
        tracker.user_online("user-1", "alice")
        tracker.user_offline("user-1")
        assert tracker.is_online("user-1") is False
        assert tracker.get_online_count() == 0

    def test_user_offline_nonexistent(self, tracker):
        """下线不存在的用户不应报错。"""
        tracker.user_offline("nonexistent")  # 不应抛出异常

    def test_refresh_updates_last_seen(self, tracker):
        """刷新操作应更新 last_seen 时间。"""
        tracker.user_online("user-1", "alice")
        old_seen = tracker._sessions["user-1"]["last_seen"]
        time.sleep(0.01)
        tracker.refresh("user-1")
        assert tracker._sessions["user-1"]["last_seen"] > old_seen

    def test_refresh_offline_user(self, tracker):
        """刷新离线用户不应报错。"""
        tracker.refresh("nonexistent")  # 不应抛出异常

    def test_get_online_users_list(self, tracker):
        """获取在线用户列表应返回正确信息。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        users = tracker.get_online_users()
        assert len(users) == 2
        usernames = {u["username"] for u in users}
        assert usernames == {"alice", "bob"}

    def test_get_online_users_order(self, tracker):
        """在线用户列表应按登录时间倒序。"""
        tracker.user_online("user-1", "alice")
        time.sleep(0.01)
        tracker.user_online("user-2", "bob")
        users = tracker.get_online_users()
        assert users[0]["username"] == "bob"  # 后登录的在前面
        assert users[1]["username"] == "alice"

    def test_get_online_users_idle_seconds(self, tracker):
        """在线用户列表应包含 idle_seconds 字段。"""
        tracker.user_online("user-1", "alice")
        users = tracker.get_online_users()
        assert "idle_seconds" in users[0]
        assert users[0]["idle_seconds"] >= 0

    def test_get_stats(self, tracker):
        """获取统计信息应包含所有字段。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        stats = tracker.get_stats()
        assert stats["online_count"] == 2
        assert stats["peak_online"] >= 2
        assert stats["peak_time"] > 0
        assert stats["timeout_seconds"] == 900

    def test_peak_online_tracking(self, tracker):
        """峰值在线人数应正确追踪。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        tracker.user_online("user-3", "charlie")
        assert tracker._peak_online == 3
        tracker.user_offline("user-1")
        tracker.user_offline("user-2")
        # 峰值不会下降
        assert tracker.get_stats()["peak_online"] == 3

    def test_cleanup_stale_sessions(self, tracker):
        """清理超时会话应正确移除。"""
        tracker.user_online("user-1", "alice")
        # 模拟超时
        tracker._timeout = 0  # 立即过期
        time.sleep(0.01)
        tracker._cleanup_stale_sessions()
        assert tracker.is_online("user-1") is False

    def test_cleanup_only_stale_sessions(self, tracker):
        """清理超时会话不应影响未超时的。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        # 让 user-1 超时
        tracker._sessions["user-1"]["last_seen"] = time.time() - 1000
        tracker._cleanup_stale_sessions()
        assert tracker.is_online("user-1") is False
        assert tracker.is_online("user-2") is True

    def test_close_clears_all(self, tracker):
        """close 应清空所有会话。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        tracker.close()
        assert tracker.get_online_count() == 0
        assert tracker._scheduler is None

    @pytest.mark.asyncio
    async def test_start_cleanup_twice(self, tracker):
        """多次启动清理任务不应重复创建调度器。"""
        tracker.start_cleanup()
        scheduler = tracker._scheduler
        tracker.start_cleanup()
        assert tracker._scheduler is scheduler

    def test_stop_cleanup_without_start(self, tracker):
        """未启动时调用 stop_cleanup 不应报错。"""
        tracker.stop_cleanup()  # 不应抛出异常

    def test_default_timeout_parsing(self, tracker):
        """默认超时时间解析正确。"""
        assert tracker._timeout == DEFAULT_ONLINE_TIMEOUT

    def test_invalid_timeout_fallback(self):
        """无效的超时配置应回退到默认值。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "not-a-number"
        container.get.return_value = config
        t = UserSessionTracker(container)
        assert t._timeout == DEFAULT_ONLINE_TIMEOUT