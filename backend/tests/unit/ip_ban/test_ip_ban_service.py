"""IP 封禁服务层的单元测试。

测试 IpBanService 的 CRUD、自动封禁规则引擎、统计等功能。
所有测试使用 in_memory_db 或 db_container 进行真实数据库交互。
"""

from __future__ import annotations

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService


# =============================================================================
# 封禁/解封操作
# =============================================================================


class TestBanOperations:
    """测试手动封禁和解封操作。"""

    @pytest.mark.asyncio
    async def test_ban_ip_creates_ban_record(self, db_container):
        """封禁 IP 应创建封禁记录。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="恶意攻击",
            ban_type="manual",
            banned_by="admin",
        )

        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["ban_type"] == "manual"
        assert result["reason"] == "恶意攻击"
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_ip_with_duration(self, db_container):
        """带过期时间的封禁应正确设置 expires_at。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            duration_minutes=30,
        )

        assert result["is_active"] is True
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_ip_updates_existing(self, db_container):
        """重复封禁同一 IP 应更新已有记录。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="首次封禁",
        )
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="更新原因",
            duration_minutes=60,
        )

        assert result["reason"] == "更新原因"
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_unban_ip_deactivates_ban(self, db_container):
        """解封应将 is_active 设为 False。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
        )

        result = await service.unban_ip(ban["id"], operator="admin")

        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, db_container):
        """解封不存在的记录应抛出错误。"""
        service = IpBanService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(99999)

        assert excinfo.value.code == "ban_not_found"

    @pytest.mark.asyncio
    async def test_batch_unban(self, db_container):
        """批量解封应正确工作。"""
        service = IpBanService(db_container)
        ban1 = await service.ban_ip(ip_or_cidr="10.0.0.1")
        ban2 = await service.ban_ip(ip_or_cidr="10.0.0.2")
        ban3 = await service.ban_ip(ip_or_cidr="10.0.0.3")

        count = await service.batch_unban(
            [ban1["id"], ban2["id"]], operator="admin"
        )

        assert count == 2

        # 验证剩余封禁仍活跃
        list_result = await service.list_bans(is_active=True)
        assert list_result["total"] == 1  # 只剩 ban3

    @pytest.mark.asyncio
    async def test_batch_unban_skips_inactive(self, db_container):
        """批量解封应跳过已不活跃的记录。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.unban_ip(ban["id"])

        count = await service.batch_unban([ban["id"]])
        assert count == 0


# =============================================================================
# 查询/列表
# =============================================================================


class TestListBans:
    """测试封禁列表查询。"""

    @pytest.mark.asyncio
    async def test_list_bans_empty(self, db_container):
        """空列表返回空结果。"""
        service = IpBanService(db_container)
        result = await service.list_bans()

        assert result["total"] == 0
        assert result["list"] == []

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, db_container):
        """分页查询正确工作。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}")

        page1 = await service.list_bans(page=1, page_size=2)
        assert page1["total"] == 5
        assert len(page1["list"]) == 2

        page2 = await service.list_bans(page=2, page_size=2)
        assert len(page2["list"]) == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, db_container):
        """ban_type 筛选正确。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1")  # manual（默认）
        # 模拟自动封禁
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto")

        manual = await service.list_bans(ban_type="manual")
        auto = await service.list_bans(ban_type="auto")

        assert manual["total"] == 1
        assert auto["total"] == 1

    @pytest.mark.asyncio
    async def test_list_bans_keyword_search(self, db_container):
        """关键词搜索正确。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1")
        await service.ban_ip(ip_or_cidr="10.0.0.1")

        result = await service.list_bans(keyword="192.168")
        assert result["total"] == 1


# =============================================================================
# 自动封禁规则引擎
# =============================================================================


