"""博客插件 —— API 路由。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from pydantic import BaseModel, Field

from backend.core.container import ServiceContainer
from backend.core.middleware import get_current_user, require_level, require_user

router = APIRouter(prefix="/api/blog", tags=["blog"])


# --- 请求体模型 ---
class CreatePostRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=256, description="标题")
    subtitles: list[str] | None = Field(None, description="副标题列表")
    introduction: str | None = Field(
        None, max_length=10000, description="引言（Markdown 富文本）"
    )
    paragraphs: list[dict] | None = Field(
        None, description="段落列表，每项含 content/type/heading/media_url/caption"
    )
    tags: list[str] = Field(default_factory=list, description="标签列表")
    cover_url: str | None = Field(None, max_length=1024, description="封面图片 URL")
    required_level: int = Field(
        default=5,
        ge=0,
        le=5,
        description="阅读所需最低 P 等级（0-5，数字越小权限越高）",
    )


class UpdatePostRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=256, description="标题")
    subtitles: list[str] | None = Field(None, description="副标题列表")
    introduction: str | None = Field(
        None, max_length=10000, description="引言（Markdown 富文本）"
    )
    paragraphs: list[dict] | None = Field(None, description="段落列表")
    cover_url: str | None = Field(None, max_length=1024, description="封面图片 URL")
    required_level: int | None = Field(
        None, ge=0, le=5, description="阅读所需最低 P 等级（0-5，数字越小权限越高）"
    )
    tags: list[str] | None = Field(None, description="标签列表")


class CreateCommentRequest(BaseModel):
    content: str = Field(..., min_length=1, description="评论内容")
    parent_id: str | None = Field(None, description="父评论 ID（回复）")


class CreateReportRequest(BaseModel):
    post_id: str = Field(..., description="被举报帖子 ID")
    reason: str | None = Field(None, max_length=500, description="举报原因")


# --- 公开路由：帖子列表/详情 ---
@router.get("/posts")
async def get_posts(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段"),
    status: str | None = Query(
        None, description="状态筛选（仅管理员可用，公开默认 published）"
    ),
    q: str | None = Query(None, description="搜索关键词（标题+内容）"),
    tag: str | None = Query(None, description="按标签筛选"),
):
    """帖子列表（支持搜索、标签和状态筛选，按权限过滤）。"""
    from backend.core.middleware import require_user as _require_user

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    user = get_current_user(request)
    user_level = user["level"] if user else None

    # 非管理员只能看到 published 的文章
    status_filter = status
    if status_filter and status_filter != "published":
        try:
            u = _require_user(request)
            if u.get("level", 5) > 0:
                status_filter = "published"
        except Exception:
            status_filter = "published"

    result = await blog_service.list_posts(
        page=page,
        page_size=page_size,
        status_filter=status_filter or "published",
        sort_by=sort_by,
        user_level=user_level,
        search_query=q,
        tag_filter=tag,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/posts/by-id/{post_id}")
async def get_post_by_id(post_id: str, request: Request):
    """按 ID 获取帖子详情（含标签，按权限过滤）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    user = get_current_user(request)
    user_level = user["level"] if user else None
    user_id = uuid.UUID(user["id"]) if user else None
    result = await blog_service.get_post_detail_by_id(
        uuid.UUID(post_id), user_level=user_level, user_id=user_id
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/posts/{slug}")
async def get_post(slug: str, request: Request):
    """帖子详情（按权限过滤 + 状态控制）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    user = get_current_user(request)
    user_level = user["level"] if user else None
    user_id = uuid.UUID(user["id"]) if user else None
    result = await blog_service.get_post_by_slug(
        slug, user_level=user_level, user_id=user_id
    )
    return {"code": "ok", "message": "获取成功", "data": result}


# --- 需登录：发帖 ---
@router.post("/posts")
async def create_post(req: CreatePostRequest, request: Request):
    """发帖（需登录，进入审核队列）。"""
    user = require_user(request)
    author_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.create_post(
        author_id=author_id,
        title=req.title,
        subtitles=req.subtitles,
        introduction=req.introduction,
        paragraphs_data=req.paragraphs,
        tags=req.tags,
        cover_url=req.cover_url,
        required_level=req.required_level,
        user_level=user["level"],
    )
    return {"code": "ok", "message": "发帖成功，等待审核", "data": result}


# --- 需登录：我的帖子 ---
@router.get("/my-posts")
async def get_my_posts(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str | None = Query(
        None, description="状态过滤：pending/published/rejected/draft"
    ),
):
    """我的帖子列表（需登录，包含所有状态）。"""
    user = require_user(request)
    author_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.list_my_posts(
        author_id=author_id,
        page=page,
        page_size=page_size,
        status_filter=status,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


# --- 作者本人：编辑 ---
@router.put("/posts/{post_id}")
async def update_post(post_id: str, req: UpdatePostRequest, request: Request):
    """编辑帖子（作者本人）。"""
    user = require_user(request)
    author_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.update_post(
        post_id=uuid.UUID(post_id),
        author_id=author_id,
        title=req.title,
        subtitles=req.subtitles,
        introduction=req.introduction,
        paragraphs_data=req.paragraphs,
        cover_url=req.cover_url,
        required_level=req.required_level,
        tags=req.tags,
        user_level=user["level"],
    )
    return {"code": "ok", "message": "编辑成功，重新进入审核", "data": result}


# --- 作者本人或 P0：删除 ---
@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, request: Request):
    """删除帖子（作者本人 或 P0）。"""
    user = require_user(request)
    user_id = uuid.UUID(user["id"])
    user_level = user["level"]

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    await blog_service.delete_post(
        post_id=uuid.UUID(post_id),
        user_id=user_id,
        user_level=user_level,
    )
    return {"code": "ok", "message": "删除成功", "data": {}}


# --- 公开：评论列表 ---
@router.get("/posts/{post_id}/comments")
async def get_comments(
    post_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """评论列表（公开，按权限过滤帖子的 required_level）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    user = get_current_user(request)
    user_level = user["level"] if user else None
    result = await blog_service.list_comments(
        post_id=uuid.UUID(post_id),
        page=page,
        page_size=page_size,
        user_level=user_level,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


# --- 需登录：评论 ---
@router.post("/posts/{post_id}/comments")
async def create_comment(post_id: str, req: CreateCommentRequest, request: Request):
    """评论（需登录）。"""
    user = require_user(request)
    author_id = uuid.UUID(user["id"])

    parent_id = uuid.UUID(req.parent_id) if req.parent_id else None

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.create_comment(
        post_id=uuid.UUID(post_id),
        author_id=author_id,
        content=req.content,
        parent_id=parent_id,
    )
    return {"code": "ok", "message": "评论成功", "data": result}


# --- 段落查询（支持懒加载：limit/offset 控制） ---
@router.get("/posts/{post_id}/paragraphs")
async def get_post_paragraphs(
    post_id: str,
    request: Request,
    limit: int | None = Query(
        None, ge=1, le=100, description="限制段落数量（可选，用于懒加载）"
    ),
    offset: int = Query(0, ge=0, description="跳过的段落数（可选）"),
):
    """获取帖子的段落列表（按权限过滤 required_level）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    user = get_current_user(request)
    user_level = user["level"] if user else None
    result = await blog_service.get_post_paragraphs(
        post_id=uuid.UUID(post_id),
        limit=limit,
        offset=offset,
        user_level=user_level,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


# --- 段落评论（公开读，登录写） ---
@router.get("/posts/{post_id}/paragraph-comments/{paragraph_pid}")
async def get_paragraph_comments(
    post_id: str,
    paragraph_pid: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """段落评论列表（公开，按权限过滤 required_level）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    user = get_current_user(request)
    user_level = user["level"] if user else None
    result = await blog_service.get_paragraph_comments(
        post_id=uuid.UUID(post_id),
        paragraph_pid=paragraph_pid,
        page=page,
        page_size=page_size,
        user_level=user_level,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.post("/posts/{post_id}/paragraph-comments/{paragraph_pid}")
async def create_paragraph_comment(
    post_id: str, paragraph_pid: str, req: CreateCommentRequest, request: Request
):
    """段落评论（需登录）。"""
    user = require_user(request)
    author_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.create_paragraph_comment(
        post_id=uuid.UUID(post_id),
        paragraph_pid=paragraph_pid,
        author_id=author_id,
        content=req.content,
    )
    return {"code": "ok", "message": "评论成功", "data": result}


# --- 需登录：点赞 ---
@router.get("/posts/{post_id}/like-status")
async def get_like_status(post_id: str, request: Request):
    """获取点赞状态（需登录）。"""
    user = get_current_user(request)
    if not user:
        return {"code": "ok", "data": {"liked": False, "count": 0}}

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.get_like_status(
        post_id=uuid.UUID(post_id),
        user_id=uuid.UUID(user["id"]),
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.post("/posts/{post_id}/like")
async def toggle_like(post_id: str, request: Request):
    """点赞（需登录，幂等）。"""
    user = require_user(request)
    user_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.toggle_like(
        post_id=uuid.UUID(post_id),
        user_id=user_id,
    )
    return {"code": "ok", "message": "操作成功", "data": result}


# --- P0：审核管理 ---
@router.get("/moderation/pending")
@require_level(0)
async def get_pending_posts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """待审核列表（P0）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.list_pending_posts(
        page=page,
        page_size=page_size,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.post("/moderation/{post_id}/approve")
@require_level(0)
async def approve_post(post_id: str, request: Request):
    """通过审核（P0）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    user = require_user(request)
    result = await blog_service.approve_post(
        uuid.UUID(post_id), reviewer_id=uuid.UUID(user["id"])
    )
    return {"code": "ok", "message": "审核通过", "data": result}


@router.post("/moderation/{post_id}/reject")
@require_level(0)
async def reject_post(post_id: str, request: Request):
    """拒绝审核（P0）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    user = require_user(request)
    result = await blog_service.reject_post(
        uuid.UUID(post_id), reviewer_id=uuid.UUID(user["id"])
    )
    return {"code": "ok", "message": "审核拒绝", "data": result}


# 批量审核请求体
class BatchModerationRequest(BaseModel):
    post_ids: list[str] = Field(..., description="帖子 ID 列表")


@router.post("/moderation/batch-approve")
@require_level(0)
async def batch_approve_posts(req: BatchModerationRequest, request: Request):
    """批量通过审核（P0）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    success = 0
    failed = 0
    for post_id in req.post_ids:
        try:
            await blog_service.approve_post(uuid.UUID(post_id))
            success += 1
        except Exception:
            failed += 1
    return {
        "code": "ok",
        "message": f"成功 {success}，失败 {failed}",
        "data": {"success": success, "failed": failed},
    }


@router.post("/moderation/batch-reject")
@require_level(0)
async def batch_reject_posts(req: BatchModerationRequest, request: Request):
    """批量拒绝审核（P0）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    success = 0
    failed = 0
    for post_id in req.post_ids:
        try:
            await blog_service.reject_post(uuid.UUID(post_id))
            success += 1
        except Exception:
            failed += 1
    return {
        "code": "ok",
        "message": f"成功 {success}，失败 {failed}",
        "data": {"success": success, "failed": failed},
    }


# --- 需登录：收藏 ---
@router.post("/favorites/{post_id}")
async def add_favorite(post_id: str, request: Request):
    """收藏帖子（需登录）。"""
    user = require_user(request)
    user_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.add_favorite(
        post_id=uuid.UUID(post_id),
        user_id=user_id,
    )
    return {"code": "ok", "message": "收藏成功", "data": result}


@router.delete("/favorites/{post_id}")
async def remove_favorite(post_id: str, request: Request):
    """取消收藏（需登录）。"""
    user = require_user(request)
    user_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.remove_favorite(
        post_id=uuid.UUID(post_id),
        user_id=user_id,
    )
    return {"code": "ok", "message": "已取消收藏", "data": result}


@router.get("/favorites")
async def get_favorites(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """我的收藏列表（需登录）。"""
    user = require_user(request)
    user_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.list_favorites(
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/posts/{post_id}/favorite-status")
async def get_favorite_status(post_id: str, request: Request):
    """检查收藏状态（需登录）。"""
    user = get_current_user(request)
    if not user:
        return {"code": "ok", "data": {"favorited": False}}

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    favorited = await blog_service.check_favorite(
        post_id=uuid.UUID(post_id),
        user_id=uuid.UUID(user["id"]),
    )
    return {"code": "ok", "data": {"favorited": favorited}}


# --- 需登录：举报 ---
@router.post("/reports")
async def create_report(req: CreateReportRequest, request: Request):
    """举报（需登录）。"""
    user = require_user(request)
    reporter_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.create_report(
        post_id=uuid.UUID(req.post_id),
        reporter_id=reporter_id,
        reason=req.reason,
    )
    return {"code": "ok", "message": "举报成功", "data": result}


# --- 文件导入 ---


@router.post("/import")
async def import_post(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    required_level: int = Form(default=5),
    tags: str = Form(default=""),
):
    """从文件导入帖子（需登录）。"""
    user = require_user(request)
    author_id = uuid.UUID(user["id"])

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.import_post(
        file=file,
        author_id=author_id,
        user_level=user["level"],
        required_level=required_level,
        tags=tag_list,
    )
    return {
        "code": "ok",
        "message": "文件解析成功，请检查内容后保存发布",
        "data": result,
    }


@router.post("/upload-file")
async def upload_post_file(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
):
    """上传 TXT/MD 文件创建帖子（需登录）。"""
    user = require_user(request)
    author_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.import_post(
        file=file,
        author_id=author_id,
        user_level=user["level"],
    )
    return {"code": "ok", "message": "导入成功，等待审核", "data": result}


# --- 标签 ---


@router.get("/tags")
async def get_tags(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """标签列表（公开）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.list_tags(page=page, page_size=page_size)
    return {"code": "ok", "message": "获取成功", "data": result}


@router.post("/tags")
async def create_tag(
    request: Request,
    name: str = Query(..., min_length=1, max_length=64, description="标签名"),
):
    """创建标签（需登录）。"""
    require_user(request)
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.create_tag(name=name)
    return {"code": "ok", "message": "创建成功", "data": result}


@router.get("/posts/by-tag/{tag_name}")
async def get_posts_by_tag(
    tag_name: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """按标签查询帖子（按权限过滤）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    user = get_current_user(request)
    user_level = user["level"] if user else None
    result = await blog_service.get_posts_by_tag(
        tag_name=tag_name,
        page=page,
        page_size=page_size,
        user_level=user_level,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/posts/{post_id}/tags")
async def get_post_tags(post_id: str, request: Request):
    """获取帖子标签（公开，按权限过滤 required_level）。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    user = get_current_user(request)
    user_level = user["level"] if user else None
    tags = await blog_service.get_post_tags(
        uuid.UUID(post_id), user_level=user_level
    )
    return {"code": "ok", "message": "获取成功", "data": {"tags": tags}}


@router.post("/posts/{post_id}/tags")
async def add_tag_to_post(
    post_id: str,
    request: Request,
    name: str = Query(..., min_length=1, max_length=64),
):
    """给帖子加标签（作者本人）。"""
    user = require_user(request)
    user_id = uuid.UUID(user["id"])
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.add_tag_to_post(
        post_id=uuid.UUID(post_id),
        tag_name=name,
        user_id=user_id,
    )
    return {"code": "ok", "message": "添加成功", "data": result}


@router.delete("/posts/{post_id}/tags/{tag_name}")
async def remove_tag_from_post(post_id: str, tag_name: str, request: Request):
    """从帖子移除标签（作者本人）。"""
    user = require_user(request)
    user_id = uuid.UUID(user["id"])
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    await blog_service.remove_tag_from_post(
        post_id=uuid.UUID(post_id),
        tag_name=tag_name,
        user_id=user_id,
    )
    return {"code": "ok", "message": "移除成功", "data": {}}


# ── 统计端点（P0） ──


@router.get("/stats/daily-trend")
@require_level(0)
async def get_daily_trend(
    request: Request,
    days: int = 7,
):
    """每日曝光量趋势（P0）。返回最近 N 天的浏览量、帖子新增量。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.get_daily_trend(days=days)
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/admin/hot-posts")
@require_level(0)
async def get_hot_posts(
    request: Request,
    limit: int = Query(10, ge=5, le=50),
):
    """内容话题热度排行（P0）。按浏览量降序，含点赞数和评论数。"""
    container: ServiceContainer = request.app.state.container
    blog_service = container.get("blog")
    result = await blog_service.get_hot_posts(limit=limit)
    return {"code": "ok", "message": "获取成功", "data": result}
