"""系统监控全链路集成测试。

Mock 边界：psutil 模块（系统调用，外部依赖）。
不 mock SystemMonitorService 或其任何内部方法。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.plugins.system_monitor.services import SystemMonitorService
from backend.tests.conftest import patch_container_service


def _make_psutil_mocks():
    """创建一组模拟的 psutil 返回值。"""
    # virtual_memory
    mem_mock = MagicMock()
    mem_mock.total = 16 * 1024**3
    mem_mock.used = 8 * 1024**3
    mem_mock.available = 8 * 1024**3
    mem_mock.free = 8 * 1024**3
    mem_mock.percent = 50.0

    # swap_memory
    swap_mock = MagicMock()
    swap_mock.total = 2 * 1024**3
    swap_mock.used = 512 * 1024**2
    swap_mock.free = 1536 * 1024**2
    swap_mock.percent = 25.0

    # disk_usage
    disk_mock = MagicMock()
    disk_mock.total = 500 * 1024**3
    disk_mock.used = 250 * 1024**3
    disk_mock.free = 250 * 1024**3
    disk_mock.percent = 50.0

    # cpu_freq
    freq_mock = MagicMock()
    freq_mock.current = 2500.0
    freq_mock.min = 800.0
    freq_mock.max = 5000.0

    # net_io_counters
    net_mock = MagicMock()
    net_mock.bytes_sent = 10000
    net_mock.bytes_recv = 20000
    net_mock.packets_sent = 100
    net_mock.packets_recv = 200
    net_mock.errin = 0
    net_mock.errout = 0
    net_mock.dropin = 0
    net_mock.dropout = 0

    return mem_mock, swap_mock, disk_mock, freq_mock, net_mock


@pytest.fixture
def mock_psutil():
    """Mock psutil 模块的所有系统调用。"""
    mem_mock, swap_mock, disk_mock, freq_mock, net_mock = _make_psutil_mocks()

    patcher = patch.multiple(
        "backend.plugins.system_monitor.services.psutil",
        cpu_percent=MagicMock(return_value=12.5),
        cpu_count=MagicMock(return_value=8),
        cpu_freq=MagicMock(return_value=freq_mock),
        virtual_memory=MagicMock(return_value=mem_mock),
        swap_memory=MagicMock(return_value=swap_mock),
        disk_usage=MagicMock(return_value=disk_mock),
        disk_partitions=MagicMock(return_value=[]),
        net_io_counters=MagicMock(return_value=net_mock),
        pids=MagicMock(return_value=[1, 2, 3, 4, 5]),
        boot_time=MagicMock(return_value=1000000.0),
        getloadavg=MagicMock(return_value=(0.5, 0.3, 0.1)),
        process_iter=MagicMock(return_value=[]),
    )
    patcher.start()
    yield
    patcher.stop()


@pytest.fixture
async def system_monitor_service(db_container, mock_psutil):
    """创建真实的 SystemMonitorService 实例并注入容器。"""
    svc = SystemMonitorService(db_container)
    patch_container_service(db_container, "system_monitor", svc)
    return svc


@pytest.mark.asyncio
class TestSystemMonitorAPI:
    """系统监控 API 全链路集成测试。"""

    async def test_unauthenticated_returns_401(self, client):
        """未登录访问系统监控应返回 401。"""
        response = await client.get("/api/system/summary")
        assert response.status_code == 401

    async def test_system_summary(self, client, admin_headers, system_monitor_service):
        """系统概览接口应返回所有关键指标。"""
        response = await client.get("/api/system/summary", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        summary = data["data"]
        assert summary["cpu_percent"] == 12.5
        assert summary["cpu_count"] == 8
        assert summary["memory_percent"] == 50.0
        assert summary["disk_percent"] == 50.0
        assert summary["process_count"] == 5
        assert "python_version" in summary
        assert "platform" in summary
        assert "load_1" in summary

    async def test_cpu_detail(self, client, admin_headers, system_monitor_service):
        """CPU 详情接口。"""
        response = await client.get("/api/system/cpu", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        cpu = data["data"]
        assert cpu["count_logical"] == 8
        assert cpu["freq_current"] == 2500.0
        assert "load_1" in cpu

    async def test_memory_detail(self, client, admin_headers, system_monitor_service):
        """内存详情接口。"""
        response = await client.get("/api/system/memory", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        mem = data["data"]
        assert mem["percent"] == 50.0
        assert mem["total"] == 16 * 1024**3
        assert "swap_percent" in mem

    async def test_disk_detail(self, client, admin_headers, system_monitor_service):
        """磁盘详情接口。"""
        response = await client.get("/api/system/disk", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        disk = data["data"]
        assert disk["root_percent"] == 50.0
        assert disk["partitions"] == []

    async def test_network_io(self, client, admin_headers, system_monitor_service):
        """网络 I/O 接口。"""
        response = await client.get("/api/system/network", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        net = data["data"]
        assert net["bytes_sent"] == 10000
        assert net["bytes_recv"] == 20000
        assert "packets_sent" in net

    async def test_history_records(self, client, admin_headers, system_monitor_service):
        """历史记录接口应返回空历史。"""
        response = await client.get(
            "/api/system/history",
            params={"page": 1, "page_size": 10},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        history = data["data"]
        assert history["total"] == 0
        assert history["items"] == []

    async def test_进程列表(self, client, admin_headers, system_monitor_service):
        """进程列表接口应返回空列表。"""
        response = await client.get(
            "/api/system/processes",
            params={"sort_by": "pid", "limit": 5},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        procs = data["data"]
        assert procs["total"] == 0
        assert procs["items"] == []
