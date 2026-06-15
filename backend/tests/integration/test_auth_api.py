"""Auth 模块 API 集成测试。

测试真实 HTTP 请求-响应链路（HTTP → 中间件 → AuthService → 真实数据库）。
不 mock AuthService，使用真实 DB。

覆盖：
- 注册 / 登录 / 获取用户信息 / 刷新 token / 登出 全链路
- 管理员创建用户、列出用户、封禁/解封用户
- 鉴权失败（401/403）边界
"""

from __future__ import annotations

import pytest

from backend.plugins.auth.services import AuthService
from backend.tests.conftest import patch_container_service


@pytest.fixture(autouse=True)
def real_auth_service(db_container):
    """用真实 AuthService 替换容器中的 mock 服务。

    确保注册/登录等路由通过 HTTP 调用时使用真实数据库。
    """
    auth_service = AuthService(db_container)
    patch_container_service(db_container, "auth", auth_service)
    # session_tracker 需要 mock，避免异步清理任务干扰
    from unittest.mock import AsyncMock

    patch_container_service(db_container, "session_tracker", AsyncMock())


@pytest.mark.asyncio
class TestRegisterAPI:
    """注册接口测试。"""

    async def test_register_success_returns_tokens(self, client):
        """注册成功应返回 access_token、refresh_token 和用户信息。"""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "password123",
                "nickname": "testuser",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        user_data = data["data"]
        assert "access_token" in user_data
        assert "refresh_token" in user_data
        assert user_data["user"]["email"] == "newuser@example.com"
        assert user_data["user"]["username"] == "newuser"

    async def test_register_first_user_is_p0(self, client):
        """第一个注册用户应为 P0（管理员）。"""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "first@example.com",
                "username": "firstuser",
                "password": "password123",
                "nickname": "testuser",
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["user"]["level"] == 0

    async def test_register_second_user_is_p5(self, client):
        """后续注册用户默认应为 P5。"""
        await client.post(
            "/api/auth/register",
            json={
                "email": "admin2@example.com",
                "username": "admin2",
                "password": "password123",
                "nickname": "testuser",
            },
        )
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "normal@example.com",
                "username": "normaluser",
                "password": "password123",
                "nickname": "testuser",
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["user"]["level"] == 5

    async def test_register_duplicate_email_returns_409(self, client):
        """重复邮箱注册应返回 409。"""
        await client.post(
            "/api/auth/register",
            json={
                "email": "dupe@example.com",
                "username": "user1",
                "password": "password123",
                "nickname": "testuser",
            },
        )
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "dupe@example.com",
                "username": "user2",
                "password": "password123",
                "nickname": "testuser2",
            },
        )
        assert response.status_code == 409
        assert response.json()["code"] == "email_exists"

    async def test_register_invalid_email_format_returns_400(self, client):
        """邮箱格式错误应返回 400。"""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "username": "testuser",
                "password": "password123",
                "nickname": "testuser",
            },
        )
        assert response.status_code == 400


