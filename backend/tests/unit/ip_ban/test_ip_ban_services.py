"""IpBanService 核心业务逻辑单元测试（使用内存数据库）。

IpBanService 是 IP 封禁插件的核心，涉及安全关键逻辑：
- IP/CIDR 封禁状态管理
- 自动封禁规则引擎
- 事件记录和阈值检查
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.core.middleware import AppError
from backend.plugins.ip_ban.models import AutoBanRuleConfig, IpBan, IpBanLog
from backend.plugins.ip_ban.services import IpBanService


# =============================================================================
# IpBanService — 基础 CRUD
# =============================================================================


class TestIpBanService:
    """IpBanService 核心行为测试。"""

    @pytest.mark.asyncio
    async def test_ban_ip_creates_record(self, db_container):
        """封禁 IP 应创建记录和操作日志。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="恶意攻击",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=60,
        )

        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["expires_at"] is not None

        # 验证日志存在
        async with db_container.get("db")["session_factory"]() as session:
            logs = (await session.execute(__import__("sqlalchemy").select(IpBanLog))).scalars().all()  # noqa: E501
            assert len(logs) == 1
            assert logs[0].action == "ban"

    @pytest.mark.asyncio
    async def test_ban_ip_permanent(self, db_container):
        """永久封禁不应设置过期时间。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="永久封禁",
            duration_minutes=None,
        )

        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_ban_ip_duplicate_updates_existing(self, db_container):
        """重复封禁同一 IP 应更新已有记录而非新建。"""
        service = IpBanService(db_container)
        result1 = await service.ban_ip(
            ip_or_cidr="192.168.1.1", reason="首次封禁", duration_minutes=30
        )
        result2 = await service.ban_ip(
            ip_or_cidr="192.168.1.1", reason="更新封禁", duration_minutes=120
        )

        assert result1["id"] == result2["id"]
        assert result2["reason"] == "更新封禁"

    @pytest.mark.asyncio
    async def test_unban_ip(self, db_container):
        """解封应禁用封禁记录并记录日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="10.0.0.1", reason="测试封禁", duration_minutes=60
        )

        result = await service.unban_ip(ban["id"], operator="admin")
        assert result["is_active"] is False

        # 验证操作日志
        async with db_container.get("db")["session_factory"]() as session:
            logs = (await session.execute(__import__("sqlalchemy").select(IpBanLog).where(IpBanLog.action == "unban"))).scalars().all()  # noqa: E501
            assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, db_container):
        """解封不存在的记录应抛 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(99999)
        assert excinfo.value.code == "ban_not_found"
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_unban(self, db_container):
        """批量解封应返回实际解封数量。"""
        service = IpBanService(db_container)
        ban1 = await service.ban_ip("10.0.0.1", duration_minutes=60)
        ban2 = await service.ban_ip("10.0.0.2", duration_minutes=60)
        # 先解封一个，使其 inactive
        await service.unban_ip(ban1["id"])

        # 批量解封两个（其中一个已解封）
        count = await service.batch_unban([ban1["id"], ban2["id"]], operator="admin")
        assert count == 1  # 只有 ban2 是活跃的

    @pytest.mark.asyncio
    async def test_list_bans_with_filters(self, db_container):
        """分页查询应支持类型、状态和关键词过滤。"""
        service = IpBanService(db_container)
        await service.ban_ip("10.0.0.1", ban_type="auto", duration_minutes=30)
        await service.ban_ip("10.0.0.2", ban_type="manual", duration_minutes=60)
        await service.ban_ip("192.168.1.1", ban_type="manual", duration_minutes=0)
        # 解封第二个
        bans = await service.list_bans(page=1, page_size=20)
        all_bans = bans["list"]
        if len(all_bans) >= 2:
            await service.unban_ip(all_bans[1]["id"])

        # 按类型过滤
        auto_result = await service.list_bans(ban_type="auto")
        assert all(b["ban_type"] == "auto" for b in auto_result["list"])

        # 按关键词搜索
        keyword_result = await service.list_bans(keyword="192.168")
        assert all("192.168" in b["ip_or_cidr"] for b in keyword_result["list"])

        # 分页
        page_result = await service.list_bans(page=1, page_size=1)
        assert len(page_result["list"]) <= 1
        assert page_result["page"] == 1
        assert page_result["page_size"] == 1


# =============================================================================
# IpBanService — IP 检查
# =============================================================================


class TestIpCheck:
    """IP 封禁检查逻辑测试。"""

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_true_for_banned_ip(self, db_container):
        """被封禁的 IP 应被检查出来。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            "10.0.0.5", reason="测试封禁", duration_minutes=60
        )

        is_banned = await service.is_ip_banned("10.0.0.5")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_for_clean_ip(self, db_container):
        """未被封禁的 IP 应返回 False。"""
        service = IpBanService(db_container)
        is_banned = await service.is_ip_banned("10.0.0.99")
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_cidr_match(self, db_container):
        """CIDR 段封禁后，段内 IP 应被检测为被封禁。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            "10.0.0.0/24", reason="封禁整个网段", duration_minutes=60
        )

        assert await service.is_ip_banned("10.0.0.1") is True
        assert await service.is_ip_banned("10.0.0.100") is True
        assert await service.is_ip_banned("10.0.1.1") is False  # 不在段内

    @pytest.mark.asyncio
    async def test_expired_ban_not_active(self, db_container):
        """已过期的封禁不应被视为活跃。"""
        service = IpBanService(db_container)
        # 直接插入一条已过期的封禁记录到数据库
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        async with db_container.get("db")["session_factory"]() as session:
            expired_ban = IpBan(
                ip_or_cidr="10.0.0.1",
                ban_type="manual",
                reason="已过期",
                expires_at=past_time,
            )
            session.add(expired_ban)
            await session.commit()

        is_banned = await service.is_ip_banned("10.0.0.1")
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_unbanned_ip_not_banned(self, db_container):
        """解封后的 IP 不应再被视为被封禁。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            "10.0.0.1", reason="测试", duration_minutes=60
        )
        await service.unban_ip(ban["id"])

        is_banned = await service.is_ip_banned("10.0.0.1")
        assert is_banned is False


