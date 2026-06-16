"""博客插件测试 —— 帖子 CRUD、评论、标签。"""

from __future__ import annotations

import json
import uuid

import pytest

POSTS_URL = "/api/blog/posts"


def _make_post_payload(suffix):
    return {
        "title": f"Test Post {suffix}",
        "content": json.dumps({"type": "doc", "content": []}),
        "tags": ["test", "pytest"],
        "required_level": 5,
    }


class TestBlogPosts:
    @pytest.mark.asyncio
    async def test_create_post(self, async_client, auth_headers):
        suffix = uuid.uuid4().hex[:8]
        payload = _make_post_payload(suffix)
        resp = await async_client.post(POSTS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_posts_public(self, async_client):
        resp = await async_client.get(POSTS_URL)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_post_detail(self, async_client, auth_headers):
        suffix = uuid.uuid4().hex[:8]
        create_resp = await async_client.post(
            POSTS_URL, json=_make_post_payload(suffix), headers=auth_headers
        )
        assert create_resp.status_code == 200, f"创建失败: {create_resp.text}"
        data = create_resp.json()["data"]
        # 尝试获取 post ID（响应格式可能是 data.post.id 或 data.id）
        post_data = data.get("post") or data
        post_id = post_data["id"]

        resp = await async_client.get(f"{POSTS_URL}/by-id/{post_id}", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_create_post_without_auth(self, async_client):
        resp = await async_client.post(
            POSTS_URL, json={"title": "no auth", "content": "{}"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_my_posts(self, async_client, auth_headers):
        resp = await async_client.get("/api/blog/my-posts", headers=auth_headers)
        assert resp.status_code == 200


class TestBlogComments:
    @pytest.mark.asyncio
    async def test_add_comment(self, async_client, auth_headers):
        suffix = uuid.uuid4().hex[:8]
        post_resp = await async_client.post(
            POSTS_URL, json=_make_post_payload(suffix), headers=auth_headers
        )
        assert post_resp.status_code == 200, f"创建帖子失败: {post_resp.text}"
        post_data = post_resp.json()["data"].get("post") or post_resp.json()["data"]
        post_id = post_data["id"]

        resp = await async_client.post(
            f"{POSTS_URL}/{post_id}/comments",
            json={"content": "test comment"},
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestBlogTags:
    @pytest.mark.asyncio
    async def test_list_tags(self, async_client):
        resp = await async_client.get("/api/blog/tags")
        assert resp.status_code == 200
