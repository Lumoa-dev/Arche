"""插件配置基类。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PluginSettingsBase(BaseModel):
    """所有插件配置的基类。"""

    @classmethod
    def get_field_defaults(cls) -> dict[str, str]:
        """获取所有字段及其默认值，用于生成 .env.example。"""
        result = {}
        for name, field in cls.model_fields.items():
            default = field.default
            if default is None:
                result[name] = ""
            elif isinstance(default, (list, dict, set)):
                result[name] = str(default)
            else:
                result[name] = str(default)
        return result


def create_plugin_settings(
    name: str,
    fields: dict[str, type],
    defaults: dict[str, Any] | None = None,
) -> type[PluginSettingsBase]:
    """动态创建插件 Settings 类。"""
    from pydantic import create_model

    defaults = defaults or {}

    # 构造字段定义：(type, default_value)
    field_definitions = {}
    for field_name, field_type in fields.items():
        default = defaults.get(field_name, ...)
        field_definitions[field_name] = (field_type, default)

    # 动态创建模型，继承自PluginSettingsBase
    settings_class = create_model(  # type: ignore[call-overload]
        f"{name.title().replace('_', '')}Settings",
        __base__=PluginSettingsBase,
        **field_definitions,
    )

    return settings_class
