"""ConfigManager 配置管理器测试。"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic_settings import BaseSettings

from backend.core.config import (
    ConfigManager,
    PluginSettingsRegistry,
    get_config,
)
from backend.core.config import (
    config_manager as global_config_manager,
)


class TestPluginSettingsRegistry:
    """测试插件配置注册表。"""

    def test_registry_initial_state(self):
        """初始状态下注册表为空。"""
        registry = PluginSettingsRegistry()
        assert registry.get_all() == {}

    def test_register_and_get_settings(self):
        """注册和获取插件配置类功能正常。"""

        class TestPluginSettings(BaseSettings):
            api_key: str = "test-key"
            enabled: bool = True

        registry = PluginSettingsRegistry()
        registry.register("test-plugin", TestPluginSettings)

        assert registry.get("test-plugin") == TestPluginSettings
        assert registry.get("non-existent") is None
        assert "test-plugin" in registry.get_all()

    def test_iterate_items(self):
        """遍历插件配置功能正常。"""

        class Plugin1Settings(BaseSettings):
            pass

        class Plugin2Settings(BaseSettings):
            pass

        registry = PluginSettingsRegistry()
        registry.register("plugin1", Plugin1Settings)
        registry.register("plugin2", Plugin2Settings)

        items = list(registry.items())
        assert len(items) == 2
        assert ("plugin1", Plugin1Settings) in items
        assert ("plugin2", Plugin2Settings) in items


class TestConfigManager:
    """测试配置管理器核心功能。"""

    def setup_method(self):
        """每个测试用例前重置单例状态，避免互相影响。"""
        ConfigManager._instance = None
        # 使用临时目录避免 xdist 并行执行时的文件竞争
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="arche-test-config-"))
        self.test_env_file = self._tmp_dir / "test.env"
        self.test_env_file.write_text(
            """
# Test config
DATABASE_URL=sqlite:///test.db
SECRET_KEY=test-secret
LOG_LEVEL=INFO
# Commented key
# COMMENTED_KEY=value
""",
            encoding="utf-8",
        )

    def teardown_method(self):
        """测试后清理临时文件。"""
        if self._tmp_dir.exists():
            import shutil

            shutil.rmtree(self._tmp_dir)
        # 重置单例
        ConfigManager._instance = None
        # 恢复环境变量
        for key in ["DATABASE_URL", "SECRET_KEY", "CUSTOM_KEY"]:
            if key in os.environ:
                del os.environ[key]

    def test_singleton_pattern(self):
        """ConfigManager 是单例模式，多次实例化返回同一个对象。"""
        config1 = ConfigManager(env_file=str(self.test_env_file))
        config2 = ConfigManager(
            env_file="different.env"
        )  # 第二次的env_file参数会被忽略

        assert config1 is config2
        assert id(config1) == id(config2)

    def test_load_env_file(self):
        """正确加载 .env 文件中的配置。"""
        config = ConfigManager(env_file=str(self.test_env_file))

        assert config.get("DATABASE_URL") == "sqlite:///test.db"
        assert config.get("SECRET_KEY") == "test-secret"
        assert config.get("LOG_LEVEL") == "INFO"
        assert config.get("COMMENTED_KEY") is None  # 注释的配置不会被加载
        assert config.get("NON_EXISTENT_KEY") is None

    def test_environment_variables_override_env_file(self):
        """操作系统环境变量覆盖 .env 文件中的配置。"""
        # 设置环境变量
        os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
        os.environ["CUSTOM_KEY"] = "custom-value"

        config = ConfigManager(env_file=str(self.test_env_file))

        # 环境变量的值覆盖了.env文件的值
        assert config.get("DATABASE_URL") == "postgresql://user:pass@localhost/db"
        # 环境变量中新增的配置也能读取到
        assert config.get("CUSTOM_KEY") == "custom-value"
        # 没有被环境变量覆盖的还是保持.env的值
        assert config.get("SECRET_KEY") == "test-secret"

    def test_get_method_with_default(self):
        """get 方法支持默认值。"""
        config = ConfigManager(env_file=str(self.test_env_file))

        assert config.get("NON_EXISTENT", "default-value") == "default-value"
        assert config.get("LOG_LEVEL", "DEBUG") == "INFO"  # 存在的配置不会用默认值

    def test_get_required_method(self):
        """get_required 方法在配置不存在时抛出异常。"""
        config = ConfigManager(env_file=str(self.test_env_file))

        # 存在的配置正常返回
        assert config.get_required("DATABASE_URL") == "sqlite:///test.db"

        # 不存在的配置抛出 RuntimeError
        with pytest.raises(
            RuntimeError, match="Required config 'NON_EXISTENT' is not set"
        ):
            config.get_required("NON_EXISTENT")

    def test_set_method(self):
        """set 方法设置内存中的配置值，优先级最高。"""
        config = ConfigManager(env_file=str(self.test_env_file))

        assert config.get("DATABASE_URL") == "sqlite:///test.db"

        # 设置新值
        config.set("DATABASE_URL", "sqlite:///new.db")
        assert config.get("DATABASE_URL") == "sqlite:///new.db"

        # 设置不存在的配置
        config.set("NEW_KEY", "new-value")
        assert config.get("NEW_KEY") == "new-value"

    def test_reload_method(self):
        """reload 方法重新加载配置。"""
        config = ConfigManager(env_file=str(self.test_env_file))
        assert config.get("DATABASE_URL") == "sqlite:///test.db"

        # 修改.env文件
        self.test_env_file.write_text(
            """