@pytest.mark.asyncio
class TestLoginAPI:
    """登录接口测试。"""

    async def _register_user(self, client, email: str, username: str, password: str):
        """辅助函数：注册用户并返回响应。"""
        return await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "username": username,
                "password": password,
                "nickname": "testuser",
            },
        )

    async def test_login_with_email_success(self, client):
        """使用邮箱登录成功。"""
        await self._register_user(
            client, "login@example.com", "loginuser", "testpass123"
        )
        response = await client.post(
            "/api/auth/login",
            json={"identity": "login@example.com", "password": "testpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert "access_token" in data["data"]
        assert data["data"]["user"]["email"] == "login@example.com"

    async def test_login_with_username_success(self, client):
        """使用用户名登录成功。"""
        await self._register_user(
            client, "login2@example.com", "loginuser2", "testpass123"
        )
        response = await client.post(
            "/api/auth/login",
            json={"identity": "loginuser2", "password": "testpass123"},
        )
        assert response.status_code == 200

    async def test_login_wrong_password_returns_401(self, client):
        """密码错误返回 401。"""
        await self._register_user(
            client, "wrongpass@example.com", "wrongpassuser", "correctpass"
        )
        response = await client.post(
            "/api/auth/login",
            json={"identity": "wrongpassuser", "password": "wrongpass"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user_returns_401(self, client):
        """不存在的用户返回 401。"""
        response = await client.post(
            "/api/auth/login",
            json={"identity": "nobody@example.com", "password": "whatever"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestMeAndRefreshAPI:
    """获取用户信息和刷新 token 测试。"""

    async def test_get_me_with_valid_token(self, client, auth_headers):
        """带有效 token 获取当前用户信息。"""
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["email"] == "test@example.com"

    async def test_get_me_without_token_returns_401(self, client):
        """未带 token 访问受保护接口返回 401。"""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_get_me_with_invalid_token_returns_401(self, client):
        """无效 token 返回 401。"""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )
        assert response.status_code == 401

    async def test_refresh_token_success(self, client, db_container):
        """使用 refresh token 换取新的 access token。"""
        from backend.plugins.auth.services import AuthService

        # 先注册一个用户获取 refresh token
        svc = AuthService(db_container)
        result = await svc.register(
            email="refreshme@example.com",
            username="refreshuser",
            nickname="test_user",
            password="password123",
        )
        refresh_token = result["refresh_token"]
        assert refresh_token

        # 通过 HTTP 刷新
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()["data"]

    async def test_refresh_with_invalid_token_returns_401(self, client):
        """无效 refresh token 返回 401。"""
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"},
        )
        assert response.status_code == 401

    async def test_logout_success(self, client, auth_headers):
        """登出成功。"""
        response = await client.post("/api/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["code"] == "ok"


@pytest.mark.asyncio
class TestUserManagementAPI:
    """用户管理接口测试（管理员权限）。"""

    async def test_list_users_requires_admin(self, client, auth_headers):
        """普通用户（P5）不能列出所有用户。"""
        response = await client.get("/api/auth/users", headers=auth_headers)
        assert response.status_code == 403

    async def test_admin_list_users(self, client, admin_headers):
        """管理员可以列出用户。"""
        response = await client.get("/api/auth/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        # list_users 返回 {"list": [...], "total": ..., ...}
        assert len(data["data"]["list"]) >= 1

    async def test_admin_create_user(self, client, admin_headers):
        """管理员可以创建指定等级的用户。"""
        response = await client.post(
            "/api/auth/admin/users",
            json={
                "email": "createdbyadmin@example.com",
                "username": "admincreated",
                "password": "password123",
                "nickname": "admincreated",
                "level": 3,
            },
            headers=admin_headers,
        )
        assert response.status_code == 200
        # admin_create_user 返回 user dict（_user_to_dict）
        assert response.json()["data"]["level"] == 3

    async def test_disable_and_enable_user(self, client, admin_headers, db_container):
        """管理员可以封禁/解封用户。"""
        # 先创建一个待操作的用户
        from backend.plugins.auth.services import AuthService

        svc = AuthService(db_container)
        user_result = await svc.register(
            email="target@example.com",
            username="targetuser",
            nickname="test_user",
            password="password123",
        )
        target_user_id = user_result["user"]["id"]

        # 封禁
        disable_resp = await client.post(
            f"/api/auth/users/{target_user_id}/disable",
            headers=admin_headers,
        )
        assert disable_resp.status_code == 200

        # 验证该用户无法登录
        login_resp = await client.post(
            "/api/auth/login",
            json={"identity": "target@example.com", "password": "password123"},
        )
        assert login_resp.status_code == 401

        # 解封
        enable_resp = await client.post(
            f"/api/auth/users/{target_user_id}/enable",
            headers=admin_headers,
        )
        assert enable_resp.status_code == 200

        # 验证可以重新登录
        login_resp2 = await client.post(
            "/api/auth/login",
            json={"identity": "target@example.com", "password": "password123"},
        )
        assert login_resp2.status_code == 200

    async def test_get_non_existent_user_returns_not_found(self, client, admin_headers):
        """获取不存在的用户返回 not_found。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/auth/users/{fake_id}",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["code"] == "not_found"
