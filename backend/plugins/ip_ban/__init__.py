"""IP 封禁插件。

负责 IP/CIDR封禁管理、自动封禁规则引擎、请求拦截中间件。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.plugin_registry import registry

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer

# 导入模型，确保在 create_all 前注册到 Base
from backend.plugins.ip_ban.middleware import IpBanMiddleware
from backend.plugins.ip_ban.models import (  # noqa: F401
    AutoBanRuleConfig,
    IpBan,
    IpBanLog,
)
from backend.plugins.ip_ban.routes import router
from backend.plugins.ip_ban.services import IpBanService


class IpBanPlugin(BasePlugin):
    name = "ip_ban"
    version = "0.1.0"

    def __init__(self):
        self._app = None

    def setup(self, app: FastAPI) -> None:
        self._app = app
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        container.register("ip_ban", lambda c: IpBanService(c))

        if self._app:
            self._app.add_middleware(IpBanMiddleware)


plugin = IpBanPlugin()
registry.register("ip_ban", plugin)
