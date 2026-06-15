"""GitHub 代理插件 —— GitHub API 反向代理插件。

负责代理 GitHub API 和静态资源，支持缓存和 Token 注入。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.config import config_manager
from backend.core.plugin_registry import registry
from backend.plugins.github_proxy.settings import GitHubProxySettings

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer

from backend.plugins.github_proxy.routes import router
from backend.plugins.github_proxy.services import GitHubService


class GithubProxyPlugin(BasePlugin):
    name = "github_proxy"
    version = "0.1.0"
    requires = None
    optional = None

    def __init__(self):
        self._app = None

    def setup(self, app: FastAPI) -> None:
        """注册路由。"""
        self._app = app
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        """注册 GitHubService 到容器。"""
        # 注册统一门面服务（主要使用这个）
        container.register("github", lambda c: GitHubService(c))
        # 也保留原服务名，兼容旧代码
        container.register("github_proxy", lambda c: GitHubService(c))

    def on_startup(self) -> None:
        """启动时检查 GitHub CLI 是否可用。"""
        import asyncio
        import logging

        logger = logging.getLogger(__name__)

        async def _check_gh_cli():
            try:
                proc = await asyncio.create_subprocess_exec(
                    "gh",
                    "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                if proc.returncode == 0:
                    version = stdout.decode().split("\n")[0].strip()
                    logger.info(f"[GitHub] CLI 可用: {version}")
                    return True
            except FileNotFoundError:
                logger.warning("[GitHub] CLI 未安装，CLI 模式不可用")
            except Exception as e:
                logger.warning(f"[GitHub] CLI 检查失败: {e}")
            return False

        # 后台检查，不阻塞启动
        asyncio.create_task(_check_gh_cli())  # noqa: RUF006

    def on_shutdown(self) -> None:
        pass


# 注册插件配置
config_manager.register_plugin_settings("github_proxy", GitHubProxySettings)

# 自注册
plugin = GithubProxyPlugin()
registry.register("github_proxy", plugin)
