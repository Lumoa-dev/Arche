"""pytest 配置和共享 fixture。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402

# =============================================================================
# 自动 marker 分层 + 本地智能测试（按 diff 跳过）
# =============================================================================
INTEGRATION_DIR = (Path(__file__).parent / "integration").resolve()
E2E_DIR = (Path(__file__).parent / "e2e").resolve()

# 测试目录 → 源码目录映射（用于 diff 判断）
# 改 backend/core/ 中的文件 → 跑 unit/core/
# 改 backend/plugins/auth/ 中的文件 → 跑 unit/auth/ + 集成测试
TEST_SOURCE_MAP = {
    "unit/core/": ["backend/core/"],
    "unit/auth/": ["backend/plugins/auth/", "backend/core/"],
    "unit/blog/": ["backend/plugins/blog/", "backend/core/"],
    "unit/oss/": ["backend/plugins/oss/", "backend/core/"],
    "unit/github_proxy/": ["backend/plugins/github_proxy/", "backend/core/"],
    "unit/crawler/": ["backend/plugins/crawler/", "backend/core/"],
    "unit/cloud_integration/": ["backend/plugins/cloud_integration/", "backend/core/"],
    "unit/monitor/": ["backend/plugins/monitor/", "backend/core/"],
    "unit/asset_mgmt/": ["backend/plugins/asset_mgmt/", "backend/core/"],
    "unit/system_monitor/": ["backend/plugins/system_monitor/", "backend/core/"],
    "integration/": None,  # 集成测试：任一 backend 文件变化就跑
    "e2e/": "__never__",  # E2E 永不自动跑
}

# 总在 diff 模式中包含的测试（核心基础设施变更）
CORE_DIRS = ["backend/core/", "backend/tests/conftest.py", "pyproject.toml"]


def pytest_addoption(parser):
    """添加自定义选项。"""
    parser.addoption(
        "--all",
        action="store_true",
        default=False,
        help="本地全量跑（默认是按 diff 智能跳过）",
    )


def _get_changed_files() -> set[str]:
    """获取与 master/main 相比有变更的文件列表。"""
    # 优先用 CI 提供的变更列表
    if os.environ.get("GITHUB_EVENT_NAME"):
        return set()

    for branch in ("HEAD~1", "main", "master"):
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", branch],
                capture_output=True,
                text=True,
                check=True,
                cwd=PROJECT_ROOT,
            )
            files = {f.strip() for f in result.stdout.split("\n") if f.strip()}
            if files:
                return files
        except subprocess.CalledProcessError:
            continue
    return set()


def _is_test_for_source(test_rel: str, changed: set[str]) -> bool:
    """判断某个测试是否针对有变更的源码。"""
    for test_dir, source_dirs in TEST_SOURCE_MAP.items():
        if test_rel.startswith(test_dir):
            if source_dirs is None:
                # 集成测试：只要 backend 源码变了就跑
                return any(
                    f.startswith("backend/") and not f.startswith("backend/tests/")
                    for f in changed
                )
            if source_dirs == "__never__":
                return False
            # 单元测试：对应源码目录有变更就跑
            return any(any(f.startswith(s) for f in changed) for s in source_dirs)
    # 其他测试（不在映射表中）保守跑
    return True


def pytest_collection_modifyitems(config, items):
    """自动标记 + 智能跳过。

    标记：
    - integration/ 下的测试自动加 integration marker
    - e2e/ 下的测试自动加 e2e marker

    智能跳过（本地 diff 模式）：
    - 没加 --all 且不在 CI 环境时，自动跳过未变更插件的测试
    """
    # ── 自动打 marker ──
    for item in items:
        try:
            test_path = Path(item.fspath).resolve()
        except (TypeError, ValueError):
            continue
        try:
            test_path.relative_to(INTEGRATION_DIR)
            item.add_marker(pytest.mark.integration)
        except ValueError:
            pass
        try:
            test_path.relative_to(E2E_DIR)
            item.add_marker(pytest.mark.e2e)
        except ValueError:
            pass

    # ── 智能跳过（本地 diff 模式） ──
    is_full = config.getoption("--all", default=False) or os.environ.get("CI")
    if is_full:
        return

    changed = _get_changed_files()
    if not changed:
        return

    # 检查是否有任何核心文件变更（有则全部跑）
    core_changed = any(any(f.startswith(c) for f in changed) for c in CORE_DIRS)
    if core_changed:
        return

    deselected = []
    for item in items:
        try:
            test_rel = Path(item.fspath).resolve().relative_to(Path(__file__).parent)
            test_rel_str = str(test_rel.as_posix())
        except (TypeError, ValueError):
            continue

        if not _is_test_for_source(test_rel_str, changed):
            deselected.append(item)

    if deselected:
        items[:] = [i for i in items if i not in deselected]
        config.hook.pytest_deselected(items=deselected)
        print(f"\n🔍 Diff 模式：跳过了 {len(deselected)} 个未变更插件的测试")
        print("   用 --all 参数运行全量测试\n")


# =============================================================================
# 基础 Fixture
# =============================================================================


@pytest.fixture
def fake_container():
    """假的服务容器，模拟 config 返回测试值。"""
    container = MagicMock()

    class FakeConfig:
        _values = {  # noqa: RUF012
            "GITHUB_TOKEN": "test_token",
            "GITHUB_CACHE_TTL": 300,
            "GITHUB_TIMEOUT": 10,
            "GITHUB_DEFAULT_MODE": "auto",
            "SECRET_KEY": "test_secret_key_12345",
        }

        def get_required(self, key):
            return self._values.get(key, "")

        def get(self, key, default=None):
            return self._values.get(key, default)

    container.get.return_value = FakeConfig()
    # Mock oss_rate_limiter，避免测试时需要真实的 RateLimiter
    mock_limiter = MagicMock()
    mock_limiter.consume = AsyncMock()

    def _fake_container_get(name):
        if name == "config":
            return FakeConfig()
        return mock_limiter

    container.get = _fake_container_get
    return container


@pytest.fixture
def anyio_backend():
    """asyncio 后端配置。"""
    return "asyncio"


# =============================================================================
# 数据库 Fixture
# =============================================================================


@pytest.fixture
async def module_db():
    """创建独立的内存数据库引擎和表，每个测试函数独立使用。

    返回: {"engine": engine, "session_factory": session_factory}
    """
    from sqlalchemy.ext.asyncio import (
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.pool import StaticPool

    # 确保模型在 create_all 前已导入并注册到 Base.metadata
    from backend.core import models as _core_models  # noqa: F401
    from backend.core.db import Base
    from backend.plugins.asset_mgmt import models as _asset_models  # noqa: F401
    from backend.plugins.auth import models as _auth_models  # noqa: F401
    from backend.plugins.blog import models as _blog_models  # noqa: F401
    from backend.plugins.cloud_integration import models as _cloud_models  # noqa: F401
    from backend.plugins.crawler import models as _crawler_models  # noqa: F401
    from backend.plugins.monitor import models as _monitor_models  # noqa: F401
    from backend.plugins.oss import models as _oss_models  # noqa: F401

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    yield {"engine": engine, "session_factory": session_factory}

    await engine.dispose()


@pytest.fixture
async def in_memory_db(module_db):
    """函数级 fixture：每个测试结束后清理所有数据。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from backend.core.db import Base

    engine = module_db["engine"]
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    yield {"engine": engine, "session_factory": session_factory}

    async with session_factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest.fixture
