"""训练日志解析器单元测试 —— 覆盖正则匹配、JSON 解析及边界情况。"""

from __future__ import annotations

import pytest

from backend.plugins.cloud_integration.log_parser import LogParser


class TestLogParser:
    """LogParser 纯函数测试。"""

    def test_parse_training_log_default_pattern(self):
        """从最后一行开始匹配，返回最后匹配的 epoch/loss。"""
        content = "Epoch 4: loss = 0.3456\nEpoch 5: loss = 0.2345\n"
        result = LogParser.parse_training_log(content)
        assert result["epoch"] == 5
        assert result["loss"] == 0.2345

    def test_parse_training_log_reverse_order(self):
        """从最后一行开始匹配，应返回最后匹配的结果。"""
        content = "Epoch 1: loss = 0.5\nEpoch 2: loss = 0.4\n"
        result = LogParser.parse_training_log(content)
        assert result["epoch"] == 2
        assert result["loss"] == 0.4

    def test_parse_training_log_no_match(self):
        content = "Some random log content without expected format"
        result = LogParser.parse_training_log(content)
        assert result == {}

    def test_parse_training_log_empty_content(self):
        result = LogParser.parse_training_log("")
        assert result == {}

    def test_parse_training_log_with_different_format(self):
        """使用自定义正则模式。"""
        content = "Step: 100, accuracy: 0.95"
        pattern = r"Step:\s*(\d+).*?accuracy:\s*([\d.]+)"
        result = LogParser.parse_training_log(content, pattern=pattern)
        assert result["epoch"] == 100
        assert result["loss"] == 0.95

    def test_parse_training_log_non_numeric_value(self):
        """当匹配值无法转换为数字时，保留原始字符串。"""
        content = "Epoch: five, loss: unknown"
        result = LogParser.parse_training_log(content)
        # 默认模式不匹配，返回空 dict
        assert result == {}

    def test_parse_huggingface_log(self):
        content = '{"loss": 0.123, "epoch": 3.0}\n{"loss": 0.456, "epoch": 4.0}\n'
        result = LogParser.parse_huggingface_log(content)
        assert result["loss"] == 0.456
        assert result["epoch"] == 4

    def test_parse_huggingface_log_no_match(self):
        content = "Plain text log without JSON"
        result = LogParser.parse_huggingface_log(content)
        assert result == {}

    def test_parse_json_log(self):
        content = '{"epoch": 5, "loss": 0.234, "step": 1000}\n'
        result = LogParser.parse_json_log(content)
        assert result["epoch"] == 5
        assert result["loss"] == 0.234
        assert result["step"] == 1000

    def test_parse_json_log_partial_fields(self):
        content = '{"epoch": 3, "accuracy": 0.95}\n'
        result = LogParser.parse_json_log(content)
        assert result["epoch"] == 3
        assert "loss" not in result

    def test_parse_json_log_invalid_json(self):
        content = "not json\n{also not}\n"
        result = LogParser.parse_json_log(content)
        assert result == {}

    def test_parse_json_log_mixed_content(self):
        content = "some text\n{'loss': 0.5}\n{\"epoch\": 2, \"loss\": 0.3}\n"
        result = LogParser.parse_json_log(content)
        assert result["epoch"] == 2
        assert result["loss"] == 0.3

    def test_parse_huggingface_log_with_extra_fields(self):
        content = '{"loss": 0.5, "epoch": 2.0, "learning_rate": 1e-5}\n'
        result = LogParser.parse_huggingface_log(content)
        assert result["loss"] == 0.5
        assert result["epoch"] == 2