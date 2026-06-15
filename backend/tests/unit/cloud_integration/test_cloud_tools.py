"""cloud_integration 工具层单元测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.plugins.cloud_integration.cost import calculator
from backend.plugins.cloud_integration.log_parser import LogParser
from backend.plugins.cloud_integration.steps import StepCommandBuilder


class TestStepCommandBuilder:
    def test_clone_repo_with_token(self):
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/a/b.git", branch="dev", token="abc"
        )
        assert "https://abc@github.com/a/b.git" in cmd
        assert "--branch dev" in cmd

    def test_training_related_commands(self):
        assert "nohup python3 train.py" in StepCommandBuilder.start_training("train.py")
        assert "kill -0 123" in StepCommandBuilder.check_process("123")
        assert StepCommandBuilder.tail_log("/tmp/x.log", 20) == "tail -n 20 /tmp/x.log"


class TestLogParser:
    def test_parse_training_log(self):
        content = "x\nepoch 2 loss: 0.45\n"
        parsed = LogParser.parse_training_log(content)
        assert parsed == {"epoch": 2, "loss": 0.45}

    def test_parse_json_log(self):
        content = '{"step": 10, "epoch": 3, "loss": 0.2}\n'
        parsed = LogParser.parse_json_log(content)
        assert parsed == {"step": 10, "epoch": 3, "loss": 0.2}

    def test_parse_no_match(self):
        assert LogParser.parse_training_log("nothing") == {}


class TestCostCalculator:
    def test_calculate_rate_known_and_default(self):
        assert calculator.calculate_rate("mock", "A100") == 15.0
        assert calculator.calculate_rate("mock", "unknown") == 10.0
        assert calculator.calculate_rate("unknown_provider", "A100") == 15.0

    def test_calculate_instance_cost(self):
        start = datetime.now(timezone.utc) - timedelta(hours=2)
        end = datetime.now(timezone.utc)
        cost = calculator.calculate_instance_cost(start, end, "mock", "A100")
        assert cost == 30.0

    def test_aggregate_costs(self):
        now = datetime.now(timezone.utc)
        instances = [
            {
                "instance_id": "i1",
                "provider": "mock",
                "gpu_type": "A100",
                "started_at": now - timedelta(hours=1),
                "stopped_at": now,
            },
            {
                "instance_id": "i2",
                "provider": "mock",
                "gpu_type": "RTX4090",
                "started_at": now - timedelta(hours=2),
                "stopped_at": now,
            },
        ]
        result = calculator.aggregate_costs(instances)
        assert result["instance_count"] == 2
        assert result["total_cost"] == 25.0
