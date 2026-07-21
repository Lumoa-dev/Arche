"""配置管理路由单元测试 —— CRUD、敏感字段掩码、缓存失效。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from backend.core.middleware import register_error_handlers
from backend.core.plugin_registry import discover_plugins, registry


# =============================================================================
# 辅助 Fixture
# =============================================================================


@pytest.fixture
async def config_app(in_memory_db, fake_container):
    """创建仅含 config_mgmt 路由的测试应用。"""

    class FakeConfigWithDb:
        def __init__(self):
            self._session_factory = in_memory_db["session_factory"]
            self._cache_invalidated = False

        def get(self, key, default=None):
            return default

        def invalidate_cache(self, key=None):
            self._cache_invalidated = True

    app = FastAPI(title="Config Test")
    app.state.container = fake_container
    register_error_handlers(app)

    # 添加认证中间件：设置管理员用户（level=0）
    from starlette.middleware.base import BaseHTTPMiddleware

    class FakeAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.user = {
                "id": 1,
                "email": "admin@example.com",
                "username": "admin",
                "level": 0,
            }
            return await call_next(request)

    app.add_middleware(FakeAuthMiddleware)

    # 注册 config_mgmt 路由
    from backend.plugins.config_mgmt.routes import router as config_router

    app.include_router(config_router)

    # 将 config 替换为带 DB 的版本
    config_with_db = FakeConfigWithDb()
    fake_container.get = lambda name: (
        config_with_db if name == "config" else fake_container.get(name)
    )

    yield app


@pytest.fixture
async def config_client(config_app):
    async with AsyncClient(
        transport=ASGITransport(app=config_app), base_url="http://test"
    ) as ac:
        yield ac


# =============================================================================
# 辅助函数
# =============================================================================


async def _seed_config(session_factory, key, value, group="general", is_sensitive=False):
    """向数据库插入一条配置。"""
    from backend.core.models import ConfigEntry

    async with session_factory() as session:
        entry = ConfigEntry(
            key=key,
            value=value,
            group=group,
            is_sensitive=is_sensitive,
        )
        session.add(entry)
        await session.commit()
    return entry


# =============================================================================
# 配置项管理
# =============================================================================


class TestConfigManagement:
    """测试配置管理 CRUD 操作。"""

    async def test_create_config(self, config_client, in_memory_db):
        response = await config_client.post(
            "/api/admin/config",
            json={
                "key": "test_key",
                "value": "test_value",
                "group": "general",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert data["data"]["key"] == "test_key"
        assert data["data"]["value"] == "test_value"

    async def test_create_config_duplicate(self, config_client, in_memory_db):
        """重复创建同一配置项应返回错误。"""
        await config_client.post(
            "/api/admin/config",
            json={"key": "dup_key", "value": "first"},
        )
        response = await config_client.post(
            "/api/admin/config",
            json={"key": "dup_key", "value": "second"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "error"
        assert "已存在" in data["message"]

    async def test_list_configs(self, config_client, in_memory_db):
        await _seed_config(in_memory_db["session_factory"], "key1", "val1")
        await _seed_config(in_memory_db["session_factory"], "key2", "val2")
        response = await config_client.get("/api/admin/config")
        data = response.json()
        assert data["code"] == "ok"
        assert len(data["data"]) == 2

    async def test_list_configs_by_group(self, config_client, in_memory_db):
        await _seed_config(
            in_memory_db["session_factory"], "k1", "v1", group="group_a"
        )
        await _seed_config(
            in_memory_db["session_factory"], "k2", "v2", group="group_b"
        )
        response = await config_client.get("/api/admin/config?group=group_a")
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["key"] == "k1"

    async def test_get_config(self, config_client, in_memory_db):
        await _seed_config(in_memory_db["session_factory"], "my_key", "my_value")
        response = await config_client.get("/api/admin/config/my_key")
        data = response.json()
        assert data["code"] == "ok"
        assert data["data"]["value"] == "my_value"

    async def test_get_config_not_found(self, config_client):
        response = await config_client.get("/api/admin/config/nonexistent")
        data = response.json()
        assert data["code"] == "error"
        assert "不存在" in data["message"]

    async def test_update_config(self, config_client, in_memory_db):
        await _seed_config(in_memory_db["session_factory"], "updatable", "old_value")
        response = await config_client.put(
            "/api/admin/config/updatable",
            json={"value": "new_value"},
        )
        data = response.json()
        assert data["code"] == "ok"
        assert data["message"] == "更新成功"

        # 验证数据库已更新
        from backend.core.models import ConfigEntry
        from sqlalchemy import select

        async with in_memory_db["session_factory"]() as session:
            result = await session.execute(
                select(ConfigEntry).where(ConfigEntry.key == "updatable")
            )
            entry = result.scalar_one()
            assert entry.value == "new_value"

    async def test_update_config_not_found(self, config_client):
        response = await config_client.put(
            "/api/admin/config/nonexistent",
            json={"value": "new_value"},
        )
        data = response.json()
        assert data["code"] == "error"
        assert "不存在" in data["message"]

    async def test_delete_config(self, config_client, in_memory_db):
        await _seed_config(in_memory_db["session_factory"], "deletable", "to_delete")
        response = await config_client.delete("/api/admin/config/deletable")
        data = response.json()
        assert data["code"] == "ok"

        # 验证已删除
        from backend.core.models import ConfigEntry
        from sqlalchemy import select

        async with in_memory_db["session_factory"]() as session:
            result = await session.execute(
                select(ConfigEntry).where(ConfigEntry.key == "deletable")
            )
            assert result.scalar_one_or_none() is None

    async def test_delete_config_not_found(self, config_client):
        response = await config_client.delete("/api/admin/config/nonexistent")
        data = response.json()
        assert data["code"] == "error"
        assert "不存在" in data["message"]

    async def test_list_groups(self, config_client, in_memory_db):
        await _seed_config(
            in_memory_db["session_factory"], "k1", "v1", group="alpha"
        )
        await _seed_config(
            in_memory_db["session_factory"], "k2", "v2", group="beta"
        )
        response = await config_client.get("/api/admin/config/groups")
        data = response.json()
        assert "alpha" in data["data"]
        assert "beta" in data["data"]


# =============================================================================
# 敏感字段掩码
# =============================================================================


class TestSensitiveFieldMasking:
    """测试敏感字段的掩码行为。"""

    async def test_list_masks_sensitive_values(self, config_client, in_memory_db):
        """list 接口应对敏感字段值掩码为 '***'。"""
        await _seed_config(
            in_memory_db["session_factory"],
            "secret_key",
            "real_secret_value",
            is_sensitive=True,
        )
        await _seed_config(
            in_memory_db["session_factory"],
            "normal_key",
            "normal_value",
            is_sensitive=False,
        )
        response = await config_client.get("/api/admin/config")
        data = response.json()
        items = {item["key"]: item["value"] for item in data["data"]}
        assert items["secret_key"] == "***"
        assert items["normal_key"] == "normal_value"

    async def test_get_shows_real_value(self, config_client, in_memory_db):
        """get 接口应返回敏感字段的真实值。"""
        await _seed_config(
            in_memory_db["session_factory"],
            "secret_key",
            "real_secret_value",
            is_sensitive=True,
        )
        response = await config_client.get("/api/admin/config/secret_key")
        data = response.json()
        assert data["data"]["value"] == "real_secret_value"


# =============================================================================
# 缓存失效
# =============================================================================


class TestCacheInvalidation:
    """测试配置更新/删除时的缓存失效。"""

    async def test_update_invalidates_cache(self, config_client, in_memory_db, fake_container):
        """更新配置后应调用 invalidate_cache。"""
        await _seed_config(in_memory_db["session_factory"], "cached_key", "old")

        # 替换 config 为可追踪的 mock
        mock_config = MagicMock()
        config_with_db = MagicMock()
        config_with_db._session_factory = in_memory_db["session_factory"]
        config_with_db.invalidate_cache = MagicMock()
        fake_container.get = lambda name: (
            config_with_db if name == "config" else MagicMock()
        )

        response = await config_client.put(
            "/api/admin/config/cached_key",
            json={"value": "new"},
        )
        assert response.status_code == 200
        config_with_db.invalidate_cache.assert_called_once_with("cached_key")

    async def test_delete_invalidates_cache(self, config_client, in_memory_db, fake_container):
        """删除配置后应调用 invalidate_cache。"""
        await _seed_config(in_memory_db["session_factory"], "del_key", "val")

        config_with_db = MagicMock()
        config_with_db._session_factory = in_memory_db["session_factory"]
        config_with_db.invalidate_cache = MagicMock()
        fake_container.get = lambda name: (
            config_with_db if name == "config" else MagicMock()
        )

        response = await config_client.delete("/api/admin/config/del_key")
        assert response.status_code == 200
        config_with_db.invalidate_cache.assert_called_once_with("del_key")

    async def test_reload_config_invalidates_all_cache(self, config_client, fake_container):
        """reload 接口应清除所有缓存。"""
        config_with_db = MagicMock()
        config_with_db.invalidate_cache = MagicMock()
        fake_container.get = lambda name: (
            config_with_db if name == "config" else MagicMock()
        )

        response = await config_client.post("/api/admin/config/reload")
        assert response.status_code == 200
        config_with_db.invalidate_cache.assert_called_once_with()


# =============================================================================
# DB 未就绪降级
# =============================================================================


class TestDbUnavailable:
    """测试数据库未就绪时的降级行为。"""

    async def test_list_configs_db_not_ready(self, config_client, fake_container):
        config_no_db = MagicMock()
        config_no_db._session_factory = None
        fake_container.get = lambda name: (
            config_no_db if name == "config" else MagicMock()
        )
        response = await config_client.get("/api/admin/config")
        data = response.json()
        assert data["code"] == "error"
        assert "数据库未就绪" in data["message"]

    async def test_get_config_db_not_ready(self, config_client, fake_container):
        config_no_db = MagicMock()
        config_no_db._session_factory = None
        fake_container.get = lambda name: (
            config_no_db if name == "config" else MagicMock()
        )
        response = await config_client.get("/api/admin/config/some_key")
        data = response.json()
        assert data["code"] == "error"
        assert "数据库未就绪" in data["message"]

    async def test_create_config_db_not_ready(self, config_client, fake_container):
        config_no_db = MagicMock()
        config_no_db._session_factory = None
        fake_container.get = lambda name: (
            config_no_db if name == "config" else MagicMock()
        )
        response = await config_client.post(
            "/api/admin/config",
            json={"key": "test", "value": "val"},
        )
        data = response.json()
        assert data["code"] == "error"
        assert "数据库未就绪" in data["message"]

    async def test_update_config_db_not_ready(self, config_client, fake_container):
        config_no_db = MagicMock()
        config_no_db._session_factory = None
        fake_container.get = lambda name: (
            config_no_db if name == "config" else MagicMock()
        )
        response = await config_client.put(
            "/api/admin/config/some_key",
            json={"value": "new"},
        )
        data = response.json()
        assert data["code"] == "error"
        assert "数据库未就绪" in data["message"]

    async def test_delete_config_db_not_ready(self, config_client, fake_container):
        config_no_db = MagicMock()
        config_no_db._session_factory = None
        fake_container.get = lambda name: (
            config_no_db if name == "config" else MagicMock()
        )
        response = await config_client.delete("/api/admin/config/some_key")
        data = response.json()
        assert data["code"] == "error"
        assert "数据库未就绪" in data["message"]