"""Blog 模块 API 集成测试。

测试真实 HTTP 请求-响应链路（HTTP → 中间件 → BlogService → 真实数据库）。
不 mock BlogService，使用真实 DB。

覆盖：
- 未登录查看公开文章列表
- 登录后发文 → 查看个人文章
- 管理员审核文章（待审核列表 → 通过 → 拒绝）
- 评论 → 点赞 → 收藏 → 举报
- 鉴权失败（401/403）边界
"""

from __future__ import annotations

import uuid

import pytest

from backend.plugins.blog.services import BlogService
from backend.tests.conftest import patch_container_service


@pytest.fixture(autouse=True)
def real_blog_service(db_container):
    """用真实 BlogService 替换容器中的 mock 服务。"""
    blog_service = BlogService(db_container)
    patch_container_service(db_container, "blog", blog_service)


@pytest.fixture
async def user_and_admin_tokens(db_container):
    """创建 admin 用户和普通用户，返回各自 token 头。

    避免 auth_headers + admin_headers 一起使用时邮箱冲突。
    """
    from backend.plugins.auth.services import AuthService

    svc = AuthService(db_container)
    # 第一个注册的用户自动 P0
    admin_result = await svc.register(
        email="blog_admin@example.com",
        username="blog_admin",
        nickname="test_user",
        password="password123",
    )
    # 第二个用户为 P5
    user_result = await svc.register(
        email="blog_user@example.com",
        username="blog_user",
        nickname="test_user",
        password="password123",
    )
    return {
        "user": {"Authorization": f"Bearer {user_result['access_token']}"},
        "admin": {"Authorization": f"Bearer {admin_result['access_token']}"},
    }


