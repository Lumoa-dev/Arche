"""核心应用配置测试。"""

import os

from backend.core.settings.app import AppSettings


class TestAppSettings:
    """测试核心应用配置类。"""

    def setup_method(self):
        """清理环境变量。"""
        for key in [
            "DATABASE_URL",
            "SECRET_KEY",
            "CORS_ORIGINS",
            "LOG_LEVEL",
            "LOG_FILE",
            "EXTRA_CONFIG",
        ]:
            if key in os.environ:
                del os.environ[key]

    def test_default_values(self):
        """默认值正确。"""
        settings = AppSettings()

        assert settings.DATABASE_URL == "sqlite+aiosqlite:///./data/arche.db"
        assert settings.SECRET_KEY == "change-me-to-random-string"
        assert settings.CORS_ORIGINS == "http://localhost:5173"
        assert settings.LOG_LEVEL == "INFO"
        assert settings.LOG_FILE is None

    def test_environment_variables_override_defaults(self):
        """环境变量正确覆盖默认值。"""
        os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
        os.environ["SECRET_KEY"] = "production-secret-123"
        os.environ["CORS_ORIGINS"] = "https://app.example.com,https://admin.example.com"
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["LOG_FILE"] = "/var/log/arche/app.log"

        settings = AppSettings()

        assert settings.DATABASE_URL == "postgresql://user:pass@localhost/db"
        assert settings.SECRET_KEY == "production-secret-123"
        assert (
            settings.CORS_ORIGINS == "https://app.example.com,https://admin.example.com"
        )
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.LOG_FILE == "/var/log/arche/app.log"

    def test_extra_config_allowed(self):
        """extra="allow" 允许构造参数中的额外字段。"""
        os.environ["EXTRA_CONFIG"] = "extra-value"

        settings = AppSettings()

        # pydantic-settings 仅从环境变量加载已声明字段；
        # 未声明的环境变量不会自动注入到 model_extra。
        extras = settings.model_extra or {}
        assert "EXTRA_CONFIG" not in extras

        # extra="allow" 的语义体现在构造参数里传入额外字段时。
        from_kwargs = AppSettings.model_validate({"EXTRA_CONFIG": "extra-value"})
        assert (from_kwargs.model_extra or {}).get("EXTRA_CONFIG") == "extra-value"

    def test_settings_from_dict(self):
        """可以从字典创建设置实例。"""
        settings = AppSettings(
            DATABASE_URL="sqlite:///custom.db",
            SECRET_KEY="custom-secret",
            LOG_LEVEL="WARNING",
        )

        assert settings.DATABASE_URL == "sqlite:///custom.db"
        assert settings.SECRET_KEY == "custom-secret"
        assert settings.LOG_LEVEL == "WARNING"
        # 没有指定的项使用默认值
        assert settings.CORS_ORIGINS == "http://localhost:5173"
        assert settings.LOG_FILE is None
