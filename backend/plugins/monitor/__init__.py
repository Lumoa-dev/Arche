"""监控插件 —— 监控大屏插件。

提供监控模板的 CRUD API。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.plugin_registry import registry
from backend.plugins.monitor.routes import router

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer


class MonitorPlugin(BasePlugin):
    name = "monitor"
    version = "0.1.0"
    optional = ["system_monitor"]  # noqa: RUF012

    def setup(self, app: FastAPI) -> None:
        """注册路由。"""
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        """注册服务。"""
        pass


# 自注册
plugin = MonitorPlugin()
registry.register("monitor", plugin)
