"""部署 Webhook 插件 —— 接收 CI/CD 触发器 POST 请求，执行部署脚本。"""

from __future__ import annotations

import asyncio
import subprocess
from typing import TYPE_CHECKING

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.base_plugin import BasePlugin
from backend.core.config import config_manager
from backend.core.middleware import AppError, AuthError
from backend.core.plugin_registry import registry
from backend.plugins.deploy_webhook.settings import DeployWebhookSettings

if TYPE_CHECKING:
    from fastapi import FastAPI


class DeployRequest(BaseModel):
    token: str


# 注册插件配置
config_manager.register_plugin_settings("deploy_webhook", DeployWebhookSettings)

router = APIRouter()


def _get_deploy_script() -> str:
    """获取部署脚本路径。"""
    path = config_manager.get("DEPLOY_SCRIPT", "/home/admin/arche/deploy.sh")
    return path if path is not None else "/home/admin/arche/deploy.sh"


def _run_script() -> tuple[int, str, str]:
    """执行部署脚本。返回 (returncode, stdout, stderr)。"""
    deploy_script = _get_deploy_script()
    proc = subprocess.run(
        ["bash", deploy_script],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.returncode, proc.stdout, proc.stderr


@router.post("/api/deploy")
async def trigger_deploy(request: DeployRequest):
    deploy_token = config_manager.get("DEPLOY_TOKEN", "")
    if not deploy_token or request.token != deploy_token:
        raise AuthError(message="Invalid deploy token")

    deploy_script = _get_deploy_script()
    import os

    if not os.path.isfile(deploy_script):
        raise AppError(
            f"Deploy script not found at {deploy_script}",
            code="deploy_script_not_found",
            status_code=500,
        )

    returncode, stdout, stderr = await asyncio.to_thread(_run_script)

    if returncode != 0:
        return {
            "status": "failed",
            "returncode": returncode,
            "stdout": stdout[-2000:],
            "stderr": stderr[-1000:],
        }

    return {
        "status": "success",
        "stdout": stdout[-2000:],
    }


class DeployWebhookPlugin(BasePlugin):
    name = "deploy_webhook"
    version = "0.1.0"

    def setup(self, app: FastAPI) -> None:
        app.include_router(router)


plugin = DeployWebhookPlugin()
registry.register("deploy_webhook", plugin)
