"""PluginRegistry 插件注册表测试。"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI

from backend.core.base_plugin import BasePlugin
from backend.core.container import ServiceContainer
from backend.core.plugin_registry import (
    DependencyError,
    PluginRegistry,
    discover_plugins,
)
from backend.core.plugin_registry import (
    registry as global_registry,
)


class TestPluginRegistry:
    """测试插件注册表的核心功能。"""

    def setup_method(self):
        """每个测试用例前创建独立的注册表实例，避免互相影响。"""
        self.registry = PluginRegistry()
        self.app = FastAPI()
        self.container = ServiceContainer()

    def test_registry_initial_state(self):
        """初始状态下注册表为空。"""
        assert self.registry.available == []
        assert self.registry.active == []

    def test_register_plugin(self):
        """注册插件功能正常。"""

        class TestPlugin(BasePlugin):
            name = "test-plugin"

            def setup(self, app: FastAPI) -> None:
                pass

        plugin = TestPlugin()
        self.registry.register("test-plugin", plugin)

        assert "test-plugin" in self.registry.available
        assert "test-plugin" not in self.registry.active

    def test_activate_existing_plugin(self):
        """激活已注册的插件，调用setup方法。"""
        setup_called = False

        class TestPlugin(BasePlugin):
            name = "test-plugin"

            def setup(self, app: FastAPI) -> None:
                nonlocal setup_called
                setup_called = True

        plugin = TestPlugin()
        self.registry.register("test-plugin", plugin)
        self.registry.activate("test-plugin", self.app)

        assert setup_called is True
        assert "test-plugin" in self.registry.active

    def test_activate_non_existing_plugin(self):
        """激活不存在的插件抛出 ValueError。"""
        with pytest.raises(ValueError, match="Plugin 'non-existent' not registered"):
            self.registry.activate("non-existent", self.app)

    def test_activate_all_plugins(self):
        """激活所有已注册的插件，顺序正确。"""
        called_order = []

        class PluginA(BasePlugin):
            name = "plugin-a"

            def setup(self, app: FastAPI) -> None:
                called_order.append("plugin-a")

        class PluginB(BasePlugin):
            name = "plugin-b"
            requires = ["plugin-a"]  # 依赖A  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                called_order.append("plugin-b")

        plugin_a = PluginA()
        plugin_b = PluginB()

        self.registry.register("plugin-b", plugin_b)
        self.registry.register("plugin-a", plugin_a)  # 故意按反向顺序注册

        self.registry.activate_all(self.app)

        # 拓扑排序后应该先激活A再激活B
        assert called_order == ["plugin-a", "plugin-b"]
        assert self.registry.active == ["plugin-a", "plugin-b"]

    def test_register_services(self):
        """注册服务功能正常，按拓扑顺序调用。"""
        called_order = []

        class PluginA(BasePlugin):
            name = "plugin-a"

            def setup(self, app: FastAPI) -> None:
                pass

            def register_services(self, container: ServiceContainer) -> None:
                called_order.append("plugin-a")

        class PluginB(BasePlugin):
            name = "plugin-b"
            requires = ["plugin-a"]  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                pass

            def register_services(self, container: ServiceContainer) -> None:
                called_order.append("plugin-b")

        plugin_a = PluginA()
        plugin_b = PluginB()

        self.registry.register("plugin-b", plugin_b)
        self.registry.register("plugin-a", plugin_a)

        self.registry.register_services(self.container)

        # 按拓扑顺序调用
        assert called_order == ["plugin-a", "plugin-b"]

    @pytest.mark.asyncio
    async def test_on_startup_hook_sync(self):
        """启动钩子支持同步方法，按激活顺序调用。"""
        called_order = []

        class PluginA(BasePlugin):
            name = "plugin-a"

            def setup(self, app: FastAPI) -> None:
                pass

            def on_startup(self) -> None:
                called_order.append("plugin-a")

        class PluginB(BasePlugin):
            name = "plugin-b"
            requires = ["plugin-a"]  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                pass

            def on_startup(self) -> None:
                called_order.append("plugin-b")

        plugin_a = PluginA()
        plugin_b = PluginB()

        self.registry.register("plugin-b", plugin_b)
        self.registry.register("plugin-a", plugin_a)
        self.registry.activate_all(self.app)

        await self.registry.on_startup()

        # 按激活顺序调用启动钩子
        assert called_order == ["plugin-a", "plugin-b"]

    @pytest.mark.asyncio
    async def test_on_startup_hook_async(self):
        """启动钩子支持异步方法。"""
        called = False

        class TestPlugin(BasePlugin):
            name = "test-plugin"

            def setup(self, app: FastAPI) -> None:
                pass

            async def on_startup(self) -> None:
                nonlocal called
                called = True

        plugin = TestPlugin()
        self.registry.register("test-plugin", plugin)
        self.registry.activate("test-plugin", self.app)

        await self.registry.on_startup()

        assert called is True

    def test_on_shutdown_hook(self):
        """关闭钩子按激活逆序调用。"""
        called_order = []

        class PluginA(BasePlugin):
            name = "plugin-a"

            def setup(self, app: FastAPI) -> None:
                pass

            def on_shutdown(self) -> None:
                called_order.append("plugin-a")

        class PluginB(BasePlugin):
            name = "plugin-b"
            requires = ["plugin-a"]  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                pass

            def on_shutdown(self) -> None:
                called_order.append("plugin-b")

        plugin_a = PluginA()
        plugin_b = PluginB()

        self.registry.register("plugin-b", plugin_b)
        self.registry.register("plugin-a", plugin_a)
        self.registry.activate_all(self.app)  # 激活顺序：A → B

        self.registry.on_shutdown()

        # 关闭顺序应该是逆序：B → A
        assert called_order == ["plugin-b", "plugin-a"]

    def test_topological_sort_hard_dependency_missing(self):
        """硬依赖不存在时抛出 DependencyError。"""

        class PluginA(BasePlugin):
            name = "plugin-a"
            requires = ["plugin-b"]  # 依赖不存在的B  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                pass

        plugin_a = PluginA()
        self.registry.register("plugin-a", plugin_a)

        with pytest.raises(
            DependencyError, match="插件 'plugin-a' 依赖 'plugin-b'，但该插件未注册"
        ):
            self.registry.activate_all(self.app)

    def test_topological_sort_optional_dependency_missing(self):
        """可选依赖不存在时忽略，不影响启动。"""
        called = False

        class PluginA(BasePlugin):
            name = "plugin-a"
            optional = ["plugin-b"]  # 可选依赖不存在的B  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                nonlocal called
                called = True

        plugin_a = PluginA()
        self.registry.register("plugin-a", plugin_a)

        # 不应该抛出错误
        self.registry.activate_all(self.app)
        assert called is True

    def test_topological_sort_optional_dependency_exists(self):
        """可选依赖存在时，按依赖关系排序。"""
        called_order = []

        class PluginA(BasePlugin):
            name = "plugin-a"

            def setup(self, app: FastAPI) -> None:
                called_order.append("plugin-a")

        class PluginB(BasePlugin):
            name = "plugin-b"
            optional = ["plugin-a"]  # 可选依赖A  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                called_order.append("plugin-b")

        plugin_a = PluginA()
        plugin_b = PluginB()

        self.registry.register("plugin-b", plugin_b)
        self.registry.register("plugin-a", plugin_a)

        self.registry.activate_all(self.app)

        # 可选依赖存在时，A应该在B前面
        assert called_order == ["plugin-a", "plugin-b"]

    def test_topological_sort_circular_dependency(self):
        """循环依赖时抛出 DependencyError。"""

        class PluginA(BasePlugin):
            name = "plugin-a"
            requires = ["plugin-b"]  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                pass

        class PluginB(BasePlugin):
            name = "plugin-b"
            requires = ["plugin-a"]  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                pass

        plugin_a = PluginA()
        plugin_b = PluginB()

        self.registry.register("plugin-a", plugin_a)
        self.registry.register("plugin-b", plugin_b)

        with pytest.raises(DependencyError, match="循环依赖 detected"):
            self.registry.activate_all(self.app)

    def test_topological_sort_complex_dependencies(self):
        """复杂依赖场景排序正确。
        依赖关系：
        A 无依赖
        B 依赖 A
        C 依赖 B
        D 依赖 A, C
        顺序应该是：A → B → C → D
        """
        called_order = []

        class PluginA(BasePlugin):
            name = "plugin-a"

            def setup(self, app: FastAPI) -> None:
                called_order.append("A")

        class PluginB(BasePlugin):
            name = "plugin-b"
            requires = ["plugin-a"]  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                called_order.append("B")

        class PluginC(BasePlugin):
            name = "plugin-c"
            requires = ["plugin-b"]  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                called_order.append("C")

        class PluginD(BasePlugin):
            name = "plugin-d"
            requires = ["plugin-a", "plugin-c"]  # noqa: RUF012

            def setup(self, app: FastAPI) -> None:
                called_order.append("D")

        # 乱序注册
        self.registry.register("plugin-d", PluginD())
        self.registry.register("plugin-b", PluginB())
        self.registry.register("plugin-a", PluginA())
        self.registry.register("plugin-c", PluginC())

        self.registry.activate_all(self.app)

        assert called_order == ["A", "B", "C", "D"]


class TestDiscoverPlugins:
    """测试插件自动发现功能。"""

    @pytest.mark.skip(
        reason="Path mocking is too complex, this function is tested in integration tests"
    )
    def test_discover_plugins_default_directory(self, tmp_path):
        """默认情况下扫描 backend/plugins 目录。"""
        pass

    def test_discover_plugins_custom_directory(self, tmp_path):
        """可以指定自定义插件目录。"""
        custom_dir = tmp_path / "custom-plugins"
        custom_dir.mkdir()

        # 创建自定义插件
        plugin_dir = custom_dir / "custom-plugin"
        plugin_dir.mkdir()
        plugin_init = plugin_dir / "__init__.py"
        plugin_init.write_text("""
