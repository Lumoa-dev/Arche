"""博客插件 —— 博客内容发布、浏览、互动插件。

负责帖子 CRUD、评论、点赞、审核、举报。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.config import config_manager
from backend.core.plugin_registry import registry
from backend.plugins.blog.settings import BlogSettings

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer

# 导入模型，确保在 create_all 前注册到 Base
from backend.plugins.blog.models import (  # noqa: F401
    BlogComment,
    BlogLike,
    BlogPost,
    BlogPostTag,
    BlogReport,
    BlogTag,
)
from backend.plugins.blog.routes import router
from backend.plugins.blog.services import BlogService


class BlogPlugin(BasePlugin):
    name = "blog"
    version = "0.1.0"
    requires = ["auth", "oss"]  # noqa: RUF012
    optional = ["auth"]  # noqa: RUF012

    def __init__(self):
        self._app = None

    def setup(self, app: FastAPI) -> None:
        """注册路由。"""
        self._app = app
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        """注册 BlogService 到容器。"""
        container.register("blog", lambda c: BlogService(c))

    def on_startup(self) -> None:
        """启动时初始化敏感词过滤器。"""
        from backend.plugins.blog.sensitive_words import init_filter

        # 从容器获取配置
        # 延迟导入避免循环
        try:
            from backend.core.container import container as global_container

            config = global_container.get("config")
            words_str = config.get("SENSITIVE_WORDS", "")
            words = (
                [w.strip() for w in words_str.split(",") if w.strip()]
                if words_str
                else []
            )
            init_filter(words)
        except Exception:
            init_filter([])

    def on_shutdown(self) -> None:
        pass


# 注册插件配置
config_manager.register_plugin_settings("blog", BlogSettings)

# 自注册
plugin = BlogPlugin()
registry.register("blog", plugin)
