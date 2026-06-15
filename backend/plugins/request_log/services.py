"""请求日志服务 —— RequestLogMiddleware + LogAggregationService。"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timedelta

from fastapi import Request, Response
from sqlalchemy import extract, select
from sqlalchemy import func as sa_func
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.middleware import get_current_user

logger = logging.getLogger(__name__)

# ── 行为分类 ──

_LOGIN_PATH = "/api/auth/login"
_API_PREFIX = "/api/"


def classify_action(method: str, path: str, status_code: int) -> str:
    if path == _LOGIN_PATH and status_code >= 400:
        return "login_fail"
    if path.startswith(_API_PREFIX):
        return "api_call"
    if method == "GET":
        return "page_view"
    return "other"


# ── 跳过列表 ──

_SKIP_PATHS = frozenset({
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
})

_SKIP_PREFIXES = (
    "/static/",
    "/assets/",
)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip
    client = request.client
    if client:
        return client.host
    return ""


def _get_session_factory():
    from backend.core.container import container as global_container

    try:
        db = global_container.get("db")
        return db["session_factory"]
    except Exception:
        return None


class RequestLogMiddleware(BaseHTTPMiddleware):
    """记录每个请求的明细日志。

    请求处理完成后，异步写入 RequestLog 表并更新 IpActionCounter。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        for skip in _SKIP_PATHS:
            if path == skip:
                return await call_next(request)
        if path.startswith(_SKIP_PREFIXES):
            return await call_next(request)

        start = time.time()
        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start) * 1000, 2)
            asyncio.create_task(  # noqa: RUF006
                _write_log_async(request, response.status_code, duration_ms)
            )
            return response
        except Exception:
            duration_ms = round((time.time() - start) * 1000, 2)
            asyncio.create_task(  # noqa: RUF006
                _write_log_async(request, 500, duration_ms)
            )
            raise


async def _write_log_async(
    request: Request, status_code: int, duration_ms: float
) -> None:
    try:
        path = request.url.path
        method = request.method
        ip = _get_client_ip(request)
        action = classify_action(method, path, status_code)
        user_agent = request.headers.get("User-Agent", "")[:512]
        referer = request.headers.get("Referer", "")[:1024]

        user = get_current_user(request)
        user_id = user.get("id") if user else None

        from backend.plugins.request_log.models import IpActionCounter, RequestLog

        session_factory = _get_session_factory()
        if session_factory is None:
            return
        async with session_factory() as session:
            log_entry = RequestLog(
                ip=ip,
                method=method,
                path=path,
                status_code=status_code,
                user_agent=user_agent or None,
                referer=referer or None,
                duration_ms=duration_ms,
                user_id=user_id,
                action=action,
            )
            session.add(log_entry)

            now = datetime.now()
            today = now.date()
            current_hour = now.hour

            result = await session.execute(
                select(IpActionCounter).where(
                    IpActionCounter.ip == ip,
                    IpActionCounter.action == action,
                    IpActionCounter.action_date == today,
                    IpActionCounter.hour == current_hour,
                )
            )
            counter = result.scalar_one_or_none()
            if counter:
                counter.count = counter.count + 1
            else:
                session.add(
                    IpActionCounter(
                        ip=ip,
                        action=action,
                        action_date=today,
                        hour=current_hour,
                        count=1,
                    )
                )

            await session.commit()
    except Exception:
        logger.exception("写入请求日志异常")


class LogAggregationService:
    """定时聚合服务：归并明细 + TTL 清理。

    每整小时运行一次聚合任务，每 6 小时执行一次 TTL 清理。
    """

    def __init__(self):
        self._scheduler = None

    def start(self) -> None:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.interval import IntervalTrigger
        except ImportError:
            logger.warning("APScheduler 未安装，跳过定时任务启动")
            return

        if self._scheduler:
            return

        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._aggregate_job,
            IntervalTrigger(hours=1),
            id="request_log_aggregate",
            replace_existing=True,
            name="请求日志聚合",
        )
        self._scheduler.add_job(
            self._cleanup_job,
            IntervalTrigger(hours=6),
            id="request_log_cleanup",
            replace_existing=True,
            name="请求日志 TTL 清理",
        )
        self._scheduler.start()
        logger.info("请求日志聚合服务已启动")

    def stop(self) -> None:
        if self._scheduler and getattr(self._scheduler, "running", False):
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            logger.info("请求日志聚合服务已停止")

    async def _aggregate_job(self) -> None:
        """归并前 1 小时的明细日志到聚合表。"""
        try:
            from backend.plugins.request_log.models import IpActionCounter, RequestLog

            session_factory = _get_session_factory()
            async with session_factory() as session:
                one_hour_ago = datetime.now() - timedelta(hours=1)

                stmt = (
                    select(
                        RequestLog.ip,
                        RequestLog.action,
                        extract("year", RequestLog.created_at).label("yr"),
                        extract("month", RequestLog.created_at).label("mo"),
                        extract("day", RequestLog.created_at).label("dy"),
                        extract("hour", RequestLog.created_at).label("hr"),
                        sa_func.count().label("cnt"),
                    )
                    .where(RequestLog.created_at >= one_hour_ago)
                    .group_by(
                        RequestLog.ip,
                        RequestLog.action,
                        extract("year", RequestLog.created_at),
                        extract("month", RequestLog.created_at),
                        extract("day", RequestLog.created_at),
                        extract("hour", RequestLog.created_at),
                    )
                )
                result = await session.execute(stmt)
                rows = result.all()

                for row in rows:
                    action_date = date(int(row.yr), int(row.mo), int(row.dy))
                    counter_result = await session.execute(
                        select(IpActionCounter).where(
                            IpActionCounter.ip == row.ip,
                            IpActionCounter.action == row.action,
                            IpActionCounter.action_date == action_date,
                            IpActionCounter.hour == int(row.hr),
                        )
                    )
                    counter = counter_result.scalar_one_or_none()
                    if counter:
                        counter.count = counter.count + int(row.cnt)
                    else:
                        session.add(
                            IpActionCounter(
                                ip=row.ip,
                                action=row.action,
                                action_date=action_date,
                                hour=int(row.hr),
                                count=int(row.cnt),
                            )
                        )

                await session.commit()
                logger.info("请求日志聚合完成，处理 %d 条", len(rows))
        except Exception:
            logger.exception("请求日志聚合任务异常")

    async def _cleanup_job(self) -> None:
        """清理超过 TTL 的明细日志。"""
        try:
            from backend.plugins.request_log.models import RequestLog

            session_factory = _get_session_factory()
            async with session_factory() as session:
                cutoff = datetime.now() - timedelta(days=7)
                count_subq = (
                    select(RequestLog)
                    .where(RequestLog.created_at < cutoff)
                    .subquery()
                )
                result = await session.execute(
                    select(sa_func.count()).select_from(count_subq)
                )
                total = result.scalar() or 0

                await session.execute(
                    RequestLog.__table__.delete().where(RequestLog.created_at < cutoff)
                )
                await session.commit()
                logger.info("请求日志 TTL 清理完成，删除 %d 条", total)
        except Exception:
            logger.exception("请求日志 TTL 清理异常")
