"""训练日志解析器测试 —— 从远程日志中提取进度信息。

测试策略：
- 纯函数，无外部依赖，使用固定日志内容确保确定性
- 覆盖：默认格式、HuggingFace 格式、JSON 格式、边界情况
"""

from __future__ import annotations

import pytest

from backend.plugins.cloud_integration.log_parser import LogParser

parser = LogParser()


class TestParseTrainingLog:
    """parse_training_log 测试。"""

    def test_parse_basic_training_log(self):
        """解析标准训练日志格式。"""
        log = """
Epoch 1: loss = 2.3456
Epoch 2: loss = 1.2345
Epoch 3: loss = 0.9876
"""
        result = parser.parse_training_log(log)
        assert result["epoch"] == 3
        assert result["loss"] == 0.9876

    def test_parse_training_log_reverse(self):
        """从最后一行往前找，取最新的 epoch。"""
        log = """
Epoch 1: loss = 2.3456
Epoch 2: loss = 1.2345
"""
        result = parser.parse_training_log(log)
        assert result["epoch"] == 2
        assert result["loss"] == 1.2345

    def test_parse_training_log_no_match(self):
        """无匹配行返回空字典。"""
        log = "Starting training...\nLoading data..."
        result = parser.parse_training_log(log)
        assert result == {}

    def test_parse_training_log_empty(self):
        """空日志返回空字典。"""
        result = parser.parse_training_log("")
        assert result == {}

    def test_parse_training_log_custom_pattern(self):
        """自定义正则模式。"""
        log = """
Step 100: accuracy=0.85
Step 200: accuracy=0.92
"""
        pattern = r"Step\s+(\d+).*?accuracy=([\d.]+)"
        result = parser.parse_training_log(log, pattern)
        assert result["epoch"] == 200
        assert result["loss"] == 0.92

    def test_parse_training_log_case_insensitive(self):
        """默认模式大小写不敏感。"""
        log = "EPOCH 5: LOSS = 0.5"
        result = parser.parse_training_log(log)
        assert result["epoch"] == 5
        assert result["loss"] == 0.5

    def test_parse_training_log_bad_epoch_value(self):
        """epoch 值无法转换为数字时保留原始字符串（使用自定义模式）。"""
        # 自定义模式捕获非数字值
        log = "Epoch: N/A, loss: 1.0"
        pattern = r"Epoch:\s*([\w/]+).*?loss:\s*([\d.]+)"
        result = parser.parse_training_log(log, pattern)
        assert result["epoch"] == "N/A"
        assert result["loss"] == 1.0


class TestParseHuggingfaceLog:
    """parse_huggingface_log 测试。"""

    def test_parse_huggingface_json(self):
        """解析 HuggingFace JSON 格式日志。"""
        log = '{"loss": 2.5, "epoch": 1.0}\n{"loss": 1.8, "epoch": 2.0}\n'
        result = parser.parse_huggingface_log(log)
        assert result["loss"] == 1.8
        assert result["epoch"] == 2

    def test_parse_huggingface_log_mixed(self):
        """混合格式日志中提取 HuggingFace 格式。"""
        log = """
Epoch 1: loss = 2.5
{"loss": 1.5, "epoch": 2.0}
"""
        result = parser.parse_huggingface_log(log)
        assert result["loss"] == 1.5
        assert result["epoch"] == 2

    def test_parse_huggingface_no_match(self):
        """无匹配行返回空字典。"""
        log = "Training started..."
        result = parser.parse_huggingface_log(log)
        assert result == {}

    def test_parse_huggingface_empty(self):
        """空日志返回空字典。"""
        result = parser.parse_huggingface_log("")
        assert result == {}


class TestParseJsonLog:
    """parse_json_log 测试。"""

    def test_parse_json_log_basic(self):
        """解析 JSON 格式日志行。"""
        log = '{"epoch": 1.0, "loss": 2.5, "step": 100}'
        result = parser.parse_json_log(log)
        assert result["epoch"] == 1
        assert result["loss"] == 2.5
        assert result["step"] == 100

    def test_parse_json_log_multi_line(self):
        """多行 JSON 日志，取最后一行。"""
        log = (
            '{"epoch": 1.0, "loss": 2.5}\n'
            '{"epoch": 2.0, "loss": 1.5}\n'
            '{"epoch": 3.0, "loss": 0.8}'
        )
        result = parser.parse_json_log(log)
        assert result["epoch"] == 3
        assert result["loss"] == 0.8

    def test_parse_json_log_partial_fields(self):
        """JSON 行只包含部分字段。"""
        log = '{"loss": 1.5}'
        result = parser.parse_json_log(log)
        assert "loss" in result
        assert "epoch" not in result
        assert result["loss"] == 1.5

    def test_parse_json_log_empty(self):
        """空日志返回空字典。"""
        result = parser.parse_json_log("")
        assert result == {}

    def test_parse_json_log_no_json_lines(self):
        """无 JSON 行返回空字典。"""
        log = "Not a JSON line\nAlso not JSON"
        result = parser.parse_json_log(log)
        assert result == {}

    def test_parse_json_log_invalid_json(self):
        """包含无效 JSON 行时跳过。"""
        log = '{invalid json}\n{"epoch": 1.0, "loss": 2.5}'
        result = parser.parse_json_log(log)
        assert result["epoch"] == 1
        assert result["loss"] == 2.5

    def test_parse_json_log_with_additional_fields(self):
        """包含额外字段的 JSON 行保留已知字段。"""
        log = '{"epoch": 2.0, "loss": 1.5, "step": 200, "eval_loss": 2.0}'
        result = parser.parse_json_log(log)
        assert result["epoch"] == 2
        assert result["loss"] == 1.5
        assert result["step"] == 200
        # eval_loss 不在已知字段中，不应返回
        assert "eval_loss" not in result