"""爬虫插件 —— 总调度器：CrawlerOrchestrator。

全局并发控制、流水线编排、状态查询。
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from backend.core.container import ServiceContainer
from backend.plugins.crawler.models import CrawlRecord
from backend.plugins.crawler.pipeline import (
    ClassifyStage,
    CrawlItem,
    FetchStage,
    ParseStage,
    QualityStage,
    StorageStage,
)
from backend.plugins.crawler.seed_manager import SeedManager
from backend.plugins.crawler.url_scheduler import UrlScheduler


class CrawlerOrchestrator:
    """总调度器：全局并发控制、流水线编排、状态查询。"""

    def __init__(self, container: ServiceContainer):
        self.container = container
        self.seed_manager = SeedManager(container)
        self.url_scheduler = UrlScheduler(max_global=10, max_per_domain=2)
        self.fetch_stage = FetchStage()
        self.parse_stage = ParseStage()
        self.classify_stage = ClassifyStage()
        self.quality_stage = QualityStage()
        self.storage_stage = StorageStage(container)

        self._running = False
        self._start_time: float | None = None
        self._pages_crawled = 0
        self._pages_rejected = 0
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """启动常驻守护进程。"""
        if self._running:
            return
        self._running = True
        self._start_time = time.monotonic()
        await self.seed_manager.initialize()
        self._task = asyncio.create_task(self._daemon_loop())

    async def stop(self) -> None:
        """优雅关闭。"""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _daemon_loop(self) -> None:
        """主循环：不断从种子池取 URL、送入流水线。"""
        active_tasks: list[asyncio.Task] = []
        while self._running:
            # 清理已完成的任务
            active_tasks = [t for t in active_tasks if not t.done()]

            # 如果还有并发配额，取新种子
            if self.url_scheduler.active_count < self.url_scheduler._max_global:
                url = self.seed_manager.pop_seed()
                if url:
                    task = asyncio.create_task(self._run_pipeline(url))
                    active_tasks.append(task)
                    # 佛系模式：随机停留 5-300 秒
                    import random

                    delay = random.uniform(5, 300)
                    await asyncio.sleep(delay)
                else:
                    # 种子池空了，等待
                    await asyncio.sleep(5)
            else:
                # 等待正在任务完成
                await asyncio.sleep(1)

        # 关闭时等待所有活跃任务完成
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)

    async def _run_pipeline(self, url: str, source_url: str = "") -> CrawlItem | None:
        """执行完整流水线。"""
        item = CrawlItem(url=url, source=source_url or urlparse(url).netloc)

        # 探嗅
        from backend.plugins.crawler.probe import ProbeService

        probe = ProbeService()
        try:
            probe_result = await probe.probe(url)
            item.probe_result = probe_result
            if probe_result.get("is_functional"):
                self.seed_manager.add_to_blacklist(
                    urlparse(url).netloc, reason="functional"
                )
                self._pages_rejected += 1
                return None
            if not probe_result.get("has_content", False):
                self._pages_rejected += 1
                return None
        except Exception:
            self._pages_rejected += 1
            return None
        finally:
            await probe.close()

        # 抓取 → 解析 → 分类 → 质检 → 存储
        await self.url_scheduler.acquire(url)
        try:
            item = await self.fetch_stage.process(item)  # type: ignore[assignment]
            if item and not item.error:
                item = await self.parse_stage.process(item)  # type: ignore[assignment]
            if item and not item.error:
                item = await self.classify_stage.process(item)  # type: ignore[assignment]
            if item and not item.error:
                item = await self.quality_stage.process(item)  # type: ignore[assignment]
            if item and item.quality_passed and not item.error:
                item = await self.storage_stage.process(item)  # type: ignore[assignment]
                if item:
                    self._save_record(item)
                    self._pages_crawled += 1
                    # 发现新链接，加入种子池
                    if item.links:
                        self.seed_manager.discover_seeds_from_links(item.links, url)
                else:
                    self._pages_rejected += 1
            else:
                self._pages_rejected += 1
        finally:
            await self.url_scheduler.release(url)

        return item

    def _save_record(self, item: CrawlItem) -> None:
        """将抓取记录写入数据库。"""
        try:
            db = self.container.get("db")
            session_factory = db["session_factory"]

            import asyncio as _asyncio

            async def _save():
                try:
                    async with session_factory() as session:
                        record = CrawlRecord(
                            url=item.url,
                            title=item.title[:512] if item.title else None,
                            content_type=item.content_type or None,
                            status_code=item.status_code,
                            source=item.source or urlparse(item.url).netloc,
                            crawled_at=datetime.now(timezone.utc),
                            file_path=item.oss_path,
                            file_size=item.file_size,
                        )
                        session.add(record)
                        await session.commit()
                except Exception as e:
                    logging.getLogger(__name__).error(f"保存爬虫记录失败: {e}")

            _asyncio.get_running_loop().create_task(_save())
        except Exception as e:
            logging.getLogger(__name__).error(f"创建保存任务失败: {e}")

    async def add_seed(self, url: str) -> bool:
        """手动添加种子 URL。"""
        return self.seed_manager.add_seed(url)

    async def get_status(self) -> dict:
        """返回运行状态。"""
        uptime = time.monotonic() - self._start_time if self._start_time else 0
        return {
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "active_tasks": self.url_scheduler.active_count,
            "queue_size": self.url_scheduler.queue_size + self.seed_manager.queue_size,
            "seeds_count": self.seed_manager.queue_size,
            "pages_crawled": self._pages_crawled,
            "pages_rejected": self._pages_rejected,
            "domains_active": self.url_scheduler.domains_active,
        }

    async def get_recent_records(self, limit: int = 50) -> list[dict]:
        """获取最近抓取的记录列表。"""
        from sqlalchemy import desc, select

        db = self.container.get("db")
        session_factory = db["session_factory"]

        async with session_factory() as session:
            result = await session.execute(
                select(CrawlRecord).order_by(desc(CrawlRecord.crawled_at)).limit(limit)
            )
            records = result.scalars().all()
            return [
                {
                    "id": str(r.id),
                    "url": r.url,
                    "title": r.title,
                    "content_type": r.content_type,
                    "status_code": r.status_code,
                    "status": str(r.status_code),
                    "source": r.source,
                    "crawled_at": r.crawled_at.isoformat() if r.crawled_at else None,
                    "created_at": r.crawled_at.isoformat() if r.crawled_at else None,
                    "file_path": r.file_path,
                    "file_size": r.file_size,
                }
                for r in records
            ]

    async def get_record(self, record_id) -> dict | None:
        """获取单条记录详情。"""
        import uuid as _uuid

        from sqlalchemy import select

        db = self.container.get("db")
        session_factory = db["session_factory"]

        if isinstance(record_id, str):
            record_id = _uuid.UUID(record_id)

        async with session_factory() as session:
            result = await session.execute(
                select(CrawlRecord).where(CrawlRecord.id == record_id)
            )
            r = result.scalar_one_or_none()
            if not r:
                return None
            return {
                "id": str(r.id),
                "url": r.url,
                "title": r.title,
                "content_type": r.content_type,
                "status_code": r.status_code,
                "status": str(r.status_code),
                "source": r.source,
                "crawled_at": r.crawled_at.isoformat() if r.crawled_at else None,
                "created_at": r.crawled_at.isoformat() if r.crawled_at else None,
                "file_path": r.file_path,
                "file_size": r.file_size,
            }

    async def get_stats(self) -> dict:
        """统计信息。"""
        from sqlalchemy import func, select

        db = self.container.get("db")
        session_factory = db["session_factory"]

        async with session_factory() as session:
            total = await session.execute(select(func.count(CrawlRecord.id)))
            total = total.scalar_one()

            # 按类型分布
            type_dist = await session.execute(
                select(CrawlRecord.content_type, func.count(CrawlRecord.id)).group_by(
                    CrawlRecord.content_type
                )
            )
            type_counts = {row[0] or "unknown": row[1] for row in type_dist.all()}

            # 按域名分布
            domain_dist = await session.execute(
                select(CrawlRecord.source, func.count(CrawlRecord.id))
                .group_by(CrawlRecord.source)
                .order_by(func.count(CrawlRecord.id).desc())
                .limit(20)
            )
            domain_counts = {row[0] or "unknown": row[1] for row in domain_dist.all()}

            return {
                "total_crawled": total,
                "by_type": type_counts,
                "by_domain": domain_counts,
            }
