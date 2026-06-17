"""插件级测试工具 —— 按需激活指定插件进行独立测试。

与根 conftest.py 不同，本 conftest 会覆盖 async_client 等核心 fixture，
为每个插件测试自动构建仅包含目标插件及其依赖的独立应用，实现测试隔离。

使用方式：
    测试类定义 plugin_name 类属性即可自动获得隔离的测试环境：

        class TestBlogPosts:
            plugin_name = "blog"

            @pytest.mark.asyncio
            async def test_create_post(self, async_client, auth_headers):
                ...

    如果不设置 plugin_name，会从测试文件所在目录名自动推断。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI


# ── 插件名自动推断 ──────────────────────────────────────────────────


def _resolve_plugin_name(request: pytest.FixtureRequest) -> str:
    """从测试类/模块/目录名推断插件名。"""
    # 1. 测试类的 plugin_name 属性
    cls_name = getattr(getattr(request, "cls", None), "plugin_name", None)
    if cls_name:
        return cls_name
    # 2. 测试模块的 plugin_name 属性
    mod_name = getattr(request.module, "plugin_name", None)
    if mod_name:
        return mod_name
    # 3. 测试文件所在目录名
    dir_name = Path(request.fspath).parent.name
    if dir_name and not dir_name.startswith("_"):
        return dir_name
    raise ValueError(
        "无法推断插件名：请在测试类中设置 plugin_name = \"xxx\"，"
        "或将测试文件放在以插件名命名的目录下"
    )


# ── 插件应用构建 ────────────────────────────────────────────────────


def _build_plugin_app(plugin_name: str) -> FastAPI:
    """构建仅包含指定插件及其依赖的 FastAPI 应用。

    1. 重置插件注册表
    2. 发现所有插件
    3. 激活目标插件 + 所有它 require/optional 的依赖
    4. 返回已配置的应用实例
    """
    from backend.core.container import ServiceContainer
    from backend.core.db import init_db
    from backend.core.middleware import (
        register_error_handlers,
        setup_cors,
        setup_security_headers,
    )
    from backend.core.plugin_registry import discover_plugins, registry

    registry.reset()
    discover_plugins()

    # 创建独立的 DI 容器
    container = ServiceContainer()

    # 注册配置
    from backend.core.config import config_manager

    container.register("config", lambda c: config_manager)

    # 初始化数据库
    import os
    from pathlib import Path

    db_path = Path(__file__).resolve().parent / f"test_{plugin_name}.db"
    if db_path.exists():
        db_path.unlink()

    os.environ["GITHUB_TOKEN"] = "test-github-token-for-pytest"

    database_url = os.environ.get("ARCHE_TEST_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    engine, session_factory = init_db(database_url)
    container.register(
        "db", lambda c: {"engine": engine, "session_factory": session_factory}
    )

    # 创建 FastAPI 应用
    app = FastAPI(title=f"Arche Plugin Test ({plugin_name})", version="0.1.0")
    app.state.container = container

    # 同步到模块级单例，供 auth_headers 等依赖全局容器的 fixture 使用
    from backend.core import container as _container_mod

    _container_mod.container = container

    # 收集目标插件及其所有依赖
    plugin_obj = registry._plugins.get(plugin_name)
    if plugin_obj is None:
        raise ValueError(
            f"插件 '{plugin_name}' 未注册，可用插件: {list(registry._plugins.keys())}"
        )

    deps = set()
    deps.add(plugin_name)
    for dep_name in getattr(plugin_obj, "requires", []):
        deps.add(dep_name)
    for dep_name in getattr(plugin_obj, "optional", []):
        if dep_name in registry._plugins:
            deps.add(dep_name)

    # 按拓扑序激活
    ordered = registry._topological_sort()
    for name in ordered:
        if name in deps:
            registry.activate(name, app)

    # 注册服务
    for name in ordered:
        if name in deps:
            plugin = registry._plugins[name]
            if hasattr(plugin, "register_services"):
                plugin.register_services(container)

    # 中间件
    setup_cors(app, ["*"])
    register_error_handlers(app)
    setup_security_headers(app)

    # 建表
    import asyncio

    async def _create_tables():
        async with engine.begin() as conn:
            from backend.core.db import Base

            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    return app


@pytest.fixture
def plugin_app(request) -> FastAPI:
    """Fixture 工厂 —— 返回一个仅包含指定插件的应用。

    用法：
        def test_something(plugin_app):
            app = plugin_app("blog")
            ...
    """
    return _build_plugin_app


@pytest_asyncio.fixture
async def plugin_client(plugin_app, request) -> httpx.AsyncClient:
    """Fixture 工厂 —— 返回指定插件的异步 HTTP 客户端。

    用法：
        async def test_route(plugin_client):
            client = await plugin_client("blog")
            resp = await client.get("/api/blog/posts")
    """
    # 尝试从 request.param 获取插件名（用于 parametrize）
    plugin_name = getattr(request, "param", None) or "auth"

    app = _build_plugin_app(plugin_name)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    yield client
    await client.aclose()


# ── 覆盖根 conftest 的核心 fixture ─────────────────────────────────
#
# 这些 fixture 与根 conftest.py 的同名 fixture 完全兼容，
# 但构建的应用只包含当前插件（及其依赖），而非所有 13 个插件。
# pytest 会优先使用最近 conftest 中的 fixture，因此插件测试
# 会自动使用下方的隔离版本。
#
# 依赖的 fixture（auth_headers、admin_headers）仍从根 conftest
# 解析，但它们依赖的 async_client 会在此处被覆盖，从而实现
# 自动全链路隔离。


@pytest_asyncio.fixture
async def async_client(request) -> AsyncGenerator[httpx.AsyncClient, None]:
    """基于插件隔离的异步 HTTP 客户端。

    自动从测试类/模块的 plugin_name 属性或测试文件目录名推断插件名，
    构建仅包含该插件（及其依赖）的独立应用。
    """
    plugin_name = _resolve_plugin_name(request)
    app = _build_plugin_app(plugin_name)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client
