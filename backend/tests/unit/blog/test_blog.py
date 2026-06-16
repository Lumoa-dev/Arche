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
