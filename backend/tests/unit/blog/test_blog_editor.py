"""博客编辑器重构相关功能测试 —— 文件导入、内容校验、视频链接、举报、收藏、统计。

覆盖重构后新增但未被现有测试覆盖的服务方法：
  - import_post / _extract_title / _extract_html_body / _parse_docx
  - validate_content / validate_post_file_refs / scan_and_clean_post_files
  - _is_trusted_video_host / _validate_video_url
  - create_report / get_hot_posts / get_stats / get_daily_trend
  - add_favorite / remove_favorite / check_favorite / list_favorites
  - list_my_posts / get_post_detail_by_id / get_posts_by_tag
  - get_like_status / remove_tag_from_post / list_pending_posts
  - get_paragraph_comments / create_paragraph_comment
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.blog.services import BlogService


# =============================================================================
# 复用 test_blog.py 中的 mock 辅助
# =============================================================================


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
    return _make_blog_container()


# =============================================================================
# 文件导入测试
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceImportPost:
    """import_post 文件导入功能测试。"""

    async def test_import_markdown_with_title(self, blog_container):
        """导入 .md 文件，应提取 # 标题并分离正文。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = "test.md"
        mock_file.read = AsyncMock(return_value=b"# Hello World\n\nThis is content.")

        result = await service.import_post(
            file=mock_file, author_id=uuid.uuid4()
        )

        assert result["title"] == "Hello World"
        assert "This is content" in result["content"]
        assert result["status"] == "pending"

    async def test_import_markdown_without_title(self, blog_container):
        """导入无标题的 .md 文件，应使用文件名作为标题。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = "my-notes.md"
        mock_file.read = AsyncMock(return_value=b"Just some text without a heading.")

        result = await service.import_post(
            file=mock_file, author_id=uuid.uuid4()
        )

        assert result["title"] == "my-notes"
        assert "Just some text" in result["content"]

    async def test_import_txt_file(self, blog_container):
        """导入 .txt 文件，无标题时用文件名。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = "readme.txt"
        mock_file.read = AsyncMock(return_value=b"Plain text content.")

        result = await service.import_post(
            file=mock_file, author_id=uuid.uuid4()
        )

        assert result["title"] == "readme"
        assert result["content"] == "Plain text content."

    async def test_import_html_file(self, blog_container):
        """导入 .html 文件，应提取 body 内容并转为简单 Markdown。"""
        service = BlogService(blog_container)

        html_content = b"<html><body><h1>Title</h1><p>Paragraph</p></body></html>"
        mock_file = MagicMock()
        mock_file.filename = "page.html"
        mock_file.read = AsyncMock(return_value=html_content)

        result = await service.import_post(
            file=mock_file, author_id=uuid.uuid4()
        )

        # _extract_html_body 将 <h1>Title</h1> 转为 # Title
        # _extract_title 提取 Title 作为标题并从正文中移除 # Title 行
        assert result["title"] == "Title"
        assert result["content"] == "Paragraph"

    async def test_import_unsupported_file_type(self, blog_container):
        """导入不支持的文件类型应拒绝。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = "data.pdf"
        mock_file.read = AsyncMock(return_value=b"pdf content")

        with pytest.raises(Exception) as excinfo:
            await service.import_post(
                file=mock_file, author_id=uuid.uuid4()
            )
        assert "不支持的文件类型" in str(excinfo.value)

    async def test_import_docx_missing_dependency(self, blog_container):
        """导入 .docx 但 python-docx 未安装时应报错。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = "report.docx"
        mock_file.read = AsyncMock(return_value=b"fake docx")

        with patch.dict("sys.modules", {"docx": None}):
            with pytest.raises(Exception) as excinfo:
                await service.import_post(
                    file=mock_file, author_id=uuid.uuid4()
                )
        assert "python-docx 未安装" in str(excinfo.value)

    async def test_import_post_with_tags(self, blog_container):
        """导入帖子时传入标签。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = "test.md"
        mock_file.read = AsyncMock(return_value=b"# Hello\n\nContent.")

        result = await service.import_post(
            file=mock_file, author_id=uuid.uuid4(), tags=["python", "tutorial"]
        )

        assert result["tags"] == ["python", "tutorial"]

    async def test_import_post_no_filename(self, blog_container):
        """文件名为空时应因无后缀而拒绝导入。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.filename = ""
        mock_file.read = AsyncMock(return_value=b"content without title")

        with pytest.raises(Exception) as excinfo:
            await service.import_post(
                file=mock_file, author_id=uuid.uuid4()
            )
        assert "不支持的文件类型" in str(excinfo.value)


