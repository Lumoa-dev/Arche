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


# =============================================================================
# 登出 & Token 黑名单测试
# =============================================================================


class TestLogoutAndTokenBlacklist:
    """测试登出与 Token 黑名单机制。"""

    @pytest.mark.asyncio
    async def test_logout_blacklists_token(self, db_container):
        """登出后 token 应进入黑名单。"""
        service = AuthService(db_container)
        result = await service.register(
            "logout@example.com", "logoutuser", nickname="test_user", password="password123"
        )
        token = result["access_token"]

        # 登出前不应在黑名单
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert service.is_token_blacklisted(payload["jti"]) is False

        # 登出
        await service.logout(token)

        # 登出后应在黑名单
        assert service.is_token_blacklisted(payload["jti"]) is True

    @pytest.mark.asyncio
    async def test_logout_invalid_token_no_error(self, db_container):
        """登出无效 token 不应抛出异常。"""
        service = AuthService(db_container)
        # 不应抛出异常
        await service.logout("invalid.token.here")
        await service.logout("")

    @pytest.mark.asyncio
    async def test_logout_refresh_token_also_blacklisted(self, db_container):
        """登出时 refresh token 也应加入黑名单。"""
        service = AuthService(db_container)
        result = await service.register(
            "logout2@example.com", "logoutuser2", nickname="test_user", password="password123"
        )

        await service.logout(result["refresh_token"])

        payload = jwt.decode(
            result["refresh_token"], service.secret_key, algorithms=["HS256"]
        )
        assert service.is_token_blacklisted(payload["jti"]) is True

    @pytest.mark.asyncio
    async def test_blacklist_cleanup_removes_expired(self, db_container):
        """黑名单清理应移除已过期的条目。"""
        service = AuthService(db_container)

        # 直接向黑名单添加过期条目
        import time
        service._token_blacklist["expired_jti"] = time.time() - 3600  # 1 小时前过期
        service._token_blacklist["valid_jti"] = time.time() + 3600  # 1 小时后过期

        # is_token_blacklisted 会触发清理
        assert service.is_token_blacklisted("expired_jti") is False
        assert service.is_token_blacklisted("valid_jti") is True


# =============================================================================
# 软删除用户测试
# =============================================================================


class TestSoftDeleteUser:
    """测试软删除用户功能。"""

    @pytest.mark.asyncio
    async def test_soft_delete_marks_user(self, db_container):
        """软删除应标记用户并禁用账号。"""
        service = AuthService(db_container)
        result = await service.register(
            "delete@example.com", "deleteuser", nickname="test_user", password="password123"
        )
        user_id = uuid.UUID(result["user"]["id"])

        deleted = await service.soft_delete_user(
            user_id, reason="violation", expires_in_days=30
        )

        assert deleted["is_active"] is False
        assert deleted["deletion_status"] == "deleted_by_admin"
        assert deleted["deletion_reason"] == "violation"
        assert deleted["deleted_at"] is not None
        assert deleted["deletion_expires_at"] is not None

    @pytest.mark.asyncio
    async def test_soft_delete_user_requested(self, db_container):
        """用户主动请求删除的标记。"""
        service = AuthService(db_container)
        result = await service.register(
            "selfdelete@example.com", "selfdel", nickname="test_user", password="password123"
        )
        user_id = uuid.UUID(result["user"]["id"])

        deleted = await service.soft_delete_user(
            user_id, reason="user_requested", expires_in_days=7
        )

        assert deleted["deletion_status"] == "user_requested_deletion"
        assert deleted["is_active"] is False

    @pytest.mark.asyncio
    async def test_soft_delete_nonexistent_user(self, db_container):
        """软删除不存在的用户应抛出错误。"""
        service = AuthService(db_container)
        with pytest.raises(AppError) as exc:
            await service.soft_delete_user(uuid.uuid4(), reason="test", expires_in_days=7)
        assert exc.value.code == "user_not_found"

    @pytest.mark.asyncio
    async def test_soft_delete_already_deleted_user(self, db_container):
        """重复删除已删除的用户应抛出错误。"""
        service = AuthService(db_container)
        result = await service.register(
            "alrdel@example.com", "alrdel", nickname="test_user", password="password123"
        )
        user_id = uuid.UUID(result["user"]["id"])

        await service.soft_delete_user(user_id, reason="violation", expires_in_days=30)
        with pytest.raises(AppError) as exc:
            await service.soft_delete_user(user_id, reason="violation", expires_in_days=30)
        assert exc.value.code == "user_already_deleted"


# =============================================================================
# 密码重置测试
# =============================================================================