@pytest.mark.asyncio
class TestPublicPostList:
    """公开帖子列表测试。"""

    async def test_guest_gets_empty_published_list(self, client):
        """未登录用户查看公开文章列表，初始为空。"""
        response = await client.get("/api/blog/posts")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert data["data"]["items"] == []

    async def test_guest_can_search_and_filter(self, client):
        """未登录用户可以使用搜索和标签参数。"""
        response = await client.get(
            "/api/blog/posts",
            params={"page": 1, "page_size": 5, "q": "python", "tag": "test"},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
class TestCreateAndViewPosts:
    """发帖和查看个人帖子测试。"""

    async def test_create_post_requires_auth(self, client):
        """未登录用户不能发帖。"""
        response = await client.post(
            "/api/blog/posts",
            json={"title": "Test Post", "content": "This is test content", "tags": []},
        )
        assert response.status_code == 401

    async def test_create_post_success(self, client, user_and_admin_tokens):
        """登录用户发帖成功，状态为 pending。"""
        response = await client.post(
            "/api/blog/posts",
            json={
                "title": "我的第一篇博客",
                "content": "这是正文内容，用于测试发帖功能。",
                "tags": ["test", "blog"],
                "required_level": 5,
            },
            headers=user_and_admin_tokens["user"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        post = data["data"]
        assert post["title"] == "我的第一篇博客"
        assert post["status"] == "pending"
        assert post["slug"] is not None

    async def test_list_my_posts_contains_created(self, client, user_and_admin_tokens):
        """发表帖子后，/my-posts 能查到。"""
        create_resp = await client.post(
            "/api/blog/posts",
            json={"title": "我的帖子", "content": "帖子内容。", "tags": []},
            headers=user_and_admin_tokens["user"],
        )
        assert create_resp.status_code == 200
        created_id = create_resp.json()["data"]["id"]

        response = await client.get(
            "/api/blog/my-posts", headers=user_and_admin_tokens["user"]
        )
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert any(item["id"] == created_id for item in items)

    async def test_pending_post_not_in_public_list(self, client, user_and_admin_tokens):
        """刚发的 pending 帖不会出现在公开列表里。"""
        await client.post(
            "/api/blog/posts",
            json={"title": "待审核帖子", "content": "内容内容内容。", "tags": []},
            headers=user_and_admin_tokens["user"],
        )
        public_resp = await client.get("/api/blog/posts")
        assert public_resp.status_code == 200
        titles = [item["title"] for item in public_resp.json()["data"]["items"]]
        assert "待审核帖子" not in titles


@pytest.mark.asyncio
class TestModeration:
    """管理员审核测试。"""

    async def test_non_admin_cannot_access_moderation(
        self, client, user_and_admin_tokens
    ):
        """普通用户无法访问审核接口。"""
        response = await client.get(
            "/api/blog/moderation/pending",
            headers=user_and_admin_tokens["user"],
        )
        assert response.status_code == 403

    async def test_admin_approve_post(self, client, user_and_admin_tokens):
        """管理员通过审核后，帖子变为 published 并在公开列表可见。"""
        user_headers = user_and_admin_tokens["user"]
        admin_headers = user_and_admin_tokens["admin"]

        # 普通用户发帖
        create_resp = await client.post(
            "/api/blog/posts",
            json={
                "title": "等待审核",
                "content": "这是一篇需要审核的文章。",
                "tags": [],
            },
            headers=user_headers,
        )
        post_id = create_resp.json()["data"]["id"]

        # 管理员查看待审核列表
        pending_resp = await client.get(
            "/api/blog/moderation/pending", headers=admin_headers
        )
        assert pending_resp.status_code == 200
        pending_ids = [item["id"] for item in pending_resp.json()["data"]["items"]]
        assert post_id in pending_ids

        # 管理员通过审核
        approve_resp = await client.post(
            f"/api/blog/moderation/{post_id}/approve",
            headers=admin_headers,
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["code"] == "ok"

        # 现在公开列表能看到了
        public_resp = await client.get("/api/blog/posts")
        assert public_resp.status_code == 200
        titles = [item["title"] for item in public_resp.json()["data"]["items"]]
        assert "等待审核" in titles

    async def test_admin_reject_post(self, client, user_and_admin_tokens):
        """管理员可以拒绝审核。"""
        user_headers = user_and_admin_tokens["user"]
        admin_headers = user_and_admin_tokens["admin"]

        create_resp = await client.post(
            "/api/blog/posts",
            json={"title": "将被拒绝", "content": "这篇文章会被拒绝。", "tags": []},
            headers=user_headers,
        )
        post_id = create_resp.json()["data"]["id"]

        reject_resp = await client.post(
            f"/api/blog/moderation/{post_id}/reject",
            headers=admin_headers,
        )
        assert reject_resp.status_code == 200

        # 公开列表仍为空
        public_resp = await client.get("/api/blog/posts")
        assert len(public_resp.json()["data"]["items"]) == 0


@pytest.mark.asyncio
class TestInteractions:
    """互动功能测试（评论、点赞、收藏、举报）。"""

    async def _create_published_post(self, client, tokens):
        """辅助：发帖并通过审核，返回帖子 ID。"""
        create_resp = await client.post(
            "/api/blog/posts",
            json={"title": "互动测试帖", "content": "用于测试互动功能。", "tags": []},
            headers=tokens["user"],
        )
        post_id = create_resp.json()["data"]["id"]
        await client.post(
            f"/api/blog/moderation/{post_id}/approve",
            headers=tokens["admin"],
        )
        return post_id

    async def test_comment_on_post(self, client, user_and_admin_tokens):
        """登录用户可以在帖子上评论。"""
        post_id = await self._create_published_post(client, user_and_admin_tokens)
        user_headers = user_and_admin_tokens["user"]

        comment_resp = await client.post(
            f"/api/blog/posts/{post_id}/comments",
            json={"content": "这是一条测试评论"},
            headers=user_headers,
        )
        assert comment_resp.status_code == 200
        assert comment_resp.json()["code"] == "ok"

        # 验证评论列表
        list_resp = await client.get(f"/api/blog/posts/{post_id}/comments")
        assert list_resp.status_code == 200
        comments = list_resp.json()["data"]["items"]
        assert len(comments) >= 1
        assert comments[0]["content"] == "这是一条测试评论"

    async def test_like_post(self, client, user_and_admin_tokens):
        """登录用户可以给帖子点赞（幂等）。"""
        post_id = await self._create_published_post(client, user_and_admin_tokens)
        user_headers = user_and_admin_tokens["user"]

        # 点赞
        like_resp = await client.post(
            f"/api/blog/posts/{post_id}/like",
            headers=user_headers,
        )
        assert like_resp.status_code == 200

        # 再次点赞（幂等，取消点赞）
        like_resp2 = await client.post(
            f"/api/blog/posts/{post_id}/like",
            headers=user_headers,
        )
        assert like_resp2.status_code == 200

    async def test_favorite_post(self, client, user_and_admin_tokens):
        """登录用户可以收藏帖子。"""
        post_id = await self._create_published_post(client, user_and_admin_tokens)
        user_headers = user_and_admin_tokens["user"]

        # 收藏
        fav_resp = await client.post(
            f"/api/blog/favorites/{post_id}",
            headers=user_headers,
        )
        assert fav_resp.status_code == 200

        # 检查收藏状态
        status_resp = await client.get(
            f"/api/blog/posts/{post_id}/favorite-status",
            headers=user_headers,
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["data"]["favorited"] is True

        # 取消收藏
        unfav_resp = await client.delete(
            f"/api/blog/favorites/{post_id}",
            headers=user_headers,
        )
        assert unfav_resp.status_code == 200

    async def test_guest_favorite_status_is_false(self, client):
        """未登录用户查询收藏状态返回 false。"""
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/blog/posts/{fake_id}/favorite-status")
        assert response.status_code == 200
        assert response.json()["data"]["favorited"] is False

    async def test_report_post(self, client, user_and_admin_tokens):
        """登录用户可以举报帖子。"""
        post_id = await self._create_published_post(client, user_and_admin_tokens)

        report_resp = await client.post(
            "/api/blog/reports",
            json={"post_id": post_id, "reason": "spam"},
            headers=user_and_admin_tokens["user"],
        )
        assert report_resp.status_code == 200
        assert report_resp.json()["code"] == "ok"

    async def test_get_non_existent_post_returns_404(self, client):
        """获取不存在的帖子返回 404。"""
        fake_slug = "this-post-does-not-exist"
        response = await client.get(f"/api/blog/posts/{fake_slug}")
        assert response.status_code == 404


@pytest.mark.asyncio
class TestTags:
    """标签功能测试。"""

    async def test_list_tags(self, client):
        """获取标签列表。"""
        response = await client.get("/api/blog/tags")
        assert response.status_code == 200
        assert response.json()["code"] == "ok"


@pytest.mark.asyncio
class TestUpdatePostWithContent:
    """编辑帖子 — content 字段全链路集成测试。

    关键缺口识别：
    - PUT /posts/{id} 端点支持 content 字段但集成测试未覆盖
    - update_post 不会检查敏感词（与 create_post 不一致）
    - update_post 仅标题变更触发重新审核
    """

    async def _create_and_approve_post(self, client, tokens):
        """辅助：发帖并通过审核，返回帖子 ID 和 slug。"""
        create_resp = await client.post(
            "/api/blog/posts",
            json={"title": "编辑测试帖", "content": "原始内容", "tags": []},
            headers=tokens["user"],
        )
        post_id = create_resp.json()["data"]["id"]
        await client.post(
            f"/api/blog/moderation/{post_id}/approve",
            headers=tokens["admin"],
        )
        return post_id

    async def test_update_post_content_success(self, client, user_and_admin_tokens):
        """PUT 编辑帖子 content 字段成功。"""
        post_id = await self._create_and_approve_post(client, user_and_admin_tokens)
        user_headers = user_and_admin_tokens["user"]

        tip_tap_json = '{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"更新后的 TipTap 内容"}]}]}'
        update_resp = await client.put(
            f"/api/blog/posts/{post_id}",
            json={"content": tip_tap_json},
            headers=user_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["code"] == "ok"

        # 验证 content 已更新
        get_resp = await client.get(f"/api/blog/posts/by-id/{post_id}")
        assert get_resp.json()["data"]["content"] == tip_tap_json

    async def test_update_post_content_only_keeps_published(self, client, user_and_admin_tokens):
        """仅修改 content 时帖子保持 published 状态（不触发重新审核）。"""
        post_id = await self._create_and_approve_post(client, user_and_admin_tokens)
        user_headers = user_and_admin_tokens["user"]

        # 仅修改 content，不修改 title
        update_resp = await client.put(
            f"/api/blog/posts/{post_id}",
            json={"content": "仅更新内容"},
            headers=user_headers,
        )
        assert update_resp.status_code == 200

        # content-only 更新不触发重审，帖子仍为 published
        detail_resp = await client.get(f"/api/blog/posts/by-id/{post_id}")
        assert detail_resp.json()["data"]["status"] == "published"

    async def test_update_post_title_triggers_re_review(self, client, user_and_admin_tokens):
        """修改 title 时帖子重新进入审核（status → pending）。"""
        post_id = await self._create_and_approve_post(client, user_and_admin_tokens)
        user_headers = user_and_admin_tokens["user"]

        update_resp = await client.put(
            f"/api/blog/posts/{post_id}",
            json={"title": "新标题"},
            headers=user_headers,
        )
        assert update_resp.status_code == 200

        # 修改标题触发重审，帖子变为 pending，公开列表不可见
        public_resp = await client.get("/api/blog/posts")
        titles = [item["title"] for item in public_resp.json()["data"]["items"]]
        assert "新标题" not in titles

        # 管理员重新通过审核
        await client.post(
            f"/api/blog/moderation/{post_id}/approve",
            headers=user_and_admin_tokens["admin"],
        )

        public_resp2 = await client.get("/api/blog/posts")
        titles2 = [item["title"] for item in public_resp2.json()["data"]["items"]]
        assert "新标题" in titles2

    async def test_update_post_no_permission(self, client, user_and_admin_tokens):
        """非作者无法编辑帖子。"""
        post_id = await self._create_and_approve_post(client, user_and_admin_tokens)

        # 用另一个用户（admin 非作者）尝试编辑
        update_resp = await client.put(
            f"/api/blog/posts/{post_id}",
            json={"content": "恶意编辑"},
            headers=user_and_admin_tokens["admin"],
        )
        assert update_resp.status_code == 403

    async def test_update_post_not_found(self, client, user_and_admin_tokens):
        """编辑不存在的帖子返回 404。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        update_resp = await client.put(
            f"/api/blog/posts/{fake_id}",
            json={"content": "内容"},
            headers=user_and_admin_tokens["user"],
        )
        assert update_resp.status_code == 404
