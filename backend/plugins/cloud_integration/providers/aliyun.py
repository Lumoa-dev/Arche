"""Aliyun ECS Cloud Provider — 阿里云 ECS 实例管理。

使用阿里云官方 SDK，通过 asyncio.to_thread 包装同步调用。
"""

from __future__ import annotations

import asyncio
import contextlib
import time

from backend.core.middleware import AppError

from .base import CloudProvider


def _run_sync(func, *args, **kwargs):
    """在后台线程中执行同步操作。"""
    return asyncio.to_thread(func, *args, **kwargs)


# 阿里云 ECS 实例规格到 GPU 的映射
GPU_INSTANCE_MAP = {
    "ecs.gn7i-c8g1.2xlarge": {"gpu_type": "A10", "gpu_count": 1},
    "ecs.gn7i-c16g1.4xlarge": {"gpu_type": "A10", "gpu_count": 2},
    "ecs.gn7-c16g1.4xlarge": {"gpu_type": "A100", "gpu_count": 1},
    "ecs.gn7-c32g1.8xlarge": {"gpu_type": "A100", "gpu_count": 2},
    "ecs.gn6v-c8g1.2xlarge": {"gpu_type": "V100", "gpu_count": 1},
    "ecs.gn6v-c16g1.4xlarge": {"gpu_type": "V100", "gpu_count": 2},
}

# 默认实例规格
DEFAULT_INSTANCE_TYPE = "ecs.gn7i-c8g1.2xlarge"


