"""配置管理 —— 统一环境变量 + pydantic-settings + 数据库缓存。"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic_settings import BaseSettings

from .settings import AppSettings


class PluginSettingsRegistry:
    """插件配置注册表。"""

    def __init__(self) -> None:
        self._registry: dict[str, type[BaseSettings]] = {}

    def register(self, name: str, settings_class: type[BaseSettings]) -> None:
        """注册插件配置类。"""
        self._registry[name] = settings_class

    def get(self, name: str) -> type[BaseSettings] | None:
        """获取插件配置类。"""
        return self._registry.get(name)

    def get_all(self) -> dict[str, type[BaseSettings]]:
        """获取所有注册的插件配置。"""
        return dict(self._registry)

    def items(self):
        """遍历所有插件配置。"""
        return self._registry.items()


class ConfigManager:
    """
    统一配置管理器。

    分层：.env 文件 < 环境变量 < 数据库（缓存）
    """

    _instance: ConfigManager | None = None

    def __new__(cls, env_file: str = ".env") -> ConfigManager:  # noqa: ARG004
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # type: ignore[has-type]
        return cls._instance

    def __init__(self, env_file: str = ".env") -> None:
        if self._initialized:  # type: ignore[has-type]
            return
        self._initialized = True

        self._env_file = env_file
        self._app_settings: AppSettings | None = None
        self._plugin_registry = PluginSettingsRegistry()
        self._values: dict[str, str] = {}
        self._session_factory: Any | None = None
        self._cache: dict[str, tuple[str, float]] = {}
        self._cache_ttl: int = 60
        self._load()

    def _load(self) -> None:
        """加载 .env 文件和环境变量。"""
        path = Path(self._env_file)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                self._values[key.strip()] = value.strip().strip("\"'")

        # 操作系统环境变量覆盖 .env
        for key, value in os.environ.items():
            self._values[key] = value

    def get(self, key: str, default: str | None = None) -> str | None:
        """获取配置值，分层读取：内存 > DB缓存 > .env/环境变量 > 默认值。"""
        # 第一层：内存中的值（最高优先级）
        if key in self._values:
            return self._values[key]

        # 第二层：数据库缓存
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            del self._cache[key]

        # 第三层：从数据库查询
        if self._session_factory:
            db_value = self._fetch_from_db(key)
            if db_value is not None:
                self._cache[key] = (db_value, time.time() + self._cache_ttl)
                return db_value

        return default

    def _fetch_from_db(self, key: str) -> str | None:
        """从数据库查询配置。"""
        factory = self._session_factory
        if factory is None:
            return None
        try:
            import asyncio

            from sqlalchemy import select

            from backend.core.models import ConfigEntry

            async def _query():
                async with factory() as session:
                    result = await session.execute(
                        select(ConfigEntry).where(ConfigEntry.key == key)
                    )
                    entry = result.scalar_one_or_none()
                    return entry.value if entry else None

            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(asyncio.run, _query()).result(timeout=5)
        except Exception:
            return None

    def get_required(self, key: str) -> str:
        """获取必填配置值。"""
        value = self.get(key)
        if value is None:
            raise RuntimeError(f"Required config '{key}' is not set")
        return value

    def set(self, key: str, value: str) -> None:
        """设置配置值（仅内存）。"""
        self._values[key] = value

    def set_session_factory(self, session_factory) -> None:
        """注入数据库会话工厂，启用 DB 回退。"""
        self._session_factory = session_factory

    def invalidate_cache(self, key: str | None = None) -> None:
        """清除缓存。"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    @property
    def app_settings(self) -> AppSettings:
        """获取应用设置（懒加载）。"""
        if self._app_settings is None:
            env_dict = {
                k: v
                for k, v in self._values.items()
                if k
                in [
                    "DATABASE_URL",
                    "SECRET_KEY",
                    "CORS_ORIGINS",
                    "LOG_LEVEL",
                    "LOG_FILE",
                ]
            }
            self._app_settings = AppSettings(**env_dict)
        return self._app_settings

    @property
    def plugins(self) -> PluginSettingsRegistry:
        """获取插件配置注册表。"""
        return self._plugin_registry

    def register_plugin_settings(
        self, name: str, settings_class: type[BaseSettings]
    ) -> None:
        """注册插件配置类。"""
        self._plugin_registry.register(name, settings_class)

    def generate_env_example(self) -> str:
        """生成完整的 .env.example 文件内容。"""
        lines = [
            "# === Core Settings ===",
            "DATABASE_URL=sqlite+aiosqlite:///./data/arche.db",
            "SECRET_KEY=change-me-to-random-string",
            "CORS_ORIGINS=http://localhost:5173",
            "LOG_LEVEL=INFO",
            "# LOG_FILE=/path/to/logfile.log",
            "",
        ]

        for name, settings_class in self._plugin_registry.items():
            lines.append(f"# === {name.upper()} ===")
            try:
                for field_name, field in settings_class.model_fields.items():
                    default = field.default
                    if default is None:
                        default_str = ""
                    elif isinstance(default, (list, dict, set)):
                        default_str = (
                            ",".join(str(v) for v in default) if default else ""
                        )
                    else:
                        default_str = str(default)
                    lines.append(f"{field_name}={default_str}")
            except Exception:
                pass
            lines.append("")

        return "\n".join(lines)

    def reload(self) -> None:
        """重新加载配置。"""
        self._values.clear()
        self._cache.clear()
        self._load()
        self._app_settings = None


# 全局单例实例
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """获取全局配置管理器实例。"""
    return config_manager
