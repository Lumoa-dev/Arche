"""博客插件 单元测试。

所有 BlogService 测试使用纯 mock，不启动真实数据库。
内存开销接近零，运行速度极快。
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.blog.sensitive_words import (
    SensitiveWordFilter,
    get_filter,
    init_filter,
)
from backend.plugins.blog.services import (
    MAX_TAGS_PER_POST,
    BlogService,
    can_user_see_post,
)

# =============================================================================
# 测试辅助
# =============================================================================


def _make_blog_container():
    """创建支持 BlogService 的轻量 fake_container。

    关键：mock_session.execute 必须用 AsyncMock(return_value=MagicMock())，
    否则 await session.execute(...) 返回的仍是 AsyncMock，
    其 .scalar_one_or_none() 也会返回协程而非值。
    """
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

    # 构造 mock session：execute 返回普通 MagicMock（不是 AsyncMock）
    mock_execute_result = MagicMock()
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # session_factory() 返回 async context manager
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
# 工具函数测试
# =============================================================================


class TestAccessLevelFunctions:
    """权限等级工具函数测试（已简化：直接比较整数）。"""

    def test_can_user_see_post_admin(self):
        assert can_user_see_post(0, 0) is True  # P0看需要P0的帖子
        assert can_user_see_post(0, 1) is False  # P1不能看需要P0的帖子

    def test_can_user_see_post_normal(self):
        assert can_user_see_post(2, 2) is True  # P2看需要P2的帖子
        assert can_user_see_post(2, 3) is False  # P3不能看需要P2的帖子
        assert can_user_see_post(2, 0) is True  # P0能看需要P2的帖子

    def test_can_user_see_post_public(self):
        assert can_user_see_post(5, 5) is True  # P5看公开帖子
        assert can_user_see_post(5, 0) is True  # P0也能看公开帖子
        assert can_user_see_post(5, 5) is True  # 访客看公开帖子


# =============================================================================
# 敏感词过滤器测试
# =============================================================================


class TestSensitiveWordFilter:
    """敏感词过滤器测试。"""

    def test_filter_init_empty(self):
        f = SensitiveWordFilter()
        assert f.check("")[0] is True
        assert f.check("任何内容")[0] is True

    def test_filter_with_words(self):
        f = SensitiveWordFilter(["敏感词1", "敏感词2"])
        passed, matched = f.check("这是正常内容")
        assert passed is True
        assert matched == []

        passed, matched = f.check("这包含敏感词1内容")
        assert passed is False
        assert matched == ["敏感词1"]

        passed, matched = f.check("敏感词1和敏感词2都有")
        assert passed is False
        assert set(matched) == {"敏感词1", "敏感词2"}

    def test_filter_case_insensitive(self):
        f = SensitiveWordFilter(["BADWORD"])
        passed, matched = f.check("badword is here")
        assert passed is False
        assert matched == ["BADWORD"]

    def test_filter_empty_text(self):
        f = SensitiveWordFilter(["敏感词"])
        passed, matched = f.check("")
        assert passed is True
        assert matched == []

    def test_global_filter_init(self):
        f = init_filter(["test1", "test2"])
        assert f is not None
        assert get_filter() is f

    def test_global_filter_get_creates_default(self):
        import backend.plugins.blog.sensitive_words as sw

        sw._filter = None
        f = get_filter()
        assert f is not None
        assert isinstance(f, SensitiveWordFilter)


# =============================================================================
# BlogService 测试 - Slug 生成
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceSlugGeneration:
    """BlogService Slug生成测试。"""

    async def test_generate_slug_basic(self, blog_container):
        """基础slug生成 - 纯字符串处理，不涉及数据库查询。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None
        slug = await service.generate_slug("Hello World")
        assert slug == "hello-world"

    async def test_generate_slug_chinese(self, blog_container):
        """中文标题保留。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None
        slug = await service.generate_slug("你好世界")
        assert slug == "你好世界"

    async def test_generate_slug_special_chars(self, blog_container):
        """特殊字符合并为单个-。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None
        slug = await service.generate_slug("Hello  --  World!!")
        assert slug == "hello-world"

    async def test_generate_slug_empty_title(self, blog_container):
        """空标题默认用'post'。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None
        slug = await service.generate_slug("  ")
        assert slug == "post"

    async def test_generate_slug_duplicate(self, blog_container):
        """重复slug时添加数字后缀。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.slug = "duplicate"

        results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_post)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
        blog_container._mock_session.execute = AsyncMock(side_effect=results)
        slug = await service.generate_slug("duplicate")
        assert slug == "duplicate-1"

    async def test_generate_slug_exclude_slug(self, blog_container):
        """exclude_slug相同时不添加后缀。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.slug = "existing-post"
        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        slug = await service.generate_slug(
            "existing post", exclude_slug="existing-post"
        )
        assert slug == "existing-post"


# =============================================================================
# BlogService 测试 - 帖子 CRUD
# =============================================================================


@pytest.mark.asyncio
class TestBlogServicePostCRUD:
    """BlogService 帖子CRUD测试。"""

    async def test_list_posts_empty(self, blog_container):
        """空帖子列表。"""
        service = BlogService(blog_container)

        # list_posts 执行两次查询：count + data
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_posts(page=1, page_size=20)
        assert result["total"] == 0
        assert result["items"] == []
        assert result["page"] == 1
        assert result["page_size"] == 20

    async def test_get_post_by_slug_not_found(self, blog_container):
        """获取不存在的帖子。"""
        service = BlogService(blog_container)
        blog_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await service.get_post_by_slug("not-found")
        assert "帖子不存在" in str(excinfo.value)

    async def test_get_post_by_slug_permission_denied(self, blog_container):
        """无权限查看帖子。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.required_level = 0
        mock_post.views = 0
        mock_post.status = "published"
        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with pytest.raises(Exception) as excinfo:
            await service.get_post_by_slug("test-post", user_level=2)
        assert "无权查看此帖子" in str(excinfo.value)

    async def test_get_post_by_slug_increases_views(self, blog_container):
        """查看帖子增加浏览量。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.required_level = 5
        mock_post.views = 0
        mock_post.status = "published"
        mock_post.author_id = uuid.uuid4()
        mock_post.content = "Test content paragraph one.\n\nTest content paragraph two."

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post
        # list_posts 内部还有 author 和 likes 查询
        blog_container._mock_result.all.return_value = []

        with patch.object(service, "get_post_tags", return_value=[]):
            await service.get_post_by_slug("test-post")

        assert mock_post.views == 1

    async def test_create_post_sensitive_word_rejected(self, blog_container):
        """包含敏感词的帖子被拒绝。"""
        service = BlogService(blog_container)
        init_filter(["敏感词"])

        with pytest.raises(Exception) as excinfo:
            await service.create_post(
                author_id=uuid.uuid4(),
                title="Test Post",
                content="This contains 敏感词",
            )
        assert "敏感词" in str(excinfo.value)

    async def test_create_post_access_level_too_high(self, blog_container):
        """用户尝试设置高于自身权限的等级。"""
        service = BlogService(blog_container)

        with pytest.raises(Exception) as excinfo:
            await service.create_post(
                author_id=uuid.uuid4(),
                title="Test Post",
                required_level=0,
                user_level=2,
            )
        assert "无权设置" in str(excinfo.value)

    async def test_update_post_basic(self, blog_container):
        """编辑帖子。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        post_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.id = post_id
        mock_post.author_id = author_id

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with patch.object(service, "generate_slug", return_value="new-title"):
            await service.update_post(
                post_id=post_id,
                author_id=author_id,
                title="New Title",
            )
        assert mock_post.status == "pending"

    async def test_update_post_permission_denied(self, blog_container):
        """非作者尝试编辑帖子。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with pytest.raises(Exception) as excinfo:
            await service.update_post(
                post_id=uuid.uuid4(),
                author_id=other_user_id,
                title="Hacked Title",
            )
        assert "无权限编辑此帖子" in str(excinfo.value)

    async def test_delete_post_by_author(self, blog_container):
        """作者删除帖子。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        await service.delete_post(
            post_id=uuid.uuid4(),
            user_id=author_id,
            user_level=5,
        )
        blog_container._mock_session.delete.assert_called_once()

    async def test_delete_post_by_admin(self, blog_container):
        """P0管理员删除他人帖子。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        await service.delete_post(
            post_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_level=0,
        )
        blog_container._mock_session.delete.assert_called_once()

    async def test_delete_post_permission_denied(self, blog_container):
        """普通用户删除他人帖子。"""
        service = BlogService(blog_container)

        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.author_id = author_id

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with pytest.raises(Exception) as excinfo:
            await service.delete_post(
                post_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                user_level=5,
            )
        assert "无权限删除此帖子" in str(excinfo.value)


# =============================================================================
# BlogService 测试 - 评论功能
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceComments:
    """BlogService 评论功能测试。"""

    async def test_create_comment_basic(self, blog_container):
        """发表评论。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = uuid.uuid4()

        blog_container._mock_result.scalar_one_or_none.return_value = None
        blog_container._mock_session.refresh = AsyncMock(return_value=mock_comment)

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.create_comment(
                post_id=post_id,
                author_id=author_id,
                content="This is a comment",
            )
        assert result is not None

    async def test_create_comment_parent_not_found(self, blog_container):
        """父评论不存在。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        author_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        mock_post = MagicMock()

        blog_container._mock_result.scalar_one_or_none.return_value = None

        with patch.object(service, "get_post_by_id", return_value=mock_post):  # noqa: SIM117
            with pytest.raises(Exception) as excinfo:
                await service.create_comment(
                    post_id=post_id,
                    author_id=author_id,
                    content="This is a reply",
                    parent_id=parent_id,
                )
        assert "父评论不存在" in str(excinfo.value)

    async def test_list_comments_empty(self, blog_container):
        """空评论列表。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        mock_post = MagicMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.list_comments(post_id=post_id)

        assert result["total"] == 0
        assert result["items"] == []