class AliyunProvider(CloudProvider):
    """阿里云 ECS Provider：通过 SDK 管理 GPU 实例生命周期。"""

    name = "aliyun"

    def __init__(self, credentials: dict | None = None):
        creds = credentials or {}
        self._access_key_id = creds.get("access_key_id", "")
        self._access_key_secret = creds.get("access_key_secret", "")
        self._region = creds.get("region", "cn-shanghai")
        self._security_group_id = creds.get("security_group_id", "")
        self._vswitch_id = creds.get("vswitch_id", "")
        self._image_id = creds.get("image_id", "")

        self._client = None
        self._instances: dict[str, dict] = {}

    def _get_client(self):
        """延迟初始化 AcsClient。"""
        if self._client is None:
            from aliyunsdkcore.client import AcsClient

            if not self._access_key_id or not self._access_key_secret:
                raise AppError(
                    "阿里云 AccessKey 未配置，请设置 ALIYUN_ACCESS_KEY_ID 和 ALIYUN_ACCESS_KEY_SECRET",  # noqa: E501
                    code="aliyun_credentials_missing",
                    status_code=500,
                )

            self._client = AcsClient(
                self._access_key_id,
                self._access_key_secret,
                self._region,
            )
        return self._client

    def _do_action(self, request):
        """发送请求并解析 JSON 响应。"""
        client = self._get_client()
        response = client.do_action_with_exception(request)
        import json

        if isinstance(response, bytes):
            return json.loads(response.decode("utf-8"))
        return json.loads(response) if response else {}

    async def create_instance(self, job_id: str, config: dict) -> dict:
        """创建 ECS GPU 实例。"""
        if not self._security_group_id or not self._vswitch_id or not self._image_id:
            raise AppError(
                "阿里云 ECS 创建失败：缺少必要配置（security_group_id / vswitch_id / image_id）",  # noqa: E501
                code="aliyun_config_missing",
                status_code=500,
            )

        instance_type = config.get("instance_type", DEFAULT_INSTANCE_TYPE)
        gpu_info = GPU_INSTANCE_MAP.get(
            instance_type, GPU_INSTANCE_MAP[DEFAULT_INSTANCE_TYPE]
        )

        from aliyunsdkecs.request.v20140526.RunInstancesRequest import (
            RunInstancesRequest,
        )

        request = RunInstancesRequest()
        request.set_accept_format("json")
        set_region = getattr(request, "set_RegionId", None)
        if set_region:
            set_region(self._region)
        request.set_ImageId(self._image_id)
        request.set_InstanceType(instance_type)
        request.set_SecurityGroupId(self._security_group_id)
        request.set_VSwitchId(self._vswitch_id)
        request.set_InstanceName(f"veil-{job_id[:8]}")
        request.set_Amount(1)
        request.set_InternetMaxBandwidthOut(5)
        request.set_Password(config.get("password", "VeilTemp123!"))

        result = await _run_sync(self._do_action, request)

        instance_id = (
            result.get("InstanceIdSets", {})
            .get("InstanceIdSet", [{}])[0]
            .get("InstanceId", "")
        )

        instance = {
            "instance_id": instance_id,
            "job_id": job_id,
            "status": "pending",
            "host": "",
            "port": 22,
            "user": "root",
            "gpu_type": gpu_info["gpu_type"],
            "gpu_count": gpu_info["gpu_count"],
            "created_at": time.time(),
            "started_at": None,
            "stopped_at": None,
        }
        self._instances[instance_id] = instance
        return instance

    async def start_instance(self, instance_id: str) -> dict:
        """启动 ECS 实例。"""
        from aliyunsdkecs.request.v20140526.StartInstanceRequest import (
            StartInstanceRequest,
        )

        request = StartInstanceRequest()
        request.set_accept_format("json")
        request.set_InstanceId(instance_id)

        await _run_sync(self._do_action, request)

        instance = self._instances.get(instance_id)
        if instance:
            instance["status"] = "running"
            instance["started_at"] = time.time()

        return instance or {"instance_id": instance_id, "status": "running"}

    async def stop_instance(self, instance_id: str) -> dict:
        """停止 ECS 实例。"""
        from aliyunsdkecs.request.v20140526.StopInstanceRequest import (
            StopInstanceRequest,
        )

        request = StopInstanceRequest()
        request.set_accept_format("json")
        request.set_InstanceId(instance_id)

        await _run_sync(self._do_action, request)

        instance = self._instances.get(instance_id)
        if instance:
            instance["status"] = "stopped"
            instance["stopped_at"] = time.time()

        return instance or {"instance_id": instance_id, "status": "stopped"}

    async def delete_instance(self, instance_id: str) -> None:
        """释放 ECS 实例。"""
        from aliyunsdkecs.request.v20140526.DeleteInstanceRequest import (
            DeleteInstanceRequest,
        )

        request = DeleteInstanceRequest()
        request.set_accept_format("json")
        request.set_InstanceId(instance_id)

        with contextlib.suppress(Exception):
            await _run_sync(self._do_action, request)
        self._instances.pop(instance_id, None)

    async def get_instance_status(self, instance_id: str) -> dict:
        """获取 ECS 实例状态。"""
        from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import (
            DescribeInstancesRequest,
        )

        request = DescribeInstancesRequest()
        request.set_accept_format("json")
        request.set_InstanceIds([instance_id])

        try:
            result = await _run_sync(self._do_action, request)
            instances = result.get("Instances", {}).get("Instance", [])
            if instances:
                aliyun_status = instances[0].get("Status", "Stopped")
                status_map = {
                    "Running": "running",
                    "Stopped": "stopped",
                    "Pending": "pending",
                }
                aliyun_status = status_map.get(aliyun_status, "stopped")

                instance = self._instances.get(instance_id)
                if instance:
                    instance["status"] = aliyun_status
                    if aliyun_status == "running" and not instance.get("host"):
                        instance["host"] = (
                            instances[0]
                            .get("PublicIpAddress", {})
                            .get("IpAddress", [""])[0]
                        )
                        if not instance["host"]:
                            eips = instances[0].get("EipAddress", {})
                            instance["host"] = eips.get("IpAddress", "")

                return {
                    "status": aliyun_status,
                    "gpu_util": 0.0,
                    "mem_used": 0,
                    "mem_total": 40960,
                    "temperature": 0.0,
                    "uptime_seconds": 0,
                }
        except Exception:
            pass

        return {
            "status": "unknown",
            "gpu_util": 0.0,
            "mem_used": 0,
            "mem_total": 40960,
            "temperature": 0.0,
            "uptime_seconds": 0,
        }

    async def get_gpu_metrics(self, instance_id: str) -> dict:
        """获取 GPU 指标。

        MVP 阶段返回默认值。真实 GPU 利用率需 SSH 到实例执行 nvidia-smi。
        """
        status = await self.get_instance_status(instance_id)
        if status["status"] != "running":
            return {
                "utilization_pct": 0.0,
                "memory_used_mb": 0,
                "memory_total_mb": 40960,
                "temperature_c": 0.0,
            }

        return {
            "utilization_pct": 0.0,
            "memory_used_mb": 0,
            "memory_total_mb": 40960,
            "temperature_c": 0.0,
        }

    async def get_cost(self, instance_id: str, start: str, end: str) -> float:
        """计算运行费用。复用 cost calculator 中的阿里云定价表。"""
        from ..cost import calculator

        instance = self._instances.get(instance_id)
        if not instance:
            return 0.0

        gpu_type = instance.get("gpu_type", "A100")
        rate = calculator.calculate_rate("aliyun", gpu_type)

        try:
            start_ts = float(start)
            end_ts = float(end)
            hours = (end_ts - start_ts) / 3600
        except (ValueError, TypeError):
            hours = 1.0

        return round(max(hours, 0) * rate, 2)