async def db_container(in_memory_db, fake_container):
    """带有真实内存数据库的 fake container。"""

    class FakeConfigWithDb:
        _values = {  # noqa: RUF012
            "GITHUB_TOKEN": "test_token",
            "GITHUB_CACHE_TTL": 300,
            "GITHUB_TIMEOUT": 10,
            "GITHUB_DEFAULT_MODE": "auto",
            "SECRET_KEY": "test_secret_key_12345",
        }

        def __init__(self):
            self._session_factory = in_memory_db["session_factory"]

        def get_required(self, key):
            return self._values.get(key, "")

        def get(self, key, default=None):
            return self._values.get(key, default)

        def invalidate_cache(self, key=None):
            return None

    # get_service 使用的缓存，避免 MagicMock 的 hasattr 总是返回 True
    _auth_cache = {"instance": None}

    def get_service(name):
        if name == "db":
            return in_memory_db
        elif name == "config":
            return FakeConfigWithDb()
        elif name == "auth":
            from backend.plugins.auth.services import AuthService

            # 单例：缓存 AuthService 实例，确保限流器/黑名单状态跨请求保持
            if _auth_cache["instance"] is None:
                _auth_cache["instance"] = AuthService(fake_container)
            return _auth_cache["instance"]
        elif name == "blog":
            from backend.plugins.blog.services import BlogService

            return BlogService(fake_container)
        elif name == "github":
            from backend.plugins.github_proxy.services import GitHubService

            return GitHubService(fake_container)
        elif name == "storage":
            from backend.plugins.oss.services import StorageService

            return StorageService(fake_container)
        elif name == "asset_mgmt":
            from backend.plugins.asset_mgmt.services import AssetMgmtService

            return AssetMgmtService(fake_container)
        elif name == "oss_rate_limiter":
            limiter = AsyncMock()
            limiter.consume = AsyncMock()
            return limiter
        service = AsyncMock()
        service.get.return_value = "mock"
        return service

    fake_container.get = get_service
    return fake_container