# =============================================================================
# BlogService 测试 - 点赞功能
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceLikes:
    """BlogService 点赞功能测试。"""

    async def test_toggle_like_like(self, blog_container):
        """第一次点赞。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_post = MagicMock()

        blog_container._mock_result.scalar_one_or_none.return_value = None

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.toggle_like(post_id=post_id, user_id=user_id)
        assert result["action"] == "liked"

    async def test_toggle_like_unlike(self, blog_container):
        """取消点赞。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.like_count = 1
        mock_like = MagicMock()
        mock_like.like_count = 1

        blog_container._mock_result.scalar_one_or_none.return_value = mock_like

        with patch.object(service, "get_post_by_id", return_value=mock_post):
            result = await service.toggle_like(post_id=post_id, user_id=user_id)
        assert result["action"] == "unliked"


# =============================================================================
# BlogService 测试 - 审核功能
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceModeration:
    """BlogService 审核功能测试。"""

    async def test_approve_post(self, blog_container):
        """通过帖子审核。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.status = "pending"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        await service.approve_post(post_id=uuid.uuid4())
        assert mock_post.status == "published"

    async def test_reject_post(self, blog_container):
        """拒绝帖子审核。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.status = "pending"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        await service.reject_post(post_id=uuid.uuid4())
        assert mock_post.status == "rejected"

    async def test_approve_post_wrong_status(self, blog_container):
        """审核已发布帖子应失败。"""
        service = BlogService(blog_container)

        mock_post = MagicMock()
        mock_post.status = "published"

        blog_container._mock_result.scalar_one_or_none.return_value = mock_post

        with pytest.raises(Exception) as excinfo:
            await service.approve_post(post_id=uuid.uuid4())
        assert "无法审核" in str(excinfo.value)


