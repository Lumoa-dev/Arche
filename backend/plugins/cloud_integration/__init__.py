"""云集成插件 —— 云训练插件。

负责 ML 模型训练任务的管理：创建、启动、停止、监控。
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.config import config_manager
from backend.core.plugin_registry import registry
from backend.plugins.cloud_integration.settings import CloudIntegrationSettings

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer

# 导入模型，确保在 create_all 前注册到 Base
from backend.plugins.cloud_integration.models import (
    TrainingCost as TrainingCost,
)
from backend.plugins.cloud_integration.models import (
    TrainingInstance as TrainingInstance,
)
from backend.plugins.cloud_integration.models import (
    TrainingJob as TrainingJob,
)
from backend.plugins.cloud_integration.models import (
    TrainingTaskStep as TrainingTaskStep,
)
from backend.plugins.cloud_integration.orchestrator import TrainingOrchestrator
from backend.plugins.cloud_integration.routes import router
from backend.plugins.cloud_integration.services import CloudTrainingService

# 全局引用，用于 on_shutdown
_orchestrator_ref = None
logger = logging.getLogger(__name__)


class CloudIntegrationPlugin(BasePlugin):
    name = "cloud_integration"
    version = "0.1.0"

    def __init__(self):
        self._app = None

    def setup(self, app: FastAPI) -> None:
        """注册路由。"""
        self._app = app
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        """注册 CloudTrainingService 和 TrainingOrchestrator 到容器。"""
        container.register("cloud_training", lambda c: CloudTrainingService(c))
        container.register("cloud_orchestrator", lambda c: TrainingOrchestrator(c))

    def on_startup(self) -> None:
        """启动训练任务编排守护进程。"""
        global _orchestrator_ref
        try:
            from backend.core.container import container as global_container

            orchestrator = global_container.get("cloud_orchestrator")
            if orchestrator:
                _orchestrator_ref = orchestrator
                loop = asyncio.get_running_loop()
                task = loop.create_task(orchestrator.start())

                def _log_error(fut: asyncio.Task) -> None:
                    exc = fut.exception()
                    if exc:
                        logger.error("编排器启动失败: %s", exc)

                task.add_done_callback(_log_error)
        except RuntimeError:
            logger.warning("没有运行中的事件循环，编排器推迟到异步上下文中启动")
        except Exception:
            logger.exception("编排器启动异常")

    def on_shutdown(self) -> None:
        """停止训练任务编排守护进程。"""
        global _orchestrator_ref
        if _orchestrator_ref:
            try:
                loop = asyncio.get_running_loop()
                if loop.is_closed():
                    logger.warning("事件循环已关闭，跳过编排器停止")
                    _orchestrator_ref = None
                    return
                task = loop.create_task(_orchestrator_ref.stop())

                def _log_error(fut: asyncio.Task) -> None:
                    exc = fut.exception()
                    if exc:
                        logger.error("编排器停止失败: %s", exc)

                task.add_done_callback(_log_error)
            except RuntimeError:
                logger.warning("没有运行中的事件循环，跳过编排器停止")
            finally:
                _orchestrator_ref = None


# 注册插件配置
config_manager.register_plugin_settings("cloud_integration", CloudIntegrationSettings)

# 自注册
plugin = CloudIntegrationPlugin()
registry.register("cloud_integration", plugin)
