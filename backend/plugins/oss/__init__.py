"""对象存储插件 —— 文件存储插件：流式读写、后端解耦、动态配额、限速、冷热分层。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.config import config_manager
from backend.core.plugin_registry import registry
from backend.plugins.oss.settings import OssSettings

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer

# 导入模型、路由、服务，确保在 create_all 前注册
from backend.plugins.oss.models import OSSFile, UserOSSQuota  # noqa: F401
from backend.plugins.oss.rate_limiter import RateLimiterManager
from backend.plugins.oss.routes import router
from backend.plugins.oss.services import StorageService

logger = logging.getLogger(__name__)


class OSSPlugin(BasePlugin):
    name = "oss"
    version = "0.2.0"
    optional = ["auth"]  # noqa: RUF012

    def __init__(self):
        self._eviction_job = None
        self._rate_limiter = None

    def setup(self, app: FastAPI) -> None:
        """注册路由。"""
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        """注册限速器 + StorageService 到容器。"""
        # 注册限速器
        config = container.get("config")
        global_rate = int(
            config.get("OSS_GLOBAL_RATE_LIMIT_BYTES", str(10 * 1024 * 1024))
        )
        rate_limiter = RateLimiterManager(global_rate=global_rate)

        def _oss_rate_limiter_factory(c):  # noqa: ARG001
            return rate_limiter

        container.register("oss_rate_limiter", _oss_rate_limiter_factory)
        self._rate_limiter = rate_limiter

        # 注册 StorageService（内部依赖 rate_limiter）
        container.register("storage", lambda c: StorageService(c))

    def on_startup(self) -> None:
        """启动冷热分层调度定时任务。"""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.interval import IntervalTrigger

            scheduler = AsyncIOScheduler()

            async def _evict():
                storage_service = self._get_service()
                if storage_service:
                    count = await storage_service.evict_cold_files(days=7)
                    if count > 0:
                        logger.info(f"[OSS] 冷热迁移: {count} 个文件已推到阿里云")

            scheduler.add_job(
                _evict,
                trigger=IntervalTrigger(hours=1),
                id="oss_cold_eviction",
                name="OSS 冷热分层迁移",
                replace_existing=True,
            )
            scheduler.start()
            self._eviction_job = scheduler
        except Exception as e:
            logger.warning(f"[OSS] APScheduler 启动失败: {e}")

    def on_shutdown(self) -> None:
        """关闭时停止调度器。"""
        if self._eviction_job and getattr(self._eviction_job, "running", False):
            self._eviction_job.shutdown(wait=False)

    def _cleanup_temp_files(self) -> None:
        """清理 /tmp/veil_oss/ 残留临时文件。"""
        import tempfile

        tmp_dir = Path(tempfile.gettempdir()) / "veil_oss"
        if tmp_dir.exists():
            import shutil

            try:
                shutil.rmtree(tmp_dir)
                logger.info(f"[OSS] 已清理临时目录 {tmp_dir}")
            except Exception as e:
                logger.warning(f"[OSS] 清理临时目录失败: {e}")

    def _get_service(self) -> StorageService | None:
        """获取 StorageService 实例。"""
        try:
            from backend.core.container import container as global_container

            return global_container.get("storage")
        except Exception:
            return None


# 注册插件配置
config_manager.register_plugin_settings("oss", OssSettings)

# 自注册
plugin = OSSPlugin()
registry.register("oss", plugin)