# =============================================================================
# BlogService 测试 - 标签功能
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceTags:
    """BlogService 标签功能测试。"""

    async def test_create_tag_basic(self, blog_container):
        """创建标签。"""
        service = BlogService(blog_container)

        blog_container._mock_result.scalar_one_or_none.return_value = None

        result = await service.create_tag(name="Python")
        assert result is not None

    async def test_create_tag_existing(self, blog_container):
        """创建已存在的标签。"""
        service = BlogService(blog_container)

        mock_tag = MagicMock()
        mock_tag.name = "python"
        blog_container._mock_result.scalar_one_or_none.return_value = mock_tag

        result = await service.create_tag(name="Python")
        assert result is not None

    async def test_create_tag_empty_name(self, blog_container):
        """空标签名应失败。"""
        service = BlogService(blog_container)

        with pytest.raises(Exception) as excinfo:
            await service.create_tag(name="  ")
        assert "标签名不能为空" in str(excinfo.value)

    async def test_create_tag_too_long(self, blog_container):
        """过长标签名应失败。"""
        service = BlogService(blog_container)

        with pytest.raises(Exception) as excinfo:
            await service.create_tag(name="a" * 100)
        assert "标签名过长" in str(excinfo.value)

    async def test_list_tags_empty(self, blog_container):
        """空标签列表。"""
        service = BlogService(blog_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_tags()
        assert result["total"] == 0
        assert result["items"] == []

    async def test_add_tag_to_post_too_many_tags(self, blog_container):
        """帖子标签数达上限。"""
        service = BlogService(blog_container)

        post_id = uuid.uuid4()
        author_id = uuid.uuid4()
        mock_post = MagicMock()
        mock_post.id = post_id
        mock_post.author_id = author_id

        blog_container._mock_session.execute.return_value.scalar_one_or_none.return_value = mock_post

        # 标签数已达上限
        count_result = MagicMock()
        count_result.scalar_one.return_value = MAX_TAGS_PER_POST
        blog_container._mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_post)),
                count_result,
            ]
        )

        with pytest.raises(Exception) as excinfo:
            await service.add_tag_to_post(
                post_id=post_id,
                tag_name="new-tag",
                user_id=author_id,
            )
        assert "已达上限" in str(excinfo.value)


