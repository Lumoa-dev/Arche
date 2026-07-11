"""IpBanService 单元测试 —— 封禁管理、自动规则引擎、统计。

覆盖：
- ban_ip / unban_ip / batch_unban 的 CRUD 行为
- list_bans / get_ban_logs 的分页和过滤
- get_stats 的统计聚合
- is_ip_banned 的活跃/过期判断
- 自动封禁规则引擎：record_event 触发规则检查
- get_rule_configs / update_rule_config 的规则管理
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService


class TestIpBanServiceBase:
    """IpBanService 基础行为。"""

    # ── ban_ip ──

    @pytest.mark.asyncio
    async def test_ban_ip_creates_new_ban(self, db_container):
        """封禁新 IP 应创建记录并返回封禁信息。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="恶意扫描",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=60,
        )

        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["reason"] == "恶意扫描"
        assert result["banned_by"] == "admin"
        assert result["is_active"] is True
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_ip_permanent(self, db_container):
        """不传 duration_minutes 应创建永久封禁。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="永久封禁",
        )

        assert result["ip_or_cidr"] == "10.0.0.1"
        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_ban_ip_updates_existing_active_ban(self, db_container):
        """对已存在的活跃封禁记录再次封禁应更新信息。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="首次封禁")
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="更新封禁原因",
            duration_minutes=120,
        )

        assert result["reason"] == "更新封禁原因"
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_ip_cidr_range(self, db_container):
        """封禁 CIDR 段应正确存储。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.0/24",
            reason="封禁整个子网",
        )

        assert result["ip_or_cidr"] == "10.0.0.0/24"
        assert result["is_active"] is True

    # ── unban_ip ──

    @pytest.mark.asyncio
    async def test_unban_ip_deactivates_ban(self, db_container):
        """解封应标记为未激活。"""
        service = IpBanService(db_container)
        created = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")
        result = await service.unban_ip(ban_id=created["id"], operator="admin")

        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, db_container):
        """解封不存在的记录应抛出 AppError。"""
        service = IpBanService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(ban_id=99999, operator="admin")

        assert excinfo.value.code == "ban_not_found"
        assert excinfo.value.status_code == 404

    # ── batch_unban ──

    @pytest.mark.asyncio
    async def test_batch_unban_multiple(self, db_container):
        """批量解封应返回实际解封数量。"""
        service = IpBanService(db_container)
        b1 = await service.ban_ip(ip_or_cidr="10.0.0.2", reason="测试")
        b2 = await service.ban_ip(ip_or_cidr="10.0.0.3", reason="测试")
        b3 = await service.ban_ip(ip_or_cidr="10.0.0.4", reason="测试")

        count = await service.batch_unban(
            ban_ids=[b1["id"], b2["id"], b3["id"]], operator="admin"
        )

        assert count == 3

    @pytest.mark.asyncio
    async def test_batch_unban_partial(self, db_container):
        """批量解封中不存在的记录应被忽略。"""
        service = IpBanService(db_container)
        b1 = await service.ban_ip(ip_or_cidr="10.0.0.5", reason="测试")

        count = await service.batch_unban(
            ban_ids=[b1["id"], 99999], operator="admin"
        )

        assert count == 1

    # ── list_bans ──

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, db_container):
        """分页查询应返回正确数量和元数据。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}", reason="测试")

        result = await service.list_bans(page=1, page_size=2)

        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, db_container):
        """按 ban_type 过滤应只返回对应类型的记录。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="手动", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="自动", ban_type="auto")

        result = await service.list_bans(ban_type="auto")

        assert result["total"] == 1
        assert result["list"][0]["ban_type"] == "auto"

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_keyword(self, db_container):
        """按 IP 关键词过滤应返回匹配记录。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1", reason="测试")
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")

        result = await service.list_bans(keyword="192.168")

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_active(self, db_container):
        """按活跃状态过滤应正确筛选。"""
        service = IpBanService(db_container)
        b = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")
        await service.unban_ip(ban_id=b["id"])

        result = await service.list_bans(is_active=False)

        assert result["total"] == 1
        assert result["list"][0]["is_active"] is False

    # ── get_ban_logs ──

    @pytest.mark.asyncio
    async def test_get_ban_logs_records_ban_and_unban(self, db_container):
        """封禁和解封操作应产生操作日志。"""
        service = IpBanService(db_container)
        created = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")
        await service.unban_ip(ban_id=created["id"], operator="admin")

        logs = await service.get_ban_logs(page=1, page_size=10)

        assert logs["total"] == 2
        actions = [log["action"] for log in logs["list"]]
        assert "ban" in actions
        assert "unban" in actions

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, db_container):
        """按操作类型过滤日志。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")

        result = await service.get_ban_logs(action="ban")

        assert result["total"] == 1
        assert result["list"][0]["action"] == "ban"

    # ── get_stats ──

    @pytest.mark.asyncio
    async def test_get_stats_returns_counts(self, db_container):
        """统计接口应返回正确的计数。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="手动", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="自动", ban_type="auto")

        stats = await service.get_stats()

        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 2
        assert stats["manual_bans"] == 1
        assert stats["auto_bans"] == 1

    # ── is_ip_banned ──

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_true_for_banned_ip(self, db_container):
        """被封禁的 IP 应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")

        result = await service.is_ip_banned("10.0.0.1")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_for_unbanned_ip(self, db_container):
        """未被封禁的 IP 应返回 False。"""
        service = IpBanService(db_container)

        result = await service.is_ip_banned("10.0.0.99")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_matches_cidr_range(self, db_container):
        """IP 在封禁的 CIDR 段内应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.0/24", reason="封禁子网")

        assert await service.is_ip_banned("10.0.0.50") is True
        assert await service.is_ip_banned("10.0.1.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_for_expired_ban(self, db_container):
        """已过期的封禁应返回 False。"""
        service = IpBanService(db_container)
        # 创建 1 分钟的封禁，然后将 expires_at 设为过去
        created = await service.ban_ip(
            ip_or_cidr="10.0.0.1", reason="测试", duration_minutes=1
        )

        from backend.plugins.ip_ban.models import IpBan
        from sqlalchemy import select

        async with db_container.get("db")["session_factory"]() as session:
            result = await session.execute(select(IpBan).where(IpBan.id == created["id"]))
            ban = result.scalar_one()
            ban.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        result = await service.is_ip_banned("10.0.0.1")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_after_unban(self, db_container):
        """解封后 IP 应返回 False。"""
        service = IpBanService(db_container)
        created = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")
        await service.unban_ip(ban_id=created["id"])

        result = await service.is_ip_banned("10.0.0.1")

        assert result is False


class TestIpBanRuleEngine:
    """自动封禁规则引擎测试。"""

    # ── get_rule_configs ──

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, db_container):
        """未配置任何规则时，应返回默认规则。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()

        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_get_rule_configs_merges_db_rules(self, db_container):
        """数据库中的规则应覆盖默认值。"""
        from backend.plugins.ip_ban.models import AutoBanRuleConfig

        async with db_container.get("db")["session_factory"]() as session:
            rule = AutoBanRuleConfig(
                id="login_failure",
                name="自定义登录失败",
                threshold=5,
                window_seconds=60,
                ban_duration_minutes=10,
                description="自定义规则",
            )
            session.add(rule)
            await session.commit()

        service = IpBanService(db_container)
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")

        assert login_rule["threshold"] == 5
        assert login_rule["window_seconds"] == 60

    # ── update_rule_config ──

    @pytest.mark.asyncio
    async def test_update_rule_config_updates_fields(self, db_container):
        """更新规则应只修改允许的字段。"""
        service = IpBanService(db_container)
        # 先触发 get_rule_configs 确保默认规则已创建
        await service.get_rule_configs()

        result = await service.update_rule_config(
            "login_failure",
            {"threshold": 15, "ban_duration_minutes": 45},
        )

        assert result["threshold"] == 15
        assert result["ban_duration_minutes"] == 45
        # 未更新的字段应保持默认
        assert result["enabled"] is True

    @pytest.mark.asyncio
    async def test_update_rule_config_nonexistent_raises_error(self, db_container):
        """更新不存在的规则应抛出 AppError。"""
        service = IpBanService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config(
                "nonexistent_rule",
                {"threshold": 10},
            )

        assert excinfo.value.code == "rule_not_found"

    # ── record_event → 规则触发 ──

    @pytest.mark.asyncio
    async def test_record_event_login_failure_triggers_ban(self, db_container):
        """登录失败事件超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        # 降低 login_failure 阈值以方便测试
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"threshold": 3, "window_seconds": 60, "ban_duration_minutes": 30},
        )

        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.100")

        is_banned = await service.is_ip_banned("10.0.0.100")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_below_threshold_no_ban(self, db_container):
        """登录失败事件未达阈值不应触发封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"threshold": 10, "window_seconds": 60},
        )

        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.101")

        is_banned = await service.is_ip_banned("10.0.0.101")
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_record_event_rate_limit_triggers_ban(self, db_container):
        """请求频率事件超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "rate_limit",
            {"threshold": 5, "window_seconds": 60, "ban_duration_minutes": 10},
        )

        for _ in range(5):
            await service.record_event("rate_limit", "10.0.0.200")

        is_banned = await service.is_ip_banned("10.0.0.200")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_high_4xx_triggers_ban(self, db_container):
        """4xx 高频事件超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "high_4xx",
            {"threshold": 3, "window_seconds": 60, "ban_duration_minutes": 10},
        )

        for _ in range(3):
            await service.record_event("high_4xx", "10.0.0.30", status_code=401)

        # 验证封禁记录已创建
        bans = await service.list_bans()
        assert bans["total"] > 0, "应创建封禁记录"

        is_banned = await service.is_ip_banned("10.0.0.30")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_disabled_rule_does_not_ban(self, db_container):
        """禁用的规则不应触发封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"enabled": False, "threshold": 1, "window_seconds": 60},
        )

        await service.record_event("login_failure", "10.0.0.50")

        is_banned = await service.is_ip_banned("10.0.0.50")
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_cleanup_counters_removes_expired_entries(self, db_container):
        """清理过期计数器应删除超时条目。"""
        service = IpBanService(db_container)
        service._counters["login_failure:10.0.0.1"] = [
            (time.time() - 7200, 0),  # 2 小时前，已过期
            (time.time() - 100, 0),  # 仍在窗口内
        ]

        service._cleanup_counters()

        assert len(service._counters["login_failure:10.0.0.1"]) == 1

    @pytest.mark.asyncio
    async def test_cleanup_counters_removes_empty_keys(self, db_container):
        """清理后空列表的键应被删除。"""
        service = IpBanService(db_container)
        service._counters["old_key:1.2.3.4"] = [(time.time() - 7200, 0)]

        service._cleanup_counters()

        assert "old_key:1.2.3.4" not in service._counters