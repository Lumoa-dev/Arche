"""云集成插件 —— 云训练插件。

负责 ML 模型训练任务的管理：创建、启动、停止、监控。
"""

from __future__ import annotations

import asyncio
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
                loop.create_task(orchestrator.start())  # noqa: RUF006
        except RuntimeError:
            pass

    def on_shutdown(self) -> None:
        """停止训练任务编排守护进程。"""
        global _orchestrator_ref
        if _orchestrator_ref:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_orchestrator_ref.stop())  # noqa: RUF006
            except RuntimeError:
                pass


# 注册插件配置
config_manager.register_plugin_settings("cloud_integration", CloudIntegrationSettings)

# 自注册
plugin = CloudIntegrationPlugin()
registry.register("cloud_integration", plugin)
