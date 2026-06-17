"""插件注册表 —— 目录扫描、DAG 拓扑排序和生命周期管理。"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

    from .container import ServiceContainer


class DependencyError(Exception):
    pass


class PluginRegistry:
    """单例注册表，管理插件发现、排序和激活。"""

    def __init__(self) -> None:
        self._plugins: dict[str, Any] = {}
        self._active: list[str] = []

    def register(self, name: str, plugin: Any) -> None:
        self._plugins[name] = plugin

    def reset(self) -> None:
        """清空所有已注册和已激活的插件。"""
        self._plugins.clear()
        self._active.clear()

    def activate(self, name: str, app: FastAPI) -> None:
        if name not in self._plugins:
            raise ValueError(f"Plugin '{name}' not registered")
        plugin = self._plugins[name]
        if hasattr(plugin, "setup"):
            plugin.setup(app)
        self._active.append(name)

    def activate_all(self, app: FastAPI) -> None:
        ordered = self._topological_sort()
        for name in ordered:
            self.activate(name, app)

    def register_services(self, container: ServiceContainer) -> None:
        ordered = self._topological_sort()
        for name in ordered:
            plugin = self._plugins[name]
            if hasattr(plugin, "register_services"):
                plugin.register_services(container)

    async def on_startup(self) -> None:
        import asyncio

        for name in self._active:
            plugin = self._plugins.get(name)
            if plugin and hasattr(plugin, "on_startup"):
                result = plugin.on_startup()
                if asyncio.iscoroutine(result):
                    await result

    def on_shutdown(self) -> None:
        for name in reversed(self._active):
            plugin = self._plugins.get(name)
            if plugin and hasattr(plugin, "on_shutdown"):
                plugin.on_shutdown()

    def _topological_sort(self) -> list[str]:
        """Kahn 算法，包含硬依赖/可选依赖校验。"""
        names = list(self._plugins)
        in_degree: dict[str, int] = {n: 0 for n in names}
        graph: dict[str, list[str]] = {n: [] for n in names}

        for name, plugin in self._plugins.items():
            for dep in getattr(plugin, "requires", []):
                if dep not in self._plugins:
                    raise DependencyError(f"插件 '{name}' 依赖 '{dep}'，但该插件未注册")
                graph[dep].append(name)
                in_degree[name] += 1

            for dep in getattr(plugin, "optional", []):
                if dep in self._plugins:
                    graph[dep].append(name)
                    in_degree[name] += 1

        queue = [n for n in names if in_degree[n] == 0]
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(names):
            missing = set(names) - set(result)
            raise DependencyError(f"循环依赖 detected，涉及插件: {', '.join(missing)}")

        return result

    @property
    def active(self) -> list[str]:
        return list(self._active)

    @property
    def available(self) -> list[str]:
        return list(self._plugins)


registry = PluginRegistry()


def discover_plugins(plugin_dir: Path | None = None) -> None:
    """自动发现并导入插件目录下的所有插件目录。"""
    if plugin_dir is None:
        plugin_dir = Path(__file__).resolve().parent.parent / "plugins"
    for entry in sorted(plugin_dir.iterdir()):
        if not entry.is_dir():
            continue
        init_file = entry / "__init__.py"
        if not init_file.exists():
            continue
        module_name = f"backend.plugins.{entry.name}"
        import_module(module_name)
