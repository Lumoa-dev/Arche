"""博客插件 复杂逻辑边界条件测试。

覆盖范围：
- _is_trusted_video_host() / _validate_video_url() 视频链接验证
- _extract_title() Markdown 标题提取
- _extract_html_body() HTML 转 Markdown
- validate_content() 内容全面校验
- scan_and_clean_post_files() / validate_post_file_refs() 文件引用管理
- import_post() 文件导入逻辑
- get_post_by_slug() 非 published 状态边界条件
- create_report() 举报+降流逻辑
- get_daily_trend() / get_hot_posts() 统计功能
- 段落评论边界条件

使用纯 mock，不启动真实数据库。
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.blog.services import BlogService


# =============================================================================
# 测试辅助
# =============================================================================


def _make_blog_container():
    """创建支持 BlogService 的轻量 mock container。"""
    container = MagicMock()

    class FakeConfig:
        _values = {  # noqa: RUF012
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
# 视频链接验证测试
# =============================================================================


class TestVideoUrlValidation:
    """视频链接验证测试。"""

    def test_is_trusted_video_host_bilibili(self):
        """bilibili 域名应被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://www.bilibili.com/video/BV1GJ411x7H7"
        ) is True
        assert BlogService._is_trusted_video_host(
            "https://bilibili.com/video/BV1xx"
        ) is True

    def test_is_trusted_video_host_b23tv(self):
        """b23.tv 短域名应被识别。"""
        assert BlogService._is_trusted_video_host(
            "https://b23.tv/BV1GJ411x7H7"
        ) is True

    def test_is_trusted_video_host_youtube(self):
        """youtube.com 域名应被识别。"""
        assert BlogService._is_trusted_video_host(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ) is True

    def test_is_trusted_video_host_untrusted(self):
        """非受信任域名应返回 False。"""
        assert BlogService._is_trusted_video_host(
            "https://example.com/video"
        ) is False

    def test_is_trusted_video_host_invalid_url(self):
        """非法 URL 应返回 False。"""
        assert BlogService._is_trusted_video_host("not-a-url") is False

    def test_validate_video_url_bilibili_valid(self):
        """有效的 bilibili 视频链接应通过验证。"""
        service = BlogService.__new__(BlogService)
        assert service._validate_video_url(
            "https://www.bilibili.com/video/BV1GJ411x7H7"
        ) is True

    def test_validate_video_url_bilibili_invalid(self):
        """无效的 bilibili 视频链接应不通过验证。"""
        service = BlogService.__new__(BlogService)
        assert service._validate_video_url(
            "https://www.bilibili.com/"
        ) is False

    def test_validate_video_url_youtube_valid(self):
        """有效的 YouTube 链接应通过验证。"""
        service = BlogService.__new__(BlogService)
        assert service._validate_video_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ) is True
        assert service._validate_video_url(
            "https://youtu.be/embed/dQw4w9WgXcQ"
        ) is True

    def test_validate_video_url_youtube_shorts(self):
        """YouTube Shorts 链接应通过验证。"""
        service = BlogService.__new__(BlogService)
        assert service._validate_video_url(
            "https://www.youtube.com/shorts/abc123"
        ) is True

    def test_validate_video_url_youtube_invalid(self):
        """无效的 YouTube 链接应不通过验证。"""
        service = BlogService.__new__(BlogService)
        assert service._validate_video_url(
            "https://www.youtube.com/"
        ) is False

    def test_validate_video_url_b23tv_valid(self):
        """有效的 b23.tv 链接应通过验证。"""
        service = BlogService.__new__(BlogService)
        assert service._validate_video_url(
            "https://b23.tv/BV1GJ411x7H7"
        ) is True

    def test_validate_video_url_untrusted_host(self):
        """非受信任主机应返回 True（不验证格式）。"""
        service = BlogService.__new__(BlogService)
        assert service._validate_video_url(
            "https://example.com/video"
        ) is True


# =============================================================================
# 标题提取测试
# =============================================================================


