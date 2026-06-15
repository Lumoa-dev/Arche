"""模拟云训练 Provider —— 模拟本地开发环境的实例生命周期。"""

from __future__ import annotations

import asyncio
import random
import time
import uuid

from .base import CloudProvider

# Mock 定价（元/小时）
MOCK_PRICING = {
    "A100": 15.0,
    "H100": 25.0,
    "V100": 8.0,
    "RTX4090": 5.0,
    "default": 10.0,
}


class MockProvider(CloudProvider):
    """Mock Provider：用 asyncio.sleep 模拟实例操作，随机数模拟 GPU 指标。"""

    name = "mock"

    def __init__(self, credentials: dict | None = None):  # noqa: ARG002
        self._instances: dict[str, dict] = {}

    def _get_rate(self, gpu_type: str) -> float:
        return MOCK_PRICING.get(gpu_type, MOCK_PRICING["default"])

    async def create_instance(self, job_id: str, config: dict) -> dict:
        await asyncio.sleep(0.1)  # 模拟创建延迟

        gpu_type = config.get("gpu_type", "A100")
        instance_id = f"mock-{uuid.uuid4().hex[:8]}"

        instance = {
            "instance_id": instance_id,
            "job_id": job_id,
            "status": "pending",
            "host": "127.0.0.1",
            "port": 22,
            "user": "mock",
            "gpu_type": gpu_type,
            "gpu_count": config.get("gpu_count", 1),
            "created_at": time.time(),
            "started_at": None,
            "stopped_at": None,
        }
        self._instances[instance_id] = instance
        return instance

    async def start_instance(self, instance_id: str) -> dict:
        await asyncio.sleep(0.1)
        instance = self._instances.get(instance_id)
        if not instance:
            raise RuntimeError(f"实例 {instance_id} 不存在")
        instance["status"] = "running"
        instance["started_at"] = time.time()
        return instance

    async def stop_instance(self, instance_id: str) -> dict:
        await asyncio.sleep(0.1)
        instance = self._instances.get(instance_id)
        if not instance:
            raise RuntimeError(f"实例 {instance_id} 不存在")
        instance["status"] = "stopped"
        instance["stopped_at"] = time.time()
        return instance

    async def delete_instance(self, instance_id: str) -> None:
        await asyncio.sleep(0.05)
        self._instances.pop(instance_id, None)

    async def get_instance_status(self, instance_id: str) -> dict:
        instance = self._instances.get(instance_id)
        if not instance:
            raise RuntimeError(f"实例 {instance_id} 不存在")

        uptime = 0
        if instance["started_at"]:
            end = instance["stopped_at"] or time.time()
            uptime = end - instance["started_at"]

        return {
            "status": instance["status"],
            "gpu_util": random.uniform(60, 98)
            if instance["status"] == "running"
            else 0,
            "mem_used": random.randint(8000, 16000)
            if instance["status"] == "running"
            else 0,
            "mem_total": 40960,
            "temperature": random.uniform(45, 80)
            if instance["status"] == "running"
            else 25,
            "uptime_seconds": uptime,
        }

    async def get_gpu_metrics(self, instance_id: str) -> dict:
        status = await self.get_instance_status(instance_id)
        return {
            "utilization_pct": status["gpu_util"],
            "memory_used_mb": status["mem_used"],
            "memory_total_mb": status["mem_total"],
            "temperature_c": status["temperature"],
        }

    async def get_cost(self, instance_id: str, start: str, end: str) -> float:  # noqa: ARG002
        instance = self._instances.get(instance_id)
        if not instance:
            return 0.0

        rate = self._get_rate(instance["gpu_type"])
        started = instance["started_at"] or time.time()
        stopped = instance["stopped_at"] or time.time()
        hours = (stopped - started) / 3600
        return round(hours * rate, 2)
