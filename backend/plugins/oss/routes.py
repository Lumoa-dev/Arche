"""对象存储插件 —— 路由：上传/下载/删除/列表/外部写入/存储统计/配额管理/管理端点。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from backend.core.container import ServiceContainer
from backend.core.middleware import require_level, require_user

router = APIRouter(prefix="/api/oss", tags=["oss"])


# === 用户端点 ===


@router.post("/upload")
@require_level(5)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    is_private: bool = Form(default=False),
):
    """用户上传文件（流式写入 + 限速）。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    result = await storage_service.upload_file(
        file=file,
        owner_id=uuid.UUID(user["id"]),
        user_level=user["level"],
        is_private=is_private,
    )
    return {"code": "ok", "message": "上传成功", "data": result}


@router.get("/files/{file_id}")
async def download_file(file_id: str, request: Request):
    """下载文件（流式返回）。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    source, meta, _is_stream = await storage_service.download_file(
        file_id=uuid.UUID(file_id),
        requester_id=uuid.UUID(user["id"]),
        requester_level=user["level"],
    )

    filename = meta.get("path", "download").rsplit("/", 1)[-1]
    return StreamingResponse(
        source,
        media_type=meta.get("mime_type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, request: Request):
    """删除文件。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    await storage_service.delete_file(
        file_id=uuid.UUID(file_id),
        requester_id=uuid.UUID(user["id"]),
        requester_level=user["level"],
    )
    return {"code": "ok", "message": "删除成功", "data": {}}


@router.get("/my")
async def list_my_files(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """我的文件列表。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    files = await storage_service.list_my_files(
        user_id=uuid.UUID(user["id"]),
        limit=limit,
        offset=offset,
    )
    return {"code": "ok", "message": "获取成功", "data": {"files": files}}


@router.post("/external/{tenant_id}/upload")
async def external_upload(
    tenant_id: str,
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
):
    """外部租户写入文件。"""
    require_user(request)
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    result = await storage_service.external_upload(
        file=file,
        tenant_id=tenant_id,
    )
    return {"code": "ok", "message": "上传成功", "data": result}


@router.get("/external/{tenant_id}/files")
async def list_external_files(
    tenant_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """外部租户文件列表。"""
    require_user(request)
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    files = await storage_service.list_external_files(
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
    )
    return {"code": "ok", "message": "获取成功", "data": {"files": files}}


@router.get("/storage/stats")
async def get_storage_stats(
    request: Request,
    user_scope: bool = Query(default=False),
):
    """存储统计。默认全局统计，user_scope=true 时仅统计当前用户。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    user_id = uuid.UUID(user["id"]) if user_scope else None
    stats = await storage_service.get_storage_stats(user_id=user_id)
    return {"code": "ok", "message": "获取成功", "data": stats}


@router.get("/quota")
async def get_quota(request: Request):
    """用户存储配额使用情况。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    quota = await storage_service.get_p1_quota_used(uuid.UUID(user["id"]))
    return {"code": "ok", "message": "获取成功", "data": quota}


# === 管理端点 ===


@router.post("/admin/evict")
@require_level(0)
async def trigger_eviction(
    request: Request,
    days: int = Query(default=7, ge=1, le=30),
):
    """手动触发冷热迁移（P0）。"""
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    count = await storage_service.evict_cold_files(days=days)
    return {
        "code": "ok",
        "message": f"迁移完成，{count} 个文件已推到阿里云",
        "data": {"migrated": count},
    }


@router.get("/admin/quotas")
@require_level(0)
async def list_user_quotas(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """用户配额列表（P0）。"""
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    result = await storage_service.list_user_quotas(limit=limit, offset=offset)
    return {"code": "ok", "message": "获取成功", "data": result}


@router.put("/admin/quotas/{user_id}")
@require_level(0)
async def update_user_quota(request: Request, user_id: str):
    """更新用户配额和限速倍率（P0）。"""
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    body = await request.json()
    result = await storage_service.update_user_quota(
        uuid.UUID(user_id),
        quota_bytes=body.get("quota_bytes"),
        speed_multiplier=body.get("speed_multiplier"),
    )
    return {"code": "ok", "message": "配额更新成功", "data": result}


@router.get("/admin/rate-limit")
@require_level(0)
async def get_rate_limit_config(request: Request):
    """获取全局限速配置（P0）。"""
    container: ServiceContainer = request.app.state.container
    rate_limiter = container.get("oss_rate_limiter")
    return {
        "code": "ok",
        "message": "获取成功",
        "data": {
            "global_rate_bytes": rate_limiter.global_rate,
            "global_rate_mb": round(rate_limiter.global_rate / 1024 / 1024, 2),
        },
    }


@router.put("/admin/rate-limit")
@require_level(0)
async def update_global_rate_limit(request: Request):
    """更新全局限速（P0）。"""
    container: ServiceContainer = request.app.state.container
    rate_limiter = container.get("oss_rate_limiter")
    body = await request.json()
    rate_bytes = body.get("global_rate_bytes")
    if rate_bytes:
        rate_limiter.set_global_rate(rate_bytes)
    return {
        "code": "ok",
        "message": "限速更新成功",
        "data": {"global_rate_bytes": rate_limiter.global_rate},
    }


@router.put("/admin/rate-limit/users/{user_id}")
@require_level(0)
async def update_user_speed_multiplier(request: Request, user_id: str):
    """更新用户限速倍率（P0）。"""
    container: ServiceContainer = request.app.state.container
    rate_limiter = container.get("oss_rate_limiter")
    storage_service = container.get("storage")
    body = await request.json()
    multiplier = body.get("speed_multiplier", 1.0)
    rate_limiter.set_user_multiplier(uuid.UUID(user_id), multiplier)
    # 同步到数据库
    await storage_service.update_user_quota(
        uuid.UUID(user_id), speed_multiplier=multiplier
    )
    return {"code": "ok", "message": "倍率更新成功", "data": {"multiplier": multiplier}}


@router.get("/admin/files")
@require_level(0)
async def admin_list_files(
    request: Request,
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """管理员文件列表，可按用户过滤（P0）。"""
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    uid = uuid.UUID(user_id) if user_id else None
    files = await storage_service.admin_list_files(
        user_id=uid, limit=limit, offset=offset
    )
    return {"code": "ok", "message": "获取成功", "data": {"files": files}}


@router.delete("/admin/files/{file_id}")
@require_level(0)
async def admin_delete_file(request: Request, file_id: str):
    """管理员删除任意文件（P0）。"""
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    await storage_service.admin_delete_file(uuid.UUID(file_id))
    return {"code": "ok", "message": "删除成功", "data": {}}


@router.get("/admin/stats")
@require_level(0)
async def admin_stats(request: Request):
    """OSS 统计大盘（P0）。"""
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    stats = await storage_service.get_admin_stats()
    return {"code": "ok", "message": "获取成功", "data": stats}


@router.get("/admin/stats/top-users")
@require_level(0)
async def top_users_by_storage(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
):
    """按存储使用量排行的用户列表（P0）。"""
    container: ServiceContainer = request.app.state.container
    storage_service = container.get("storage")
    users = await storage_service.get_top_users_by_storage(limit=limit)
    return {"code": "ok", "message": "获取成功", "data": {"users": users}}
