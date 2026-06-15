"""云训练 Provider 注册表和工厂。"""

from __future__ import annotations

from .base import CloudProvider

_providers: dict[str, type[CloudProvider]] = {}


def register(name: str, provider_class: type[CloudProvider]) -> None:
    """注册一个 Provider。"""
    _providers[name] = provider_class


def get_provider(name: str, credentials: dict | None = None) -> CloudProvider:
    """根据名称获取 Provider 实例。"""
    if name not in _providers:
        available = list(_providers.keys())
        raise ValueError(f"未知的 Provider: {name}，可用的有: {available}")
    return _providers[name](credentials or {})


# 启动时自动注册
def _auto_register():
    from .aliyun import AliyunProvider
    from .mock import MockProvider
    from .zhixingyun import ZhixingyunProvider

    register("mock", MockProvider)
    register("aliyun", AliyunProvider)
    register("zhixingyun", ZhixingyunProvider)


_auto_register()
