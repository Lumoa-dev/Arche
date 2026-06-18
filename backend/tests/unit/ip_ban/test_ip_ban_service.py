"""IP 封禁插件 —— 服务层单元测试。

使用真实内存数据库测试 IpBanService 的 CRUD、规则引擎和统计功能。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.models import IpBan, IpBanLog
from backend.plugins.ip_ban.services import IpBanService


@pytest.fixture
def ip_ban_service(db_container):
    """使用 db_container 的 IpBanService 实例。"""
    return IpBanService(db_container)


# =============================================================================
# 封禁 CRUD
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceCRUD:
    async def test_ban_ip_creates_record(self, ip_ban_service):
        """手动封禁创建记录并写入日志。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="恶意请求",
            ban_type="manual",
            banned_by="admin",
        )
        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["reason"] == "恶意请求"
        assert result["banned_by"] == "admin"
        assert result["expires_at"] is None  # 永久封禁
        assert "id" in result

    async def test_ban_ip_with_duration(self, ip_ban_service):
        """带时效的封禁。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            duration_minutes=30,
        )
        assert result["expires_at"] is not None

        expires = datetime.fromisoformat(result["expires_at"])
        now = datetime.now()
        # SQLite 存储时可能丢失时区信息，统一用 naive 比较
        if expires.tzinfo is not None:
            from datetime import timezone
            expires = expires.replace(tzinfo=None)
        assert expires > now
        # 30 分钟 ± 5 秒误差
        diff = (expires - now).total_seconds()
        assert 25 * 60 <= diff <= 35 * 60

    async def test_ban_ip_duplicate_updates(self, ip_ban_service):
        """重复封禁同一 IP 应更新而非新建。"""
        r1 = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1", reason="首次", duration_minutes=10,
        )
        r2 = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1", reason="更新理由", duration_minutes=60,
        )
        assert r1["id"] == r2["id"]
        assert r2["reason"] == "更新理由"

    async def test_ban_ip_cidr_block(self, ip_ban_service):
        """封禁 CIDR 段。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.0/24",
            reason="封禁整段",
        )
        assert result["ip_or_cidr"] == "10.0.0.0/24"

    async def test_is_ip_banned_exact_match(self, ip_ban_service):
        """精确 IP 封禁应被检测到。"""
        await ip_ban_service.ban_ip(ip_or_cidr="192.168.1.1")
        assert await ip_ban_service.is_ip_banned("192.168.1.1") is True

    async def test_is_ip_banned_cidr_match(self, ip_ban_service):
        """CIDR 段封禁应匹配段内 IP。"""
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.0/24")
        assert await ip_ban_service.is_ip_banned("10.0.0.50") is True
        assert await ip_ban_service.is_ip_banned("10.0.1.1") is False

    async def test_is_ip_banned_not_banned(self, ip_ban_service):
        """未封禁的 IP 应返回 False。"""
        assert await ip_ban_service.is_ip_banned("1.2.3.4") is False

    async def test_is_ip_banned_expired(self, ip_ban_service):
        """过期封禁不应被匹配。"""
        # 创建一个已过期的封禁
        session_factory = ip_ban_service.session_factory
        async with session_factory() as session:
            ban = IpBan(
                ip_or_cidr="10.0.0.1",
                ban_type="auto",
                reason="已过期",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            session.add(ban)
            await session.commit()

        assert await ip_ban_service.is_ip_banned("10.0.0.1") is False

    async def test_unban_ip(self, ip_ban_service):
        """解封使记录变为非活跃。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1", banned_by="admin",
        )
        ban_id = result["id"]

        unbanned = await ip_ban_service.unban_ip(ban_id, operator="admin")
        assert unbanned["is_active"] is False

        # 确认不再被封禁
        assert await ip_ban_service.is_ip_banned("192.168.1.1") is False

    async def test_unban_ip_not_found(self, ip_ban_service):
        """解封不存在的记录应抛异常。"""
        with pytest.raises(AppError) as exc:
            await ip_ban_service.unban_ip(99999)
        assert exc.value.status_code == 404

    async def test_batch_unban(self, ip_ban_service):
        """批量解封。"""
        r1 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1")
        r2 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.2")
        r3 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.3")

        count = await ip_ban_service.batch_unban(
            [r1["id"], r2["id"], r3["id"]], operator="admin"
        )
        assert count == 3

        # 确认全部解封
        for ip in ["10.0.0.1", "10.0.0.2", "10.0.0.3"]:
            assert await ip_ban_service.is_ip_banned(ip) is False

    async def test_batch_unban_mixed(self, ip_ban_service):
        """混合已解封和未解封的记录。"""
        r1 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1")
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.2")

        # 先解封 r1
        await ip_ban_service.unban_ip(r1["id"])

        # 批量解封所有
        # 需要先查 ID
        session_factory = ip_ban_service.session_factory
        async with session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(select(IpBan))
            all_bans = result.scalars().all()

        ban_ids = [b.id for b in all_bans]
        count = await ip_ban_service.batch_unban(ban_ids)
        # 只有活跃的记录被解封（原来有 2 条，已解封 1 条，剩余 1 条）
        assert count == 1

    async def test_list_bans_pagination(self, ip_ban_service):
        """分页查询封禁列表。"""
        for i in range(5):
            await ip_ban_service.ban_ip(ip_or_cidr=f"10.0.0.{i}")

        page1 = await ip_ban_service.list_bans(page=1, page_size=2)
        assert len(page1["list"]) == 2
        assert page1["total"] == 5
        assert page1["page"] == 1
        assert page1["page_size"] == 2

        page2 = await ip_ban_service.list_bans(page=2, page_size=2)
        assert len(page2["list"]) == 2

    async def test_list_bans_filter_by_type(self, ip_ban_service):
        """按封禁类型过滤。"""
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto")

        result = await ip_ban_service.list_bans(ban_type="manual")
        assert len(result["list"]) == 1
        assert result["list"][0]["ban_type"] == "manual"

    async def test_list_bans_keyword_search(self, ip_ban_service):
        """按关键词搜索。"""
        await ip_ban_service.ban_ip(ip_or_cidr="192.168.1.1")
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1")

        result = await ip_ban_service.list_bans(keyword="192.168")
        assert len(result["list"]) == 1
        assert result["list"][0]["ip_or_cidr"] == "192.168.1.1"


# =============================================================================
# 封禁日志
# =============================================================================


@pytest.mark.asyncio
class TestIpBanLogs:
    async def test_get_ban_logs(self, ip_ban_service):
        """封禁操作产生日志。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1", banned_by="admin",
        )
        logs = await ip_ban_service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] == 1
        assert logs["list"][0]["action"] == "ban"
        assert logs["list"][0]["operator"] == "admin"

    async def test_get_ban_logs_filter_by_action(self, ip_ban_service):
        """按操作类型过滤日志。"""
        result = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1")
        await ip_ban_service.unban_ip(result["id"])

        ban_logs = await ip_ban_service.get_ban_logs(action="ban")
        assert ban_logs["total"] == 1

        unban_logs = await ip_ban_service.get_ban_logs(action="unban")
        assert unban_logs["total"] == 1


