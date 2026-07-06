"""UserSessionTracker 用户会话跟踪器单元测试。

覆盖用户上线/下线追踪、心跳刷新、超时清理等核心逻辑。
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from backend.plugins.auth.session import UserSessionTracker


class TestUserSessionTracker:
    """UserSessionTracker 基础功能测试。"""

    @pytest.fixture
    def tracker(self):
        """创建带 mock config 的 UserSessionTracker。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "300"  # 5 分钟超时
        container.get.return_value = config
        return UserSessionTracker(container)

    def test_user_online(self, tracker):
        """用户上线。"""
        tracker.user_online("user_123", "Alice")
        assert tracker.is_online("user_123") is True

    def test_user_online_twice(self, tracker):
        """同一用户重复上线应刷新但不重复计数。"""
        tracker.user_online("user_1", "Alice")
        tracker.user_online("user_1", "Alice")
        assert tracker.get_online_count() == 1

    def test_user_online_multiple_users(self, tracker):
        """多个用户上线。"""
        tracker.user_online("user_1", "Alice")
        tracker.user_online("user_2", "Bob")
        tracker.user_online("user_3", "Charlie")
        assert tracker.get_online_count() == 3

    def test_user_offline(self, tracker):
        """用户下线。"""
        tracker.user_online("user_1", "Alice")
        tracker.user_offline("user_1")
        assert tracker.is_online("user_1") is False
        assert tracker.get_online_count() == 0

    def test_user_offline_not_online(self, tracker):
        """不存在的用户下线不报错。"""
        tracker.user_offline("ghost_user")
        assert tracker.is_online("ghost_user") is False

    def test_refresh_updates_last_seen(self, tracker):
        """刷新应更新 last_seen 时间。"""
        tracker.user_online("user_1", "Alice")
        old_seen = tracker._sessions["user_1"]["last_seen"]

        time.sleep(0.001)
        tracker.refresh("user_1")
        new_seen = tracker._sessions["user_1"]["last_seen"]

        assert new_seen > old_seen

    def test_refresh_nonexistent_user(self, tracker):
        """刷新不存在的用户不报错。"""
        tracker.refresh("ghost_user")

    def test_get_online_count_zero(self, tracker):
        """无在线用户时返回 0。"""
        assert tracker.get_online_count() == 0

    def test_get_online_count_after_offline(self, tracker):
        """用户下线后计数应减少。"""
        tracker.user_online("user_1", "Alice")
        tracker.user_online("user_2", "Bob")
        tracker.user_offline("user_1")
        assert tracker.get_online_count() == 1

    def test_get_online_users_empty(self, tracker):
        """无在线用户时返回空列表。"""
        assert tracker.get_online_users() == []

    def test_get_online_users_returns_user_info(self, tracker):
        """get_online_users 应返回用户详细信息。"""
        tracker.user_online("user_1", "Alice")
        users = tracker.get_online_users()
        assert len(users) == 1
        assert users[0]["user_id"] == "user_1"
        assert users[0]["username"] == "Alice"
        assert "login_at" in users[0]
        assert "last_seen" in users[0]
        assert "idle_seconds" in users[0]

    def test_get_online_users_sorted_by_login_time(self, tracker):
        """在线用户列表应按登录时间倒序。"""
        tracker.user_online("user_1", "Alice")
        time.sleep(0.001)
        tracker.user_online("user_2", "Bob")
        users = tracker.get_online_users()
        assert users[0]["user_id"] == "user_2"
        assert users[1]["user_id"] == "user_1"

    def test_is_online_returns_false_for_nonexistent(self, tracker):
        """不存在的用户应返回 False。"""
        assert tracker.is_online("ghost_user") is False

    def test_username_updated_on_reonline(self, tracker):
        """重复上线应更新用户名。"""
        tracker.user_online("user_1", "Alice")
        tracker.user_online("user_1", "AliceUpdated")
        assert tracker._sessions["user_1"]["username"] == "AliceUpdated"


