"""BasePlugin 抽象基类测试。"""

from abc import ABC

import pytest
from fastapi import FastAPI

from backend.core.base_plugin import BasePlugin
from backend.core.container import ServiceContainer


class TestBasePlugin:
    """测试 BasePlugin 抽象基类的行为规范。"""

    def test_base_plugin_is_abstract(self):
        """BasePlugin 是抽象类，不能直接实例化。"""
        with pytest.raises(
            TypeError, match="Can't instantiate abstract class BasePlugin"
        ):
            BasePlugin()  # type: ignore

    def test_subclass_must_implement_setup(self):
        """子类必须实现 setup 方法，否则实例化失败。"""

        # 没有实现 setup 方法的子类
        class BadPlugin(BasePlugin):
            pass

        with pytest.raises(
            TypeError, match="Can't instantiate abstract class BadPlugin"
        ):
            BadPlugin()  # pyright: ignore[reportAbstractUsage]

        # 实现了 setup 方法的子类可以正常实例化
        class GoodPlugin(BasePlugin):
            def setup(self, app: FastAPI) -> None:
                pass

        plugin = GoodPlugin()
        assert isinstance(plugin, BasePlugin)
        assert isinstance(plugin, ABC)

    def test_plugin_metadata_defaults(self):
        """插件元数据默认值正确。"""

        class TestPlugin(BasePlugin):
            def setup(self, app: FastAPI) -> None:
                pass

        plugin = TestPlugin()
        assert plugin.name == ""
        assert plugin.version == "0.1.0"
        assert plugin.requires == []
        assert plugin.optional == []

    def test_plugin_metadata_custom(self):
        """自定义插件元数据正确读取。"""

        class TestPlugin(BasePlugin):
            name = "test-plugin"
            version = "1.0.0"
            requires = ["plugin-a", "plugin-b"]  # noqa: RUF012
            optional = ["plugin-c"]  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                pass

        plugin = TestPlugin()
        assert plugin.name == "test-plugin"
        assert plugin.version == "1.0.0"
        assert plugin.requires == ["plugin-a", "plugin-b"]
        assert plugin.optional == ["plugin-c"]

    def test_optional_methods_default_implementation(self):
        """可选方法有默认空实现，可以不重写。"""

        class TestPlugin(BasePlugin):
            def setup(self, app: FastAPI) -> None:
                pass

        plugin = TestPlugin()
        app = FastAPI()
        container = ServiceContainer()

        # 调用默认实现不会报错
        plugin.setup(app)
        plugin.register_services(container)
        plugin.on_startup()
        plugin.on_shutdown()

    def test_optional_methods_can_be_overridden(self):
        """可选方法可以被重写，功能正常。"""
        called = {"register_services": False, "on_startup": False, "on_shutdown": False}

        class TestPlugin(BasePlugin):
            def setup(self, app: FastAPI) -> None:
                pass

            def register_services(self, container: ServiceContainer) -> None:
                called["register_services"] = True

            def on_startup(self) -> None:
                called["on_startup"] = True

            def on_shutdown(self) -> None:
                called["on_shutdown"] = True

        plugin = TestPlugin()
        container = ServiceContainer()

        plugin.register_services(container)
        assert called["register_services"] is True

        plugin.on_startup()
        assert called["on_startup"] is True

        plugin.on_shutdown()
        assert called["on_shutdown"] is True
