"""IpBanService 集成行为测试。

使用真实内存数据库测试 IpBanService 的 CRUD、自动封禁引擎和统计功能。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService


@pytest.mark.asyncio
class TestIpBanService:
    """IpBanService 核心功能测试。"""

    # ── 封禁管理 ──

    async def test_ban_ip_basic(self, db_container):
        """基础封禁操作。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
            ban_type="manual",
            banned_by="admin",
        )

        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["reason"] == "测试封禁"
        assert result["is_active"] is True
        assert result["banned_by"] == "admin"

    async def test_ban_ip_with_duration(self, db_container):
        """带时长封禁。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            duration_minutes=30,
        )

        assert result["is_active"] is True
        assert result["expires_at"] is not None

    async def test_ban_ip_permanent(self, db_container):
        """永久封禁（无过期时间）。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="永久封禁",
        )

        assert result["is_active"] is True
        assert result["expires_at"] is None

    async def test_ban_ip_duplicate_updates_existing(self, db_container):
        """重复封禁同一 IP 时更新已有记录。"""
        service = IpBanService(db_container)
        result1 = await service.ban_ip(ip_or_cidr="192.168.1.1", reason="首次封禁")
        result2 = await service.ban_ip(
            ip_or_cidr="192.168.1.1", reason="更新封禁原因"
        )

        assert result2["id"] == result1["id"]
        assert result2["reason"] == "更新封禁原因"

    async def test_ban_ip_cidr(self, db_container):
        """封禁 CIDR 段。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(ip_or_cidr="192.168.0.0/16", reason="封禁整个段")

        assert result["ip_or_cidr"] == "192.168.0.0/16"
        assert result["is_active"] is True

    async def test_ban_ip_creates_log(self, db_container):
        """封禁操作创建操作日志。"""
        from backend.plugins.ip_ban.models import IpBanLog

        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.99", reason="测试日志")

        logs = await service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] >= 1
        assert logs["list"][0]["action"] == "ban"
        assert logs["list"][0]["ip_or_cidr"] == "10.0.0.99"

    # ── 解封管理 ──

    async def test_unban_ip(self, db_container):
        """解封操作。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.3", reason="待解封")

        result = await service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

    async def test_unban_ip_not_found(self, db_container):
        """解封不存在的记录应报错。"""
        service = IpBanService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(ban_id=99999, operator="admin")
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "ban_not_found"

    async def test_batch_unban(self, db_container):
        """批量解封。"""
        service = IpBanService(db_container)
        ban1 = await service.ban_ip(ip_or_cidr="10.0.0.4", reason="批量1")
        ban2 = await service.ban_ip(ip_or_cidr="10.0.0.5", reason="批量2")

        count = await service.batch_unban(
            ban_ids=[ban1["id"], ban2["id"]], operator="admin"
        )
        assert count == 2

    async def test_batch_unban_partial(self, db_container):
        """批量解封部分已解封的记录。"""
        service = IpBanService(db_container)
        ban1 = await service.ban_ip(ip_or_cidr="10.0.0.6", reason="有效")
        ban2 = await service.ban_ip(ip_or_cidr="10.0.0.7", reason="已解封")
        await service.unban_ip(ban_id=ban2["id"], operator="admin")

        count = await service.batch_unban(
            ban_ids=[ban1["id"], ban2["id"]], operator="admin"
        )
        assert count == 1  # 只有 ban1 被解封

    # ── IP 检查 ──

    async def test_is_ip_banned_exact_match(self, db_container):
        """精确 IP 封禁检查。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.8", reason="测试")

        assert await service.is_ip_banned("10.0.0.8") is True
        assert await service.is_ip_banned("10.0.0.9") is False

    async def test_is_ip_banned_cidr_match(self, db_container):
        """CIDR 段封禁检查。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.0/24", reason="段封禁")

        assert await service.is_ip_banned("192.168.1.100") is True
        assert await service.is_ip_banned("192.168.2.1") is False

    async def test_is_ip_banned_expired(self, db_container):
        """已过期封禁不拦截。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.10",
            reason="已过期",
            duration_minutes=0,  # 立即过期
        )

        # 修改 expires_at 为过去时间
        from backend.plugins.ip_ban.models import IpBan
        from sqlalchemy import select

        async with db_container.get("db")["session_factory"]() as session:
            result = await session.execute(
                select(IpBan).where(IpBan.ip_or_cidr == "10.0.0.10")
            )
            ban = result.scalar_one()
            ban.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        assert await service.is_ip_banned("10.0.0.10") is False

    async def test_is_ip_banned_unbanned(self, db_container):
        """解封后不再拦截。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.11", reason="待解封")
        await service.unban_ip(ban_id=ban["id"], operator="admin")

        assert await service.is_ip_banned("10.0.0.11") is False

    # ── 列表查询 ──

    async def test_list_bans_pagination(self, db_container):
        """分页查询封禁列表。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{20+i}", reason=f"测试{i}")

        result = await service.list_bans(page=1, page_size=2)
        assert len(result["list"]) == 2
        assert result["total"] == 5
        assert result["page"] == 1
        assert result["page_size"] == 2

    async def test_list_bans_filter_by_type(self, db_container):
        """按封禁类型筛选。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.30", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.31", ban_type="auto")

        manual = await service.list_bans(ban_type="manual")
        auto = await service.list_bans(ban_type="auto")
        assert manual["total"] >= 1
        assert auto["total"] >= 1
        assert all(b["ban_type"] == "manual" for b in manual["list"])

    async def test_list_bans_filter_by_keyword(self, db_container):
        """按关键词搜索 IP。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.40")
        await service.ban_ip(ip_or_cidr="10.0.0.41")

        result = await service.list_bans(keyword="10.0.0.40")
        assert result["total"] >= 1
        assert all("10.0.0.40" in b["ip_or_cidr"] for b in result["list"])

    async def test_list_bans_empty(self, db_container):
        """空封禁列表。"""
        service = IpBanService(db_container)
        result = await service.list_bans()
        assert result["total"] == 0
        assert result["list"] == []

    # ── 封禁日志 ──

    async def test_get_ban_logs(self, db_container):
        """查询封禁操作日志。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.50", reason="日志测试")
        await service.ban_ip(ip_or_cidr="10.0.0.51", reason="更多日志")

        logs = await service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] >= 2
        assert len(logs["list"]) >= 2

    async def test_get_ban_logs_filter_by_action(self, db_container):
        """按操作类型筛选日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.52")
        await service.unban_ip(ban_id=ban["id"], operator="admin")

        ban_logs = await service.get_ban_logs(action="ban")
        unban_logs = await service.get_ban_logs(action="unban")
        assert ban_logs["total"] >= 1
        assert unban_logs["total"] >= 1
        assert all(l["action"] == "unban" for l in unban_logs["list"])

    # ── 统计 ──

    async def test_get_stats(self, db_container):
        """获取封禁统计。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.60", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.61", ban_type="auto")

        stats = await service.get_stats()
        assert stats["total_bans"] >= 2
        assert stats["active_bans"] >= 2
        assert stats["manual_bans"] >= 1
        assert stats["auto_bans"] >= 1

    # ── 活跃 IP 段 ──

    async def test_get_active_ip_ranges(self, db_container):
        """获取活跃 IP/CIDR 段列表。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.70")
        await service.ban_ip(ip_or_cidr="192.168.0.0/16")

        ranges = await service.get_active_ip_ranges()
        assert "10.0.0.70" in ranges
        assert "192.168.0.0/16" in ranges

    # ── 自动封禁规则引擎 ──

    async def test_rule_configs_defaults(self, db_container):
        """获取默认规则配置。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()

        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    async def test_update_rule_config(self, db_container):
        """更新规则配置。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()  # 确保默认规则已创建

        updated = await service.update_rule_config(
            "login_failure", {"threshold": 20, "enabled": False}
        )
        assert updated["threshold"] == 20
        assert updated["enabled"] is False

    async def test_update_rule_config_not_found(self, db_container):
        """更新不存在的规则应报错。"""
        service = IpBanService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("nonexistent_rule", {"enabled": False})
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "rule_not_found"

    # ── 自动封禁触发 ──

    async def test_record_event_login_failure_trigger_ban(self, db_container):
        """登录失败次数超过阈值触发自动封禁。"""
        service = IpBanService(db_container)

        # 先确保规则存在于数据库中（调用两次：第一次创建，第二次从 DB 读取）
        await service.get_rule_configs()
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        threshold = login_rule["threshold"]

        # 触发超过阈值的登录失败事件
        for i in range(threshold + 1):
            await service.record_event("login_failure", "10.0.0.100")

        # 验证被自动封禁
        assert await service.is_ip_banned("10.0.0.100") is True

    async def test_record_event_below_threshold(self, db_container):
        """登录失败次数低于阈值不触发封禁。"""
        service = IpBanService(db_container)

        # 先确保规则存在于数据库中
        await service.get_rule_configs()
        await service.get_rule_configs()

        # 仅触发几次
        for i in range(3):
            await service.record_event("login_failure", "10.0.0.101")

        assert await service.is_ip_banned("10.0.0.101") is False

    async def test_record_event_rate_limit(self, db_container):
        """请求频率超过阈值触发自动封禁。"""
        service = IpBanService(db_container)

        # 先确保规则存在于数据库中
        await service.get_rule_configs()
        rules = await service.get_rule_configs()
        rate_rule = next(r for r in rules if r["id"] == "rate_limit")
        threshold = rate_rule["threshold"]

        for i in range(threshold + 1):
            await service.record_event("rate_limit", "10.0.0.102")

        assert await service.is_ip_banned("10.0.0.102") is True

    async def test_record_event_high_4xx(self, db_container):
        """4xx 高频触发自动封禁。"""
        service = IpBanService(db_container)

        # 先确保规则存在于数据库中
        await service.get_rule_configs()
        rules = await service.get_rule_configs()
        rule = next(r for r in rules if r["id"] == "high_4xx")
        threshold = rule["threshold"]

        for i in range(threshold + 1):
            await service.record_event("high_4xx", "10.0.0.103", status_code=403)

        assert await service.is_ip_banned("10.0.0.103") is True

    async def test_record_event_mixed_ips_independent(self, db_container):
        """不同 IP 的计数器相互独立。"""
        service = IpBanService(db_container)

        # 先确保规则存在于数据库中
        await service.get_rule_configs()
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        threshold = login_rule["threshold"]

        # IP-A 触发阈值
        for i in range(threshold + 1):
            await service.record_event("login_failure", "10.0.0.200")

        # IP-B 只触发少量
        for i in range(3):
            await service.record_event("login_failure", "10.0.0.201")

        assert await service.is_ip_banned("10.0.0.200") is True
        assert await service.is_ip_banned("10.0.0.201") is False

    # ── 计数器清理 ──

    async def test_counter_cleanup(self, db_container):
        """计数器清理过期的条目。"""
        import time

        service = IpBanService(db_container)

        # 添加一个过期条目到计数器
        key = "login_failure:10.0.0.99"
        service._counters[key] = [(time.time() - 4000, 0)]  # 超过 1 小时

        # 触发清理
        service._cleanup_counters()

        assert key not in service._counters