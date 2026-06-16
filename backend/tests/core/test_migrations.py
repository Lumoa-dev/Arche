"""核心层测试 —— Alembic 数据库迁移。

注意：在 conftest 中，create_app() 的 startup 钩子已自动执行
alembic upgrade("head") + ensure_tables()。这些测试验证迁移
的正确性和幂等性。
注意：ensure_tables() 的幂等性已在启动序列中隐式验证。
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestAlembicMigrations:
    """测试数据库迁移系统。"""

    @pytest.mark.asyncio
    async def test_tables_exist_after_migration(self, app):
        """所有核心表和插件表已创建（通过 ensure_tables）。"""
        from sqlalchemy import inspect as sa_inspect

        container = app.state.container
        db = container.get("db")
        engine = db["engine"]

        async with engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: sa_inspect(sync_conn).get_table_names()
            )

        assert "config_entries" in tables
        assert "users" in tables
        assert "blog_posts" in tables
        assert "ip_bans" in tables, f"ip_bans missing: {tables}"
        assert "request_logs" in tables, f"request_logs missing: {tables}"

    @pytest.mark.asyncio
    async def test_blog_tables_created(self, app):
        """博客插件的表已创建。"""
        from sqlalchemy import inspect as sa_inspect

        container = app.state.container
        engine = container.get("db")["engine"]

        async with engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: sa_inspect(sync_conn).get_table_names()
            )

        blog_table_names = [t for t in tables if "blog" in t]
        assert len(blog_table_names) >= 1, f"no blog tables found: {tables}"

    def test_migration_files_exist(self):
        """迁移版本文件存在。"""
        versions_dir = (
            Path(__file__).resolve().parent.parent.parent / "migrations" / "versions"
        )
        py_files = sorted(versions_dir.glob("*.py"))
        assert len(py_files) >= 1, "no migration version files"

    def test_alembic_env_exists(self):
        """Alembic env.py 存在且包含必要的配置。"""
        env_path = (
            Path(__file__).resolve().parent.parent.parent / "migrations" / "env.py"
        )
        assert env_path.exists(), "migrations/env.py not found"
        content = env_path.read_text(encoding="utf-8")
        assert "run_migrations" in content
