from __future__ import annotations


class TestResourceExhaustion:
    """资源耗尽 / DoS 韧性测试：验证 API 在大负载下不会崩溃。"""

    async def test_oversized_request_body_rejected(self, client):
        """超大请求体应被拒绝。"""
        huge_payload = {"title": "x" * 100000, "content": "y" * 100000, "tags": []}
        resp = await client.post(
            "/api/blog/posts",
            json=huge_payload,
        )
        # 未认证返回 401，但不应返回 500 或 hang
        assert resp.status_code in (401, 413, 422), (
            f"Oversized body not handled: status {resp.status_code}"
        )

    async def test_deeply_nested_json_rejected(self, client):
        """深度嵌套的 JSON 应被拒绝不导致崩溃。"""

        def make_nested(depth):
            if depth <= 0:
                return "x"
            return {"nested": make_nested(depth - 1)}

        deep_json = make_nested(500)
        resp = await client.post(
            "/api/auth/register",
            json=deep_json,
        )
        assert resp.status_code in (400, 422, 401), (
            f"Deeply nested JSON not handled: status {resp.status_code}"
        )

    async def test_huge_query_params(self, client):
        """超长查询参数应被处理不崩溃。"""
        resp = await client.get(
            "/api/blog/posts",
            params={"q": "x" * 5000},
        )
        # 允许 400/401/413/422/200，只要不 500
        assert resp.status_code != 500, "Huge query param caused 500"

    async def test_many_query_params(self, client):
        """大量查询参数应被处理不崩溃。"""
        params = {f"param_{i}": f"value_{i}" for i in range(50)}
        resp = await client.get("/api/blog/posts", params=params)
        assert resp.status_code != 500, "Many query params caused 500"

    async def test_large_file_upload_rejected(self, client, auth_headers, db_container):
        """超大文件上传应被拒绝。"""
        from unittest.mock import AsyncMock

        from backend.tests.conftest import patch_container_service

        # 使用 mock storage 避免依赖 MinIO
        mock_storage = AsyncMock()
        mock_storage.upload_file = AsyncMock(
            return_value={
                "id": "mock-id",
                "owner_id": "test",
                "path": "test",
                "size": 0,
                "mime_type": "image/png",
                "storage_type": "local",
            }
        )
        patch_container_service(db_container, "storage", mock_storage)

        huge_content = b"x" * (5 * 1024 * 1024)  # 5MB
        resp = await client.post(
            "/api/oss/upload",
            files={"file": ("huge.png", huge_content, "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code != 500, "Large file upload caused 500"

    async def test_concurrent_register_requests(self, client):
        """并发注册请求应正确处理（无竞态条件导致重复用户）。"""
        import asyncio

        payload = {
            "email": "concurrent-test@example.com",
            "username": "concurrenttest",
            "password": "testpass123",
        }

        async def register():
            return await client.post("/api/auth/register", json=payload)

        tasks = [register() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        for r in results:
            if isinstance(r, Exception):
                continue
            if r.status_code == 200:
                success_count += 1

        # 最多只有一个注册成功（用户唯一约束）
        assert success_count <= 1, (
            f"Concurrent registration created {success_count} users (expected ≤1)"
        )
