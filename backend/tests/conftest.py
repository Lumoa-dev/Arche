"""测试基础架构 —— 真实 ASGI 全栈、真实数据库、零 Mock。

所有测试走真实后端链路：路由器 → 中间件（认证/IP封禁/请求日志）→ 服务层 → 数据库。
每个 fixture 返回真实对象，没有 MagicMock，没有模拟数据库。

数据库策略：
  - 使用文件型 SQLite（`test_arche.db`）确保 Alembic 迁移正常工作
  - 会话级作用域复用，降低创建开销
  - CI 中可通过 `ARCHE_TEST_DB_URL` 环境变量切换为 PostgreSQL
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ── 测试环境变量（在导入任何 backend 模块前生效） ──────────────────────
_TEST_DB = str(Path(__file__).parent / "test_arche.db")
# 直接覆盖 os.environ（防止 .env 文件中的值通过 ConfigManager 读取）
os.environ["DATABASE_URL"] = os.environ.get(
    "ARCHE_TEST_DB_URL", f"sqlite+aiosqlite:///{_TEST_DB}"
)
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


# ── FastAPI 应用 ────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session")
async def app():
    """创建真实 FastAPI 应用 —— 所有插件激活、文件型 SQLite 数据库。

    使用 TestClient 触发 lifespan startup（Alembic 迁移、建表、种子配置），
    之后 async_client 使用纯 ASGI transport（lifespan 已运行无需再次触发）。
    """
    # 清理上次测试的数据库文件
    db_path = Path(_TEST_DB)
    if db_path.exists():
        db_path.unlink()

    from backend.core.plugin_registry import discover_plugins, registry

    registry.reset()
    discover_plugins()

    from backend.core import create_app

    application = create_app()

    # 使用 TestClient 触发 lifespan startup（迁移、建表、种子配置、on_startup 钩子）
    from fastapi.testclient import TestClient

    with TestClient(application) as test_client:
        # 发一个请求确保 startup 完成
        test_client.get("/api/ping")

        yield application

    # 关闭数据库连接
    from backend.core.db import close_db

    await close_db()

    # 清理数据库文件
    try:
        db_path = Path(_TEST_DB)
        if db_path.exists():
            db_path.unlink()
    except PermissionError:
        pass  # Windows 上可能被缓存占用


# ── HTTP 客户端 ────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """异步 HTTP 客户端 —— 走真实 ASGI 全栈。

    httpx.AsyncClient 的 ASGITransport 会在进入/退出时自动触发
    lifespan startup/shutdown 事件。
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture
def client(app):
    """同步 TestClient —— 适用于不涉及 async 断言的纯路由测试。

    FastAPI 的 TestClient 内部使用 httpx，会自动管理 lifespan 事件。
    """
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


# ── 认证工具 ────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def auth_headers(async_client: httpx.AsyncClient) -> dict[str, str]:
    """注册一个普通测试用户并返回 JWT 认证头。

    创建用户 → 登录 → 提取 access_token → 返回 Authorization header。
    """
    user_suffix = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"test_{user_suffix}@example.com",
        "username": f"testuser_{user_suffix}",
        "nickname": f"测试用户_{user_suffix}",
        "password": "TestPass123!",
    }

    # 注册
    resp = await async_client.post("/api/auth/register", json=reg_payload)
    assert resp.status_code == 200, f"注册失败: {resp.text}"

    # 登录
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
    """注册 P0 管理员用户并返回 JWT 认证头。

    注册后通过数据库直接设置 level=0，确保拥有管理员权限。
    """
    user_suffix = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"admin_{user_suffix}@example.com",
        "username": f"admin_{user_suffix}",
        "nickname": f"管理员_{user_suffix}",
        "password": "AdminPass123!",
    }

    resp = await async_client.post("/api/auth/register", json=reg_payload)
    assert resp.status_code == 200, f"管理员注册失败: {resp.text}"

    # 手动将用户等级设为 P0（确保即使不是第一个注册用户也能当管理员）
    from sqlalchemy import select, update

    from backend.plugins.auth.models import User

    # 通过 app 的 session_factory 直接操作数据库
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

    # 重新登录获取带 level=0 信息的 JWT
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
    """返回一个真实的数据库会话 —— 可进行 CRUD 断言。

    使用 app.state.container 中注册的 session_factory 创建会话。
    """
    from backend.core.container import container as global_container

    sf: async_sessionmaker[AsyncSession] | None = None

    # 尝试从 app state 获取
    if hasattr(app.state, "container"):
        try:
            db = app.state.container.get("db")
            sf = db.get("session_factory")
        except Exception:
            pass

    # 兜底：全局容器
    if sf is None and global_container.is_available("db"):
        db = global_container.get("db")
        sf = db.get("session_factory")

    assert sf is not None, "无法获取 session_factory，应用可能未正确初始化"

    async with sf() as session:
        yield session
