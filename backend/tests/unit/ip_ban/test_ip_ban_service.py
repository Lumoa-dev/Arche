"""IpBanService 行为测试。

测试原则：
- 覆盖核心 CRUD、自动封禁规则引擎、IP/CIDR 匹配
- 使用内存数据库做真实 DB 交互
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.models import IpBan, IpBanLog
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# IP/CIDR 匹配
# =============================================================================


class TestIpMatchesCidr:
    """测试 IP/CIDR 段匹配逻辑。"""

    @pytest.mark.asyncio
    async def test_ipv4_exact_match(self):
        """精确 IPv4 地址应匹配自身。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1")

    @pytest.mark.asyncio
    async def test_ipv4_in_cidr_range(self):
        """IPv4 在 CIDR 段内应匹配。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24")

    @pytest.mark.asyncio
    async def test_ipv4_outside_cidr_range(self):
        """IPv4 在 CIDR 段外应不匹配。"""
        assert not ip_matches_cidr("10.0.0.1", "192.168.1.0/24")

    @pytest.mark.asyncio
    async def test_ipv6_in_cidr(self):
        """IPv6 在 CIDR 段内应匹配。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32")

    @pytest.mark.asyncio
    async def test_invalid_ip_returns_false(self):
        """无效 IP 字符串应返回 False 而非抛异常。"""
        assert not ip_matches_cidr("not-an-ip", "192.168.1.0/24")

    @pytest.mark.asyncio
    async def test_invalid_cidr_returns_false(self):
        """无效 CIDR 字符串应返回 False。"""
        assert not ip_matches_cidr("192.168.1.1", "not-a-cidr")


# =============================================================================
# 手动封禁管理
# =============================================================================


class TestBanIp:
    """测试手动封禁 IP。"""

    @pytest.mark.asyncio
    async def test_ban_ip_creates_ban_and_log(self, db_container):
        """封禁 IP 应创建封禁记录和操作日志。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="恶意攻击",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=30,
        )

        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["expires_at"] is not None

        # 验证日志已写入
        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            logs = (await session.execute(
                __import__("sqlalchemy").select(IpBanLog).where(IpBanLog.ip_or_cidr == "192.168.1.100")
            )).scalars().all()
            assert len(logs) == 1
            assert logs[0].action == "ban"

    @pytest.mark.asyncio
    async def test_ban_ip_permanent(self, db_container):
        """不传 duration_minutes 时应为永久封禁（expires_at=None）。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="永久封禁",
        )
        assert result["expires_at"] is None
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_ip_existing_active_returns_existing(self, db_container):
        """已存在的活跃封禁记录应返回已有记录，不重复创建。"""
        service = IpBanService(db_container)
        result1 = await service.ban_ip(ip_or_cidr="192.168.1.1", reason="首次")
        result2 = await service.ban_ip(ip_or_cidr="192.168.1.1", reason="重复")

        assert result1["id"] == result2["id"]  # 同一 ID

    @pytest.mark.asyncio
    async def test_ban_ip_updates_existing_expiry(self, db_container):
        """已存在活跃封禁时，更新过期时间。"""
        service = IpBanService(db_container)
        result1 = await service.ban_ip(ip_or_cidr="192.168.1.1", duration_minutes=10)
        result2 = await service.ban_ip(ip_or_cidr="192.168.1.1", duration_minutes=60)

        assert result2["id"] == result1["id"]
        # 第二次返回的 expires_at 应 > 第一次
        assert result2["expires_at"] != result1["expires_at"]


