"""System Monitor Service — 基于 psutil 的系统资源采集与历史数据管理。"""

from __future__ import annotations

import sys
import time
from collections import deque
from operator import itemgetter
from pathlib import Path
from typing import TYPE_CHECKING

import psutil
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    from backend.core.container import ServiceContainer


class SystemMonitorService:
    MAX_HISTORY = 300

    def __init__(self, container: ServiceContainer):
        self.container = container
        config = container.get("config")
        interval = config.get("MONITOR_COLLECT_INTERVAL", "10")
        self._collect_interval = int(interval) if str(interval).strip() else 10

        self._scheduler: AsyncIOScheduler | None = None
        self._history: deque = deque(maxlen=self.MAX_HISTORY)
        self._last_net = psutil.net_io_counters()

        # ── 容器环境检测与 cgroup v2 状态 ──
        self._in_container = self._detect_container()
        self._last_cgroup_cpu_usage: int | None = None  # 上一次 usage_usec
        self._last_cgroup_cpu_time: float | None = None  # 上一次读取时间戳
        self._cgroup_cpu_cores: float = 0.0  # 容器可用 CPU 核数（解析自 cpu.max）
        if self._in_container:
            self._cgroup_cpu_cores = self._parse_cgroup_cpu_max()

    # ── 容器环境检测 ──

    @staticmethod
    def _detect_container() -> bool:
        """检测当前进程是否运行在容器环境中。

        检测策略：
          1. /.dockerenv 文件存在（Docker 容器标志）
          2. /proc/1/cgroup 中包含 docker 或 kubepods 字符串
        """
        if Path("/.dockerenv").exists():
            return True

        cgroup_path = Path("/proc/1/cgroup")
        if cgroup_path.exists():
            try:
                content = cgroup_path.read_text(encoding="utf-8", errors="ignore")
                if "docker" in content or "kubepods" in content:
                    return True
            except OSError:
                pass

        return False

    def _parse_cgroup_cpu_max(self) -> float:
        """解析 /sys/fs/cgroup/cpu.max，返回可用 CPU 核数。

        格式："quota_us period_us" 或 "max period_us"
        - "max" 表示无限制，返回 0.0（由上层使用 cpu_count 兜底）
        """
        cpu_max_path = Path("/sys/fs/cgroup/cpu.max")
        if not cpu_max_path.exists():
            return 0.0
        try:
            line = cpu_max_path.read_text(encoding="utf-8", errors="ignore").strip()
            parts = line.split()
            if len(parts) < 2:
                return 0.0
            quota_str, period_str = parts[0], parts[1]
            period_us = int(period_str)
            if period_us <= 0:
                return 0.0
            if quota_str == "max":
                return 0.0  # 无限制，上层使用 cpu_count
            quota_us = int(quota_str)
            return quota_us / period_us
        except (OSError, ValueError, IndexError):
            return 0.0

    def _read_cgroup_cpu_usage(self) -> int | None:
        """读取 /sys/fs/cgroup/cpu.stat 中的 usage_usec 值（微秒）。"""
        cpu_stat_path = Path("/sys/fs/cgroup/cpu.stat")
        if not cpu_stat_path.exists():
            return None
        try:
            for line in cpu_stat_path.read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines():
                if line.startswith("usage_usec"):
                    return int(line.split()[1])
        except (OSError, ValueError, IndexError):
            pass
        return None

    def _get_cgroup_cpu_percent(self) -> float:
        """通过 cgroup v2 计算容器 CPU 使用百分比。

        计算方式：
          - 读取 cpu.stat 中的 usage_usec（累计 CPU 时间，微秒）
          - 计算两次读取间的增量
          - 根据 cpu.max 中的配额归一化到百分比

        首次读取时返回 0.0（无历史数据）。
        """
        now = time.time()
        usage = self._read_cgroup_cpu_usage()
        if usage is None:
            return 0.0

        if self._last_cgroup_cpu_usage is None or self._last_cgroup_cpu_time is None:
            # 首次读取，保存状态后返回 0
            self._last_cgroup_cpu_usage = usage
            self._last_cgroup_cpu_time = now
            return 0.0

        # 计算增量
        usage_delta = usage - self._last_cgroup_cpu_usage
        time_delta = now - self._last_cgroup_cpu_time

        # 更新状态
        self._last_cgroup_cpu_usage = usage
        self._last_cgroup_cpu_time = now

        if usage_delta <= 0 or time_delta <= 0:
            return 0.0

        # 基础百分比（相对单核）
        raw_pct = (usage_delta / (time_delta * 1_000_000)) * 100.0

        # 根据 cpu.max 配额归一化
        cpu_cores = self._cgroup_cpu_cores
        if cpu_cores <= 0:
            cpu_cores = psutil.cpu_count()

        if cpu_cores <= 0:
            return raw_pct

        return raw_pct / cpu_cores

    def _get_cpu_percent(self) -> float:
        """获取 CPU 使用百分比。

        - 容器环境：通过 cgroup v2 计算
        - 非容器环境：使用 psutil
        """
        if self._in_container:
            return self._get_cgroup_cpu_percent()
        return psutil.cpu_percent(interval=0)

    # --- 采集控制 ---
    def start_collection(self) -> None:
        if self._scheduler:
            return
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._collect_snapshot,
            trigger=IntervalTrigger(seconds=self._collect_interval),
            id="system_monitor_collect",
            replace_existing=True,
        )
        self._scheduler.start()

    def stop_collection(self) -> None:
        if self._scheduler and getattr(self._scheduler, "running", False):
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    async def _collect_snapshot(self) -> None:
        """定时采集系统快照。"""
        net = psutil.net_io_counters()
        net_diff_sent = net.bytes_sent - self._last_net.bytes_sent
        net_diff_recv = net.bytes_recv - self._last_net.bytes_recv
        self._last_net = net

        try:
            load = list(psutil.getloadavg())
        except (OSError, NotImplementedError):
            load = [0.0, 0.0, 0.0]

        snapshot = {
            "ts": time.time(),
            "cpu_pct": self._get_cpu_percent(),
            "cpu_count": psutil.cpu_count(),
            "mem_total": psutil.virtual_memory().total,
            "mem_used": psutil.virtual_memory().used,
            "mem_pct": psutil.virtual_memory().percent,
            "disk_total": psutil.disk_usage("/").total,
            "disk_used": psutil.disk_usage("/").used,
            "disk_pct": psutil.disk_usage("/").percent,
            "net_sent_rate": net_diff_sent / self._collect_interval,
            "net_recv_rate": net_diff_recv / self._collect_interval,
            "load_1": load[0],
            "load_5": load[1],
            "load_15": load[2],
        }
        self._history.append(snapshot)

    # --- 查询接口（同步） ---
    def get_summary(self) -> dict:
        """系统概览。"""
        try:
            load = list(psutil.getloadavg())
        except (OSError, NotImplementedError):
            load = [0.0, 0.0, 0.0]

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        return {
            "cpu_percent": self._get_cpu_percent(),
            "cpu_count": psutil.cpu_count(),
            "memory_used_gb": round(mem.used / 1024**3, 2),
            "memory_total_gb": round(mem.total / 1024**3, 2),
            "memory_percent": mem.percent,
            "disk_used_gb": round(disk.used / 1024**3, 2),
            "disk_total_gb": round(disk.total / 1024**3, 2),
            "disk_percent": disk.percent,
            "net_sent": net.bytes_sent,
            "net_recv": net.bytes_recv,
            "process_count": len(psutil.pids()),
            "python_version": sys.version.split()[0],
            "uptime": time.time() - psutil.boot_time(),
            "platform": sys.platform,
            "load_1": load[0],
            "load_5": load[1],
            "load_15": load[2],
        }

    def get_cpu_detail(self) -> dict:
        """CPU 详细信息。"""
        freq = psutil.cpu_freq()
        try:
            load = list(psutil.getloadavg())
        except (OSError, NotImplementedError):
            load = [0.0, 0.0, 0.0]

        # 容器环境下无法获取 per-CPU 百分比，回退为空列表
        if self._in_container:
            per_cpu = []
        else:
            per_cpu = psutil.cpu_percent(interval=0, percpu=True)

        return {
            "count_physical": psutil.cpu_count(logical=False),
            "count_logical": psutil.cpu_count(logical=True),
            "freq_current": freq.current if freq else None,
            "freq_min": freq.min if freq else None,
            "freq_max": freq.max if freq else None,
            "per_cpu_pct": per_cpu,
            "load_1": load[0],
            "load_5": load[1],
            "load_15": load[2],
        }

    def get_memory_detail(self) -> dict:
        """内存详细信息。"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "free": mem.free,
            "percent": mem.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_free": swap.free,
            "swap_percent": swap.percent,
        }

    def get_disk_detail(self) -> dict:
        """磁盘详细信息（按分区）。"""
        usage = psutil.disk_usage("/")
        partitions = []
        for part in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(part.mountpoint)
                partitions.append(
                    {
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total": u.total,
                        "used": u.used,
                        "free": u.free,
                        "percent": u.percent,
                    }
                )
            except (PermissionError, OSError):
                pass

        return {
            "root_total": usage.total,
            "root_used": usage.used,
            "root_free": usage.free,
            "root_percent": usage.percent,
            "partitions": partitions,
        }

    def get_network_io(self) -> dict:
        """网络 I/O。"""
        net = psutil.net_io_counters()
        return {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errin": net.errin,
            "errout": net.errout,
            "dropin": net.dropin,
            "dropout": net.dropout,
        }

    def get_history(self, page: int = 1, page_size: int = 50) -> dict:
        """历史数据分页查询。"""
        total = len(self._history)
        start = max(0, total - page * page_size)
        end = total - (page - 1) * page_size
        items = list(self._history)[start:end]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_processes(self, sort_by: str = "cpu", limit: int = 50) -> dict:
        """进程列表，按指定字段排序。"""
        procs = []
        for proc in psutil.process_iter(
            ["pid", "name", "status", "cpu_percent", "memory_percent", "create_time"]
        ):
            try:
                info = proc.info
                procs.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"] or "unknown",
                        "status": info["status"],
                        "cpu_percent": info["cpu_percent"] or 0.0,
                        "memory_percent": round(info["memory_percent"] or 0.0, 2),
                        "create_time": info["create_time"],
                    }
                )
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                pass

        reverse = True
        key = (
            sort_by
            if sort_by in ("cpu_percent", "memory_percent", "pid", "create_time")
            else "cpu_percent"
        )
        procs.sort(key=itemgetter(key), reverse=reverse)

        return {"items": procs[:limit], "total": len(procs), "limit": limit}
