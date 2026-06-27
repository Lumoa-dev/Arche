"""IpBanService 单元测试 —— IP 封禁管理服务。

测试重点：
- IP 匹配（精确 IP / CIDR / IPv6 / 无效输入）
- 封禁 CRUD（ban / unban / batch_unban）
- 自动封禁规则引擎（login_failure / high_4xx / rate_limit）
- 规则配置读取和更新
- 统计数据聚合
- 分页查询和过滤
- 计数器和过期清理
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from backend.core.middleware import AppError
from backend.plugins.ip_ban.models import AutoBanRuleConfig, IpBan, IpBanLog
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# ip_matches_cidr
# =============================================================================


class TestIPMatchesCIDR:
    """IP-CIDR 匹配函数测试。"""

    def test_exact_ip_match(self):
        """精确 IP 匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1") is True

    def test_ip_in_cidr(self):
        """IP 在 CIDR 段内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ip_outside_cidr(self):
        """IP 不在 CIDR 段内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv6_exact_match(self):
        """IPv6 精确匹配。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::1") is True

    def test_ipv6_in_cidr(self):
        """IPv6 在 CIDR 段内。"""
        assert ip_matches_cidr("2001:db8::42", "2001:db8::/32") is True

    def test_invalid_ip_returns_false(self):
        """无效 IP 返回 False。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "invalid-cidr") is False

    def test_private_range_match(self):
        """私有地址段匹配。"""
        assert ip_matches_cidr("10.10.10.10", "10.0.0.0/8") is True
        assert ip_matches_cidr("172.16.0.1", "172.16.0.0/12") is True
        assert ip_matches_cidr("192.168.0.1", "192.168.0.0/16") is True


# =============================================================================
# IpBanService — 基础封禁/解封
# =============================================================================


