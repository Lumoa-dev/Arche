"""云训练 Provider 抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CloudProvider(ABC):
    """云训练 Provider 抽象接口。

    所有具体 Provider（Mock、智云星、阿里云等）必须实现此接口。
    """

    name: str = ""

    def __init__(self, credentials: dict | None = None) -> None:  # noqa: B027
        """初始化 Provider，传入认证凭据（具体字段由 Provider 定义）。"""
        pass

    @abstractmethod
    async def create_instance(self, job_id: str, config: dict) -> dict:
        """创建云实例。

        Returns:
            {instance_id, status, host, port, user, gpu_type, gpu_count}
        """
        ...

    @abstractmethod
    async def start_instance(self, instance_id: str) -> dict:
        """启动已创建的实例。"""
        ...

    @abstractmethod
    async def stop_instance(self, instance_id: str) -> dict:
        """停止运行中的实例。"""
        ...

    @abstractmethod
    async def delete_instance(self, instance_id: str) -> None:
        """销毁实例。"""
        ...

    @abstractmethod
    async def get_instance_status(self, instance_id: str) -> dict:
        """获取实例状态。

        Returns:
            {status, gpu_util, mem_used, mem_total, temperature, uptime_seconds}
        """
        ...

    @abstractmethod
    async def get_gpu_metrics(self, instance_id: str) -> dict:
        """获取 GPU 指标。

        Returns:
            {utilization_pct, memory_used_mb, memory_total_mb, temperature_c}
        """
        ...

    @abstractmethod
    async def get_cost(self, instance_id: str, start: str, end: str) -> float:
        """计算实例运行费用。

        Returns:
            费用（元）
        """
        ...
