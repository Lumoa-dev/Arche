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
        data = resp.json()
        assert data["code"] == "ok"
        post = data["data"].get("post") or data["data"]
        assert post["title"] == payload["title"]

    @pytest.mark.asyncio
    async def test_list_posts_public(self, async_client):
        resp = await async_client.get(POSTS_URL)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_post_detail(self, async_client, auth_headers):
        suffix = uuid.uuid4().hex[:8]
        payload = _make_post_payload(suffix)
        create_resp = await async_client.post(
            POSTS_URL, json=payload, headers=auth_headers
        )
        assert create_resp.status_code == 200, f"创建失败: {create_resp.text}"
        data = create_resp.json()["data"]
        post_data = data.get("post") or data
        post_id = post_data["id"]
        assert post_data["title"] == payload["title"]

        resp = await async_client.get(
            f"{POSTS_URL}/by-id/{post_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["data"]["title"] == payload["title"]

    @pytest.mark.asyncio
    async def test_create_post_without_auth(self, async_client):
        resp = await async_client.post(
            POSTS_URL, json={"title": "no auth", "content": "{}"}
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "auth" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_my_posts(self, async_client, auth_headers):
        suffix = uuid.uuid4().hex[:8]
        payload = _make_post_payload(suffix)
        await async_client.post(POSTS_URL, json=payload, headers=auth_headers)

        resp = await async_client.get("/api/blog/my-posts", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # /my-posts 返回帖子列表
        posts = data.get("data", {}).get("posts") or data.get("data", {}).get("list") or data.get("data")
        # 验证列表非空且包含刚创建的帖子标题
        if isinstance(posts, list):
            titles = [p.get("title", "") for p in posts]
            assert payload["title"] in titles, f"刚创建的帖子不在列表中: {titles}"

    @pytest.mark.asyncio
    async def test_update_post(self, async_client, auth_headers):
        suffix = uuid.uuid4().hex[:8]
        payload = _make_post_payload(suffix)
        create_resp = await async_client.post(
            POSTS_URL, json=payload, headers=auth_headers
        )
        assert create_resp.status_code == 200
        post_id = (create_resp.json()["data"].get("post") or create_resp.json()["data"])["id"]

        new_title = f"Updated Title {suffix}"
        resp = await async_client.put(
            f"{POSTS_URL}/{post_id}",
            json={"title": new_title},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        updated = data["data"].get("post") or data["data"]
        assert updated["title"] == new_title

    @pytest.mark.asyncio
    async def test_update_post_not_author(self, async_client, auth_headers, admin_headers):
        """非作者不能编辑帖子。"""
        suffix = uuid.uuid4().hex[:8]
        create_resp = await async_client.post(
            POSTS_URL, json=_make_post_payload(suffix), headers=auth_headers
        )
        assert create_resp.status_code == 200
        post_id = (create_resp.json()["data"].get("post") or create_resp.json()["data"])["id"]

        # 用 admin 用户（非作者）更新
        resp = await async_client.put(
            f"{POSTS_URL}/{post_id}",
            json={"title": "hacked title"},
            headers=admin_headers,
        )
        assert resp.status_code == 403
        data = resp.json()
        assert "permission" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_delete_post(self, async_client, auth_headers):
        suffix = uuid.uuid4().hex[:8]
        create_resp = await async_client.post(
            POSTS_URL, json=_make_post_payload(suffix), headers=auth_headers
        )
        assert create_resp.status_code == 200
        post_id = (create_resp.json()["data"].get("post") or create_resp.json()["data"])["id"]

        resp = await async_client.delete(
            f"{POSTS_URL}/{post_id}", headers=auth_headers
        )
        assert resp.status_code == 200

        # 删除后再查应 404
        resp = await async_client.get(
            f"{POSTS_URL}/by-id/{post_id}", headers=auth_headers
        )
        assert resp.status_code != 200  # not_found 或 404


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
        data = resp.json()
        assert data["code"] == "ok"


class TestBlogTags:
    @pytest.mark.asyncio
    async def test_list_tags(self, async_client):
        resp = await async_client.get("/api/blog/tags")
        assert resp.status_code == 200
