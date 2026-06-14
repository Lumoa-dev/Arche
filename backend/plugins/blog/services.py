"""博客插件 —— 服务层。"""

from __future__ import annotations

import io
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import delete, func, select, text
from fastapi import UploadFile

from backend.core.middleware import AppError

from .models import (
    BlogPost,
    BlogParagraph,
    BlogComment,
    BlogLike,
    BlogReport,
    BlogTag,
    BlogPostTag,
    BlogFavorite,
    ModerationRecord,
    PostFile,
)

MAX_TAGS_PER_POST = 50


def can_user_see_post(required_level: int, user_level: int) -> bool:
    """判断用户是否有权限查看帖子（用户等级 <= 帖子要求等级则可看）。"""
    return user_level <= required_level


class BlogService:
    """博客服务：帖子 CRUD、评论、点赞、审核、举报。"""

    def __init__(self, container):
        self.container = container
        db = container.get("db")
        self.session_factory = db["session_factory"]

    # --- Slug 生成 ---

    async def generate_slug(self, title: str, exclude_slug: str | None = None) -> str:
        """异步生成唯一 slug。"""
        slug = re.sub(r"[^\w一-鿿-]", "-", title.lower().strip())
        slug = re.sub(r"-+", "-", slug).strip("-")
        if not slug:
            slug = "post"

        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogPost).where(BlogPost.slug == slug)
            )
            existing = result.scalar_one_or_none()

        if existing and existing.slug != (exclude_slug or ""):
            counter = 1
            while True:
                candidate = f"{slug}-{counter}"
                async with self.session_factory() as session:
                    result = await session.execute(
                        select(BlogPost).where(BlogPost.slug == candidate)
                    )
                    if not result.scalar_one_or_none():
                        return candidate
                    counter += 1

        return slug

    # --- 帖子 CRUD ---

    async def list_posts(
        self,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = "published",
        sort_by: str = "created_at",
        user_level: int | None = None,
        search_query: str | None = None,
        tag_filter: str | None = None,
    ) -> dict:
        """获取帖子列表（公开，分页，支持搜索和标签筛选）。"""
        offset = (page - 1) * page_size

        from backend.plugins.auth.models import User

        async with self.session_factory() as session:
            query = select(BlogPost)
            count_query = select(func.count()).select_from(BlogPost)

            if status_filter:
                query = query.where(BlogPost.status == status_filter)
                count_query = count_query.where(BlogPost.status == status_filter)

            # 搜索过滤（按标题）
            if search_query:
                search_pattern = f"%{search_query}%"
                search_filter = BlogPost.title.ilike(search_pattern)
                query = query.where(search_filter)
                count_query = count_query.where(search_filter)

            # 标签筛选
            if tag_filter:
                tag_posts = (
                    select(BlogPostTag.post_id)
                    .join(BlogTag, BlogTag.id == BlogPostTag.tag_id)
                    .where(BlogTag.name == tag_filter)
                )
                query = query.where(BlogPost.id.in_(tag_posts))
                count_query = count_query.where(BlogPost.id.in_(tag_posts))

            # 权限过滤：用户只能看到 required_level >= user_level 的帖子
            if user_level is not None:
                query = query.where(BlogPost.required_level >= user_level)
                count_query = count_query.where(BlogPost.required_level >= user_level)

            # 总数
            total_result = await session.execute(count_query)
            total = total_result.scalar_one()

            # 排序
            order_col = getattr(BlogPost, sort_by, BlogPost.created_at)
            query = query.order_by(order_col.desc())
            query = query.offset(offset).limit(page_size)

            result = await session.execute(query)
            posts = result.scalars().all()

            # 批量获取作者信息和点赞数
            if posts:
                author_ids = [p.author_id for p in posts]
                author_result = await session.execute(
                    select(User.id, User.username).where(User.id.in_(author_ids))
                )
                author_map = {row.id: row.username for row in author_result.all()}

                likes_result = await session.execute(
                    select(BlogLike.post_id, func.count(BlogLike.id))
                    .where(BlogLike.post_id.in_([p.id for p in posts]))
                    .group_by(BlogLike.post_id)
                )
                likes_map = {row.post_id: row.count for row in likes_result.all()}
            else:
                author_map = {}
                likes_map = {}

            return {
                "items": [
                    self._post_to_dict(
                        p,
                        author_username=author_map.get(p.author_id),
                        likes_count=likes_map.get(p.id, 0),
                    )
                    for p in posts
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    async def list_my_posts(
        self,
        author_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
    ) -> dict:
        """我的帖子列表（包含所有状态，供作者查看）。"""
        from backend.plugins.auth.models import User

        offset = (page - 1) * page_size

        async with self.session_factory() as session:
            query = select(BlogPost).where(BlogPost.author_id == author_id)
            count_query = (
                select(func.count())
                .select_from(BlogPost)
                .where(BlogPost.author_id == author_id)
            )

            if status_filter:
                query = query.where(BlogPost.status == status_filter)
                count_query = count_query.where(BlogPost.status == status_filter)

            # 排序
            query = query.order_by(BlogPost.created_at.desc())
            query = query.offset(offset).limit(page_size)

            # 总数
            total_result = await session.execute(count_query)
            total = total_result.scalar_one()

            result = await session.execute(query)
            posts = result.scalars().all()

            if not posts:
                return {
                    "items": [],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }

            # 获取作者信息
            author_result = await session.execute(
                select(User.username).where(User.id == author_id)
            )
            author_row = author_result.scalar_one_or_none()
            author_username = author_row if author_row else "未知"

            # 获取点赞数
            likes_result = await session.execute(
                select(BlogLike.post_id, func.count(BlogLike.id))
                .where(BlogLike.post_id.in_([p.id for p in posts]))
                .group_by(BlogLike.post_id)
            )
            likes_map = {row.post_id: row.count for row in likes_result.all()}

            return {
                "items": [
                    self._post_to_dict(
                        p,
                        author_username=author_username,
                        likes_count=likes_map.get(p.id, 0),
                    )
                    for p in posts
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    async def get_post_by_slug(
        self,
        slug: str,
        user_level: int | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        """根据 slug 获取帖子详情。

        权限控制：
        - published 帖子：公开可见（按 required_level 过滤）
        - 非 published 帖子：仅作者本人和 P0 可见
        - 浏览量：仅 published 帖子，且不计作者本人和审核人员的访问
        """
        from backend.plugins.auth.models import User

        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogPost).where(BlogPost.slug == slug)
            )
            post = result.scalar_one_or_none()
            if not post:
                raise AppError("帖子不存在", code="post_not_found", status_code=404)

            # required_level 权限检查
            if user_level is not None and not can_user_see_post(
                post.required_level, user_level
            ):
                raise AppError(
                    "无权查看此帖子", code="permission_denied", status_code=403
                )

            # 状态检查：非 published 只允许作者和 P0 查看
            is_author = user_id is not None and post.author_id == user_id
            is_admin = user_level is not None and user_level == 0
            if post.status != "published" and not is_author and not is_admin:
                raise AppError("帖子不存在", code="post_not_found", status_code=404)

            # 浏览量：仅 published 帖子，不计作者本人和审核人员
            should_count_view = (
                post.status == "published" and not is_author and not is_admin
            )
            if should_count_view:
                try:
                    # 使用原子 SQL 更新浏览量，避免 SQLite 并发写冲突
                    await session.execute(
                        text("UPDATE blog_posts SET views = views + 1 WHERE id = :id"),
                        {"id": post.id},
                    )
                    await session.commit()
                    post.views += 1  # 同步本地对象
                except Exception:
                    await session.rollback()
                    # 浏览量更新失败不阻碍帖子正常返回

            # 查询作者用户名
            author_result = await session.execute(
                select(User.username).where(User.id == post.author_id)
            )
            author_username = author_result.scalar_one_or_none()

            post_dict = self._post_to_dict(post, author_username=author_username)
            post_dict["tags"] = await self.get_post_tags(post.id)
            return post_dict

    async def get_post_by_id(self, post_id: uuid.UUID) -> BlogPost:
        """根据 ID 获取帖子模型对象。"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            if not post:
                raise AppError("帖子不存在", code="post_not_found", status_code=404)
            return post

    async def get_post_detail_by_id(
        self,
        post_id: uuid.UUID,
        user_level: int | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        """根据 ID 获取帖子详情（含标签，按权限过滤）。"""
        from backend.plugins.auth.models import User

        post = await self.get_post_by_id(post_id)

        # required_level 权限检查
        if user_level is not None and not can_user_see_post(
            post.required_level, user_level
        ):
            raise AppError("无权查看此帖子", code="permission_denied", status_code=403)

        # 状态检查
        is_author = user_id is not None and post.author_id == user_id
        is_admin = user_level is not None and user_level == 0
        if post.status != "published" and not is_author and not is_admin:
            raise AppError("帖子不存在", code="post_not_found", status_code=404)

        # 查询作者用户名
        async with self.session_factory() as session:
            author_result = await session.execute(
                select(User.username).where(User.id == post.author_id)
            )
            author_username = author_result.scalar_one_or_none()

        post_dict = self._post_to_dict(post, author_username=author_username)
        post_dict["tags"] = await self.get_post_tags(post.id)
        return post_dict

    async def create_post(
        self,
        author_id: uuid.UUID,
        title: str,
        subtitles: list[str] | None = None,
        introduction: list[dict] | None = None,
        paragraphs_data: list[dict] | None = None,
        tags: list[str] | None = None,
        cover_url: str | None = None,
        required_level: int = 5,
        user_level: int = 5,
    ) -> dict:
        """创建帖子，默认进入审核队列（status=pending）。"""
        from backend.plugins.auth.models import User
        from backend.plugins.blog.sensitive_words import get_filter

        # 权限等级验证：用户不能设置高于自身等级的可见门槛
        if required_level < user_level:
            raise AppError(
                f"无权设置 P{required_level} 权限，最高可设置 P{user_level}",
                code="access_level_too_high",
                status_code=403,
            )

        # 敏感词检查
        word_filter = get_filter()
        text_to_check = title
        if paragraphs_data:
            text_to_check += " " + " ".join(
                p.get("content", "") for p in paragraphs_data
            )
        passed, matched_words = word_filter.check(text_to_check)
        if not passed:
            raise AppError(
                f"内容包含敏感词: {', '.join(matched_words)}",
                code="sensitive_word",
                status_code=400,
            )

        slug_base = re.sub(r"[^\w一-鿿-]", "-", title.lower().strip())
        slug_base = re.sub(r"-+", "-", slug_base).strip("-") or "post"

        async with self.session_factory() as session:
            # 生成唯一 slug（同一 session 内查询）
            result = await session.execute(
                select(BlogPost).where(BlogPost.slug == slug_base)
            )
            existing = result.scalar_one_or_none()
            slug = slug_base
            if existing:
                counter = 1
                while True:
                    candidate = f"{slug_base}-{counter}"
                    result = await session.execute(
                        select(BlogPost).where(BlogPost.slug == candidate)
                    )
                    if not result.scalar_one_or_none():
                        slug = candidate
                        break
                    counter += 1

            post = BlogPost(
                author_id=author_id,
                title=title,
                slug=slug,
                cover_url=cover_url,
                introduction=introduction,
                subtitles=subtitles,
                status="pending",
                required_level=required_level,
            )
            session.add(post)
            await session.flush()  # 获取 post.id

            # 创建段落
            if paragraphs_data:
                paragraph_ids = []
                for i, pdata in enumerate(paragraphs_data):
                    pid = f"{str(post.id)[:8]}_{str(i + 1).zfill(3)}"
                    paragraph_ids.append(pid)
                    paragraph = BlogParagraph(
                        pid=pid,
                        post_id=post.id,
                        content=pdata.get("content", ""),
                        type=pdata.get("type", "text"),
                        heading=pdata.get("heading"),
                        media_url=pdata.get("media_url"),
                        caption=pdata.get("caption"),
                        word_count=len(pdata.get("content", "")),
                    )
                    session.add(paragraph)
                post.paragraph_ids = paragraph_ids

            # 处理标签（同一 session）
            if tags:
                for tag_name in tags[:MAX_TAGS_PER_POST]:
                    normalized_name = tag_name.strip().lower()
                    if not normalized_name:
                        continue
                    tag_result = await session.execute(
                        select(BlogTag).where(
                            func.lower(BlogTag.name) == normalized_name
                        )
                    )
                    tag = tag_result.scalar_one_or_none()
                    if not tag:
                        try:
                            tag = BlogTag(name=normalized_name)
                            session.add(tag)
                            await session.flush()
                        except Exception:
                            # 并发插入导致冲突，重新查询
                            await session.rollback()
                            tag_result = await session.execute(
                                select(BlogTag).where(
                                    func.lower(BlogTag.name) == normalized_name
                                )
                            )
                            tag = tag_result.scalar_one_or_none()
                            if not tag:
                                continue
                    session.add(BlogPostTag(post_id=post.id, tag_id=tag.id))

            await session.commit()
            await session.refresh(post)

            # 获取作者名
            author_result = await session.execute(
                select(User.username).where(User.id == author_id)
            )
            author_username = author_result.scalar_one_or_none()

            result = self._post_to_dict(post, author_username=author_username)
            result["tags"] = await self.get_post_tags(post.id)
            return result

    async def update_post(
        self,
        post_id: uuid.UUID,
        author_id: uuid.UUID,
        title: str | None = None,
        subtitles: list[str] | None = None,
        introduction: list[dict] | None = None,
        paragraphs_data: list[dict] | None = None,
        required_level: int | None = None,
        tags: list[str] | None = None,
        cover_url: str | None = None,
        user_level: int = 5,
    ) -> dict:
        """编辑帖子（仅作者本人）。"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            if not post:
                raise AppError("帖子不存在", code="post_not_found", status_code=404)
            if post.author_id != author_id:
                raise AppError(
                    "无权限编辑此帖子", code="permission_denied", status_code=403
                )

            if title is not None:
                post.title = title
                # 重新生成 slug
                post.slug = await self.generate_slug(title, exclude_slug=post.slug)
            if introduction is not None:
                post.introduction = introduction
            if subtitles is not None:
                post.subtitles = subtitles
            if cover_url is not None:
                post.cover_url = cover_url
            if paragraphs_data is not None:
                # 删除旧段落
                await session.execute(
                    delete(BlogParagraph).where(BlogParagraph.post_id == post_id)
                )
                # 创建新段落
                paragraph_ids = []
                for i, pdata in enumerate(paragraphs_data):
                    pid = f"{str(post.id)[:8]}_{str(i + 1).zfill(3)}"
                    paragraph_ids.append(pid)
                    paragraph = BlogParagraph(
                        pid=pid,
                        post_id=post.id,
                        content=pdata.get("content", ""),
                        type=pdata.get("type", "text"),
                        heading=pdata.get("heading"),
                        media_url=pdata.get("media_url"),
                        caption=pdata.get("caption"),
                        word_count=len(pdata.get("content", "")),
                    )
                    session.add(paragraph)
                post.paragraph_ids = paragraph_ids
            if required_level is not None:
                # 权限等级验证：用户不能设置高于自身等级的可见门槛
                if required_level < user_level:
                    raise AppError(
                        f"无权设置 P{required_level} 权限，最高可设置 P{user_level}",
                        code="access_level_too_high",
                        status_code=403,
                    )
                post.required_level = required_level
            # 处理标签更新
            if tags is not None:
                # 删除旧的标签关联
                await session.execute(
                    delete(BlogPostTag).where(BlogPostTag.post_id == post_id)
                )
                # 创建新的标签关联
                for tag_name in tags[:MAX_TAGS_PER_POST]:
                    normalized_name = tag_name.strip().lower()
                    if not normalized_name:
                        continue
                    tag_result = await session.execute(
                        select(BlogTag).where(
                            func.lower(BlogTag.name) == normalized_name
                        )
                    )
                    tag = tag_result.scalar_one_or_none()
                    if not tag:
                        try:
                            tag = BlogTag(name=normalized_name)
                            session.add(tag)
                            await session.flush()
                        except Exception:
                            await session.rollback()
                            tag_result = await session.execute(
                                select(BlogTag).where(
                                    func.lower(BlogTag.name) == normalized_name
                                )
                            )
                            tag = tag_result.scalar_one_or_none()
                            if not tag:
                                continue
                    session.add(BlogPostTag(post_id=post.id, tag_id=tag.id))
            # 仅标题变更才重新进入审核
            if title is not None:
                post.status = "pending"

            await session.commit()
            await session.refresh(post)

            return self._post_to_dict(post)

    async def delete_post(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
        user_level: int,
    ) -> None:
        """删除帖子（作者本人 或 P0）。"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            if not post:
                raise AppError("帖子不存在", code="post_not_found", status_code=404)

            if post.author_id != user_id and user_level != 0:
                raise AppError(
                    "无权限删除此帖子", code="permission_denied", status_code=403
                )

            # 删除关联数据
            await session.execute(
                delete(BlogParagraph).where(BlogParagraph.post_id == post_id)
            )
            await session.execute(
                delete(BlogComment).where(BlogComment.post_id == post_id)
            )
            await session.execute(delete(BlogLike).where(BlogLike.post_id == post_id))
            await session.execute(
                delete(BlogReport).where(BlogReport.post_id == post_id)
            )
            await session.execute(
                delete(BlogPostTag).where(BlogPostTag.post_id == post_id)
            )
            await session.delete(post)
            await session.commit()

    # --- 段落查询 ---

    async def get_post_paragraphs(
        self,
        post_id: uuid.UUID,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict]:
        """获取帖子的段落列表，按 paragraph_ids 顺序返回。"""
        async with self.session_factory() as session:
            post_result = await session.execute(
                select(BlogPost.paragraph_ids).where(BlogPost.id == post_id)
            )
            row = post_result.one_or_none()
            if not row:
                return []
            paragraph_ids = row[0] or []

            if offset > 0 or limit is not None:
                paragraph_ids = paragraph_ids[
                    offset : offset + limit if limit else None
                ]

            if not paragraph_ids:
                return []

            result = await session.execute(
                select(BlogParagraph).where(BlogParagraph.pid.in_(paragraph_ids))
            )
            para_map = {p.pid: p for p in result.scalars().all()}

            return [
                {
                    "pid": pid,
                    "content": para_map[pid].content if pid in para_map else "",
                    "type": para_map[pid].type if pid in para_map else "text",
                    "word_count": para_map[pid].word_count if pid in para_map else 0,
                    "heading": para_map[pid].heading if pid in para_map else None,
                    "media_url": para_map[pid].media_url if pid in para_map else None,
                    "caption": para_map[pid].caption if pid in para_map else None,
                }
                for pid in paragraph_ids
                if pid in para_map
            ]

    # --- 评论 ---

    async def list_comments(
        self,
        post_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """获取评论列表（公开）。"""
        # 验证帖子存在
        await self.get_post_by_id(post_id)

        from backend.plugins.auth.models import User

        offset = (page - 1) * page_size

        async with self.session_factory() as session:
            count_result = await session.execute(
                select(func.count()).where(BlogComment.post_id == post_id)
            )
            total = count_result.scalar_one()

            result = await session.execute(
                select(BlogComment)
                .where(BlogComment.post_id == post_id)
                .order_by(BlogComment.created_at.asc())
                .offset(offset)
                .limit(page_size)
            )
            comments = result.scalars().all()

            # 批量获取作者信息
            if comments:
                author_ids = [c.author_id for c in comments]
                author_result = await session.execute(
                    select(User.id, User.username).where(User.id.in_(author_ids))
                )
                author_map = {row.id: row.username for row in author_result.all()}
            else:
                author_map = {}

            return {
                "items": [
                    self._comment_to_dict(
                        c, author_username=author_map.get(c.author_id)
                    )
                    for c in comments
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    async def create_comment(
        self,
        post_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
        parent_id: uuid.UUID | None = None,
    ) -> dict:
        """发表评论（需登录）。"""
        # 验证帖子存在
        await self.get_post_by_id(post_id)

        async with self.session_factory() as session:
            # 如果有 parent_id，验证父评论存在且属于同一帖子
            if parent_id is not None:
                result = await session.execute(
                    select(BlogComment).where(
                        BlogComment.id == parent_id,
                        BlogComment.post_id == post_id,
                    )
                )
                if not result.scalar_one_or_none():
                    raise AppError(
                        "父评论不存在", code="parent_comment_not_found", status_code=404
                    )

            comment = BlogComment(
                post_id=post_id,
                author_id=author_id,
                content=content,
                parent_id=parent_id,
            )
            session.add(comment)

            post_result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = post_result.scalar_one_or_none()
            if post:
                current = getattr(post, "comment_count", 0) or 0
                post.comment_count = current + 1
                session.add(post)

            await session.commit()
            await session.refresh(comment)

            return self._comment_to_dict(comment)

    # --- 段落评论 ---

    async def get_paragraph_comments(
        self,
        post_id: uuid.UUID,
        paragraph_pid: str,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """获取段落评论列表。"""
        from backend.plugins.auth.models import User

        offset = (page - 1) * page_size

        async with self.session_factory() as session:
            count_result = await session.execute(
                select(func.count()).where(
                    BlogComment.post_id == post_id,
                    BlogComment.paragraph_pid == paragraph_pid,
                )
            )
            total = count_result.scalar_one()

            result = await session.execute(
                select(BlogComment)
                .where(
                    BlogComment.post_id == post_id,
                    BlogComment.paragraph_pid == paragraph_pid,
                )
                .order_by(BlogComment.created_at.asc())
                .offset(offset)
                .limit(page_size)
            )
            comments = result.scalars().all()

            if comments:
                author_ids = [c.author_id for c in comments]
                author_result = await session.execute(
                    select(User.id, User.username).where(User.id.in_(author_ids))
                )
                author_map = {row.id: row.username for row in author_result.all()}
            else:
                author_map = {}

            return {
                "items": [
                    self._comment_to_dict(
                        c, author_username=author_map.get(c.author_id)
                    )
                    for c in comments
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    async def create_paragraph_comment(
        self,
        post_id: uuid.UUID,
        paragraph_pid: str,
        author_id: uuid.UUID,
        content: str,
    ) -> dict:
        """对某段落发表评论。"""
        await self.get_post_by_id(post_id)

        async with self.session_factory() as session:
            comment = BlogComment(
                post_id=post_id,
                author_id=author_id,
                content=content,
                paragraph_pid=paragraph_pid,
            )
            session.add(comment)

            post_result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = post_result.scalar_one_or_none()
            if post:
                current = getattr(post, "comment_count", 0) or 0
                post.comment_count = current + 1
                session.add(post)

            await session.commit()
            await session.refresh(comment)

            return self._comment_to_dict(comment)

    # --- 点赞 ---

    async def get_like_status(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """获取点赞状态（是否已点赞 + 点赞数）。"""
        await self.get_post_by_id(post_id)

        async with self.session_factory() as session:
            # 检查是否已点赞
            result = await session.execute(
                select(BlogLike).where(
                    BlogLike.post_id == post_id,
                    BlogLike.user_id == user_id,
                )
            )
            liked = result.scalar_one_or_none() is not None

            # 获取点赞总数
            count_result = await session.execute(
                select(func.count()).where(BlogLike.post_id == post_id)
            )
            count = count_result.scalar_one()

            return {"liked": liked, "count": count}

    async def toggle_like(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """点赞（幂等，重复调用取消点赞）。"""
        # 验证帖子存在
        await self.get_post_by_id(post_id)

        async with self.session_factory() as session:
            # 检查是否已点赞
            result = await session.execute(
                select(BlogLike).where(
                    BlogLike.post_id == post_id,
                    BlogLike.user_id == user_id,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # 取消点赞
                await session.delete(existing)
                post_result = await session.execute(
                    select(BlogPost).where(BlogPost.id == post_id)
                )
                post = post_result.scalar_one_or_none()
                if post:
                    current = getattr(post, "like_count", 0) or 0
                    post.like_count = max(0, current - 1)
                    session.add(post)
                await session.commit()
                return {"action": "unliked"}

            # 点赞
            like = BlogLike(post_id=post_id, user_id=user_id)
            session.add(like)
            post_result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = post_result.scalar_one_or_none()
            if post:
                current = getattr(post, "like_count", 0) or 0
                post.like_count = current + 1
                session.add(post)
            await session.commit()
            return {"action": "liked"}

    # --- 审核 ---

    async def list_pending_posts(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取待审核帖子列表（P0）。"""
        from backend.plugins.auth.models import User

        offset = (page - 1) * page_size

        async with self.session_factory() as session:
            count_result = await session.execute(
                select(func.count()).where(BlogPost.status == "pending")
            )
            total = count_result.scalar_one()

            result = await session.execute(
                select(BlogPost)
                .where(BlogPost.status == "pending")
                .order_by(BlogPost.created_at.asc())
                .offset(offset)
                .limit(page_size)
            )
            posts = result.scalars().all()

            # 批量获取作者信息
            if posts:
                author_ids = [p.author_id for p in posts]
                author_result = await session.execute(
                    select(User.id, User.username).where(User.id.in_(author_ids))
                )
                author_map = {row.id: row.username for row in author_result.all()}
            else:
                author_map = {}

            return {
                "items": [
                    self._post_to_dict(p, author_username=author_map.get(p.author_id))
                    for p in posts
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    async def approve_post(
        self, post_id: uuid.UUID, reviewer_id: uuid.UUID | None = None
    ) -> dict:
        """通过审核（P0）。"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            if not post:
                raise AppError("帖子不存在", code="post_not_found", status_code=404)
            if post.status not in ("pending", "under_review"):
                raise AppError(
                    f"帖子状态为 {post.status}，无法审核",
                    code="invalid_status",
                    status_code=400,
                )

            post.status = "published"

            from datetime import datetime, timezone
            from uuid import uuid4

            record = ModerationRecord(
                id=uuid4(),
                target_type="post",
                target_id=str(post.id),
                submitter_id=post.author_id,
                reviewer_id=reviewer_id,
                status="approved",
                reviewed_at=datetime.now(timezone.utc),
            )
            record.generate_sid("modr")
            session.add(record)

            await session.commit()
            await session.refresh(post)

            return self._post_to_dict(post)

    async def reject_post(
        self, post_id: uuid.UUID, reviewer_id: uuid.UUID | None = None
    ) -> dict:
        """拒绝审核（P0）。"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            if not post:
                raise AppError("帖子不存在", code="post_not_found", status_code=404)
            if post.status not in ("pending", "under_review"):
                raise AppError(
                    f"帖子状态为 {post.status}，无法审核",
                    code="invalid_status",
                    status_code=400,
                )

            post.status = "rejected"

            from datetime import datetime, timezone
            from uuid import uuid4

            record = ModerationRecord(
                id=uuid4(),
                target_type="post",
                target_id=str(post.id),
                submitter_id=post.author_id,
                reviewer_id=reviewer_id,
                status="rejected",
                reviewed_at=datetime.now(timezone.utc),
            )
            record.generate_sid("modr")
            session.add(record)

            await session.commit()
            await session.refresh(post)

            return self._post_to_dict(post)

    # --- 标签 ---

    async def list_tags(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """获取标签列表（公开，包含文章数量）。"""
        offset = (page - 1) * page_size

        async with self.session_factory() as session:
            count_result = await session.execute(
                select(func.count()).select_from(BlogTag)
            )
            total = count_result.scalar_one()

            result = await session.execute(
                select(BlogTag)
                .order_by(BlogTag.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            tags = result.scalars().all()

            # 批量获取每个标签的文章数量
            if tags:
                tag_ids = [t.id for t in tags]
                post_count_result = await session.execute(
                    select(BlogPostTag.tag_id, func.count(BlogPostTag.post_id))
                    .where(BlogPostTag.tag_id.in_(tag_ids))
                    .group_by(BlogPostTag.tag_id)
                )
                post_count_map = {
                    row.tag_id: row.count for row in post_count_result.all()
                }
            else:
                post_count_map = {}

            return {
                "items": [
                    {**self._tag_to_dict(t), "count": post_count_map.get(t.id, 0)}
                    for t in tags
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    async def create_tag(self, name: str) -> dict:
        """创建标签。"""
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise AppError("标签名不能为空", code="empty_tag_name", status_code=400)
        if len(normalized_name) > 64:
            raise AppError("标签名过长", code="tag_name_too_long", status_code=400)

        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogTag).where(func.lower(BlogTag.name) == normalized_name)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return self._tag_to_dict(existing)

            tag = BlogTag(name=normalized_name)
            session.add(tag)
            try:
                await session.commit()
            except Exception:
                # 并发插入导致冲突，重新查询
                await session.rollback()
                result = await session.execute(
                    select(BlogTag).where(func.lower(BlogTag.name) == normalized_name)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    return self._tag_to_dict(existing)
                raise

            await session.refresh(tag)
            return self._tag_to_dict(tag)

    async def get_tag_by_name(self, name: str) -> BlogTag | None:
        """根据名称获取标签。"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogTag).where(func.lower(BlogTag.name) == name.strip().lower())
            )
            return result.scalar_one_or_none()

    async def get_posts_by_tag(
        self,
        tag_name: str,
        page: int = 1,
        page_size: int = 20,
        user_level: int | None = None,
    ) -> dict:
        """按标签查询帖子列表。"""
        tag = await self.get_tag_by_name(tag_name)
        if not tag:
            raise AppError("标签不存在", code="tag_not_found", status_code=404)

        offset = (page - 1) * page_size

        async with self.session_factory() as session:
            count_query = (
                select(func.count())
                .select_from(BlogPostTag)
                .join(BlogPost, BlogPost.id == BlogPostTag.post_id)
                .where(
                    BlogPostTag.tag_id == tag.id,
                    BlogPost.status == "published",
                )
            )
            if user_level is not None:
                count_query = count_query.where(BlogPost.required_level >= user_level)
            total = (await session.execute(count_query)).scalar_one()

            query = (
                select(BlogPost)
                .join(BlogPostTag, BlogPost.id == BlogPostTag.post_id)
                .where(
                    BlogPostTag.tag_id == tag.id,
                    BlogPost.status == "published",
                )
                .order_by(BlogPost.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            if user_level is not None:
                query = query.where(BlogPost.required_level >= user_level)
            result = await session.execute(query)
            posts = result.scalars().all()

            return {
                "tag": self._tag_to_dict(tag),
                "items": [self._post_to_dict(p) for p in posts],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    async def add_tag_to_post(
        self,
        post_id: uuid.UUID,
        tag_name: str,
        user_id: uuid.UUID,
    ) -> dict:
        """给帖子添加标签（仅作者或 P0）。"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            if not post:
                raise AppError("帖子不存在", code="post_not_found", status_code=404)
            if post.author_id != user_id:
                raise AppError(
                    "无权限操作此帖子", code="permission_denied", status_code=403
                )

            # 检查标签数量上限
            tag_count_result = await session.execute(
                select(func.count())
                .select_from(BlogPostTag)
                .where(BlogPostTag.post_id == post_id)
            )
            tag_count = tag_count_result.scalar_one()
            if tag_count >= MAX_TAGS_PER_POST:
                raise AppError(
                    f"帖子标签数已达上限 ({MAX_TAGS_PER_POST})",
                    code="too_many_tags",
                    status_code=400,
                )

        # 获取或创建标签
        tag = await self.get_tag_by_name(tag_name)
        if not tag:
            tag_dict = await self.create_tag(tag_name)
            tag_id = uuid.UUID(tag_dict["id"])
        else:
            tag_dict = self._tag_to_dict(tag)
            tag_id = tag.id

        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogPostTag).where(
                    BlogPostTag.post_id == post_id,
                    BlogPostTag.tag_id == tag_id,
                )
            )
            if result.scalar_one_or_none():
                raise AppError("标签已存在", code="tag_already_exists", status_code=400)

            post_tag = BlogPostTag(post_id=post_id, tag_id=tag_id)
            session.add(post_tag)
            await session.commit()

            return {"tag": tag, "post_id": str(post_id)}

    async def remove_tag_from_post(
        self,
        post_id: uuid.UUID,
        tag_name: str,
        user_id: uuid.UUID,
    ) -> None:
        """从帖子移除标签（仅作者或 P0）。"""
        tag = await self.get_tag_by_name(tag_name)
        if not tag:
            raise AppError("标签不存在", code="tag_not_found", status_code=404)

        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            if not post:
                raise AppError("帖子不存在", code="post_not_found", status_code=404)
            if post.author_id != user_id:
                raise AppError(
                    "无权限操作此帖子", code="permission_denied", status_code=403
                )

            result = await session.execute(
                select(BlogPostTag).where(
                    BlogPostTag.post_id == post_id,
                    BlogPostTag.tag_id == tag.id,
                )
            )
            post_tag = result.scalar_one_or_none()
            if not post_tag:
                raise AppError("帖子无此标签", code="tag_not_on_post", status_code=400)

            await session.delete(post_tag)
            await session.commit()

    async def get_post_tags(self, post_id: uuid.UUID) -> list[dict]:
        """获取帖子的所有标签。"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogTag)
                .join(BlogPostTag, BlogTag.id == BlogPostTag.tag_id)
                .where(BlogPostTag.post_id == post_id)
                .order_by(BlogTag.name)
            )
            tags = result.scalars().all()
            return [self._tag_to_dict(t) for t in tags]

    # --- 文件导入 ---

    ALLOWED_IMPORT_TYPES = {".md", ".txt", ".docx", ".html", ".htm"}

    async def import_post(
        self,
        file: UploadFile,
        author_id: uuid.UUID,
        user_level: int = 5,
        required_level: int = 5,
        tags: list[str] | None = None,
    ) -> dict:
        """从文件导入帖子。"""
        filename = file.filename or ""
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_IMPORT_TYPES:
            allowed = ", ".join(sorted(self.ALLOWED_IMPORT_TYPES))
            raise AppError(
                f"不支持的文件类型: {ext}，支持 {allowed}",
                code="unsupported_file_type",
                status_code=400,
            )

        content = await file.read()

        # 解析文件内容
        if ext == ".md" or ext == ".txt":
            text = content.decode("utf-8", errors="replace")
        elif ext == ".html" or ext == ".htm":
            text = content.decode("utf-8", errors="replace")
            text = self._extract_html_body(text)
        elif ext == ".docx":
            text = await self._parse_docx(content)
        else:
            text = content.decode("utf-8", errors="replace")

        # 从内容提取标题（第一个 # heading 或文件名）
        title, body = self._extract_title(text, filename)

        # 仅返回解析后的数据，不持久化
        # 用户后续通过手动点击"保存"触发 create_post 流程
        return {
            "title": title,
            "content": body,
            "tags": tags or [],
            "status": "pending",
        }

    def _extract_title(self, text: str, fallback_filename: str) -> tuple[str, str]:
        """从 Markdown 文本中提取标题。"""
        match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # 移除标题行
            body = re.sub(r"^#\s+.+$\n?", "", text, count=1, flags=re.MULTILINE).strip()
            return title, body
        # 没有标题，用文件名作为标题
        name = Path(fallback_filename).stem or "导入的帖子"
        return name, text.strip()

    def _extract_html_body(self, html: str) -> str:
        """从 HTML 中提取 body 内容并转为简单 Markdown。"""
        import html as html_mod

        # 提取 body
        match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
        text = match.group(1) if match else html

        # 简单转换：heading, paragraph, br
        text = re.sub(
            r"<h1[^>]*>(.*?)</h1>", r"# \1\n", text, flags=re.IGNORECASE | re.DOTALL
        )
        text = re.sub(
            r"<h2[^>]*>(.*?)</h2>", r"## \1\n", text, flags=re.IGNORECASE | re.DOTALL
        )
        text = re.sub(
            r"<h3[^>]*>(.*?)</h3>", r"### \1\n", text, flags=re.IGNORECASE | re.DOTALL
        )
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(
            r"<p[^>]*>(.*?)</p>", r"\1\n\n", text, flags=re.IGNORECASE | re.DOTALL
        )
        text = re.sub(r"<[^>]+>", "", text)
        text = html_mod.unescape(text)
        return text.strip()

    async def _parse_docx(self, content: bytes) -> str:
        """解析 .docx 文件内容为文本。"""
        try:
            from docx import Document
        except ImportError:
            raise AppError(
                "python-docx 未安装，无法解析 .docx 文件",
                code="missing_dependency",
                status_code=500,
            )

        doc = Document(io.BytesIO(content))
        parts = []
        for para in doc.paragraphs:
            if para.style and para.style.name and para.style.name.startswith("Heading"):
                level = para.style.name.replace("Heading ", "")
                prefix = "#" * int(level) if level.isdigit() else "#"
                parts.append(f"{prefix} {para.text}")
            else:
                parts.append(para.text)
        return "\n\n".join(p for p in parts if p.strip())

    # --- 收藏 ---

    async def add_favorite(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """收藏帖子（需登录）。"""
        # 验证帖子存在
        await self.get_post_by_id(post_id)

        async with self.session_factory() as session:
            # 检查是否已收藏
            result = await session.execute(
                select(BlogFavorite).where(
                    BlogFavorite.post_id == post_id,
                    BlogFavorite.user_id == user_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return {"action": "already_favorited", "favorite_id": str(existing.id)}

            # 创建收藏
            favorite = BlogFavorite(post_id=post_id, user_id=user_id)
            session.add(favorite)
            await session.commit()
            await session.refresh(favorite)

            return {"action": "favorited", "favorite_id": str(favorite.id)}

    async def remove_favorite(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """取消收藏（需登录）。"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogFavorite).where(
                    BlogFavorite.post_id == post_id,
                    BlogFavorite.user_id == user_id,
                )
            )
            favorite = result.scalar_one_or_none()
            if favorite:
                await session.delete(favorite)
                await session.commit()

            return {"action": "unfavorited"}

    async def check_favorite(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """检查是否已收藏。"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(BlogFavorite).where(
                    BlogFavorite.post_id == post_id,
                    BlogFavorite.user_id == user_id,
                )
            )
            return result.scalar_one_or_none() is not None

    async def list_favorites(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """我的收藏列表（需登录）。"""
        from backend.plugins.auth.models import User

        offset = (page - 1) * page_size

        async with self.session_factory() as session:
            # 查询收藏的帖子
            query = (
                select(BlogFavorite)
                .join(BlogPost, BlogPost.id == BlogFavorite.post_id)
                .where(BlogPost.status == "published")
                .order_by(BlogFavorite.created_at.desc())
            )

            # 总数
            count_query = select(func.count()).select_from(BlogFavorite)
            count_result = await session.execute(count_query)
            total = count_result.scalar_one()

            # 分页
            query = query.offset(offset).limit(page_size)
            result = await session.execute(query)
            favorites = result.scalars().all()

            if not favorites:
                return {
                    "items": [],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }

            # 获取帖子详情
            post_ids = [f.post_id for f in favorites]
            posts_result = await session.execute(
                select(BlogPost).where(BlogPost.id.in_(post_ids))
            )
            posts_map = {p.id: p for p in posts_result.scalars().all()}

            # 获取作者信息
            author_ids = [p.author_id for p in posts_map.values()]
            author_result = await session.execute(
                select(User.id, User.username).where(User.id.in_(author_ids))
            )
            author_map = {row.id: row.username for row in author_result.all()}

            # 获取点赞数
            likes_result = await session.execute(
                select(BlogLike.post_id, func.count(BlogLike.id))
                .where(BlogLike.post_id.in_(post_ids))
                .group_by(BlogLike.post_id)
            )
            likes_map = {row.post_id: row.count for row in likes_result.all()}

            return {
                "items": [
                    self._post_to_dict(
                        posts_map[f.post_id],
                        author_username=author_map.get(posts_map[f.post_id].author_id),
                        likes_count=likes_map.get(f.post_id, 0),
                    )
                    for f in favorites
                    if f.post_id in posts_map
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    # ── Dashboard 统计 ──

    async def get_stats(self) -> dict:
        """获取博客相关统计（用于控制台 Dashboard）。"""
        async with self.session_factory() as session:
            # 帖子总数
            total_posts_result = await session.execute(
                select(func.count()).select_from(BlogPost)
            )
            total_posts = total_posts_result.scalar_one()

            # 发布的帖子总数
            published_result = await session.execute(
                select(func.count())
                .select_from(BlogPost)
                .where(BlogPost.status == "published")
            )
            published_posts = published_result.scalar_one()

            # 待审核帖子数
            pending_result = await session.execute(
                select(func.count())
                .select_from(BlogPost)
                .where(BlogPost.status == "pending")
            )
            pending_posts = pending_result.scalar_one()

            # 总浏览量
            views_result = await session.execute(
                select(func.coalesce(func.sum(BlogPost.views), 0))
            )
            total_views = views_result.scalar_one()

            # 总评论数
            comments_result = await session.execute(
                select(func.count()).select_from(BlogComment)
            )
            total_comments = comments_result.scalar_one()

            # 总点赞数
            likes_result = await session.execute(
                select(func.count()).select_from(BlogLike)
            )
            total_likes = likes_result.scalar_one()

            # 今日新增帖子
            from datetime import datetime, timezone

            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_posts_result = await session.execute(
                select(func.count())
                .select_from(BlogPost)
                .where(BlogPost.created_at >= today_start)
            )
            today_posts = today_posts_result.scalar_one()

        return {
            "total_posts": total_posts,
            "published_posts": published_posts,
            "pending_posts": pending_posts,
            "total_views": total_views,
            "total_comments": total_comments,
            "total_likes": total_likes,
            "today_posts": today_posts,
        }

    # ── 每日曝光量趋势 ──

    async def get_daily_trend(self, days: int = 7) -> dict:
        """获取最近 N 天的每日浏览量、帖子新增量趋势。"""
        from datetime import datetime, timedelta, timezone

        end_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start_date = end_date - timedelta(days=days - 1)

        async with self.session_factory() as session:
            # 每日新增帖子数
            posts_query = (
                select(
                    func.date(BlogPost.created_at).label("date"),
                    func.count().label("count"),
                )
                .where(BlogPost.created_at >= start_date)
                .group_by(func.date(BlogPost.created_at))
                .order_by(func.date(BlogPost.created_at))
            )
            posts_result = await session.execute(posts_query)
            posts_by_date = {row.date: row.count for row in posts_result.all()}

            # 每日浏览量（按帖子 created_at 聚合，取 sum of views）
            views_query = (
                select(
                    func.date(BlogPost.created_at).label("date"),
                    func.coalesce(func.sum(BlogPost.views), 0).label("total_views"),
                )
                .where(BlogPost.created_at >= start_date)
                .group_by(func.date(BlogPost.created_at))
                .order_by(func.date(BlogPost.created_at))
            )
            views_result = await session.execute(views_query)
            views_by_date = {row.date: row.total_views for row in views_result.all()}

            # 每日新增评论数
            comments_query = (
                select(
                    func.date(BlogComment.created_at).label("date"),
                    func.count().label("count"),
                )
                .where(BlogComment.created_at >= start_date)
                .group_by(func.date(BlogComment.created_at))
                .order_by(func.date(BlogComment.created_at))
            )
            comments_result = await session.execute(comments_query)
            comments_by_date = {row.date: row.count for row in comments_result.all()}

            # 组装时间序列
            trend = []
            for i in range(days):
                date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                trend.append(
                    {
                        "date": date,
                        "views": int(views_by_date.get(date, 0)),
                        "posts": int(posts_by_date.get(date, 0)),
                        "comments": int(comments_by_date.get(date, 0)),
                    }
                )

        return {"days": days, "trend": trend}

    # --- 举报 ---

    async def create_report(
        self,
        post_id: uuid.UUID,
        reporter_id: uuid.UUID,
        reason: str | None = None,
    ) -> dict:
        """举报帖子（需登录）。"""
        # 验证帖子存在
        await self.get_post_by_id(post_id)

        async with self.session_factory() as session:
            report = BlogReport(
                post_id=post_id,
                reporter_id=reporter_id,
                reason=reason,
            )
            session.add(report)

            # 举报触发风控：将帖子标记为 throttled（降流）
            result = await session.execute(
                select(BlogPost).where(BlogPost.id == post_id)
            )
            post = result.scalar_one()
            if post.status == "published":
                post.status = "throttled"

            await session.commit()
            await session.refresh(report)

            return self._report_to_dict(report)

    # --- 帖子文件生命周期管理 ---

    async def scan_and_clean_post_files(
        self, post_id: uuid.UUID, content: str
    ) -> list[int]:
        """
        扫描正文中的 [#N] 引用，清理未引用的文件。
        返回被引用的文件索引列表。
        """
        # 1. 提取所有 [#N] 引用
        refs = set()
        for match in re.finditer(r"\[#(\d+)\]", content):
            refs.add(int(match.group(1)))

        async with self.session_factory() as session:
            # 2. 查询该帖子的所有临时文件
            result = await session.execute(
                select(PostFile).where(
                    PostFile.post_id == post_id, PostFile.status == "temp"
                )
            )
            post_files = result.scalars().all()

            referenced_indices = []
            orphaned_ids = []

            for pf in post_files:
                if pf.file_index in refs:
                    pf.status = "persisted"
                    referenced_indices.append(pf.file_index)
                else:
                    orphaned_ids.append(pf.id)

            # 3. 删除未引用的文件记录（实际 OSS 文件保留，由定时任务清理）
            if orphaned_ids:
                await session.execute(
                    delete(PostFile).where(PostFile.id.in_(orphaned_ids))
                )

            await session.commit()

        return sorted(refs)

    async def validate_post_file_refs(
        self, content: str, owner_id: uuid.UUID
    ) -> list[str]:
        """
        校验正文中所有 [#N] 引用是否都已上传。
        返回错误信息列表（为空则校验通过）。
        """
        refs = set()
        for match in re.finditer(r"\[#(\d+)\]", content):
            refs.add(int(match.group(1)))

        if not refs:
            return []

        async with self.session_factory() as session:
            result = await session.execute(
                select(PostFile.file_index).where(
                    PostFile.owner_id == owner_id,
                    PostFile.file_index.in_(list(refs)),
                    PostFile.status.in_(["temp", "persisted"]),
                )
            )
            existing = {row[0] for row in result.all()}

        missing = refs - existing
        if missing:
            return [
                f"图片 #'{idx}' 未上传，请先上传或移除引用" for idx in sorted(missing)
            ]
        return []

    async def validate_content(self, content: str, owner_id: uuid.UUID) -> list[str]:
        """全面校验正文内容。"""
        errors = []
        # 检查文件引用
        file_errors = await self.validate_post_file_refs(content, owner_id)
        errors.extend(file_errors)
        # 检查视频链接（检测 bilibili/youtube 链接格式）
        for match in re.finditer(r"\[([^\]]*)\]\((https?://[^)]+)\)", content):
            url = match.group(2)
            if self._is_trusted_video_host(url):
                if not self._validate_video_url(url):
                    errors.append(f"视频链接 '{url}' 格式无效")
        return errors

    @staticmethod
    def _is_trusted_video_host(url: str) -> bool:
        """安全地检查 URL 的 hostname 是否为受信任的视频平台。"""
        trusted_domains = ("bilibili.com", "b23.tv", "youtube.com")
        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname or ""
        except ValueError:
            return False
        # 规范化：转小写、移除尾部点号
        hostname = hostname.lower().rstrip(".")
        return any(
            hostname == domain or hostname.endswith("." + domain)
            for domain in trusted_domains
        )

    def _validate_video_url(self, url: str) -> bool:
        """验证视频分享链接的基本格式。"""
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        is_bilibili = hostname == "bilibili.com" or hostname.endswith(".bilibili.com")
        is_b23tv = hostname == "b23.tv" or hostname.endswith(".b23.tv")
        is_youtube = hostname == "youtube.com" or hostname.endswith(".youtube.com")
        if is_bilibili or is_b23tv:
            return bool(re.search(r"(BV[\w]+|video/[\w]+)", url))
        if is_youtube:
            return bool(re.search(r"(watch\?v=|embed/|shorts/)", url))
        return True

    # ── 内容话题热度排行（P0 管理用）──

    async def get_hot_posts(self, limit: int = 10) -> list[dict]:
        """按浏览量降序获取热门帖子（含点赞数和评论数）。"""
        from backend.plugins.auth.models import User

        async with self.session_factory() as session:
            query = (
                select(BlogPost)
                .where(BlogPost.status == "published")
                .order_by(BlogPost.views.desc())
                .limit(limit)
            )
            result = await session.execute(query)
            posts = result.scalars().all()

            if not posts:
                return []

            post_ids = [p.id for p in posts]

            # 作者信息
            author_ids = [p.author_id for p in posts]
            author_result = await session.execute(
                select(User.id, User.username).where(User.id.in_(author_ids))
            )
            author_map = {row.id: row.username for row in author_result.all()}

            # 点赞数
            likes_result = await session.execute(
                select(BlogLike.post_id, func.count(BlogLike.id))
                .where(BlogLike.post_id.in_(post_ids))
                .group_by(BlogLike.post_id)
            )
            likes_map = {row.post_id: row.count for row in likes_result.all()}

            # 评论数
            comments_result = await session.execute(
                select(BlogComment.post_id, func.count(BlogComment.id))
                .where(BlogComment.post_id.in_(post_ids))
                .group_by(BlogComment.post_id)
            )
            comments_map = {row.post_id: row.count for row in comments_result.all()}

            return [
                {
                    "id": str(p.id),
                    "title": p.title,
                    "author_username": author_map.get(p.author_id, "未知"),
                    "views": p.views,
                    "likes": likes_map.get(p.id, 0),
                    "comments": comments_map.get(p.id, 0),
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in posts
            ]

    # --- 数据转换 ---

    def _tag_to_dict(self, tag: BlogTag) -> dict:
        return {
            "id": str(tag.id),
            "name": tag.name,
            "color": tag.color,
            "created_at": tag.created_at.isoformat() if tag.created_at else None,
        }

    def _post_to_dict(
        self,
        post: BlogPost,
        *,
        author_username: str | None = None,
        likes_count: int = 0,
    ) -> dict:
        return {
            "id": str(post.id),
            "author_id": str(post.author_id),
            "author_username": author_username or str(post.author_id)[:8],
            "title": post.title,
            "slug": post.slug,
            "cover_url": post.cover_url,
            "subtitles": post.subtitles,
            "introduction": post.introduction,
            "paragraph_ids": post.paragraph_ids,
            "status": post.status,
            "views": post.views,
            "likes": likes_count,
            "like_count": post.like_count,
            "comment_count": post.comment_count,
            "required_level": post.required_level,
            "is_pinned": post.is_pinned,
            "is_featured": post.is_featured,
            "category_id": post.category_id,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "updated_at": post.updated_at.isoformat() if post.updated_at else None,
            "published_at": post.published_at.isoformat()
            if post.published_at
            else None,
        }

    def _comment_to_dict(
        self, comment: BlogComment, *, author_username: str | None = None
    ) -> dict:
        return {
            "id": str(comment.id),
            "post_id": str(comment.post_id),
            "author_id": str(comment.author_id),
            "author_username": author_username or str(comment.author_id)[:8],
            "content": comment.content,
            "parent_id": str(comment.parent_id) if comment.parent_id else None,
            "paragraph_pid": comment.paragraph_pid,
            "status": comment.status,
            "like_count": comment.like_count,
            "created_at": comment.created_at.isoformat()
            if comment.created_at
            else None,
            "updated_at": comment.updated_at.isoformat()
            if comment.updated_at
            else None,
        }

    def _report_to_dict(self, report: BlogReport) -> dict:
        return {
            "id": str(report.id),
            "post_id": str(report.post_id),
            "reporter_id": str(report.reporter_id),
            "reason": report.reason,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
