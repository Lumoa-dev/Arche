"""用户在线会话追踪器 —— 基于内存的事件驱动式实现。

方案：
  第 1 层：事件驱动 —— 登录 → online，页面关闭/sendBeacon → offline
  第 2 层：隐式心跳 —— 任何携带 token 的 API 请求自动刷新 last_seen_at
  第 3 层：兜底超时 —— 后台定时扫描，超过阈值自动标记离线
"""

from __future__ import annotations

import logging
import time
from operator import itemgetter
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    from backend.core.container import ServiceContainer

logger = logging.getLogger(__name__)

# 默认超时阈值（秒）：连续 N 秒无活动视为离线
DEFAULT_ONLINE_TIMEOUT = 900  # 15 分钟


class UserSessionTracker:
    """线程安全的在线用户追踪器（单机内存版）。"""

    def __init__(self, container: ServiceContainer):
        self.container = container
        config = container.get("config")
        timeout_str = config.get("ONLINE_TIMEOUT_SECONDS", str(DEFAULT_ONLINE_TIMEOUT))
        try:
            self._timeout = (
                int(timeout_str) if str(timeout_str).strip() else DEFAULT_ONLINE_TIMEOUT
            )
        except (ValueError, TypeError):
            self._timeout = DEFAULT_ONLINE_TIMEOUT

        # user_id → {"last_seen": float, "username": str, "login_at": float}
        self._sessions: dict[str, dict] = {}
        self._scheduler: AsyncIOScheduler | None = None

        # 统计缓存
        self._online_count = 0
        self._peak_online = 0
        self._peak_time = 0.0

    # ── 生命期控制 ──

    def start_cleanup(self) -> None:
        """启动定时清理任务（兜底超时）。"""
        if self._scheduler:
            return
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._cleanup_stale_sessions,
            trigger=IntervalTrigger(minutes=1),
            id="session_cleanup",
            replace_existing=True,
        )
        self._scheduler.start()

    def stop_cleanup(self) -> None:
        if self._scheduler and getattr(self._scheduler, "running", False):
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    # ── 核心操作 ──

    def user_online(self, user_id: str, username: str) -> None:
        """用户上线（登录时调用）。"""
        now = time.time()
        if user_id not in self._sessions:
            self._sessions[user_id] = {
                "last_seen": now,
                "username": username,
                "login_at": now,
            }
            self._online_count = len(self._sessions)
            if self._online_count > self._peak_online:
                self._peak_online = self._online_count
                self._peak_time = now
            logger.info(
                "用户上线: %s (%s), 当前在线: %d", username, user_id, self._online_count
            )
        else:
            # 已在线，刷新即可
            self._sessions[user_id]["last_seen"] = now
            self._sessions[user_id]["username"] = username

    def user_offline(self, user_id: str) -> None:
        """用户下线（sendBeacon 或退出登录时调用）。"""
        session = self._sessions.pop(user_id, None)
        if session:
            self._online_count = len(self._sessions)
            elapsed = time.time() - session["login_at"]
            logger.info(
                "用户下线: %s (%s), 在线时长 %.0f秒, 当前在线: %d",
                session["username"],
                user_id,
                elapsed,
                self._online_count,
            )

    def refresh(self, user_id: str) -> None:
        """刷新用户的最后活动时间（API 请求时调用）。"""
        if user_id in self._sessions:
            self._sessions[user_id]["last_seen"] = time.time()

    # ── 查询 ──

    def get_online_count(self) -> int:
        """获取当前在线用户数。"""
        return len(self._sessions)

    def get_online_users(self) -> list[dict]:
        """获取在线用户列表（按登录时间倒序）。"""
        now = time.time()
        users = []
        for uid, info in self._sessions.items():
            users.append(
                {
                    "user_id": uid,
                    "username": info["username"],
                    "login_at": info["login_at"],
                    "last_seen": info["last_seen"],
                    "idle_seconds": int(now - info["last_seen"]),
                }
            )
        users.sort(key=itemgetter("login_at"), reverse=True)
        return users

    def is_online(self, user_id: str) -> bool:
        return user_id in self._sessions

    def get_stats(self) -> dict:
        """获取在线统计快照。"""
        return {
            "online_count": self.get_online_count(),
            "peak_online": self._peak_online,
            "peak_time": self._peak_time,
            "timeout_seconds": self._timeout,
        }

    # ── 内部维护 ──

    def _cleanup_stale_sessions(self) -> None:
        """清理超时会话（兜底逻辑）。"""
        now = time.time()
        stale_ids = [
            uid
            for uid, info in self._sessions.items()
            if now - info["last_seen"] > self._timeout
        ]
        for uid in stale_ids:
            session = self._sessions.pop(uid, None)
            if session:
                logger.info(
                    "会话超时自动离线: %s (%s), 空闲 %.0f秒",
                    session["username"],
                    uid,
                    now - session["last_seen"],
                )
        if stale_ids:
            self._online_count = len(self._sessions)
            logger.debug(
                "清理超时会话 %d 个, 当前在线: %d", len(stale_ids), self._online_count
            )

    def close(self) -> None:
        self.stop_cleanup()
        self._sessions.clear()
