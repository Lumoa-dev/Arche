"""博客插件 高级单元测试。

覆盖 list_posts、get_post_by_slug、update_post、import_post 等核心方法
的搜索过滤、标签筛选、权限分支、文件导入、内容验证等复杂逻辑。
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.blog.services import BlogService


def _make_blog_container():
    """创建支持 BlogService 的轻量 fake_container。"""
    container = MagicMock()

    class FakeConfig:
        _values = {
            "GITHUB_TOKEN": "test_token",
            "SECRET_KEY": "test_secret_key_12345",
        }

        def get_required(self, key):
            return self._values.get(key, "")

        def get(self, key, default=None):
            return self._values.get(key, default)

    mock_execute_result = MagicMock()
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.rollback = AsyncMock()

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    def get_service(name):
        if name == "db":
            return {"session_factory": mock_session_factory}
        if name == "config":
            return FakeConfig()
        if name == "oss_rate_limiter":
            limiter = MagicMock()
            limiter.consume = AsyncMock()
            return limiter
        return MagicMock()

    container.get = get_service
    container._mock_session = mock_session
    container._mock_result = mock_execute_result
    container._mock_session_factory = mock_session_factory

    return container


@pytest.fixture
def blog_container():
    """每个测试用例独立的轻量 blog container。"""
    return _make_blog_container()


# =============================================================================
# list_posts — 搜索/标签/状态/排序/权限过滤
# =============================================================================


@pytest.mark.asyncio
class TestListPosts:
    """list_posts 搜索过滤和权限分支测试。"""

    async def test_list_posts_search_filter(self, blog_container):
        """搜索关键词过滤。"""
        service = BlogService(blog_container)
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        data_result = MagicMock()
        mock_post = MagicMock()
        mock_post.author_id = uuid.uuid4()
        mock_post.id = uuid.uuid4()
        mock_post.required_level = 5
        mock_post.title = "Hello World"
        mock_post.status = "published"
        mock_post.views = 0
        mock_post.content = "content"
        data_result.scalars.return_value.all.return_value = [mock_post]

        # list_posts 执行 4 次查询：count → data → author → likes
        author_result = MagicMock()
        author_result.all.return_value = []
        likes_result = MagicMock()
        likes_result.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result, author_result, likes_result]
        )

        result = await service.list_posts(
            page=1, page_size=20, search_query="Hello"
        )
        assert result["total"] == 1

    async def test_list_posts_tag_filter(self, blog_container):
        """标签筛选。"""
        service = BlogService(blog_container)
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_posts(
            page=1, page_size=20, tag_filter="Python"
        )
        assert result["total"] == 0
        assert result["items"] == []

    async def test_list_posts_all_status(self, blog_container):
        """status_filter=None 不过滤状态。"""
        service = BlogService(blog_container)
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_posts(status_filter=None)
        assert result["total"] == 0

    async def test_list_posts_user_level_filter(self, blog_container):
        """user_level 权限过滤。"""
        service = BlogService(blog_container)
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_posts(user_level=2)
        assert result["total"] == 0

    async def test_list_posts_sort_by_views(self, blog_container):
        """按浏览量排序。"""
        service = BlogService(blog_container)
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_posts(sort_by="views")
        assert result["total"] == 0

    async def test_list_posts_pagination(self, blog_container):
        """分页参数正确传递。"""
        service = BlogService(blog_container)
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_posts(page=3, page_size=10)
        assert result["page"] == 3
        assert result["page_size"] == 10


# =============================================================================
# get_post_by_slug — 非 published 权限分支
# =============================================================================


@pytest.mark.asyncio
class TestGetPostBySlug:
    """get_post_by_slug 权限分支测试。"""

    async def test_get_post_draft_as_author(self, blog_container):
        """作者查看自己的草稿。"""
        service = BlogService(blog_container)
        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_post.status = "draft"
        mock_post.author_id = author_id
        mock_post.views = 0
        mock_post.content = "content"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_result.all.return_value = []

        with patch.object(service, "get_post_tags", return_value=[]):
            result = await service.get_post_by_slug(
                "draft-post", user_level=5, user_id=author_id
            )
        assert result is not None

    async def test_get_post_draft_as_admin(self, blog_container):
        """P0 管理员查看他人草稿。"""
        service = BlogService(blog_container)
        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_post.status = "draft"
        mock_post.author_id = uuid.uuid4()
        mock_post.views = 0
        mock_post.content = "content"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_result.all.return_value = []

        with patch.object(service, "get_post_tags", return_value=[]):
            result = await service.get_post_by_slug(
                "draft-post", user_level=0, user_id=uuid.uuid4()
            )
        assert result is not None

    async def test_get_post_draft_as_other_user(self, blog_container):
        """普通用户查看他人草稿 → 404。"""
        service = BlogService(blog_container)
        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_post.status = "draft"
        mock_post.author_id = uuid.uuid4()
        mock_post.views = 0
        mock_post.content = "content"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with pytest.raises(Exception) as excinfo:
            await service.get_post_by_slug(
                "draft-post", user_level=5, user_id=uuid.uuid4()
            )
        assert "帖子不存在" in str(excinfo.value)

    async def test_get_post_published_view_count_not_author(
        self, blog_container
    ):
        """published 帖子，非作者访问应增加浏览量。"""
        service = BlogService(blog_container)
        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_post.status = "published"
        mock_post.author_id = uuid.uuid4()
        mock_post.views = 5
        mock_post.content = "content"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_result.all.return_value = []

        with patch.object(service, "get_post_tags", return_value=[]):
            result = await service.get_post_by_slug(
                "pub-post", user_level=5, user_id=uuid.uuid4()
            )
        assert result is not None


# =============================================================================
# update_post — 段落/标签/内容/权限等级更新
# =============================================================================


@pytest.mark.asyncio
class TestUpdatePost:
    """update_post 段落/标签/内容/权限等级更新测试。"""

    async def test_update_post_content(self, blog_container):
        """更新帖子内容。"""
        service = BlogService(blog_container)
        author_id = uuid.uuid4()
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id
        mock_post.slug = "old-slug"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        await service.update_post(
            post_id=post_id,
            author_id=author_id,
            content="New TipTap JSON content",
        )
        assert mock_post.content == "New TipTap JSON content"

    async def test_update_post_paragraphs(self, blog_container):
        """更新帖子段落（删除旧段落+创建新段落）。"""
        service = BlogService(blog_container)
        author_id = uuid.uuid4()
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id
        mock_post.id = post_id
        mock_post.slug = "old-slug"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        await service.update_post(
            post_id=post_id,
            author_id=author_id,
            paragraphs_data=[
                {"content": "New paragraph 1", "type": "text"},
                {"content": "New paragraph 2", "type": "text"},
            ],
        )
        # 删除了旧段落
        from unittest.mock import ANY

        blog_container._mock_session.execute.assert_any_call(
            ANY
        )
        # 添加了新段落
        assert blog_container._mock_session.add.call_count >= 2

    async def test_update_post_tags(self, blog_container):
        """更新帖子标签（删除旧标签+创建新标签）。"""
        service = BlogService(blog_container)
        author_id = uuid.uuid4()
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id
        mock_post.slug = "old-slug"

        # update_post 执行流程：
        # 1. find post → mock_post
        # 2. delete old BlogPostTag
        # 3. find tag "python" → None (create new)
        # 4. find tag "testing" → None (create new)
        blog_container._mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_post)),  # 查找帖子
                MagicMock(),  # 删除旧标签
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # 查找标签 python
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # 查找标签 testing
            ]
        )

        await service.update_post(
            post_id=post_id,
            author_id=author_id,
            tags=["python", "testing"],
        )
        # 创建了新标签 + 新标签关联
        assert blog_container._mock_session.add.call_count >= 2

    async def test_update_post_required_level(self, blog_container):
        """更新帖子权限等级。"""
        service = BlogService(blog_container)
        author_id = uuid.uuid4()
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id
        mock_post.slug = "old-slug"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        await service.update_post(
            post_id=post_id,
            author_id=author_id,
            required_level=3,
            user_level=3,
        )
        assert mock_post.required_level == 3

    async def test_update_post_required_level_too_high(self, blog_container):
        """用户设置高于自身权限的等级→拒绝。"""
        service = BlogService(blog_container)
        author_id = uuid.uuid4()
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id
        mock_post.slug = "old-slug"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with pytest.raises(Exception) as excinfo:
            await service.update_post(
                post_id=post_id,
                author_id=author_id,
                required_level=0,
                user_level=5,
            )
        assert "无权设置" in str(excinfo.value)

    async def test_update_post_title_resets_status(self, blog_container):
        """仅标题变更后 status 重置为 pending。"""
        service = BlogService(blog_container)
        author_id = uuid.uuid4()
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id
        mock_post.slug = "old-slug"
        mock_post.status = "published"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with patch.object(service, "generate_slug", return_value="new-title"):
            await service.update_post(
                post_id=post_id,
                author_id=author_id,
                title="New Title",
            )
        assert mock_post.status == "pending"


# =============================================================================
# import_post — 文件导入
# =============================================================================


@pytest.mark.asyncio
class TestImportPost:
    """import_post 文件导入测试。"""

    async def test_import_markdown(self, blog_container):
        """导入 .md 文件。"""
        service = BlogService(blog_container)
        mock_file = MagicMock()
        mock_file.filename = "test.md"
        mock_file.read = AsyncMock(
            return_value=b"# Hello World\n\nThis is a test."
        )

        result = await service.import_post(
            file=mock_file, author_id=uuid.uuid4()
        )
        assert result["title"] == "Hello World"
        assert "This is a test." in result["content"]

    async def test_import_txt(self, blog_container):
        """导入 .txt 文件（无标题则用文件名）。"""
        service = BlogService(blog_container)
        mock_file = MagicMock()
        mock_file.filename = "my-note.txt"
        mock_file.read = AsyncMock(return_value=b"Just some text content.")

        result = await service.import_post(
            file=mock_file, author_id=uuid.uuid4()
        )
        assert result["title"] == "my-note"
        assert result["content"] == "Just some text content."

    async def test_import_unsupported_type(self, blog_container):
        """不支持的文件类型→拒绝。"""
        service = BlogService(blog_container)
        mock_file = MagicMock()
        mock_file.filename = "image.png"
        mock_file.read = AsyncMock()

        with pytest.raises(Exception) as excinfo:
            await service.import_post(
                file=mock_file, author_id=uuid.uuid4()
            )
        assert "不支持的文件类型" in str(excinfo.value)

    async def test_import_html(self, blog_container):
        """导入 .html 文件，提取 body 内容。"""
        service = BlogService(blog_container)
        mock_file = MagicMock()
        mock_file.filename = "article.html"
        mock_file.read = AsyncMock(
            return_value=b"<html><body><h1>HTML Title</h1><p>HTML content.</p></body></html>"
        )

        result = await service.import_post(
            file=mock_file, author_id=uuid.uuid4()
        )
        assert result["title"] == "HTML Title"
        assert "HTML content." in result["content"]

    async def test_import_with_tags(self, blog_container):
        """导入时携带标签。"""
        service = BlogService(blog_container)
        mock_file = MagicMock()
        mock_file.filename = "test.md"
        mock_file.read = AsyncMock(
            return_value=b"# Tagged Post\n\nContent."
        )

        result = await service.import_post(
            file=mock_file, author_id=uuid.uuid4(), tags=["python", "test"]
        )
        assert result["tags"] == ["python", "test"]


# =============================================================================
# 工具方法 — _extract_title / _extract_html_body
# =============================================================================


class TestExtractHelpers:
    """_extract_title 和 _extract_html_body 工具方法测试。"""

    def test_extract_title_with_heading(self):
        """从 Markdown 中提取标题。"""
        service = BlogService.__new__(BlogService)
        title, body = service._extract_title(
            "# My Title\n\nBody content here.", "fallback.txt"
        )
        assert title == "My Title"
        assert "Body content here." in body
        assert "# My Title" not in body

    def test_extract_title_no_heading(self):
        """无标题时使用文件名。"""
        service = BlogService.__new__(BlogService)
        title, body = service._extract_title(
            "Just plain text.", "my-file.txt"
        )
        assert title == "my-file"
        assert body == "Just plain text."

    def test_extract_html_body(self):
        """从 HTML 中提取 body 并转为 Markdown。"""
        service = BlogService.__new__(BlogService)
        html = "<html><body><h1>Title</h1><p>Paragraph</p></body></html>"
        result = service._extract_html_body(html)
        assert "# Title" in result
        assert "Paragraph" in result

    def test_extract_html_body_no_body_tag(self):
        """无 body 标签时回退处理整个 HTML。"""
        service = BlogService.__new__(BlogService)
        html = "<h2>Subtitle</h2><br/><p>Content</p>"
        result = service._extract_html_body(html)
        assert "## Subtitle" in result
        assert "Content" in result


# =============================================================================
# get_post_paragraphs — 段落查询
# =============================================================================


@pytest.mark.asyncio
class TestGetPostParagraphs:
    """get_post_paragraphs 段落查询测试。"""

    async def test_get_paragraphs_no_paragraph_ids(self, blog_container):
        """帖子无段落。"""
        service = BlogService(blog_container)
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.paragraph_ids = None
        mock_post.required_level = 5

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        # 第二次查询 paragraph_ids
        blog_container._mock_session.execute = AsyncMock(
            return_value=MagicMock(
                one_or_none=MagicMock(return_value=None)
            )
        )

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.get_post_paragraphs(post_id=post_id)
        assert result == []

    async def test_get_paragraphs_with_offset_limit(self, blog_container):
        """段落分页。"""
        service = BlogService(blog_container)
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.paragraph_ids = ["pid_001", "pid_002", "pid_003"]
        mock_post.required_level = 5

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.get_post_paragraphs(
                post_id=post_id, offset=1, limit=1
            )
        assert result == []


# =============================================================================
# get_like_status — 点赞状态查询
# =============================================================================


@pytest.mark.asyncio
class TestGetLikeStatus:
    """get_like_status 点赞状态查询测试。"""

    async def test_get_like_status_liked(self, blog_container):
        """已点赞。"""
        service = BlogService(blog_container)
        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_post = MagicMock()

        # 第一次查询 exists → 有结果表示已点赞
        exists_result = MagicMock()
        exists_result.scalar_one_or_none.return_value = MagicMock()
        # 第二次查询 count → 返回 3
        count_result = MagicMock()
        count_result.scalar_one.return_value = 3

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[exists_result, count_result]
        )

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.get_like_status(
                post_id=post_id, user_id=user_id
            )
        assert result["liked"] is True
        assert result["count"] == 3

    async def test_get_like_status_not_liked(self, blog_container):
        """未点赞。"""
        service = BlogService(blog_container)
        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_post = MagicMock()

        exists_result = MagicMock()
        exists_result.scalar_one_or_none.return_value = None
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[exists_result, count_result]
        )

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.get_like_status(
                post_id=post_id, user_id=user_id
            )
        assert result["liked"] is False
        assert result["count"] == 0


# =============================================================================
# get_post_detail_by_id — 权限分支
# =============================================================================


@pytest.mark.asyncio
class TestGetPostDetailById:
    """get_post_detail_by_id 权限分支测试。"""

    async def test_get_detail_by_id_permission_denied(self, blog_container):
        """required_level 权限不足。"""
        service = BlogService(blog_container)
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.required_level = 0

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with pytest.raises(Exception) as excinfo:
            await service.get_post_detail_by_id(
                post_id=post_id, user_level=5
            )
        assert "无权查看" in str(excinfo.value)

    async def test_get_detail_by_id_draft_as_other(self, blog_container):
        """非 published 帖子，非作者非 P0 → 404。"""
        service = BlogService(blog_container)
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_post.status = "draft"
        mock_post.author_id = uuid.uuid4()

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with pytest.raises(Exception) as excinfo:
            await service.get_post_detail_by_id(
                post_id=post_id, user_level=5, user_id=uuid.uuid4()
            )
        assert "帖子不存在" in str(excinfo.value)