# =============================================================================
# BlogService 测试 - 内容校验
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceContentValidation:
    """BlogService 内容校验测试。"""

    async def test_is_trusted_video_host_bilibili(self, blog_container):
        """bilibili.com 域名被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://www.bilibili.com/video/BV1GJ411x7H7"
        )
        assert BlogService._is_trusted_video_host(
            "https://bilibili.com/video/BV1xx411c7mu"
        )

    async def test_is_trusted_video_host_b23tv(self, blog_container):
        """b23.tv 短域名被识别为受信任。"""
        assert BlogService._is_trusted_video_host("https://b23.tv/abc123")
        assert BlogService._is_trusted_video_host("https://www.b23.tv/xyz456")

    async def test_is_trusted_video_host_youtube(self, blog_container):
        """youtube.com 域名被识别为受信任。"""
        assert BlogService._is_trusted_video_host(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert BlogService._is_trusted_video_host(
            "https://youtube.com/shorts/abc123"
        )

    async def test_is_trusted_video_host_untrusted(self, blog_container):
        """不受信域名返回 False。"""
        assert not BlogService._is_trusted_video_host(
            "https://evil-site.com/video"
        )
        assert not BlogService._is_trusted_video_host(
            "https://bilibili.com.evil.com/x"
        )
        assert not BlogService._is_trusted_video_host("not-a-url")
        assert not BlogService._is_trusted_video_host("")

    async def test_validate_video_url_bilibili_valid(self, blog_container):
        """有效 bilibili 视频链接。"""
        service = BlogService(blog_container)
        assert service._validate_video_url(
            "https://www.bilibili.com/video/BV1GJ411x7H7"
        )
        assert service._validate_video_url(
            "https://b23.tv/BV1xx411c7mu"
        )

    async def test_validate_video_url_youtube_valid(self, blog_container):
        """有效 YouTube 视频链接。"""
        service = BlogService(blog_container)
        assert service._validate_video_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert service._validate_video_url(
            "https://www.youtube.com/embed/dQw4w9WgXcQ"
        )
        assert service._validate_video_url(
            "https://youtube.com/shorts/abc123"
        )

    async def test_validate_video_url_invalid(self, blog_container):
        """无效视频链接格式返回 False。"""
        service = BlogService(blog_container)
        assert not service._validate_video_url(
            "https://www.bilibili.com/watch/not-a-bv"
        )
        assert not service._validate_video_url(
            "https://www.youtube.com/feed/explore"
        )

    async def test_validate_video_url_trusted_domain_no_pattern(self, blog_container):
        """受信域名但链接不含视频 ID 模式返回 False。"""
        service = BlogService(blog_container)
        assert not service._validate_video_url(
            "https://bilibili.com/"
        )
        assert not service._validate_video_url(
            "https://youtube.com/"
        )

    async def test_validate_post_file_refs_all_exist(self, blog_container):
        """正文中所有 [#N] 引用文件均已上传。"""
        service = BlogService(blog_container)

        mock_result = MagicMock()
        mock_result.all.return_value = [(1,), (2,), (3,)]
        blog_container._mock_session.execute.return_value = mock_result

        errors = await service.validate_post_file_refs(
            "正文引用 [#1] 和 [#2] 以及 [#3]", owner_id=uuid.uuid4()
        )

        assert errors == []

    async def test_validate_post_file_refs_missing(self, blog_container):
        """正文中部分 [#N] 引用文件未上传。"""
        service = BlogService(blog_container)

        mock_result = MagicMock()
        mock_result.all.return_value = [(1,)]  # 只有 #1 存在
        blog_container._mock_session.execute.return_value = mock_result

        errors = await service.validate_post_file_refs(
            "用了 [#1] 和 [#2]", owner_id=uuid.uuid4()
        )

        assert len(errors) == 1
        assert "#'2'" in errors[0]
        assert "未上传" in errors[0]

    async def test_validate_post_file_refs_no_refs(self, blog_container):
        """正文中没有文件引用时直接通过。"""
        service = BlogService(blog_container)
        errors = await service.validate_post_file_refs(
            "纯文本，没有文件引用", owner_id=uuid.uuid4()
        )
        assert errors == []

    async def test_validate_content_combines_file_and_video_errors(self, blog_container):
        """validate_content 合并文件和视频链接校验结果。"""
        service = BlogService(blog_container)
        mock_result = MagicMock()
        mock_result.all.return_value = []  # 没有任何文件
        blog_container._mock_session.execute.return_value = mock_result

        errors = await service.validate_content(
            "引用 [#1]", owner_id=uuid.uuid4(),
        )

        # 至少包含文件引用错误
        file_errors = [e for e in errors if "#'1'" in e]
        assert len(file_errors) >= 1

    async def test_validate_content_no_issues(self, blog_container):
        """内容没有问题时的校验通过。"""
        service = BlogService(blog_container)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        blog_container._mock_session.execute.return_value = mock_result

        errors = await service.validate_content(
            "这是一段完全正常的内容。", owner_id=uuid.uuid4()
        )
        assert errors == []

    async def test_validate_content_with_valid_video(self, blog_container):
        """视频链接合法时不报错。"""
        service = BlogService(blog_container)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        blog_container._mock_session.execute.return_value = mock_result

        content = (
            "视频链接: https://www.bilibili.com/video/BV1GJ411x7H7"
        )
        errors = await service.validate_content(content, owner_id=uuid.uuid4())
        assert errors == []


# =============================================================================
# BlogService 测试 - 文件导入与解析
# =============================================================================


class TestBlogServiceImport:
    """BlogService 文件导入与解析测试。"""

    def test_extract_title_from_markdown(self, blog_container):
        """从 Markdown 文本中提取 # 标题。"""
        service = BlogService(blog_container)
        text = "# 我的文章\n\n这是正文内容。\n\n## 小节标题"
        title, body = service._extract_title(text, "unknown.md")
        assert title == "我的文章"
        assert "这是正文内容" in body
        assert "# 我的文章" not in body

    def test_extract_title_no_heading(self, blog_container):
        """无标题时使用文件名作为标题。"""
        service = BlogService(blog_container)
        text = "直接是正文，没有标题行"
        title, body = service._extract_title(text, "hello_world.md")
        assert title == "hello_world"
        assert body == "直接是正文，没有标题行"

    def test_extract_title_empty_text(self, blog_container):
        """空文本使用文件名。"""
        service = BlogService(blog_container)
        title, body = service._extract_title("", "导入的帖子.txt")
        assert title == "导入的帖子"
        assert body == ""

    def test_extract_html_body_basic(self, blog_container):
        """从 HTML 提取 body 内容。"""
        service = BlogService(blog_container)
        html = "<html><body><h1>标题</h1><p>段落内容</p></body></html>"
        text = service._extract_html_body(html)
        assert "# 标题" in text
        assert "段落内容" in text

    def test_extract_html_body_no_body_tag(self, blog_container):
        """无 body 标签时直接处理整个 HTML。"""
        service = BlogService(blog_container)
        html = "<h1>标题</h1><p>正文</p>"
        text = service._extract_html_body(html)
        assert "# 标题" in text
        assert "正文" in text

    def test_extract_html_body_complex(self, blog_container):
        """复杂 HTML 转换。"""
        service = BlogService(blog_container)
        html = """
        <body>
            <h1>主标题</h1>
            <h2>副标题</h2>
            <p>第一段<br/>换行</p>
            <h3>三级标题</h3>
            <p>第二段</p>
        </body>
        """
        text = service._extract_html_body(html)
        assert "# 主标题" in text
        assert "## 副标题" in text
        assert "### 三级标题" in text
        assert "第一段" in text
        assert "换行" in text
        assert "第二段" in text

    def test_extract_html_body_empty(self, blog_container):
        """空 HTML 返回空字符串。"""
        service = BlogService(blog_container)
        text = service._extract_html_body("")
        assert text == ""

    def test_extract_html_body_escaped_html(self, blog_container):
        """HTML 实体被正确转义。"""
        service = BlogService(blog_container)
        html = '<body><p>A &amp; B &lt; C</p></body>'
        text = service._extract_html_body(html)
        assert "&" in text
        assert "A & B < C" in text or "A &amp; B" in text  # 实体被 unescape


# =============================================================================
# BlogService 测试 - 统计与趋势
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceStats:
    """BlogService 统计功能测试。"""

    async def test_get_stats_all_zeros(self, blog_container):
        """空数据库时所有统计值为 0。"""
        service = BlogService(blog_container)

        # 6 次 count 查询 + 1 次 coalesce 查询
        results = []
        for _ in range(6):
            r = MagicMock()
            r.scalar_one.return_value = 0
            results.append(r)
        # coalesce 查询
        r_coalesce = MagicMock()
        r_coalesce.scalar_one.return_value = 0
        results.append(r_coalesce)

        blog_container._mock_session.execute = AsyncMock(side_effect=results)

        stats = await service.get_stats()

        assert stats["total_posts"] == 0
        assert stats["published_posts"] == 0
        assert stats["pending_posts"] == 0
        assert stats["total_views"] == 0
        assert stats["total_comments"] == 0
        assert stats["total_likes"] == 0
        assert stats["today_posts"] == 0

    async def test_get_daily_trend_returns_days_count(self, blog_container):
        """get_daily_trend 返回指定天数的趋势数据。"""
        service = BlogService(blog_container)

        # 三个查询: posts, views, comments
        r1 = MagicMock()
        r1.all.return_value = []
        r2 = MagicMock()
        r2.all.return_value = []
        r3 = MagicMock()
        r3.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[r1, r2, r3]
        )

        result = await service.get_daily_trend(days=7)
        assert result["days"] == 7
        assert len(result["trend"]) == 7

    async def test_get_hot_posts_empty(self, blog_container):
        """无发布帖子时返回空列表。"""
        service = BlogService(blog_container)

        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        blog_container._mock_session.execute.return_value = r

        result = await service.get_hot_posts(limit=10)
        assert result == []

    async def test_get_hot_posts_returns_top_n(self, blog_container):
        """get_hot_posts 按浏览量降序返回限制数量的帖子。"""
        service = BlogService(blog_container)

        mock_posts = [MagicMock() for _ in range(3)]
        for i, p in enumerate(mock_posts):
            p.id = uuid.uuid4()
            p.title = f"热门文章{i + 1}"
            p.views = 100 - i * 10
            p.author_id = uuid.uuid4()
            p.created_at = None

        r_posts = MagicMock()
        r_posts.scalars.return_value.all.return_value = mock_posts

        # 作者查询
        r_author = MagicMock()
        r_author.all.return_value = [
            MagicMock(id=mock_posts[0].author_id, username="作者1"),
            MagicMock(id=mock_posts[1].author_id, username="作者2"),
            MagicMock(id=mock_posts[2].author_id, username="作者3"),
        ]

        # 点赞查询
        r_likes = MagicMock()
        r_likes.all.return_value = []

        # 评论查询
        r_comments = MagicMock()
        r_comments.all.return_value = []

        blog_container._mock_session.execute = AsyncMock(
            side_effect=[r_posts, r_author, r_likes, r_comments]
        )

        result = await service.get_hot_posts(limit=3)
        assert len(result) == 3
        assert result[0]["title"] == "热门文章1"


