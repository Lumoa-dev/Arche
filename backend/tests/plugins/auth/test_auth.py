"""认证插件测试 —— 注册/登录/登出/Token 刷新/权限管理。

测试模式：通过 async_client 发真实 HTTP 请求到真实后端，
所有操作走真实数据库，零 mock。
"""

from __future__ import annotations

import uuid

import pytest


class TestRegister:
    """测试用户注册。"""

    REGISTER_URL = "/api/auth/register"

    @pytest.mark.asyncio
    async def test_register_success(self, async_client):
        """正常注册应返回用户信息和 token。"""
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "email": f"new_{suffix}@example.com",
            "username": f"newuser_{suffix}",
            "nickname": f"新用户_{suffix}",
            "password": "SecurePass1!",
        }
        resp = await async_client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 200, f"注册失败: {resp.text}"
        data = resp.json()
        assert data["code"] == "ok"
        assert "access_token" in data["data"]
        assert data["data"]["user"]["email"] == payload["email"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client, auth_headers):
        """重复邮箱注册应返回错误。"""
        suffix = uuid.uuid4().hex[:8]
        email = f"dup_{suffix}@example.com"
        payload = {
            "email": email,
            "username": f"dupuser_{suffix}",
            "nickname": "重复测试",
            "password": "SecurePass1!",
        }
        resp = await async_client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 200

        # 再次用相同邮箱注册
        resp = await async_client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 409, f"应拒绝重复邮箱: {resp.text}"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, async_client):
        """重复用户名注册应返回错误。"""
        suffix = uuid.uuid4().hex[:8]
        username = f"dupuser_{suffix}"
        payload = {
            "email": f"first_{suffix}@example.com",
            "username": username,
            "nickname": "第一个",
            "password": "SecurePass1!",
        }
        resp = await async_client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 200

        # 相同用户名、不同邮箱
        payload2 = {
            "email": f"second_{suffix}@example.com",
            "username": username,
            "nickname": "第二个",
            "password": "SecurePass1!",
        }
        resp = await async_client.post(self.REGISTER_URL, json=payload2)
        assert resp.status_code == 409, f"应拒绝重复用户名: {resp.text}"

    @pytest.mark.asyncio
    async def test_register_invalid_data(self, async_client):
        """无效数据应返回 422。"""
        # 空 body
        resp = await async_client.post(
            self.REGISTER_URL, json={}, headers={"Content-Type": "application/json"}
        )
        assert resp.status_code == 422

        # 密码太短
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "email": f"short_{suffix}@example.com",
            "username": f"short_{suffix}",
            "nickname": "短密码",
            "password": "ab",
        }
        resp = await async_client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_level_assignment(self, async_client, db_session):
        """验证用户等级分配。"""
        from sqlalchemy import select

        from backend.plugins.auth.models import User

        suffix = uuid.uuid4().hex[:8]
        payload = {
            "email": f"level_{suffix}@example.com",
            "username": f"level_{suffix}",
            "nickname": "等级测试",
            "password": "SecurePass1!",
        }
        resp = await async_client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 200

        # 直接从数据库检查 level
        result = await db_session.execute(
            select(User).where(User.username == payload["username"])
        )
        user = result.scalar_one()
        assert user.level is not None


class TestLogin:
    """测试用户登录。"""

    LOGIN_URL = "/api/auth/login"

    @pytest.mark.asyncio
    async def test_login_success(self, async_client):
        """正常登录应返回 access_token 和 refresh_token。"""
        suffix = uuid.uuid4().hex[:8]
        reg_payload = {
            "email": f"login_{suffix}@example.com",
            "username": f"login_{suffix}",
            "nickname": "登录测试",
            "password": "LoginPass1!",
        }
        reg_resp = await async_client.post("/api/auth/register", json=reg_payload)
        assert reg_resp.status_code == 200

        # 登录
        login_payload = {
            "identity": reg_payload["username"],
            "password": reg_payload["password"],
        }
        resp = await async_client.post("/api/auth/login", json=login_payload)
        assert resp.status_code == 200, f"登录失败: {resp.text}"
        data = resp.json()
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client):
        """错误密码应返回 401。"""
        suffix = uuid.uuid4().hex[:8]
        reg_payload = {
            "email": f"wp_{suffix}@example.com",
            "username": f"wp_{suffix}",
            "nickname": "错误密码",
            "password": "CorrectPass1!",
        }
        await async_client.post("/api/auth/register", json=reg_payload)

        login_payload = {
            "identity": reg_payload["username"],
            "password": "WrongPass1!",
        }
        resp = await async_client.post("/api/auth/login", json=login_payload)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client):
        """不存在的用户应返回 401。"""
        login_payload = {
            "identity": "nonexistent_user_xyz",
            "password": "SomePass1!",
        }
        resp = await async_client.post("/api/auth/login", json=login_payload)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_by_email(self, async_client):
        """支持通过邮箱登录。"""
        suffix = uuid.uuid4().hex[:8]
        reg_payload = {
            "email": f"email_login_{suffix}@example.com",
            "username": f"emaillogin_{suffix}",
            "nickname": "邮箱登录",
            "password": "EmailPass1!",
        }
        await async_client.post("/api/auth/register", json=reg_payload)

        login_payload = {
            "identity": reg_payload["email"],
            "password": reg_payload["password"],
        }
        resp = await async_client.post("/api/auth/login", json=login_payload)
        assert resp.status_code == 200, f"邮箱登录失败: {resp.text}"


