"""IpBanService 业务逻辑测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


class TestIPMatchCIDR:
    """测试 IP 与 CIDR 匹配。"""

    def test_ipv4_exact_match(self):
        """IPv4 精确匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IPv4 在子网内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IPv4 不在子网内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_invalid_ip(self):
        """无效 IP 返回 False。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr(self):
        """无效 CIDR 返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_cidr_any(self):
        """0.0.0.0/0 匹配所有 IPv4。"""
        assert ip_matches_cidr("1.2.3.4", "0.0.0.0/0") is True

    def test_empty_strings(self):
        """空字符串返回 False。"""
        assert ip_matches_cidr("", "") is False


class TestIpBanService:
    """测试 IpBanService 核心逻辑。"""

    @pytest.mark.asyncio
    async def test_ban_ip_creates_new_ban(self, db_container):
        """封禁新 IP 应创建记录。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="test ban",
            ban_type="manual",
            banned_by="admin",
        )
        assert result["ip_or_cidr"] == "10.0.0.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_ip_existing_returns_existing(self, db_container):
        """重复封禁同一 IP 应返回已有记录。"""
        service = IpBanService(db_container)
        result1 = await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="first ban",
            ban_type="manual",
            banned_by="admin",
        )
        result2 = await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="second ban",
            ban_type="manual",
            banned_by="admin",
        )
        # 两条记录应指向同一个 ID（更新了已有记录）
        assert result1["id"] == result2["id"]

    @pytest.mark.asyncio
    async def test_ban_ip_with_expiry(self, db_container):
        """封禁带过期时间应正确设置。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.3",
            reason="temporary ban",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=60,
        )
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_ip_permanent(self, db_container):
        """永久封禁 expires_at 为 None。"""
        service = IpBanService(db_container)
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.4",
            reason="permanent ban",
            ban_type="manual",
            banned_by="admin",
        )
        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_unban_ip(self, db_container):
        """解封应标记为不活跃。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="10.0.0.5",
            reason="to be unbanned",
            ban_type="manual",
            banned_by="admin",
        )
        result = await service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent(self, db_container):
        """解封不存在的记录应抛出异常。"""
        service = IpBanService(db_container)
        with pytest.raises(Exception) as excinfo:
            await service.unban_ip(ban_id=99999, operator="admin")
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_unban(self, db_container):
        """批量解封应返回解封数量。"""
        service = IpBanService(db_container)
        ban1 = await service.ban_ip(
            ip_or_cidr="10.0.0.6", reason="ban1", ban_type="manual", banned_by="admin"
        )
        ban2 = await service.ban_ip(
            ip_or_cidr="10.0.0.7", reason="ban2", ban_type="manual", banned_by="admin"
        )
        count = await service.batch_unban(
            ban_ids=[ban1["id"], ban2["id"]], operator="admin"
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_batch_unban_partial(self, db_container):
        """批量解封时，不存在的记录应跳过。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(
            ip_or_cidr="10.0.0.8", reason="ban", ban_type="manual", banned_by="admin"
        )
        count = await service.batch_unban(
            ban_ids=[ban["id"], 99999], operator="admin"
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_stats(self, db_container):
        """获取封禁统计应返回正确数字。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.9", reason="stats1", ban_type="manual", banned_by="admin"
        )
        await service.ban_ip(
            ip_or_cidr="10.0.0.10", reason="stats2", ban_type="auto", banned_by="admin"
        )
        stats = await service.get_stats()
        assert stats["total_bans"] == 2
        assert stats["manual_bans"] == 1
        assert stats["auto_bans"] == 1

    @pytest.mark.asyncio
    async def test_is_ip_banned(self, db_container):
        """检查 IP 是否被封禁。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.11", reason="test", ban_type="manual", banned_by="admin"
        )
        is_banned = await service.is_ip_banned("10.0.0.11")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_not_found(self, db_container):
        """未封禁的 IP 应返回 False。"""
        service = IpBanService(db_container)
        is_banned = await service.is_ip_banned("192.168.1.1")
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, db_container):
        """获取活跃 IP 范围列表。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.0/24", reason="range", ban_type="manual", banned_by="admin"
        )
        ranges = await service.get_active_ip_ranges()
        assert "10.0.0.0/24" in ranges

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, db_container):
        """分页查询封禁列表。"""
        service = IpBanService(db_container)
        for i in range(5):
            await service.ban_ip(
                ip_or_cidr=f"10.0.0.{100 + i}",
                reason=f"page-test-{i}",
                ban_type="manual",
                banned_by="admin",
            )
        result = await service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    @pytest.mark.asyncio
    async def test_list_bans_with_keyword(self, db_container):
        """按关键词搜索封禁列表。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.50", reason="special", ban_type="manual", banned_by="admin"
        )
        await service.ban_ip(
            ip_or_cidr="10.0.0.51", reason="other", ban_type="manual", banned_by="admin"
        )
        result = await service.list_bans(keyword="50")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "10.0.0.50"

    @pytest.mark.asyncio
    async def test_get_ban_logs(self, db_container):
        """获取封禁操作日志。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.20", reason="log-test", ban_type="manual", banned_by="admin"
        )
        logs = await service.get_ban_logs()
        assert logs["total"] >= 1
        assert logs["list"][0]["action"] == "ban"

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, db_container):
        """获取规则配置应返回默认规则。"""
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
        # 先确保规则存在
        await service.get_rule_configs()
        result = await service.update_rule_config(
            "login_failure", {"threshold": 20, "enabled": False}
        )
        assert result["threshold"] == 20
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule(self, db_container):
        """更新不存在的规则应抛出异常。"""
        service = IpBanService(db_container)
        with pytest.raises(Exception) as excinfo:
            await service.update_rule_config("nonexistent_rule", {"threshold": 10})
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_ban_logs_with_action_filter(self, db_container):
        """按操作类型过滤日志。"""
        service = IpBanService(db_container)
        await service.ban_ip(
            ip_or_cidr="10.0.0.30", reason="filter-test", ban_type="manual", banned_by="admin"
        )
        ban_logs = await service.get_ban_logs(action="ban")
        assert ban_logs["total"] >= 1
        unban_logs = await service.get_ban_logs(action="unban")
        assert unban_logs["total"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_counters(self, db_container):
        """清理过期计数器。"""
        service = IpBanService(db_container)
        # 添加一些过期计数器
        import time
        service._counters["old_key"] = [(time.time() - 7200, 200)]
        service._cleanup_counters()
        assert "old_key" not in service._counters