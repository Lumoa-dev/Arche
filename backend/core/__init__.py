"""Arche Core — 微内核应用工厂

组装顺序：
1. 配置日志
2. 初始化数据库
3. 创建ServiceContainer，注册配置文件
4. 激活插件（DAG 排序设置）
5. 将插件服务注册到容器中
6. 设置中间件（CORS，错误处理程序）
7. 寄存启动/关机钩子
"""

from __future__ import annotations

import logging
import logging.config
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from .config import config_manager as config_manager
from .container import ServiceContainer
from .db import close_db, init_db
from .middleware import register_error_handlers, setup_cors, setup_security_headers
from .plugin_registry import registry

_DEFAULT_CONFIG_SEED = [
    # (key, group, description, is_sensitive)
    ("MINIO_ENDPOINT", "minio", "MinIO 服务地址", False),
    ("MINIO_ROOT_USER", "minio", "MinIO 管理员用户名", False),
    ("MINIO_ROOT_PASSWORD", "minio", "MinIO 管理员密码", True),
    ("MINIO_SECURE", "minio", "是否启用 TLS", False),
    ("OSS_ACCESS_KEY_ID", "oss", "阿里云 OSS AccessKey ID", True),
    ("OSS_ACCESS_KEY_SECRET", "oss", "阿里云 OSS AccessKey Secret", True),
    ("OSS_ENDPOINT", "oss", "阿里云 OSS Endpoint", False),
    ("OSS_BUCKET_NAME", "oss", "阿里云 OSS Bucket 名称", False),
    ("CLOUD_PROVIDER", "cloud", "云训练 Provider (mock/zhixingyun/aliyun)", False),
    ("ZHIXINGYUN_API_KEY", "cloud", "智星云 API Key", True),
    ("ZHIXINGYUN_API_SECRET", "cloud", "智星云 API Secret", True),
    ("ALIYUN_ACCESS_KEY_ID", "cloud", "阿里云 ECS AccessKey ID", True),
    ("ALIYUN_ACCESS_KEY_SECRET", "cloud", "阿里云 ECS AccessKey Secret", True),
    ("ALIYUN_REGION", "cloud", "阿里云 ECS Region", False),
    ("ALIYUN_SECURITY_GROUP_ID", "cloud", "阿里云安全组 ID", False),
    ("ALIYUN_VSWITCH_ID", "cloud", "阿里云交换机 ID", False),
    ("ALIYUN_IMAGE_ID", "cloud", "阿里云镜像 ID", False),
    ("CLOUD_API_KEY", "cloud", "通用云 API Key", True),
    ("CLOUD_API_SECRET", "cloud", "通用云 API Secret", True),
    ("GITHUB_TOKEN", "github", "GitHub API Token", True),
    ("GITHUB_API_BASE", "github", "GitHub API Base URL", False),
    ("GITHUB_RAW_BASE", "github", "GitHub Raw Base URL", False),
    ("GITHUB_CACHE_TTL", "github", "GitHub 缓存 TTL (秒)", False),
    ("GITHUB_TIMEOUT", "github", "GitHub 请求超时 (秒)", False),
    ("CRAWLER_SEEDS", "crawler", "爬虫种子 URL", False),
    ("CRAWLER_STORAGE_ROOT", "crawler", "爬虫存储目录", False),
    ("LOG_LEVEL", "logging", "日志级别 (DEBUG/INFO/WARNING/ERROR)", False),
    ("LOG_FILE", "logging", "日志文件路径", False),
    ("MONITOR_COLLECT_INTERVAL", "system", "监控采集间隔 (秒)", False),
    ("SENSITIVE_WORDS", "system", "敏感词列表 (逗号分隔)", False),
    ("DEPLOY_TOKEN", "deploy", "部署 Webhook Token", True),
]


async def _seed_default_config(session_factory) -> None:
    """将 .env 中的默认值初始化到数据库（仅首次启动时）。"""
    try:
        from sqlalchemy import select

        from backend.core.models import ConfigEntry

        async with session_factory() as session:
            result = await session.execute(select(ConfigEntry).limit(1))
            if result.first():
                return

            for key, group, desc, sensitive in _DEFAULT_CONFIG_SEED:
                value = config_manager.get(key, "")
                if not value and key == "LOG_LEVEL":
                    value = "INFO"

                entry = ConfigEntry(
                    key=key,
                    group=group,
                    description=desc,
                    is_sensitive=sensitive,
                    value=value,
                )
                session.add(entry)

            await session.commit()
    except Exception:
        logging.exception("Config seed skipped")


