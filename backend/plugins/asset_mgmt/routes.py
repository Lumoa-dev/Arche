"""资产管理插件 —— FastAPI 路由：统一目录、搜索、统计。

所有端点需要 P0 权限。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Request

from backend.core.container import ServiceContainer
from backend.core.middleware import require_level, require_user

router = APIRouter(prefix="/api/assets", tags=["asset_mgmt"])


@router.get("")
@require_level(0)
async def list_assets(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    asset_type: str | None = Query(None, description="资产类型过滤"),
):
    """统一资产目录（P0）。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    asset_service = container.get("asset_mgmt")
    result = await asset_service.list_assets(
        owner_id=uuid.UUID(user["id"]),
        page=page,
        page_size=page_size,
        asset_type=asset_type,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/search")
@require_level(0)
async def search_assets(
    request: Request,
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    asset_type: str | None = Query(None, description="资产类型过滤"),
    date_from: str | None = Query(None, description="起始时间 ISO 8601"),
    date_to: str | None = Query(None, description="结束时间 ISO 8601"),
):
    """资产搜索（P0）。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    asset_service = container.get("asset_mgmt")
    results = await asset_service.search_assets(
        owner_id=uuid.UUID(user["id"]),
        keyword=keyword,
        asset_type=asset_type,
        date_from=date_from,
        date_to=date_to,
    )
    return {
        "code": "ok",
        "message": "搜索成功",
        "data": {"items": results, "total": len(results)},
    }


@router.get("/stats")
@require_level(0)
async def get_asset_stats(request: Request):
    """资产统计（P0）。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    asset_service = container.get("asset_mgmt")
    stats = await asset_service.get_stats(
        owner_id=uuid.UUID(user["id"]),
    )
    return {"code": "ok", "message": "获取成功", "data": stats}