# =============================================================================
# IpBanService — 自动封禁规则引擎
# =============================================================================


class TestAutoBanRules:
    """自动封禁规则引擎行为测试。"""

    @pytest.mark.asyncio
    async def test_rule_configs_use_defaults_when_empty(self, db_container):
        """规则表为空时应返回默认规则。"""
        service = IpBanService(db_container)
        # 第一次调用初始化数据库，第二次读取包含 enabled 等字段
        await service.get_rule_configs()
        rules = await service.get_rule_configs()

        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

        # 验证默认值（从 DB 读取，包含 enabled）
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 10
        assert login_rule["window_seconds"] == 300
        assert login_rule["enabled"] is True

    @pytest.mark.asyncio
    async def test_update_rule_config(self, db_container):
        """更新规则配置应生效。"""
        service = IpBanService(db_container)
        # 先获取规则（触发默认规则创建）
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        rule_id = login_rule["id"]

        # 更新阈值
        updated = await service.update_rule_config(
            rule_id, {"threshold": 5, "enabled": False}
        )
        assert updated["threshold"] == 5
        assert updated["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises_error(self, db_container):
        """更新不存在的规则应抛 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("nonexistent", {"threshold": 5})
        assert excinfo.value.code == "rule_not_found"

    @pytest.mark.asyncio
    async def test_update_ignores_invalid_fields(self, db_container):
        """更新规则时应忽略不允许的字段。"""
        service = IpBanService(db_container)
        rule = (await service.get_rule_configs())[0]

        updated = await service.update_rule_config(
            rule["id"],
            {"threshold": 20, "invalid_field": "should_be_ignored", "id": "hacked"},
        )
        assert updated["threshold"] == 20
        # id 不应被修改
        assert updated["id"] == rule["id"]


# =============================================================================
# IpBanService — 事件记录和自动封禁
# =============================================================================


class TestEventRecording:
    """事件记录和自动封禁触发逻辑测试。"""

    @pytest.mark.asyncio
    async def test_record_login_failure_triggers_auto_ban(self, db_container):
        """登录失败次数超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        # 将 login_failure 阈值临时改为 3
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        await service.update_rule_config(
            login_rule["id"],
            {"threshold": 3, "ban_duration_minutes": 30},
        )

        # 记录 3 次登录失败（阈值）
        ip = "10.0.0.100"
        for _ in range(3):
            await service.record_event("login_failure", ip)

        # 验证 IP 被自动封禁
        assert await service.is_ip_banned(ip) is True

    @pytest.mark.asyncio
    async def test_record_login_failure_below_threshold(self, db_container):
        """登录失败次数低于阈值不应触发封禁。"""
        service = IpBanService(db_container)
        # 先初始化规则配置到数据库（确保 enabled 字段可用）
        await service.get_rule_configs()

        ip = "10.0.0.101"
        for _ in range(2):
            await service.record_event("login_failure", ip)

        assert await service.is_ip_banned(ip) is False

    @pytest.mark.asyncio
    async def test_record_rate_limit_triggers_auto_ban(self, db_container):
        """请求频率超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()
        rate_rule = next(r for r in rules if r["id"] == "rate_limit")
        await service.update_rule_config(
            rate_rule["id"],
            {"threshold": 3, "ban_duration_minutes": 10},
        )

        ip = "10.0.0.200"
        for _ in range(3):
            await service.record_event("rate_limit", ip)

        assert await service.is_ip_banned(ip) is True

    @pytest.mark.asyncio
    async def test_disabled_rule_does_not_auto_ban(self, db_container):
        """禁用的规则不应触发自动封禁。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        await service.update_rule_config(
            login_rule["id"],
            {"enabled": False, "threshold": 1},
        )

        ip = "10.0.0.102"
        await service.record_event("login_failure", ip)

        assert await service.is_ip_banned(ip) is False

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, db_container):
        """获取活跃 IP 段列表应包含所有未过期的封禁。"""
        service = IpBanService(db_container)
        await service.ban_ip("10.0.0.0/24", duration_minutes=60)
        await service.ban_ip("192.168.1.1", duration_minutes=60)

        ranges = await service.get_active_ip_ranges()
        assert "10.0.0.0/24" in ranges
        assert "192.168.1.1" in ranges

    @pytest.mark.asyncio
    async def test_record_event_unknown_type_no_error(self, db_container):
        """未知事件类型不应导致错误。"""
        service = IpBanService(db_container)
        # 不应抛异常
        await service.record_event("unknown_event", "10.0.0.1")


