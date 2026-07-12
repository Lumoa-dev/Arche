"""IP 封禁插件 —— 业务逻辑服务。"""

from __future__ import annotations

import ipaddress
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select

try:
    import aiohttp

    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False

from backend.core.middleware import AppError

logger = logging.getLogger(__name__)


def ip_matches_cidr(ip_str: str, cidr_str: str) -> bool:
    """判断 IP 是否匹配 CIDR 段。支持 IPv4 和 IPv6。"""
    try:
        ip = ipaddress.ip_address(ip_str)
        net = ipaddress.ip_network(cidr_str, strict=False)
        return ip in net
    except ValueError:
        return False


class IpBanService:
    """IP 封禁管理服务。

    负责封禁记录的 CRUD、自动封禁规则引擎、IP 匹配检查。
    """

    def __init__(self, container):
        self.container = container
        db = container.get("db")
        self.session_factory = db["session_factory"]
        config = container.get("config")
        self._webhook_url = config.get("IP_BAN_WEBHOOK_URL", "")
        self._counters: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self._last_cleanup = 0.0

    def _cleanup_counters(self) -> None:
        """清理过期计数器条目。"""
        now = time.time()
        for key in list(self._counters):
            self._counters[key] = [
                (t, s) for t, s in self._counters[key] if now - t < 3600
            ]
            if not self._counters[key]:
                del self._counters[key]
        self._last_cleanup = now

    # ── IP 检查 ──

    async def is_ip_banned(self, ip_str: str) -> bool:
        """检查 IP 是否在活跃封禁列表中（含 CIDR 匹配）。"""
        now = datetime.now(timezone.utc)
        from backend.plugins.ip_ban.models import IpBan

        async with self.session_factory() as session:
            result = await session.execute(
                select(IpBan).where(
                    IpBan.is_active.is_(True),
                    or_(
                        IpBan.expires_at.is_(None),
                        IpBan.expires_at > now,
                    ),
                )
            )
            active_bans = result.scalars().all()

        return any(ip_matches_cidr(ip_str, ban.ip_or_cidr) for ban in active_bans)

    async def get_active_ip_ranges(self) -> list[str]:
        """获取所有活跃的 IP/CIDR 段（用于初始化布隆过滤器）。"""
        now = datetime.now(timezone.utc)
        from backend.plugins.ip_ban.models import IpBan

        async with self.session_factory() as session:
            result = await session.execute(
                select(IpBan.ip_or_cidr).where(
                    IpBan.is_active.is_(True),
                    or_(
                        IpBan.expires_at.is_(None),
                        IpBan.expires_at > now,
                    ),
                )
            )
            return [row[0] for row in result.all()]

    # ── 手动封禁管理 ──

    async def ban_ip(
        self,
        ip_or_cidr: str,
        reason: str = "",
        ban_type: str = "manual",
        rule_id: str | None = None,
        banned_by: str | None = None,
        duration_minutes: int | None = None,
    ) -> dict:
        """封禁一个 IP 或 CIDR 段。如果已存在活跃记录则返回已有记录。"""
        from backend.plugins.ip_ban.models import IpBan, IpBanLog

        expires_at = None
        if duration_minutes and duration_minutes > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=duration_minutes
            )

        async with self.session_factory() as session:
            existing_result = await session.execute(
                select(IpBan).where(
                    IpBan.ip_or_cidr == ip_or_cidr,
                    IpBan.is_active.is_(True),
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                if expires_at:
                    existing.expires_at = expires_at
                if reason:
                    existing.reason = reason
                await session.commit()
                await session.refresh(existing)
                return self._ban_to_dict(existing)

            ban = IpBan(
                ip_or_cidr=ip_or_cidr,
                ban_type=ban_type,
                reason=reason,
                rule_id=rule_id,
                banned_by=banned_by,
                expires_at=expires_at,
            )
            session.add(ban)

            log = IpBanLog(
                ip_or_cidr=ip_or_cidr,
                action="ban",
                ban_type=ban_type,
                reason=reason,
                operator=banned_by,
                detail=(
                    f"封禁时长: {duration_minutes}分钟"
                    if duration_minutes
                    else "永久封禁"
                ),
            )
            session.add(log)

            await session.commit()
            await session.refresh(ban)

        await self._send_webhook_notification(
            "ip_banned",
            {
                "ip_or_cidr": ip_or_cidr,
                "ban_type": ban_type,
                "reason": reason,
                "duration_minutes": duration_minutes,
            },
        )

        return self._ban_to_dict(ban)

    async def unban_ip(self, ban_id: int, operator: str | None = None) -> dict:
        """解封一个封禁记录。"""
        from backend.plugins.ip_ban.models import IpBan, IpBanLog

        async with self.session_factory() as session:
            result = await session.execute(select(IpBan).where(IpBan.id == ban_id))
            ban = result.scalar_one_or_none()
            if not ban:
                raise AppError("封禁记录不存在", code="ban_not_found", status_code=404)

            ban.is_active = False

            log = IpBanLog(
                ban_id=ban.id,
                ip_or_cidr=ban.ip_or_cidr,
                action="unban",
                ban_type=ban.ban_type,
                reason=ban.reason,
                operator=operator,
            )
            session.add(log)

            await session.commit()
            await session.refresh(ban)

        return self._ban_to_dict(ban)

    async def batch_unban(self, ban_ids: list[int], operator: str | None = None) -> int:
        """批量解封，返回解封数量。"""
        from backend.plugins.ip_ban.models import IpBan, IpBanLog

        count = 0
        async with self.session_factory() as session:
            for ban_id in ban_ids:
                result = await session.execute(select(IpBan).where(IpBan.id == ban_id))
                ban = result.scalar_one_or_none()
                if ban and ban.is_active:
                    ban.is_active = False
                    log = IpBanLog(
                        ban_id=ban.id,
                        ip_or_cidr=ban.ip_or_cidr,
                        action="unban",
                        ban_type=ban.ban_type,
                        reason=ban.reason,
                        operator=operator,
                    )
                    session.add(log)
                    count += 1
            await session.commit()

        return count

    async def list_bans(
        self,
        page: int = 1,
        page_size: int = 20,
        ban_type: str | None = None,
        is_active: bool | None = None,
        keyword: str | None = None,
    ) -> dict:
        """分页查询封禁列表。"""
        from backend.plugins.ip_ban.models import IpBan

        async with self.session_factory() as session:
            query = select(IpBan)

            if ban_type:
                query = query.where(IpBan.ban_type == ban_type)
            if is_active is not None:
                query = query.where(IpBan.is_active.is_(is_active))
            if keyword:
                query = query.where(IpBan.ip_or_cidr.contains(keyword))

            count_query = select(func.count(IpBan.id))
            if ban_type:
                count_query = count_query.where(IpBan.ban_type == ban_type)
            if is_active is not None:
                count_query = count_query.where(IpBan.is_active.is_(is_active))
            if keyword:
                count_query = count_query.where(IpBan.ip_or_cidr.contains(keyword))

            total_result = await session.execute(count_query)
            total = total_result.scalar_one()

            query = (
                query.order_by(IpBan.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(query)
            bans = result.scalars().all()

            return {
                "list": [self._ban_to_dict(b) for b in bans],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    async def get_ban_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        action: str | None = None,
    ) -> dict:
        """分页查询封禁操作日志。"""
        from backend.plugins.ip_ban.models import IpBanLog

        async with self.session_factory() as session:
            query = select(IpBanLog)
            if action:
                query = query.where(IpBanLog.action == action)

            count_query = select(func.count(IpBanLog.id))
            if action:
                count_query = count_query.where(IpBanLog.action == action)
            total_result = await session.execute(count_query)
            total = total_result.scalar_one()

            query = (
                query.order_by(IpBanLog.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(query)
            logs = result.scalars().all()

            return {
                "list": [
                    {
                        "id": log.id,
                        "ban_id": log.ban_id,
                        "ip_or_cidr": log.ip_or_cidr,
                        "action": log.action,
                        "ban_type": log.ban_type,
                        "reason": log.reason,
                        "operator": log.operator,
                        "detail": log.detail,
                        "created_at": log.created_at.isoformat()
                        if log.created_at
                        else None,
                    }
                    for log in logs
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    # ── 自动封禁规则引擎 ──

    async def get_rule_configs(self) -> list[dict]:
        """获取所有自动封禁规则配置。"""
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with self.session_factory() as session:
            result = await session.execute(
                select(AutoBanRuleConfig).order_by(AutoBanRuleConfig.id)
            )
            rules = result.scalars().all()

        default_rules = self._get_default_rules()
        merged = {}
        for rule in rules:
            merged[rule.id] = {
                "id": rule.id,
                "name": rule.name,
                "enabled": rule.enabled,
                "threshold": rule.threshold,
                "window_seconds": rule.window_seconds,
                "ban_duration_minutes": rule.ban_duration_minutes,
                "description": rule.description,
            }

        for rule_id, default in default_rules.items():
            if rule_id not in merged:
                await self._ensure_default_rule(rule_id, default)
                merged[rule_id] = {
                    "id": rule_id,
                    **default,
                }

        return list(merged.values())

    async def update_rule_config(self, rule_id: str, updates: dict) -> dict:
        """更新自动封禁规则配置。"""
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with self.session_factory() as session:
            result = await session.execute(
                select(AutoBanRuleConfig).where(AutoBanRuleConfig.id == rule_id)
            )
            rule = result.scalar_one_or_none()
            if not rule:
                raise AppError("规则不存在", code="rule_not_found", status_code=404)

            allowed_fields = {
                "enabled",
                "threshold",
                "window_seconds",
                "ban_duration_minutes",
                "description",
                "name",
            }
            for key, value in updates.items():
                if key in allowed_fields:
                    setattr(rule, key, value)

            await session.commit()
            await session.refresh(rule)

        return {
            "id": rule.id,
            "name": rule.name,
            "enabled": rule.enabled,
            "threshold": rule.threshold,
            "window_seconds": rule.window_seconds,
            "ban_duration_minutes": rule.ban_duration_minutes,
            "description": rule.description,
        }

    def _get_default_rules(self) -> dict:
        """获取默认规则定义。"""
        return {
            "login_failure": {
                "name": "登录失败封禁",
                "enabled": True,
                "threshold": 10,
                "window_seconds": 300,
                "ban_duration_minutes": 30,
                "description": "同 IP 5 分钟内登录失败次数超过阈值，自动封禁 30 分钟",
            },
            "high_4xx": {
                "name": "4xx 高频封禁",
                "enabled": True,
                "threshold": 50,
                "window_seconds": 3600,
                "ban_duration_minutes": 60,
                "description": "同 IP 1 小时内 4xx 请求超过阈值，自动封禁 1 小时",
            },
            "rate_limit": {
                "name": "请求频率封禁",
                "enabled": True,
                "threshold": 200,
                "window_seconds": 60,
                "ban_duration_minutes": 10,
                "description": "同 IP 1 分钟内请求数超过阈值，自动封禁 10 分钟",
            },
            "geo_surge": {
                "name": "地域突增预警",
                "enabled": True,
                "threshold": 100,
                "window_seconds": 300,
                "ban_duration_minutes": 0,
                "description": (
                    "同地域/运营商 IP 在窗口内突增超过阈值，触发告警（不自动封禁）"
                ),
            },
        }

    async def _ensure_default_rule(self, rule_id: str, default: dict) -> None:
        """确保默认规则存在于数据库中。"""
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with self.session_factory() as session:
            rule = AutoBanRuleConfig(
                id=rule_id,
                name=default["name"],
                threshold=default["threshold"],
                window_seconds=default["window_seconds"],
                ban_duration_minutes=default["ban_duration_minutes"],
                description=default["description"],
            )
            session.add(rule)
            try:
                await session.commit()
            except Exception:
                await session.rollback()

    # ── 自动封禁触发 ──

    async def record_event(
        self, event_type: str, ip_str: str, status_code: int | None = None
    ) -> None:
        """记录一个事件（登录失败 / 4xx / 请求等），触发规则检查。"""
        now = time.time()
        if now - self._last_cleanup > 60:
            self._cleanup_counters()

        key = f"{event_type}:{ip_str}"
        self._counters[key].append((now, status_code or 0))

        if event_type == "login_failure":
            await self._check_login_failure_rule(ip_str)
        elif event_type == "high_4xx" and status_code:
            await self._check_high_4xx_rule(ip_str)
        elif event_type == "rate_limit":
            await self._check_rate_limit_rule(ip_str)

    async def _check_login_failure_rule(self, ip_str: str) -> None:
        """检查登录失败规则。"""
        rules = await self.get_rule_configs()
        rule = next((r for r in rules if r["id"] == "login_failure"), None)
        if not rule or not rule["enabled"]:
            return

        key = f"login_failure:{ip_str}"
        now = time.time()
        window_start = now - rule["window_seconds"]
        count = sum(1 for t, _ in self._counters.get(key, []) if t > window_start)

        if count >= rule["threshold"]:
            logger.warning(
                "自动封禁触发 [login_failure] IP=%s count=%d threshold=%d",
                ip_str,
                count,
                rule["threshold"],
            )
            await self.ban_ip(
                ip_or_cidr=ip_str,
                reason=f"登录失败次数过多 ({count}次/{rule['window_seconds']}秒)",
                ban_type="auto",
                rule_id="login_failure",
                duration_minutes=rule["ban_duration_minutes"],
            )

    async def _check_high_4xx_rule(self, ip_str: str) -> None:
        """检查高频 4xx 规则。"""
        rules = await self.get_rule_configs()
        rule = next((r for r in rules if r["id"] == "high_4xx"), None)
        if not rule or not rule["enabled"]:
            return

        key = f"high_4xx:{ip_str}"
        now = time.time()
        window_start = now - rule["window_seconds"]
        count = sum(
            1
            for t, s in self._counters.get(key, [])
            if t > window_start and 400 <= s < 500
        )

        if count >= rule["threshold"]:
            logger.warning(
                "自动封禁触发 [high_4xx] IP=%s count=%d threshold=%d",
                ip_str,
                count,
                rule["threshold"],
            )
            await self.ban_ip(
                ip_or_cidr=ip_str,
                reason=f"4xx 请求过多 ({count}次/{rule['window_seconds']}秒)",
                ban_type="auto",
                rule_id="high_4xx",
                duration_minutes=rule["ban_duration_minutes"],
            )

    async def _check_rate_limit_rule(self, ip_str: str) -> None:
        """检查请求频率规则。"""
        rules = await self.get_rule_configs()
        rule = next((r for r in rules if r["id"] == "rate_limit"), None)
        if not rule or not rule["enabled"]:
            return

        key = f"rate_limit:{ip_str}"
        now = time.time()
        window_start = now - rule["window_seconds"]
        count = sum(1 for t, _ in self._counters.get(key, []) if t > window_start)

        if count >= rule["threshold"]:
            logger.warning(
                "自动封禁触发 [rate_limit] IP=%s count=%d threshold=%d",
                ip_str,
                count,
                rule["threshold"],
            )
            await self.ban_ip(
                ip_or_cidr=ip_str,
                reason=f"请求频率过高 ({count}次/{rule['window_seconds']}秒)",
                ban_type="auto",
                rule_id="rate_limit",
                duration_minutes=rule["ban_duration_minutes"],
            )

    # ── 通知 ──

    async def _send_webhook_notification(self, event: str, data: dict) -> None:
        """发送封禁通知到 webhook（钉钉/飞书兼容格式）。"""
        if not self._webhook_url or not _HAS_AIOHTTP:
            return

        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": (
                        f"[IP 封禁通知]\n"
                        f"事件: {event}\n"
                        f"IP/CIDR: {data.get('ip_or_cidr', '')}\n"
                        f"类型: {data.get('ban_type', '')}\n"
                        f"原因: {data.get('reason', '')}\n"
                        f"封禁时长: {data.get('duration_minutes', '永久')}分钟\n"
                    )
                },
            }
            async with aiohttp.ClientSession() as session:
                await session.post(
                    self._webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5),
                )
        except Exception:
            logger.warning("Webhook 通知发送失败: %s", str(Exception))

    # ── 工具方法 ──

    def _ban_to_dict(self, ban) -> dict:
        return {
            "id": ban.id,
            "ip_or_cidr": ban.ip_or_cidr,
            "ban_type": ban.ban_type,
            "reason": ban.reason,
            "rule_id": ban.rule_id,
            "banned_by": ban.banned_by,
            "created_at": ban.created_at.isoformat() if ban.created_at else None,
            "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
            "is_active": ban.is_active,
        }

    async def get_stats(self) -> dict:
        """获取封禁统计。"""
        from backend.plugins.ip_ban.models import IpBan, IpBanLog

        async with self.session_factory() as session:
            total_result = await session.execute(select(func.count(IpBan.id)))
            total_bans = total_result.scalar_one()

            active_result = await session.execute(
                select(func.count(IpBan.id)).where(
                    IpBan.is_active.is_(True),
                    or_(
                        IpBan.expires_at.is_(None),
                        IpBan.expires_at > datetime.now(timezone.utc),
                    ),
                )
            )
            active_bans = active_result.scalar_one()

            auto_result = await session.execute(
                select(func.count(IpBan.id)).where(IpBan.ban_type == "auto")
            )
            auto_bans = auto_result.scalar_one()

            manual_result = await session.execute(
                select(func.count(IpBan.id)).where(IpBan.ban_type == "manual")
            )
            manual_bans = manual_result.scalar_one()

            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_result = await session.execute(
                select(func.count(IpBanLog.id)).where(
                    IpBanLog.created_at >= today_start,
                    IpBanLog.action == "ban",
                )
            )
            today_bans = today_result.scalar_one()

        return {
            "total_bans": total_bans,
            "active_bans": active_bans,
            "auto_bans": auto_bans,
            "manual_bans": manual_bans,
            "today_bans": today_bans,
        }