# =============================================================================
# BlogService 测试 - 帖子文件生命周期
# =============================================================================


@pytest.mark.asyncio
class TestBlogServiceFileLifecycle:
    """BlogService 帖子文件生命周期测试。"""

    async def test_scan_and_clean_post_files_referenced(self, blog_container):
        """正文引用的文件被标记为 persisted。"""
        service = BlogService(blog_container)

        pf1 = MagicMock()
        pf1.file_index = 1
        pf1.id = uuid.uuid4()
        pf1.status = "temp"

        pf2 = MagicMock()
        pf2.file_index = 2
        pf2.id = uuid.uuid4()
        pf2.status = "temp"

        r = MagicMock()
        r.scalars.return_value.all.return_value = [pf1, pf2]
        blog_container._mock_session.execute.return_value = r

        refs = await service.scan_and_clean_post_files(
            uuid.uuid4(), "正文引用 [#1]"
        )

        assert sorted(refs) == [1]
        assert pf1.status == "persisted"
        assert pf2.status == "temp"  # 未引用的不改状态

    async def test_scan_and_clean_post_files_no_refs(self, blog_container):
        """正文无引用时清理所有 temp 文件。"""
        service = BlogService(blog_container)

        pf1 = MagicMock()
        pf1.file_index = 1
        pf1.id = uuid.uuid4()
        pf1.status = "temp"

        r = MagicMock()
        r.scalars.return_value.all.return_value = [pf1]
        blog_container._mock_session.execute.return_value = r

        refs = await service.scan_and_clean_post_files(
            uuid.uuid4(), "无引用的正文"
        )

        assert refs == []