# =============================================================================
# 规则引擎
# =============================================================================


@pytest.mark.asyncio
class TestAutoBanRules:
    async def test_get_rule_configs_creates_defaults(self, ip_ban_service):
        """首次获取规则配置时自动创建默认规则。"""
        rules = await ip_ban_service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert rule_ids == {"login_failure", "high_4xx", "rate_limit", "geo_surge"}

    async def test_get_rule_configs_persistent(self, ip_ban_service):
        """规则配置在被创建后应持久化。"""
        await ip_ban_service.get_rule_configs()
        # 第二次获取不应重复创建
        rules = await ip_ban_service.get_rule_configs()
        assert len(rules) == 4

    async def test_update_rule_config(self, ip_ban_service):
        """更新规则配置。"""
        await ip_ban_service.get_rule_configs()  # 确保默认规则存在
        updated = await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 5, "enabled": False}
        )
        assert updated["threshold"] == 5
        assert updated["enabled"] is False

    async def test_update_rule_config_not_found(self, ip_ban_service):
        """更新不存在的规则应抛异常。"""
        with pytest.raises(AppError) as exc:
            await ip_ban_service.update_rule_config("nonexistent", {})
        assert exc.value.status_code == 404

    async def test_record_event_triggers_auto_ban(self, ip_ban_service):
        """登录失败超过阈值应触发自动封禁。"""
        # 设置低阈值以便测试
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 3, "enabled": True}
        )

        # 模拟 3 次登录失败
        for _ in range(3):
            await ip_ban_service.record_event("login_failure", "10.0.0.99")

        assert await ip_ban_service.is_ip_banned("10.0.0.99") is True

    async def test_record_event_below_threshold(self, ip_ban_service):
        """低于阈值的失败不应触发封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 5, "enabled": True}
        )

        # 模拟 3 次失败（未达阈值）
        for _ in range(3):
            await ip_ban_service.record_event("login_failure", "10.0.0.99")

        assert await ip_ban_service.is_ip_banned("10.0.0.99") is False

    async def test_disabled_rule_does_not_trigger(self, ip_ban_service):
        """禁用的规则不应触发封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 3, "enabled": False}
        )

        for _ in range(5):
            await ip_ban_service.record_event("login_failure", "10.0.0.99")

        assert await ip_ban_service.is_ip_banned("10.0.0.99") is False


# =============================================================================
# 统计
# =============================================================================


@pytest.mark.asyncio
class TestIpBanStats:
    async def test_get_stats_empty(self, ip_ban_service):
        """空数据库的统计。"""
        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0

    async def test_get_stats_with_data(self, ip_ban_service):
        """有封禁记录时的统计。"""
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto")

        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 2
        assert stats["manual_bans"] == 1
        assert stats["auto_bans"] == 1