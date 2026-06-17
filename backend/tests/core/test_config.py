"""核心层测试 —— 配置管理器（分层读取、必填校验、缓存）。"""

from __future__ import annotations

import pytest


class TestConfigManager:
    """测试 ConfigManager 单例和基本功能。"""

    def test_singleton(self):
        """ConfigManager 是单例。"""
        from backend.core.config import ConfigManager

        c1 = ConfigManager()
        c2 = ConfigManager()
        assert c1 is c2

    def test_get_env_var(self):
        """get() 能读取环境变量。"""
        from backend.core.config import config_manager

        # SECRET_KEY 是在 conftest 中设置的
        value = config_manager.get("SECRET_KEY")
        assert value == "test-secret-key-for-pytest-0123456789"

    def test_get_default(self):
        """get() 在键不存在时返回默认值。"""
        from backend.core.config import config_manager

        value = config_manager.get("NONEXISTENT_KEY", "fallback")
        assert value == "fallback"

    def test_get_default_none(self):
        """get() 在键不存在且无默认值时返回 None。"""
        from backend.core.config import config_manager

        value = config_manager.get("NONEXISTENT_KEY_2")
        assert value is None

    def test_get_required_exists(self):
        """get_required() 对存在的键返回值。"""
        from backend.core.config import config_manager

        value = config_manager.get_required("SECRET_KEY")
        assert value == "test-secret-key-for-pytest-0123456789"

    def test_get_required_raises(self):
        """get_required() 对不存在的键抛出 RuntimeError。"""
        from backend.core.config import config_manager

        with pytest.raises(RuntimeError, match="Required config"):
            config_manager.get_required("NONEXISTENT_KEY_3")

    def test_set_and_get(self):
        """set() 写入后 get() 能读取。"""
        from backend.core.config import config_manager

        config_manager.set("TEST_KEY", "test_value")
        assert config_manager.get("TEST_KEY") == "test_value"

    def test_set_overrides_env(self):
        """set() 优先级高于环境变量。"""
        from backend.core.config import config_manager

        original = config_manager.get("SECRET_KEY")
        config_manager.set("SECRET_KEY", "override_value")
        assert config_manager.get("SECRET_KEY") == "override_value"
        # 恢复
        config_manager.set("SECRET_KEY", original)

    def test_invalidate_cache_single(self):
        """invalidate_cache() 能清除单个键的缓存。"""
        from backend.core.config import config_manager

        config_manager._cache["TEST_CACHE"] = ("cached_value", 9999999999)
        assert "TEST_CACHE" in config_manager._cache
        config_manager.invalidate_cache("TEST_CACHE")
        assert "TEST_CACHE" not in config_manager._cache

    def test_invalidate_cache_all(self):
        """invalidate_cache() 无参数时清除所有缓存。"""
        from backend.core.config import config_manager

        config_manager._cache["KEY_A"] = ("val_a", 9999999999)
        config_manager._cache["KEY_B"] = ("val_b", 9999999999)
        config_manager.invalidate_cache()
        assert config_manager._cache == {}

    def test_reload_clears_values(self):
        """reload() 清空内存值并从环境变量重新加载。"""
        from backend.core.config import config_manager

        # 写入自定义值
        config_manager.set("RELOAD_TEST", "will_be_cleared")
        assert config_manager.get("RELOAD_TEST") == "will_be_cleared"

        config_manager.reload()
        # reload 后自定义值被清除
        assert config_manager.get("RELOAD_TEST") is None
        # 环境变量仍然存在
        assert (
            config_manager.get("SECRET_KEY") == "test-secret-key-for-pytest-0123456789"
        )


class TestPluginSettingsRegistry:
    """测试插件配置注册表。"""

    def test_register_and_get(self):
        """插件配置类可以注册和获取。"""
        from pydantic_settings import BaseSettings

        from backend.core.config import config_manager

        class TestSettings(BaseSettings):
            test_field: str = "default"

        config_manager.register_plugin_settings("test_plugin", TestSettings)
        retrieved = config_manager.plugins.get("test_plugin")
        assert retrieved is TestSettings

    def test_get_nonexistent(self):
        """不存在的插件配置返回 None。"""
        from backend.core.config import config_manager

        assert config_manager.plugins.get("nonexistent_plugin") is None

    def test_iterate_all(self):
        """plugins.items() 返回所有注册项。"""
        from backend.core.config import config_manager

        items = dict(config_manager.plugins.items())
        # 至少包含在插件 __init__ 中注册的配置
        assert "blog" in items
        assert "oss" in items


class TestAppSettings:
    """测试 AppSettings Pydantic 模型。"""

    def test_app_settings_populated(self):
        """app_settings 属性从环境变量填充。"""
        from backend.core.config import config_manager

        settings = config_manager.app_settings
        assert settings is not None
        # DATABASE_URL 是在 conftest 中设置的
        assert "sqlite" in settings.DATABASE_URL