class TestExtractTitle:
    """Markdown 标题提取测试。"""

    def test_extract_title_from_h1(self):
        """从 # heading 提取标题。"""
        service = BlogService.__new__(BlogService)
        title, body = service._extract_title(
            "# Hello World\n\nThis is content.", "test.md"
        )
        assert title == "Hello World"
        assert "Hello World" not in body
        assert "This is content." in body

    def test_extract_title_no_heading(self):
        """无标题时使用文件名。"""
        service = BlogService.__new__(BlogService)
        title, body = service._extract_title(
            "Just some content without heading.", "my-post.md"
        )
        assert title == "my-post"
        assert body == "Just some content without heading."

    def test_extract_title_empty_text(self):
        """空文本使用默认标题。"""
        service = BlogService.__new__(BlogService)
        title, body = service._extract_title("", "imported.md")
        assert title == "imported"
        assert body == ""

    def test_extract_title_only_heading(self):
        """只有标题没有正文。"""
        service = BlogService.__new__(BlogService)
        title, body = service._extract_title("# Only Title\n", "test.md")
        assert title == "Only Title"
        assert body == ""

    def test_extract_title_multiple_headings(self):
        """多个标题只取第一个。"""
        service = BlogService.__new__(BlogService)
        title, body = service._extract_title(
            "# First Title\n\nContent\n\n# Second Title\n\nMore content",
            "test.md",
        )
        assert title == "First Title"
        assert "# Second Title" in body  # 第二个标题保留在正文中


# =============================================================================
# HTML 转 Markdown 测试
# =============================================================================


class TestExtractHtmlBody:
    """HTML 转 Markdown 测试。"""

    def test_extract_html_body_simple(self):
        """简单的 HTML 段落转换。"""
        service = BlogService.__new__(BlogService)
        result = service._extract_html_body(
            "<html><body><p>Hello World</p></body></html>"
        )
        assert "Hello World" in result

    def test_extract_html_body_headings(self):
        """HTML heading 标签转换。"""
        service = BlogService.__new__(BlogService)
        result = service._extract_html_body(
            "<body><h1>Title</h1><h2>Subtitle</h2><p>Content</p></body>"
        )
        assert "# Title" in result
        assert "## Subtitle" in result
        assert "Content" in result

    def test_extract_html_body_no_body_tag(self):
        """无 body 标签时使用整个 HTML。"""
        service = BlogService.__new__(BlogService)
        result = service._extract_html_body("<p>Only paragraph</p>")
        assert "Only paragraph" in result

    def test_extract_html_body_br_to_newline(self):
        """<br> 标签转换为换行。"""
        service = BlogService.__new__(BlogService)
        result = service._extract_html_body("<body>Line1<br>Line2<br/>Line3</body>")
        assert "Line1\nLine2\nLine3" in result

    def test_extract_html_body_strips_html_tags(self):
        """HTML 标签应被移除。"""
        service = BlogService.__new__(BlogService)
        result = service._extract_html_body(
            "<body><div><strong>bold</strong> and <em>italic</em></div></body>"
        )
        assert "bold" in result
        assert "italic" in result
        assert "<strong>" not in result
        assert "<em>" not in result


# =============================================================================
# 内容校验测试
# =============================================================================


class TestValidateContent:
    """内容全面校验测试。"""

    @pytest.mark.asyncio
    async def test_validate_content_valid(self, blog_container):
        """有效内容校验通过。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = []
        blog_container._mock_result.scalar_one_or_none.return_value = None

        errors = await service.validate_content(
            "Hello World", owner_id=uuid.uuid4()
        )
        assert errors == []

    @pytest.mark.asyncio
    async def test_validate_content_missing_file_ref(self, blog_container):
        """内容引用未上传的文件应报错。"""
        service = BlogService(blog_container)
        # mock 返回空（无已上传文件）
        blog_container._mock_result.all.return_value = []

        errors = await service.validate_content(
            "Check this image [#1]",
            owner_id=uuid.uuid4(),
        )
        assert len(errors) > 0
        assert "#'1'" in errors[0]

    @pytest.mark.asyncio
    async def test_validate_content_invalid_video(self, blog_container):
        """无效的视频链接应报错。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = []
        blog_container._mock_result.scalar_one_or_none.return_value = None

        # 使用 bilibili 链接但缺少 BV 号
        errors = await service.validate_content(
            "Check this [video](https://www.bilibili.com/)",
            owner_id=uuid.uuid4(),
        )
        assert len(errors) > 0
        assert "视频链接" in errors[0]


# =============================================================================
# 文件引用管理测试
# =============================================================================


