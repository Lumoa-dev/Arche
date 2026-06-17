"""请求日志插件 —— 结构化 IP 请求日志记录、聚合与查询。

提供：
- RequestLogMiddleware：每个请求经过时记录明细
- IpActionCounter 聚合表：按 IP + 行为分类 + 时间窗口聚合计数
- APScheduler 定时任务：归并聚合 + 明细 TTL 清理
- REST API：IP 行为查询、TOP IP、异常趋势
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base_plugin import BasePlugin
from backend.core.plugin_registry import registry
from backend.plugins.request_log.models import IpActionCounter, RequestLog  # noqa: F401
from backend.plugins.request_log.routes import router

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.core.container import ServiceContainer


class RequestLogPlugin(BasePlugin):
    name = "request_log"
    version = "0.1.0"
    optional = ["auth"]  # noqa: RUF012

    def setup(self, app: FastAPI) -> None:
        from backend.plugins.request_log.services import RequestLogMiddleware

        app.add_middleware(RequestLogMiddleware)
        app.include_router(router)

    def register_services(self, container: ServiceContainer) -> None:
        from backend.plugins.request_log.services import LogAggregationService

        svc = LogAggregationService()

        def _factory(_container):
            return svc

        container.register("request_log", _factory)

    def on_startup(self):
        from backend.plugins.request_log.services import LogAggregationService

        container = __import__(
            "backend.core.container", fromlist=["container"]
        ).container
        svc = container.get("request_log")
        if isinstance(svc, LogAggregationService):
            svc.start()

    def on_shutdown(self):
        from backend.plugins.request_log.services import LogAggregationService

        container = __import__(
            "backend.core.container", fromlist=["container"]
        ).container
        if container.is_available("request_log"):
            svc = container.get("request_log")
            if isinstance(svc, LogAggregationService):
                svc.stop()


plugin = RequestLogPlugin()
registry.register("request_log", plugin)
