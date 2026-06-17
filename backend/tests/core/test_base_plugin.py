"""BasePlugin 单元测试 —— 插件基类接口和默认实现。"""

from __future__ import annotations

from backend.core.base_plugin import BasePlugin


class TestBasePlugin:
    def test_abstract_class_cannot_instantiate_directly(self):
        """BasePlugin 有抽象方法，不能直接实例化。"""
        import pytest

        with pytest.raises(TypeError):
            BasePlugin()  # type: ignore[abstract]

    def test_minimal_concrete_plugin(self):
        """最少实现的插件应可用。"""
        from backend.core.base_plugin import BasePlugin

        class MinimalPlugin(BasePlugin):
            name = "minimal"

            def setup(self, app):
                pass

        plugin = MinimalPlugin()
        assert plugin.name == "minimal"
        assert plugin.version == "0.1.0"

    def test_default_version(self):
        class P(BasePlugin):
            name = "test"

            def setup(self, app):
                pass

        assert P().version == "0.1.0"

    def test_default_requires_and_optional(self):
        class P(BasePlugin):
            name = "test"

            def setup(self, app):
                pass

        plugin = P()
        assert plugin.requires == []
        assert plugin.optional == []

    def test_register_services_default_noop(self):
        """register_services 默认实现不应报错。"""

        class P(BasePlugin):
            name = "test"

            def setup(self, app):
                pass

        plugin = P()
        # 不传 container 只验证不抛异常
        result = plugin.register_services(None)  # type: ignore[arg-type]
        assert result is None

    def test_on_startup_default_returns_none(self):
        """on_startup 默认返回 None。"""

        class P(BasePlugin):
            name = "test"

            def setup(self, app):
                pass

        result = P().on_startup()
        assert result is None

    def test_on_shutdown_default_noop(self):
        """on_shutdown 默认不抛异常。"""

        class P(BasePlugin):
            name = "test"

            def setup(self, app):
                pass

        P().on_shutdown()  # should not raise

    def test_full_plugin_lifecycle(self):
        """验证完整生命周期方法的正常执行。"""
        calls = []

        class FullPlugin(BasePlugin):
            name = "full"
            version = "2.0.0"

            def setup(self, app):
                calls.append("setup")

            def register_services(self, container):
                calls.append("register_services")

            def on_startup(self):
                calls.append("on_startup")
                return None

            def on_shutdown(self):
                calls.append("on_shutdown")

        plugin = FullPlugin()
        plugin.setup(None)  # type: ignore[arg-type]
        plugin.register_services(None)  # type: ignore[arg-type]
        plugin.on_startup()
        plugin.on_shutdown()

        assert calls == ["setup", "register_services", "on_startup", "on_shutdown"]
