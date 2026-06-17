"""统一搜索插件 —— 全局搜索建议接口。

提供 /api/search/suggestions 端点，支持按前缀分类搜索和多表模糊匹配。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.plugin_registry import registry

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer

from backend.plugins.search.routes import router
from backend.plugins.search.services import SearchService


class SearchPlugin(BasePlugin):
    name = "search"
    version = "0.1.0"
    optional = ["auth"]  # noqa: RUF012

    def __init__(self):
        self._app = None

    def setup(self, app: FastAPI) -> None:
        self._app = app
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        container.register("search", lambda c: SearchService(c))


# 自注册
plugin = SearchPlugin()
registry.register("search", plugin)
