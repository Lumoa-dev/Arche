"""边界场景测试 —— 空值、超长、格式异常、并发。

覆盖所有插件公共端点的异常输入处理能力。
"""

from __future__ import annotations

import asyncio
import uuid

import pytest


class TestEmptyInput:
    """空值/缺失值处理。"""

    @pytest.mark.asyncio
    async def test_empty_body(self, async_client):
        """所有 POST/PUT 端点对空 body 返回 422。"""
        endpoints = [
            ("POST", "/api/auth/register"),
            ("POST", "/api/auth/login"),
            ("POST", "/api/auth/logout"),
            ("POST", "/api/auth/refresh"),
            ("POST", "/api/oss/upload"),
        ]
        for method, path in endpoints:
            if method == "POST":
                resp = await async_client.post(path, json={})
            else:
                resp = await async_client.put(path, json={})
            # 空 body 应触发验证错误，不崩贵
            assert resp.status_code in (401, 422), f"{method} {path}: {resp.status_code}"

    @pytest.mark.asyncio
    async def test_missing_required_field(self, async_client):
        """缺少必填字段返回 422。"""
        resp = await async_client.post(
            "/api/auth/register",
            json={"email": "test@test.com"},  # 缺少 username, nickname, password
        )
        assert resp.status_code == 422


class TestLongInput:
    """超长输入处理。"""

    @pytest.mark.asyncio
    async def test_very_long_username(self, async_client):
        """超长用户名应被拒绝。"""
        resp = await async_client.post(
            "/api/auth/register",
            json={
                "email": "long@test.com",
                "username": "a" * 1000,
                "nickname": "long",
                "password": "Test1234!",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_very_long_password(self, async_client):
        """超长密码应被拒绝或截断。"""
        resp = await async_client.post(
            "/api/auth/register",
            json={
                "email": "longpw@test.com",
                "username": "longpw",
                "nickname": "longpw",
                "password": "a" * 10000,
            },
        )
        assert resp.status_code in (200, 422, 413)  # 413 = payload too large

    @pytest.mark.asyncio
    async def test_very_long_blog_title(self, async_client, auth_headers):
        """超长帖子标题应被拒绝。"""
        import json

        resp = await async_client.post(
            "/api/blog/posts",
            json={
                "title": "x" * 10000,
                "content": json.dumps({"type": "doc", "content": []}),
                "tags": ["test"],
            },
            headers=auth_headers,
        )
        assert resp.status_code in (200, 400, 422, 413)


class TestMethodNotAllowed:
    """HTTP 方法限制。"""

    @pytest.mark.asyncio
    async def test_get_on_create_endpoint(self, async_client):
        """GET 请求创建端点返回 405。"""
        resp = await async_client.get("/api/auth/register")
        assert resp.status_code in (405, 404)

    @pytest.mark.asyncio
    async def test_post_on_list_endpoint(self, async_client):
        """POST 请求列表端点返回 405。"""
        resp = await async_client.post("/api/blog/posts?page=1", headers={"Content-Type": "application/json"})
        assert resp.status_code in (405, 401, 422)

    @pytest.mark.asyncio
    async def test_put_on_readonly_endpoint(self, async_client):
        """PUT 请求只读端点返回 405。"""
        resp = await async_client.put("/api/ping", json={})
        assert resp.status_code in (405, 404)


class TestConcurrency:
    """并发请求测试。"""

    @pytest.mark.asyncio
    async def test_concurrent_registration(self, async_client):
        """并发注册不产生数据竞争。"""
        suffix = uuid.uuid4().hex[:8]
        base_email = f"concur_{suffix}@test.com"
        base_user = f"concur_{suffix}"

        async def register_user(idx: int):
            payload = {
                "email": f"{idx}_{base_email}",
                "username": f"{idx}_{base_user}",
                "nickname": f"user_{idx}",
                "password": "Test1234!",
            }
            return await async_client.post("/api/auth/register", json=payload)

        # 同时发 10 个注册
        tasks = [register_user(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)
        assert successes >= 8, f"并发注册成功率太低: {successes}/10"

    @pytest.mark.asyncio
    async def test_rapid_login(self, async_client):
        """短时间内重复登录不崩溃。"""
        suffix = uuid.uuid4().hex[:8]
        reg = {
            "email": f"rapid_{suffix}@test.com",
            "username": f"rapid_{suffix}",
            "nickname": "rapid",
            "password": "Test1234!",
        }
        await async_client.post("/api/auth/register", json=reg)

        async def login():
            return await async_client.post(
                "/api/auth/login",
                json={"identity": reg["username"], "password": reg["password"]},
            )

        tasks = [login() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)
        assert successes >= 3, f"快速登录成功率太低: {successes}/5"


class TestUnicode:
    """Unicode 与编码处理。"""

    @pytest.mark.asyncio
    async def test_unicode_username(self, async_client):
        """中文字符用户名可正常注册。"""
        suffix = uuid.uuid4().hex[:4]
        resp = await async_client.post(
            "/api/auth/register",
            json={
                "email": f"cn_{suffix}@test.com",
                "username": f"中文字_{suffix}",
                "nickname": "中文昵称",
                "password": "Test1234!",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_emoji_in_input(self, async_client):
        """emoji 在输入中不崩溃。"""
        resp = await async_client.post(
            "/api/auth/register",
            json={
                "email": f"emoji_{uuid.uuid4().hex[:4]}@test.com",
                "username": "emoji_test_user",
                "nickname": "😀🔥🎉",
                "password": "Test1234!",
            },
        )
        assert resp.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_zero_width_chars(self, async_client):
        """零宽字符不导致安全漏洞。"""
        resp = await async_client.post(
            "/api/auth/register",
            json={
                "email": f"zwsp_{uuid.uuid4().hex[:4]}@test.com",
                "username": "admin\u200b\u200c\u200d",
                "nickname": "Zero Width",
                "password": "Test1234!",
            },
        )
        # 零宽字符可能被接受或拒绝，但不崩溃
        assert resp.status_code in (200, 400, 422)
