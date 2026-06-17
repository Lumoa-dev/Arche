"""系统监控插件 —— 系统资源监控插件。

采集 CPU/内存/磁盘/网络等系统指标，APScheduler 定时采样，内存循环缓冲。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.config import config_manager
from backend.core.plugin_registry import registry
from backend.plugins.system_monitor.settings import SystemMonitorSettings

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer

from backend.plugins.system_monitor.routes import router
from backend.plugins.system_monitor.services import SystemMonitorService


class SystemMonitorPlugin(BasePlugin):
    name = "system_monitor"
    version = "0.1.0"
    optional = ["auth"]  # noqa: RUF012

    def __init__(self):
        self._app = None

    def setup(self, app: FastAPI) -> None:
        self._app = app
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        container.register("system_monitor", lambda c: SystemMonitorService(c))
        # 注册 API 请求统计追踪器
        from backend.plugins.system_monitor.stats import RequestStatsTracker

        container.register("request_stats", lambda c: RequestStatsTracker(c))

    def on_startup(self) -> None:
        """启动系统监控采集任务。"""
        if not self._app:
            return
        container = self._app.state.container
        if container.is_available("system_monitor"):
            svc = container.get("system_monitor")
            svc.start_collection()

    def on_shutdown(self) -> None:
        if not self._app:
            return
        container = self._app.state.container
        if container.is_available("system_monitor"):
            svc = container.get("system_monitor")
            svc.stop_collection()


# 注册插件配置
config_manager.register_plugin_settings("system_monitor", SystemMonitorSettings)

plugin = SystemMonitorPlugin()
registry.register("system_monitor", plugin)
