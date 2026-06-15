"""
Veil entry point.

Usage:
    uvicorn backend.main:app --reload
"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中以保证导入正常
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core import create_app
from backend.core.plugin_registry import discover_plugins

# 在创建应用前先发现插件
discover_plugins()

app = create_app()
