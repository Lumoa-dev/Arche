"""博客插件 —— 补充测试：覆盖 BlogService 中尚未测试的方法。

测试策略：
- 静态/同步方法直接调用，无需 mock
- 异步方法使用 _make_blog_container() 的 mock 模式
- 遵循现有测试文件的风格和约定
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.blog.models import BlogFavorite, BlogReport
from backend.plugins.blog.services import BlogService


# =============================================================================
# 测试辅助：复用 test_blog.py 中的 _make_blog_container
# =============================================================================


def _make_blog_container():
    """创建支持 BlogService 的轻量 fake_container。"""
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
# TestVideoUrlValidation — 视频 URL 验证（静态方法，同步测试）
# =============================================================================


class TestVideoUrlValidation:
    """视频 URL 验证测试（静态方法，无需实例化）。"""

    # --- _is_trusted_video_host ---

    def test_is_trusted_video_host_bilibili(self):
        """bilibili.com 域名应被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://www.bilibili.com/video/BV1GJ411x7"
        ) is True

    def test_is_trusted_video_host_b23tv(self):
        """b23.tv 短链接应被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://b23.tv/BV1GJ411x7"
        ) is True

    def test_is_trusted_video_host_youtube(self):
        """youtube.com 域名应被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ) is True

    def test_is_trusted_video_host_untrusted(self):
        """非受信任域名应返回 False。"""
        assert BlogService._is_trusted_video_host(
            "https://vimeo.com/123456"
        ) is False

    def test_is_trusted_video_host_invalid_url(self):
        """无效 URL 应返回 False。"""
        assert BlogService._is_trusted_video_host("not-a-url") is False

    def test_is_trusted_video_host_subdomain(self):
        """子域名也应被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://subdomain.bilibili.com/video/123"
        ) is True

    # --- _validate_video_url ---

    def test_validate_video_url_bilibili_bv(self):
        """bilibili BV 视频 URL 应验证通过。"""
        service = BlogService(_make_blog_container())
        assert service._validate_video_url(
            "https://www.bilibili.com/video/BV1GJ411x7"
        ) is True

    def test_validate_video_url_bilibili_video(self):
        """bilibili /video/ 路径 URL 应验证通过。"""
        service = BlogService(_make_blog_container())
        assert service._validate_video_url(
            "https://www.bilibili.com/video/av123456"
        ) is True

    def test_validate_video_url_youtube_watch(self):
        """youtube watch?v= 格式应验证通过。"""
        service = BlogService(_make_blog_container())
        assert service._validate_video_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ) is True

    def test_validate_video_url_youtube_embed(self):
        """youtube embed/ 格式应验证通过。"""
        service = BlogService(_make_blog_container())
        assert service._validate_video_url(
            "https://www.youtube.com/embed/dQw4w9WgXcQ"
        ) is True

    def test_validate_video_url_youtube_shorts(self):
        """youtube shorts/ 格式应验证通过。"""
        service = BlogService(_make_blog_container())
        assert service._validate_video_url(
            "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        ) is True

    def test_validate_video_url_invalid(self):
        """缺少视频 ID 的 bilibili URL 应验证失败。"""
        service = BlogService(_make_blog_container())
        assert service._validate_video_url(
            "https://www.bilibili.com/"
        ) is False

    def test_validate_video_url_untrusted_host(self):
        """非受信任主机的 URL 应返回 True（透传通过）。"""
        service = BlogService(_make_blog_container())
        assert service._validate_video_url(
            "https://vimeo.com/123456"
        ) is True


# =============================================================================
# TestExtractTitle — 标题提取（同步方法）
# =============================================================================


class TestExtractTitle:
    """标题提取测试。"""

    def test_extract_title_with_heading(self):
        """从 Markdown 的 # Heading 中提取标题。"""
        service = BlogService(_make_blog_container())
        text = "# 我的第一篇博客文章\n\n这是正文内容。"
        title, body = service._extract_title(text, "import.md")
        assert title == "我的第一篇博客文章"
        assert "这是正文内容" in body

    def test_extract_title_without_heading(self):
        """无 heading 时回退到文件名。"""
        service = BlogService(_make_blog_container())
        text = "这是正文内容，没有标题行。"
        title, body = service._extract_title(text, "我的文档.md")
        assert title == "我的文档"
        assert body == "这是正文内容，没有标题行。"

    def test_extract_title_removes_heading_from_body(self):
        """标题行应从 body 中移除。"""
        service = BlogService(_make_blog_container())
        text = "# 标题\n\n第一段\n\n# 二级标题\n\n第二段"
        title, body = service._extract_title(text, "test.md")
        assert title == "标题"
        # 第一个 # Heading 行应被移除，但后续的 # 保留
        assert "二级标题" in body
        assert "第一段" in body

    def test_extract_html_body(self):
        """HTML body 提取并转换为简单 Markdown。"""
        service = BlogService(_make_blog_container())
        html = (
            "<html><body>"
            "<h1>主标题</h1>"
            "<p>第一段</p>"
            "<br/>"
            "<h2>副标题</h2>"
            "<p>第二段</p>"
            "</body></html>"
        )
        result = service._extract_html_body(html)
        assert "# 主标题" in result
        assert "第一段" in result
        assert "## 副标题" in result
        assert "第二段" in result


