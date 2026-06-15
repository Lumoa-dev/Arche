"""资产管理插件 —— 聚合查询服务。

跨插件查询各类型资产，合并后返回统一格式。
"""

from __future__ import annotations

import uuid
from operator import itemgetter

from sqlalchemy import func, select


class AssetMgmtService:
    """资产管理服务：跨插件聚合查询、搜索、统计。"""

    def __init__(self, container):
        self.container = container
        db = container.get("db")
        self.session_factory = db["session_factory"]

    # --- 统一资产目录 ---

    async def list_assets(
        self,
        owner_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        asset_type: str | None = None,
    ) -> dict:
        """统一资产目录：跨插件查询用户资产，分页返回。"""
        offset = (page - 1) * page_size
        assets = []

        async with self.session_factory() as session:
            # 博客帖子
            if asset_type is None or asset_type == "blog_post":
                from backend.plugins.blog.models import BlogPost

                query = select(BlogPost).where(BlogPost.author_id == owner_id)
                result = await session.execute(query)
                for post in result.scalars().all():
                    assets.append(
                        {
                            "id": str(post.id),
                            "asset_type": "blog_post",
                            "source_id": str(post.id),
                            "title": post.title,
                            "description": post.title[:200] if post.title else None,
                            "tags": [],
                            "created_at": post.created_at.isoformat()
                            if post.created_at
                            else None,
                            "source_plugin": "blog",
                        }
                    )

            # 对象存储文件
            if asset_type is None or asset_type == "file":
                from backend.plugins.oss.models import OSSFile

                query = select(OSSFile).where(OSSFile.owner_id == owner_id)  # type: ignore[assignment]
                result = await session.execute(query)
                for f in result.scalars().all():
                    assets.append(
                        {
                            "id": str(f.id),
                            "asset_type": "file",
                            "source_id": str(f.id),
                            "title": f.path.rsplit("/", 1)[-1]
                            if "/" in f.path
                            else f.path,
                            "description": f.mime_type,
                            "tags": [],
                            "created_at": f.created_at.isoformat()
                            if f.created_at
                            else None,
                            "source_plugin": "oss",
                        }
                    )

            # 训练任务
            if asset_type is None or asset_type == "training_job":
                from backend.plugins.cloud_integration.models import TrainingJob

                query = select(TrainingJob).where(TrainingJob.creator_id == owner_id)  # type: ignore[assignment]
                result = await session.execute(query)
                for job in result.scalars().all():
                    assets.append(
                        {
                            "id": str(job.id),
                            "asset_type": "training_job",
                            "source_id": str(job.id),
                            "title": job.name,
                            "description": job.status,
                            "tags": [],
                            "created_at": job.created_at.isoformat()
                            if job.created_at
                            else None,
                            "source_plugin": "cloud_integration",
                        }
                    )

        # 按创建时间倒序排序
        assets.sort(key=itemgetter("created_at"), reverse=True)

        total = len(assets)
        paginated = assets[offset : offset + page_size]

        return {
            "items": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # --- 资产搜索 ---

    async def search_assets(
        self,
        owner_id: uuid.UUID,
        keyword: str,
        asset_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        """按关键词搜索资产，支持类型和时间范围过滤。"""

        all_assets = await self.list_assets(
            owner_id, page=1, page_size=10000, asset_type=asset_type
        )

        results = []
        keyword_lower = keyword.lower()

        for asset in all_assets["items"]:
            # 关键词匹配：标题或描述
            title_match = keyword_lower in (asset.get("title") or "").lower()
            desc_match = keyword_lower in (asset.get("description") or "").lower()
            if not title_match and not desc_match:
                continue

            # 时间范围过滤
            created_at = asset.get("created_at")
            if date_from and created_at and created_at < date_from:
                continue
            if date_to and created_at and created_at > date_to:
                continue

            results.append(asset)

        return results

    # --- 资产统计 ---

    async def get_stats(self, owner_id: uuid.UUID) -> dict:
        """按类型分组统计用户资产。"""
        from backend.plugins.blog.models import BlogPost
        from backend.plugins.cloud_integration.models import TrainingJob
        from backend.plugins.oss.models import OSSFile

        async with self.session_factory() as session:
            # 博客帖子
            blog_count = await session.execute(
                select(func.count(BlogPost.id)).where(BlogPost.author_id == owner_id)
            )

            # 对象存储文件（count + 总字节数）
            file_result = await session.execute(
                select(
                    func.count(OSSFile.id),
                    func.sum(OSSFile.size),
                ).where(OSSFile.owner_id == owner_id)
            )
            file_count, file_total_size = file_result.one()
            file_count = file_count or 0
            file_total_size = file_total_size or 0

            # 训练任务
            job_count = await session.execute(
                select(func.count(TrainingJob.id)).where(
                    TrainingJob.creator_id == owner_id
                )
            )

        blog_total = blog_count.scalar() or 0
        job_total = job_count.scalar() or 0

        # crawl_result 暂不加入统计：CrawlRecord 表缺少 owner_id 字段，无法按用户过滤
        crawl_total = 0

        total = blog_total + file_count + crawl_total + job_total

        return {
            "owner_id": str(owner_id),
            "by_type": {
                "blog_post": blog_total,
                "file": {
                    "count": file_count,
                    "total_size_bytes": file_total_size,
                },
                "crawl_result": crawl_total,
                "training_job": job_total,
            },
            "total_assets": total,
            "total": total,
        }
