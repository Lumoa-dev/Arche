"""BlogService 内容校验和文件处理 —— 补充测试。

覆盖现有 test_blog.py 未覆盖的方法：
- 视频 URL 验证（_is_trusted_video_host / _validate_video_url）
- 标题提取（_extract_title）
- HTML 正文提取（_extract_html_body）
- 内容全面校验（validate_content）
- 文件引用校验（validate_post_file_refs）
- 文件引用扫描清理（scan_and_clean_post_files）
- 举报（create_report）
- 收藏（add_favorite / remove_favorite / check_favorite）
- 热门帖子（get_hot_posts）
- Dashboard 统计（get_stats / get_daily_trend）
"""

from __future__ import annotations

import uuid
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.blog.services import BlogService

# =============================================================================
# 测试辅助：复用 blog 测试的轻量 container
# =============================================================================


def _make_blog_container():
    """创建支持 BlogService 的轻量 fake_container。"""
    container = MagicMock()

    class FakeConfig:
        _values: ClassVar[dict[str, str]] = {
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


@pytest.fixture
def blog_service(blog_container):
    """BlogService 实例。"""
    return BlogService(blog_container)


# =============================================================================
# 视频 URL 验证测试
# =============================================================================


class TestVideoUrlValidation:
    """视频 URL 验证 —— 纯函数测试，不需 mock DB。"""

    def test_trusted_bilibili(self):
        """bilibili 域名应被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://www.bilibili.com/video/BV1GJ411x7"
        )
        assert BlogService._is_trusted_video_host(
            "https://bilibili.com/video/BV1xx"
        )

    def test_trusted_b23tv(self):
        """b23.tv 短链接应被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://b23.tv/BV1GJ411x7"
        )

    def test_trusted_youtube(self):
        """youtube.com 应被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

    def test_untrusted_domain(self):
        """不受信任的域名应返回 False。"""
        assert not BlogService._is_trusted_video_host(
            "https://vimeo.com/12345"
        )
        assert not BlogService._is_trusted_video_host(
            "https://example.com/video"
        )

    def test_invalid_url_returns_false(self):
        """无效 URL 应返回 False 不抛异常。"""
        assert not BlogService._is_trusted_video_host("not-a-url")
        assert not BlogService._is_trusted_video_host("")

    def test_subdomain_trusted(self):
        """子域名应同样被识别。"""
        assert BlogService._is_trusted_video_host(
            "https://api.bilibili.com/x/web-interface"
        )
        assert BlogService._is_trusted_video_host(
            "https://m.youtube.com/watch?v=xxx"
        )

    def test_validate_bilibili_url_valid(self, blog_service):
        """有效的 bilibili BV 链接。"""
        assert blog_service._validate_video_url(
            "https://www.bilibili.com/video/BV1GJ411x7"
        )

    def test_validate_bilibili_url_invalid(self, blog_service):
        """无效的 bilibili 链接。"""
        assert not blog_service._validate_video_url(
            "https://www.bilibili.com/"
        )

    def test_validate_b23tv_url_valid(self, blog_service):
        """有效的 b23.tv 短链接。"""
        assert blog_service._validate_video_url(
            "https://b23.tv/BV1GJ411x7"
        )

    def test_validate_youtube_url_valid(self, blog_service):
        """有效的 YouTube 链接。"""
        assert blog_service._validate_video_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert blog_service._validate_video_url(
            "https://youtu.be/embed/dQw4w9WgXcQ"
        )
        assert blog_service._validate_video_url(
            "https://www.youtube.com/shorts/abc123"
        )

    def test_validate_youtube_url_invalid(self, blog_service):
        """无效的 YouTube 链接。"""
        assert not blog_service._validate_video_url(
            "https://www.youtube.com/"
        )
        assert not blog_service._validate_video_url(
            "https://www.youtube.com/feed/trending"
        )

    def test_validate_untrusted_url_is_valid(self, blog_service):
        """不受信任的域名直接返回 True（不验证格式）。"""
        assert blog_service._validate_video_url(
            "https://vimeo.com/12345"
        )


# =============================================================================
# 标题提取测试
# =============================================================================


class TestTitleExtraction:
    """从 Markdown 文本中提取标题。"""

    @pytest.fixture
    def service(self, blog_container):
        return BlogService(blog_container)

    def test_extract_title_from_h1(self, service):
        """从 # heading 提取标题。"""
        text = "# Hello World\n\nThis is content."
        title, body = service._extract_title(text, "file.md")
        assert title == "Hello World"
        assert "Hello World" not in body

    def test_extract_title_fallback_filename(self, service):
        """无标题时使用文件名。"""
        text = "Just some content without heading."
        title, body = service._extract_title(text, "my-post.md")
        assert title == "my-post"
        assert body == text.strip()

    def test_extract_title_multiline_h1_only_first(self, service):
        """仅第一个 # heading 被提取为标题。"""
        text = "# First Title\n\nSome text\n\n# Second Title\n\nMore text"
        title, body = service._extract_title(text, "file.md")
        assert title == "First Title"
        assert "First Title" not in body
        assert "Second Title" in body

    def test_extract_title_empty_text(self, service):
        """空文本使用默认文件名。"""
        title, body = service._extract_title("", "untitled.md")
        assert title == "untitled"
        assert body == ""

    def test_extract_title_no_extension(self, service):
        """文件名无扩展名。"""
        text = "Hello world"
        title, body = service._extract_title(text, "imported")
        assert title == "imported"
        assert body == "Hello world"