class TestAuthMiddleware:
    """测试 JWT 认证中间件。"""

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self, async_client):
        """未认证访问受保护端点返回 401。"""
        resp = await async_client.get("/api/auth/users")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, async_client):
        """无效 token 返回 401。"""
        resp = await async_client.get(
            "/api/auth/users",
            headers={"Authorization": "Bearer definitely_invalid_token"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, async_client):
        """过期 token 返回 401。"""
        import jwt

        expired_token = jwt.encode(
            {
                "sub": "00000000-0000-0000-0000-000000000000",
                "exp": 1000000000,
                "level": 5,
            },
            key="test-secret-key-for-pytest",
            algorithm="HS256",
        )
        resp = await async_client.get(
            "/api/auth/users",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_auth_succeeds(self, async_client, auth_headers):
        """有效认证可以访问受保护端点（/api/auth/me 对任何用户开放）。"""
        resp = await async_client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200


class TestLogout:
    """测试登出。"""

    @pytest.mark.asyncio
    async def test_logout_success(self, async_client, auth_headers):
        """登出应成功并让 token 失效。"""
        resp = await async_client.post("/api/auth/logout", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_no_auth(self, async_client):
        """未认证登出返回 401。"""
        resp = await async_client.post("/api/auth/logout")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_token_invalid_after_logout(self, async_client, auth_headers):
        """登出后同一个 token 不能再使用。"""
        resp = await async_client.post("/api/auth/logout", headers=auth_headers)
        assert resp.status_code == 200

        resp = await async_client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 401, "登出后 token 应失效"


class TestRefreshToken:
    """测试 Token 刷新。"""

    @pytest.mark.asyncio
    async def test_refresh_success(self, async_client):
        """使用 refresh_token 应获得新的 access_token。"""
        suffix = uuid.uuid4().hex[:8]
        reg_payload = {
            "email": f"refresh_{suffix}@example.com",
            "username": f"refresh_{suffix}",
            "nickname": "刷新测试",
            "password": "Refresh1!",
        }
        await async_client.post("/api/auth/register", json=reg_payload)

        login_resp = await async_client.post(
            "/api/auth/login",
            json={"identity": reg_payload["username"], "password": reg_payload["password"]},
        )
        refresh_token = login_resp.json()["data"]["refresh_token"]

        resp = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200, f"刷新失败: {resp.text}"
        assert "access_token" in resp.json()["data"]

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, async_client):
        """无效的 refresh_token 应返回错误。"""
        resp = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"},
        )
        assert resp.status_code == 401


class TestGetCurrentUser:
    """测试获取当前用户信息。"""

    @pytest.mark.asyncio
    async def test_me(self, async_client, auth_headers):
        """GET /api/auth/me 返回当前用户信息。"""
        resp = await async_client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # 响应格式: {"code":"ok","data":{"id":"...","email":"...","username":"...", ...}}
        assert "username" in data["data"]
        assert "email" in data["data"]

    @pytest.mark.asyncio
    async def test_me_no_auth(self, async_client):
        """未认证访问 /api/auth/me 返回 401。"""
        resp = await async_client.get("/api/auth/me")
        assert resp.status_code == 401


class TestUserManagement:
    """测试用户管理（管理员功能）。"""

    @pytest.mark.asyncio
    async def test_list_users(self, async_client, admin_headers):
        """GET /api/auth/users 返回用户列表（管理员）。"""
        resp = await async_client.get("/api/auth/users", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "list" in data["data"]
        assert len(data["data"]["list"]) >= 1

    @pytest.mark.asyncio
    async def test_list_users_forbidden_for_regular_user(self, async_client, auth_headers):
        """普通用户不能访问用户列表。"""
        resp = await async_client.get("/api/auth/users", headers=auth_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user_detail(self, async_client, admin_headers, db_session):
        """GET /api/auth/users/{id} 返回指定用户详情。"""
        from sqlalchemy import select

        from backend.plugins.auth.models import User

        result = await db_session.execute(select(User).limit(1))
        user = result.scalar_one()

        resp = await async_client.get(
            f"/api/auth/users/{user.id}", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == user.username

    @pytest.mark.asyncio
    async def test_get_user_detail_not_found(self, async_client, admin_headers):
        """不存在的用户 ID 返回 not_found。"""
        fake_id = str(uuid.uuid4())
        resp = await async_client.get(
            f"/api/auth/users/{fake_id}", headers=admin_headers
        )
        data = resp.json()
        assert data["code"] == "not_found"
