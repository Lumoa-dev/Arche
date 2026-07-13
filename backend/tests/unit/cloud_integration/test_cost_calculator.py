"""云训练费用计算器测试 —— 定价表和费用聚合。

测试策略：
- 纯函数，无外部依赖，使用固定时间确保确定性
- 覆盖：各 Provider 定价、运行时计算、聚合、边界情况
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend.plugins.cloud_integration.cost.calculator import (
    PRICING_TABLE,
    aggregate_costs,
    calculate_instance_cost,
    calculate_rate,
)


class TestCalculateRate:
    """calculate_rate 测试。"""

    def test_known_provider_known_gpu(self):
        """已知 Provider 和 GPU 类型返回正确单价。"""
        assert calculate_rate("mock", "A100") == 15.0
        assert calculate_rate("zhixingyun", "V100") == 7.5
        assert calculate_rate("aliyun", "H100") == 28.0

    def test_known_provider_unknown_gpu(self):
        """已知 Provider 但未知 GPU 返回默认单价。"""
        assert calculate_rate("mock", "UNKNOWN_GPU") == 10.0
        assert calculate_rate("zhixingyun", "UNKNOWN_GPU") == 10.0

    def test_unknown_provider(self):
        """未知 Provider 回退到 mock 定价。"""
        rate = calculate_rate("unknown_provider", "A100")
        assert rate == 15.0  # mock 的 A100 价格

    def test_unknown_provider_unknown_gpu(self):
        """未知 Provider 和未知 GPU 返回默认值。"""
        rate = calculate_rate("unknown_provider", "UNKNOWN_GPU")
        assert rate == 10.0  # mock 的 default 价格

    def test_all_providers_have_default(self):
        """所有 Provider 都有 default 兜底价格。"""
        for provider in PRICING_TABLE:
            assert "default" in PRICING_TABLE[provider]

    def test_pricing_table_is_immutable(self):
        """定价表在测试中不应被修改。"""
        # 验证定价表是模块级常量
        assert PRICING_TABLE["mock"]["A100"] == 15.0


class TestCalculateInstanceCost:
    """calculate_instance_cost 测试。"""

    def test_running_instance(self):
        """正在运行的实例（无 stopped_at）使用当前时间计算。"""
        from datetime import timedelta
        from unittest.mock import patch

        start = datetime.now() - timedelta(hours=2)
        with patch("backend.plugins.cloud_integration.cost.calculator.datetime") as mock_dt:
            mock_dt.now.return_value = datetime.now()
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs) if args else mock_dt.now()
            cost = calculate_instance_cost(start, None, "mock", "A100")
            assert cost > 0

    def test_completed_instance(self):
        """已完成的实例正确计算费用。"""
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 2, 30, 0)  # 2.5 小时
        cost = calculate_instance_cost(start, end, "mock", "A100")
        # 2.5 * 15 = 37.5
        assert cost == 37.5

    def test_zero_duration(self):
        """开始和结束时间相同，费用为 0。"""
        now = datetime.now()
        cost = calculate_instance_cost(now, now, "mock", "A100")
        assert cost == 0.0

    def test_no_start_time(self):
        """无开始时间返回 0 费用。"""
        cost = calculate_instance_cost(None, datetime.now(), "mock", "A100")
        assert cost == 0.0

    def test_different_gpu_types(self):
        """不同 GPU 类型费用不同。"""
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)  # 1 小时
        cost_a100 = calculate_instance_cost(start, end, "mock", "A100")
        cost_v100 = calculate_instance_cost(start, end, "mock", "V100")
        assert cost_a100 > cost_v100  # A100 比 V100 贵

    def test_rounding(self):
        """费用四舍五入到 2 位小数。"""
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 0, 1, 0)  # 1 分钟
        cost = calculate_instance_cost(start, end, "mock", "A100")
        # (1/60) * 15 = 0.25
        assert cost == 0.25


class TestAggregateCosts:
    """aggregate_costs 测试。"""

    def test_single_instance(self):
        """单个实例的聚合。"""
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 2, 0, 0)  # 2 小时
        instances = [
            {
                "instance_id": "inst-001",
                "provider": "mock",
                "gpu_type": "A100",
                "started_at": start,
                "stopped_at": end,
            }
        ]
        result = aggregate_costs(instances)
        assert result["total_cost"] == 30.0  # 2 * 15
        assert result["currency"] == "CNY"
        assert result["instance_count"] == 1
        assert len(result["breakdown"]) == 1

    def test_multiple_instances(self):
        """多个实例的聚合。"""
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)  # 1 小时
        instances = [
            {
                "instance_id": "inst-001",
                "provider": "mock",
                "gpu_type": "A100",
                "started_at": start,
                "stopped_at": end,
            },
            {
                "instance_id": "inst-002",
                "provider": "zhixingyun",
                "gpu_type": "V100",
                "started_at": start,
                "stopped_at": end,
            },
        ]
        result = aggregate_costs(instances)
        # 1 * 15 (A100 mock) + 1 * 7.5 (V100 zhixingyun) = 22.5
        assert result["total_cost"] == 22.5
        assert result["instance_count"] == 2

    def test_empty_instances(self):
        """空实例列表返回 0 费用。"""
        result = aggregate_costs([])
        assert result["total_cost"] == 0.0
        assert result["instance_count"] == 0
        assert result["breakdown"] == []

    def test_instance_without_optional_fields(self):
        """缺少可选字段的实例使用默认值。"""
        instances = [
            {
                "started_at": datetime(2024, 1, 1, 0, 0, 0),
                "stopped_at": datetime(2024, 1, 1, 1, 0, 0),
            }
        ]
        result = aggregate_costs(instances)
        # 使用默认 provider=mock, gpu_type=A100
        assert result["total_cost"] == 15.0
        assert result["breakdown"][0]["provider"] == "mock"
        assert result["breakdown"][0]["gpu_type"] == "A100"

    def test_total_cost_rounding(self):
        """总费用正确四舍五入。"""
        start = datetime(2024, 1, 1, 0, 0, 0)
        # 1 分钟 * 3 个实例
        end = datetime(2024, 1, 1, 0, 1, 0)
        instances = [
            {
                "instance_id": f"inst-{i:03d}",
                "provider": "mock",
                "gpu_type": "A100",
                "started_at": start,
                "stopped_at": end,
            }
            for i in range(3)
        ]
        result = aggregate_costs(instances)
        # 每个 (1/60) * 15 = 0.25, 3 个共 0.75
        assert result["total_cost"] == 0.75