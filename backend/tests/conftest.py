"""测试基础架构 —— 真实 ASGI 全栈、自动环境感知。

所有测试走真实后端链路：路由器 → 中间件（认证/IP封禁/请求日志）→ 服务层 → 数据库。
每个 fixture 返回真实对象，没有 MagicMock，没有模拟数据库。

环境策略（自动检测）：
  1. PostgreSQL + MinIO 可用 → 全真服务测试（Docker/CI/WSL 直连）
  2. 仅 SQLite + 本地文件系统 → 轻量本地测试（裸金属开发机）

可通过 ARCHE_TEST_DB_URL 环境变量强制指定数据库 URL，覆盖自动检测。
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.tests import test_env

logger = logging.getLogger(__name__)

# ── 测试环境变量（在导入任何 backend 模块前生效） ──────────────────────
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-0123456789"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["CORS_ORIGINS"] = "http://testserver"
os.environ["GITHUB_TOKEN"] = "test-github-token-for-pytest"
os.environ["ARCHE_TEST"] = "1"


# ── 启动日志 ─────────────────────────────────────────────────────────


def pytest_configure(config):
    """pytest 配置完成后输出环境检测报告。"""
    # 使用 print 而非 logger，确保在测试收集阶段可见
    print(f"\n[TestEnv] {test_env.describe_environment()}")
    db_url = test_env.recommended_db_url()
    if db_url:
        print(f"[TestEnv] Database: PostgreSQL ({db_url})")
    else:
        print("[TestEnv] Database: SQLite in-memory (per-test)")
    storage = test_env.recommended_storage()
    print(f"[TestEnv] Storage: {storage['strategy']}")


# ── 事件循环 ────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    """测试会话复用同一个事件循环（pytest-asyncio 要求）。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ── FastAPI 应用（function-scoped，每个测试独立 DB） ────────────────


