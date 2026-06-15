"""API 请求统计 —— QPS、P99 延迟、请求量追踪。"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from operator import itemgetter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.core.container import ServiceContainer


class RequestStatsTracker:
    """内存版 API 请求统计追踪器。

    - 按分钟聚合 QPS
    - 滑动窗口计算 P99 延迟
    - 按路径统计请求量
    """

    WINDOW_SECONDS = 60  # 统计窗口：1 分钟
    MAX_PATH_HISTORY = 500  # _path_stats_history 最大条目数

    def __init__(self, container: ServiceContainer):
        self.container = container

        # 当前分钟的时间戳（秒级，取整到分钟）
        self._current_minute: int = 0
        self._minute_count: int = 0  # 当前分钟请求数

        # 历史每分钟的请求数（最近 60 分钟）
        self._qps_history: deque[dict] = deque(maxlen=60)

        # 延迟样本（滑动窗口，最近 1000 个请求的延迟）
        self._latency_samples: deque[float] = deque(maxlen=1000)

        # 按路径统计（最近 60 分钟）
        self._path_stats: dict[str, int] = defaultdict(int)
        self._path_stats_history: dict[str, int] = {}
        self._path_stats_reset_time: float = time.time()

        # 累积总数
        self._total_requests: int = 0
        self._total_errors: int = 0

        # 今日统计（按自然日）
        self._today_date: str = ""
        self._today_requests: int = 0

    def record_request(self, path: str, duration_ms: float, status_code: int) -> None:
        """记录一次 API 请求。"""
        now = time.time()
        minute = int(now // 60)

        # 换分钟了，归档上一分钟数据
        if minute != self._current_minute:
            if self._current_minute > 0 and self._minute_count > 0:
                self._qps_history.append(
                    {
                        "ts": self._current_minute * 60,
                        "count": self._minute_count,
                        "qps": round(self._minute_count / self.WINDOW_SECONDS, 2),
                    }
                )
            self._current_minute = minute
            self._minute_count = 0

        self._minute_count += 1

        # 延迟样本
        self._latency_samples.append(duration_ms)

        # 路径统计（每 5 分钟重置一次，避免无限增长）
        if now - self._path_stats_reset_time > 300:
            for path, count in self._path_stats.items():
                self._path_stats_history[path] = (
                    self._path_stats_history.get(path, 0) + count
                )
            # 限制历史条目数，防止内存泄漏
            if len(self._path_stats_history) > self.MAX_PATH_HISTORY:
                sorted_items = sorted(
                    self._path_stats_history.items(),
                    key=itemgetter(1),
                    reverse=True,
                )[: self.MAX_PATH_HISTORY]
                self._path_stats_history = dict(sorted_items)
            self._path_stats.clear()
            self._path_stats_reset_time = now
        self._path_stats[path] += 1

        # 累积
        self._total_requests += 1
        if status_code >= 500:
            self._total_errors += 1

        # 今日统计
        today = time.strftime("%Y-%m-%d", time.localtime(now))
        if today != self._today_date:
            self._today_date = today
            self._today_requests = 0
        self._today_requests += 1

    # ── 查询接口 ──

    def get_current_qps(self) -> float:
        """获取当前 QPS。"""
        if self._minute_count == 0:
            return 0.0
        elapsed = time.time() - (self._current_minute * 60)
        if elapsed <= 0:
            return 0.0
        return round(self._minute_count / elapsed, 2)

    def get_p99_latency(self) -> float:
        """获取 P99 延迟（毫秒）。"""
        if not self._latency_samples:
            return 0.0
        sorted_samples = sorted(self._latency_samples)
        idx = int(len(sorted_samples) * 0.99)
        return round(sorted_samples[min(idx, len(sorted_samples) - 1)], 2)

    def get_p50_latency(self) -> float:
        """获取 P50 延迟（毫秒）。"""
        if not self._latency_samples:
            return 0.0
        sorted_samples = sorted(self._latency_samples)
        idx = int(len(sorted_samples) * 0.5)
        return round(sorted_samples[min(idx, len(sorted_samples) - 1)], 2)

    def get_qps_history(self) -> list[dict]:
        """获取 QPS 历史趋势（最近 60 分钟）。"""
        return list(self._qps_history)

    def get_today_requests(self) -> int:
        """获取今日总请求量。"""
        return self._today_requests

    def get_path_stats(self) -> dict[str, int]:
        """获取按路径的请求统计（按次数降序）。"""
        combined = dict(self._path_stats_history)
        for path, count in self._path_stats.items():
            combined[path] = combined.get(path, 0) + count
        return dict(sorted(combined.items(), key=itemgetter(1), reverse=True))

    def get_stats(self) -> dict:
        """获取完整统计快照。"""
        return {
            "current_qps": self.get_current_qps(),
            "p99_latency_ms": self.get_p99_latency(),
            "p50_latency_ms": self.get_p50_latency(),
            "today_requests": self.get_today_requests(),
            "total_requests": self._total_requests,
            "total_errors": self._total_errors,
            "error_rate": round(
                self._total_errors / max(self._total_requests, 1) * 100, 2
            ),
        }

    def close(self) -> None:
        self._qps_history.clear()
        self._latency_samples.clear()
        self._path_stats.clear()
        self._path_stats_history.clear()
