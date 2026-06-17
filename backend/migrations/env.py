"""Alembic env.py —— 异步 SQLAlchemy + SQLite / PostgreSQL 支持。"""

import asyncio
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# 导入项目 Base 和所有模型，确保 alembic 能检测到表结构
sys.path.insert(0, "")  # 保证项目根目录在 sys.path
from backend.core.db import Base
from backend.core.models import ConfigEntry  # noqa: F401
from backend.plugins.asset_mgmt.models import AssetIndex  # noqa: F401

# 导入所有模型（让 Base.metadata 包含全部表）
from backend.plugins.auth.models import PageComponentPermission, User  # noqa: F401
from backend.plugins.blog.models import (  # noqa: F401
    BlogComment,
    BlogFavorite,
    BlogLike,
    BlogParagraph,
    BlogPost,
    BlogPostTag,
    BlogReport,
    BlogTag,
)
from backend.plugins.cloud_integration.models import (  # noqa: F401
    Artifact,
    CodeRepo,
    Dataset,
    TrainingCost,
    TrainingInstance,
    TrainingJob,
    TrainingTaskStep,
)
from backend.plugins.crawler.models import CrawlRecord  # noqa: F401
from backend.plugins.monitor.models import MonitorTemplate  # noqa: F401
from backend.plugins.oss.models import OSSFile, UserOSSQuota  # noqa: F401

# ip_ban 插件模型（确保 --autogenerate 可检测）
from backend.plugins.ip_ban.models import (  # noqa: F401
    AutoBanRuleConfig,
    IpBan,
    IpBanLog,
)

# request_log 插件模型（确保 --autogenerate 可检测）
from backend.plugins.request_log.models import (  # noqa: F401
    IpActionCounter,
    RequestLog,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """从 .env 或环境变量读取 DATABASE_URL，覆盖 alembic.ini 的硬编码值。"""
    import os
    from pathlib import Path

    # 先读取 .env 文件
    env_path = Path(".env")
    env_values: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env_values[key.strip()] = value.strip().strip("\"'")

    # 优先级：系统环境变量 > .env 文件 > alembic.ini
    url = os.getenv("DATABASE_URL") or env_values.get("DATABASE_URL")
    if url:
        return url
    # 回退到 alembic.ini 中的值
    return (
        config.get_main_option("sqlalchemy.url")
        or "sqlite+aiosqlite:///./data/arche.db"
    )


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 脚本，不连接数据库。"""
    url = get_url()
    is_sqlite = url.startswith("sqlite")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=is_sqlite,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """在线模式：实际连接数据库执行迁移。"""
    is_sqlite = connection.dialect.name == "sqlite"
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=is_sqlite,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """异步迁移：使用 aiosqlite / asyncpg 执行。"""
    url = get_url()
    config.set_main_option("sqlalchemy.url", url)

    cfg = {}
    section = config.get_section(config.config_ini_section)
    if section:
        for key in section:
            if key.startswith("sqlalchemy."):
                cfg[key] = section[key]
    if "sqlalchemy.url" not in cfg:
        cfg["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式入口：异步数据库用异步方式，同步数据库用同步方式。"""
    url = get_url()
    if url and url.startswith("sqlite"):
        # SQLite 必须用异步方式（aiosqlite）
        asyncio.run(run_async_migrations())
    elif url and ("asyncpg" in url or "postgresql+asyncpg" in url):
        # PostgreSQL 异步
        asyncio.run(run_async_migrations())
    else:
        # 同步数据库（备用方案）
        connectable = config.attributes.get("connection", None)
        if connectable is None:
            cfg = {"sqlalchemy.url": url}
            connectable = async_engine_from_config(
                cfg,
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
            )
        if isinstance(connectable, Connection):
            do_run_migrations(connectable)
        else:
            asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
