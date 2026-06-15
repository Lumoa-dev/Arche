"""GitHub 代理插件 —— 反向代理路由。

代理 GitHub API 和静态资源，支持缓存和 P1 权限控制。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from backend.core.container import ServiceContainer
from backend.core.middleware import require_level

router = APIRouter(prefix="/api/github", tags=["github_proxy"])


@router.get("/health/status")
@require_level(1)
async def get_health_status(request: Request):
    """检查 GitHub 代理健康状态，检测 CLI 和 HTTP 模式是否可用。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("github")

    result = {
        "http": {"available": False, "error": None},
        "cli": {"available": False, "error": None},
    }

    # 测试 CLI
    try:
        await service.cli_service._run_gh_command("GET", "/rate_limit", {})
        result["cli"]["available"] = True
    except Exception as e:
        result["cli"]["error"] = str(e)  # type: ignore[assignment]

    # 测试 HTTP (跳过，因为可能超时)
    result["http"]["available"] = True
    result["http"]["note"] = "HTTP 模式需手动测试"  # type: ignore[assignment]

    return {
        "code": "ok",
        "message": "健康检查完成",
        "data": result,
    }


@router.get("/raw/{path:path}")
@require_level(1)
async def proxy_raw(path: str, request: Request, mode: str = "auto"):
    """代理 GitHub 静态资源（需 P1 权限）。

    转发到 https://raw.githubusercontent.com/{path}，
    适用于 raw 文件内容（图片、文本等）。

    Args:
        mode: 模式选择 - auto（默认）, http, cli
    """
    container: ServiceContainer = request.app.state.container
    service = container.get("github")

    result = await service.proxy_raw_content(path=path, mode=mode)

    response_headers = {
        "X-GitHub-Cache": "HIT" if result["cached"] else "MISS",
        "X-GitHub-Mode": result.get("mode", mode),
    }

    content_type = result["headers"].get("Content-Type", "application/octet-stream")
    response_headers["Content-Type"] = content_type

    return Response(
        content=result["data"],
        status_code=result["status_code"],
        headers=response_headers,
    )


@router.post("/cache/clear")
@require_level(1)
async def clear_cache(request: Request):
    """清空代理缓存（需 P1 权限）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("github")
    count = service.clear_cache()
    return {
        "code": "ok",
        "message": f"已清空 HTTP: {count['http']}, CLI: {count['cli']} 条缓存",
        "data": {"cleared": count},
    }


async def _proxy_github_impl(
    path: str, request: Request, mode: str = "auto"
) -> JSONResponse:
    """反向代理 GitHub API 内部实现。"""
    from backend.core.middleware import require_user

    container: ServiceContainer = request.app.state.container
    service = container.get("github")
    user = require_user(request)

    query_params = dict(request.query_params)
    query_params.pop("mode", None)

    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()

    result = await service.proxy_request(
        method=request.method,
        path=path,
        query_params=query_params,
        headers=dict(request.headers),
        body=body,
        user_id=user["id"],
        mode=mode,
    )

    response_headers = {
        "X-GitHub-Cache": "HIT" if result["cached"] else "MISS",
        "X-GitHub-Mode": result.get("mode", mode),
    }
    if result.get("fallback_from"):
        response_headers["X-GitHub-Fallback"] = result["fallback_from"]
        response_headers["X-GitHub-Fallback-Reason"] = result.get("fallback_reason", "")

    return JSONResponse(
        status_code=result["status_code"],
        content=result["data"],
        headers=response_headers,
    )


@router.get("/{path:path}")
@require_level(1)
async def proxy_github_get(path: str, request: Request, mode: str = "auto"):
    """反向代理 GitHub API - GET（需 P1 权限）。"""
    return await _proxy_github_impl(path, request, mode)


@router.post("/{path:path}")
@require_level(1)
async def proxy_github_post(path: str, request: Request, mode: str = "auto"):
    """反向代理 GitHub API - POST（需 P1 权限）。"""
    return await _proxy_github_impl(path, request, mode)


@router.put("/{path:path}")
@require_level(1)
async def proxy_github_put(path: str, request: Request, mode: str = "auto"):
    """反向代理 GitHub API - PUT（需 P1 权限）。"""
    return await _proxy_github_impl(path, request, mode)


@router.patch("/{path:path}")
@require_level(1)
async def proxy_github_patch(path: str, request: Request, mode: str = "auto"):
    """反向代理 GitHub API - PATCH（需 P1 权限）。"""
    return await _proxy_github_impl(path, request, mode)


@router.delete("/{path:path}")
@require_level(1)
async def proxy_github_delete(path: str, request: Request, mode: str = "auto"):
    """反向代理 GitHub API - DELETE（需 P1 权限）。"""
    return await _proxy_github_impl(path, request, mode)
