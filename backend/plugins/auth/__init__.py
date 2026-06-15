"""认证插件 —— 认证与等级权限插件。

负责用户注册/登录/JWT 认证，以及中间件装配。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.plugin_registry import registry

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer

# 导入模型，确保在 create_all 前注册到 Base
from backend.plugins.auth.middleware import AuthMiddleware
from backend.plugins.auth.models import User  # noqa: F401
from backend.plugins.auth.routes import router
from backend.plugins.auth.services import AuthService


class AuthPlugin(BasePlugin):
    name = "auth"
    version = "0.1.0"

    def __init__(self):
        self._app = None

    def setup(self, app: FastAPI) -> None:
        """注册路由，保存 app 引用供后续中间件挂载。"""
        self._app = app
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        """注册 AuthService 到容器，并挂载 JWT 认证中间件。"""
        # 注册认证服务
        container.register("auth", lambda c: AuthService(c))

        # 注册在线会话追踪器
        from backend.plugins.auth.session import UserSessionTracker

        container.register("session_tracker", lambda c: UserSessionTracker(c))

        # 挂载 JWT 中间件（需要 SECRET_KEY）
        secret_key = container.get("config").get_required("SECRET_KEY")
        if self._app:
            self._app.add_middleware(AuthMiddleware, secret_key=secret_key)

    def on_startup(self) -> None:
        """启动在线会话清理任务。"""
        from backend.core.container import container as global_container

        try:
            if global_container.is_available("session_tracker"):
                tracker = global_container.get("session_tracker")
                tracker.start_cleanup()
        except Exception:
            pass


# 自注册
plugin = AuthPlugin()
registry.register("auth", plugin)
