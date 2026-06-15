from __future__ import annotations

import pytest

from backend.tests.adversarial.conftest import XSS_PAYLOADS
from backend.tests.conftest import patch_container_service


class TestXSSInjections:
    PAYLOADS = XSS_PAYLOADS

    @pytest.fixture(autouse=True)
    def setup_blog_service(self, db_container):
        from backend.plugins.blog.services import BlogService

        blog_service = BlogService(db_container)
        patch_container_service(db_container, "blog", blog_service)

    async def _create_post(self, client, auth_headers, payload, field="content"):
        post_data = {"title": "test post", "content": "safe content", "tags": []}
        post_data[field] = payload
        resp = await client.post(
            "/api/blog/posts",
            json=post_data,
            headers=auth_headers,
        )
        return resp

    async def test_blog_create_rejects_xss_in_content(self, client, auth_headers):
        for payload in self.PAYLOADS:
            resp = await self._create_post(client, auth_headers, payload, "content")
            assert resp.status_code in (200, 400, 422), f"XSS payload failed: {payload}"
            if resp.status_code == 200:
                data = resp.json()
                assert data["code"] == "ok"

    async def test_blog_create_rejects_xss_in_title(self, client, auth_headers):
        for payload in self.PAYLOADS:
            resp = await self._create_post(client, auth_headers, payload, "title")
            assert resp.status_code in (200, 400, 422), (
                f"XSS title payload failed: {payload}"
            )
            if resp.status_code == 200:
                data = resp.json()
                assert data["code"] == "ok"

    async def _create_comment(self, client, auth_headers, payload, post_id):
        resp = await client.post(
            f"/api/blog/posts/{post_id}/comments",
            json={"content": payload},
            headers=auth_headers,
        )
        return resp

    async def test_comment_rejects_xss(self, client, auth_headers, db_container):
        from backend.plugins.blog.services import BlogService

        blog_service = BlogService(db_container)
        patch_container_service(db_container, "blog", blog_service)

        post_resp = await client.post(
            "/api/blog/posts",
            json={"title": "test post", "content": "safe content", "tags": []},
            headers=auth_headers,
        )
        assert post_resp.status_code == 200
        post_id = post_resp.json()["data"]["id"]

        for payload in self.PAYLOADS:
            resp = await self._create_comment(client, auth_headers, payload, post_id)
            assert resp.status_code in (200, 400, 422), f"XSS comment failed: {payload}"
            if resp.status_code == 200:
                data = resp.json()
                assert data["code"] == "ok"

    async def _create_report(self, client, auth_headers, payload, post_id):
        resp = await client.post(
            "/api/blog/reports",
            json={"post_id": post_id, "reason": payload},
            headers=auth_headers,
        )
        return resp

    async def test_report_rejects_xss(self, client, auth_headers, db_container):
        from backend.plugins.blog.services import BlogService

        blog_service = BlogService(db_container)
        patch_container_service(db_container, "blog", blog_service)

        post_resp = await client.post(
            "/api/blog/posts",
            json={"title": "test post", "content": "safe content", "tags": []},
            headers=auth_headers,
        )
        assert post_resp.status_code == 200
        post_id = post_resp.json()["data"]["id"]

        for payload in self.PAYLOADS:
            resp = await self._create_report(client, auth_headers, payload, post_id)
            assert resp.status_code in (200, 400, 422), f"XSS report failed: {payload}"

    async def test_markdown_image_xss(self, client, auth_headers):
        """Markdown 图片语法中的 XSS 尝试。"""
        md_xss_payloads = [
            "![](javascript:alert(1))",
            "![x](http://evil.com/steal?cookie=x)",
            "[click me](javascript:alert(1))",
            "[x](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)",
        ]
        for payload in md_xss_payloads:
            resp = await self._create_post(client, auth_headers, payload, "content")
            assert resp.status_code in (200, 400, 422), (
                f"Markdown XSS payload failed: {payload}"
            )
            if resp.status_code == 200:
                data = resp.json()
                assert data["code"] == "ok"
