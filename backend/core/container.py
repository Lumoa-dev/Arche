"""服务容器 —— 延迟注册、检索及循环依赖检测。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class CircularDependencyError(Exception):
    pass


class ServiceNotFoundError(Exception):
    pass


class ServiceContainer:
    """轻量级 IoC 容器，支持延迟实例化和循环检测。"""

    def __init__(self):
        self._factories: dict[str, Callable[[ServiceContainer], Any]] = {}
        self._instances: dict[str, Any] = {}
        self._resolving: list[str] = []

    def register(self, name: str, factory: Callable[[ServiceContainer], Any]) -> None:
        self._factories[name] = factory

    def get(self, name: str) -> Any:
        if name in self._resolving:
            cycle = " -> ".join([*self._resolving, name])
            raise CircularDependencyError(f"循环依赖: {cycle}")
        if name not in self._factories:
            raise ServiceNotFoundError(f"服务 '{name}' 未注册")
        if name not in self._instances:
            self._resolving.append(name)
            try:
                self._instances[name] = self._factories[name](self)
            finally:
                self._resolving.remove(name)
        return self._instances[name]

    def is_available(self, name: str) -> bool:
        return name in self._factories

    def shutdown(self) -> None:
        for instance in reversed(list(self._instances.values())):
            if hasattr(instance, "close"):
                instance.close()


# 全局单例，供插件 on_startup 等异步生命周期访问
container = ServiceContainer()
