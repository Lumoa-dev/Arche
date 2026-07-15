"""配置管理路由 单元测试。

测试 CRUD 操作的路由逻辑，覆盖：
- 列表查询（含分组过滤、敏感字段掩码）
- 单条查询（404 边界）
- 创建（重复键检测、输入验证）
- 更新（缓存失效）
- 删除（404 边界、缓存失效）
- 分组列表
- 缓存重载
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request

from backend.plugins.config_mgmt import routes


def _make_async_session_mock(scalar_all_return=None, scalar_one_or_none_return=None, all_return=None):
    """创建可被 ``async with`` 使用的 mock 数据库会话。

    生成 session 可以：
    - ``await session.execute(query)`` → 返回 mock_result
    - ``result.scalars().all()`` → 返回 scalar_all_return
    - ``result.scalar_one_or_none()`` → 返回 scalar_one_or_none_return
    - ``result.all()`` → 返回 all_return
    """
    mock_result = MagicMock()
    if scalar_all_return is not None:
        mock_result.scalars.return_value.all.return_value = scalar_all_return
    # 始终设置 scalar_one_or_none 的返回值，包括 None
    mock_result.scalar_one_or_none.return_value = scalar_one_or_none_return
    if all_return is not None:
        mock_result.all.return_value = all_return

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()
    # async with 支持
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session


def _make_mock_request(session_mock=None) -> Request:
    """创建带有认证用户状态和 mock 容器的 Request。"""
    if session_mock is None:
        session_mock = _make_async_session_mock(scalar_all_return=[])

    mock_config = MagicMock()
    # session_factory 是一个可调用对象，返回 mock session
    mock_config._session_factory = MagicMock(return_value=session_mock)
    mock_config.invalidate_cache = MagicMock()

    mock_container = MagicMock()
    mock_container.get.return_value = mock_config

    mock_app = type(
        "MockApp",
        (),
        {"state": type("MockState", (), {"container": mock_container})()},
    )()
    scope = {"type": "http", "app": mock_app, "headers": []}
    request = Request(scope)
    request.state.user = {
        "id": "admin",
        "username": "admin",
        "level": 0,
        "email": "admin@test.com",
        "blog_quality_level": 0,
    }
    return request


@pytest.mark.asyncio
class TestListConfigs:
    """配置列表查询测试。"""

    async def test_list_all_configs(self):
        """列出所有配置，应返回完整列表。"""
        entries = [
            MagicMock(
                key="PUBLIC_NAME",
                value="Arche",
                group="app",
                description="public",
                is_sensitive=False,
            ),
            MagicMock(
                key="SECRET",
                value="top-secret",
                group="secrets",
                description="secret",
                is_sensitive=True,
            ),
        ]
        session = _make_async_session_mock(scalar_all_return=entries)
        request = _make_mock_request(session)

        result = await routes.list_configs(request=request)
        assert result["code"] == "ok"
        assert len(result["data"]) == 2

    async def test_filter_by_group(self):
        """按分组过滤应只返回该组配置。"""
        entry = MagicMock(
            key="PUBLIC_NAME",
            value="Arche",
            group="app",
            description="public",
            is_sensitive=False,
        )
        session = _make_async_session_mock(scalar_all_return=[entry])
        request = _make_mock_request(session)

        result = await routes.list_configs(request=request, group="app")
        assert result["code"] == "ok"
        assert len(result["data"]) == 1
        assert result["data"][0]["key"] == "PUBLIC_NAME"

    async def test_empty_configs(self):
        """无配置时返回空列表。"""
        session = _make_async_session_mock(scalar_all_return=[])
        request = _make_mock_request(session)

        result = await routes.list_configs(request=request)
        assert result["code"] == "ok"
        assert result["data"] == []

    async def test_sensitive_value_masked(self):
        """敏感配置值应被掩码为 ***。"""
        entry = MagicMock(
            key="SECRET_KEY",
            value="real-secret",
            group="security",
            description="secret key",
            is_sensitive=True,
        )
        session = _make_async_session_mock(scalar_all_return=[entry])
        request = _make_mock_request(session)

        result = await routes.list_configs(request=request)
        assert result["data"][0]["value"] == "***"
        assert result["data"][0]["is_sensitive"] is True


@pytest.mark.asyncio
class TestGetConfig:
    """单条配置查询测试。"""

    async def test_get_existing_config(self):
        """存在的配置应返回真实值。"""
        entry = MagicMock(
            key="PUBLIC_NAME",
            value="Arche",
            group="app",
            description="public",
            is_sensitive=False,
        )
        session = _make_async_session_mock(scalar_one_or_none_return=entry)
        request = _make_mock_request(session)

        result = await routes.get_config("PUBLIC_NAME", request=request)
        assert result["code"] == "ok"
        assert result["data"]["value"] == "Arche"

    async def test_get_non_existent_config(self):
        """不存在的配置应返回 error。"""
        session = _make_async_session_mock(scalar_one_or_none_return=None)
        request = _make_mock_request(session)

        result = await routes.get_config("UNKNOWN", request=request)
        assert result["code"] == "error"
        assert "不存在" in result["message"]


@pytest.mark.asyncio
class TestUpdateConfig:
    """配置更新测试。"""

    async def test_update_existing_config(self):
        """更新已有配置应成功并清除缓存。"""
        entry = MagicMock(
            key="PUBLIC_NAME",
            value="Arche",
            group="app",
            description="public",
            is_sensitive=False,
        )
        session = _make_async_session_mock(scalar_one_or_none_return=entry)
        request = _make_mock_request(session)

        result = await routes.update_config(
            "PUBLIC_NAME",
            routes.UpdateConfigRequest(value="New Value"),
            request=request,
        )
        assert result["code"] == "ok"
        request.app.state.container.get().invalidate_cache.assert_called_once_with(
            "PUBLIC_NAME"
        )

    async def test_update_non_existent_config(self):
        """更新不存在的配置应返回 error。"""
        session = _make_async_session_mock(scalar_one_or_none_return=None)
        request = _make_mock_request(session)

        result = await routes.update_config(
            "UNKNOWN",
            routes.UpdateConfigRequest(value="value"),
            request=request,
        )
        assert result["code"] == "error"
        assert "不存在" in result["message"]


@pytest.mark.asyncio
class TestCreateConfig:
    """配置创建测试。"""

    async def test_create_new_config(self):
        """创建新配置应成功。"""
        # 第一次查询检查是否存在 → 返回 None (不存在)
        session = _make_async_session_mock(scalar_one_or_none_return=None)
        request = _make_mock_request(session)

        result = await routes.create_config(
            routes.CreateConfigRequest(
                key="NEW_KEY",
                value="new-value",
                group="custom",
                description="new config",
                is_sensitive=False,
            ),
            request=request,
        )
        assert result["code"] == "ok"
        assert result["data"]["key"] == "NEW_KEY"

    async def test_create_duplicate_config(self):
        """创建已存在的配置应返回错误。"""
        existing = MagicMock(key="EXISTING")
        session = _make_async_session_mock(scalar_one_or_none_return=existing)
        request = _make_mock_request(session)

        result = await routes.create_config(
            routes.CreateConfigRequest(
                key="EXISTING",
                value="value",
            ),
            request=request,
        )
        assert result["code"] == "error"
        assert "已存在" in result["message"]


@pytest.mark.asyncio
class TestDeleteConfig:
    """配置删除测试。"""

    async def test_delete_existing_config(self):
        """删除已有配置应成功并清除缓存。"""
        entry = MagicMock(key="TO_DELETE")
        session = _make_async_session_mock(scalar_one_or_none_return=entry)
        request = _make_mock_request(session)

        result = await routes.delete_config("TO_DELETE", request=request)
        assert result["code"] == "ok"
        request.app.state.container.get().invalidate_cache.assert_called_once_with(
            "TO_DELETE"
        )

    async def test_delete_non_existent_config(self):
        """删除不存在的配置应返回 error。"""
        session = _make_async_session_mock(scalar_one_or_none_return=None)
        request = _make_mock_request(session)

        result = await routes.delete_config("UNKNOWN", request=request)
        assert result["code"] == "error"
        assert "不存在" in result["message"]


@pytest.mark.asyncio
class TestListGroups:
    """配置分组列表测试。"""

    async def test_list_groups(self):
        """应返回去重后的分组列表。"""
        session = _make_async_session_mock(all_return=[("app",), ("secrets",)])
        request = _make_mock_request(session)

        result = await routes.list_groups(request=request)
        assert result["code"] == "ok"
        assert "app" in result["data"]
        assert "secrets" in result["data"]


@pytest.mark.asyncio
class TestReloadConfig:
    """配置缓存重载测试。"""

    async def test_reload_clears_cache(self):
        """重载应清除所有缓存。"""
        request = _make_mock_request()

        result = await routes.reload_config(request=request)
        assert result["code"] == "ok"
        request.app.state.container.get().invalidate_cache.assert_called_once_with()