def _setup_pg_schema(database_url: str, schema_name: str) -> str:
    """为 PostgreSQL 测试创建独立 schema。

    当使用 PostgreSQL 时，每个测试获得一个独立 schema，
    确保测试间完全隔离。测试结束后由 _teardown_pg_schema 清理。

    Args:
        database_url: 原始 PostgreSQL URL
        schema_name: 要创建的 schema 名称（如 test_a1b2c3d4）

    Returns:
        修改后的 database_url，包含 search_path 参数
    """
    import re

    if not database_url.startswith("postgresql"):
        return database_url  # 非 PostgreSQL 无需操作

    # 用简单连接创建 schema
    from sqlalchemy import text as sa_text
    from sqlalchemy.ext.asyncio import create_async_engine

    temp_engine = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    import asyncio

    async def _create():
        async with temp_engine.connect() as conn:
            await conn.execute(sa_text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            # 将后续连接的 search_path 设为该 schema
            await conn.execute(
                sa_text(f"SET search_path TO {schema_name}, public")
            )

    asyncio.get_running_loop().run_until_complete(_create())
    import asyncio as _asyncio

    _asyncio.get_event_loop().run_until_complete(temp_engine.dispose())

    # 为后续连接附加 search_path 参数
    # asyncpg 支持通过 connect_args 传递
    separator = "&" if "?" in database_url else "?"
    return f"{database_url}{separator}search_path={schema_name}"


async def _teardown_pg_schema(database_url: str, schema_name: str) -> None:
    """清理 PostgreSQL 测试 schema。"""
    if not database_url.startswith("postgresql"):
        return

    from sqlalchemy import text as sa_text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    async with engine.begin() as conn:
        await conn.execute(sa_text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
    await engine.dispose()


def _build_app(db_url: str):
    """构建 FastAPI 应用，使用指定数据库 URL。

    首次调用时发现插件并注册到全局 registry，
    后续调用复用已发现的插件列表，仅创建新的 FastAPI 实例。
    """
    import os

    # 确保测试环境变量始终覆盖
    os.environ["DATABASE_URL"] = db_url
    os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-0123456789"
    os.environ["LOG_LEVEL"] = "CRITICAL"
    os.environ["GITHUB_TOKEN"] = "test-github-token-for-pytest"

    from backend.core.config import config_manager

    # ConfigManager 是单例，_load 只执行一次。
    # 后续测试需要手动更新 _values 确保正确的数据库 URL。
    config_manager._values["DATABASE_URL"] = db_url
    config_manager._values["SECRET_KEY"] = "test-secret-key-for-pytest-0123456789"
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
    """创建真实 FastAPI 应用 —— 基于环境检测自动选择数据库。

    环境检测顺序：
      1. ARCHE_TEST_DB_URL 显式指定 → 使用该 URL
      2. PostgreSQL 端口可达     → 使用 PostgreSQL（全真测试）
      3. 降级                    → SQLite in-memory（本地轻量测试）

    隔离策略：
      - SQLite in-memory：每个测试独立数据库（天生隔离）
      - PostgreSQL：每个测试创建独立 schema（CREATE SCHEMA test_{uuid}）
        测试结束后 DROP SCHEMA CASCADE 自动清理
    """
    import uuid as _uuid

    # 自动检测数据库 URL
    db_url = test_env.recommended_db_url()
    use_pg = db_url.startswith("postgresql") if db_url else False

    # PostgreSQL：创建独立 schema 实现隔离
    pg_schema = None
    if use_pg:
        pg_schema = f"test_{_uuid.uuid4().hex[:12]}"
        db_url = _setup_pg_schema(db_url, pg_schema)
    else:
        # 降级：SQLite in-memory，每个测试独立
        db_id = _uuid.uuid4().hex[:12]
        db_url = (
            f"sqlite+aiosqlite:///file:arche_test_{db_id}"
            "?mode=memory&cache=shared&uri=true"
        )

    application = _build_app(db_url)

    # 确保表已创建 + 种子配置（所有 fixture 依赖 app 自动获得）
    from backend.core.config import config_manager
    from backend.core.db import ensure_tables
    from backend.core.db import session_factory as sf

    await ensure_tables()
    if sf is not None:
        config_manager.set_session_factory(sf)
        from backend.core import _seed_default_config

        await _seed_default_config(sf)

    yield application

    # 关闭数据库连接
    import backend.core.db as db_module
    from backend.core.db import close_db

    db_module._initialized = False
    await close_db()

    # PostgreSQL：清理独立 schema
    if pg_schema:
        original_url = test_env.recommended_db_url()
        if original_url.startswith("postgresql"):
            await _teardown_pg_schema(original_url, pg_schema)


# ── OSS 测试存储目录 ──────────────────────────────────────────────


@pytest.fixture
def oss_storage_dir(tmp_path) -> str:
    """为 OSS 测试创建临时存储目录，测试结束后自动清理。

    当 MinIO 不可用时，OSS 服务自动回退到本地文件系统。
    该 fixture 提供一个已存在的临时目录作为 OSS 存储根，
    替换 pytest.skip('目录未初始化')。
    """
    storage_path = tmp_path / "oss_storage"
    storage_path.mkdir(parents=True, exist_ok=True)
    os.environ["OSS_STORAGE_DIR"] = str(storage_path)
    return str(storage_path)


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
    from sqlalchemy import select

    from backend.core.container import container as global_container
    from backend.plugins.auth.models import User

    sf = global_container.get("db")["session_factory"]
    async with sf() as session:
        user = await session.scalar(
            select(User).where(User.username == reg_payload["username"])
        )
        user.level = 5
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
    from sqlalchemy import select

    from backend.core.container import container as global_container
    from backend.plugins.auth.models import User

    sf = global_container.get("db")["session_factory"]
    async with sf() as session:
        user = await session.scalar(
            select(User).where(User.username == reg_payload["username"])
        )
        user.level = 0
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