class TestUnbanIp:
    """测试解封 IP。"""

    @pytest.mark.asyncio
    async def test_unban_ip_deactivates_ban(self, db_container):
        """解封应将 is_active 设为 False。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="192.168.1.100", reason="测试")
        result = await service.unban_ip(ban_id=ban["id"], operator="admin")

        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_ip_creates_unban_log(self, db_container):
        """解封应创建解封操作日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="192.168.1.100", reason="测试")
        await service.unban_ip(ban_id=ban["id"], operator="admin")

        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            logs = (await session.execute(
                __import__("sqlalchemy").select(IpBanLog).where(IpBanLog.ip_or_cidr == "192.168.1.100")
            )).scalars().all()
            unban_logs = [l for l in logs if l.action == "unban"]
            assert len(unban_logs) == 1

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, db_container):
        """解封不存在的记录应抛出 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as exc:
            await service.unban_ip(ban_id=9999, operator="admin")
        assert exc.value.status_code == 404


class TestBatchUnban:
    """测试批量解封。"""

    @pytest.mark.asyncio
    async def test_batch_unban_multiple(self, db_container):
        """批量解封应同时处理多个封禁记录。"""
        service = IpBanService(db_container)
        b1 = await service.ban_ip(ip_or_cidr="10.0.0.1")
        b2 = await service.ban_ip(ip_or_cidr="10.0.0.2")
        b3 = await service.ban_ip(ip_or_cidr="10.0.0.3")
        _ = b3  # 第三个不解封

        count = await service.batch_unban([b1["id"], b2["id"]], operator="admin")
        assert count == 2

    @pytest.mark.asyncio
    async def test_batch_unban_already_inactive(self, db_container):
        """已解封的记录不应计入返回数量。"""
        service = IpBanService(db_container)
        b1 = await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.unban_ip(b1["id"])
        count = await service.batch_unban([b1["id"]], operator="admin")
        assert count == 0


# =============================================================================
# 查询与检查
# =============================================================================


class TestListBans:
    """测试分页查询封禁列表。"""

    @pytest.mark.asyncio
    async def test_list_returns_all_active_bans(self, db_container):
        """list_bans 应返回所有封禁记录。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.ban_ip(ip_or_cidr="10.0.0.2")

        result = await service.list_bans(page=1, page_size=20)
        assert result["total"] >= 2
        assert len(result["list"]) >= 2

    @pytest.mark.asyncio
    async def test_list_filter_by_ban_type(self, db_container):
        """按 ban_type 过滤应只返回对应类型的记录。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto", reason="自动")

        result = await service.list_bans(ban_type="auto")
        assert all(b["ban_type"] == "auto" for b in result["list"])

    @pytest.mark.asyncio
    async def test_list_filter_by_keyword(self, db_container):
        """按关键字过滤应匹配 IP/CIDR 段。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1")
        await service.ban_ip(ip_or_cidr="10.0.0.1")

        result = await service.list_bans(keyword="192.168")
        assert all("192.168" in b["ip_or_cidr"] for b in result["list"])


