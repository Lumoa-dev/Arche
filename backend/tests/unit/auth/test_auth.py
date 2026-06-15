"""AuthService 行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现
- 用内存数据库做真实交互
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.core.middleware import AppError, AuthError
from backend.plugins.auth.services import AuthService

# =============================================================================
# 注册行为测试
# =============================================================================


class TestRegister:
    """测试用户注册行为。"""

    @pytest.mark.asyncio
    async def test_register_success_returns_user_and_tokens(self, db_container):
        """正常注册应返回用户信息和 token。"""
        service = AuthService(db_container)
        result = await service.register(
            "test@example.com", "testuser", nickname="test_user", password="password123"
        )

        assert "user" in result
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["email"] == "test@example.com"
        assert result["user"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_first_user_is_p0(self, db_container):
        """第一个注册用户自动为 P0 等级。"""
        service = AuthService(db_container)
        result = await service.register(
            "admin@example.com", "admin", nickname="test_user", password="password123"
        )
        assert result["user"]["level"] == 0

    @pytest.mark.asyncio
    async def test_second_user_is_p5(self, db_container):
        """后续注册用户默认为 P5 等级。"""
        service = AuthService(db_container)
        # 第一个用户
        await service.register(
            "admin@example.com", "admin", nickname="test_user", password="password123"
        )
        # 第二个用户
        result = await service.register(
            "user@example.com", "user", nickname="test_user", password="password123"
        )
        assert result["user"]["level"] == 5

    @pytest.mark.asyncio
    async def test_invalid_email_format_raises_error(self, db_container):
        """邮箱格式不正确应抛出错误。"""
        service = AuthService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.register(
                "not-an-email", "testuser", nickname="test_user", password="password123"
            )

        assert excinfo.value.code == "invalid_email"
        assert excinfo.value.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_email_raises_error(self, db_container):
        """空邮箱应抛出错误。"""
        service = AuthService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.register(
                "   ", "testuser", nickname="test_user", password="password123"
            )

        assert excinfo.value.code == "invalid_email"

    @pytest.mark.asyncio
    async def test_duplicate_email_raises_error(self, db_container):
        """邮箱已被使用应抛出错误。"""
        service = AuthService(db_container)
        await service.register(
            "test@example.com", "user1", nickname="test_user", password="password123"
        )

        with pytest.raises(AppError) as excinfo:
            await service.register(
                "test@example.com",
                "user2",
                nickname="test_user",
                password="password123",
            )

        assert excinfo.value.code == "email_exists"
        assert excinfo.value.status_code == 409

    @pytest.mark.asyncio
    async def test_duplicate_email_case_insensitive(self, db_container):
        """邮箱大小写不敏感，TEST@example.com 视为与 test@example.com 相同。"""
        service = AuthService(db_container)
        await service.register(
            "test@example.com", "user1", nickname="test_user", password="password123"
        )

        with pytest.raises(AppError) as excinfo:
            await service.register(
                "TEST@example.com",
                "user2",
                nickname="test_user",
                password="password123",
            )

        assert excinfo.value.code == "email_exists"

    @pytest.mark.asyncio
    async def test_duplicate_username_raises_error(self, db_container):
        """用户名已存在应抛出错误。"""
        service = AuthService(db_container)
        await service.register(
            "user1@example.com",
            "sameuser",
            nickname="test_user",
            password="password123",
        )

        with pytest.raises(AppError) as excinfo:
            await service.register(
                "user2@example.com",
                "sameuser",
                nickname="test_user",
                password="password123",
            )

        assert excinfo.value.code == "username_exists"
        assert excinfo.value.status_code == 409


# =============================================================================
# 登录行为测试
# =============================================================================


class TestLogin:
    """测试用户登录行为。"""

    @pytest.fixture
    async def test_user(self, db_container):
        """创建一个测试用户供登录测试使用。"""
        service = AuthService(db_container)
        result = await service.register(
            "login@example.com",
            "loginuser",
            nickname="test_user",
            password="password123",
        )
        return result["user"]

    @pytest.mark.asyncio
    async def test_login_with_email_success(self, db_container, test_user):
        """使用邮箱+正确密码登录成功。"""
        service = AuthService(db_container)
        result = await service.login("login@example.com", "password123")

        assert "user" in result
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["email"] == "login@example.com"

    @pytest.mark.asyncio
    async def test_login_with_username_success(self, db_container, test_user):
        """使用用户名+正确密码登录成功。"""
        service = AuthService(db_container)
        result = await service.login("loginuser", "password123")

        assert result["user"]["username"] == "loginuser"
        assert "access_token" in result

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises_error(self, db_container, test_user):
        """密码错误应抛出认证错误。"""
        service = AuthService(db_container)

        with pytest.raises(AuthError) as excinfo:
            await service.login("login@example.com", "wrongpassword")

        assert "密码错误" in str(excinfo.value) or "错误" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_login_user_not_found_raises_error(self, db_container):
        """用户不存在应抛出认证错误。"""
        service = AuthService(db_container)

        with pytest.raises(AuthError) as excinfo:
            await service.login("notfound@example.com", "password123")

        assert "不存在" in str(excinfo.value) or "错误" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_login_disabled_user_raises_error(self, db_container, test_user):
        """被禁用的用户登录应抛出错误。"""
        service = AuthService(db_container)

        # 禁用用户
        user_id = uuid.UUID(test_user["id"])
        await service.disable_user(user_id)

        with pytest.raises(AuthError) as excinfo:
            await service.login("login@example.com", "password123")

        assert "禁用" in str(excinfo.value)


# =============================================================================
# Token 行为测试
# =============================================================================


class TestToken:
    """测试 Token 行为。"""

    @pytest.fixture
    async def test_user_tokens(self, db_container):
        """创建测试用户并获取 token。"""
        service = AuthService(db_container)
        result = await service.register(
            "token@example.com",
            "tokenuser",
            nickname="test_user",
            password="password123",
        )
        return result

    @pytest.mark.asyncio
    async def test_access_token_contains_correct_payload(
        self, db_container, test_user_tokens
    ):
        """access token 应包含正确的用户信息。"""
        service = AuthService(db_container)
        token = test_user_tokens["access_token"]

        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])

        assert payload["email"] == "token@example.com"
        assert payload["username"] == "tokenuser"
        assert payload["level"] == 0  # 第一个用户是 P0
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_refresh_token_returns_new_access_token(
        self, db_container, test_user_tokens
    ):
        """使用 refresh token 应能刷新出新的 access token。"""
        service = AuthService(db_container)
        refresh_token = test_user_tokens["refresh_token"]

        result = await service.refresh_token(refresh_token)

        assert "access_token" in result
        assert result["access_token"] != test_user_tokens["access_token"]

    @pytest.mark.asyncio
    async def test_expired_token_raises_error(self, db_container, test_user_tokens):
        """过期 token 应抛出错误。"""
        service = AuthService(db_container)

        # 创建一个已过期的 token
        expired_payload = {
            "sub": test_user_tokens["user"]["id"],
            "email": test_user_tokens["user"]["email"],
            "username": test_user_tokens["user"]["username"],
            "level": test_user_tokens["user"]["level"],
            "blog_quality_level": test_user_tokens["user"]["blog_quality_level"],
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload, service.secret_key, algorithm="HS256"
        )

        with pytest.raises(AuthError) as excinfo:
            service._verify_token(expired_token)

        assert "过期" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_invalid_token_raises_error(self, db_container):
        """无效 token 应抛出错误。"""
        service = AuthService(db_container)

        with pytest.raises(AuthError) as excinfo:
            service._verify_token("not.a.valid.token")

        assert "无效" in str(excinfo.value)


# =============================================================================
# 用户管理行为测试
# =============================================================================


class TestUserManagement:
    """测试用户管理行为。"""

    @pytest.fixture
    async def test_users(self, db_container):
        """创建多个测试用户。"""
        service = AuthService(db_container)
        users = []
        for i in range(5):
            result = await service.register(
                f"user{i}@example.com",
                f"user{i}",
                nickname="test_user",
                password="password123",
            )
            users.append(result["user"])
        return users

    @pytest.mark.asyncio
    async def test_list_users_returns_paginated_results(self, db_container, test_users):
        """用户列表应返回分页结果。"""
        service = AuthService(db_container)
        result = await service.list_users(page=1, page_size=10)

        assert "list" in result
        assert "total" in result
        assert result["total"] == 5
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert len(result["list"]) == 5

    @pytest.mark.asyncio
    async def test_list_users_pagination_works(self, db_container, test_users):
        """分页功能应正确工作。"""
        service = AuthService(db_container)

        # 第一页
        page1 = await service.list_users(page=1, page_size=2)
        assert len(page1["list"]) == 2

        # 第二页
        page2 = await service.list_users(page=2, page_size=2)
        assert len(page2["list"]) == 2

        # 第三页（剩余）
        page3 = await service.list_users(page=3, page_size=2)
        assert len(page3["list"]) == 1

    @pytest.mark.asyncio
    async def test_list_users_active_filter(self, db_container, test_users):
        """状态筛选应正确工作。"""
        service = AuthService(db_container)

        # 禁用一个用户
        await service.disable_user(uuid.UUID(test_users[0]["id"]))

        # 筛选活跃用户
        active = await service.list_users(status_filter="active")
        assert active["total"] == 4

        # 筛选禁用用户
        disabled = await service.list_users(status_filter="disabled")
        assert disabled["total"] == 1

    @pytest.mark.asyncio
    async def test_get_user_by_id_returns_correct_user(self, db_container, test_users):
        """按 ID 获取用户应返回正确信息。"""
        service = AuthService(db_container)
        target_user = test_users[2]

        result = await service.get_user(uuid.UUID(target_user["id"]))

        assert result is not None
        assert result["id"] == target_user["id"]
        assert result["email"] == target_user["email"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_none(self, db_container):
        """获取不存在的用户返回 None。"""
        service = AuthService(db_container)
        fake_id = uuid.uuid4()

        result = await service.get_user(fake_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_level(self, db_container, test_users):
        """修改用户等级应正确生效。"""
        service = AuthService(db_container)
        user = test_users[1]

        result = await service.update_user(uuid.UUID(user["id"]), level=3)

        assert result["level"] == 3

    @pytest.mark.asyncio
    async def test_disable_user_sets_is_active_false(self, db_container, test_users):
        """禁用用户应设置 is_active 为 False。"""
        service = AuthService(db_container)
        user = test_users[1]

        result = await service.disable_user(uuid.UUID(user["id"]))

        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_enable_user_sets_is_active_true(self, db_container, test_users):
        """启用用户应设置 is_active 为 True。"""
        service = AuthService(db_container)
        user = test_users[1]

        # 先禁用
        await service.disable_user(uuid.UUID(user["id"]))

        # 再启用
        result = await service.enable_user(uuid.UUID(user["id"]))

        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_user_raises_error(self, db_container):
        """修改不存在的用户应抛出错误。"""
        service = AuthService(db_container)
        fake_id = uuid.uuid4()

        with pytest.raises(AppError) as excinfo:
            await service.update_user(fake_id, level=3)

        assert excinfo.value.code == "user_not_found"


# =============================================================================
# 管理员创建用户测试
# =============================================================================


class TestAdminCreateUser:
    """测试管理员创建用户行为。"""

    @pytest.mark.asyncio
    async def test_admin_create_user_success(self, db_container):
        """管理员创建用户应成功。"""
        service = AuthService(db_container)
        result = await service.admin_create_user(
            "admin@example.com",
            "adminuser",
            nickname="test_user",
            password="password123",
        )

        assert result["email"] == "admin@example.com"
        assert result["username"] == "adminuser"
        assert result["level"] == 5  # 默认为 P5

    @pytest.mark.asyncio
    async def test_admin_create_user_with_custom_level(self, db_container):
        """管理员创建用户可以指定等级。"""
        service = AuthService(db_container)
        result = await service.admin_create_user(
            "admin@example.com",
            "adminuser",
            nickname="test_user",
            password="password123",
            level=1,
        )

        assert result["level"] == 1

    @pytest.mark.asyncio
    async def test_admin_create_user_first_not_p0(self, db_container):
        """管理员创建的第一个用户不会自动变成 P0。"""
        service = AuthService(db_container)
        result = await service.admin_create_user(
            "admin@example.com",
            "adminuser",
            nickname="test_user",
            password="password123",
        )

        assert result["level"] == 5  # 不是 P0