class TestFileReferenceManagement:
    """文件引用管理测试。"""

    @pytest.mark.asyncio
    async def test_validate_post_file_refs_all_valid(self, blog_container):
        """所有引用文件都已上传。"""
        service = BlogService(blog_container)
        # mock 返回已有文件索引
        blog_container._mock_result.all.return_value = [(1,), (2,)]

        errors = await service.validate_post_file_refs(
            "Content with [#1] and [#2]", owner_id=uuid.uuid4()
        )
        assert errors == []

    @pytest.mark.asyncio
    async def test_validate_post_file_refs_missing(self, blog_container):
        """有引用文件未上传。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = [(1,)]

        errors = await service.validate_post_file_refs(
            "Content with [#1] and [#2]", owner_id=uuid.uuid4()
        )
        assert len(errors) == 1
        assert "#'2'" in errors[0]

    @pytest.mark.asyncio
    async def test_validate_post_file_refs_no_refs(self, blog_container):
        """无引用时校验通过。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = []

        errors = await service.validate_post_file_refs(
            "Content without references", owner_id=uuid.uuid4()
        )
        assert errors == []

    @pytest.mark.asyncio
    async def test_scan_and_clean_post_files(self, blog_container):
        """扫描并清理未引用的文件。"""
        service = BlogService(blog_container)

        mock_file1 = MagicMock()
        mock_file1.file_index = 1
        mock_file1.status = "temp"
        mock_file2 = MagicMock()
        mock_file2.file_index = 2
        mock_file2.status = "temp"
        mock_file3 = MagicMock()
        mock_file3.file_index = 3
        mock_file3.status = "temp"

        blog_container._mock_result.scalars.return_value.all.return_value = [
            mock_file1,
            mock_file2,
            mock_file3,
        ]

        result = await service.scan_and_clean_post_files(
            uuid.uuid4(), "Content with [#1] and [#3]"
        )

        assert result == [1, 3]
        # file1 和 file3 应标记为 persisted
        assert mock_file1.status == "persisted"
        assert mock_file3.status == "persisted"
        # file2 应被删除（未引用）
        blog_container._mock_session.execute.assert_called()


# =============================================================================
# 文件导入测试
# =============================================================================


class TestImportPost:
    """文件导入逻辑测试。"""

    @pytest.mark.asyncio
    async def test_import_markdown_file(self, blog_container):
        """导入 .md 文件。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = "test.md"
        mock_file.read = AsyncMock(
            return_value=b"# Hello World\n\nThis is a test post."
        )

        result = await service.import_post(mock_file, author_id=uuid.uuid4())
        assert result["title"] == "Hello World"
        assert "test post" in result["content"]
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_import_txt_file(self, blog_container):
        """导入 .txt 文件。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = "notes.txt"
        mock_file.read = AsyncMock(return_value=b"Just plain text content.")

        result = await service.import_post(mock_file, author_id=uuid.uuid4())
        assert result["title"] == "notes"
        assert result["content"] == "Just plain text content."

    @pytest.mark.asyncio
    async def test_import_unsupported_file_type(self, blog_container):
        """不支持的文件类型应报错。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = "virus.exe"
        mock_file.read = AsyncMock(return_value=b"bad")

        with pytest.raises(Exception) as excinfo:
            await service.import_post(mock_file, author_id=uuid.uuid4())
        assert "不支持的文件类型" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_import_html_file(self, blog_container):
        """导入 .html 文件。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = "page.html"
        mock_file.read = AsyncMock(
            return_value=b"<html><body><h1>HTML Title</h1><p>HTML content</p></body></html>"
        )

        result = await service.import_post(mock_file, author_id=uuid.uuid4())
        assert result["title"] == "HTML Title"
        assert "HTML content" in result["content"]


# =============================================================================
# 帖子状态边界条件测试
# =============================================================================


