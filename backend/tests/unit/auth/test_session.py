"""UserSessionTracker 在线会话追踪器单元测试。

覆盖：上线/下线/刷新/超时清理/统计/生命周期管理。
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from backend.plugins.auth.session import DEFAULT_ONLINE_TIMEOUT, UserSessionTracker


@pytest.fixture
def session_tracker():
    """创建轻量 UserSessionTracker 实例。"""
    container = MagicMock()
    config = MagicMock()
    config.get.return_value = str(DEFAULT_ONLINE_TIMEOUT)
    container.get.return_value = config
    return UserSessionTracker(container)


# =============================================================================
# 上线/下线
# =============================================================================


class TestUserOnline:
    """用户上线行为测试。"""

    def test_user_online_new(self, session_tracker):
        """新用户上线。"""
        session_tracker.user_online("user_1", "Alice")
        assert session_tracker.is_online("user_1") is True
        assert session_tracker.get_online_count() == 1

    def test_user_online_duplicate(self, session_tracker):
        """重复上线不增加计数。"""
        session_tracker.user_online("user_1", "Alice")
        session_tracker.user_online("user_1", "Alice")
        assert session_tracker.get_online_count() == 1

    def test_user_online_multiple_users(self, session_tracker):
        """多用户上线。"""
        session_tracker.user_online("user_1", "Alice")
        session_tracker.user_online("user_2", "Bob")
        session_tracker.user_online("user_3", "Charlie")
        assert session_tracker.get_online_count() == 3

    def test_user_online_tracks_peak(self, session_tracker):
        """峰值统计。"""
        session_tracker.user_online("user_1", "Alice")
        session_tracker.user_online("user_2", "Bob")
        session_tracker.user_online("user_3", "Charlie")
        assert session_tracker._peak_online == 3

        # 用户下线后再上线，峰值不降
        session_tracker.user_offline("user_1")
        session_tracker.user_offline("user_2")
        assert session_tracker._peak_online == 3


class TestUserOffline:
    """用户下线行为测试。"""

    def test_user_offline(self, session_tracker):
        """正常下线。"""
        session_tracker.user_online("user_1", "Alice")
        session_tracker.user_offline("user_1")
        assert session_tracker.is_online("user_1") is False
        assert session_tracker.get_online_count() == 0

    def test_user_offline_non_existent(self, session_tracker):
        """下线不存在的用户不报错。"""
        session_tracker.user_offline("non_existent")
        assert session_tracker.get_online_count() == 0

    def test_user_offline_updates_count(self, session_tracker):
        """下线后在线计数正确。"""
        session_tracker.user_online("user_1", "Alice")
        session_tracker.user_online("user_2", "Bob")
        session_tracker.user_offline("user_1")
        assert session_tracker.get_online_count() == 1


# =============================================================================
# 刷新
# =============================================================================


class TestRefresh:
    """刷新最后活动时间测试。"""

    def test_refresh_online_user(self, session_tracker):
        """刷新在线用户的 last_seen。"""
        session_tracker.user_online("user_1", "Alice")
        original_last_seen = session_tracker._sessions["user_1"]["last_seen"]

        time.sleep(0.001)  # 确保时间变化
        session_tracker.refresh("user_1")

        assert session_tracker._sessions["user_1"]["last_seen"] > original_last_seen

    def test_refresh_offline_user(self, session_tracker):
        """刷新离线用户不报错（无操作）。"""
        session_tracker.refresh("non_existent")
        # 不应影响其他操作
        assert session_tracker.get_online_count() == 0


# =============================================================================
# 查询
# =============================================================================


class TestQuery:
    """查询方法测试。"""

    def test_is_online(self, session_tracker):
        """is_online 判断。"""
        session_tracker.user_online("user_1", "Alice")
        assert session_tracker.is_online("user_1") is True
        assert session_tracker.is_online("user_2") is False

    def test_get_online_count(self, session_tracker):
        """get_online_count 计数。"""
        assert session_tracker.get_online_count() == 0
        session_tracker.user_online("user_1", "Alice")
        assert session_tracker.get_online_count() == 1

    def test_get_online_users(self, session_tracker):
        """get_online_users 返回用户列表。"""
        session_tracker.user_online("user_1", "Alice")
        session_tracker.user_online("user_2", "Bob")
        users = session_tracker.get_online_users()
        assert len(users) == 2
        # 按 login_at 倒序
        assert users[0]["username"] == "Bob"
        assert users[1]["username"] == "Alice"

    def test_get_online_users_empty(self, session_tracker):
        """空在线列表。"""
        assert session_tracker.get_online_users() == []

    def test_get_stats(self, session_tracker):
        """get_stats 返回统计信息。"""
        session_tracker.user_online("user_1", "Alice")
        stats = session_tracker.get_stats()
        assert stats["online_count"] == 1
        assert stats["peak_online"] == 1
        assert stats["timeout_seconds"] == DEFAULT_ONLINE_TIMEOUT
        assert stats["peak_time"] > 0


# =============================================================================
# 超时清理
# =============================================================================


class TestCleanup:
    """超时会话清理测试。"""

    def test_cleanup_no_stale_sessions(self, session_tracker):
        """无超时会话。"""
        session_tracker.user_online("user_1", "Alice")
        with patch.object(time, "time", return_value=time.time() + 10):
            session_tracker._cleanup_stale_sessions()
        assert session_tracker.get_online_count() == 1

    def test_cleanup_all_stale(self, session_tracker):
        """所有会话超时。"""
        session_tracker.user_online("user_1", "Alice")
        session_tracker.user_online("user_2", "Bob")
        # 模拟时间远超过超时阈值
        future = time.time() + DEFAULT_ONLINE_TIMEOUT + 100
        with patch.object(time, "time", return_value=future):
            session_tracker._cleanup_stale_sessions()
        assert session_tracker.get_online_count() == 0
        assert session_tracker.is_online("user_1") is False
        assert session_tracker.is_online("user_2") is False

    def test_cleanup_partial_stale(self, session_tracker):
        """部分会话超时。"""
        session_tracker.user_online("user_1", "Alice")
        # 让 user_2 的 last_seen 更早
        session_tracker.user_online("user_2", "Bob")
        session_tracker._sessions["user_2"]["last_seen"] = (
            time.time() - DEFAULT_ONLINE_TIMEOUT - 100
        )

        session_tracker._cleanup_stale_sessions()
        assert session_tracker.is_online("user_1") is True
        assert session_tracker.is_online("user_2") is False
        assert session_tracker.get_online_count() == 1


# =============================================================================
# 生命周期
# =============================================================================


@pytest.mark.asyncio
class TestLifecycle:
    """定时器生命周期测试。"""

    async def test_start_cleanup(self, session_tracker):
        """启动定时清理任务。"""
        session_tracker.start_cleanup()
        assert session_tracker._scheduler is not None
        assert session_tracker._scheduler.running is True
        session_tracker.stop_cleanup()

    async def test_start_cleanup_idempotent(self, session_tracker):
        """重复启动不创建多个 scheduler。"""
        session_tracker.start_cleanup()
        scheduler_1 = session_tracker._scheduler
        session_tracker.start_cleanup()
        assert session_tracker._scheduler is scheduler_1
        session_tracker.stop_cleanup()

    async def test_stop_cleanup(self, session_tracker):
        """停止定时清理任务。"""
        session_tracker.start_cleanup()
        session_tracker.stop_cleanup()
        assert session_tracker._scheduler is None

    async def test_stop_cleanup_not_started(self, session_tracker):
        """未启动时停止不报错。"""
        session_tracker.stop_cleanup()
        assert session_tracker._scheduler is None

    async def test_close(self, session_tracker):
        """关闭时清理所有会话。"""
        session_tracker.user_online("user_1", "Alice")
        session_tracker.user_online("user_2", "Bob")
        session_tracker.close()
        assert session_tracker.get_online_count() == 0
        assert session_tracker._scheduler is None


# =============================================================================
# 配置
# =============================================================================


class TestConfig:
    """配置初始化测试。"""

    def test_custom_timeout(self):
        """自定义超时时间。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "300"
        container.get.return_value = config
        tracker = UserSessionTracker(container)
        assert tracker._timeout == 300

    def test_invalid_timeout_fallback(self):
        """无效超时回退到默认值。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = "invalid"
        container.get.return_value = config
        tracker = UserSessionTracker(container)
        assert tracker._timeout == DEFAULT_ONLINE_TIMEOUT

    def test_empty_timeout_fallback(self):
        """空字符串超时回退到默认值。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = ""
        container.get.return_value = config
        tracker = UserSessionTracker(container)
        assert tracker._timeout == DEFAULT_ONLINE_TIMEOUT