# =============================================================================
# TestValidateContent — 内容校验（异步，使用 blog_container mock）
# =============================================================================


@pytest.mark.asyncio
class TestValidateContent:
    """内容校验测试。"""

    async def test_validate_content_no_errors(self, blog_container):
        """干净的内容应返回空错误列表。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = []

        content = "这是一段干净的正文内容，没有文件引用。"
        errors = await service.validate_content(content, owner_id=uuid.uuid4())
        assert errors == []

    async def test_validate_content_file_refs_missing(self, blog_container):
        """缺失文件引用的 [#N] 应返回错误。"""
        service = BlogService(blog_container)
        # 第一次 execute 查询 PostFile，返回空列表（无已上传文件）
        blog_container._mock_result.all.return_value = []

        content = "这是一段正文，引用了图片 [#1] 和 [#2]。"
        errors = await service.validate_content(content, owner_id=uuid.uuid4())
        # 应返回两个错误：图片 #1 和 #2 未上传
        assert len(errors) == 2
        assert all("未上传" in err for err in errors)

    async def test_validate_content_invalid_video_url(self, blog_container):
        """无效的视频链接应返回错误。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = []

        content = "视频链接：[点击观看](https://www.bilibili.com/)"
        errors = await service.validate_content(content, owner_id=uuid.uuid4())
        assert len(errors) == 1
        assert "格式无效" in errors[0]

    async def test_validate_content_valid_video_url(self, blog_container):
        """有效的视频链接应通过校验。"""
        service = BlogService(blog_container)
        blog_container._mock_result.all.return_value = []

        content = "视频链接：[点击观看](https://www.bilibili.com/video/BV1GJ411x7)"
        errors = await service.validate_content(content, owner_id=uuid.uuid4())
        assert errors == []


# =============================================================================
# TestFavoriteOperations — 收藏操作（异步，使用 blog_container mock）
# =============================================================================


@pytest.mark.asyncio
class TestFavoriteOperations:
    """收藏操作测试。"""

    async def test_add_favorite(self, blog_container):
        """add_favorite() 应创建收藏记录并返回 favorited。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_favorite = MagicMock()
        mock_favorite.id = uuid.uuid4()

        blog_container._mock_result.scalar_one_or_none.return_value = None
        blog_container._mock_session.refresh = AsyncMock(return_value=mock_favorite)

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.add_favorite(post_id=post_id, user_id=user_id)

        assert result["action"] == "favorited"
        assert "favorite_id" in result

    async def test_add_favorite_already_favorited(self, blog_container):
        """已收藏时，add_favorite() 应返回 already_favorited。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_post = MagicMock()
        existing_favorite = MagicMock()
        existing_favorite.id = uuid.uuid4()

        blog_container._mock_result.scalar_one_or_none.return_value = existing_favorite

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.add_favorite(post_id=post_id, user_id=user_id)

        assert result["action"] == "already_favorited"
        assert "favorite_id" in result

    async def test_remove_favorite(self, blog_container):
        """remove_favorite() 应删除收藏记录。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        existing_favorite = MagicMock()

        blog_container._mock_result.scalar_one_or_none.return_value = existing_favorite

        result = await service.remove_favorite(post_id=post_id, user_id=user_id)
        assert result["action"] == "unfavorited"
        blog_container._mock_session.delete.assert_called_once_with(existing_favorite)

    async def test_remove_favorite_nonexistent(self, blog_container):
        """收藏不存在时，remove_favorite() 也应返回 unfavorited。"""
        service = BlogService(blog_container)

        blog_container._mock_result.scalar_one_or_none.return_value = None

        result = await service.remove_favorite(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
        assert result["action"] == "unfavorited"

    async def test_check_favorite_true(self, blog_container):
        """已收藏时，check_favorite() 返回 True。"""
        service = BlogService(blog_container)

        existing_favorite = MagicMock()
        blog_container._mock_result.scalar_one_or_none.return_value = existing_favorite

        result = await service.check_favorite(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
        assert result is True

    async def test_check_favorite_false(self, blog_container):
        """未收藏时，check_favorite() 返回 False。"""
        service = BlogService(blog_container)

        blog_container._mock_result.scalar_one_or_none.return_value = None

        result = await service.check_favorite(
            post_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
        assert result is False


# =============================================================================
# TestReportOperations — 举报操作（异步，使用 blog_container mock）
# =============================================================================


@pytest.mark.asyncio
class TestReportOperations:
    """举报操作测试。"""

    async def test_create_report(self, blog_container):
        """create_report() 应创建举报记录并将 published 帖子降流为 throttled。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        reporter_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.status = "published"

        # 第一个 execute 返回 mock_post（get_post_by_id 中的查询）
        # 第二个 execute 中的 scalar_one 返回 mock_post（create_report 中查询 post）
        # 第三个 execute 的 scalar_one_or_none 用于其他
        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        blog_container._mock_result.scalar_one.return_value = mock_post

        mock_report = MagicMock()
        mock_report.id = uuid.uuid4()
        mock_report.post_id = post_id
        mock_report.reporter_id = reporter_id
        mock_report.reason = "垃圾广告"
        blog_container._mock_session.refresh = AsyncMock(return_value=mock_report)

        result = await service.create_report(
            post_id=post_id, reporter_id=reporter_id, reason="垃圾广告"
        )

        # 验证帖子被降流
        assert mock_post.status == "throttled"
        # 验证返回举报字典
        assert result["reason"] == "垃圾广告"
        assert result["post_id"] == str(post_id)
        assert result["reporter_id"] == str(reporter_id)


# =============================================================================
# TestStatsOperations — 统计操作（异步，使用 blog_container mock）
# =============================================================================


@pytest.mark.asyncio
class TestStatsOperations:
    """统计操作测试。"""

    async def test_get_stats_returns_summary(self, blog_container):
        """get_stats() 应返回包含所有字段的统计摘要字典。"""
        service = BlogService(blog_container)

        # get_stats 执行 7 次 execute 查询：
        # total_posts, published_posts, pending_posts, total_views, total_comments, total_likes, today_posts
        scalar_results = [10, 7, 2, 500, 30, 100, 1]
        scalar_one_calls = 0

        def scalar_one_side_effect(*args, **kwargs):
            nonlocal scalar_one_calls
            val = scalar_results[scalar_one_calls % len(scalar_results)]
            scalar_one_calls += 1
            return val

        blog_container._mock_result.scalar_one = MagicMock(
            side_effect=scalar_one_side_effect
        )

        result = await service.get_stats()

        assert result["total_posts"] == 10
        assert result["published_posts"] == 7
        assert result["pending_posts"] == 2
        assert result["total_views"] == 500
        assert result["total_comments"] == 30
        assert result["total_likes"] == 100
        assert result["today_posts"] == 1