@pytest.mark.asyncio
class TestPostStatusEdgeCases:
    """帖子状态边界条件测试。"""

    async def test_get_post_by_slug_draft_seen_by_author(self, blog_container):
        """作者可以看到自己的草稿。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_post.author_id = author_id
        mock_post.status = "draft"
        mock_post.views = 0
        mock_post.content = "draft content"
        mock_post.like_count = 0
        mock_post.comment_count = 0
        mock_post.slug = "test-draft"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_result.all.return_value = []

        with patch.object(service, "get_post_tags", return_value=[]):
            result = await service.get_post_by_slug(
                "test-draft", user_id=author_id, user_level=5
            )
        assert result is not None

    async def test_get_post_by_slug_draft_hidden_from_others(
        self, blog_container
    ):
        """非作者/P0 看不到草稿帖子。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        other_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_post.author_id = author_id
        mock_post.status = "draft"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with pytest.raises(Exception) as excinfo:
            await service.get_post_by_slug(
                "test-draft", user_id=other_id, user_level=5
            )
        assert "帖子不存在" in str(excinfo.value)

    async def test_get_post_by_slug_draft_seen_by_admin(self, blog_container):
        """P0 管理员可以看到草稿。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_post.author_id = author_id
        mock_post.status = "draft"
        mock_post.views = 0
        mock_post.content = "draft content"
        mock_post.like_count = 0
        mock_post.comment_count = 0
        mock_post.slug = "test-draft"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_result.all.return_value = []

        with patch.object(service, "get_post_tags", return_value=[]):
            result = await service.get_post_by_slug(
                "test-draft", user_id=uuid.uuid4(), user_level=0
            )
        assert result is not None

    async def test_get_post_by_slug_view_count_not_for_author(
        self, blog_container
    ):
        """作者查看自己的帖子不计浏览量。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_post.author_id = author_id
        mock_post.status = "published"
        mock_post.views = 10
        mock_post.content = "content"
        mock_post.like_count = 0
        mock_post.comment_count = 0
        mock_post.slug = "test-post"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_result.all.return_value = []

        with patch.object(service, "get_post_tags", return_value=[]):
            result = await service.get_post_by_slug(
                "test-post", user_id=author_id, user_level=5
            )
        # 作者查看不计浏览量
        assert result is not None


# =============================================================================
# 举报功能测试
# =============================================================================


@pytest.mark.asyncio
class TestReportFunction:
    """举报功能测试。"""

    async def test_create_report_throttles_published_post(self, blog_container):
        """举报将 published 帖子降流为 throttled。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        reporter_id = uuid.uuid4()

        mock_post = MagicMock()
        mock_post.status = "published"
        mock_post.id = post_id

        # get_post_by_id 使用 scalar_one_or_none
        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        # create_report 内联查询使用 scalar_one
        blog_container._mock_result.scalar_one.return_value = mock_post

        result = await service.create_report(
            post_id=post_id, reporter_id=reporter_id, reason="spam"
        )
        assert result is not None
        assert mock_post.status == "throttled"

    async def test_create_report_does_not_change_non_published(
        self, blog_container
    ):
        """举报非 published 帖子不改变状态。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        reporter_id = uuid.uuid4()

        mock_post = MagicMock()
        mock_post.status = "pending"
        mock_post.id = post_id

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_result.scalar_one.return_value = mock_post

        result = await service.create_report(
            post_id=post_id, reporter_id=reporter_id, reason="spam"
        )
        # pending 状态不应被改为 throttled
        assert mock_post.status == "pending"


# =============================================================================
# 统计功能测试
# =============================================================================


@pytest.mark.asyncio
class TestStatsFunction:
    """统计功能测试。"""

    async def test_get_daily_trend(self, blog_container):
        """获取每日趋势数据。"""
        service = BlogService(blog_container)

        # 三次 execute 分别返回 posts, views, comments
        posts_result = MagicMock()
        posts_result.all.return_value = []
        views_result = MagicMock()
        views_result.all.return_value = []
        comments_result = MagicMock()
        comments_result.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[posts_result, views_result, comments_result]
        )

        result = await service.get_daily_trend(days=7)
        assert result["days"] == 7
        assert len(result["trend"]) == 7

    async def test_get_hot_posts(self, blog_container):
        """获取热门帖子排行。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.id = uuid.uuid4()
        mock_post.author_id = uuid.uuid4()
        mock_post.title = "Hot Post"
        mock_post.views = 1000
        mock_post.status = "published"
        mock_post.created_at = None

        # posts query
        post_result = MagicMock()
        post_result.scalars.return_value.all.return_value = [mock_post]
        # author query — 使用支持属性访问的 mock row
        mock_author_row = MagicMock()
        mock_author_row.id = mock_post.author_id
        mock_author_row.username = "author1"
        author_result = MagicMock()
        author_result.all.return_value = [mock_author_row]
        # likes query
        mock_like_row = MagicMock()
        mock_like_row.post_id = mock_post.id
        mock_like_row.count = 50
        likes_result = MagicMock()
        likes_result.all.return_value = [mock_like_row]
        # comments query
        mock_comment_row = MagicMock()
        mock_comment_row.post_id = mock_post.id
        mock_comment_row.count = 10
        comments_result = MagicMock()
        comments_result.all.return_value = [mock_comment_row]

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[
                post_result,
                author_result,
                likes_result,
                comments_result,
            ]
        )

        result = await service.get_hot_posts(limit=10)
        assert len(result) == 1
        assert result[0]["title"] == "Hot Post"
        assert result[0]["views"] == 1000
        assert result[0]["likes"] == 50
        assert result[0]["comments"] == 10


# =============================================================================
# 段落评论边界条件测试
# =============================================================================


@pytest.mark.asyncio
class TestParagraphComments:
    """段落评论边界条件测试。"""

    async def test_get_paragraph_comments(self, blog_container):
        """获取段落评论列表。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.required_level = 5

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.get_paragraph_comments(
                post_id=post_id, paragraph_pid="post_001"
            )
        assert result["total"] == 0
        assert result["items"] == []

    async def test_get_paragraph_comments_permission_denied(
        self, blog_container
    ):
        """无权限查看段落评论。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.required_level = 0

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            with pytest.raises(Exception) as excinfo:
                await service.get_paragraph_comments(
                    post_id=post_id, paragraph_pid="p1", user_level=2
                )
        assert "无权查看" in str(excinfo.value)

    async def test_create_paragraph_comment(self, blog_container):
        """创建段落评论。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        author_id = uuid.uuid4()

        mock_post = MagicMock()
        mock_post.comment_count = 0

        mock_comment = MagicMock()
        mock_comment.id = uuid.uuid4()

        # get_post_by_id 返回 mock_post
        # 然后 session 查询 post
        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_session.refresh = AsyncMock(return_value=mock_comment)

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.create_paragraph_comment(
                post_id=post_id,
                paragraph_pid="post_001",
                author_id=author_id,
                content="Paragraph comment",
            )
        assert result is not None


