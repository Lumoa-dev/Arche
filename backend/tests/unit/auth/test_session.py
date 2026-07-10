"""用户在线会话追踪器测试 —— UserSessionTracker。"""

import time
from unittest.mock import MagicMock, patch

import pytest

from backend.plugins.auth.session import UserSessionTracker


@pytest.fixture
def tracker():
    """创建 UserSessionTracker 实例。"""
    container = MagicMock()
    config = MagicMock()
    config.get.return_value = "300"  # 5 分钟超时
    container.get.return_value = config
    return UserSessionTracker(container)


class TestUserSessionTracker:
    """测试在线用户追踪器核心功能。"""

    def test_init_default_timeout(self, tracker):
        """初始超时时间从配置读取。"""
        assert tracker._timeout == 300

    def test_init_fallback_timeout(self):
        """配置无效时使用默认超时。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = ""  # 空字符串
        container.get.return_value = config
        t = UserSessionTracker(container)
        assert t._timeout == 900  # DEFAULT_ONLINE_TIMEOUT

    def test_init_invalid_timeout(self):
        """配置为非数字时使用默认超时。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "not-a-number"
        container.get.return_value = config
        t = UserSessionTracker(container)
        assert t._timeout == 900

    def test_user_online_new_user(self, tracker):
        """新用户上线后在线人数增加。"""
        tracker.user_online("user1", "Alice")
        assert tracker.is_online("user1") is True
        assert tracker.get_online_count() == 1

    def test_user_online_multiple_users(self, tracker):
        """多个用户上线后在线人数正确。"""
        tracker.user_online("user1", "Alice")
        tracker.user_online("user2", "Bob")
        tracker.user_online("user3", "Charlie")
        assert tracker.get_online_count() == 3

    def test_user_online_duplicate(self, tracker):
        """同一用户重复上线不增加计数。"""
        tracker.user_online("user1", "Alice")
        tracker.user_online("user1", "Alice")
        assert tracker.get_online_count() == 1

    def test_user_offline(self, tracker):
        """用户下线后在线人数减少。"""
        tracker.user_online("user1", "Alice")
        tracker.user_online("user2", "Bob")
        tracker.user_offline("user1")
        assert tracker.is_online("user1") is False
        assert tracker.get_online_count() == 1

    def test_user_offline_nonexistent(self, tracker):
        """不存在的用户下线不报错。"""
        tracker.user_offline("nonexistent")  # 不应抛出异常
        assert tracker.get_online_count() == 0

    def test_offline_updates_peak(self, tracker):
        """上下线操作更新峰值统计。"""
        tracker.user_online("user1", "Alice")
        tracker.user_online("user2", "Bob")
        tracker.user_online("user3", "Charlie")
        tracker.user_offline("user1")
        assert tracker.get_stats()["peak_online"] == 3

    def test_refresh_updates_last_seen(self, tracker):
        """刷新操作更新最后活动时间。"""
        tracker.user_online("user1", "Alice")
        old_last_seen = tracker._sessions["user1"]["last_seen"]
        time.sleep(0.001)
        tracker.refresh("user1")
        assert tracker._sessions["user1"]["last_seen"] > old_last_seen

    def test_refresh_nonexistent_user(self, tracker):
        """刷新不存在的用户不报错。"""
        tracker.refresh("nonexistent")  # 不应抛出异常

    def test_get_online_users(self, tracker):
        """获取在线用户列表返回正确信息。"""
        tracker.user_online("user1", "Alice")
        tracker.user_online("user2", "Bob")

        users = tracker.get_online_users()
        assert len(users) == 2
        # 按登录时间倒序
        assert users[0]["username"] == "Bob"
        assert users[1]["username"] == "Alice"
        assert "idle_seconds" in users[0]
        assert "login_at" in users[0]
        assert "last_seen" in users[0]

    def test_get_stats(self, tracker):
        """统计信息包含所有字段。"""
        tracker.user_online("user1", "Alice")
        stats = tracker.get_stats()
        assert "online_count" in stats
        assert "peak_online" in stats
        assert "peak_time" in stats
        assert "timeout_seconds" in stats
        assert stats["online_count"] == 1

    def test_cleanup_stale_sessions(self, tracker):
        """超时会话被清理。"""
        tracker._timeout = 0  # 立即超时
        tracker.user_online("user1", "Alice")
        tracker.user_online("user2", "Bob")
        tracker._cleanup_stale_sessions()
        assert tracker.get_online_count() == 0

    @patch("time.time")
    def test_cleanup_partial_stale(self, mock_time, tracker):
        """只清理超时会话，保留未超时会话。"""
        mock_time.return_value = 1000.0
        tracker._timeout = 100
        tracker.user_online("user1", "Alice")  # login_at=1000
        mock_time.return_value = 1050.0
        tracker.user_online("user2", "Bob")  # login_at=1050

        mock_time.return_value = 1150.0  # user1 超时 (1000+100=1100), user2 未超时
        tracker._cleanup_stale_sessions()
        assert tracker.is_online("user1") is False
        assert tracker.is_online("user2") is True
        assert tracker.get_online_count() == 1

    @pytest.mark.asyncio
    async def test_start_cleanup_sets_scheduler(self, tracker):
        """启动调度器后 _scheduler 被设置。"""
        assert tracker._scheduler is None
        tracker.start_cleanup()
        assert tracker._scheduler is not None
        tracker.stop_cleanup()
        assert tracker._scheduler is None

    def test_double_start_cleanup(self, tracker):
        """重复启动不创建新调度器。"""
        # 先手动设置 scheduler 来模拟已启动状态
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        tracker._scheduler = AsyncIOScheduler()
        scheduler1 = tracker._scheduler
        tracker.start_cleanup()
        assert tracker._scheduler is scheduler1  # 同一实例

    def test_close(self, tracker):
        """关闭后清除所有会话。"""
        tracker.user_online("user1", "Alice")
        tracker.user_online("user2", "Bob")
        tracker.close()
        assert tracker.get_online_count() == 0
        assert tracker._scheduler is None

    def test_peak_online_tracking(self, tracker):
        """峰值在线人数正确跟踪。"""
        assert tracker.get_stats()["peak_online"] == 0
        tracker.user_online("user1", "Alice")
        assert tracker.get_stats()["peak_online"] == 1
        tracker.user_online("user2", "Bob")
        assert tracker.get_stats()["peak_online"] == 2
        tracker.user_offline("user1")
        # 峰值不变
        assert tracker.get_stats()["peak_online"] == 2

    def test_online_user_idle_seconds(self, tracker):
        """在线用户列表包含空闲秒数。"""
        tracker.user_online("user1", "Alice")
        users = tracker.get_online_users()
        assert users[0]["idle_seconds"] >= 0