# =============================================================================
# 标题提取测试
# =============================================================================


class TestBlogServiceExtractTitle:
    """_extract_title 标题提取测试。"""

    def test_extract_title_from_markdown(self):
        """从 Markdown 文本中提取 # 标题。"""
        service = BlogService(MagicMock())
        title, body = service._extract_title(
            "# My Title\n\nSome content here.", "fallback.md"
        )
        assert title == "My Title"
        assert "Some content here" in body
        assert "# My Title" not in body

    def test_extract_title_no_heading(self):
        """无标题时使用文件名。"""
        service = BlogService(MagicMock())
        title, body = service._extract_title(
            "Just content without heading.", "my_doc.md"
        )
        assert title == "my_doc"
        assert body == "Just content without heading."

    def test_extract_title_empty_text(self):
        """空文本时使用文件名。"""
        service = BlogService(MagicMock())
        title, body = service._extract_title("", "empty.md")
        assert title == "empty"
        assert body == ""


# =============================================================================
# HTML 提取测试
# =============================================================================


class TestBlogServiceExtractHtmlBody:
    """_extract_html_body HTML 提取测试。"""

    def test_extract_html_body_with_body_tag(self):
        """提取 <body> 标签内的内容。"""
        service = BlogService(MagicMock())
        html = "<html><head></head><body><h1>Title</h1><p>Content</p></body></html>"
        result = service._extract_html_body(html)
        assert "# Title" in result
        assert "Content" in result

    def test_extract_html_body_no_body_tag(self):
        """无 <body> 标签时直接处理整个 HTML。"""
        service = BlogService(MagicMock())
        html = "<h1>Title</h1><p>Content</p>"
        result = service._extract_html_body(html)
        assert "# Title" in result
        assert "Content" in result

    def test_extract_html_body_with_br(self):
        """<br> 标签应转为换行。"""
        service = BlogService(MagicMock())
        html = "<body>Line1<br>Line2<br/>Line3</body>"
        result = service._extract_html_body(html)
        assert "Line1\nLine2\nLine3" in result

    def test_extract_html_body_handles_mixed_heading_levels(self):
        """不同级别的标题应正确转换。"""
        service = BlogService(MagicMock())
        html = "<body><h1>H1</h1><h2>H2</h2><h3>H3</h3></body>"
        result = service._extract_html_body(html)
        assert "# H1" in result
        assert "## H2" in result
        assert "### H3" in result

    def test_extract_html_body_unescapes_html_entities(self):
        """HTML 实体应被反转义。"""
        service = BlogService(MagicMock())
        html = "<body><p>Tom &amp; Jerry</p></body>"
        result = service._extract_html_body(html)
        assert "Tom & Jerry" in result


# =============================================================================
# 视频链接验证测试
# =============================================================================