class TestAutoBanRules:
    """测试自动封禁规则引擎。"""

    @pytest.mark.asyncio
    async def test_get_rule_configs_has_defaults(self, db_container):
        """获取规则配置应包含默认规则。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()

        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_update_rule_config(self, db_container):
        """更新规则配置应生效。"""
        service = IpBanService(db_container)
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")

        updated = await service.update_rule_config(
            "login_failure",
            {"threshold": 5, "enabled": False},
        )

        assert updated["threshold"] == 5
        assert updated["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises_error(self, db_container):
        """更新不存在的规则应抛出错误。"""
        service = IpBanService(db_container)

        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("nonexistent_rule", {"threshold": 5})

        assert excinfo.value.code == "rule_not_found"

    @pytest.mark.asyncio
    async def test_record_event_can_trigger_auto_ban(self, db_container):
        """记录事件达到阈值应触发自动封禁。"""
        service = IpBanService(db_container)

        # 先通过 get_rule_configs 确保默认规则存在于 DB
        await service.get_rule_configs()

        # 将 login_failure 阈值调低以方便测试
        await service.update_rule_config(
            "login_failure",
            {"threshold": 3, "ban_duration_minutes": 10},
        )

        # 记录 3 次登录失败事件
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.99")

        # 验证该 IP 被自动封禁
        is_banned = await service.is_ip_banned("10.0.0.99")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_auto_ban_respects_disabled_rule(self, db_container):
        """禁用的规则不应触发自动封禁。"""
        service = IpBanService(db_container)

        # 先通过 get_rule_configs 确保默认规则存在于 DB
        await service.get_rule_configs()

        # 禁用 login_failure 规则
        await service.update_rule_config("login_failure", {"enabled": False})

        # 记录多次登录失败事件
        for _ in range(20):
            await service.record_event("login_failure", "10.0.0.99")

        is_banned = await service.is_ip_banned("10.0.0.99")
        assert is_banned is False


# =============================================================================
# IP 检查
# =============================================================================


class TestIpCheck:
    """测试 IP 封禁检查。"""

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_true_for_banned_ip(self, db_container):
        """被封禁的 IP 应返回 True。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.1.1")

        assert await service.is_ip_banned("192.168.1.1") is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_for_unknown(self, db_container):
        """未被封禁的 IP 应返回 False。"""
        service = IpBanService(db_container)

        assert await service.is_ip_banned("192.168.1.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_matches_cidr(self, db_container):
        """IP 应匹配 CIDR 范围内的封禁。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="192.168.0.0/16")

        assert await service.is_ip_banned("192.168.1.1") is True
        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_ignores_expired(self, db_container):
        """已过期的封禁不应被匹配。"""
        service = IpBanService(db_container)

        # 创建一个已过期的封禁（duration_minutes=0 表示永久）
        # 我们直接通过 unban 来模拟过期
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.unban_ip(ban["id"])

        assert await service.is_ip_banned("10.0.0.1") is False


# =============================================================================
# 封禁日志
# =============================================================================


class TestBanLogs:
    """测试封禁操作日志。"""

    @pytest.mark.asyncio
    async def test_ban_creates_log_entry(self, db_container):
        """封禁操作应创建日志。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            banned_by="admin",
        )

        logs = await service.get_ban_logs()
        assert logs["total"] == 1
        assert logs["list"][0]["action"] == "ban"
        assert logs["list"][0]["operator"] == "admin"

    @pytest.mark.asyncio
    async def test_unban_creates_log_entry(self, db_container):
        """解封操作应创建日志。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")

        await service.unban_ip(ban["id"], operator="admin")

        logs = await service.get_ban_logs()
        # 封禁和解封各一条
        assert logs["total"] == 2

    @pytest.mark.asyncio
    async def test_auto_ban_creates_log(self, db_container):
        """自动封禁也应创建日志。"""
        service = IpBanService(db_container)
        # 先通过 get_rule_configs 确保默认规则存在于 DB
        await service.get_rule_configs()
        await service.update_rule_config("login_failure", {"threshold": 2})

        for _ in range(2):
            await service.record_event("login_failure", "10.0.0.99")

        logs = await service.get_ban_logs()
        assert logs["total"] >= 1


# =============================================================================
# 封禁统计
# =============================================================================


class TestBanStats:
    """测试封禁统计功能。"""

    @pytest.mark.asyncio
    async def test_get_stats_returns_zero_when_empty(self, db_container):
        """空数据库返回全零统计。"""
        service = IpBanService(db_container)
        stats = await service.get_stats()

        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0
        assert stats["today_bans"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_counts_correctly(self, db_container):
        """统计应正确分类。"""
        service = IpBanService(db_container)

        # 手动封禁
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        # 自动封禁
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto")

        stats = await service.get_stats()

        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 2
        assert stats["manual_bans"] == 1
        assert stats["auto_bans"] == 1


# =============================================================================
# 活跃 IP 范围
# =============================================================================


class TestActiveIpRanges:
    """测试获取活跃 IP 范围。"""

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, db_container):
        """获取活跃 IP 范围正确。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.ban_ip(ip_or_cidr="192.168.0.0/16")

        ranges = await service.get_active_ip_ranges()
        assert len(ranges) == 2
        assert "10.0.0.1" in ranges
        assert "192.168.0.0/16" in ranges