from backend.core.plugin_registry import registry
from backend.core.base_plugin import BasePlugin

class CustomPlugin(BasePlugin):
    name = "custom-plugin"
    def setup(self, app):
        pass

registry.register("custom-plugin", CustomPlugin())
""")

        # 清空全局注册表
        global_registry._plugins.clear()
        global_registry._active.clear()

        # 保存原始的 import_module，用 importlib 从文件加载（避免 exec 整段源码）
        import importlib.util
        import sys
        from importlib import import_module as original_import

        def custom_import(name, *args, **kwargs):
            if name == "backend.plugins.custom-plugin":
                spec = importlib.util.spec_from_file_location(name, plugin_init)
                if spec is None or spec.loader is None:
                    raise ImportError(f"invalid spec: {name}")
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
                return module
            return original_import(name, *args, **kwargs)

        with patch(
            "backend.core.plugin_registry.import_module", side_effect=custom_import
        ):
            discover_plugins(plugin_dir=custom_dir)

        assert "custom-plugin" in global_registry.available

    def test_discover_plugins_alphabetical_order(self, tmp_path):
        """插件按字母顺序导入。"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # 创建三个插件，按字母顺序是b、a、c
        for name in ["plugin-b", "plugin-a", "plugin-c"]:
            plugin_dir = plugins_dir / name
            plugin_dir.mkdir()
            (plugin_dir / "__init__.py").write_text(f"""
from backend.core.plugin_registry import registry
from backend.core.base_plugin import BasePlugin

class {name.replace("-", "_").title()}(BasePlugin):
    name = "{name}"
    def setup(self, app):
        pass

registry.register("{name}", {name.replace("-", "_").title()}())
""")

        # 记录导入顺序
        import_order = []

        def tracking_import(name, *args, **kwargs):
            if name.startswith("backend.plugins."):
                import_order.append(name.split(".")[-1])
            # 不真的导入，返回mock模块
            mock_module = type("MockModule", (), {})()
            return mock_module

        with patch(
            "backend.core.plugin_registry.import_module", side_effect=tracking_import
        ):
            global_registry._plugins.clear()
            discover_plugins(plugin_dir=plugins_dir)

        # 导入顺序应该是按字母排序的：plugin-a, plugin-b, plugin-c
        assert import_order == ["plugin-a", "plugin-b", "plugin-c"]
