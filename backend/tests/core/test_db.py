"""核心层测试 —— 数据库初始化、建表、Schema 校验。"""

from __future__ import annotations

import pytest


class TestDatabaseInit:
    """测试 init_db() 数据库初始化。"""

    @pytest.mark.asyncio
    async def test_db_engine_created(self, app):
        """数据库引擎已创建并能执行查询。"""
        from sqlalchemy import text as sa_text

        container = app.state.container
        db = container.get("db")
        engine = db["engine"]

        async with engine.connect() as conn:
            result = await conn.execute(sa_text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_factory_works(self, app):
        """session_factory 能创建真实会话。"""
        from sqlalchemy.ext.asyncio import AsyncSession

        container = app.state.container
        db = container.get("db")
        sf = db["session_factory"]

        async with sf() as session:
            assert isinstance(session, AsyncSession)
            # 执行简单查询验证连接可用
            from sqlalchemy import text as sa_text

            result = await session.execute(sa_text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_tables_created(self, app, db_session):
        """所有 ORM 模型的表已创建。"""
        from sqlalchemy import inspect as sa_inspect

        container = app.state.container
        db = container.get("db")
        engine = db["engine"]

        async with engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: sa_inspect(sync_conn).get_table_names()
            )

        # 至少包含核心表
        assert "config_entries" in tables, f"config_entries 表缺失，已有表: {tables}"
        assert "users" in tables, f"users 表缺失，已有表: {tables}"

    @pytest.mark.asyncio
    async def test_core_models_present(self, app, db_session):
        """核心模型表存在且有预期列。"""
        from sqlalchemy import inspect as sa_inspect

        container = app.state.container
        db = container.get("db")
        engine = db["engine"]

        async with engine.connect() as conn:
            # ConfigEntry
            config_cols = await conn.run_sync(
                lambda sync_conn: {
                    c["name"] for c in sa_inspect(sync_conn).get_columns("config_entries")
                }
            )
            assert "key" in config_cols
            assert "value" in config_cols
            assert "group" in config_cols
            assert "is_sensitive" in config_cols

            # User (auth)
            user_cols = await conn.run_sync(
                lambda sync_conn: {
                    c["name"] for c in sa_inspect(sync_conn).get_columns("users")
                }
            )
            assert "email" in user_cols
            assert "username" in user_cols
            assert "password_hash" in user_cols
            assert "level" in user_cols


class TestConfigSeed:
    """测试启动时配置种子写入。"""

    @pytest.mark.asyncio
    async def test_default_config_seeded(self, db_session):
        """启动种子已写入 config_entries 表。"""
        from sqlalchemy import select

        from backend.core.models import ConfigEntry

        result = await db_session.execute(select(ConfigEntry).limit(1))
        entry = result.scalar()
        assert entry is not None, "config_entries 表为空，种子未写入"
        assert hasattr(entry, "key")
        assert hasattr(entry, "value")

    @pytest.mark.asyncio
    async def test_log_level_seeded(self, db_session):
        """LOG_LEVEL 配置项已写入。"""
        from sqlalchemy import select

        from backend.core.models import ConfigEntry

        result = await db_session.execute(
            select(ConfigEntry).where(ConfigEntry.key == "LOG_LEVEL")
        )
        entry = result.scalar()
        assert entry is not None
        assert entry.value == "CRITICAL"  # 测试环境变量中设置的值

    @pytest.mark.asyncio
    async def test_seed_is_idempotent(self, app, db_session):
        """种子写入是幂等的 —— 再次触发不会产生重复行。"""
        from sqlalchemy import func, select

        from backend.core.models import ConfigEntry

        # 计数当前行数
        result = await db_session.execute(select(func.count()).select_from(ConfigEntry))
        count_before = result.scalar()

        # 再次触发 seed（模拟应用重启）
        from backend.core import _seed_default_config

        container = app.state.container
        db = container.get("db")
        await _seed_default_config(db["session_factory"])

        # 重新计数
        result = await db_session.execute(select(func.count()).select_from(ConfigEntry))
        count_after = result.scalar()

        assert count_after == count_before, f"种子不幂等: {count_before} → {count_after}"