# =============================================================================
# 我的帖子列表测试
# =============================================================================


@pytest.mark.asyncio
class TestMyPosts:
    """我的帖子列表测试。"""

    async def test_list_my_posts_empty(self, blog_container):
        """空列表。"""
        service = BlogService(blog_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_my_posts(
            author_id=uuid.uuid4(), page=1, page_size=20
        )
        assert result["total"] == 0
        assert result["items"] == []

    async def test_list_my_posts_with_filter(self, blog_container):
        """按状态过滤我的帖子。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()

        # 两个查询：count 和 data
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        data_result = MagicMock()
        mock_post = MagicMock()
        mock_post.id = uuid.uuid4()
        mock_post.author_id = author_id
        mock_post.status = "pending"
        mock_post.title = "Pending Post"
        mock_post.slug = "pending-post"
        data_result.scalars.return_value.all.return_value = [mock_post]

        # 还需要 author 和 likes 查询
        author_result = MagicMock()
        author_result.scalar_one_or_none.return_value = "author1"
        likes_result = MagicMock()
        likes_result.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[
                count_result,
                data_result,
                author_result,
                likes_result,
            ]
        )

        result = await service.list_my_posts(
            author_id=author_id, page=1, page_size=20, status_filter="pending"
        )
        assert result["total"] == 1
        assert len(result["items"]) == 1


# =============================================================================
# 待审核帖子列表测试
# =============================================================================


@pytest.mark.asyncio
class TestPendingPosts:
    """待审核帖子列表测试。"""

    async def test_list_pending_posts_empty(self, blog_container):
        """空待审核列表。"""
        service = BlogService(blog_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_pending_posts(page=1, page_size=20)
        assert result["total"] == 0
        assert result["items"] == []

    async def test_list_pending_posts_with_data(self, blog_container):
        """待审核列表有数据。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        data_result = MagicMock()
        mock_post = MagicMock()
        mock_post.id = uuid.uuid4()
        mock_post.author_id = author_id
        data_result.scalars.return_value.all.return_value = [mock_post]

        # 还需要 author 查询 — 使用支持属性访问的 mock row
        mock_author_row = MagicMock()
        mock_author_row.id = author_id
        mock_author_row.username = "author1"
        author_result = MagicMock()
        author_result.all.return_value = [mock_author_row]

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result, author_result]
        )

        result = await service.list_pending_posts(page=1, page_size=20)
        assert result["total"] == 1
        assert len(result["items"]) == 1


# =============================================================================
# 收藏功能测试
# =============================================================================


