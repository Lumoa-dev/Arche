"""配置管理 API — 管理员可 CRUD 运行时配置。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.core.middleware import require_level

router = APIRouter(prefix="/api/admin/config", tags=["admin-config"])


class UpdateConfigRequest(BaseModel):
    value: str = Field(..., description="配置值")


class CreateConfigRequest(BaseModel):
    key: str = Field(..., min_length=1, description="配置键")
    value: str = Field(..., description="配置值")
    group: str = Field(default="general", description="配置分组")
    description: str | None = Field(default=None, description="配置描述")
    is_sensitive: bool = Field(default=False, description="是否敏感")


# --- List all / By group ---


@router.get("")
@require_level(0)
async def list_configs(request: Request, group: str | None = None):
    """列出所有配置（可按 group 过滤），敏感字段掩码返回。"""
    from backend.core.container import ServiceContainer
    from backend.core.models import ConfigEntry

    container: ServiceContainer = request.app.state.container
    config = container.get("config")
    session_factory = config._session_factory

    if not session_factory:
        return {"code": "error", "message": "数据库未就绪", "data": []}

    async with session_factory() as session:
        query = select(ConfigEntry)
        if group:
            query = query.where(ConfigEntry.group == group)
        query = query.order_by(ConfigEntry.group, ConfigEntry.key)
        result = await session.execute(query)
        entries = result.scalars().all()

    items = [
        {
            "key": e.key,
            "value": "***" if e.is_sensitive else e.value,
            "group": e.group,
            "description": e.description,
            "is_sensitive": e.is_sensitive,
        }
        for e in entries
    ]
    return {"code": "ok", "message": "获取成功", "data": items}


# --- Groups ---


@router.get("/groups")
@require_level(0)
async def list_groups(request: Request):
    """列出所有配置分组。"""
    from sqlalchemy import distinct

    from backend.core.container import ServiceContainer
    from backend.core.models import ConfigEntry

    container: ServiceContainer = request.app.state.container
    config = container.get("config")
    session_factory = config._session_factory

    if not session_factory:
        return {"code": "ok", "data": []}

    async with session_factory() as session:
        result = await session.execute(
            select(distinct(ConfigEntry.group)).order_by(ConfigEntry.group)
        )
        groups = [row[0] for row in result.all()]

    return {"code": "ok", "message": "获取成功", "data": groups}


# --- Get single entry ---


@router.get("/{key}")
@require_level(0)
async def get_config(key: str, request: Request):
    """获取单条配置详情（敏感字段也返回真实值）。"""
    from backend.core.container import ServiceContainer
    from backend.core.models import ConfigEntry

    container: ServiceContainer = request.app.state.container
    config = container.get("config")
    session_factory = config._session_factory

    if not session_factory:
        return {"code": "error", "message": "数据库未就绪", "data": {}}

    async with session_factory() as session:
        result = await session.execute(
            select(ConfigEntry).where(ConfigEntry.key == key)
        )
        entry = result.scalar_one_or_none()

    if not entry:
        return {"code": "error", "message": f"配置项 {key} 不存在", "data": {}}

    return {
        "code": "ok",
        "message": "获取成功",
        "data": {
            "key": entry.key,
            "value": entry.value,
            "group": entry.group,
            "description": entry.description,
            "is_sensitive": entry.is_sensitive,
        },
    }


# --- Update ---


@router.put("/{key}")
@require_level(0)
async def update_config(key: str, req: UpdateConfigRequest, request: Request):
    """更新配置值，同时清除内存缓存。"""
    from backend.core.container import ServiceContainer
    from backend.core.models import ConfigEntry

    container: ServiceContainer = request.app.state.container
    config = container.get("config")
    session_factory = config._session_factory

    if not session_factory:
        return {"code": "error", "message": "数据库未就绪", "data": {}}

    async with session_factory() as session:
        result = await session.execute(
            select(ConfigEntry).where(ConfigEntry.key == key)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return {"code": "error", "message": f"配置项 {key} 不存在", "data": {}}
        entry.value = req.value
        await session.commit()

    # 立即清除缓存，下次 get() 时重新读取
    config.invalidate_cache(key)

    return {"code": "ok", "message": "更新成功", "data": {"key": key}}


# --- Create ---


@router.post("")
@require_level(0)
async def create_config(req: CreateConfigRequest, request: Request):
    """创建新的配置项。"""
    from backend.core.container import ServiceContainer
    from backend.core.models import ConfigEntry

    container: ServiceContainer = request.app.state.container
    config = container.get("config")
    session_factory = config._session_factory

    if not session_factory:
        return {"code": "error", "message": "数据库未就绪", "data": {}}

    async with session_factory() as session:
        # 检查是否已存在
        existing = await session.execute(
            select(ConfigEntry).where(ConfigEntry.key == req.key)
        )
        if existing.scalar_one_or_none():
            return {"code": "error", "message": f"配置项 {req.key} 已存在", "data": {}}

        entry = ConfigEntry(
            key=req.key,
            value=req.value,
            group=req.group,
            description=req.description,
            is_sensitive=req.is_sensitive,
        )
        session.add(entry)
        await session.commit()

    return {
        "code": "ok",
        "message": "创建成功",
        "data": {
            "key": entry.key,
            "value": entry.value,
            "group": entry.group,
            "description": entry.description,
            "is_sensitive": entry.is_sensitive,
        },
    }


# --- Delete ---


@router.delete("/{key}")
@require_level(0)
async def delete_config(key: str, request: Request):
    """删除配置项。"""
    from backend.core.container import ServiceContainer
    from backend.core.models import ConfigEntry

    container: ServiceContainer = request.app.state.container
    config = container.get("config")
    session_factory = config._session_factory

    if not session_factory:
        return {"code": "error", "message": "数据库未就绪", "data": {}}

    async with session_factory() as session:
        result = await session.execute(
            select(ConfigEntry).where(ConfigEntry.key == key)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return {"code": "error", "message": f"配置项 {key} 不存在", "data": {}}
        await session.delete(entry)
        await session.commit()

    # 清除缓存
    config.invalidate_cache(key)

    return {"code": "ok", "message": "删除成功", "data": {}}


# --- Reload cache ---


@router.post("/reload")
@require_level(0)
async def reload_config(request: Request):
    """强制清除所有配置缓存，下次请求时重新从数据库加载。"""
    from backend.core.container import ServiceContainer

    container: ServiceContainer = request.app.state.container
    config = container.get("config")
    config.invalidate_cache()

    return {"code": "ok", "message": "缓存已清除", "data": {}}
