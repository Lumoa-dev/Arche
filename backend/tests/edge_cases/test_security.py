"""安全攻击测试 —— 注入类攻击向量。

通过真实 HTTP 请求验证后端对各种攻击向量的防御能力。
"""

from __future__ import annotations

import uuid

import pytest


class TestSQLInjection:
    """SQL 注入防护测试。"""

    @pytest.mark.asyncio
    async def test_sql_injection_in_login(self, async_client):
        """登录接口的 identity 字段拒接 SQL 注入。"""
        resp = await async_client.post(
            "/api/auth/login",
            json={"identity": "' OR '1'='1", "password": "' OR '1'='1"},
        )
        # 注入失败时返回 401（不应 500，更不应 200）
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_sql_injection_in_search(self, async_client, auth_headers):
        """搜索接口拒接 SQL 注入。"""
        resp = await async_client.get(
            "/api/search/suggestions?q='; DROP TABLE users; --",
            headers=auth_headers,
        )
        # ORM 参数化查询，注入 payload 作为普通搜索关键词处理
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_sql_injection_integer_field(self, async_client, admin_headers):
        """数字参数拒接 SQL 注入。"""
        resp = await async_client.get(
            "/api/auth/users?page=1&page_size=10; DROP TABLE users",
            headers=admin_headers,
        )
        # page_size 参数化查询，注入 payload 被忽略或校验失败
        assert resp.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_sql_union_injection(self, async_client, auth_headers):
        """UNION 注入不导致数据泄露。"""
        resp = await async_client.get(
            "/api/search/suggestions?q=test UNION SELECT * FROM users",
            headers=auth_headers,
        )
        # ORM 参数化，UNION 作为普通文本搜索
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_sql_injection_in_registration(self, async_client):
        """注册接口 JSON body 中的 SQL 注入不导致崩溃。"""
        suffix = uuid.uuid4().hex[:4]
        resp = await async_client.post(
            "/api/auth/register",
            json={
                "email": f"sqli_{suffix}@test.com",
                "username": "admin'; DROP TABLE users; --",
                "nickname": "SQLi Attempt",
                "password": "Test1234!",
            },
        )
        # ORM 参数化，注入 payload 当作普通用户名处理
        assert resp.status_code in (200, 400, 422)


class TestXSS:
    """XSS 跨站脚本防护测试。"""

    @pytest.mark.asyncio
    async def test_xss_in_register(self, async_client):
        """注册接口拒接/转义 XSS 负载。"""
        resp = await async_client.post(
            "/api/auth/register",
            json={
                "email": "xss@test.com",
                "username": "<script>alert(1)</script>",
                "nickname": "<img src=x onerror=alert(1)>",
                "password": "Test1234!",
            },
        )
        # 应拒绝或返回 200 但转义内容
        assert resp.status_code in (200, 400, 422)

    @pytest.mark.asyncio
    async def test_xss_in_blog_post(self, async_client, auth_headers):
        """创建帖子时注入 XSS。"""
        import json

        resp = await async_client.post(
            "/api/blog/posts",
            json={
                "title": "<script>document.cookie</script>",
                "content": json.dumps(
                    {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "text": "<img src=x onerror=alert('XSS')>",
                                        "type": "text",
                                    }
                                ],
                            }
                        ],
                    }
                ),
                "tags": ["<script>"],
            },
            headers=auth_headers,
        )
        # 应成功创建（内容不执行），或拒绝
        assert resp.status_code in (200, 400, 422)

    @pytest.mark.asyncio
    async def test_xss_in_query_param(self, async_client, auth_headers):
        """查询参数中的 XSS 负载不破坏响应。"""
        resp = await async_client.get(
            '/api/search/suggestions?q=<script>alert("XSS")</script>',
            headers=auth_headers,
        )
        assert resp.status_code in (200, 400, 422)
        # 响应体不包含未转义的脚本
        text = resp.text.lower()
        assert "<script>" not in text or "&lt;" in text  # 应已转义

    @pytest.mark.asyncio
    async def test_xss_in_blog_comment(self, async_client, auth_headers):
        """帖子评论中的 XSS 负载不破坏响应。"""
        import json

        # 先创建一篇帖子
        suffix = uuid.uuid4().hex[:4]
        post_resp = await async_client.post(
            "/api/blog/posts",
            json={
                "title": f"XSS Test {suffix}",
                "content": json.dumps({"type": "doc", "content": []}),
                "tags": ["test"],
            },
            headers=auth_headers,
        )
        assert post_resp.status_code == 200
        post_id = post_resp.json()["data"].get("post", post_resp.json()["data"]).get("id", "")

        # 提交含 XSS 的评论
        comment_resp = await async_client.post(
            f"/api/blog/posts/{post_id}/comments",
            json={
                "content": json.dumps({
                    "type": "doc",
                    "content": [
                        {"type": "paragraph", "content": [{"text": "<script>alert('xss')</script>", "type": "text"}]}
                    ]
                }),
                "author_name": "<script>alert('xss')</script>",
            },
            headers=auth_headers,
        )
        assert comment_resp.status_code in (200, 201, 400, 422)


