"""资产管理插件 —— 统一资产管理插件。

负责跨插件查询用户资产（文件、文章、爬虫结果、训练任务），
提供统一目录、搜索、统计功能。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.plugin_registry import registry

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer

# 导入模型，确保在 create_all 前注册到 Base
from backend.plugins.asset_mgmt.models import AssetIndex  # noqa: F401
from backend.plugins.asset_mgmt.routes import router
from backend.plugins.asset_mgmt.services import AssetMgmtService


class AssetMgmtPlugin(BasePlugin):
    name = "asset_mgmt"
    version = "0.1.0"

    def __init__(self):
        self._app = None

    def setup(self, app: FastAPI) -> None:
        """注册路由。"""
        self._app = app
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        """注册 AssetMgmtService 到容器。"""
        container.register("asset_mgmt", lambda c: AssetMgmtService(c))

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass


# 自注册
plugin = AssetMgmtPlugin()
registry.register("asset_mgmt", plugin)