class TestBlogServiceVideoUrlValidation:
    """视频链接验证测试。"""

    def test_is_trusted_video_host_bilibili(self):
        """bilibili.com 域名应被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://www.bilibili.com/video/BV1GJ411x7"
        ) is True
        assert BlogService._is_trusted_video_host(
            "https://b23.tv/abc123"
        ) is True

    def test_is_trusted_video_host_youtube(self):
        """youtube.com 域名应被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ) is True

    def test_is_trusted_video_host_untrusted(self):
        """不受信任的域名应返回 False。"""
        assert BlogService._is_trusted_video_host(
            "https://vimeo.com/12345"
        ) is False
        assert BlogService._is_trusted_video_host(
            "https://example.com/video.mp4"
        ) is False

    def test_is_trusted_video_host_invalid_url(self):
        """无效 URL 应返回 False。"""
        assert BlogService._is_trusted_video_host("not-a-url") is False
        assert BlogService._is_trusted_video_host("") is False

    def test_is_trusted_video_host_subdomain(self):
        """子域名也应被识别。"""
        assert BlogService._is_trusted_video_host(
            "https://player.bilibili.com/player.html"
        ) is True

    def test_validate_video_url_bilibili_valid(self):
        """有效的 Bilibili 视频链接。"""
        service = BlogService(MagicMock())
        assert service._validate_video_url(
            "https://www.bilibili.com/video/BV1GJ411x7FH"
        ) is True

    def test_validate_video_url_bilibili_invalid(self):
        """无效的 Bilibili 视频链接。"""
        service = BlogService(MagicMock())
        assert service._validate_video_url(
            "https://www.bilibili.com/"
        ) is False

    def test_validate_video_url_youtube_valid(self):
        """有效的 YouTube 视频链接。"""
        service = BlogService(MagicMock())
        assert service._validate_video_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ) is True

    def test_validate_video_url_youtube_invalid(self):
        """无效的 YouTube 视频链接。"""
        service = BlogService(MagicMock())
        assert service._validate_video_url(
            "https://www.youtube.com/"
        ) is False

    def test_validate_video_url_untrusted_domain(self):
        """不受信任域名默认返回 True（不校验格式）。"""
        service = BlogService(MagicMock())
        assert service._validate_video_url(
            "https://example.com/video"
        ) is True


# =============================================================================
# 内容校验测试
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceValidateContent:
    """内容校验测试。"""

    async def test_validate_content_no_errors(self, blog_container):
        """内容无引用时校验通过。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = []
        blog_container._mock_result.scalar_one_or_none.return_value = None

        errors = await service.validate_content("Clean content", uuid.uuid4())
        assert errors == []

    async def test_validate_content_with_missing_file_ref(self, blog_container):
        """内容引用未上传的文件应报错。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = []

        errors = await service.validate_content(
            "See image [#1]", uuid.uuid4()
        )
        assert any("图片 #'1' 未上传" in e for e in errors)

    async def test_validate_content_with_valid_file_ref(self, blog_container):
        """内容引用已上传的文件应通过。"""
        service = BlogService(blog_container)
        mock_row = MagicMock()
        mock_row.__getitem__.return_value = 1
        blog_container._mock_result.all.return_value = [mock_row]

        errors = await service.validate_content(
            "See image [#1]", uuid.uuid4()
        )
        file_errors = [e for e in errors if "未上传" in e]
        assert file_errors == []

    async def test_validate_content_with_invalid_video_url(self, blog_container):
        """内容中包含无效视频链接应报错。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = []
        blog_container._mock_result.scalar_one_or_none.return_value = None

        errors = await service.validate_content(
            "[video](https://www.bilibili.com/)", uuid.uuid4()
        )
        video_errors = [e for e in errors if "视频链接" in e]
        assert len(video_errors) > 0


# =============================================================================
# 文件引用管理测试
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceFileRefs:
    """文件引用管理和清理测试。"""

    async def test_validate_post_file_refs_no_refs(self, blog_container):
        """内容无文件引用时校验通过。"""
        service = BlogService(blog_container)
        errors = await service.validate_post_file_refs(
            "No file references here.", uuid.uuid4()
        )
        assert errors == []

    async def test_validate_post_file_refs_all_found(self, blog_container):
        """所有引用文件都存在时应通过。"""
        service = BlogService(blog_container)
        mock_row = MagicMock()
        mock_row.__getitem__.return_value = 1
        blog_container._mock_result.all.return_value = [mock_row]

        errors = await service.validate_post_file_refs(
            "Image [#1]", uuid.uuid4()
        )
        assert errors == []

    async def test_validate_post_file_refs_missing(self, blog_container):
        """引用不存在的文件应报错。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = []

        errors = await service.validate_post_file_refs(
            "Images [#1] and [#2]", uuid.uuid4()
        )
        assert len(errors) == 2

    async def test_scan_and_clean_post_files_marks_persisted(self, blog_container):
        """扫描时被引用的文件应标记为 persisted。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.file_index = 1
        mock_file.status = "temp"
        mock_file.id = uuid.uuid4()
        blog_container._mock_result.scalars.return_value.all.return_value = [
            mock_file
        ]

        post_id = uuid.uuid4()
        refs = await service.scan_and_clean_post_files(
            post_id, "Content with [#1]"
        )

        assert refs == [1]
        assert mock_file.status == "persisted"

    async def test_scan_and_clean_post_files_removes_orphans(self, blog_container):
        """扫描时未引用的文件应被删除。"""
        service = BlogService(blog_container)

        mock_file = MagicMock()
        mock_file.file_index = 99
        mock_file.status = "temp"
        mock_file.id = uuid.uuid4()
        blog_container._mock_result.scalars.return_value.all.return_value = [
            mock_file
        ]

        post_id = uuid.uuid4()
        refs = await service.scan_and_clean_post_files(
            post_id, "Content with [#1]"
        )

        assert refs == [1]
        blog_container._mock_session.execute.assert_called()

    async def test_scan_and_clean_post_files_no_files(self, blog_container):
        """帖子无临时文件时返回空。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalars.return_value.all.return_value = []

        post_id = uuid.uuid4()
        refs = await service.scan_and_clean_post_files(
            post_id, "Content with [#1]"
        )

        assert refs == [1]


