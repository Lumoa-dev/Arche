"""爬虫插件 —— API 路由：状态、种子、黑名单、记录查询。"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from backend.core.container import ServiceContainer
from backend.core.middleware import require_level

router = APIRouter(prefix="/api/crawler", tags=["crawler"])


# --- 系统控制 ---


@router.get("/status")
@require_level(0)
async def get_status(request: Request):
    """获取爬虫运行状态。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    result = await orchestrator.get_status()
    return {"code": "ok", "data": result}


@router.post("/start")
@require_level(0)
async def start_crawler(request: Request):
    """启动爬虫。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    await orchestrator.start()
    return {"code": "ok", "message": "爬虫已启动"}


@router.post("/stop")
@require_level(0)
async def stop_crawler(request: Request):
    """停止爬虫。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    await orchestrator.stop()
    return {"code": "ok", "message": "爬虫已停止"}


# --- 记录查询 ---


@router.get("/records")
@require_level(0)
async def list_records(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """分页抓取记录。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    records = await orchestrator.get_recent_records(limit=page * page_size)
    start = (page - 1) * page_size
    end = start + page_size
    return {"code": "ok", "data": {"items": records[start:end], "total": len(records)}}


@router.get("/records/{record_id}")
@require_level(0)
async def get_record(record_id: str, request: Request):
    """单条记录详情。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    result = await orchestrator.get_record(record_id)
    if not result:
        return {"code": "not_found", "message": "记录不存在", "data": None}
    return {"code": "ok", "data": result}


@router.get("/records/{record_id}/file")
@require_level(0)
async def get_record_file(record_id: str, request: Request):
    """下载 OSS 中对应文件内容。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    record = await orchestrator.get_record(record_id)
    if not record or not record.get("file_path"):
        return {"code": "not_found", "message": "文件或记录不存在", "data": None}
    import json
    import os
    from pathlib import Path

    storage_root = Path(
        os.environ.get("CRAWLER_STORAGE_ROOT", "data/crawler")
    ).resolve()
    rel = Path(record["file_path"])
    if rel.is_absolute() or ".." in rel.parts:
        return {"code": "error", "message": "非法文件路径", "data": None}
    file_path = (storage_root / rel).resolve()
    try:
        file_path.relative_to(storage_root)
    except ValueError:
        return {"code": "error", "message": "非法文件路径", "data": None}
    if not file_path.exists():
        return {"code": "not_found", "message": "文件不存在", "data": None}
    content = (
        file_path.read_text(encoding="utf-8")
        if file_path.suffix == ".json"
        else file_path.read_bytes()
    )
    if isinstance(content, str):
        return {"code": "ok", "data": json.loads(content)}
    return {"code": "ok", "data": "binary content"}


# --- 种子管理 ---


class AddSeedRequest(BaseModel):
    url: str = Field(..., min_length=1)


@router.post("/seeds")
@require_level(0)
async def add_seed(req: AddSeedRequest, request: Request):
    """手动添加种子 URL。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    success = await orchestrator.add_seed(req.url)
    if success:
        return {"code": "ok", "message": "种子已添加"}
    return {"code": "error", "message": "种子已存在或在黑名单中"}


@router.get("/seeds")
@require_level(0)
async def get_seeds(request: Request):
    """种子池状态。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    return {
        "code": "ok",
        "data": {
            "queue_size": orchestrator.seed_manager.queue_size,
            "total_seen": orchestrator.seed_manager.total_seen,
            "blacklist": orchestrator.seed_manager.get_blacklist(),
            "whitelist": orchestrator.seed_manager.get_whitelist(),
        },
    }


# --- 黑名单 ---


class AddBlacklistRequest(BaseModel):
    pattern: str = Field(..., min_length=1)
    reason: str = ""


@router.post("/blacklist")
@require_level(0)
async def add_blacklist(req: AddBlacklistRequest, request: Request):
    """添加黑名单规则。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    orchestrator.seed_manager.add_to_blacklist(req.pattern, req.reason)
    return {"code": "ok", "message": "黑名单已添加"}


@router.get("/blacklist")
@require_level(0)
async def get_blacklist(request: Request):
    """黑名单列表。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    return {"code": "ok", "data": orchestrator.seed_manager.get_blacklist()}


# --- 统计 ---


@router.get("/stats")
@require_level(0)
async def get_stats(request: Request):
    """统计信息。"""
    container: ServiceContainer = request.app.state.container
    orchestrator = container.get("crawler")
    result = await orchestrator.get_stats()
    return {"code": "ok", "data": result}
