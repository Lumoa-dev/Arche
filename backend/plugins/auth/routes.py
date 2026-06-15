"""认证插件 —— 路由：注册、登录、登出、获取当前用户、刷新 token。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from backend.core.container import ServiceContainer
from backend.core.middleware import require_level, require_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- 请求体模型 ---
class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=128, description="邮箱")
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    nickname: str = Field(..., min_length=1, max_length=64, description="昵称")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class LoginRequest(BaseModel):
    identity: str = Field(..., description="邮箱或用户名")
    password: str = Field(..., description="密码")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")


class UpdateUserRequest(BaseModel):
    level: int | None = Field(None, ge=0, le=10, description="用户等级")
    is_active: bool | None = Field(None, description="是否启用")
    nickname: str | None = Field(None, min_length=1, max_length=64, description="昵称")
    avatar: str | None = Field(None, max_length=1024, description="头像 URL")
    bio: str | None = Field(None, description="个人简介")
    links: list[str] | None = Field(None, description="个人链接列表")


class UpdateUserSettingsRequest(BaseModel):
    default_post_permission: str | None = Field(None, description="发帖默认权限等级")
    language: str | None = Field(None, description="界面语言偏好")
    theme: str | None = Field(None, description="界面主题")
    notify_comment_reply: bool | None = Field(None, description="评论回复通知")
    notify_like: bool | None = Field(None, description="点赞通知")
    notify_system: bool | None = Field(None, description="系统公告通知")
    privacy_show_online: bool | None = Field(None, description="展示在线状态")
    privacy_show_login_history: bool | None = Field(None, description="公开登录历史")
    privacy_show_badges: bool | None = Field(None, description="展示徽章")
    default_post_status: str | None = Field(None, description="发帖默认状态")
    auto_save_interval: int | None = Field(None, description="自动保存间隔（秒）")
    extras: dict | None = Field(None, description="扩展设置")


class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=128, description="邮箱")
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    nickname: str = Field(..., min_length=1, max_length=64, description="昵称")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    level: int | None = Field(None, ge=0, le=10, description="用户等级（默认 5）")


class SoftDeleteUserRequest(BaseModel):
    reason: str = Field(
        ...,
        pattern=r"^(violation|user_request)$",
        description="删号原因: violation(违规) / user_request(用户主动注销)",
    )
    expires_in_days: int = Field(
        ..., ge=30, le=90, description="永久清理过期天数: 30/60/90"
    )


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


# --- 页面权限请求体 ---
class SetPageComponentRequest(BaseModel):
    level: int = Field(..., ge=0, le=10, description="用户等级")
    page_name: str = Field(..., min_length=1, max_length=128, description="页面名称")
    component_name: str = Field(
        ..., min_length=1, max_length=128, description="组件名称"
    )
    visible: bool = Field(..., description="是否可见")


class SetPageBatchRequest(BaseModel):
    level: int = Field(..., ge=0, le=10, description="用户等级")
    page_name: str = Field(..., min_length=1, max_length=128, description="页面名称")
    visible: bool = Field(..., description="是否可见（页面下所有组件统一设置）")


# --- 路由 ---
@router.post("/register")
async def register(req: RegisterRequest, request: Request):
    """用户注册，默认 P5 等级。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.register(
        email=req.email,
        username=req.username,
        nickname=req.nickname,
        password=req.password,
    )
    return {"code": "ok", "message": "注册成功", "data": result}


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    """用户登录，返回 JWT token。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    # 获取客户端 IP 用于限流
    client_ip = request.client.host if request.client else ""
    result = await auth_service.login(
        identity=req.identity,
        password=req.password,
        client_ip=client_ip,
    )

    # 标记用户在线
    if container.is_available("session_tracker"):
        tracker = container.get("session_tracker")
        tracker.user_online(result["user"]["id"], result["user"]["username"])

    return {"code": "ok", "message": "登录成功", "data": result}


@router.post("/logout")
async def logout(request: Request):
    """用户登出。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    await auth_service.logout(token)

    # 标记用户离线
    if container.is_available("session_tracker"):
        from backend.core.middleware import get_current_user

        user = get_current_user(request)
        if user:
            tracker = container.get("session_tracker")
            tracker.user_offline(user["id"])

    return {"code": "ok", "message": "登出成功", "data": {}}


@router.get("/me")
async def get_me(request: Request):
    """获取当前登录用户信息（含页面组件权限映射）。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    user_level = user.get("level", 5)
    page_permissions = await auth_service.get_page_permissions(user_level)
    user["page_permissions"] = page_permissions
    return {"code": "ok", "message": "获取成功", "data": user}


@router.post("/refresh")
async def refresh(req: RefreshRequest, request: Request):
    """刷新 access token。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.refresh_token(req.refresh_token)
    return {"code": "ok", "message": "刷新成功", "data": result}


# --- 用户设置 ---
@router.get("/settings")
async def get_my_settings(request: Request):
    """获取当前用户设置。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.get_user_settings(uuid.UUID(user["id"]))
    return {"code": "ok", "message": "获取成功", "data": result}


@router.put("/settings")
async def update_my_settings(req: UpdateUserSettingsRequest, request: Request):
    """更新当前用户设置。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    result = await auth_service.update_user_settings(uuid.UUID(user["id"]), updates)
    return {"code": "ok", "message": "更新成功", "data": result}


