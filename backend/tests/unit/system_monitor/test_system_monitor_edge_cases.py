"""SystemMonitorService 边界情况测试（psutil 模拟）。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.plugins.system_monitor import services as system_services
from backend.plugins.system_monitor.services import SystemMonitorService


def _service(monkeypatch, config_value="10"):
    net = SimpleNamespace(
        bytes_sent=100,
        bytes_recv=200,
        packets_sent=3,
        packets_recv=4,
        errin=0,
        errout=0,
        dropin=0,
        dropout=0,
    )
    mem = SimpleNamespace(
        total=8 * 1024**3,
        used=2 * 1024**3,
        available=6 * 1024**3,
        free=5 * 1024**3,
        percent=25.0,
    )
    swap = SimpleNamespace(total=1024, used=256, free=768, percent=25.0)
    disk = SimpleNamespace(total=1000, used=400, free=600, percent=40.0)
    freq = SimpleNamespace(current=2400.0, min=1200.0, max=3600.0)
    part = SimpleNamespace(device="disk0", mountpoint="/", fstype="ext4")

    def _net_io_counters():
        return net

    def _virtual_memory():
        return mem

    def _swap_memory():
        return swap

    def _disk_usage(path):
        return disk

    def _disk_partitions(all=False):
        return [part]

    def _cpu_percent(interval=0, percpu=False):
        return [1.0, 2.0] if percpu else 12.5

    def _cpu_count(logical=True):
        return 8 if logical else 4

    monkeypatch.setattr(system_services.psutil, "net_io_counters", _net_io_counters)
    monkeypatch.setattr(system_services.psutil, "virtual_memory", _virtual_memory)
    monkeypatch.setattr(system_services.psutil, "swap_memory", _swap_memory)
    monkeypatch.setattr(system_services.psutil, "disk_usage", _disk_usage)
    monkeypatch.setattr(system_services.psutil, "disk_partitions", _disk_partitions)
    monkeypatch.setattr(system_services.psutil, "cpu_percent", _cpu_percent)
    monkeypatch.setattr(system_services.psutil, "cpu_count", _cpu_count)
    monkeypatch.setattr(system_services.psutil, "cpu_freq", lambda: freq)
    monkeypatch.setattr(system_services.psutil, "getloadavg", lambda: (0.1, 0.2, 0.3))
    monkeypatch.setattr(system_services.psutil, "pids", lambda: [1, 2])
    monkeypatch.setattr(system_services.psutil, "boot_time", lambda: 100.0)
    monkeypatch.setattr(system_services.time, "time", lambda: 200.0)

    container = MagicMock()
    container.get.return_value.get.return_value = config_value
    return SystemMonitorService(container)


class TestContainerDetection:
    def test_container_detection_dockerenv_exists(self, monkeypatch):
        class _MockPath:
            def __init__(self, path):
                self._path = path

            def exists(self):
                return self._path == "/.dockerenv"

            def read_text(self, **kwargs):
                return ""

        monkeypatch.setattr(system_services, "Path", _MockPath)
        service = _service(monkeypatch)
        assert service._in_container is True

    def test_container_detection_via_cgroup(self, monkeypatch):
        class _MockPath:
            def __init__(self, path):
                self._path = path

            def exists(self):
                if self._path == "/.dockerenv":
                    return False
                return self._path == "/proc/1/cgroup"

            def read_text(self, **kwargs):
                if self._path == "/proc/1/cgroup":
                    return "0::/system.slice/docker-abc123.scope"
                return ""

        monkeypatch.setattr(system_services, "Path", _MockPath)
        service = _service(monkeypatch)
        assert service._in_container is True

    def test_container_detection_no_container(self, monkeypatch):
        class _MockPath:
            def __init__(self, path):
                self._path = path

            def exists(self):
                return False

            def read_text(self, **kwargs):
                return ""

        monkeypatch.setattr(system_services, "Path", _MockPath)
        service = _service(monkeypatch)
        assert service._in_container is False


class TestCgroupCpu:
    def test_cgroup_parse_cpu_max_unlimited(self, monkeypatch):
        _paths = {
            "/.dockerenv": (True, ""),
            "/sys/fs/cgroup/cpu.max": (True, "max 100000"),
        }

        class _MockPath:
            def __init__(self, path):
                self._path = path

            def exists(self):
                info = _paths.get(self._path)
                return info is not None and info[0]

            def read_text(self, **kwargs):
                info = _paths.get(self._path)
                return info[1] if info else ""

        monkeypatch.setattr(system_services, "Path", _MockPath)
        service = _service(monkeypatch)
        assert service._cgroup_cpu_cores == 0.0

    def test_cgroup_parse_cpu_max_normal(self, monkeypatch):
        _paths = {
            "/.dockerenv": (True, ""),
            "/sys/fs/cgroup/cpu.max": (True, "40000 100000"),
        }

        class _MockPath:
            def __init__(self, path):
                self._path = path

            def exists(self):
                info = _paths.get(self._path)
                return info is not None and info[0]

            def read_text(self, **kwargs):
                info = _paths.get(self._path)
                return info[1] if info else ""

        monkeypatch.setattr(system_services, "Path", _MockPath)
        service = _service(monkeypatch)
        assert service._cgroup_cpu_cores == 0.4

    def test_cgroup_parse_cpu_max_file_missing(self, monkeypatch):
        _paths = {
            "/.dockerenv": (True, ""),
        }

        class _MockPath:
            def __init__(self, path):
                self._path = path

            def exists(self):
                info = _paths.get(self._path)
                return info is not None and info[0]

            def read_text(self, **kwargs):
                info = _paths.get(self._path)
                return info[1] if info else ""

        monkeypatch.setattr(system_services, "Path", _MockPath)
        service = _service(monkeypatch)
        assert service._cgroup_cpu_cores == 0.0

    def test_cgroup_cpu_percent_first_call_returns_zero(self, monkeypatch):
        _paths = {
            "/.dockerenv": (True, ""),
            "/sys/fs/cgroup/cpu.max": (True, "20000 100000"),
        }

        class _MockPath:
            def __init__(self, path):
                self._path = path

            def exists(self):
                info = _paths.get(self._path)
                return info is not None and info[0]

            def read_text(self, **kwargs):
                info = _paths.get(self._path)
                return info[1] if info else ""

        monkeypatch.setattr(system_services, "Path", _MockPath)
        service = _service(monkeypatch)
        assert service._cgroup_cpu_cores == 0.2
        assert service._last_cgroup_cpu_usage is None

        monkeypatch.setattr(service, "_read_cgroup_cpu_usage", lambda: 500000)
        result = service._get_cgroup_cpu_percent()
        assert result == 0.0
        assert service._last_cgroup_cpu_usage == 500000


class TestNetworkIO:
    @pytest.mark.asyncio
    async def test_network_io_after_collect_snapshot_shows_diff(self, monkeypatch):
        net_state = {"sent": 100, "recv": 200}

        def _net_io_counters():
            return SimpleNamespace(
                bytes_sent=net_state["sent"],
                bytes_recv=net_state["recv"],
                packets_sent=3,
                packets_recv=4,
                errin=0,
                errout=0,
                dropin=0,
                dropout=0,
            )

        mem = SimpleNamespace(
            total=8 * 1024**3,
            used=2 * 1024**3,
            available=6 * 1024**3,
            free=5 * 1024**3,
            percent=25.0,
        )
        swap = SimpleNamespace(total=1024, used=256, free=768, percent=25.0)
        disk = SimpleNamespace(total=1000, used=400, free=600, percent=40.0)
        freq = SimpleNamespace(current=2400.0, min=1200.0, max=3600.0)
        part = SimpleNamespace(device="disk0", mountpoint="/", fstype="ext4")

        monkeypatch.setattr(system_services.psutil, "net_io_counters", _net_io_counters)

        def _virtual_memory():
            return mem

        def _swap_memory():
            return swap

        def _disk_usage(path):
            return disk

        def _disk_partitions(all=False):
            return [part]

        def _cpu_percent(interval=0, percpu=False):
            return [1.0, 2.0] if percpu else 12.5

        def _cpu_count(logical=True):
            return 8 if logical else 4

        monkeypatch.setattr(system_services.psutil, "virtual_memory", _virtual_memory)
        monkeypatch.setattr(system_services.psutil, "swap_memory", _swap_memory)
        monkeypatch.setattr(system_services.psutil, "disk_usage", _disk_usage)
        monkeypatch.setattr(system_services.psutil, "disk_partitions", _disk_partitions)
        monkeypatch.setattr(system_services.psutil, "cpu_percent", _cpu_percent)
        monkeypatch.setattr(system_services.psutil, "cpu_count", _cpu_count)
        monkeypatch.setattr(system_services.psutil, "cpu_freq", lambda: freq)
        monkeypatch.setattr(
            system_services.psutil, "getloadavg", lambda: (0.1, 0.2, 0.3)
        )
        monkeypatch.setattr(system_services.psutil, "pids", lambda: [1, 2])
        monkeypatch.setattr(system_services.psutil, "boot_time", lambda: 100.0)
        monkeypatch.setattr(system_services.time, "time", lambda: 200.0)

        container = MagicMock()
        container.get.return_value.get.return_value = "10"
        service = SystemMonitorService(container)

        net_state["sent"] = 500
        net_state["recv"] = 700

        await service._collect_snapshot()
        history = service.get_history(page=1, page_size=10)
        assert len(history["items"]) == 1
        item = history["items"][0]
        assert item["net_sent_rate"] == 40.0
        assert item["net_recv_rate"] == 50.0

    def test_network_io_zero_initial(self, monkeypatch):
        service = _service(monkeypatch)
        net = service.get_network_io()
        assert net["bytes_sent"] == 100
        assert net["bytes_recv"] == 200
        assert net["packets_sent"] == 3
        assert net["packets_recv"] == 4
        assert net["errin"] == 0
        assert net["errout"] == 0
        assert net["dropin"] == 0
        assert net["dropout"] == 0


class TestProcessSorting:
    def _make_processes(self, monkeypatch, service):
        class Proc:
            def __init__(self, info):
                self.info = info

        def _process_iter(fields):
            return [
                Proc(
                    {
                        "pid": 3,
                        "name": "chrome",
                        "status": "running",
                        "cpu_percent": 5.0,
                        "memory_percent": 12.34,
                        "create_time": 3.0,
                    }
                ),
                Proc(
                    {
                        "pid": 2,
                        "name": "python",
                        "status": "running",
                        "cpu_percent": 10.0,
                        "memory_percent": 5.55,
                        "create_time": 2.0,
                    }
                ),
                Proc(
                    {
                        "pid": 1,
                        "name": "systemd",
                        "status": "sleeping",
                        "cpu_percent": 0.0,
                        "memory_percent": 1.23,
                        "create_time": 1.0,
                    }
                ),
            ]

        monkeypatch.setattr(system_services.psutil, "process_iter", _process_iter)

    def test_get_processes_sort_by_memory(self, monkeypatch):
        service = _service(monkeypatch)
        self._make_processes(monkeypatch, service)
        result = service.get_processes(sort_by="memory_percent", limit=10)
        items = result["items"]
        assert len(items) == 3
        assert items[0]["pid"] == 3
        assert items[1]["pid"] == 2
        assert items[2]["pid"] == 1
        assert items[0]["memory_percent"] == 12.34

    def test_get_processes_sort_by_unknown_field(self, monkeypatch):
        service = _service(monkeypatch)
        self._make_processes(monkeypatch, service)
        result = service.get_processes(sort_by="nonexistent_field", limit=10)
        items = result["items"]
        assert len(items) == 3
        assert items[0]["pid"] == 2
        assert items[1]["pid"] == 3
        assert items[2]["pid"] == 1


class TestHistoryPagination:
    def _populate_history(self, service, count):
        for i in range(count):
            service._history.append({"ts": 100.0 + i, "cpu_pct": float(i)})

    def test_get_history_multiple_pages(self, monkeypatch):
        service = _service(monkeypatch)
        self._populate_history(service, 25)

        page1 = service.get_history(page=1, page_size=10)
        assert page1["total"] == 25
        assert len(page1["items"]) == 10
        assert page1["page"] == 1

        page2 = service.get_history(page=2, page_size=10)
        assert len(page2["items"]) == 10

        page3 = service.get_history(page=3, page_size=10)
        assert len(page3["items"]) == 5

        all_items = page1["items"] + page2["items"] + page3["items"]
        assert len(all_items) == 25
        seen = {item["cpu_pct"] for item in all_items}
        assert seen == set(range(25))

    def test_get_history_small_dataset(self, monkeypatch):
        service = _service(monkeypatch)
        self._populate_history(service, 3)

        result = service.get_history(page=1, page_size=50)
        assert result["total"] == 3
        assert len(result["items"]) == 3
        assert result["page_size"] == 50


class TestConfigEdgeCases:
    def test_collect_interval_empty_string(self, monkeypatch):
        net = SimpleNamespace(
            bytes_sent=100,
            bytes_recv=200,
            packets_sent=3,
            packets_recv=4,
            errin=0,
            errout=0,
            dropin=0,
            dropout=0,
        )
        mem = SimpleNamespace(
            total=8 * 1024**3,
            used=2 * 1024**3,
            available=6 * 1024**3,
            free=5 * 1024**3,
            percent=25.0,
        )
        swap = SimpleNamespace(total=1024, used=256, free=768, percent=25.0)
        disk = SimpleNamespace(total=1000, used=400, free=600, percent=40.0)
        freq = SimpleNamespace(current=2400.0, min=1200.0, max=3600.0)
        part = SimpleNamespace(device="disk0", mountpoint="/", fstype="ext4")

        def _net_io_counters():
            return net

        def _virtual_memory():
            return mem

        def _swap_memory():
            return swap

        def _disk_usage(path):
            return disk

        def _disk_partitions(all=False):
            return [part]

        def _cpu_percent(interval=0, percpu=False):
            return [1.0, 2.0] if percpu else 12.5

        def _cpu_count(logical=True):
            return 8 if logical else 4

        monkeypatch.setattr(system_services.psutil, "net_io_counters", _net_io_counters)
        monkeypatch.setattr(system_services.psutil, "virtual_memory", _virtual_memory)
        monkeypatch.setattr(system_services.psutil, "swap_memory", _swap_memory)
        monkeypatch.setattr(system_services.psutil, "disk_usage", _disk_usage)
        monkeypatch.setattr(system_services.psutil, "disk_partitions", _disk_partitions)
        monkeypatch.setattr(system_services.psutil, "cpu_percent", _cpu_percent)
        monkeypatch.setattr(system_services.psutil, "cpu_count", _cpu_count)
        monkeypatch.setattr(system_services.psutil, "cpu_freq", lambda: freq)
        monkeypatch.setattr(
            system_services.psutil, "getloadavg", lambda: (0.1, 0.2, 0.3)
        )
        monkeypatch.setattr(system_services.psutil, "pids", lambda: [1, 2])
        monkeypatch.setattr(system_services.psutil, "boot_time", lambda: 100.0)
        monkeypatch.setattr(system_services.time, "time", lambda: 200.0)

        container = MagicMock()
        container.get.return_value.get.return_value = ""
        service = SystemMonitorService(container)
        assert service._collect_interval == 10

    def test_collect_interval_invalid_string(self, monkeypatch):
        net = SimpleNamespace(
            bytes_sent=100,
            bytes_recv=200,
            packets_sent=3,
            packets_recv=4,
            errin=0,
            errout=0,
            dropin=0,
            dropout=0,
        )
        mem = SimpleNamespace(
            total=8 * 1024**3,
            used=2 * 1024**3,
            available=6 * 1024**3,
            free=5 * 1024**3,
            percent=25.0,
        )
        swap = SimpleNamespace(total=1024, used=256, free=768, percent=25.0)
        disk = SimpleNamespace(total=1000, used=400, free=600, percent=40.0)
        freq = SimpleNamespace(current=2400.0, min=1200.0, max=3600.0)
        part = SimpleNamespace(device="disk0", mountpoint="/", fstype="ext4")

        def _net_io_counters():
            return net

        def _virtual_memory():
            return mem

        def _swap_memory():
            return swap

        def _disk_usage(path):
            return disk

        def _disk_partitions(all=False):
            return [part]

        def _cpu_percent(interval=0, percpu=False):
            return [1.0, 2.0] if percpu else 12.5

        def _cpu_count(logical=True):
            return 8 if logical else 4

        monkeypatch.setattr(system_services.psutil, "net_io_counters", _net_io_counters)
        monkeypatch.setattr(system_services.psutil, "virtual_memory", _virtual_memory)
        monkeypatch.setattr(system_services.psutil, "swap_memory", _swap_memory)
        monkeypatch.setattr(system_services.psutil, "disk_usage", _disk_usage)
        monkeypatch.setattr(system_services.psutil, "disk_partitions", _disk_partitions)
        monkeypatch.setattr(system_services.psutil, "cpu_percent", _cpu_percent)
        monkeypatch.setattr(system_services.psutil, "cpu_count", _cpu_count)
        monkeypatch.setattr(system_services.psutil, "cpu_freq", lambda: freq)
        monkeypatch.setattr(
            system_services.psutil, "getloadavg", lambda: (0.1, 0.2, 0.3)
        )
        monkeypatch.setattr(system_services.psutil, "pids", lambda: [1, 2])
        monkeypatch.setattr(system_services.psutil, "boot_time", lambda: 100.0)
        monkeypatch.setattr(system_services.time, "time", lambda: 200.0)

        container = MagicMock()
        container.get.return_value.get.return_value = "abc"
        with pytest.raises(ValueError):
            SystemMonitorService(container)