class TestUserSessionTrackerTimeout:
    """UserSessionTracker 超时清理测试。"""

    @pytest.fixture
    def tracker(self):
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "1"  # 1 秒超时
        container.get.return_value = config
        return UserSessionTracker(container)

    def test_timeout_from_config(self, tracker):
        """超时时间应从 config 读取。"""
        assert tracker._timeout == 1

    def test_cleanup_stale_sessions_removes_expired(self, tracker):
        """清理应移除过期的会话。"""
        tracker.user_online("user_1", "Alice")
        # 模拟会话过期
        tracker._sessions["user_1"]["last_seen"] = time.time() - 10
        tracker._cleanup_stale_sessions()
        assert tracker.is_online("user_1") is False

    def test_cleanup_stale_sessions_keeps_active(self, tracker):
        """未过期的会话应保留。"""
        tracker.user_online("user_1", "Alice")
        tracker._cleanup_stale_sessions()
        assert tracker.is_online("user_1") is True

    def test_cleanup_stale_sessions_empty(self, tracker):
        """无过期会话时不应报错。"""
        tracker.user_online("user_1", "Alice")
        tracker._cleanup_stale_sessions()
        assert tracker.get_online_count() == 1

    def test_cleanup_stale_sessions_no_sessions(self, tracker):
        """无任何会话时不报错。"""
        tracker._cleanup_stale_sessions()  # 不应抛出异常


class TestUserSessionTrackerStats:
    """UserSessionTracker 统计功能测试。"""

    @pytest.fixture
    def tracker(self):
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "300"
        container.get.return_value = config
        return UserSessionTracker(container)

    def test_get_stats_contains_keys(self, tracker):
        """get_stats 应返回包含所有关键字段的字典。"""
        tracker.user_online("user_1", "Alice")
        stats = tracker.get_stats()
        assert "online_count" in stats
        assert "peak_online" in stats
        assert "peak_time" in stats
        assert "timeout_seconds" in stats

    def test_get_stats_online_count(self, tracker):
        """get_stats 的在线计数应正确。"""
        tracker.user_online("user_1", "Alice")
        tracker.user_online("user_2", "Bob")
        assert tracker.get_stats()["online_count"] == 2

    def test_get_stats_peak_online(self, tracker):
        """get_stats 的峰值在线应正确。"""
        tracker.user_online("user_1", "Alice")
        tracker.user_online("user_2", "Bob")
        tracker.user_offline("user_1")
        stats = tracker.get_stats()
        assert stats["peak_online"] == 2
        assert stats["online_count"] == 1

    def test_get_stats_timeout(self, tracker):
        """get_stats 应返回配置的超时时间。"""
        assert tracker.get_stats()["timeout_seconds"] == 300


class TestUserSessionTrackerConfig:
    """UserSessionTracker 配置处理测试。"""

    def test_init_with_empty_timeout(self):
        """配置文件为空时使用默认超时。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = ""
        container.get.return_value = config
        tracker = UserSessionTracker(container)
        from backend.plugins.auth.session import DEFAULT_ONLINE_TIMEOUT
        assert tracker._timeout == DEFAULT_ONLINE_TIMEOUT

    def test_init_with_invalid_timeout(self):
        """配置文件无效时使用默认超时。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "not_a_number"
        container.get.return_value = config
        tracker = UserSessionTracker(container)
        from backend.plugins.auth.session import DEFAULT_ONLINE_TIMEOUT
        assert tracker._timeout == DEFAULT_ONLINE_TIMEOUT


class TestUserSessionTrackerEdgeCases:
    """UserSessionTracker 边界情况测试。"""

    @pytest.fixture
    def tracker(self):
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "300"
        container.get.return_value = config
        return UserSessionTracker(container)

    @pytest.fixture
    def short_timeout_tracker(self):
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "1"
        container.get.return_value = config
        return UserSessionTracker(container)

    def test_user_offline_twice(self, tracker):
        """同一用户两次下线不报错。"""
        tracker.user_online("user_1", "Alice")
        tracker.user_offline("user_1")
        tracker.user_offline("user_1")  # 不应抛出异常

    def test_refresh_after_offline(self, tracker):
        """用户下线后 refresh 不应重新激活。"""
        tracker.user_online("user_1", "Alice")
        tracker.user_offline("user_1")
        tracker.refresh("user_1")
        assert tracker.is_online("user_1") is False

    def test_online_count_after_cleanup(self, short_timeout_tracker):
        """清理后在线计数应正确。"""
        short_timeout_tracker.user_online("user_1", "Alice")
        short_timeout_tracker.user_online("user_2", "Bob")
        short_timeout_tracker._sessions["user_2"]["last_seen"] = time.time() - 10
        short_timeout_tracker._cleanup_stale_sessions()
        assert short_timeout_tracker.get_online_count() == 1