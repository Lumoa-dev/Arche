"""数据库层 —— 异步引擎 + 延迟建表。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# 模块级变量，供 on_startup 等场景使用
engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None
_initialized = False


async def ensure_tables() -> None:
    """延迟创建表，在首次异步上下文中执行（避免事件循环冲突）。"""
    global _initialized
    if _initialized:
        return
    assert engine is not None, "Database not initialized. Call init_db() first."
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _initialized = True


def init_db(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_pre_ping: bool = True,
    pool_recycle: int = 300,
) -> tuple:
    global engine, session_factory
    kwargs: dict = {"echo": False}
    # 连接池参数仅适用于 PostgreSQL（asyncpg），SQLite 不支持 pool_* 参数
    if database_url.startswith("postgresql"):
        kwargs["pool_size"] = pool_size
        kwargs["max_overflow"] = max_overflow
        kwargs["pool_pre_ping"] = pool_pre_ping
        kwargs["pool_recycle"] = pool_recycle
        kwargs["connect_args"] = {"statement_cache_size": 0}
    engine = create_async_engine(database_url, **kwargs)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return engine, session_factory


async def close_db() -> None:
    """关闭数据库引擎，释放连接池。"""
    global engine, session_factory, _initialized
    if engine is not None:
        await engine.dispose()
        engine = None
        session_factory = None
        _initialized = False


async def validate_schema() -> None:
    """启动时校验数据库 schema 是否与模型一致。"""
    assert engine is not None, "Database not initialized. Call init_db() first."
    async with engine.begin() as conn:
        result = await conn.run_sync(_validate_schema_sync)
        if result:
            raise RuntimeError(
                f"数据库 schema 与模型不一致，请执行 migration 修复：\n{result}"
            )


def _validate_schema_sync(conn):
    """同步检查所有表的列是否匹配模型定义。"""
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy import text as sa_text

    issues = []
    # 检测数据库类型
    is_postgresql = conn.dialect.name == "postgresql"
    inspector = sa_inspect(conn)

    for table_name, table in Base.metadata.tables.items():
        try:
            if is_postgresql:
                result = conn.execute(
                    sa_text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :table"
                    ),
                    {"table": table_name},
                )
                db_cols = {row[0] for row in result.fetchall()}
            else:
                columns = inspector.get_columns(table_name)
                db_cols = {c["name"] for c in columns}
        except Exception:
            continue  # 表不存在，会在后续 create_all/migration 中创建

        model_cols = set(table.c.keys())
        missing = model_cols - db_cols
        if missing:
            issues.append(f"  {table_name} 缺少列: {', '.join(sorted(missing))}")

    return "\n".join(issues) if issues else ""