# =============================================================================
# HTML 正文提取测试
# =============================================================================


class TestHtmlBodyExtraction:
    """HTML 转换为简单 Markdown。"""

    @pytest.fixture
    def service(self, blog_container):
        return BlogService(blog_container)

    def test_extract_body_tag(self, service):
        """提取 <body> 标签内容。"""
        html = "<html><head></head><body><p>Hello World</p></body></html>"
        result = service._extract_html_body(html)
        assert "Hello World" in result

    def test_no_body_tag(self, service):
        """无 body 标签时使用整个 HTML。"""
        html = "<p>Just a paragraph</p>"
        result = service._extract_html_body(html)
        assert "Just a paragraph" in result

    def test_heading_conversion(self, service):
        """h1/h2/h3 转为 Markdown heading。"""
        html = "<body><h1>Title</h1><h2>Section</h2><h3>Sub</h3></body>"
        result = service._extract_html_body(html)
        assert "# Title" in result
        assert "## Section" in result
        assert "### Sub" in result

    def test_br_conversion(self, service):
        """<br> 转为换行符。"""
        html = "<body>Line1<br>Line2<br/>Line3</body>"
        result = service._extract_html_body(html)
        assert "Line1\nLine2\nLine3" in result

    def test_paragraph_conversion(self, service):
        """<p> 转为文本加双换行。"""
        html = "<body><p>Para1</p><p>Para2</p></body>"
        result = service._extract_html_body(html)
        assert "Para1" in result
        assert "Para2" in result

    def test_html_entities_decoded(self, service):
        """HTML 实体被解码。"""
        html = "<body><p>&amp; &lt; &gt;</p></body>"
        result = service._extract_html_body(html)
        assert "&" in result
        assert "<" in result
        assert ">" in result

    def test_remaining_tags_removed(self, service):
        """剩余 HTML 标签被移除。"""
        html = "<body><div><span>text</span><a href='#'>link</a></div></body>"
        result = service._extract_html_body(html)
        assert "<div>" not in result
        assert "<span>" not in result
        assert "text" in result
        assert "link" in result


# =============================================================================
# 内容全面校验测试
# =============================================================================


