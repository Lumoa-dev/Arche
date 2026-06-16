"""IP 封禁插件 —— 路由：封禁管理、规则配置、日志查询。"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from backend.core.middleware import require_level, require_user

router = APIRouter(prefix="/api/ip-ban", tags=["ip_ban"])


# ── 请求体模型 ──


class BanIPRequest(BaseModel):
    ip_or_cidr: str = Field(..., min_length=1, max_length=64, description="IP 或 CIDR")
    reason: str = Field("", max_length=512, description="封禁原因")
    duration_minutes: int | None = Field(
        None, ge=0, description="封禁时长（分钟），为空或0表示永久"
    )


class BatchUnbanRequest(BaseModel):
    ban_ids: list[int] = Field(..., min_length=1, description="封禁记录 ID 列表")


class UpdateRuleRequest(BaseModel):
    enabled: bool | None = Field(None, description="是否启用")
    threshold: int | None = Field(None, ge=1, description="触发阈值")
    window_seconds: int | None = Field(None, ge=1, description="统计窗口（秒）")
    ban_duration_minutes: int | None = Field(None, ge=0, description="封禁时长（分钟）")
    description: str | None = Field(None, max_length=256, description="规则描述")
    name: str | None = Field(None, max_length=128, description="规则名称")


# ── 封禁管理 ──


@router.get("/bans")
@require_level(0)
async def list_bans(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    ban_type: str | None = Query(None, description="封禁类型: auto/manual"),
    is_active: str | None = Query(None, description="状态: true/false"),
    keyword: str | None = Query(None, description="IP/CIDR 搜索关键词"),
):
    """封禁列表（P0）。"""
    container = request.app.state.container
    ip_ban_service = container.get("ip_ban")
    result = await ip_ban_service.list_bans(
        page=page,
        page_size=page_size,
        ban_type=ban_type,
        is_active={"true": True, "false": False}.get(is_active) if is_active else None,
        keyword=keyword,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.post("/bans")
@require_level(0)
async def ban_ip(req: BanIPRequest, request: Request):
    """手动封禁 IP/CIDR（P0）。"""
    user = require_user(request)
    container = request.app.state.container
    ip_ban_service = container.get("ip_ban")
    result = await ip_ban_service.ban_ip(
        ip_or_cidr=req.ip_or_cidr,
        reason=req.reason,
        ban_type="manual",
        banned_by=user.get("username", ""),
        duration_minutes=req.duration_minutes,
    )
    return {"code": "ok", "message": "封禁成功", "data": result}


@router.post("/bans/batch-unban")
@require_level(0)
async def batch_unban(req: BatchUnbanRequest, request: Request):
    """批量解封（P0）。"""
    user = require_user(request)
    container = request.app.state.container
    ip_ban_service = container.get("ip_ban")
    count = await ip_ban_service.batch_unban(
        ban_ids=req.ban_ids, operator=user.get("username", "")
    )
    return {"code": "ok", "message": f"已解封 {count} 条", "data": {"count": count}}


@router.post("/bans/{ban_id}/unban")
@require_level(0)
async def unban_ip(ban_id: int, request: Request):
    """解封单个 IP/CIDR（P0）。"""
    user = require_user(request)
    container = request.app.state.container
    ip_ban_service = container.get("ip_ban")
    result = await ip_ban_service.unban_ip(
        ban_id=ban_id, operator=user.get("username", "")
    )
    return {"code": "ok", "message": "解封成功", "data": result}


# ── 操作日志 ──


@router.get("/logs")
@require_level(0)
async def get_ban_logs(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    action: str | None = Query(None, description="操作类型: ban/unban"),
):
    """封禁操作日志（P0）。"""
    container = request.app.state.container
    ip_ban_service = container.get("ip_ban")
    result = await ip_ban_service.get_ban_logs(
        page=page, page_size=page_size, action=action
    )
    return {"code": "ok", "message": "获取成功", "data": result}


# ── 自动封禁规则配置 ──


@router.get("/rules")
@require_level(0)
async def get_rules(request: Request):
    """获取自动封禁规则配置（P0）。"""
    container = request.app.state.container
    ip_ban_service = container.get("ip_ban")
    result = await ip_ban_service.get_rule_configs()
    return {"code": "ok", "message": "获取成功", "data": result}


@router.put("/rules/{rule_id}")
@require_level(0)
async def update_rule(rule_id: str, req: UpdateRuleRequest, request: Request):
    """更新自动封禁规则配置（P0）。"""
    container = request.app.state.container
    ip_ban_service = container.get("ip_ban")
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        return {"code": "ok", "message": "无需更新", "data": {}}
    result = await ip_ban_service.update_rule_config(rule_id, updates)
    return {"code": "ok", "message": "更新成功", "data": result}


# ── 统计 ──


@router.get("/stats")
@require_level(0)
async def get_stats(request: Request):
    """封禁统计（P0）。"""
    container = request.app.state.container
    ip_ban_service = container.get("ip_ban")
    result = await ip_ban_service.get_stats()
    return {"code": "ok", "message": "获取成功", "data": result}
