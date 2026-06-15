"""BasePlugin —— 所有插件必须实现的抽象接口。"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

    from .container import ServiceContainer


class BasePlugin(ABC):
    name: str = ""
    version: str = "0.1.0"
    requires: list[str] = []  # noqa: RUF012  # 硬依赖，没有就启动失败
    optional: list[str] = []  # noqa: RUF012  # 软依赖，没有就优雅降级

    @abstractmethod
    def setup(self, app: "FastAPI") -> None:
        """注册路由、中间件等。"""
        ...

    def register_services(self, container: "ServiceContainer") -> None:  # noqa: B027
        """可选：注册服务到容器。"""
        pass

    def on_startup(self) -> Awaitable[None] | None:
        """可选：启动后钩子；可改为 async def，由注册表 await。"""
        return None

    def on_shutdown(self) -> None:  # noqa: B027
        """可选：关闭前钩子。"""
        pass
