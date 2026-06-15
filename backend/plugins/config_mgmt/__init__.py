"""配置管理插件 — 导入核心模型确保注册，提供管理 API 路由。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.models import ConfigEntry  # noqa: F401 — 确保模型注册到 Base.metadata
from backend.core.plugin_registry import registry
from backend.plugins.config_mgmt.routes import router

if TYPE_CHECKING:
    from backend.core.container import ServiceContainer


class ConfigMgmtPlugin(BasePlugin):
    name = "config_mgmt"
    requires = None

    def setup(self, app) -> None:
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        pass

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass


registry.register("config_mgmt", ConfigMgmtPlugin())
