"""ServiceContainer 依赖注入容器测试。"""

import pytest

from backend.core.container import (
    CircularDependencyError,
    ServiceContainer,
    ServiceNotFoundError,
)
from backend.core.container import (
    container as global_container,
)


class TestServiceContainer:
    """测试服务容器的核心功能。"""

    def setup_method(self):
        """每个测试用例前创建独立的容器实例。"""
        self.container = ServiceContainer()

    def test_container_initial_state(self):
        """初始状态下容器为空。"""
        assert self.container.is_available("any-service") is False

    def test_register_and_get_service(self):
        """注册并获取服务，功能正常。"""

        class TestService:
            pass

        def _test_service_factory(c):
            return TestService()

        # 注册服务工厂
        self.container.register("test-service", _test_service_factory)

        assert self.container.is_available("test-service") is True

        # 获取服务实例
        instance = self.container.get("test-service")
        assert isinstance(instance, TestService)

    def test_service_is_singleton(self):
        """多次get返回同一个实例，单例模式。"""
        factory_call_count = 0

        def test_service_factory(c):
            nonlocal factory_call_count
            factory_call_count += 1
            return object()

        self.container.register("test-service", test_service_factory)

        # 多次get
        instance1 = self.container.get("test-service")
        instance2 = self.container.get("test-service")
        instance3 = self.container.get("test-service")

        # 工厂函数只调用一次
        assert factory_call_count == 1
        # 所有实例都是同一个对象
        assert instance1 is instance2
        assert instance2 is instance3

    def test_lazy_initialization(self):
        """服务是延迟实例化的，只有第一次get的时候才调用工厂函数。"""
        factory_called = False

        def factory(c):
            nonlocal factory_called
            factory_called = True
            return object()

        self.container.register("test-service", factory)

        # 注册后还没有调用工厂
        assert factory_called is False

        # 第一次get的时候才调用
        self.container.get("test-service")
        assert factory_called is True

    def test_get_non_existent_service(self):
        """获取未注册的服务抛出 ServiceNotFoundError。"""
        with pytest.raises(ServiceNotFoundError, match="服务 'non-existent' 未注册"):
            self.container.get("non-existent")

    def test_circular_dependency_detection(self):
        """循环依赖场景抛出 CircularDependencyError。"""

        # A 依赖 B
        def factory_a(c):
            return {"dependency": c.get("service-b")}

        # B 依赖 A
        def factory_b(c):
            return {"dependency": c.get("service-a")}

        self.container.register("service-a", factory_a)
        self.container.register("service-b", factory_b)

        with pytest.raises(
            CircularDependencyError,
            match="循环依赖: service-a -> service-b -> service-a",
        ):
            self.container.get("service-a")

    def test_complex_circular_dependency(self):
        """复杂循环依赖也能正确检测。
        依赖链：A → B → C → A
        """

        def factory_a(c):
            return c.get("service-b")

        def factory_b(c):
            return c.get("service-c")

        def factory_c(c):
            return c.get("service-a")

        self.container.register("service-a", factory_a)
        self.container.register("service-b", factory_b)
        self.container.register("service-c", factory_c)

        with pytest.raises(
            CircularDependencyError,
            match="循环依赖: service-a -> service-b -> service-c -> service-a",
        ):
            self.container.get("service-a")

    def test_no_circular_dependency_for_existing_instance(self):
        """已经实例化的服务不会触发循环依赖检测。"""

        # A 依赖 B，B 不依赖任何人
        class ServiceB:
            pass

        def factory_a(c):
            return {"b": c.get("service-b")}

        def _factory_b_only(c):
            return ServiceB()

        self.container.register("service-a", factory_a)
        self.container.register("service-b", _factory_b_only)

        # 先实例化B
        b = self.container.get("service-b")
        # 再实例化A，这时候B已经存在，不会有循环
        a = self.container.get("service-a")
        assert a["b"] is b

    def test_shutdown_calls_close_in_reverse_order(self):
        """shutdown按逆序调用服务的close方法。"""
        close_order = []

        class ServiceA:
            def close(self):
                close_order.append("A")

        class ServiceB:
            def close(self):
                close_order.append("B")

        class ServiceC:
            def close(self):
                close_order.append("C")

        # 注册服务
        def _factory_shutdown_a(c):
            return ServiceA()

        def _factory_shutdown_b(c):
            return ServiceB()

        def _factory_shutdown_c(c):
            return ServiceC()

        self.container.register("service-a", _factory_shutdown_a)
        self.container.register("service-b", _factory_shutdown_b)
        self.container.register("service-c", _factory_shutdown_c)

        # 实例化顺序：A → B → C
        self.container.get("service-a")
        self.container.get("service-b")
        self.container.get("service-c")

        self.container.shutdown()

        # 关闭顺序应该是逆序：C → B → A
        assert close_order == ["C", "B", "A"]

    def test_shutdown_ignores_services_without_close(self):
        """没有close方法的服务不影响关闭流程。"""

        class ServiceWithClose:
            closed = False

            def close(self):
                self.closed = True

        class ServiceWithoutClose:
            pass

        def _factory_with_close(c):
            return ServiceWithClose()

        def _factory_without_close(c):
            return ServiceWithoutClose()

        self.container.register("with-close", _factory_with_close)
        self.container.register("without-close", _factory_without_close)

        # 实例化
        with_close = self.container.get("with-close")
        self.container.get("without-close")

        # shutdown不会报错
        self.container.shutdown()

        # 有close方法的服务被正确关闭
        assert with_close.closed is True

    def test_container_passes_self_to_factory(self):
        """工厂函数接收容器作为参数，可以获取其他服务。"""

        class ConfigService:
            def __init__(self):
                self.database_url = "sqlite:///test.db"

        class DatabaseService:
            def __init__(self, url):
                self.url = url

        def config_factory(c):
            return ConfigService()

        def db_factory(c):
            config = c.get("config")
            return DatabaseService(config.database_url)

        self.container.register("config", config_factory)
        self.container.register("db", db_factory)

        db = self.container.get("db")
        assert isinstance(db, DatabaseService)
        assert db.url == "sqlite:///test.db"

    def test_global_container_instance(self):
        """全局容器实例是正常的 ServiceContainer 对象。"""
        assert isinstance(global_container, ServiceContainer)