class TestIsIpBanned:
    """测试 IP 是否被封禁的检查。"""

    @pytest.mark.asyncio
    async def test_banned_ip_returns_true(self, db_container):
        """被封禁的 IP 应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.100")
        assert await service.is_ip_banned("192.168.1.100") is True

    @pytest.mark.asyncio
    async def test_not_banned_ip_returns_false(self, db_container):
        """未被封禁的 IP 应返回 False。"""
        service = IpBanService(db_container)
        assert await service.is_ip_banned("8.8.8.8") is False

    @pytest.mark.asyncio
    async def test_unbanned_ip_returns_false(self, db_container):
        """解封后的 IP 应返回 False。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="192.168.1.100")
        await service.unban_ip(ban["id"])
        assert await service.is_ip_banned("192.168.1.100") is False

    @pytest.mark.asyncio
    async def test_expired_ban_returns_false(self, db_container):
        """已过期的封禁应返回 False。"""
        service = IpBanService(db_container)
        # 直接创建过期记录
        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            past = datetime.now(timezone.utc) - timedelta(hours=1)
            ban = IpBan(
                ip_or_cidr="10.0.0.1",
                ban_type="manual",
                is_active=True,
                expires_at=past,
            )
            session.add(ban)
            await session.commit()

        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_cidr_range_matches_sub_ip(self, db_container):
        """CIDR 段封禁应匹配段内任一 IP。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.0/24")
        assert await service.is_ip_banned("192.168.1.50") is True
        assert await service.is_ip_banned("192.168.2.1") is False


class TestGetBanLogs:
    """测试封禁日志查询。"""

    @pytest.mark.asyncio
    async def test_get_ban_logs_returns_logs(self, db_container):
        """get_ban_logs 应返回封禁操作日志。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")

        result = await service.get_ban_logs(page=1, page_size=20)
        assert result["total"] >= 1
        assert any(log["action"] == "ban" for log in result["list"])

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, db_container):
        """按 action 过滤应只返回对应类型的日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")
        await service.unban_ip(ban["id"], operator="admin")

        ban_logs = await service.get_ban_logs(action="ban")
        unban_logs = await service.get_ban_logs(action="unban")
        assert all(l["action"] == "unban" for l in unban_logs["list"])


# =============================================================================
# 自动封禁规则引擎
# =============================================================================


class TestAutoBanRules:
    """测试自动封禁规则引擎。"""

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, db_container):
        """未配置时应返回默认规则。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_record_event_login_failure_triggers_ban(self, db_container):
        """登录失败超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)

        # 模拟 10 次登录失败（默认阈值）
        for _ in range(10):
            await service.record_event("login_failure", "10.0.0.100")

        assert await service.is_ip_banned("10.0.0.100") is True

    @pytest.mark.asyncio
    async def test_record_event_high_4xx_triggers_ban(self, db_container):
        """4xx 高频超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)

        # 模拟 50 次 4xx（默认阈值）
        for _ in range(50):
            await service.record_event("high_4xx", "10.0.0.200", status_code=404)

        assert await service.is_ip_banned("10.0.0.200") is True

    @pytest.mark.asyncio
    async def test_record_event_rate_limit_triggers_ban(self, db_container):
        """请求频率超过阈值应触发自动封禁。"""
        service = IpBanService(db_container)

        # 模拟 200 次请求（默认阈值）
        for _ in range(200):
            await service.record_event("rate_limit", "10.0.0.30")

        assert await service.is_ip_banned("10.0.0.30") is True

    @pytest.mark.asyncio
    async def test_record_event_below_threshold_no_ban(self, db_container):
        """未达阈值不应触发封禁。"""
        service = IpBanService(db_container)
        for _ in range(5):
            await service.record_event("login_failure", "10.0.0.50")

        assert await service.is_ip_banned("10.0.0.50") is False

    @pytest.mark.asyncio
    async def test_update_rule_config_modifies_behavior(self, db_container):
        """修改规则配置后，新阈值生效。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")

        # 调高阈值到 20
        await service.update_rule_config("login_failure", {"threshold": 20})

        # 10 次登录失败不应再触发封禁
        for _ in range(10):
            await service.record_event("login_failure", "10.0.0.99")
        assert await service.is_ip_banned("10.0.0.99") is False

    @pytest.mark.asyncio
    async def test_update_rule_config_disabled_rule_no_ban(self, db_container):
        """禁用规则后不应触发封禁。"""
        service = IpBanService(db_container)
        # 先触发 get_rule_configs 确保默认规则已写入 DB
        await service.get_rule_configs()
        await service.update_rule_config("login_failure", {"enabled": False})

        for _ in range(10):
            await service.record_event("login_failure", "10.0.0.88")
        assert await service.is_ip_banned("10.0.0.88") is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises_error(self, db_container):
        """更新不存在的规则应抛出 AppError。"""
        service = IpBanService(db_container)
        with pytest.raises(AppError) as exc:
            await service.update_rule_config("nonexistent_rule", {"enabled": False})
        assert exc.value.status_code == 404


# =============================================================================
# 统计
# =============================================================================


class TestGetStats:
    """测试封禁统计。"""

    @pytest.mark.asyncio
    async def test_get_stats_returns_counts(self, db_container):
        """get_stats 应返回各类统计计数。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto", reason="auto")

        stats = await service.get_stats()
        assert stats["total_bans"] >= 2
        assert stats["active_bans"] >= 2
        assert stats["manual_bans"] >= 1
        assert stats["auto_bans"] >= 1