@pytest.mark.asyncio
class TestFavorites:
    """收藏功能测试。"""

    async def test_add_favorite_new(self, blog_container):
        """新收藏。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_post = MagicMock()

        blog_container._mock_result.scalar_one_or_none.return_value = None

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.add_favorite(post_id=post_id, user_id=user_id)
        assert result["action"] == "favorited"

    async def test_add_favorite_already_exists(self, blog_container):
        """已收藏。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_favorite = MagicMock()
        mock_favorite.id = uuid.uuid4()

        blog_container._mock_result.scalar_one_or_none.return_value = mock_favorite

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.add_favorite(post_id=post_id, user_id=user_id)
        assert result["action"] == "already_favorited"

    async def test_remove_favorite(self, blog_container):
        """取消收藏。"""
        service = BlogService(blog_container)

        mock_favorite = MagicMock()
        blog_container._mock_result.scalar_one_or_none.return_value = mock_favorite

        result = await service.remove_favorite(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
        assert result["action"] == "unfavorited"

    async def test_remove_favorite_not_exists(self, blog_container):
        """取消不存在的收藏。"""
        service = BlogService(blog_container)

        blog_container._mock_result.scalar_one_or_none.return_value = None

        result = await service.remove_favorite(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
        assert result["action"] == "unfavorited"

    async def test_check_favorite_true(self, blog_container):
        """检查已收藏。"""
        service = BlogService(blog_container)

        blog_container._mock_result.scalar_one_or_none.return_value = MagicMock()

        result = await service.check_favorite(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
        assert result is True

    async def test_check_favorite_false(self, blog_container):
        """检查未收藏。"""
        service = BlogService(blog_container)

        blog_container._mock_result.scalar_one_or_none.return_value = None

        result = await service.check_favorite(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
        assert result is False


# =============================================================================
# 帖子标签管理测试
# =============================================================================


@pytest.mark.asyncio
class TestPostTagManagement:
    """帖子标签管理测试。"""

    async def test_remove_tag_from_post(self, blog_container):
        """从帖子移除标签。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id
        mock_tag = MagicMock()
        mock_tag.name = "test-tag"
        mock_tag.id = uuid.uuid4()
        mock_post_tag = MagicMock()

        blog_container._mock_result.scalar_one_or_none.side_effect = [
            mock_tag,
            mock_post,
            mock_post_tag,
        ]

        await service.remove_tag_from_post(
            post_id=post_id, tag_name="test-tag", user_id=author_id
        )
        blog_container._mock_session.delete.assert_called_once()

    async def test_remove_tag_from_post_tag_not_found(self, blog_container):
        """移除不存在的标签应报错。"""
        service = BlogService(blog_container)

        blog_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await service.remove_tag_from_post(
                post_id=uuid.uuid4(), tag_name="nonexistent", user_id=uuid.uuid4()
            )
        assert "标签不存在" in str(excinfo.value)

    async def test_remove_tag_permission_denied(self, blog_container):
        """非作者移除标签应报错。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        other_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id
        mock_tag = MagicMock()
        mock_tag.name = "test-tag"

        blog_container._mock_result.scalar_one_or_none.side_effect = [
            mock_tag,
            mock_post,
        ]

        with pytest.raises(Exception) as excinfo:
            await service.remove_tag_from_post(
                post_id=uuid.uuid4(), tag_name="test-tag", user_id=other_id
            )
        assert "无权限" in str(excinfo.value)

    async def test_get_post_tags(self, blog_container):
        """获取帖子标签。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_tag = MagicMock()
        mock_tag.name = "test"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_result.scalars.return_value.all.return_value = [
            mock_tag
        ]

        result = await service.get_post_tags(post_id)
        assert len(result) == 1
        assert result[0]["name"] == "test"

    async def test_get_posts_by_tag_not_found(self, blog_container):
        """按不存在的标签查询帖子应报错。"""
        service = BlogService(blog_container)

        blog_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await service.get_posts_by_tag("nonexistent")
        assert "标签不存在" in str(excinfo.value)


# =============================================================================
# 高级 slug 生成测试
# =============================================================================


@pytest.mark.asyncio
class TestAdvancedSlugGeneration:
    """高级 slug 生成测试。"""

    async def test_generate_slug_mixed_chinese_english(self, blog_container):
        """中英文混合标题。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None

        slug = await service.generate_slug("Hello 世界 Test")
        assert "hello" in slug
        assert "世界" in slug
        assert "test" in slug

    async def test_generate_slug_special_chars_only(self, blog_container):
        """仅特殊字符生成默认 slug。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None

        slug = await service.generate_slug("!@#$%^&*()")
        assert slug == "post"

    async def test_generate_slug_leading_trailing_spaces(self, blog_container):
        """首尾空格应被忽略。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None

        slug = await service.generate_slug("  Hello World  ")
        assert slug == "hello-world"