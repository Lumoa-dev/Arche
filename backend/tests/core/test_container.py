"""核心层测试 —— 服务容器（注册、解析、循环依赖检测）。"""

from __future__ import annotations

import pytest


class TestServiceContainer:
    """测试 ServiceContainer 基本功能。"""

    def test_create_container(self):
        """容器可以被创建。"""
        from backend.core.container import ServiceContainer

        container = ServiceContainer()
        assert container is not None

    def test_register_and_get(self):
        """服务可以注册并获取。"""
        from backend.core.container import ServiceContainer

        container = ServiceContainer()
        container.register("greeter", lambda c: "Hello, World!")
        result = container.get("greeter")
        assert result == "Hello, World!"

    def test_get_returns_singleton(self):
        """同一服务多次 get() 返回同一个实例。"""
        from backend.core.container import ServiceContainer

        container = ServiceContainer()
        container.register("counter", lambda c: object())
        instance1 = container.get("counter")
        instance2 = container.get("counter")
        assert instance1 is instance2

    def test_is_available(self):
        """is_available() 正确报告注册状态。"""
        from backend.core.container import ServiceContainer

        container = ServiceContainer()
        assert not container.is_available("unknown")
        container.register("known", lambda c: 42)
        assert container.is_available("known")

    def test_service_not_found(self):
        """获取未注册的服务抛出 ServiceNotFoundError。"""
        from backend.core.container import ServiceContainer, ServiceNotFoundError

        container = ServiceContainer()
        with pytest.raises(ServiceNotFoundError, match="unknown"):
            container.get("unknown")


class TestCircularDependency:
    """容器循环依赖检测。"""

    def test_detect_direct_cycle(self):
        """直接自引用循环依赖被检测。"""
        from backend.core.container import (
            CircularDependencyError,
            ServiceContainer,
        )

        container = ServiceContainer()
        container.register("a", lambda c: c.get("a"))

        with pytest.raises(CircularDependencyError, match="循环依赖"):
            container.get("a")

    def test_detect_indirect_cycle(self):
        """间接循环依赖 (A→B→C→A) 被检测。"""
        from backend.core.container import (
            CircularDependencyError,
            ServiceContainer,
        )

        container = ServiceContainer()
        container.register("a", lambda c: c.get("b"))
        container.register("b", lambda c: c.get("c"))
        container.register("c", lambda c: c.get("a"))

        with pytest.raises(CircularDependencyError, match="循环依赖"):
            container.get("a")

    def test_no_cycle_with_independent_services(self):
        """独立服务之间不触发循环检测。"""
        from backend.core.container import ServiceContainer

        container = ServiceContainer()
        container.register("a", lambda c: "service_a")
        container.register("b", lambda c: c.get("a") + "_and_b")

        result_b = container.get("b")
        assert result_b == "service_a_and_b"
        result_a = container.get("a")
        assert result_a == "service_a"


class TestFactoryParameters:
    """测试工厂函数接收容器参数。"""

    def test_factory_receives_container(self):
        """工厂函数的第一个参数是容器本身。"""
        from backend.core.container import ServiceContainer

        container = ServiceContainer()
        container.register("config", lambda c: {"debug": True})
        container.register(
            "service",
            lambda c: {"config": c.get("config"), "container_ref": c},
        )

        svc = container.get("service")
        assert svc["config"]["debug"] is True
        assert svc["container_ref"] is container


class TestContainerLifecycle:
    """测试容器的关闭生命周期。"""

    def test_shutdown_calls_close(self):
        """容器关闭时会调用所有服务的 close() 方法。"""
        from backend.core.container import ServiceContainer

        container = ServiceContainer()
        close_called = []

        class ServiceWithClose:
            def close(self):
                close_called.append("closed")

        container.register("svc", lambda c: ServiceWithClose())
        container.get("svc")
        container.shutdown()
        assert close_called == ["closed"]

    def test_shutdown_reverse_resolution_order(self):
        """close() 按解析（get）顺序的逆序调用。"""
        from backend.core.container import ServiceContainer

        container = ServiceContainer()
        order = []

        class Svc:
            def __init__(self, name: str):
                self.name = name

            def close(self):
                order.append(self.name)

        container.register("first", lambda c: Svc("first"))
        container.register("second", lambda c: Svc("second"))
        container.register("third", lambda c: Svc("third"))

        # 按 third → second → first 顺序解析
        container.get("third")
        container.get("second")
        container.get("first")

        container.shutdown()
        # 逆序 = first, second, third
        assert order == ["first", "second", "third"]