DATABASE_URL=sqlite:///updated.db
SECRET_KEY=updated-secret
""",
            encoding="utf-8",
        )

        # 修改环境变量
        os.environ["LOG_LEVEL"] = "DEBUG"

        # 重载前还是旧值
        assert config.get("DATABASE_URL") == "sqlite:///test.db"
        assert config.get("LOG_LEVEL") == "INFO"

        # 重载后是新值
        config.reload()
        assert config.get("DATABASE_URL") == "sqlite:///updated.db"
        assert config.get("SECRET_KEY") == "updated-secret"
        assert config.get("LOG_LEVEL") == "DEBUG"

    def test_invalidate_cache(self):
        """清除缓存功能正常。"""
        config = ConfigManager(env_file=str(self.test_env_file))

        # mock数据库缓存
        config._cache["key1"] = ("value1", time.time() + 3600)
        config._cache["key2"] = ("value2", time.time() + 3600)
        config._cache["key3"] = ("value3", time.time() + 3600)

        assert len(config._cache) == 3

        # 清除单个key
        config.invalidate_cache("key1")
        assert "key1" not in config._cache
        assert "key2" in config._cache
        assert len(config._cache) == 2

        # 清除所有缓存
        config.invalidate_cache()
        assert len(config._cache) == 0

    def test_plugin_settings_registration(self):
        """插件配置注册功能正常。"""

        class TestPluginSettings(BaseSettings):
            api_key: str = "test-key"
            enabled: bool = True
            limit: int = 100

        config = ConfigManager(env_file=str(self.test_env_file))
        config.register_plugin_settings("test-plugin", TestPluginSettings)

        assert config.plugins.get("test-plugin") == TestPluginSettings
        assert "test-plugin" in config.plugins.get_all()

    def test_generate_env_example(self):
        """生成 .env.example 文件内容功能正常。"""
        # 这个方法依赖ConfigEntry模型，暂时跳过
        pytest.skip(
            "generate_env_example requires ConfigEntry model which is not available in test context"
        )

        class Plugin1Settings(BaseSettings):
            api_key: str = "plugin1-key"
            enabled: bool = True
            hosts: list[str] = ["localhost", "127.0.0.1"]

        class Plugin2Settings(BaseSettings):
            secret: str = ""
            port: int = 8080
            debug: bool = False

        config = ConfigManager(env_file=str(self.test_env_file))
        config.register_plugin_settings("plugin1", Plugin1Settings)
        config.register_plugin_settings("plugin2", Plugin2Settings)

        example_content = config.generate_env_example()

        # 包含核心配置
        assert "# === Core Settings ===" in example_content
        assert "DATABASE_URL=sqlite:///test.db" in example_content
        assert "SECRET_KEY=test-secret" in example_content
        assert "LOG_LEVEL=INFO" in example_content

        # 包含插件1配置
        assert "# === PLUGIN1 ===" in example_content
        assert "api_key=plugin1-key" in example_content
        assert "enabled=True" in example_content
        assert "hosts=localhost,127.0.0.1" in example_content

        # 包含插件2配置
        assert "# === PLUGIN2 ===" in example_content
        assert "secret=" in example_content  # None默认值为空字符串
        assert "port=8080" in example_content
        assert "debug=False" in example_content

    @pytest.mark.asyncio
    async def test_database_cache_functionality(self):
        """数据库缓存功能正常。"""
        # 这个方法依赖ConfigEntry模型和SQLAlchemy，暂时跳过
        pytest.skip("Database cache test requires full database setup")

        config = ConfigManager(env_file=str(self.test_env_file))

        # mock数据库会话工厂
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_entry = MagicMock()
        mock_entry.value = "db-value"
        mock_result.scalar_one_or_none.return_value = mock_entry
        mock_session.execute.return_value = mock_result

        # mock会话工厂
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        config.set_session_factory(mock_session_factory)

        # 第一次获取，数据库中存在，会被缓存
        value = config.get("DB_CONFIG_KEY")
        assert value == "db-value"
        assert "DB_CONFIG_KEY" in config._cache
        assert config._cache["DB_CONFIG_KEY"][0] == "db-value"

        # 第二次获取，命中缓存，不会查询数据库
        mock_session.execute.reset_mock()
        value = config.get("DB_CONFIG_KEY")
        assert value == "db-value"
        mock_session.execute.assert_not_called()

        # 缓存过期后会重新查询数据库
        config._cache["DB_CONFIG_KEY"] = ("old-value", time.time() - 1)  # 已经过期
        value = config.get("DB_CONFIG_KEY")
        assert value == "db-value"
        mock_session.execute.assert_called_once()

    def test_get_config_returns_global_instance(self):
        """get_config() 函数返回全局单例实例。"""
        config = get_config()
        assert isinstance(config, ConfigManager)
        assert config is global_config_manager
