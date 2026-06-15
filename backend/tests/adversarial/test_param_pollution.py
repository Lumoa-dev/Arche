from __future__ import annotations

import pytest

from backend.tests.conftest import patch_container_service


class TestParameterPollution:
    PAYLOADS = [  # noqa: RUF012
        ("array_for_string", ["a", "b", "c"]),
        ("object_for_array", {"should": "be_array"}),
        ("null_for_required", None),
        ("negative_for_ge0", -1),
        ("oversized_string", "x" * 10000),
    ]

    EXTENDED_PAYLOADS = [  # noqa: RUF012
        ("boolean_for_string", True),
        ("float_for_int", 3.14),
        ("empty_object", {}),
        ("empty_array", []),
        ("min_int", -(2**31)),
        ("max_int", 2**31 - 1),
        ("nested_object_deep", {"a": {"b": {"c": {"d": {"e": "deep"}}}}}),
        ("proto_pollution", {"__proto__": {"admin": True}}),
        ("constructor_pollution", {"constructor": {"prototype": {"admin": True}}}),
        ("unicode_overlong", "\u0100\u017f" * 100),
    ]

    @pytest.fixture(autouse=True)
    def setup_blog_service(self, db_container):
        from backend.plugins.blog.services import BlogService

        blog_service = BlogService(db_container)
        patch_container_service(db_container, "blog", blog_service)

    async def test_create_post_param_pollution(
        self, client, auth_headers, db_container
    ):
        from backend.plugins.blog.services import BlogService

        blog_service = BlogService(db_container)
        patch_container_service(db_container, "blog", blog_service)

        for desc, value in self.PAYLOADS:
            payload = {"title": "test", "content": "test content", "tags": []}
            if desc == "array_for_string":
                payload["title"] = value
            elif desc == "object_for_array":
                payload["tags"] = value
            elif desc == "null_for_required":
                payload["title"] = value
            elif desc == "negative_for_ge0":
                payload["required_level"] = value
            elif desc == "oversized_string":
                payload["title"] = value

            resp = await client.post(
                "/api/blog/posts",
                json=payload,
                headers=auth_headers,
            )
            assert resp.status_code == 422, (
                f"Param pollution {desc} not rejected: got {resp.status_code}"
            )
            data = resp.json()
            assert data["code"] == "validation_error"

    async def test_register_param_pollution(self, client):
        register_payloads = [
            ("array_for_email", ["a", "b"]),
            ("null_for_required", None),
            ("oversized_string", "x" * 10000),
        ]

        for desc, value in register_payloads:
            payload = {
                "email": "test@test.com",
                "username": "testuser",
                "password": "testpass123",
            }
            if (
                desc == "array_for_email"
                or desc == "null_for_required"
                or desc == "oversized_string"
            ):
                payload["email"] = value

            resp = await client.post(
                "/api/auth/register",
                json=payload,
            )
            assert resp.status_code == 422, (
                f"Register param pollution {desc} not rejected: got {resp.status_code}"
            )

    async def test_login_param_pollution(self, client):
        for desc, value in self.PAYLOADS[:3]:
            payload = {"identity": "testuser", "password": "testpass123"}
            if desc == "array_for_string":
                payload["identity"] = value
            elif desc == "object_for_array":
                payload["password"] = value
            elif desc == "null_for_required":
                payload["identity"] = value

            resp = await client.post(
                "/api/auth/login",
                json=payload,
            )
            assert resp.status_code == 422, (
                f"Login param pollution {desc} not rejected: got {resp.status_code}"
            )

    async def test_create_post_extended_pollution(
        self, client, auth_headers, db_container
    ):
        from backend.plugins.blog.services import BlogService

        blog_service = BlogService(db_container)
        patch_container_service(db_container, "blog", blog_service)

        for desc, value in self.EXTENDED_PAYLOADS:
            payload = {"title": "test", "content": "test content", "tags": []}
            if desc in ("boolean_for_string",):
                payload["title"] = value
            elif desc in ("float_for_int", "min_int", "max_int"):
                payload["required_level"] = value
            elif desc in (
                "empty_object",
                "empty_array",
                "nested_object_deep",
                "unicode_overlong",
            ):
                payload["title"] = value
            elif desc in ("proto_pollution", "constructor_pollution"):
                payload["title"] = "test"
                payload.update(value)

            resp = await client.post(
                "/api/blog/posts",
                json=payload,
                headers=auth_headers,
            )
            assert resp.status_code != 500, (
                f"Extended param pollution {desc} caused 500"
            )
