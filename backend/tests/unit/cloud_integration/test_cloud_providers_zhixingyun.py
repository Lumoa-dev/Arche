"""Zhixingyun provider 单元测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.plugins.cloud_integration.providers.zhixingyun import (
    ZhixingyunProvider,
    _build_sign,
)


def test_build_sign_deterministic():
    sign = _build_sign({"apikey": "a", "nonce": "1", "timestamp": "2"}, "s")
    assert isinstance(sign, str)
    assert len(sign) == 32


@pytest.mark.asyncio
class TestZhixingyunProvider:
    async def test_status_mapping_and_metrics(self):
        provider = ZhixingyunProvider({"api_key": "a", "api_secret": "b"})
        provider._api_call = AsyncMock(
            return_value={
                "Status": 1,
                "IsAbnormal": 0,
                "Url": "1.1.1.1",
                "SshPort": 22,
                "LoginUserName": "root",
                "Gpu_type": "RTX4090",
                "Gpu_num": 1,
                "Ctime": "1000",
            }
        )
        status = await provider.get_instance_status("ins-1")
        assert status["status"] == "running"
        metrics = await provider.get_gpu_metrics("ins-1")
        assert "utilization_pct" in metrics

    async def test_get_cost_prefers_total_cost_then_fallback(self):
        provider = ZhixingyunProvider({"api_key": "a", "api_secret": "b"})
        provider._instances["x"] = {"api_data": {"Total_cost": "12.5"}}
        assert await provider.get_cost("x", "0", "1") == 12.5

        provider._instances["y"] = {
            "gpu_type": "RTX4090",
            "started_at": 0.0,
            "stopped_at": 3600.0,
            "api_data": {},
        }
        cost = await provider.get_cost("y", "0", "3600")
        assert cost > 0
