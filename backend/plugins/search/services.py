"""统一搜索服务 —— 全局模糊搜索 + 分类搜索。"""

from __future__ import annotations

from sqlalchemy import or_, select

from backend.core.uid import SidParts, parse_sid


class SearchService:
    """搜索服务：跨插件搜索建议。"""

    def __init__(self, container):
        self.container = container
        db = container.get("db")
        self.session_factory = db["session_factory"]

    async def search(
        self,
        keyword: str,
        limit: int = 5,
    ) -> list[dict]:
        """统一搜索入口。

        1. 先用 parse_sid 解析 keyword
        2. 如果解析出 prefix，限定搜索范围
        3. 如果没有 prefix，跨表模糊搜索
        """
        if not keyword or not keyword.strip():
            return []

        q = keyword.strip()

        # 尝试解析为 SID
        parsed = parse_sid(q)

        if parsed and parsed.prefix:
            return await self._search_by_prefix(parsed, q, limit)
        else:
            return await self._search_global(q, limit)

    async def _search_by_prefix(
        self, parsed: SidParts, raw_q: str, limit: int
    ) -> list[dict]:
        """根据 SID 前缀限定搜索范围。"""
        prefix = parsed.prefix

        if prefix == "user":
            return await self._search_users(raw_q, limit)
        elif prefix == "task":
            return await self._search_tasks(raw_q, limit)
        elif prefix == "log":
            return await self._search_logs(raw_q, limit)
        else:  # asse 或其他
            return await self._search_assets(raw_q, limit)

    async def _search_users(self, q: str, limit: int) -> list[dict]:
        """搜索用户。"""
        from backend.plugins.auth.models import User

        results = []
        pattern = f"%{q}%"

        async with self.session_factory() as session:
            query = (
                select(User)
                .where(
                    or_(
                        User.sid.ilike(pattern),
                        User.username.ilike(pattern),
                        User.email.ilike(pattern),
                    )
                )
                .limit(limit)
            )
            rows = await session.execute(query)
            for user in rows.scalars().all():
                results.append(
                    {
                        "type": "user",
                        "sid": user.sid,
                        "label": user.username,
                        "sublabel": f"等级 P{user.level}",
                        "url": f"/admin/users/list?id={user.id}",
                    }
                )
        return results

    async def _search_assets(self, q: str, limit: int) -> list[dict]:
        """搜索资产：帖子、文件等。"""
        from backend.plugins.blog.models import BlogPost
        from backend.plugins.oss.models import OSSFile

        results = []
        pattern = f"%{q}%"

        async with self.session_factory() as session:
            # 搜帖子
            query = (
                select(BlogPost)
                .where(
                    or_(
                        BlogPost.sid.ilike(pattern),
                        BlogPost.title.ilike(pattern),
                    )
                )
                .limit(limit)
            )
            rows = await session.execute(query)
            for post in rows.scalars().all():
                results.append(
                    {
                        "type": "post",
                        "sid": post.sid,
                        "label": post.title,
                        "sublabel": f"发布于 {post.created_at.strftime('%Y-%m-%d') if post.created_at else ''}",  # noqa: E501
                        "url": f"/blog/{post.slug}",
                    }
                )

            # 搜文件（如果帖子不足）
            if len(results) < limit:
                remaining = limit - len(results)
                file_query = (
                    select(OSSFile)
                    .where(
                        or_(
                            OSSFile.sid.ilike(pattern),
                            OSSFile.path.ilike(pattern),
                        )
                    )
                    .limit(remaining)
                )
                file_rows = await session.execute(file_query)
                for f in file_rows.scalars().all():
                    results.append(
                        {
                            "type": "file",
                            "sid": f.sid,
                            "label": f.path.rsplit("/", 1)[-1]
                            if "/" in f.path
                            else f.path,
                            "sublabel": f.mime_type or "",
                            "url": f"/assets?file_id={f.id}",
                        }
                    )

        return results

    async def _search_tasks(self, q: str, limit: int) -> list[dict]:
        """搜索任务。"""
        from backend.plugins.cloud_integration.models import TrainingJob

        results = []
        pattern = f"%{q}%"

        async with self.session_factory() as session:
            query = (
                select(TrainingJob)
                .where(
                    or_(
                        TrainingJob.sid.ilike(pattern),
                        TrainingJob.name.ilike(pattern),
                    )
                )
                .limit(limit)
            )
            rows = await session.execute(query)
            for job in rows.scalars().all():
                results.append(
                    {
                        "type": "task",
                        "sid": job.sid,
                        "label": job.name,
                        "sublabel": job.status,
                        "url": f"/tasks?job_id={job.id}",
                    }
                )
        return results

    async def _search_logs(self, q: str, limit: int) -> list[dict]:
        """搜索日志/记录。"""
        from backend.plugins.crawler.models import CrawlRecord

        results = []
        pattern = f"%{q}%"

        async with self.session_factory() as session:
            query = (
                select(CrawlRecord)
                .where(
                    or_(
                        CrawlRecord.sid.ilike(pattern),
                        CrawlRecord.url.ilike(pattern),
                    )
                )
                .limit(limit)
            )
            rows = await session.execute(query)
            for record in rows.scalars().all():
                results.append(
                    {
                        "type": "log",
                        "sid": record.sid,
                        "label": record.title or record.url,
                        "sublabel": f"来源: {record.source or ''}",
                        "url": f"/crawler?record_id={record.id}",
                    }
                )
        return results

    async def _search_global(self, q: str, limit: int) -> list[dict]:
        """全局模糊搜索，跨表搜索，按类型混合返回。"""
        results = []

        # 每类型取部分结果，混合后截断
        per_type = max(3, limit)
        user_results = await self._search_users(q, per_type)
        asset_results = await self._search_assets(q, per_type)

        # 混合
        results.extend(user_results)
        results.extend(asset_results)

        return results[:limit]