# --- 登录历史 ---
@router.get("/login-history")
async def get_my_login_history(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """获取当前用户登录历史。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.get_login_history(
        uuid.UUID(user["id"]), page=page, page_size=page_size
    )
    return {"code": "ok", "message": "获取成功", "data": result}


# --- 管理端点（P0） ---
@router.get("/users")
@require_level(0)
async def list_users(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str | None = Query(None, description="状态过滤：active/disabled"),
):
    """用户列表（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.list_users(
        page=page, page_size=page_size, status_filter=status
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/users/{user_id}")
@require_level(0)
async def get_user(user_id: str, request: Request):
    """用户详情（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.get_user(uuid.UUID(user_id))
    if not result:
        return {"code": "not_found", "message": "用户不存在", "data": None}
    return {"code": "ok", "message": "获取成功", "data": result}


@router.put("/users/{user_id}")
@require_level(0)
async def update_user(user_id: str, req: UpdateUserRequest, request: Request):
    """修改用户信息（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.update_user(
        uuid.UUID(user_id),
        level=req.level,
        is_active=req.is_active,
        nickname=req.nickname,
        avatar=req.avatar,
        bio=req.bio,
        links=req.links,
    )
    return {"code": "ok", "message": "修改成功", "data": result}


@router.delete("/users/{user_id}")
@require_level(0)
async def delete_user(user_id: str, request: Request):
    """禁用用户（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    await auth_service.disable_user(uuid.UUID(user_id))
    return {"code": "ok", "message": "用户已禁用", "data": {}}


@router.post("/users/{user_id}/disable")
@require_level(0)
async def disable_user(user_id: str, request: Request):
    """禁用用户（P0）。不能禁用自己。"""
    current_user = require_user(request)
    if str(current_user["id"]) == user_id:
        return {"code": "forbidden", "message": "不能禁用自己", "data": {}}

    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.disable_user(uuid.UUID(user_id))
    return {"code": "ok", "message": "用户已禁用", "data": result}


@router.post("/users/{user_id}/enable")
@require_level(0)
async def enable_user(user_id: str, request: Request):
    """启用用户（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.enable_user(uuid.UUID(user_id))
    return {"code": "ok", "message": "用户已启用", "data": result}


@router.post("/users/{user_id}/soft-delete")
@require_level(0)
async def soft_delete_user(user_id: str, req: SoftDeleteUserRequest, request: Request):
    """软删除用户（P0）：标记删除状态、原因和过期时间。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.soft_delete_user(
        uuid.UUID(user_id),
        reason=req.reason,
        expires_in_days=req.expires_in_days,
    )
    return {"code": "ok", "message": "用户已标记删除", "data": result}


@router.post("/users/{user_id}/reset-password")
@require_level(0)
async def reset_password(
    user_id: uuid.UUID, req: ResetPasswordRequest, request: Request
):
    """管理员重置用户密码（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.reset_password(user_id, new_password=req.new_password)
    return {"code": "ok", "message": "密码重置成功", "data": result}


@router.post("/admin/users")
@require_level(0)
async def admin_create_user(req: CreateUserRequest, request: Request):
    """管理员手动创建用户（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.admin_create_user(
        email=req.email,
        username=req.username,
        nickname=req.nickname,
        password=req.password,
        level=req.level if req.level is not None else 5,
    )
    return {"code": "ok", "message": "创建成功", "data": result}


@router.get("/stats")
@require_level(0)
async def get_user_stats(request: Request):
    """用户统计概览（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.get_user_stats()
    return {"code": "ok", "message": "获取成功", "data": result}


# ── 页面组件权限管理 ──


@router.get("/permissions/pages")
async def get_page_permissions(
    request: Request,
    level: int | None = Query(
        None, ge=0, le=10, description="用户等级，不传则用当前用户等级"
    ),
):
    """获取指定 level 的页面组件权限映射。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")

    # 如果未指定 level，用当前用户的 level
    if level is None:
        user = require_user(request)
        level = user.get("level", 5)

    result = await auth_service.get_page_permissions(level)
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/permissions/levels")
@require_level(0)
async def get_permission_levels(request: Request):
    """获取所有已配置权限数据的 level 列表（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    result = await auth_service.get_all_permission_levels()
    return {"code": "ok", "message": "获取成功", "data": result}


@router.put("/permissions/pages")
@require_level(0)
async def set_page_component(req: SetPageComponentRequest, request: Request):
    """设置单个页面组件的可见性（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    await auth_service.set_page_component(
        level=req.level,
        page_name=req.page_name,
        component_name=req.component_name,
        visible=req.visible,
    )
    return {"code": "ok", "message": "更新成功", "data": {}}


@router.put("/permissions/pages/batch")
@require_level(0)
async def set_page_batch(req: SetPageBatchRequest, request: Request):
    """批量设置指定页面下所有组件的可见性（P0）。"""
    container: ServiceContainer = request.app.state.container
    auth_service = container.get("auth")
    await auth_service.set_page_defaults(
        level=req.level,
        page_name=req.page_name,
        visible_default=req.visible,
    )
    return {"code": "ok", "message": "批量更新成功", "data": {}}
