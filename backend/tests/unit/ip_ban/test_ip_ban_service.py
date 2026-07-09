"""IP 封禁插件 — 核心服务测试。

风险：IpBanService 是安全关键组件，负责自动封禁规则引擎、CIDR 匹配、
封禁/解封操作。规则判断错误会导致安全漏洞或误封正常用户。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


class TestIPMatchesCIDR:
    """测试 CIDR 匹配工具函数。"""

    def test_ipv4_exact_match(self):
        """精确 IP 匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IP 在 CIDR 段内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IP 不在 CIDR 段内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_cidr_without_prefix(self):
        """不带前缀长度的 CIDR 应视为 /32。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1") is True

    def test_invalid_ip(self):
        """无效 IP 应返回 False 而非抛出异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr(self):
        """无效 CIDR 应返回 False 而非抛出异常。"""
        assert ip_matches_cidr("192.168.1.1", "invalid-cidr") is False

    def test_ipv6_match(self):
        """IPv6 地址匹配。"""
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_ipv6_in_subnet(self):
        """IPv6 地址在子网内。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True


class TestIpBanService:
    """测试 IpBanService 核心方法。"""

    @pytest.fixture
    def service(self, in_memory_db):
        """创建带有真实内存数据库的 IpBanService 实例。"""
        # 创建 mock container
        container = MagicMock()
        container.get.side_effect = lambda name: {
            "db": in_memory_db,
            "config": MagicMock(
                get=lambda key, default=None: default
            ),
        }.get(name)
        return IpBanService(container)

    @pytest.mark.asyncio
    async def test_ban_ip_permanent(self, service):
        """永久封禁应创建活跃记录且无过期时间。"""
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="恶意攻击",
            ban_type="manual",
            banned_by="admin",
        )
        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_ban_ip_temporary(self, service):
        """临时封禁应设置过期时间。"""
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            duration_minutes=30,
        )
        assert result["is_active"] is True
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_ip_duplicate(self, service):
        """重复封禁同一 IP 应返回已有记录并更新。"""
        result1 = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="首次封禁",
        )
        result2 = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="重复封禁",
            duration_minutes=60,
        )
        assert result2["id"] == result1["id"]
        assert result2["expires_at"] is not None  # 更新时间

    @pytest.mark.asyncio
    async def test_unban_ip(self, service):
        """解封操作应将 is_active 设为 False。"""
        ban_result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
        )
        unban_result = await service.unban_ip(
            ban_id=ban_result["id"], operator="admin"
        )
        assert unban_result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_ip_not_found(self, service):
        """解封不存在的记录应抛出 AppError。"""
        with pytest.raises(AppError, match="封禁记录不存在"):
            await service.unban_ip(ban_id=99999, operator="admin")

    @pytest.mark.asyncio
    async def test_batch_unban(self, service):
        """批量解封应返回实际解封数量。"""
        b1 = await service.ban_ip(ip_or_cidr="10.0.0.1")
        b2 = await service.ban_ip(ip_or_cidr="10.0.0.2")
        b3 = await service.ban_ip(ip_or_cidr="10.0.0.3")

        count = await service.batch_unban(
            ban_ids=[b1["id"], b2["id"], b3["id"]], operator="admin"
        )
        assert count == 3

    @pytest.mark.asyncio
    async def test_batch_unban_partial(self, service):
        """批量解封时，部分已解封的记录不应重复计数。"""
        b1 = await service.ban_ip(ip_or_cidr="10.0.0.1")
        b2 = await service.ban_ip(ip_or_cidr="10.0.0.2")

        await service.unban_ip(b1["id"], operator="admin")
        count = await service.batch_unban(
            ban_ids=[b1["id"], b2["id"]], operator="admin"
        )
        # b1 已解封，只解封 b2
        assert count == 1

    @pytest.mark.asyncio
    async def test_is_ip_banned_matched(self, service):
        """已封禁的 IP 应被检测到。"""
        await service.ban_ip(ip_or_cidr="192.168.1.1")
        assert await service.is_ip_banned("192.168.1.1") is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_not_matched(self, service):
        """未封禁的 IP 不应被检测到。"""
        await service.ban_ip(ip_or_cidr="192.168.1.1")
        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_cidr_match(self, service):
        """CIDR 段封禁应匹配段内所有 IP。"""
        await service.ban_ip(ip_or_cidr="192.168.1.0/24")
        assert await service.is_ip_banned("192.168.1.100") is True
        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, service):
        """获取活跃 IP 段列表。"""
        await service.ban_ip(ip_or_cidr="192.168.1.0/24")
        await service.ban_ip(ip_or_cidr="10.0.0.0/8")
        ranges = await service.get_active_ip_ranges()
        assert "192.168.1.0/24" in ranges
        assert "10.0.0.0/8" in ranges

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, service):
        """分页查询封禁列表。"""
        for i in range(5):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}")

        page1 = await service.list_bans(page=1, page_size=2)
        assert len(page1["list"]) == 2
        assert page1["total"] == 5
        assert page1["page"] == 1

        page2 = await service.list_bans(page=2, page_size=2)
        assert len(page2["list"]) == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, service):
        """按封禁类型筛选。"""
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto",
                             rule_id="test_rule", duration_minutes=30)

        manual = await service.list_bans(ban_type="manual")
        auto = await service.list_bans(ban_type="auto")
        assert len(manual["list"]) == 1
        assert len(auto["list"]) == 1

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_keyword(self, service):
        """按关键词搜索 IP/CIDR。"""
        await service.ban_ip(ip_or_cidr="192.168.1.1")
        await service.ban_ip(ip_or_cidr="10.0.0.1")

        result = await service.list_bans(keyword="192.168")
        assert len(result["list"]) == 1

    @pytest.mark.asyncio
    async def test_get_ban_logs(self, service):
        """封禁操作日志应记录每次操作。"""
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="test")
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="test")

        logs = await service.get_ban_logs(page=1, page_size=10)
        assert len(logs["list"]) == 2
        assert logs["total"] == 2

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, service):
        """按操作类型筛选日志。"""
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.unban_ip(ban_id=ban["id"], operator="admin")

        ban_logs = await service.get_ban_logs(action="ban")
        unban_logs = await service.get_ban_logs(action="unban")
        assert len(ban_logs["list"]) == 1
        assert len(unban_logs["list"]) == 1

    @pytest.mark.asyncio
    async def test_get_stats(self, service):
        """封禁统计应包含各项指标。"""
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto",
                             rule_id="rate_limit", duration_minutes=10)

        stats = await service.get_stats()
        assert stats["total_bans"] >= 2
        assert stats["manual_bans"] >= 1
        assert stats["auto_bans"] >= 1

    @pytest.mark.asyncio
    async def test_get_rule_configs_defaults(self, service):
        """首次获取规则配置应返回默认规则。"""
        rules = await service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_update_rule_config(self, service):
        """更新规则配置应生效。"""
        rules = await service.get_rule_configs()
        rule_id = rules[0]["id"]

        updated = await service.update_rule_config(rule_id, {
            "threshold": 20,
            "enabled": False,
        })
        assert updated["threshold"] == 20
        assert updated["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_rule_config_not_found(self, service):
        """更新不存在的规则应抛出 AppError。"""
        with pytest.raises(AppError, match="规则不存在"):
            await service.update_rule_config("non_existent_rule", {
                "threshold": 10,
            })

    @pytest.mark.asyncio
    async def test_record_event_login_failure(self, service):
        """记录登录失败事件应触发登录失败规则检查。"""
        for _ in range(15):
            await service.record_event("login_failure", "10.0.0.99")

        # 登录失败次数超过阈值（10次/300秒），应自动封禁
        is_banned = await service.is_ip_banned("10.0.0.99")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_rate_limit(self, service):
        """记录频率限制事件应触发频率限制规则检查。"""
        for _ in range(250):
            await service.record_event("rate_limit", "10.0.0.100")

        is_banned = await service.is_ip_banned("10.0.0.100")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_cleanup_counters(self, service):
        """清理过期计数器不应影响活跃计数器。"""
        import time

        # 添加一些过期条目
        service._counters["old:1.2.3.4"] = [(time.time() - 7200, 0)]
        service._counters["active:1.2.3.4"] = [(time.time() - 30, 0)]

        service._cleanup_counters()
        assert "old:1.2.3.4" not in service._counters
        assert "active:1.2.3.4" in service._counters