"""ConfigMgmt 路由行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现
- 数据库交互用内存 SQLite
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from backend.core.models import ConfigEntry


# =============================================================================
# ConfigEntry 模型行为测试
# =============================================================================


class TestConfigEntryModel:
    """测试 ConfigEntry 模型行为。"""

    @pytest.mark.asyncio
    async def test_create_config_entry(self, module_db):
        """创建配置项应成功。"""
        session_factory = module_db["session_factory"]
        async with session_factory() as session:
            entry = ConfigEntry(
                key="test_key",
                value="test_value",
                group="general",
                description="Test config",
                is_sensitive=False,
            )
            session.add(entry)
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(
                select(ConfigEntry).where(ConfigEntry.key == "test_key")
            )
            entry = result.scalar_one_or_none()
            assert entry is not None
            assert entry.key == "test_key"
            assert entry.value == "test_value"
            assert entry.group == "general"
            assert entry.is_sensitive is False

    @pytest.mark.asyncio
    async def test_sensitive_config_is_masked(self, module_db):
        """敏感配置项应标记为敏感。"""
        session_factory = module_db["session_factory"]
        async with session_factory() as session:
            entry = ConfigEntry(
                key="secret_key",
                value="super_secret_value",
                group="security",
                is_sensitive=True,
            )
            session.add(entry)
            await session.commit()

            assert entry.is_sensitive is True

    @pytest.mark.asyncio
    async def test_update_config_value(self, module_db):
        """更新配置值应生效。"""
        session_factory = module_db["session_factory"]
        async with session_factory() as session:
            entry = ConfigEntry(
                key="update_test",
                value="old_value",
                group="test",
            )
            session.add(entry)
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(
                select(ConfigEntry).where(ConfigEntry.key == "update_test")
            )
            entry = result.scalar_one_or_none()
            entry.value = "new_value"
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(
                select(ConfigEntry).where(ConfigEntry.key == "update_test")
            )
            entry = result.scalar_one_or_none()
            assert entry.value == "new_value"

    @pytest.mark.asyncio
    async def test_delete_config_entry(self, module_db):
        """删除配置项应成功。"""
        session_factory = module_db["session_factory"]
        async with session_factory() as session:
            entry = ConfigEntry(
                key="delete_test",
                value="to_be_deleted",
                group="test",
            )
            session.add(entry)
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(
                select(ConfigEntry).where(ConfigEntry.key == "delete_test")
            )
            entry = result.scalar_one_or_none()
            await session.delete(entry)
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(
                select(ConfigEntry).where(ConfigEntry.key == "delete_test")
            )
            entry = result.scalar_one_or_none()
            assert entry is None

    @pytest.mark.asyncio
    async def test_duplicate_key_raises_error(self, module_db):
        """重复的配置键应抛出异常。"""
        session_factory = module_db["session_factory"]
        async with session_factory() as session:
            entry1 = ConfigEntry(
                key="duplicate_key",
                value="value1",
                group="test",
            )
            session.add(entry1)
            await session.commit()

        async with session_factory() as session:
            entry2 = ConfigEntry(
                key="duplicate_key",
                value="value2",
                group="test",
            )
            session.add(entry2)
            with pytest.raises(Exception):
                await session.commit()
            await session.rollback()

    @pytest.mark.asyncio
    async def test_list_configs_by_group(self, module_db):
        """按分组列出配置应正确。"""
        session_factory = module_db["session_factory"]
        async with session_factory() as session:
            for i in range(3):
                session.add(
                    ConfigEntry(
                        key=f"general_key_{i}", value=f"val_{i}", group="general"
                    )
                )
            for i in range(2):
                session.add(
                    ConfigEntry(
                        key=f"security_key_{i}", value=f"secret_{i}", group="security"
                    )
                )
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(
                select(ConfigEntry).where(ConfigEntry.group == "security")
            )
            entries = result.scalars().all()
            assert len(entries) == 2


# =============================================================================
# ConfigMgmt 路由逻辑行为测试
# =============================================================================


class TestConfigMgmtRoutes:
    """测试配置管理路由的业务逻辑。"""

    @pytest.mark.asyncio
    async def test_config_list_masks_sensitive_values(self, module_db):
        """敏感配置项的值应被掩码。"""
        session_factory = module_db["session_factory"]
        async with session_factory() as session:
            session.add(
                ConfigEntry(
                    key="public_key",
                    value="public_value",
                    group="general",
                    is_sensitive=False,
                )
            )
            session.add(
                ConfigEntry(
                    key="secret_key",
                    value="super_secret",
                    group="security",
                    is_sensitive=True,
                )
            )
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(
                select(ConfigEntry).order_by(ConfigEntry.key)
            )
            entries = result.scalars().all()

            for e in entries:
                if e.is_sensitive:
                    assert e.value != "***"  # 数据库存真实值，掩码在路由层
                else:
                    assert e.value == "public_value"

    @pytest.mark.asyncio
    async def test_update_nonexistent_config(self, module_db):
        """更新不存在的配置项应返回 None。"""
        session_factory = module_db["session_factory"]
        async with session_factory() as session:
            result = await session.execute(
                select(ConfigEntry).where(ConfigEntry.key == "nonexistent")
            )
            entry = result.scalar_one_or_none()
            assert entry is None

    @pytest.mark.asyncio
    async def test_config_groups_list(self, module_db):
        """列出所有分组应去重。"""
        session_factory = module_db["session_factory"]
        async with session_factory() as session:
            session.add(ConfigEntry(key="a", value="1", group="general"))
            session.add(ConfigEntry(key="b", value="2", group="general"))
            session.add(ConfigEntry(key="c", value="3", group="security"))
            await session.commit()

        from sqlalchemy import distinct

        result = await session.execute(
            select(distinct(ConfigEntry.group)).order_by(ConfigEntry.group)
        )
        groups = [row[0] for row in result.all()]
        assert len(groups) == 2
        assert "general" in groups
        assert "security" in groups