from __future__ import annotations

import pytest

from backend.tests.adversarial.conftest import SQLI_PAYLOADS
from backend.tests.conftest import patch_container_service


class TestSQLInjections:
    PAYLOADS = SQLI_PAYLOADS

    @pytest.fixture(autouse=True)
    def setup_services(self, db_container):
        from backend.plugins.blog.services import BlogService

        blog_service = BlogService(db_container)
        patch_container_service(db_container, "blog", blog_service)

        from backend.plugins.search.services import SearchService

        search_service = SearchService(db_container)
        patch_container_service(db_container, "search", search_service)

    async def test_blog_posts_search_resists_sqli(self, client, auth_headers):
        for payload in self.PAYLOADS:
            resp = await client.get(
                "/api/blog/posts",
                params={"q": payload},
                headers=auth_headers,
            )
            assert resp.status_code == 200, (
                f"SQLi payload broke the endpoint: {payload}, status: {resp.status_code}"
            )
            data = resp.json()
            assert data["code"] == "ok"
            assert "data" in data
            assert "items" in data["data"]
            assert "total" in data["data"]

    async def test_blog_posts_search_public_resists_sqli(self, client):
        for payload in self.PAYLOADS:
            resp = await client.get(
                "/api/blog/posts",
                params={"q": payload},
            )
            assert resp.status_code in (200, 401), (
                f"SQLi payload caused unexpected status: {payload}, status: {resp.status_code}"
            )
            if resp.status_code == 200:
                data = resp.json()
                assert data["code"] == "ok"

    async def test_search_suggestions_resists_sqli(self, client, auth_headers):
        for payload in self.PAYLOADS:
            resp = await client.get(
                "/api/search/suggestions",
                params={"q": payload},
                headers=auth_headers,
            )
            assert resp.status_code == 200, (
                f"SQLi payload broke search: {payload}, status: {resp.status_code}"
            )
            data = resp.json()
            assert data["code"] == "ok"
            assert "data" in data
