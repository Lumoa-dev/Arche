"""请求日志路由 —— IP 行为查询、TOP IP、趋势分析。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func as sa_func
from sqlalchemy import select

from backend.core.middleware import require_level, require_user

router = APIRouter(prefix="/api/request-log", tags=["request_log"])


def _get_session_factory():
    from backend.core.container import container as global_container

    db = global_container.get("db")
    if not db:
        raise HTTPException(status_code=500, detail="数据库未初始化")
    return db["session_factory"]


@router.get("/query")
@require_level(0)
async def query_logs(
    request: Request,
    ip: str | None = Query(None, description="按 IP 过滤"),
    action: str | None = Query(None, description="按行为分类过滤"),
    start_date: str | None = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="结束日期 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """查询请求日志明细。"""
    require_user(request)
    from backend.plugins.request_log.models import RequestLog

    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = select(RequestLog)

        if ip:
            stmt = stmt.where(RequestLog.ip == ip)
        if action:
            stmt = stmt.where(RequestLog.action == action)
        if start_date:
            try:
                sd = datetime.strptime(start_date, "%Y-%m-%d")
                stmt = stmt.where(RequestLog.created_at >= sd)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的 start_date 格式")  # noqa: B904
        if end_date:
            try:
                ed = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                stmt = stmt.where(RequestLog.created_at < ed)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的 end_date 格式")  # noqa: B904

        count_stmt = select(sa_func.count()).select_from(stmt.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(RequestLog.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
        logs = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [log.to_dict() for log in logs],
        }


@router.get("/top-ips")
@require_level(0)
async def get_top_ips(
    request: Request,
    action: str | None = Query(None, description="按行为分类过滤"),
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
) -> list[dict[str, Any]]:
    """获取 TOP IP 排行。"""
    require_user(request)
    from backend.plugins.request_log.models import IpActionCounter

    session_factory = _get_session_factory()
    async with session_factory() as session:
        cutoff = date.today() - timedelta(days=days)
        stmt = (
            select(
                IpActionCounter.ip,
                sa_func.sum(IpActionCounter.count).label("total_count"),
            )
            .where(IpActionCounter.action_date >= cutoff)
            .group_by(IpActionCounter.ip)
            .order_by(sa_func.sum(IpActionCounter.count).desc())
            .limit(limit)
        )
        if action:
            stmt = stmt.where(IpActionCounter.action == action)
        result = await session.execute(stmt)
        rows = result.all()
        return [
            {"ip": row.ip, "count": int(row.total_count)} for row in rows
        ]


@router.get("/trend")
@require_level(0)
async def get_trend(
    request: Request,
    action: str | None = Query(None, description="按行为分类过滤"),
    days: int = Query(7, ge=1, le=90, description="统计天数"),
) -> list[dict[str, Any]]:
    """获取异常行为趋势（按天聚合）。"""
    require_user(request)
    from backend.plugins.request_log.models import RequestLog

    session_factory = _get_session_factory()
    async with session_factory() as session:
        cutoff = datetime.now() - timedelta(days=days)
        stmt = (
            select(
                sa_func.date(RequestLog.created_at).label("log_date"),
                sa_func.count().label("cnt"),
            )
            .where(RequestLog.created_at >= cutoff)
            .group_by(sa_func.date(RequestLog.created_at))
            .order_by(sa_func.date(RequestLog.created_at))
        )
        if action:
            stmt = stmt.where(RequestLog.action == action)
        result = await session.execute(stmt)
        rows = result.all()
        return [
            {"date": str(row.log_date), "count": int(row.cnt)} for row in rows
        ]


@router.get("/counters")
@require_level(0)
async def get_counters(
    request: Request,
    ip: str | None = Query(None, description="按 IP 过滤"),
    action: str | None = Query(None, description="按行为分类过滤"),
    start_date: str | None = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="结束日期 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """查询 IP 行为聚合计数。"""
    require_user(request)
    from backend.plugins.request_log.models import IpActionCounter

    session_factory = _get_session_factory()
    async with session_factory() as session:
        stmt = select(IpActionCounter)

        if ip:
            stmt = stmt.where(IpActionCounter.ip == ip)
        if action:
            stmt = stmt.where(IpActionCounter.action == action)
        if start_date:
            try:
                sd = date.fromisoformat(start_date)
                stmt = stmt.where(IpActionCounter.action_date >= sd)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的 start_date 格式")  # noqa: B904
        if end_date:
            try:
                ed = date.fromisoformat(end_date)
                stmt = stmt.where(IpActionCounter.action_date <= ed)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的 end_date 格式")  # noqa: B904

        count_stmt = select(sa_func.count()).select_from(stmt.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(
            IpActionCounter.action_date.desc(), IpActionCounter.hour.desc()
        )
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
        counters = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [c.to_dict() for c in counters],
        }


@router.get("/actions")
@require_level(0)
async def list_actions(request: Request) -> list[str]:
    """获取所有已记录的行为分类列表。"""
    require_user(request)
    from backend.plugins.request_log.models import IpActionCounter

    session_factory = _get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(IpActionCounter.action)
            .distinct()
            .order_by(IpActionCounter.action)
        )
        return [row[0] for row in result.all()]
