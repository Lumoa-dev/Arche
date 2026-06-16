"""测试基础架构 —— 真实 ASGI 全栈、真实数据库、零 Mock。

所有测试走真实后端链路：路由器 → 中间件（认证/IP封禁/请求日志）→ 服务层 → 数据库。
每个 fixture 返回真实对象，没有 MagicMock，没有模拟数据库。

数据库策略：
  - 每个测试使用独立 SQLite 文件（tmp_path），完全隔离
  - 启动时执行 Alembic 迁移 + ensure_tables + 种子配置
  - CI 中可通过 `ARCHE_TEST_DB_URL` 环境变量切换为 PostgreSQL
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ── 测试环境变量（在导入任何 backend 模块前生效） ──────────────────────
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["CORS_ORIGINS"] = "http://testserver"
os.environ["ARCHE_TEST"] = "1"


# ── 事件循环 ────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    """测试会话复用同一个事件循环（pytest-asyncio 要求）。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ── FastAPI 应用（function-scoped，每个测试独立 DB） ────────────────


def _build_app(db_url: str):
    """构建 FastAPI 应用，使用指定数据库 URL。

    首次调用时发现插件并注册到全局 registry，
    后续调用复用已发现的插件列表，仅创建新的 FastAPI 实例。
    """
    import os

    # 确保测试环境变量始终覆盖
    os.environ["DATABASE_URL"] = db_url
    os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"
    os.environ["LOG_LEVEL"] = "CRITICAL"

    from backend.core.config import config_manager

    # ConfigManager 是单例，_load 只执行一次。
    # 后续测试需要手动更新 _values 确保正确的数据库 URL。
    config_manager._values["DATABASE_URL"] = db_url
    config_manager._values["SECRET_KEY"] = "test-secret-key-for-pytest"
    config_manager._values["LOG_LEVEL"] = "CRITICAL"
    config_manager._cache.clear()
    config_manager._app_settings = None

    from backend.core.plugin_registry import discover_plugins, registry

    if not registry.available:
        discover_plugins()

    from backend.core import create_app

    return create_app()


@pytest_asyncio.fixture
async def app():
    """创建真实 FastAPI 应用 —— 所有插件激活，独立 in-memory SQLite。

    每个测试获得独立的 in-memory 数据库，通过 async_client 或 db_session
    自动触发 ensure_tables 建表。测试结束时自动清理。
    """
    import uuid as _uuid

    db_id = _uuid.uuid4().hex[:12]
    db_url = os.environ.get(
        "ARCHE_TEST_DB_URL",
        f"sqlite+aiosqlite:///file:arche_test_{db_id}?mode=memory&cache=shared&uri=true",
    )

    application = _build_app(db_url)

    # 确保表已创建 + 种子配置（所有 fixture 依赖 app 自动获得）
    from backend.core.db import ensure_tables, session_factory as sf
    from backend.core.config import config_manager

    await ensure_tables()
    if sf is not None:
        config_manager.set_session_factory(sf)
        from backend.core import _seed_default_config
        await _seed_default_config(sf)

    yield application

    # 关闭数据库连接
    from backend.core.db import close_db
    import backend.core.db as db_module

    db_module._initialized = False
    await close_db()

    # TestClient shutdown 已触发 close_db()，无需重复调用


# ── HTTP 客户端 ────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """异步 HTTP 客户端 —— 走真实 ASGI 全栈。"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client




# ── 认证工具 ────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def auth_headers(async_client: httpx.AsyncClient) -> dict[str, str]:
    """注册普通测试用户并返回 JWT 认证头。"""
    user_suffix = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"test_{user_suffix}@example.com",
        "username": f"testuser_{user_suffix}",
        "nickname": f"测试用户_{user_suffix}",
        "password": "TestPass123!",
    }

    resp = await async_client.post("/api/auth/register", json=reg_payload)
    assert resp.status_code == 200, f"注册失败: {resp.text}"

    # 普通用户设为 level=5（第一个注册用户会默认得到 level=0）
    from sqlalchemy import select, update
    from backend.plugins.auth.models import User
    from backend.core.container import container as global_container

    sf = global_container.get("db")["session_factory"]
    async with sf() as session:
        result = await session.execute(
            select(User).where(User.username == reg_payload["username"])
        )
        user = result.scalar_one()
        await session.execute(
            update(User).where(User.id == user.id).values(level=5)
        )
        await session.commit()

    login_payload = {
        "identity": reg_payload["username"],
        "password": reg_payload["password"],
    }
    resp = await async_client.post("/api/auth/login", json=login_payload)
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    data = resp.json()
    token = data["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(async_client: httpx.AsyncClient) -> dict[str, str]:
    """注册 P0 管理员用户并返回 JWT 认证头。"""
    user_suffix = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"admin_{user_suffix}@example.com",
        "username": f"admin_{user_suffix}",
        "nickname": f"管理员_{user_suffix}",
        "password": "AdminPass123!",
    }

    resp = await async_client.post("/api/auth/register", json=reg_payload)
    assert resp.status_code == 200, f"管理员注册失败: {resp.text}"

    # 手动将用户等级设为 P0
    from sqlalchemy import select, update

    from backend.plugins.auth.models import User

    from backend.core.container import container as global_container

    sf = global_container.get("db")["session_factory"]
    async with sf() as session:
        result = await session.execute(
            select(User).where(User.username == reg_payload["username"])
        )
        user = result.scalar_one()
        await session.execute(
            update(User).where(User.id == user.id).values(level=0)
        )
        await session.commit()

    login_payload = {
        "identity": reg_payload["username"],
        "password": reg_payload["password"],
    }
    resp = await async_client.post("/api/auth/login", json=login_payload)
    assert resp.status_code == 200, f"管理员登录失败: {resp.text}"
    data = resp.json()
    token = data["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}


# ── 数据库会话 ──────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session(app) -> AsyncGenerator[AsyncSession, None]:
    """返回真实数据库会话。"""
    from backend.core.container import container as global_container

    sf: async_sessionmaker[AsyncSession] | None = None

    if hasattr(app.state, "container"):
        try:
            db = app.state.container.get("db")
            sf = db.get("session_factory")
        except Exception:
            pass

    if sf is None and global_container.is_available("db"):
        db = global_container.get("db")
        sf = db.get("session_factory")

    assert sf is not None, "无法获取 session_factory"

    async with sf() as session:
        yield session