# =============================================================================
# 举报功能测试
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceReports:
    """举报功能测试。"""

    async def test_create_report(self, blog_container):
        """举报帖子。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        reporter_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.status = "published"
        mock_report = MagicMock()
        mock_report.id = uuid.uuid4()
        blog_container._mock_result.scalar_one.return_value = mock_post
        blog_container._mock_session.refresh = AsyncMock(return_value=mock_report)

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.create_report(
                post_id=post_id, reporter_id=reporter_id, reason="spam"
            )

        assert result is not None
        # 举报后帖子应被标记为降流
        assert mock_post.status == "throttled"

    async def test_create_report_draft_post_not_throttled(self, blog_container):
        """草稿帖子被举报后不应降流（只有 published 帖子才降流）。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        reporter_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.status = "pending"
        mock_report = MagicMock()
        mock_report.id = uuid.uuid4()
        blog_container._mock_result.scalar_one.return_value = mock_post
        blog_container._mock_session.refresh = AsyncMock(return_value=mock_report)

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.create_report(
                post_id=post_id, reporter_id=reporter_id, reason="spam"
            )

        assert result is not None
        # pending 帖子不应被降流
        assert mock_post.status == "pending"


# =============================================================================
# 收藏功能测试
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceFavorites:
    """收藏功能测试。"""

    async def test_add_favorite(self, blog_container):
        """收藏帖子。"""
        service = BlogService(blog_container)
        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_post = MagicMock()

        blog_container._mock_result.scalar_one_or_none.return_value = None

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.add_favorite(post_id=post_id, user_id=user_id)

        assert result["action"] == "favorited"

    async def test_add_favorite_already_favorited(self, blog_container):
        """重复收藏返回已收藏状态。"""
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
        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_favorite = MagicMock()

        blog_container._mock_result.scalar_one_or_none.return_value = mock_favorite

        result = await service.remove_favorite(post_id=post_id, user_id=user_id)
        assert result["action"] == "unfavorited"

    async def test_remove_favorite_not_favorited(self, blog_container):
        """取消未收藏的帖子应返回 unfavorited。"""
        service = BlogService(blog_container)
        post_id = uuid.uuid4()
        user_id = uuid.uuid4()

        blog_container._mock_result.scalar_one_or_none.return_value = None

        result = await service.remove_favorite(post_id=post_id, user_id=user_id)
        assert result["action"] == "unfavorited"

    async def test_check_favorite_true(self, blog_container):
        """检查已收藏状态。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = MagicMock()

        result = await service.check_favorite(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
        assert result is True

    async def test_check_favorite_false(self, blog_container):
        """检查未收藏状态。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None

        result = await service.check_favorite(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
        assert result is False

    async def test_list_favorites_empty(self, blog_container):
        """空收藏列表。"""
        service = BlogService(blog_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_favorites(user_id=uuid.uuid4())
        assert result["total"] == 0
        assert result["items"] == []


# =============================================================================
# 统计和趋势测试
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceStats:
    """统计和趋势测试。"""

    async def test_get_stats(self, blog_container):
        """获取博客统计。"""
        service = BlogService(blog_container)

        # 6 个 COUNT 查询 + 1 个今日查询
        count_values = [10, 7, 3, 100, 20, 50, 2]
        results = []
        for val in count_values:
            r = MagicMock()
            r.scalar_one.return_value = val
            results.append(r)

        blog_container._mock_session.execute = AsyncMock(side_effect=results)

        stats = await service.get_stats()

        assert stats["total_posts"] == 10
        assert stats["published_posts"] == 7
        assert stats["pending_posts"] == 3
        assert stats["total_views"] == 100
        assert stats["total_comments"] == 20
        assert stats["total_likes"] == 50
        assert stats["today_posts"] == 2

    async def test_get_hot_posts_empty(self, blog_container):
        """热门帖子列表为空。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalars.return_value.all.return_value = []

        result = await service.get_hot_posts(limit=10)
        assert result == []

    async def test_get_hot_posts_returns_sorted(self, blog_container):
        """热门帖子按浏览量降序。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.id = uuid.uuid4()
        mock_post.author_id = uuid.uuid4()
        mock_post.title = "Hot Post"
        mock_post.views = 100
        mock_post.created_at = None

        blog_container._mock_result.scalars.return_value.all.return_value = [
            mock_post
        ]
        # author + likes + comments 查询返回空
        blog_container._mock_result.all.return_value = []

        result = await service.get_hot_posts(limit=10)
        assert len(result) == 1
        assert result[0]["title"] == "Hot Post"
        assert result[0]["views"] == 100

    async def test_get_daily_trend(self, blog_container):
        """获取每日趋势。"""
        service = BlogService(blog_container)

        # posts, views, comments 三个查询均返回空
        blog_container._mock_result.all.return_value = []

        result = await service.get_daily_trend(days=7)

        assert result["days"] == 7
        assert len(result["trend"]) == 7
        for day in result["trend"]:
            assert "date" in day
            assert "views" in day
            assert "posts" in day
            assert "comments" in day


# =============================================================================
# 帖子查询测试
# =============================================================================


@pytest.mark.asyncio
class TestBlogServicePostQueries:
    """帖子查询功能测试。"""

    async def test_list_my_posts_empty(self, blog_container):
        """我的帖子列表为空。"""
        service = BlogService(blog_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_my_posts(author_id=uuid.uuid4())
        assert result["total"] == 0
        assert result["items"] == []

    async def test_get_post_detail_by_id_not_found(self, blog_container):
        """按 ID 获取不存在的帖子。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await service.get_post_detail_by_id(post_id=uuid.uuid4())
        assert "帖子不存在" in str(excinfo.value)

    async def test_get_post_detail_by_id_permission_denied(self, blog_container):
        """按 ID 获取帖子但权限不足。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.required_level = 0
        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with pytest.raises(Exception) as excinfo:
            await service.get_post_detail_by_id(
                post_id=uuid.uuid4(), user_level=2
            )
        assert "无权查看此帖子" in str(excinfo.value)

    async def test_get_post_detail_by_id_success(self, blog_container):
        """按 ID 成功获取帖子详情。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.id = post_id
        mock_post.author_id = uuid.uuid4()
        mock_post.required_level = 5
        mock_post.status = "published"
        mock_post.title = "Test Post"
        mock_post.content = "Content"
        mock_post.views = 0
        mock_post.like_count = 0
        mock_post.comment_count = 0
        mock_post.is_pinned = False
        mock_post.is_featured = False
        mock_post.slug = "test-post"
        mock_post.created_at = None
        mock_post.updated_at = None
        mock_post.published_at = None
        mock_post.paragraph_ids = None
        mock_post.cover_url = None
        mock_post.introduction = None
        mock_post.subtitles = None
        mock_post.category_id = None

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_result.all.return_value = []

        with patch.object(service, "get_post_tags", return_value=[]):
            result = await service.get_post_detail_by_id(
                post_id=post_id, user_level=5
            )

        assert result["title"] == "Test Post"

    async def test_get_posts_by_tag_not_found(self, blog_container):
        """按不存在的标签查询帖子。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await service.get_posts_by_tag(tag_name="nonexistent")
        assert "标签不存在" in str(excinfo.value)

    async def test_get_posts_by_tag_empty(self, blog_container):
        """按标签查询但无帖子。"""
        service = BlogService(blog_container)

        mock_tag = MagicMock()
        mock_tag.id = uuid.uuid4()
        mock_tag.name = "python"
        mock_tag.color = None
        mock_tag.created_at = None

        blog_container._mock_result.scalar_one_or_none.return_value = mock_tag
        # 两个查询：count + data
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        # 第二次调用 get_tag_by_name 需要返回 mock_tag
        with patch.object(service, "get_tag_by_name", return_value=mock_tag):
            result = await service.get_posts_by_tag(tag_name="python")

        assert result["total"] == 0
        assert result["items"] == []

    async def test_get_like_status_not_liked(self, blog_container):
        """未点赞的帖子。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.id = uuid.uuid4()

        # 查帖子 + 查点赞记录 + 查点赞数
        like_none_result = MagicMock()
        like_none_result.scalar_one_or_none.return_value = None
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[MagicMock(), like_none_result, count_result]
        )
        # 第一次 execute 用于 get_post_by_id
        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        result = await service.get_like_status(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )

        assert result["liked"] is False
        assert result["count"] == 0

    async def test_get_like_status_liked(self, blog_container):
        """已点赞的帖子。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.id = uuid.uuid4()
        mock_like = MagicMock()

        # 查帖子 + 查点赞记录 + 查点赞数
        like_found_result = MagicMock()
        like_found_result.scalar_one_or_none.return_value = mock_like
        count_result = MagicMock()
        count_result.scalar_one.return_value = 5

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[MagicMock(), like_found_result, count_result]
        )
        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        result = await service.get_like_status(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )

        assert result["liked"] is True
        assert result["count"] == 5

    async def test_list_pending_posts_empty(self, blog_container):
        """待审核列表为空。"""
        service = BlogService(blog_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_pending_posts()
        assert result["total"] == 0
        assert result["items"] == []

    async def test_remove_tag_from_post_tag_not_found(self, blog_container):
        """移除不存在的标签。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await service.remove_tag_from_post(
                post_id=uuid.uuid4(), tag_name="nonexistent", user_id=uuid.uuid4()
            )
        assert "标签不存在" in str(excinfo.value)

    async def test_remove_tag_from_post_not_on_post(self, blog_container):
        """移除帖子不存在的标签关联。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_tag = MagicMock()
        mock_tag.id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.id = post_id
        mock_post.author_id = user_id

        blog_container._mock_result.scalar_one_or_none.side_effect = [
            mock_post,  # 查询帖子（remove_tag_from_post 内部）
            None,  # BlogPostTag not found
        ]

        with patch.object(service, "get_tag_by_name", return_value=mock_tag):
            with pytest.raises(Exception) as excinfo:
                await service.remove_tag_from_post(
                    post_id=post_id, tag_name="python", user_id=user_id
                )
        assert "帖子无此标签" in str(excinfo.value)


# =============================================================================
# 段落评论测试
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceParagraphComments:
    """段落级别评论测试。"""

    async def test_get_paragraph_comments_empty(self, blog_container):
        """段落评论列表为空。"""
        service = BlogService(blog_container)

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
                post_id=uuid.uuid4(), paragraph_pid="abc_001"
            )

        assert result["total"] == 0
        assert result["items"] == []

    async def test_create_paragraph_comment(self, blog_container):
        """创建段落评论。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = uuid.uuid4()
        blog_container._mock_session.refresh = AsyncMock(return_value=mock_comment)

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.create_paragraph_comment(
                post_id=post_id,
                paragraph_pid="abc_001",
                author_id=author_id,
                content="Paragraph comment",
            )

        assert result is not None