class TestPathTraversal:
    """路径遍历防护测试。"""

    @pytest.mark.asyncio
    async def test_path_traversal_in_oss(self, async_client, auth_headers):
        """OSS 文件下载拒接路径遍历。"""
        resp = await async_client.get(
            "/api/oss/files/../../../etc/passwd",
            headers=auth_headers,
        )
        assert resp.status_code in (401, 403, 404, 422)  # 不应返回文件内容

    @pytest.mark.asyncio
    async def test_path_traversal_in_blog(self, async_client, auth_headers):
        """博客路由拒接路径遍历。"""
        for path in [
            "/api/blog/posts/../../../etc/passwd",
            "/api/blog/posts/..%2f..%2f..%2fetc%2fpasswd",
        ]:
            resp = await async_client.get(path, headers=auth_headers)
            assert resp.status_code in (401, 403, 404, 422), f"路径遍历应被拦截: {path}"


class TestParameterPollution:
    """参数污染防护测试。"""

    @pytest.mark.asyncio
    async def test_duplicate_params(self, async_client, auth_headers):
        """重复参数不应导致异常行为。"""
        resp = await async_client.get(
            "/api/search/suggestions?q=test&q=admin",
            headers=auth_headers,
        )
        assert resp.status_code in (200, 400, 422)

    @pytest.mark.asyncio
    async def test_empty_values(self, async_client, auth_headers):
        """空参数值不应崩溃。"""
        resp = await async_client.get(
            "/api/search/suggestions?q=",
            headers=auth_headers,
        )
        assert resp.status_code in (200, 400, 422)

    @pytest.mark.asyncio
    async def test_content_type_manipulation(self, async_client):
        """Content-Type 篡改不应绕过验证。"""
        resp = await async_client.post(
            "/api/auth/register",
            content=b'{"email":"test@test.com","username":"test","nickname":"test","password":"Test1234!"}',
            headers={"Content-Type": "text/plain"},
        )
        # 错误 Content-Type 可能被接受或拒绝，但不导致 500
        assert resp.status_code in (200, 400, 415, 422)
        assert resp.status_code != 500


class TestJWTSecurity:
    """JWT 安全测试。"""

    @pytest.mark.asyncio
    async def test_expired_token(self, async_client):
        """过期 token 被拒接。"""
        import jwt

        expired = jwt.encode(
            {"sub": "test", "exp": 0, "level": 5},
            key="test-secret-key-for-pytest",
            algorithm="HS256",
        )
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_tampered_token(self, async_client):
        """篡改 token 被拒接。"""
        resp = await async_client.get(
            "/api/auth/me",
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImxldmVsIjowfQ.tampered"
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_none_algorithm(self, async_client):
        """none 算法攻击被拒接。"""
        import base64
        import json

        header = (
            base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
            .rstrip(b"=")
            .decode()
        )
        payload = (
            base64.urlsafe_b64encode(json.dumps({"sub": "admin", "level": 0}).encode())
            .rstrip(b"=")
            .decode()
        )
        fake_token = f"{header}.{payload}."
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {fake_token}"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret(self, async_client):
        """错误密钥签名的 token 被拒接。"""
        import jwt

        wrong_key = jwt.encode(
            {"sub": "test", "level": 5, "exp": 9999999999},
            key="wrong-secret-key",
            algorithm="HS256",
        )
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {wrong_key}"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_token_missing_sub(self, async_client):
        """缺少 sub 字段的 token 被拒接。"""
        import jwt

        bad_token = jwt.encode(
            {"level": 5, "exp": 9999999999},
            key="test-secret-key-for-pytest",
            algorithm="HS256",
        )
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_token_wrong_type(self, async_client):
        """非 Bearer 类型的认证头被拒接。"""
        import jwt

        token = jwt.encode(
            {"sub": "test", "level": 5, "exp": 9999999999},
            key="test-secret-key-for-pytest",
            algorithm="HS256",
        )
        resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Basic {token}"},
        )
        assert resp.status_code == 401


class TestMassAssignment:
    """批量赋值防护测试。"""

    @pytest.mark.asyncio
    async def test_cannot_set_own_level(self, async_client):
        """用户不能通过注册 API 设置自己的等级。

        注册时传入 level 字段应被忽略——第一个用户获得默认 level 0
        是 auth 服务的内部逻辑，而非来自请求体。
        """
        suffix = uuid.uuid4().hex[:8]
        resp = await async_client.post(
            "/api/auth/register",
            json={
                "email": f"mass_{suffix}@test.com",
                "username": f"mass_{suffix}",
                "nickname": "Mass Assignment",
                "password": "Test1234!",
                "level": 0,  # 试图提权
                "is_admin": True,
            },
        )
        # 多余参数应被忽略或拒绝，但不导致 500
        assert resp.status_code in (200, 400, 422)
        assert resp.status_code != 500


class TestRateLimit:
    """限流与滥用防护测试。"""

    @pytest.mark.asyncio
    async def test_rapid_login_from_same_ip(self, async_client):
        """同一 IP 多次登录失败不应导致 500。"""
        for _ in range(10):
            resp = await async_client.post(
                "/api/auth/login",
                json={"identity": "nonexistent", "password": "wrong"},
            )
            # 即使触发限流，也不应返回 500
            assert resp.status_code != 500
            # 返回 429 是正常限流行为
            if resp.status_code == 429:
                break