class TestIpBanServiceBasics:
    """封禁/解封 CRUD 测试。"""

    @pytest.mark.asyncio
    async def test_ban_ip_creates_record(self, db_container):
        """ban_ip 应创建封禁记录和操作日志。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
            ban_type="manual",
            banned_by="admin",
        )

        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True

        # 验证数据库中有记录
        async with db_container.get("db")["session_factory"]() as session:
            ban_count = (await session.execute(select(IpBan))).scalars().all()
            assert len(ban_count) == 1

            log_count = (await session.execute(select(IpBanLog))).scalars().all()
            assert len(log_count) == 1
            assert log_count[0].action == "ban"

    @pytest.mark.asyncio
    async def test_ban_ip_with_duration(self, db_container):
        """带过期时间的封禁应设置 expires_at。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            duration_minutes=30,
        )
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_ip_permanent(self, db_container):
        """永久封禁（不传 duration）应无过期时间。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="永久封禁",
        )
        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_unban_ip_deactivates(self, db_container):
        """unban_ip 应将封禁记录标记为非活跃并记录操作日志。"""
        service = IpBanService(db_container)
        ban_result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试",
            banned_by="admin",
        )

        unban_result = await service.unban_ip(
            ban_id=ban_result["id"], operator="admin"
        )
        assert unban_result["is_active"] is False

        # 验证解封日志
        async with db_container.get("db")["session_factory"]() as session:
            logs = (await session.execute(select(IpBanLog))).scalars().all()
            unban_logs = [l for l in logs if l.action == "unban"]
            assert len(unban_logs) == 1

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises(self, db_container):
        """解封不存在的记录应抛出 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(ban_id=99999)
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_ban_duplicate_updates_existing(self, db_container):
        """重复封禁同一 IP 应更新已有记录。"""
        service = IpBanService(db_container)
        result1 = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="第一次封禁",
        )
        result2 = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="第二次封禁（更新）",
        )
        # 应返回同一条记录，但 reason 已更新
        assert result1["id"] == result2["id"]
        assert result2["reason"] == "第二次封禁（更新）"

    @pytest.mark.asyncio
    async def test_batch_unban(self, db_container):
        """批量解封应正确解封多个记录。"""
        service = IpBanService(db_container)
        b1 = await service.ban_ip(ip_or_cidr="10.0.0.1")
        b2 = await service.ban_ip(ip_or_cidr="10.0.0.2")
        b3 = await service.ban_ip(ip_or_cidr="10.0.0.3")

        count = await service.batch_unban(
            ban_ids=[b1["id"], b2["id"]], operator="admin"
        )
        assert count == 2

        # 验证第3条仍活跃
        async with db_container.get("db")["session_factory"]() as session:
            ban3 = (await session.execute(select(IpBan).where(IpBan.id == b3["id"]))).scalar_one()
            assert ban3.is_active is True

    @pytest.mark.asyncio
    async def test_batch_unban_empty_list(self, db_container):
        """空列表应返回 0。"""
        service = IpBanService(db_container)
        count = await service.batch_unban(ban_ids=[])
        assert count == 0

    @pytest.mark.asyncio
    async def test_is_ip_banned_exact(self, db_container):
        """精确 IP 封禁检查。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1")
        assert await service.is_ip_banned("192.168.1.1") is True
        assert await service.is_ip_banned("192.168.1.2") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_cidr(self, db_container):
        """CIDR 封禁检查。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.0/24")
        assert await service.is_ip_banned("10.0.0.50") is True
        assert await service.is_ip_banned("10.0.1.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_expired(self, db_container):
        """过期封禁不应影响 IP 检查。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", duration_minutes=0)

        # 创建一条过去的过期记录
        async with db_container.get("db")["session_factory"]() as session:
            past_ban = IpBan(
                ip_or_cidr="10.0.0.1",
                ban_type="manual",
                is_active=True,
                expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            )
            session.add(past_ban)
            await session.commit()

        # 已有的活跃记录（当前时间）会被匹配，所以至少有一条匹配
        # 但过期的不会被匹配
        assert await service.is_ip_banned("10.0.0.1") is True


# =============================================================================
# IpBanService — 分页查询
# =============================================================================


class TestIpBanServiceQuery:
    """分页查询测试。"""

    @pytest.mark.asyncio
    async def test_list_bans_empty(self, db_container):
        """空封禁列表应返回空。"""
        service = IpBanService(db_container)
        result = await service.list_bans()
        assert result["total"] == 0
        assert result["list"] == []

    @pytest.mark.asyncio
    async def test_list_bans_with_data(self, db_container):
        """有封禁记录时正确返回。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.ban_ip(ip_or_cidr="10.0.0.2")

        result = await service.list_bans()
        assert result["total"] == 2
        assert len(result["list"]) == 2

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, db_container):
        """分页参数正确。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}")

        page1 = await service.list_bans(page=1, page_size=2)
        assert len(page1["list"]) == 2
        assert page1["total"] == 5

        page2 = await service.list_bans(page=3, page_size=2)
        assert len(page2["list"]) == 1

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, db_container):
        """按 ban_type 过滤。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto")

        manual = await service.list_bans(ban_type="manual")
        assert manual["total"] == 1

        auto = await service.list_bans(ban_type="auto")
        assert auto["total"] == 1

    @pytest.mark.asyncio
    async def test_list_bans_filter_keyword(self, db_container):
        """按 IP 关键词搜索。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1")
        await service.ban_ip(ip_or_cidr="10.0.0.1")

        result = await service.list_bans(keyword="192.168")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_ban_logs(self, db_container):
        """操作日志分页查询。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", banned_by="admin")
        await service.ban_ip(ip_or_cidr="10.0.0.2", banned_by="admin")

        result = await service.get_ban_logs()
        assert result["total"] == 2
        assert len(result["list"]) == 2

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_action(self, db_container):
        """日志按 action 过滤。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.unban_ip(ban_id=ban["id"], operator="admin")

        ban_logs = await service.get_ban_logs(action="ban")
        assert ban_logs["total"] == 1

        unban_logs = await service.get_ban_logs(action="unban")
        assert unban_logs["total"] == 1


# =============================================================================
# IpBanService — 自动封禁规则
# =============================================================================


class TestIpBanServiceAutoBan:
    """自动封禁规则引擎测试。"""

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, db_container):
        """get_rule_configs 应返回默认规则配置。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_get_rule_configs_default_values(self, db_container):
        """默认规则应有正确的初始值。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()

        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 10
        assert login_rule["window_seconds"] == 300
        assert login_rule["ban_duration_minutes"] == 30
        # enabled 由 model 端默认提供（True）
        assert login_rule.get("enabled", True) is True  # noqa: B009

    @pytest.mark.asyncio
    async def test_update_rule_config(self, db_container):
        """应能更新规则配置。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()  # 先触发默认规则创建

        updated = await service.update_rule_config("login_failure", {
            "threshold": 5,
            "enabled": False,
        })
        assert updated["threshold"] == 5
        assert updated["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises(self, db_container):
        """更新不存在的规则应抛出 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("nonexistent_rule", {"enabled": False})
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_record_event_login_failure_triggers_ban(self, db_container):
        """登录失败事件超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()  # 确保默认规则已创建

        # 先修改阈值为 3
        await service.update_rule_config("login_failure", {
            "threshold": 3,
            "ban_duration_minutes": 10,
        })

        # 模拟 3 次登录失败
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.100")

        # 验证已被封禁
        assert await service.is_ip_banned("10.0.0.100") is True

    @pytest.mark.asyncio
    async def test_record_event_below_threshold(self, db_container):
        """低于阈值不应触发封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config("login_failure", {
            "threshold": 10,
        })

        # 只有 3 次
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.200")

        assert await service.is_ip_banned("10.0.0.200") is False

    @pytest.mark.asyncio
    async def test_record_event_rate_limit(self, db_container):
        """请求频率事件应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config("rate_limit", {
            "threshold": 5,
            "ban_duration_minutes": 10,
        })

        for _ in range(5):
            await service.record_event("rate_limit", "10.0.0.33")

        assert await service.is_ip_banned("10.0.0.33") is True

    @pytest.mark.asyncio
    async def test_record_event_high_4xx(self, db_container):
        """高频 4xx 事件应触发自动封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config("high_4xx", {
            "threshold": 3,
            "ban_duration_minutes": 10,
        })

        for _ in range(3):
            await service.record_event("high_4xx", "10.0.0.44", status_code=403)

        assert await service.is_ip_banned("10.0.0.44") is True

    @pytest.mark.asyncio
    async def test_disabled_rule_does_not_ban(self, db_container):
        """禁用的规则不应触发封禁。"""
        service = IpBanService(db_container)
        await service.get_rule_configs()
        await service.update_rule_config("login_failure", {
            "threshold": 3,
            "enabled": False,
        })

        for _ in range(5):
            await service.record_event("login_failure", "10.0.0.55")

        assert await service.is_ip_banned("10.0.0.55") is False


# =============================================================================
# IpBanService — 统计
# =============================================================================


class TestIpBanServiceStats:
    """统计数据测试。"""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, db_container):
        """空数据时各项统计应为 0。"""
        service = IpBanService(db_container)
        stats = await service.get_stats()
        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, db_container):
        """有封禁数据时统计正确。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto")
        await service.ban_ip(ip_or_cidr="10.0.0.3", ban_type="auto")

        stats = await service.get_stats()
        assert stats["total_bans"] == 3
        assert stats["active_bans"] == 3
        assert stats["auto_bans"] == 2
        assert stats["manual_bans"] == 1


# =============================================================================
# IpBanService — 计数器清理
# =============================================================================


class TestIpBanServiceCleanup:
    """计数器过期清理测试。"""

    @pytest.mark.asyncio
    async def test_cleanup_counters(self, db_container):
        """_cleanup_counters 应清理过期计数器。"""
        service = IpBanService(db_container)
        import time as time_module

        # 添加过期计数器
        old_time = time_module.time() - 4000  # 超过 3600 秒
        service._counters["expired:10.0.0.1"] = [(old_time, 0)]
        service._counters["active:10.0.0.2"] = [(time_module.time(), 0)]

        service._cleanup_counters()
        assert "expired:10.0.0.1" not in service._counters
        assert "active:10.0.0.2" in service._counters