# =============================================================================
# IpBanService — 统计
# =============================================================================


class TestStats:
    """封禁统计数据测试。"""

    @pytest.mark.asyncio
    async def test_get_stats_with_no_bans(self, db_container):
        """无封禁记录时统计应返回零值。"""
        service = IpBanService(db_container)
        stats = await service.get_stats()

        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0
        assert stats["today_bans"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_bans(self, db_container):
        """有封禁记录时应准确统计。"""
        service = IpBanService(db_container)
        await service.ban_ip("10.0.0.1", ban_type="manual", duration_minutes=60)
        await service.ban_ip("10.0.0.2", ban_type="auto", duration_minutes=30)

        stats = await service.get_stats()
        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 2
        assert stats["auto_bans"] == 1
        assert stats["manual_bans"] == 1
        assert stats["today_bans"] >= 1


# =============================================================================
# IpBanService — 边界情况
# =============================================================================


class TestEdgeCases:
    """IpBanService 边界情况测试。"""

    @pytest.mark.asyncio
    async def test_ban_with_cidr_notation(self, db_container):
        """封禁 CIDR 段应正常工作。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            "10.0.0.0/16", reason="封禁大段", duration_minutes=60
        )
        assert result["ip_or_cidr"] == "10.0.0.0/16"
        assert await service.is_ip_banned("10.0.1.1") is True
        assert await service.is_ip_banned("10.1.0.1") is False

    @pytest.mark.asyncio
    async def test_ban_zero_duration_creates_permanent(self, db_container):
        """duration_minutes=0 应创建永久封禁。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            "10.0.0.1", duration_minutes=0
        )
        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_list_bans_empty_result(self, db_container):
        """无封禁记录时分页查询应返回空列表。"""
        service = IpBanService(db_container)
        result = await service.list_bans(page=1, page_size=20)
        assert result["total"] == 0
        assert result["list"] == []
        assert result["page"] == 1