def _setup_logging() -> None:
    """配置统一日志：控制台 + 可选文件处理器。"""
    log_level = (config_manager.get("LOG_LEVEL", "INFO") or "INFO").upper()
    log_file = config_manager.get("LOG_FILE")

    handlers = ["console"]
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(levelname)s:     %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": log_level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
    }

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append("file")
        logging_config["handlers"]["file"] = {  # type: ignore[index]
            "class": "logging.FileHandler",
            "formatter": "default",
            "filename": str(log_path),
            "level": log_level,
            "encoding": "utf-8",
        }
        logging_config["root"]["handlers"] = handlers  # type: ignore[index]

    # 第三方库日志抑制：APScheduler 的调度日志（每秒执行/完成）只应在 WARNING 及以上输出
    logging_config["loggers"] = {
        "apscheduler": {
            "level": "WARNING",
            "handlers": handlers,
            "propagate": False,
        },
    }

    logging.config.dictConfig(logging_config)


def create_app() -> FastAPI:
    # 1. Configure logging (before anything else runs)
    _setup_logging()

    # 2. Create container, register config
    container = ServiceContainer()

    # 同步到模块级单例，供直接导入它的插件使用
    from backend.core import container as _container_mod

    _container_mod.container = container

    def _config_factory(c):  # noqa: ARG001
        return config_manager

    container.register("config", _config_factory)

    # 3. Init database
    database_url = config_manager.get_required("DATABASE_URL")
    engine, session_factory = init_db(database_url)

    def _db_factory(c):  # noqa: ARG001
        return {"engine": engine, "session_factory": session_factory}

    container.register("db", _db_factory)

    # 4. Create app
    app = FastAPI(title="Arche", version="0.1.0")
    app.state.container = container

    # 5. Activate plugins (DAG-ordered setup)
    registry.activate_all(app)

    # 6. Register plugin services into container
    registry.register_services(container)

    # 7. Middleware
    cors_origins = (
        config_manager.get("CORS_ORIGINS", "http://localhost:5173")
        or "http://localhost:5173"
    )
    setup_cors(app, [o.strip() for o in cors_origins.split(",")])
    register_error_handlers(app)
    setup_security_headers(app)

    # 添加 API 请求统计中间件
    @app.middleware("http")
    async def record_request_stats(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 2)

        try:
            if container.is_available("request_stats"):
                stats = container.get("request_stats")
                stats.record_request(
                    path=request.url.path,
                    duration_ms=duration_ms,
                    status_code=response.status_code,
                )
        except Exception:
            pass
        return response

    # 8. Startup / Shutdown hooks
    @app.on_event("startup")
    async def startup():
        import asyncio

        from alembic import command
        from alembic.config import Config as AlembicConfig

        # 运行数据库迁移
        migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
        alembic_cfg = AlembicConfig()
        alembic_cfg.set_main_option("script_location", str(migrations_dir))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)

        loop = asyncio.get_event_loop()

        def _run_migrations():
            # 自动迁移。改模型后执行 `alembic revision --autogenerate -m "xxx"`
            command.upgrade(alembic_cfg, "head")

        await loop.run_in_executor(None, _run_migrations)

        # 兜底：确保所有 ORM 模型对应的表已创建（迁移未覆盖时使用，幂等）
        from .db import ensure_tables

        await ensure_tables()

        # 校验数据库 schema 是否与模型一致
        from .db import validate_schema

        await validate_schema()

        # 注入 session factory 供数据库降级使用
        config_manager.set_session_factory(session_factory)

        # Seed default config (first run only)
        await _seed_default_config(session_factory)

        await registry.on_startup()

    @app.on_event("shutdown")
    async def shutdown():
        await close_db()
        registry.on_shutdown()
        container.shutdown()

    # 9. Mount frontend static files (built Vue app)
    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount(
            "/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend"
        )

    return app
