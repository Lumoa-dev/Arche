"""训练日志解析器 — 从远程日志中提取进度信息。"""

from __future__ import annotations

import json
import re

DEFAULT_LOG_PATTERN = r"epoch\s+(\d+).*?loss\s*[:=]\s*([\d.]+)"
HUGGINGFACE_LOG_PATTERN = r'"loss"\s*:\s*([\d.]+).*?"epoch"\s*:\s*([\d.]+)'


class LogParser:
    """解析训练日志，提取 epoch / loss / step。"""

    @staticmethod
    def parse_training_log(content: str, pattern: str = DEFAULT_LOG_PATTERN) -> dict:
        """从日志内容中提取最新的 epoch/loss。"""
        regex = re.compile(pattern, re.IGNORECASE)
        for line in reversed(content.splitlines()):
            match = regex.search(line.strip())
            if match:
                groups = match.groups()
                result: dict = {}
                if len(groups) >= 1:
                    try:
                        result["epoch"] = int(float(groups[0]))
                    except (ValueError, TypeError):
                        result["epoch"] = groups[0]
                if len(groups) >= 2:
                    try:
                        result["loss"] = float(groups[1])
                    except (ValueError, TypeError):
                        result["loss"] = groups[1]
                if result:
                    return result
        return {}

    @staticmethod
    def parse_huggingface_log(content: str) -> dict:
        """解析 HuggingFace Trainer JSON 格式日志。"""
        regex = re.compile(HUGGINGFACE_LOG_PATTERN)
        for line in reversed(content.splitlines()):
            match = regex.search(line.strip())
            if match:
                try:
                    return {
                        "loss": float(match.group(1)),
                        "epoch": int(float(match.group(2))),
                    }
                except (ValueError, TypeError):
                    continue
        return {}

    @staticmethod
    def parse_json_log(content: str) -> dict:
        """尝试将日志行解析为 JSON 对象（如 HuggingFace log_table）。"""
        for line in reversed(content.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    result: dict = {}
                    if "epoch" in data:
                        result["epoch"] = int(float(data["epoch"]))
                    if "loss" in data:
                        result["loss"] = float(data["loss"])
                    if "step" in data:
                        result["step"] = int(data["step"])
                    if result:
                        return result
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue
        return {}