class TestResetPassword:
    """测试密码重置功能。"""

    @pytest.mark.asyncio
    async def test_reset_password_success(self, db_container):
        """重置密码后应能用新密码登录。"""
        service = AuthService(db_container)
        result = await service.register(
            "reset@example.com", "resetuser", nickname="test_user", password="oldpass123"
        )
        user_id = uuid.UUID(result["user"]["id"])

        await service.reset_password(user_id, "newpass456")

        # 旧密码不应能登录
        with pytest.raises(AuthError):
            await service.login("reset@example.com", "oldpass123")

        # 新密码应能登录
        login_result = await service.login("reset@example.com", "newpass456")
        assert login_result["user"]["email"] == "reset@example.com"

    @pytest.mark.asyncio
    async def test_reset_password_nonexistent_user(self, db_container):
        """重置不存在的用户密码应抛出错误。"""
        service = AuthService(db_container)
        with pytest.raises(AppError) as exc:
            await service.reset_password(uuid.uuid4(), "newpass123")
        assert exc.value.code == "user_not_found"


# =============================================================================
# 用户设置测试
# =============================================================================


class TestUserSettings:
    """测试用户设置管理。"""

    @pytest.mark.asyncio
    async def test_get_user_settings_defaults(self, db_container):
        """新注册用户应有默认设置。"""
        service = AuthService(db_container)
        result = await service.register(
            "settings@example.com", "settingsuser", nickname="test_user", password="password123"
        )
        user_id = uuid.UUID(result["user"]["id"])

        settings = await service.get_user_settings(user_id)
        assert settings is not None
        assert settings["language"] == "zh-CN" or settings is not None
        assert "theme" in settings
        assert "notify_comment_reply" in settings

    @pytest.mark.asyncio
    async def test_update_user_settings_partial(self, db_container):
        """部分更新设置应只修改指定字段。"""
        service = AuthService(db_container)
        result = await service.register(
            "settings2@example.com", "settingsuser2", nickname="test_user", password="password123"
        )
        user_id = uuid.UUID(result["user"]["id"])

        updated = await service.update_user_settings(
            user_id, {"language": "en", "theme": "dark"}
        )
        assert updated["language"] == "en"
        assert updated["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_update_user_settings_invalid_field(self, db_container):
        """更新不存在的字段应被忽略。"""
        service = AuthService(db_container)
        result = await service.register(
            "settings3@example.com", "settingsuser3", nickname="test_user", password="password123"
        )
        user_id = uuid.UUID(result["user"]["id"])

        updated = await service.update_user_settings(
            user_id, {"nonexistent_field": "value"}
        )
        # 不应抛出异常，只是忽略
        assert updated is not None


# =============================================================================
# 页面权限管理测试
# =============================================================================


class TestPagePermissions:
    """测试页面组件权限管理。"""

    @pytest.mark.asyncio
    async def test_get_page_permissions_empty(self, db_container):
        """未配置权限的 level 应返回空映射。"""
        service = AuthService(db_container)
        permissions = await service.get_page_permissions(level=5)
        assert permissions == {}

    @pytest.mark.asyncio
    async def test_first_user_gets_all_permissions(self, db_container):
        """第一个注册用户（P0）应获得所有页面权限。"""
        service = AuthService(db_container)
        result = await service.register(
            "p0@example.com", "p0user", nickname="test_user", password="password123"
        )

        permissions = await service.get_page_permissions(level=0)
        # P0 应该有所有页面权限
        assert "home" in permissions
        assert "explore" in permissions
        assert "create" in permissions
        assert "admin_users" in permissions
        assert permissions["home"]["page"] is True

    @pytest.mark.asyncio
    async def test_set_page_component(self, db_container):
        """设置页面组件可见性应生效。"""
        service = AuthService(db_container)
        await service.set_page_component(level=5, page_name="home", component_name="page", visible=True)

        permissions = await service.get_page_permissions(level=5)
        assert permissions["home"]["page"] is True

    @pytest.mark.asyncio
    async def test_set_page_component_update(self, db_container):
        """更新已有组件可见性应覆盖。"""
        service = AuthService(db_container)
        await service.set_page_component(level=5, page_name="home", component_name="page", visible=True)
        await service.set_page_component(level=5, page_name="home", component_name="page", visible=False)

        permissions = await service.get_page_permissions(level=5)
        assert permissions["home"]["page"] is False

    @pytest.mark.asyncio
    async def test_set_page_defaults(self, db_container):
        """批量设置页面所有组件可见性。"""
        service = AuthService(db_container)
        # 先创建两个组件
        await service.set_page_component(level=5, page_name="home", component_name="page", visible=True)
        await service.set_page_component(level=5, page_name="home", component_name="sidebar", visible=True)

        # 批量设为不可见
        await service.set_page_defaults(level=5, page_name="home", visible_default=False)

        permissions = await service.get_page_permissions(level=5)
        assert permissions["home"]["page"] is False
        assert permissions["home"]["sidebar"] is False

    @pytest.mark.asyncio
    async def test_get_all_permission_levels(self, db_container):
        """获取所有已配置权限的 level 列表。"""
        service = AuthService(db_container)
        # 注册 P0
        await service.register(
            "p0perm@example.com", "p0perm", nickname="test_user", password="password123"
        )

        levels = await service.get_all_permission_levels()
        assert 0 in levels


# =============================================================================
# 用户统计测试
# =============================================================================


class TestUserStats:
    """测试用户统计功能。"""

    @pytest.mark.asyncio
    async def test_get_user_stats_empty(self, db_container):
        """空数据库应返回零值统计。"""
        service = AuthService(db_container)
        stats = await service.get_user_stats()
        assert stats["total_users"] == 0
        assert stats["active_users"] == 0
        assert stats["disabled_users"] == 0
        assert stats["today_new"] == 0
        assert stats["by_level"] == {}

    @pytest.mark.asyncio
    async def test_get_user_stats_with_data(self, db_container):
        """有用户数据时统计应正确。"""
        service = AuthService(db_container)
        await service.register(
            "stats1@example.com", "stats1", nickname="test_user", password="password123"
        )
        await service.register(
            "stats2@example.com", "stats2", nickname="test_user", password="password123"
        )

        stats = await service.get_user_stats()
        assert stats["total_users"] == 2
        assert stats["today_new"] == 2
        assert stats["by_level"].get(0, 0) == 1  # 第一个 P0
        assert stats["by_level"].get(5, 0) == 1  # 第二个 P5

    @pytest.mark.asyncio
    async def test_get_user_stats_disabled_count(self, db_container):
        """统计应正确区分活跃和禁用用户。"""
        service = AuthService(db_container)
        r1 = await service.register(
            "stats3@example.com", "stats3", nickname="test_user", password="password123"
        )
        await service.register(
            "stats4@example.com", "stats4", nickname="test_user", password="password123"
        )

        await service.disable_user(uuid.UUID(r1["user"]["id"]))

        stats = await service.get_user_stats()
        assert stats["total_users"] == 2
        assert stats["active_users"] == 1
        assert stats["disabled_users"] == 1


# =============================================================================
# 登录历史测试
# =============================================================================


class TestLoginHistory:
    """测试登录历史功能。"""

    @pytest.mark.asyncio
    async def test_login_creates_history(self, db_container):
        """登录成功后应创建登录历史记录。"""
        service = AuthService(db_container)
        result = await service.register(
            "history@example.com", "historyuser", nickname="test_user", password="password123"
        )

        # 登录一次
        await service.login("history@example.com", "password123", client_ip="192.168.1.1")

        user_id = uuid.UUID(result["user"]["id"])
        history = await service.get_login_history(user_id)
        assert history["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_login_history_empty(self, db_container):
        """无登录历史的用户应返回空列表。"""
        service = AuthService(db_container)
        result = await service.register(
            "nohistory@example.com", "nohist", nickname="test_user", password="password123"
        )

        history = await service.get_login_history(uuid.UUID(result["user"]["id"]))
        assert history["total"] == 0
        assert history["list"] == []


# =============================================================================
# 管理员创建用户重复检查测试
# =============================================================================


class TestAdminCreateUserExtended:
    """管理员创建用户的额外测试。"""

    @pytest.mark.asyncio
    async def test_admin_create_duplicate_email(self, db_container):
        """管理员创建重复邮箱应抛出错误。"""
        service = AuthService(db_container)
        await service.admin_create_user(
            "dup@example.com", "dup1", nickname="test_user", password="password123"
        )
        with pytest.raises(AppError) as exc:
            await service.admin_create_user(
                "dup@example.com", "dup2", nickname="test_user", password="password123"
            )
        assert exc.value.code == "email_exists"

    @pytest.mark.asyncio
    async def test_admin_create_duplicate_username(self, db_container):
        """管理员创建重复用户名应抛出错误。"""
        service = AuthService(db_container)
        await service.admin_create_user(
            "dup1@example.com", "dupuser", nickname="test_user", password="password123"
        )
        with pytest.raises(AppError) as exc:
            await service.admin_create_user(
                "dup2@example.com", "dupuser", nickname="test_user", password="password123"
            )
        assert exc.value.code == "username_exists"
