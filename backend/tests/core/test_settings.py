"""Settings 单元测试 —— 应用和插件配置模型。"""

from __future__ import annotations

import pytest


class TestAppSettings:
    def test_default_values(self, monkeypatch):
        from backend.core.settings.app import AppSettings

        # 清除环境变量干扰，验证纯默认值
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)

        s = AppSettings()
        assert s.DATABASE_URL == "sqlite+aiosqlite:///./data/arche.db"
        assert s.SECRET_KEY == "change-me-to-random-string"
        assert s.CORS_ORIGINS == "http://localhost:5173"
        assert s.LOG_LEVEL == "INFO"
        assert s.LOG_FILE is None

    def test_env_override(self, monkeypatch):
        from backend.core.settings.app import AppSettings

        monkeypatch.setenv("DATABASE_URL", "postgresql://test")
        monkeypatch.setenv("SECRET_KEY", "test-key")

        s = AppSettings()
        assert s.DATABASE_URL == "postgresql://test"
        assert s.SECRET_KEY == "test-key"

    def test_log_file_optional(self):
        from backend.core.settings.app import AppSettings

        s = AppSettings()
        assert s.LOG_FILE is None

    def test_extra_fields_allowed(self):
        """AppSettings 允许额外字段（model_config extra=allow）。"""
        from backend.core.settings.app import AppSettings

        s = AppSettings(UNKNOWN_FIELD="value")
        assert hasattr(s, "UNKNOWN_FIELD")
        assert s.UNKNOWN_FIELD == "value"


class TestPluginSettingsBase:
    def test_get_field_defaults(self):
        from pydantic import Field
        from pydantic_settings import BaseSettings

        from backend.core.settings.base import PluginSettingsBase

        class TestSettings(PluginSettingsBase):  # type: ignore[no-untyped-call]
            str_field: str = "default_str"
            int_field: int = 42
            list_field: list[str] = ["a", "b"]
            none_field: str | None = None

        defaults = TestSettings.get_field_defaults()
        assert defaults["str_field"] == "default_str"
        assert defaults["int_field"] == "42"  # Pydantic v2 中 int 默认值会被转为 str
        assert defaults["none_field"] == ""

    def test_get_field_defaults_empty(self):
        from backend.core.settings.base import PluginSettingsBase

        class EmptySettings(PluginSettingsBase):  # type: ignore[no-untyped-call]
            pass

        defaults = EmptySettings.get_field_defaults()
        assert defaults == {}


class TestCreatePluginSettings:
    def test_create_plugin_settings(self):
        from pydantic import Field

        from backend.core.settings.base import create_plugin_settings

        SettingClass = create_plugin_settings(
            "TestPlugin",
            {"API_KEY": str, "TIMEOUT": int, "ENABLED": bool},
            defaults={"API_KEY": "...", "TIMEOUT": 30, "ENABLED": True},
        )

        s = SettingClass()
        assert s.API_KEY == "..."
        assert s.TIMEOUT == 30
        assert s.ENABLED is True

    def test_create_plugin_settings_override(self):
        from backend.core.settings.base import create_plugin_settings

        SettingClass = create_plugin_settings(
            "TestPlugin",
            {"API_KEY": str},
            defaults={"API_KEY": "default_key"},
        )

        import os
        os.environ["API_KEY"] = "env_key"
        s = SettingClass()
        assert s.API_KEY == "default_key"
        del os.environ["API_KEY"]
