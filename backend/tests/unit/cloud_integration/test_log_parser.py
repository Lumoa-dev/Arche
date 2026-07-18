"""训练日志解析器 行为测试。

纯函数测试，无数据库依赖，运行极快。
"""

from __future__ import annotations

import pytest

from backend.plugins.cloud_integration.log_parser import LogParser


class TestLogParser:
    """训练日志解析器行为测试。"""

    # ── parse_training_log ──

    def test_parse_training_log_default_pattern(self):
        """默认正则表达式应匹配标准训练日志行。"""
        content = """
Epoch 1: loss = 0.5
Epoch 2: loss = 0.3
Epoch 3: loss = 0.1
"""
        result = LogParser.parse_training_log(content)
        assert result["epoch"] == 3
        assert result["loss"] == 0.1

    def test_parse_training_log_last_line_wins(self):
        """应取最后一行的匹配结果。"""
        content = """
Epoch 1: loss = 0.9
Epoch 10: loss = 0.05
"""
        result = LogParser.parse_training_log(content)
        assert result["epoch"] == 10
        assert result["loss"] == 0.05

    def test_parse_training_log_empty_content(self):
        """空内容应返回空字典。"""
        result = LogParser.parse_training_log("")
        assert result == {}

    def test_parse_training_log_no_match(self):
        """无匹配行应返回空字典。"""
        content = "Starting training...\nLoading data...\nDone."
        result = LogParser.parse_training_log(content)
        assert result == {}

    def test_parse_training_log_custom_pattern(self):
        """自定义正则表达式应正确工作。"""
        content = "Step: 100, Accuracy: 0.95"
        result = LogParser.parse_training_log(
            content, pattern=r"Step:\s*(\d+).*?Accuracy:\s*([\d.]+)"
        )
        assert result["epoch"] == 100
        assert result["loss"] == 0.95

    def test_parse_training_log_partial_match(self):
        """只有 epoch 没有 loss 的匹配应返回部分结果。"""
        content = "Epoch 42"
        result = LogParser.parse_training_log(
            content, pattern=r"Epoch\s+(\d+)"
        )
        assert result["epoch"] == 42
        assert "loss" not in result

    def test_parse_training_log_multiline_values(self):
        """多行日志应正确处理。"""
        content = """
Epoch 50: loss = 0.5
Epoch 51: loss = 0.4
"""
        result = LogParser.parse_training_log(content)
        assert result["epoch"] == 51
        assert result["loss"] == 0.4

    def test_parse_training_log_non_standard_format(self):
        """非标准格式但包含 epoch/loss 的日志。"""
        content = "[2024-01-01 10:00:00] epoch=5, loss=0.234, lr=1e-4"
        result = LogParser.parse_training_log(
            content, pattern=r"epoch=(\d+).*?loss=([\d.]+)"
        )
        assert result["epoch"] == 5
        assert result["loss"] == 0.234

    # ── parse_huggingface_log ──

    def test_parse_huggingface_log_success(self):
        """HuggingFace JSON 格式日志应正确解析。"""
        content = (
            '{"loss": 0.5, "epoch": 1.0}\n'
            '{"loss": 0.3, "epoch": 2.0}\n'
            '{"loss": 0.1, "epoch": 3.0}\n'
        )
        result = LogParser.parse_huggingface_log(content)
        # 取最后一行
        assert result["loss"] == 0.1
        assert result["epoch"] == 3

    def test_parse_huggingface_log_empty(self):
        """空内容应返回空字典。"""
        result = LogParser.parse_huggingface_log("")
        assert result == {}

    def test_parse_huggingface_log_no_match(self):
        """无匹配行应返回空字典。"""
        content = "Some random text without loss or epoch."
        result = LogParser.parse_huggingface_log(content)
        assert result == {}

    def test_parse_huggingface_log_invalid_line(self):
        """包含无效行的日志应跳过错误行。"""
        content = (
            "This is not JSON\n"
            '{"loss": 0.5, "epoch": 1.0}\n'
            "Also not JSON\n"
        )
        result = LogParser.parse_huggingface_log(content)
        assert result["loss"] == 0.5
        assert result["epoch"] == 1

    # ── parse_json_log ──

    def test_parse_json_log_success(self):
        """JSON 格式日志行应正确解析。"""
        content = (
            '{"loss": 0.5, "epoch": 1, "step": 100}\n'
            '{"loss": 0.3, "epoch": 2, "step": 200}\n'
        )
        result = LogParser.parse_json_log(content)
        assert result["loss"] == 0.3
        assert result["epoch"] == 2
        assert result["step"] == 200

    def test_parse_json_log_empty(self):
        """空内容应返回空字典。"""
        result = LogParser.parse_json_log("")
        assert result == {}

    def test_parse_json_log_invalid_json(self):
        """无效 JSON 行应被跳过。"""
        content = "not json\n"
        result = LogParser.parse_json_log(content)
        assert result == {}

    def test_parse_json_log_partial_fields(self):
        """JSON 行包含部分字段时应返回可用字段。"""
        content = '{"loss": 0.5}\n'
        result = LogParser.parse_json_log(content)
        assert result["loss"] == 0.5
        assert "epoch" not in result
        assert "step" not in result

    def test_parse_json_log_mixed_content(self):
        """混合内容中应提取 JSON 行。"""
        content = (
            "Some log text\n"
            '{"loss": 1.0, "epoch": 1, "step": 50}\n'
            "More text\n"
        )
        result = LogParser.parse_json_log(content)
        assert result["loss"] == 1.0
        assert result["epoch"] == 1

    def test_parse_json_log_float_epoch(self):
        """epoch 为浮点数时应转为整数。"""
        content = '{"loss": 0.5, "epoch": 2.5, "step": 150}\n'
        result = LogParser.parse_json_log(content)
        assert result["epoch"] == 2

    def test_parse_json_log_negative_values(self):
        """负值应正确解析。"""
        content = '{"loss": -0.5, "epoch": 1, "step": 100}\n'
        result = LogParser.parse_json_log(content)
        assert result["loss"] == -0.5
        assert result["epoch"] == 1