# =============================================================================
# Mock 辅助函数
# =============================================================================


def mock_subprocess_success(stdout: bytes = b'{"ok": true}', stderr: bytes = b""):
    """创建成功的 subprocess mock。"""

    class MockProc:
        returncode = 0

        async def communicate(self, input=None):
            return stdout, stderr

        async def wait(self):
            return 0

    return MockProc()


def mock_subprocess_failure(exit_code: int = 1, stderr: bytes = b"error"):
    """创建失败的 subprocess mock。"""

    class MockProc:
        returncode = exit_code

        async def communicate(self, input=None):
            return b"", stderr

    return MockProc()


def patch_container_service(container, name: str, service):
    """把 ``container.get(name)`` 临时替换成 ``service``，其它名字透传旧 get。"""
    old_get = container.get

    def _get(n: str):
        if n == name:
            return service
        return old_get(n)

    container.get = _get
    return service


# =============================================================================
# 集成测试 Fixture
# =============================================================================


@pytest.fixture
async def test_app(db_container):
    """创建真实的 FastAPI 测试应用，带内存数据库。"""
    from fastapi import FastAPI

    from backend.core.middleware import register_error_handlers
    from backend.core.plugin_registry import discover_plugins, registry
    from backend.plugins.auth.middleware import AuthMiddleware

    # 如果已有插件注册（单元测试已导入），不做 reset 以免丢失；
    # 否则从零发现注册。
    if not registry.available:
        registry.reset()
        discover_plugins()
    else:
        # 补充发现尚未注册的插件
        discover_plugins()

    app = FastAPI(title="Test Arche")
    app.state.container = db_container

    register_error_handlers(app)
    registry.activate_all(app)
    registry.register_services(db_container)

    secret_key = db_container.get("config").get_required("SECRET_KEY")
    app.add_middleware(AuthMiddleware, secret_key=secret_key)

    yield app


@pytest.fixture
async def client(test_app):
    """HTTP 测试客户端。"""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def auth_headers(db_container):
    """获取已认证用户的请求头。"""
    from backend.plugins.auth.services import AuthService

    service = AuthService(db_container)
    await service.register(
        email="admin@example.com",
        username="admin",
        nickname="test_user",
        password="admin123",
    )
    result = await service.register(
        email="test@example.com",
        username="testuser",
        nickname="test_user",
        password="testpass123",
    )
    return {"Authorization": f"Bearer {result['access_token']}"}


@pytest.fixture
async def admin_headers(db_container):
    """获取管理员的请求头。"""
    from backend.plugins.auth.services import AuthService

    service = AuthService(db_container)
    result = await service.register(
        email="admin@example.com",
        username="admin",
        nickname="test_user",
        password="admin123",
    )
    return {"Authorization": f"Bearer {result['access_token']}"}


# =============================================================================
# Crawler Fixture
# =============================================================================


@pytest.fixture
def crawler_sample_url():
    return "https://example.com/article/hello"


@pytest.fixture
def crawler_sample_html():
    return """
    <html>
      <head><title>Test Article</title></head>
      <body>
        <main>
          <p>This is crawler sample content with enough characters for quality checks.</p>  # noqa: E501
          <a href="/next">Next</a>
          <a href="https://example.com/about">About</a>
        </main>
      </body>
    </html>
    """


@pytest.fixture
def crawler_item_factory():
    from backend.plugins.crawler.pipeline import CrawlItem

    def _create(**kwargs):
        defaults = {
            "url": "https://example.com/article/hello",
            "source": "example.com",
            "status_code": 200,
            "quality_passed": True,
            "headers": {"content-type": "text/html"},
        }
        defaults.update(kwargs)
        return CrawlItem(**defaults)

    return _create


# =============================================================================
# Monitor Fixture
# =============================================================================


@pytest.fixture
def monitor_template_payload():
    return {
        "name": "CPU Dashboard",
        "components": [{"id": "cpu", "type": "metric"}],
        "refresh_interval": 15,
    }