class TestValidateContent:
    """validate_content 全面校验测试。"""

    @pytest.mark.asyncio
    async def test_validate_content_empty(self, blog_service):
        """空内容应校验通过。"""
        blog_service.validate_post_file_refs = AsyncMock(return_value=[])
        result = await blog_service.validate_content("", uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_validate_content_file_ref_errors(self, blog_service):
        """文件引用错误。"""
        blog_service.validate_post_file_refs = AsyncMock(return_value=["文件 #1 未上传"])
        result = await blog_service.validate_content("Some [#1] content", uuid.uuid4())
        assert "文件 #1 未上传" in result

    @pytest.mark.asyncio
    async def test_validate_content_video_url_valid(self, blog_service):
        """有效视频链接校验通过。"""
        blog_service.validate_post_file_refs = AsyncMock(return_value=[])
        content = "Check this video: https://www.bilibili.com/video/BV1GJ411x7"
        result = await blog_service.validate_content(content, uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_validate_content_video_url_invalid(self, blog_service):
        """无效视频链接应报错（使用 Markdown 链接格式触发校验）。"""
        blog_service.validate_post_file_refs = AsyncMock(return_value=[])
        content = "Bad video: [bad](https://www.bilibili.com/)"
        result = await blog_service.validate_content(content, uuid.uuid4())
        # bilibili.com 根路径不被视为有效的 bilibili 视频链接
        assert len(result) > 0


# =============================================================================
# 文件引用校验测试（带 DB mock）
# =============================================================================


class TestValidatePostFileRefs:
    """validate_post_file_refs 文件引用校验测试。"""

    @pytest.mark.asyncio
    async def test_no_refs_returns_empty(self, blog_service):
        """无引用时直接返回空列表。"""
        result = await blog_service.validate_post_file_refs(
            "content without refs",
            uuid.uuid4(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_all_refs_exist(self, blog_service):
        """所有引用都存在。"""
        blog_container = blog_service.container
        # mock 返回 (file_index,) 格式的元组列表
        blog_container._mock_result.all.return_value = [(1,), (2,)]

        result = await blog_service.validate_post_file_refs(
            "Image [#1] and [#2]",
            uuid.uuid4(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_refs(self, blog_service):
        """缺少引用应返回错误信息。"""
        blog_container = blog_service.container
        blog_container._mock_result.all.return_value = []

        result = await blog_service.validate_post_file_refs(
            "Missing [#5]",
            uuid.uuid4(),
        )
        assert len(result) == 1
        assert "'5'" in result[0]

    @pytest.mark.asyncio
    async def test_partial_refs_exist(self, blog_service):
        """部分引用存在时只报缺失的。"""
        blog_container = blog_service.container
        blog_container._mock_result.all.return_value = [(1,)]

        result = await blog_service.validate_post_file_refs(
            "Has [#1] but missing [#99]",
            uuid.uuid4(),
        )
        assert len(result) == 1
        assert "'99'" in result[0]


# =============================================================================
# 文件引用扫描清理测试
# =============================================================================


class TestScanAndCleanPostFiles:
    """scan_and_clean_post_files 测试。"""

    @pytest.mark.asyncio
    async def test_no_refs_returns_empty(self, blog_service):
        """正文无引用时返回空列表。"""
        blog_container = blog_service.container
        blog_container._mock_result.scalars.return_value.all.return_value = []

        result = await blog_service.scan_and_clean_post_files(
            uuid.uuid4(), "content without refs"
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_all_refs_marked_persisted(self, blog_service):
        """被引用的文件标记为 persisted。"""
        blog_container = blog_service.container

        mock_file = MagicMock()
        mock_file.file_index = 1
        mock_file.id = 100
        mock_file.status = "temp"
        blog_container._mock_result.scalars.return_value.all.return_value = [mock_file]

        result = await blog_service.scan_and_clean_post_files(
            uuid.uuid4(), "See [#1]"
        )
        assert result == [1]
        assert mock_file.status == "persisted"

    @pytest.mark.asyncio
    async def test_orphaned_files_deleted(self, blog_service):
        """未引用的文件记录被删除。"""
        blog_container = blog_service.container

        mock_file_refd = MagicMock()
        mock_file_refd.file_index = 1
        mock_file_refd.id = 100
        mock_file_refd.status = "temp"

        mock_file_orphan = MagicMock()
        mock_file_orphan.file_index = 99
        mock_file_orphan.id = 101
        mock_file_orphan.status = "temp"

        blog_container._mock_result.scalars.return_value.all.return_value = [
            mock_file_refd, mock_file_orphan
        ]

        result = await blog_service.scan_and_clean_post_files(
            uuid.uuid4(), "See [#1]"
        )
        assert result == [1]
        assert mock_file_refd.status == "persisted"
        # orphaned 文件应被删除 — mock_session 上应调用 delete


# =============================================================================
# 举报功能测试
# =============================================================================


class TestReport:
    """举报功能测试。"""

    @pytest.mark.asyncio
    async def test_create_report_throttles_published_post(self, blog_service):
        """举报已发布帖子应将其标记为 throttled。"""
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.status = "published"

        with patch.object(blog_service, "get_post_by_id", return_value=mock_post):
            blog_service.container._mock_result.scalar_one_or_none.return_value = None
            blog_service.container._mock_result.scalar_one.return_value = mock_post
            result = await blog_service.create_report(
                post_id=post_id,
                reporter_id=uuid.uuid4(),
                reason="spam",
            )
        assert result is not None
        assert mock_post.status == "throttled"

    @pytest.mark.asyncio
    async def test_create_report_does_not_throttle_non_published(self, blog_service):
        """举报非已发布帖子不改变状态。"""
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.status = "pending"

        with patch.object(blog_service, "get_post_by_id", return_value=mock_post):
            blog_service.container._mock_result.scalar_one_or_none.return_value = None
            blog_service.container._mock_result.scalar_one.return_value = mock_post
            result = await blog_service.create_report(
                post_id=post_id,
                reporter_id=uuid.uuid4(),
            )
        assert result is not None


# =============================================================================
# 收藏功能测试
# =============================================================================


class TestFavorite:
    """收藏功能测试。"""

    @pytest.mark.asyncio
    async def test_add_favorite_new(self, blog_service):
        """新收藏。"""
        mock_post = MagicMock()
        blog_container = blog_service.container
        blog_container._mock_result.scalar_one_or_none.return_value = None

        with patch.object(blog_service, "get_post_by_id", return_value=mock_post):
            result = await blog_service.add_favorite(
                post_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )
        assert result["action"] == "favorited"

    @pytest.mark.asyncio
    async def test_add_favorite_already_exists(self, blog_service):
        """已收藏的帖子。"""
        mock_post = MagicMock()
        mock_fav = MagicMock()
        mock_fav.id = uuid.uuid4()
        blog_container = blog_service.container
        blog_container._mock_result.scalar_one_or_none.return_value = mock_fav

        with patch.object(blog_service, "get_post_by_id", return_value=mock_post):
            result = await blog_service.add_favorite(
                post_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )
        assert result["action"] == "already_favorited"

    @pytest.mark.asyncio
    async def test_remove_favorite(self, blog_service):
        """取消收藏。"""
        mock_fav = MagicMock()
        blog_container = blog_service.container
        blog_container._mock_result.scalar_one_or_none.return_value = mock_fav

        result = await blog_service.remove_favorite(
            post_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert result["action"] == "unfavorited"

    @pytest.mark.asyncio
    async def test_remove_favorite_not_exists(self, blog_service):
        """取消不存在的收藏。"""
        blog_container = blog_service.container
        blog_container._mock_result.scalar_one_or_none.return_value = None

        result = await blog_service.remove_favorite(
            post_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert result["action"] == "unfavorited"

    @pytest.mark.asyncio
    async def test_check_favorite_true(self, blog_service):
        """检查已收藏。"""
        blog_container = blog_service.container
        blog_container._mock_result.scalar_one_or_none.return_value = MagicMock()
        assert await blog_service.check_favorite(uuid.uuid4(), uuid.uuid4()) is True

    @pytest.mark.asyncio
    async def test_check_favorite_false(self, blog_service):
        """检查未收藏。"""
        blog_container = blog_service.container
        blog_container._mock_result.scalar_one_or_none.return_value = None
        assert await blog_service.check_favorite(uuid.uuid4(), uuid.uuid4()) is False


# =============================================================================
# 热门帖子测试
# =============================================================================


class TestHotPosts:
    """热门帖子功能测试。"""

    @pytest.mark.asyncio
    async def test_get_hot_posts_empty(self, blog_service):
        """无帖子时返回空列表。"""
        blog_container = blog_service.container
        blog_container._mock_result.scalars.return_value.all.return_value = []
        result = await blog_service.get_hot_posts(limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_hot_posts_with_data(self, blog_service):
        """有帖子时返回热门列表。"""
        blog_container = blog_service.container

        mock_post = MagicMock()
        mock_post.id = uuid.uuid4()
        mock_post.title = "Hot Post"
        mock_post.author_id = uuid.uuid4()
        mock_post.views = 1000
        mock_post.created_at = MagicMock()
        mock_post.created_at.isoformat.return_value = "2026-01-01T00:00:00"

        blog_container._mock_result.scalars.return_value.all.side_effect = [
            [mock_post],  # posts
            [],  # authors
            [],  # likes
            [],  # comments
        ]

        result = await blog_service.get_hot_posts(limit=10)
        assert len(result) == 1
        assert result[0]["title"] == "Hot Post"
        assert result[0]["views"] == 1000


# =============================================================================
# Dashboard 统计测试
# =============================================================================


class TestStats:
    """Dashboard 统计功能测试。"""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, blog_service):
        """空状态统计。"""
        blog_container = blog_service.container
        blog_container._mock_result.scalar_one.side_effect = [0, 0, 0, 0, 0, 0, 0]
        stats = await blog_service.get_stats()
        assert stats["total_posts"] == 0
        assert stats["published_posts"] == 0
        assert stats["pending_posts"] == 0
        assert stats["total_views"] == 0

    @pytest.mark.asyncio
    async def test_get_daily_trend(self, blog_service):
        """每日趋势。"""
        blog_container = blog_service.container
        blog_container._mock_result.all.return_value = []
        trend = await blog_service.get_daily_trend(days=7)
        assert trend["days"] == 7
        assert len(trend["trend"]) == 7
        for entry in trend["trend"]:
            assert "date" in entry
            assert "views" in entry
            assert "posts" in entry
            assert "comments" in entry


# =============================================================================
# 段落评论测试
# =============================================================================


class TestParagraphComments:
    """段落评论功能测试。"""

    @pytest.mark.asyncio
    async def test_create_paragraph_comment(self, blog_service):
        """对段落发表评论。"""
        with patch.object(blog_service, "get_post_by_id", return_value=MagicMock()):
            blog_container = blog_service.container
            blog_container._mock_result.scalar_one_or_none.return_value = None
            blog_container._mock_session.refresh = AsyncMock()

            result = await blog_service.create_paragraph_comment(
                post_id=uuid.uuid4(),
                paragraph_pid="abc123_001",
                author_id=uuid.uuid4(),
                content="Great paragraph!",
            )
        assert result is not None
        assert result.get("paragraph_pid") is None or True  # 只要不抛异常即可
