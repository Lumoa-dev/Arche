"""AuthService 未覆盖方法的行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现
- 用内存数据库做真实交互
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import jwt
import pytest

from backend.core.middleware import AppError
from backend.plugins.auth.models import PageComponentPermission
from backend.plugins.auth.services import AuthService

# =============================================================================
# Token 黑名单行为测试
# =============================================================================


class TestTokenBlacklist:
    """测试 Token 黑名单行为。"""

    @pytest.fixture
    async def user_and_tokens(self, db_container):
        """创建测试用户并返回 token。"""
        service = AuthService(db_container)
        result = await service.register(
            "blacklist@example.com",
            "blacklistuser",
            nickname="test_user",
            password="password123",
        )
        return result

    @pytest.mark.asyncio
    async def test_logout_blacklists_token(self, db_container, user_and_tokens):
        """logout() 应将 token 的 jti 加入黑名单。"""
        service = AuthService(db_container)
        token = user_and_tokens["access_token"]

        # 登出前 jti 不在黑名单
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        jti = payload["jti"]
        assert not service.is_token_blacklisted(jti)

        # 执行登出
        await service.logout(token)

        # 登出后 jti 应在黑名单中
        assert service.is_token_blacklisted(jti)

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self, db_container, user_and_tokens):
        """is_token_blacklisted() 对已拉黑的 jti 返回 True。"""
        service = AuthService(db_container)
        token = user_and_tokens["access_token"]

        await service.logout(token)
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])

        assert service.is_token_blacklisted(payload["jti"]) is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self, db_container):
        """is_token_blacklisted() 对未拉黑的 jti 返回 False。"""
        service = AuthService(db_container)

        # 使用一个从未被拉黑的随机 jti
        assert service.is_token_blacklisted("nonexistent-jti") is False

    @pytest.mark.asyncio
    async def test_cleanup_blacklist_removes_expired(self, db_container):
        """_cleanup_blacklist() 应移除已过期的黑名单条目。"""
        service = AuthService(db_container)
        now = datetime.now(timezone.utc).timestamp()

        # 手动加入已过期和未过期的条目
        service._token_blacklist["expired-jti"] = now - 3600  # 1 小时前过期
        service._token_blacklist["valid-jti"] = now + 3600   # 1 小时后过期

        # 执行清理
        service._cleanup_blacklist()

        # 过期的应被移除，未过期的应保留
        assert "expired-jti" not in service._token_blacklist
        assert "valid-jti" in service._token_blacklist

    @pytest.mark.asyncio
    async def test_logout_invalid_token_does_not_raise(self, db_container):
        """logout() 接无效 token 不应抛出异常。"""
        service = AuthService(db_container)

        # 各种无效 token 都不应抛异常
        await service.logout("invalid-token")
        await service.logout("")
        await service.logout("eyJ.eyJ.Z30")


# =============================================================================
# 用户设置行为测试
# =============================================================================


class TestUserSettings:
    """测试用户设置行为。"""

    @pytest.fixture
    async def test_user(self, db_container):
        """创建测试用户。"""
        service = AuthService(db_container)
        result = await service.register(
            "settings@example.com",
            "settingsuser",
            nickname="test_user",
            password="password123",
        )
        return result["user"]

    @pytest.mark.asyncio
    async def test_get_user_settings_returns_settings(
        self, db_container, test_user,
    ):
        """get_user_settings() 应返回存在的用户设置。"""
        service = AuthService(db_container)
        user_id = uuid.UUID(test_user["id"])

        settings = await service.get_user_settings(user_id)

        assert settings is not None
        assert settings["language"] == "zh-CN"
        assert settings["theme"] == "auto"
        assert settings["default_post_permission"] == "public"
        assert settings["notify_comment_reply"] is True
        assert settings["notify_like"] is True
        assert settings["notify_system"] is True
        assert settings["privacy_show_online"] is True
        assert settings["privacy_show_login_history"] is False
        assert settings["privacy_show_badges"] is True
        assert settings["default_post_status"] == "draft"
        assert settings["auto_save_interval"] == 30
        assert settings["extras"] is None

    @pytest.mark.asyncio
    async def test_get_user_settings_returns_none(self, db_container):
        """get_user_settings() 对不存在的用户返回 None。"""
        service = AuthService(db_container)
        fake_id = uuid.uuid4()

        settings = await service.get_user_settings(fake_id)

        assert settings is None

    @pytest.mark.asyncio
    async def test_update_user_settings(self, db_container, test_user):
        """update_user_settings() 应更新允许修改的字段。"""
        service = AuthService(db_container)
        user_id = uuid.UUID(test_user["id"])

        updates = {
            "language": "en-US",
            "theme": "dark",
            "notify_comment_reply": False,
            "privacy_show_online": False,
            "default_post_status": "public",
            "auto_save_interval": 60,
        }
        result = await service.update_user_settings(user_id, updates)

        assert result["language"] == "en-US"
        assert result["theme"] == "dark"
        assert result["notify_comment_reply"] is False
        assert result["privacy_show_online"] is False
        assert result["default_post_status"] == "public"
        assert result["auto_save_interval"] == 60

    @pytest.mark.asyncio
    async def test_update_user_settings_ignores_unknown_fields(
        self, db_container, test_user,
    ):
        """update_user_settings() 应忽略不在 allowed_fields 中的字段。"""
        service = AuthService(db_container)
        user_id = uuid.UUID(test_user["id"])

        updates = {
            "language": "en-US",
            "nonexistent_field": "should_be_ignored",
            "another_bad_key": 123,
        }
        result = await service.update_user_settings(user_id, updates)

        # 合法字段应更新
        assert result["language"] == "en-US"
        # 不存在的字段不应影响结果
        assert "nonexistent_field" not in result

    @pytest.mark.asyncio
    async def test_update_user_settings_not_found(self, db_container):
        """update_user_settings() 对不存在的用户应抛出 404。"""
        service = AuthService(db_container)
        fake_id = uuid.uuid4()

        with pytest.raises(AppError) as excinfo:
            await service.update_user_settings(fake_id, {"language": "en-US"})

        assert excinfo.value.code == "settings_not_found"
        assert excinfo.value.status_code == 404


# =============================================================================
# 登录历史行为测试
# =============================================================================


class TestLoginHistory:
    """测试登录历史行为。"""

    @pytest.mark.asyncio
    async def test_get_login_history(self, db_container):
        """get_login_history() 应返回分页的登录记录列表。"""
        service = AuthService(db_container)

        # 注册用户并多次登录以产生历史记录
        await service.register(
            "history@example.com",
            "historyuser",
            nickname="test_user",
            password="password123",
        )
        # 先登录一次获取 user_id
        login_result = await service.login("history@example.com", "password123")
        user_id = uuid.UUID(login_result["user"]["id"])

        # 再多次登录以产生更多历史记录
        for _ in range(3):
            await service.login("history@example.com", "password123")

        # 获取登录历史
        result = await service.get_login_history(user_id, page=1, page_size=10)

        assert "list" in result
        assert "total" in result
        assert "page" in result
        assert "page_size" in result
        assert result["total"] >= 4  # 至少 4 次登录
        assert result["page"] == 1
        assert result["page_size"] == 10
        # 验证返回的记录结构
        if result["list"]:
            record = result["list"][0]
            assert "id" in record
            assert "ip" in record
            assert "login_at" in record


# =============================================================================
# 用户管理缺口行为测试
# =============================================================================


class TestUserManagementGaps:
    """测试用户管理中尚未覆盖的方法。"""

    @pytest.fixture
    async def test_user(self, db_container):
        """创建测试用户。"""
        service = AuthService(db_container)
        result = await service.register(
            "mgmt@example.com",
            "mgmtuser",
            nickname="test_user",
            password="password123",
        )
        return result["user"]

    @pytest.mark.asyncio
    async def test_soft_delete_user(self, db_container, test_user):
        """soft_delete_user() 应将用户标记为已删除。"""
        service = AuthService(db_container)
        user_id = uuid.UUID(test_user["id"])

        result = await service.soft_delete_user(
            user_id, reason="violation", expires_in_days=30,
        )

        assert result["is_active"] is False
        assert result["deletion_status"] == "deleted_by_admin"
        assert result["deletion_reason"] == "violation"
        assert result["deletion_expires_at"] is not None
        assert result["deleted_at"] is not None

    @pytest.mark.asyncio
    async def test_soft_delete_already_deleted_raises(self, db_container, test_user):
        """对已软删除的用户再次软删除应抛出 409。"""
        service = AuthService(db_container)
        user_id = uuid.UUID(test_user["id"])

        await service.soft_delete_user(user_id, reason="violation", expires_in_days=30)

        with pytest.raises(AppError) as excinfo:
            await service.soft_delete_user(
                user_id, reason="user_request", expires_in_days=7,
            )

        assert excinfo.value.code == "user_already_deleted"
        assert excinfo.value.status_code == 409

    @pytest.mark.asyncio
    async def test_reset_password(self, db_container, test_user):
        """reset_password() 应更改密码哈希值。"""
        service = AuthService(db_container)
        user_id = uuid.UUID(test_user["id"])
        old_password = "password123"
        new_password = "newpassword456"

        # 确认旧密码可用
        old_login = await service.login("mgmt@example.com", old_password)
        assert old_login is not None

        # 重置密码
        result = await service.reset_password(user_id, new_password)

        assert result["id"] == test_user["id"]

        # 验证新密码可用
        new_login = await service.login("mgmt@example.com", new_password)
        assert new_login is not None

        # 验证旧密码不可用
        with pytest.raises(Exception):
            await service.login("mgmt@example.com", old_password)

    @pytest.mark.asyncio
    async def test_get_user_stats(self, db_container):
        """get_user_stats() 应返回正确的统计摘要。"""
        service = AuthService(db_container)

        # 创建多个用户
        users_data = [
            ("user1@example.com", "user1"),
            ("user2@example.com", "user2"),
            ("user3@example.com", "user3"),
        ]
        created_users = []
        for email, username in users_data:
            result = await service.register(
                email, username, nickname="test_user", password="password123",
            )
            created_users.append(result["user"])

        # 禁用一个用户
        await service.disable_user(uuid.UUID(created_users[1]["id"]))

        # 获取统计
        stats = await service.get_user_stats()

        assert stats["total_users"] == 3
        assert stats["active_users"] == 2
        assert stats["disabled_users"] == 1
        assert stats["today_new"] == 3
        assert "by_level" in stats
        assert "daily_trend" in stats
        # 第一个用户是 P0，后续是 P5
        assert stats["by_level"].get(0, 0) >= 1
        assert stats["by_level"].get(5, 0) >= 2


# =============================================================================
# 页面组件权限管理行为测试
# =============================================================================


class TestPermissionManagement:
    """测试页面组件权限管理行为。"""

    @pytest.mark.asyncio
    async def test_get_page_permissions_returns_mapping(self, db_container):
        """get_page_permissions() 应返回 page->component->visible 映射。"""
        service = AuthService(db_container)
        level = 5

        # 直接插入两条权限记录
        async with db_container.get("db")["session_factory"]() as session:
            session.add(
                PageComponentPermission(
                    level=level, page_name="dashboard",
                    component_name="chart", visible=True,
                )
            )
            session.add(
                PageComponentPermission(
                    level=level, page_name="dashboard",
                    component_name="table", visible=False,
                )
            )
            session.add(
                PageComponentPermission(
                    level=level, page_name="settings",
                    component_name="page", visible=True,
                )
            )
            await session.commit()

        mapping = await service.get_page_permissions(level)

        assert "dashboard" in mapping
        assert "settings" in mapping
        assert mapping["dashboard"]["chart"] is True
        assert mapping["dashboard"]["table"] is False
        assert mapping["settings"]["page"] is True

    @pytest.mark.asyncio
    async def test_set_page_component_insert(self, db_container):
        """set_page_component() 应插入新的权限记录。"""
        service = AuthService(db_container)
        level = 3

        # 插入新记录
        await service.set_page_component(
            level=level, page_name="reports",
            component_name="page", visible=True,
        )

        # 验证已插入
        mapping = await service.get_page_permissions(level)
        assert "reports" in mapping
        assert mapping["reports"]["page"] is True

    @pytest.mark.asyncio
    async def test_set_page_component_update(self, db_container):
        """set_page_component() 应更新已有的权限记录。"""
        service = AuthService(db_container)
        level = 2

        # 先插入
        await service.set_page_component(
            level=level, page_name="analytics",
            component_name="page", visible=True,
        )

        # 再更新
        await service.set_page_component(
            level=level, page_name="analytics",
            component_name="page", visible=False,
        )

        # 验证已更新
        mapping = await service.get_page_permissions(level)
        assert mapping["analytics"]["page"] is False

        # 确认只有一条记录
        async with db_container.get("db")["session_factory"]() as session:
            from sqlalchemy import select
            rows = await session.execute(
                select(PageComponentPermission).where(
                    PageComponentPermission.level == level,
                    PageComponentPermission.page_name == "analytics",
                )
            )
            records = rows.scalars().all()
            assert len(records) == 1

    @pytest.mark.asyncio
    async def test_set_page_defaults(self, db_container):
        """set_page_defaults() 应批量更新指定页面下所有组件的可见性。"""
        service = AuthService(db_container)
        level = 4
        page_name = "admin"

        # 准备两条记录
        await service.set_page_component(
            level=level, page_name=page_name,
            component_name="sidebar", visible=True,
        )
        await service.set_page_component(
            level=level, page_name=page_name,
            component_name="header", visible=True,
        )

        # 批量设置为不可见
        await service.set_page_defaults(
            level=level, page_name=page_name, visible_default=False,
        )

        # 验证所有组件都已更新
        mapping = await service.get_page_permissions(level)
        assert mapping[page_name]["sidebar"] is False
        assert mapping[page_name]["header"] is False

    @pytest.mark.asyncio
    async def test_get_all_permission_levels(self, db_container):
        """get_all_permission_levels() 应返回所有已配置的 level 列表。"""
        service = AuthService(db_container)

        # 在多个 level 下创建权限记录
        for level in [1, 3, 5]:
            await service.set_page_component(
                level=level, page_name="home",
                component_name="page", visible=True,
            )

        levels = await service.get_all_permission_levels()

        assert 1 in levels
        assert 3 in levels
        assert 5 in levels
        # 应返回排序后的列表
        assert levels == sorted(levels)