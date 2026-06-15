"""Zhixingyun Cloud Provider — 智星云 GPU 实例管理。

通过智星云 OpenAPI 管理 GPU 实例生命周期：创建、启动、停止、释放。
签名算法：timestamp+nonce+MD5，参考 docs/zhixingyun_api/03_接口签名.md。
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import time

import httpx

from backend.core.middleware import AppError

from .base import CloudProvider

BASE_URL = "https://app.ai-galaxy.cn/openapi/v2"

# 智星云状态 → 内部状态
_STATUS_MAP = {
    1: "running",
    4: "pending",
    5: "pending",
    0: "stopped",
    -1: "failed",
    -2: "stopped",
    7: "failed",
    8: "stopped",
}


def _md5(s: str) -> str:
    # 智星云 API 签名算法明确要求 MD5（参考 docs/zhixingyun_api/03_接口签名.md）
    return hashlib.md5(s.encode("utf-8"), usedforsecurity=False).hexdigest()


def _build_sign(params: dict, secret: str) -> str:
    """MD5 签名：按 key 排序，跳过空值和 sign/secret，拼接后加 secret，取 MD5。"""
    sorted_items = sorted(
        [(k, v) for k, v in params.items() if v is not None and v != "" and k != "sign"]
    )
    sign_str = "&".join(f"{k}={v}" for k, v in sorted_items)
    sign_str += f"&secret={secret}"
    return _md5(sign_str)


def _run_sync(func, *args, **kwargs):
    return asyncio.to_thread(func, *args, **kwargs)


class ZhixingyunProvider(CloudProvider):
    """智星云 Provider：通过 OpenAPI 管理 GPU 容器实例。"""

    name = "zhixingyun"

    def __init__(self, credentials: dict | None = None):
        creds = credentials or {}
        self._api_key = creds.get("api_key", "")
        self._api_secret = creds.get("api_secret", "")
        self._instances: dict[str, dict] = {}

    def _api_call_sync(self, endpoint: str, data: dict) -> dict:
        """调用智星云 OpenAPI（同步，供 asyncio.to_thread 包装）。"""
        nonce = str(int(time.time() * 1e9))
        timestamp = str(int(time.time()))

        payload = {
            "apikey": self._api_key,
            "timestamp": timestamp,
            "nonce": nonce,
            **data,
        }
        payload["sign"] = _build_sign(payload, self._api_secret)

        url = f"{BASE_URL}/{endpoint}"
        resp = httpx.post(url, data=payload, timeout=60)
        body = resp.json()

        if not body.get("success") or str(body.get("code")) != "2000":
            raise AppError(
                f"智星云 API 错误: {body.get('message', body.get('code', 'unknown'))}",
                code="zhixingyun_api_error",
                status_code=502,
            )
        return body.get("data", {})

    async def _api_call(self, endpoint: str, data: dict) -> dict:
        return await _run_sync(self._api_call_sync, endpoint, data)

    # --- CloudProvider 接口实现 ---

    async def create_instance(self, job_id: str, config: dict) -> dict:
        """创建智云星 GPU 实例。

        需要参数:
        - gpu_type: GPU 型号，如 "GeForce RTX 4090"
        - gpu_num: GPU 数量，1/2/4/8
        - image_name: 镜像名，如 "ubuntu22_cuda12.4"
        - pack_time: 租用时长，如 1
        - unit: 单位，"hour" 或 "day"
        - spec_name: 实例规格，如 "gcs.g1.large"
        """
        gpu_type = config.get("gpu_type", "GeForce RTX 4090")
        gpu_num = config.get("gpu_num", 1)
        image_name = config.get("image_name", "ubuntu22_cuda12.4")
        pack_time = config.get("pack_time", 1)
        unit = config.get("unit", "hour")
        spec_name = config.get("spec_name", "")
        pay_type = config.get("pay_type_first", "power")
        add_disk = config.get("add_disk_size", 0)
        bandwidth = config.get("bandwidth", 32)
        due_mode = config.get("due_mode", 1)

        data = {
            "gpu_type": gpu_type,
            "gpu_num": str(gpu_num),
            "image_name": image_name,
            "pack_time": str(pack_time),
            "unit": unit,
            "pay_type_first": pay_type,
            "autorenew_on": "false",
            "autorenew_unit": "hour",
            "add_disk_size": str(add_disk),
            "bandwidth": str(bandwidth),
            "due_mode": str(due_mode),
            "ext_uid": config.get("ext_uid", ""),
        }
        if spec_name:
            data["spec_name"] = spec_name

        result = await self._api_call("store/create_kvm_instance", data)

        container_name = result.get("Container_name", "")
        instance = {
            "instance_id": container_name,
            "job_id": job_id,
            "status": "pending",
            "host": result.get("Url", ""),
            "port": result.get("SshPort", 22),
            "user": result.get("LoginUserName", "root"),
            "gpu_type": result.get("Gpu_type", gpu_type),
            "gpu_count": result.get("Gpu_num", gpu_num),
            "created_at": time.time(),
            "started_at": None,
            "stopped_at": None,
            "api_data": result,
        }
        self._instances[container_name] = instance
        return instance

    async def start_instance(self, instance_id: str) -> dict:
        """启动已关闭的实例。"""
        data = {"instance_name": instance_id}
        result = await self._api_call("instance/restart_instance_from_shutdown", data)

        instance = self._instances.get(instance_id, {})
        instance.update(
            status="pending",
            started_at=time.time(),
            api_data=result,
        )
        if result.get("Url"):
            instance["host"] = result["Url"]
        if result.get("SshPort"):
            instance["port"] = result["SshPort"]

        return instance

    async def stop_instance(self, instance_id: str) -> dict:
        """停止实例（提前退租退款）。"""
        data = {"instance_name": instance_id}
        result = await self._api_call("instance/stop_instance_with_refund", data)

        instance = self._instances.get(instance_id, {})
        instance.update(
            status="stopped",
            stopped_at=time.time(),
            api_data=result,
        )
        return instance

    async def delete_instance(self, instance_id: str) -> None:
        """删除实例：智云星 stop+refund 即释放，清除本地缓存。"""
        with contextlib.suppress(Exception):
            await self.stop_instance(instance_id)
        self._instances.pop(instance_id, None)

    async def get_instance_status(self, instance_id: str) -> dict:
        """获取实例状态，同时刷新 SSH 连接信息。"""
        data = {"instance_name": instance_id}
        result = await self._api_call("instance/get_instance_detail", data)

        status_int = result.get("Status", 0)
        status = _STATUS_MAP.get(status_int, "unknown")
        is_abnormal = result.get("IsAbnormal", 0)

        # 运行中的实例如果 IsAbnormal != 0，标记为 failed
        if status == "running" and is_abnormal != 0:
            status = "failed"

        # 刷新 SSH 信息
        host = result.get("Url", "")
        ssh_port = result.get("SshPort", 22)

        # PortMappingInner 可能有内网端口映射，优先使用外网映射
        port_mapping = result.get("PortMappingInner")
        if port_mapping and isinstance(port_mapping, dict):
            extra_port = result.get("ExtraPort", {})
            if isinstance(extra_port, dict) and extra_port.get("p1"):
                ssh_port = extra_port["p1"]

        instance = self._instances.get(instance_id, {})
        instance.update(
            status=status,
            host=host,
            port=ssh_port,
            user=result.get("LoginUserName", "root"),
            gpu_type=result.get("Gpu_type", instance.get("gpu_type", "")),
            gpu_count=result.get("Gpu_num", instance.get("gpu_count", 1)),
            api_data=result,
        )
        if not instance.get("started_at") and status == "running":
            ctime = result.get("Ctime")
            if ctime:
                instance["started_at"] = float(ctime)

        self._instances[instance_id] = instance

        uptime = 0
        if instance.get("started_at"):
            end = instance.get("stopped_at") or time.time()
            uptime = end - instance["started_at"]

        return {
            "status": status,
            "gpu_util": 0.0,
            "mem_used": 0,
            "mem_total": 40960,
            "temperature": 0.0,
            "uptime_seconds": uptime,
        }

    async def get_gpu_metrics(self, instance_id: str) -> dict:
        """获取 GPU 指标。

        智星云 API 不提供实时 GPU 利用率，需要 SSH 到实例执行 nvidia-smi。
        MVP 阶段返回默认值。
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
        """计算实例运行费用。

        优先使用 API 返回的 Total_cost（权威数据），fallback 本地定价表。
        """
        from ..cost import calculator

        instance = self._instances.get(instance_id)
        if not instance:
            return 0.0

        # 尝试从 API 获取权威费用
        try:
            api_data = instance.get("api_data", {})
            total_cost = api_data.get("Total_cost")
            if total_cost is not None:
                return float(total_cost)
        except (ValueError, TypeError):
            pass

        # Fallback：本地定价表
        gpu_type = instance.get("gpu_type", "")
        started = instance.get("started_at")
        stopped = instance.get("stopped_at")

        if started and stopped:
            hours = (stopped - started) / 3600
        else:
            try:
                hours = (float(end) - float(start)) / 3600
            except (ValueError, TypeError):
                hours = 1.0

        rate = calculator.calculate_rate("zhixingyun", gpu_type)
        return round(max(hours, 0) * rate, 2)
