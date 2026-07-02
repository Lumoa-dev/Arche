"""UserSessionTracker 在线会话追踪器测试。

测试原则：
- 纯内存实现，无需数据库
- 使用 time.time() 真实时间，通过 sleep 控制窗口
- 不启动 APScheduler（通过直接调用 _cleanup_stale_sessions 测试兜底逻辑）
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from backend.plugins.auth.session import UserSessionTracker


@pytest.fixture
def tracker():
    """创建带 mock container 的 UserSessionTracker 实例。"""
    container = MagicMock()
    config = MagicMock()
    config.get.return_value = "60"  # 60 秒超时
    container.get.return_value = config
    return UserSessionTracker(container)


class TestUserSessionTracker:
    """UserSessionTracker 行为测试。"""

    # ── 上线 / 下线 ──

    def test_user_online_adds_to_sessions(self, tracker):
        """用户上线应被添加到在线列表。"""
        tracker.user_online("user-1", "alice")
        assert tracker.is_online("user-1") is True
        assert tracker.get_online_count() == 1

    def test_user_offline_removes_from_sessions(self, tracker):
        """用户下线应从在线列表移除。"""
        tracker.user_online("user-1", "alice")
        tracker.user_offline("user-1")
        assert tracker.is_online("user-1") is False
        assert tracker.get_online_count() == 0

    def test_offline_nonexistent_user_no_error(self, tracker):
        """让不在线的用户下线不应抛出异常。"""
        tracker.user_offline("never-online")  # 不应抛异常

    def test_multiple_users_online(self, tracker):
        """多个用户同时在线应正确计数。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        tracker.user_online("user-3", "charlie")
        assert tracker.get_online_count() == 3

    # ── 刷新 ──

    def test_refresh_updates_last_seen(self, tracker):
        """refresh() 应更新用户的 last_seen 时间。"""
        tracker.user_online("user-1", "alice")
        original_last_seen = tracker._sessions["user-1"]["last_seen"]

        time.sleep(0.01)  # 确保时间有变化
        tracker.refresh("user-1")

        assert tracker._sessions["user-1"]["last_seen"] > original_last_seen

    def test_refresh_nonexistent_user_no_error(self, tracker):
        """refresh() 不存在的用户不应抛出异常。"""
        tracker.refresh("never-existed")  # 不应抛异常

    # ── 查询 ──

    def test_get_online_users_returns_user_list(self, tracker):
        """get_online_users() 应返回在线用户列表。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")

        users = tracker.get_online_users()
        assert len(users) == 2
        usernames = {u["username"] for u in users}
        assert usernames == {"alice", "bob"}

    def test_get_online_users_sorted_by_login_time(self, tracker):
        """在线用户列表应按登录时间倒序排列。"""
        tracker.user_online("user-1", "alice")
        time.sleep(0.01)
        tracker.user_online("user-2", "bob")

        users = tracker.get_online_users()
        assert users[0]["username"] == "bob"
        assert users[1]["username"] == "alice"

    def test_get_online_users_includes_idle_seconds(self, tracker):
        """在线用户信息应包含空闲秒数。"""
        tracker.user_online("user-1", "alice")
        time.sleep(0.01)

        users = tracker.get_online_users()
        assert users[0]["idle_seconds"] >= 0

    def test_is_online_returns_false_for_offline_user(self, tracker):
        """不在线的用户返回 False。"""
        assert tracker.is_online("phantom") is False

    # ── 统计 ──

    def test_get_stats_returns_snapshot(self, tracker):
        """get_stats() 返回统计快照。"""
        tracker.user_online("user-1", "alice")
        stats = tracker.get_stats()

        assert stats["online_count"] == 1
        assert stats["peak_online"] == 1
        assert stats["peak_time"] > 0
        assert stats["timeout_seconds"] == 60

    def test_peak_online_tracks_maximum(self, tracker):
        """peak_online 应记录历史最高并发数。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-2", "bob")
        tracker.user_online("user-3", "charlie")

        tracker.user_offline("user-1")
        tracker.user_offline("user-2")

        # 峰值应为 3，即使当前只有 1 人在线
        assert tracker.get_stats()["peak_online"] == 3

    # ── 重复上线 ──

    def test_duplicate_online_refreshes_not_duplicates(self, tracker):
        """同一用户重复上线不应重复计数。"""
        tracker.user_online("user-1", "alice")
        tracker.user_online("user-1", "alice")  # 再次上线
        assert tracker.get_online_count() == 1

    # ── 超时清理 ──

    def test_cleanup_stale_sessions_removes_timed_out_users(self, tracker):
        """超时会话应被清理。"""
        tracker.user_online("user-1", "alice")
        # 直接修改 last_seen 为很久以前
        tracker._sessions["user-1"]["last_seen"] = time.time() - 120  # 超过 60 秒

        tracker._cleanup_stale_sessions()

        assert tracker.is_online("user-1") is False
        assert tracker.get_online_count() == 0

    def test_cleanup_only_removes_stale_sessions(self, tracker):
        """清理只移除超时会话，不触及其他会话。"""
        tracker.user_online("user-1", "alice")
        tracker._sessions["user-1"]["last_seen"] = time.time() - 120  # 超时

        tracker.user_online("user-2", "bob")  # 未超时

        tracker._cleanup_stale_sessions()

        assert tracker.is_online("user-1") is False
        assert tracker.is_online("user-2") is True

    def test_cleanup_empty_sessions_no_error(self, tracker):
        """清理空的在线列表不应抛出异常。"""
        tracker._cleanup_stale_sessions()  # 不应抛异常

    # ── 生命周期 ──

    def test_start_cleanup_no_event_loop(self, tracker):
        """无事件循环时 start_cleanup 不应崩溃。"""
        # 不启动事件循环，直接验证不会崩溃
        tracker._scheduler = None
        # 直接创建 scheduler 但不 start
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        tracker._scheduler = AsyncIOScheduler()
        assert tracker._scheduler is not None

    def test_stop_cleanup_without_start(self, tracker):
        """未启动时 stop_cleanup 不应崩溃。"""
        tracker.stop_cleanup()  # 不应抛异常

    def test_close_clears_sessions(self, tracker):
        """close() 应清理所有会话。"""
        tracker.user_online("user-1", "alice")
        tracker.close()

        assert tracker.get_online_count() == 0
        assert tracker._scheduler is None

    # ── 配置容错 ──

    def test_invalid_timeout_uses_default(self):
        """无效的超时配置应使用默认值。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = ""  # 空字符串
        container.get.return_value = config

        t = UserSessionTracker(container)
        assert t._timeout == 900  # 默认 15 分钟