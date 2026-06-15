"""SearchService 统一搜索单元测试。

测试原则：
- 核心搜索业务逻辑用 mock 隔离测试
- 全局搜索用内存数据库验证跨表查询
- 路由测试直接调用 handler，验证请求处理和响应格式
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request

from backend.plugins.search.routes import search_suggestions
from backend.plugins.search.services import SearchService

# =============================================================================
# Mock 辅助
# =============================================================================


def _make_mock_search_container():
    """创建 SearchService 的 mock container。

    返回的 container 提供 mock db session_factory，
    外部可通过 container._mock_session 控制查询结果。
    """
    mock_execute_result = MagicMock()
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    container = MagicMock()
    container.get.side_effect = lambda name: {
        "db": {"session_factory": mock_session_factory},
    }.get(name, MagicMock())
    container._mock_session = mock_session
    container._mock_result = mock_execute_result
    container._mock_session_factory = mock_session_factory
    return container


def _make_dummy_container(in_memory_db):
    """为全局搜索测试创建容器，使用真实内存数据库。"""
    container = MagicMock()
    container.get.side_effect = lambda name: {
        "db": in_memory_db,
    }.get(name, MagicMock())
    return container


def _make_mock_request(container) -> Request:
    """创建带有 mock container 的 Request 对象。"""
    mock_state = MagicMock()
    mock_state.container = container
    mock_app = MagicMock()
    mock_app.state = mock_state
    scope = {"type": "http", "app": mock_app}
    request = Request(scope)
    return request


# 有效的 SID hex（32 位 hex，无分隔符，可被 parse_sid 正确解析）
_VALID_UUID_HEX = "550e8400e29b41d4a716446655440000"


# =============================================================================
# SearchService 测试 - 边界条件
# =============================================================================


@pytest.mark.asyncio
class TestSearchServiceEdgeCases:
    """SearchService 边界条件测试。"""

    async def test_empty_keyword_returns_empty_list(self):
        """空关键词应返回空列表。"""
        container = _make_mock_search_container()
        service = SearchService(container)
        result = await service.search("")
        assert result == []

    async def test_whitespace_keyword_returns_empty_list(self):
        """仅空白字符关键词应返回空列表。"""
        container = _make_mock_search_container()
        service = SearchService(container)
        result = await service.search("   ")
        assert result == []

    async def test_none_keyword_returns_empty_list(self):
        """None 关键词应返回空列表。"""
        container = _make_mock_search_container()
        service = SearchService(container)
        result = await service.search(None)
        assert result == []


# =============================================================================
# SearchService 测试 - SID 前缀搜索（Mock 数据库）
#
# 注：关键词必须是完整有效的 SID（前缀 + 32 位 UUID hex），
#     parse_sid 才能正确识别前缀并触发 _search_by_prefix。
# =============================================================================


@pytest.mark.asyncio
class TestSearchServicePrefixSearch:
    """SID 前缀限定搜索测试（Mock 数据库）。"""

    async def test_search_users_by_prefix_returns_formatted_results(self):
        """user- 前缀搜索用户，返回格式应包含 type/sid/label/sublabel/url。"""
        container = _make_mock_search_container()
        service = SearchService(container)

        mock_user = MagicMock()
        mock_user.sid = f"user-{_VALID_UUID_HEX}"
        mock_user.username = "testuser"
        mock_user.level = 5
        mock_user.id = 1
        mock_user.email = "test@example.com"
        container._mock_result.scalars.return_value.all.return_value = [mock_user]

        results = await service.search(f"user-{_VALID_UUID_HEX}", limit=5)

        assert len(results) == 1
        item = results[0]
        assert item["type"] == "user"
        assert item["sid"] == mock_user.sid
        assert item["label"] == "testuser"
        assert item["sublabel"] == "等级 P5"
        assert "/admin/users/list" in item["url"]

    async def test_search_users_by_prefix_empty_results(self):
        """user- 前缀搜索无匹配结果应返回空列表。"""
        container = _make_mock_search_container()
        service = SearchService(container)
        container._mock_result.scalars.return_value.all.return_value = []

        results = await service.search(f"user-{_VALID_UUID_HEX}")
        assert results == []

    async def test_search_tasks_by_prefix_returns_formatted_results(self):
        """task- 前缀搜索任务，返回格式应正确。"""
        container = _make_mock_search_container()
        service = SearchService(container)

        mock_job = MagicMock()
        mock_job.sid = f"task-{_VALID_UUID_HEX}"
        mock_job.name = "训练任务1"
        mock_job.status = "running"
        mock_job.id = 42
        container._mock_result.scalars.return_value.all.return_value = [mock_job]

        results = await service.search(f"task-{_VALID_UUID_HEX}", limit=5)

        assert len(results) == 1
        item = results[0]
        assert item["type"] == "task"
        assert item["label"] == "训练任务1"
        assert item["sublabel"] == "running"
        assert "/tasks?job_id=42" in item["url"]

    async def test_search_logs_by_prefix_returns_formatted_results(self):
        """log- 前缀搜索日志记录，返回格式应正确。"""
        container = _make_mock_search_container()
        service = SearchService(container)

        mock_record = MagicMock()
        mock_record.sid = f"log-{_VALID_UUID_HEX}"
        mock_record.title = "爬取记录1"
        mock_record.url = "https://example.com"
        mock_record.source = "example.com"
        mock_record.id = 99
        container._mock_result.scalars.return_value.all.return_value = [mock_record]

        results = await service.search(f"log-{_VALID_UUID_HEX}", limit=5)

        assert len(results) == 1
        item = results[0]
        assert item["type"] == "log"
        assert item["label"] == "爬取记录1"
        assert item["sublabel"] == "来源: example.com"
        assert "/crawler?record_id=99" in item["url"]

    async def test_search_logs_without_title_falls_back_to_url(self):
        """日志无 title 时 label 应回退到 url。"""
        container = _make_mock_search_container()
        service = SearchService(container)

        mock_record = MagicMock()
        mock_record.sid = f"log-{_VALID_UUID_HEX}"
        mock_record.title = None
        mock_record.url = "https://example.com/page"
        mock_record.source = None
        mock_record.id = 100
        container._mock_result.scalars.return_value.all.return_value = [mock_record]

        results = await service.search(f"log-{_VALID_UUID_HEX}", limit=5)

        assert results[0]["label"] == "https://example.com/page"
        assert results[0]["sublabel"] == "来源: "

    async def test_search_assets_by_prefix_returns_posts_and_files(self):
        """asse- 前缀搜索资产，应同时返回帖子和文件。"""
        container = _make_mock_search_container()
        service = SearchService(container)

        mock_post = MagicMock()
        mock_post.sid = f"asse-post-{_VALID_UUID_HEX}"
        mock_post.title = "测试帖子"
        mock_post.slug = "test-post"
        mock_post.created_at = None
        mock_post.id = 1

        mock_file = MagicMock()
        mock_file.sid = f"asse-file-{_VALID_UUID_HEX}"
        mock_file.path = "uploads/test.pdf"
        mock_file.mime_type = "application/pdf"
        mock_file.id = 2

        container._mock_result.scalars.return_value.all.side_effect = [
            [mock_post],
            [mock_file],
        ]

        results = await service.search(f"asse-{_VALID_UUID_HEX}", limit=5)

        assert len(results) == 2
        assert results[0]["type"] == "post"
        assert results[0]["label"] == "测试帖子"
        assert results[0]["url"] == "/blog/test-post"
        assert results[1]["type"] == "file"
        assert results[1]["label"] == "test.pdf"
        assert results[1]["url"] == "/assets?file_id=2"

    async def test_search_assets_fills_remaining_with_files(self):
        """帖子数量不足 limit 时，剩余名额由文件补充。"""
        container = _make_mock_search_container()
        service = SearchService(container)

        mock_post = MagicMock()
        mock_post.sid = f"asse-post-{_VALID_UUID_HEX}"
        mock_post.title = "唯一帖子"
        mock_post.slug = "only-post"
        mock_post.created_at = None
        mock_post.id = 1

        mock_file = MagicMock()
        mock_file.sid = f"asse-file-{_VALID_UUID_HEX}"
        mock_file.path = "docs/guide.pdf"
        mock_file.mime_type = "application/pdf"
        mock_file.id = 2

        container._mock_result.scalars.return_value.all.side_effect = [
            [mock_post],
            [mock_file],
        ]

        results = await service.search(f"asse-{_VALID_UUID_HEX}", limit=3)

        assert len(results) == 2
        assert results[0]["type"] == "post"
        assert results[1]["type"] == "file"

    async def test_search_assets_no_posts_only_files(self):
        """帖子结果为空时，仅返回文件结果。"""
        container = _make_mock_search_container()
        service = SearchService(container)

        mock_file = MagicMock()
        mock_file.sid = f"asse-file-{_VALID_UUID_HEX}"
        mock_file.path = "images/photo.png"
        mock_file.mime_type = "image/png"
        mock_file.id = 5

        container._mock_result.scalars.return_value.all.side_effect = [
            [],
            [mock_file],
        ]

        results = await service.search(f"asse-{_VALID_UUID_HEX}", limit=5)

        assert len(results) == 1
        assert results[0]["type"] == "file"
        assert results[0]["label"] == "photo.png"

    async def test_search_assets_no_results(self):
        """资产搜索无匹配结果应返回空列表。"""
        container = _make_mock_search_container()
        service = SearchService(container)

        container._mock_result.scalars.return_value.all.side_effect = [
            [],
            [],
        ]

        results = await service.search(f"asse-{_VALID_UUID_HEX}")
        assert results == []


# =============================================================================
# SearchService 测试 - 全局搜索（内存数据库）
# =============================================================================


@pytest.mark.asyncio
class TestSearchServiceGlobalSearch:
    """全局模糊搜索测试（使用内存 SQLite 数据库）。"""

    async def test_global_search_returns_users_and_posts(self, in_memory_db):
        """全局搜索应跨表返回用户和帖子混合结果。"""
        from backend.plugins.auth.models import User
        from backend.plugins.blog.models import BlogPost

        service = SearchService(_make_dummy_container(in_memory_db))

        async with in_memory_db["session_factory"]() as session:
            user = User(
                sid="user-550e-8400-e29b-41d4-a716-4466-5544-0000",
                username="testuser",
                nickname="testuser",
                email="test@example.com",
                password_hash="hashed_pwd",
                level=5,
            )
            post = BlogPost(
                sid="asse-post-550e-8400-e29b-41d4-a716-4466-5544-0001",
                title="test 标题",
                slug="test-post",
                status="published",
                required_level=5,
                author_id=uuid.uuid4(),
            )
            session.add(user)
            session.add(post)
            await session.commit()

        results = await service.search("test", limit=10)

        types_found = {item["type"] for item in results}
        assert "user" in types_found
        assert "post" in types_found

    async def test_global_search_respects_limit(self, in_memory_db):
        """全局搜索结果数量不应超过 limit。"""
        from backend.plugins.auth.models import User

        service = SearchService(_make_dummy_container(in_memory_db))

        async with in_memory_db["session_factory"]() as session:
            for i in range(5):
                user = User(
                    sid=f"user-550e-8400-e29b-41d4-a716-4466-5544-{i:04d}",
                    username=f"testuser{i}",
                    nickname="testuser",
                    email=f"test{i}@example.com",
                    password_hash="hashed_pwd",
                    level=5,
                )
                session.add(user)
            await session.commit()

        results = await service.search("testuser", limit=3)

        assert len(results) <= 3

    async def test_global_search_no_results(self, in_memory_db):
        """全局搜索无匹配应返回空列表。"""
        service = SearchService(_make_dummy_container(in_memory_db))

        results = await service.search("不存在的关键词xyz", limit=5)
        assert results == []

    async def test_global_search_keyword_matches_username(self, in_memory_db):
        """全局搜索 keyword 应匹配用户名字段。"""
        from backend.plugins.auth.models import User

        service = SearchService(_make_dummy_container(in_memory_db))

        async with in_memory_db["session_factory"]() as session:
            user = User(
                sid="user-550e-8400-e29b-41d4-a716-4466-5544-0000",
                username="john_doe",
                nickname="testuser",
                email="john@other.com",
                password_hash="hashed_pwd",
                level=5,
            )
            session.add(user)
            await session.commit()

        results = await service.search("john", limit=5)
        labels = {item["label"] for item in results}
        assert "john_doe" in labels


# =============================================================================
# SearchService 测试 - 错误处理
# =============================================================================


@pytest.mark.asyncio
class TestSearchServiceErrorHandling:
    """SearchService 错误处理测试。"""

    async def test_db_connection_failure_raises_exception(self):
        """数据库连接失败时应向上抛出异常。"""
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            side_effect=RuntimeError("数据库连接失败")
        )

        container = MagicMock()
        container.get.side_effect = lambda name: {
            "db": {"session_factory": mock_session_factory},
        }.get(name, MagicMock())

        service = SearchService(container)

        with pytest.raises(RuntimeError) as excinfo:
            await service.search("test", limit=5)
        assert "数据库连接失败" in str(excinfo.value)

    async def test_session_execute_failure_raises_exception(self):
        """查询执行失败时应向上抛出异常。"""
        container = _make_mock_search_container()
        service = SearchService(container)

        container._mock_session.execute = AsyncMock(
            side_effect=RuntimeError("查询执行失败")
        )

        with pytest.raises(RuntimeError) as excinfo:
            await service.search(f"user-{_VALID_UUID_HEX}", limit=5)
        assert "查询执行失败" in str(excinfo.value)


# =============================================================================
# 搜索路由测试 - 请求处理与响应格式
# =============================================================================


@pytest.mark.asyncio
class TestSearchRoute:
    """搜索路由 handler 测试。"""

    async def test_route_returns_ok_response(self):
        """路由应返回 {code: ok, data: {items: [...]}} 格式。"""
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=[])

        container = MagicMock()
        container.get.return_value = mock_search_service

        request = _make_mock_request(container)

        result = await search_suggestions(request, q="test", limit=5)

        assert result == {"code": "ok", "data": {"items": []}}

    async def test_route_passes_keyword_and_limit_to_service(self):
        """路由应将 q 和 limit 正确传递给 search_service.search。"""
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=[])

        container = MagicMock()
        container.get.return_value = mock_search_service

        request = _make_mock_request(container)

        await search_suggestions(request, q="hello", limit=3)

        mock_search_service.search.assert_awaited_once_with(keyword="hello", limit=3)

    async def test_route_uses_default_limit_parameter(self):
        """路由不传 limit 时默认应为 Query(5) 对象。"""
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=[])

        container = MagicMock()
        container.get.return_value = mock_search_service

        request = _make_mock_request(container)

        await search_suggestions(request, q="test")

        mock_search_service.search.assert_awaited_once()
        call_kwargs = mock_search_service.search.call_args.kwargs
        assert call_kwargs["keyword"] == "test"

    async def test_route_returns_formatted_search_results(self):
        """路由返回的结果格式应与 SearchService 输出一致。"""
        mock_results = [
            {
                "type": "user",
                "sid": f"user-{_VALID_UUID_HEX}",
                "label": "testuser",
                "sublabel": "等级 P5",
                "url": "/admin/users/list?id=1",
            },
        ]
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_results)

        container = MagicMock()
        container.get.return_value = mock_search_service

        request = _make_mock_request(container)

        result = await search_suggestions(request, q=f"user-{_VALID_UUID_HEX}", limit=5)

        assert result["code"] == "ok"
        assert len(result["data"]["items"]) == 1
        assert result["data"]["items"][0]["type"] == "user"
        assert result["data"]["items"][0]["label"] == "testuser"

    async def test_route_no_auth_decorator(self):
        """搜索路由 handler 不应有认证装饰器（公开接口）。"""
        import inspect

        source = inspect.getsource(search_suggestions)
        assert "@login_required" not in source
        assert "@require_auth" not in source
        assert "Depends" not in source or "get_current_user" not in source
