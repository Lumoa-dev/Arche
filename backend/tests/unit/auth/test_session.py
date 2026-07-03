"""UserSessionTracker 单元测试 —— 在线用户追踪器。

测试原则：
- 使用 MagicMock 容器隔离外部依赖
- 每个测试独立，不依赖执行顺序
- 不依赖真实定时器，手动触发清理逻辑
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, PropertyMock

import pytest

from backend.plugins.auth.session import DEFAULT_ONLINE_TIMEOUT, UserSessionTracker


@pytest.fixture
def tracker():
    """创建隔离的 UserSessionTracker 实例。"""
    container = MagicMock()
    config = MagicMock()
    config.get.return_value = str(DEFAULT_ONLINE_TIMEOUT)
    container.get.return_value = config
    return UserSessionTracker(container)


class TestUserOnline:
    """用户上线行为测试。"""

    def test_online_adds_session(self, tracker):
        """上线增加会话记录。"""
        tracker.user_online("user-1", "alice")
        assert tracker.is_online("user-1") is True
        assert tracker.get_online_count() == 1

    def test_online_twice_refreshes(self, tracker):
        """同一用户重复上线仅刷新，不重复计数。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-1", "alice")
        assert tracker.get_online_count() == 1

    def test_online_multiple_users(self, tracker):
        """多个用户同时在线。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        assert tracker.get_online_count() == 2

    def test_online_stores_username(self, tracker):
        """上线记录保存用户名。"""
        tracker.user_online("user-1", "alice")
        users = tracker.get_online_users()
        assert users[0]["username"] == "alice"


class TestUserOffline:
    """用户下线行为测试。"""

    def test_offline_removes_session(self, tracker):
        """下线移除会话记录。"""
        tracker.user_online("user-1", "alice")
        tracker.user_offline("user-1")
        assert tracker.is_online("user-1") is False
        assert tracker.get_online_count() == 0

    def test_offline_nonexistent_user(self, tracker):
        """下线不存在的用户不报错。"""
        tracker.user_offline("nonexistent")
        assert tracker.get_online_count() == 0

    def test_offline_decrements_count(self, tracker):
        """下线后在线计数递减。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        tracker.user_offline("user-1")
        assert tracker.get_online_count() == 1


class TestRefresh:
    """会话刷新行为测试。"""

    def test_refresh_updates_last_seen(self, tracker):
        """刷新更新最后活动时间。"""
        tracker.user_online("user-1", "alice")
        old_last_seen = tracker._sessions["user-1"]["last_seen"]

        time.sleep(0.001)  # 确保时间差
        tracker.refresh("user-1")
        new_last_seen = tracker._sessions["user-1"]["last_seen"]

        assert new_last_seen > old_last_seen

    def test_refresh_nonexistent_user(self, tracker):
        """刷新不存在的用户不报错。"""
        tracker.refresh("nonexistent")
        # 不抛异常即可


class TestGetOnlineUsers:
    """在线用户列表查询测试。"""

    def test_returns_empty_list_initially(self, tracker):
        """初始状态返回空列表。"""
        assert tracker.get_online_users() == []

    def test_returns_sorted_by_login_time(self, tracker):
        """返回按登录时间倒序的列表。"""
        tracker.user_online("user-1", "alice")
        time.sleep(0.001)
        tracker.user_online("user-2", "bob")
        users = tracker.get_online_users()
        assert users[0]["user_id"] == "user-2"  # 后登录的在前
        assert users[1]["user_id"] == "user-1"

    def test_idle_seconds_increases(self, tracker):
        """idle_seconds 字段正确反映空闲时间。"""
        tracker.user_online("user-1", "alice")
        time.sleep(0.01)
        users = tracker.get_online_users()
        assert users[0]["idle_seconds"] >= 0


class TestGetStats:
    """统计查询测试。"""

    def test_online_count_in_stats(self, tracker):
        """get_stats 返回在线人数。"""
        tracker.user_online("user-1", "alice")
        stats = tracker.get_stats()
        assert stats["online_count"] == 1

    def test_peak_online_tracking(self, tracker):
        """峰值在线人数正确记录。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        stats = tracker.get_stats()
        assert stats["peak_online"] == 2

        tracker.user_offline("user-1")
        stats = tracker.get_stats()
        assert stats["peak_online"] == 2  # 峰值不变

    def test_timeout_seconds(self, tracker):
        """get_stats 返回超时阈值。"""
        stats = tracker.get_stats()
        assert stats["timeout_seconds"] == DEFAULT_ONLINE_TIMEOUT


class TestCleanup:
    """超时会话清理测试。"""

    def test_cleanup_stale_sessions(self, tracker):
        """超时会话被清理。"""
        tracker.user_online("user-1", "alice")
        # 手动设置 last_seen 为过期时间
        tracker._sessions["user-1"]["last_seen"] = time.time() - DEFAULT_ONLINE_TIMEOUT - 10
        tracker._cleanup_stale_sessions()
        assert tracker.is_online("user-1") is False

    def test_cleanup_preserves_active_sessions(self, tracker):
        """活跃会话不被清理。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        # 只让 user-1 过期
        tracker._sessions["user-1"]["last_seen"] = time.time() - DEFAULT_ONLINE_TIMEOUT - 10
        tracker._cleanup_stale_sessions()
        assert tracker.is_online("user-1") is False
        assert tracker.is_online("user-2") is True

    def test_cleanup_empty_tracker(self, tracker):
        """空追踪器执行清理不报错。"""
        tracker._cleanup_stale_sessions()
        assert tracker.get_online_count() == 0

    def test_cleanup_updates_count(self, tracker):
        """清理后在线计数正确。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        tracker._sessions["user-1"]["last_seen"] = time.time() - DEFAULT_ONLINE_TIMEOUT - 10
        tracker._cleanup_stale_sessions()
        assert tracker.get_online_count() == 1


class TestContainerConfig:
    """容器配置传递测试。"""

    def test_custom_timeout_from_config(self):
        """从容器配置读取自定义超时时间。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "600"
        container.get.return_value = config
        tracker = UserSessionTracker(container)
        assert tracker._timeout == 600

    def test_invalid_timeout_falls_back(self):
        """无效的超时配置回退到默认值。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "not_a_number"
        container.get.return_value = config
        tracker = UserSessionTracker(container)
        assert tracker._timeout == DEFAULT_ONLINE_TIMEOUT

    def test_empty_timeout_falls_back(self):
        """空字符串超时配置回退到默认值。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = ""
        container.get.return_value = config
        tracker = UserSessionTracker(container)
        assert tracker._timeout == DEFAULT_ONLINE_TIMEOUT


class TestLifecycle:
    """生命周期管理测试。"""

    def test_close_clears_sessions(self, tracker):
        """close 清空所有会话。"""
        tracker.user_online("user-1", "alice")
        tracker.close()
        assert tracker.get_online_count() == 0

    @pytest.mark.asyncio
    async def test_start_cleanup_creates_scheduler(self, tracker):
        """start_cleanup 创建调度器。"""
        assert tracker._scheduler is None
        tracker.start_cleanup()
        assert tracker._scheduler is not None
        tracker.stop_cleanup()  # 清理

    @pytest.mark.asyncio
    async def test_start_cleanup_idempotent(self, tracker):
        """多次 start_cleanup 不重复创建调度器。"""
        tracker.start_cleanup()
        s1 = tracker._scheduler
        tracker.start_cleanup()
        assert tracker._scheduler is s1  # 同一实例
        tracker.stop_cleanup()  # 清理