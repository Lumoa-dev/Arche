"""monitor 插件初始化测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.routing import APIRoute

from backend.plugins.monitor import MonitorPlugin


class TestMonitorPlugin:
    def test_setup_registers_routes(self):
        app = FastAPI()
        plugin = MonitorPlugin()
        plugin.setup(app)
        paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
        assert "/api/monitor/templates" in paths
        assert "/api/monitor/components/{component_id}/data" in paths

    def test_register_services_noop(self):
        plugin = MonitorPlugin()
        plugin.register_services(container=MagicMock())
