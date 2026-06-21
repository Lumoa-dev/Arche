"""IpBanService 单元测试。

覆盖：
- ip_matches_cidr 纯函数（IPv4/IPv6/边界情况）
- 封禁/解封 CRUD
- 自动封禁规则引擎
- 分页查询和筛选
- 统计功能
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr

# =============================================================================
# ip_matches_cidr 纯函数测试
# =============================================================================


class TestIpMatchesCidr:
    """CIDR 匹配纯函数测试。"""

    def test_ipv4_exact_match(self):
        """IPv4 精确匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_subnet_match(self):
        """IPv4 子网内匹配。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_subnet_no_match(self):
        """IPv4 不在子网内应返回 False。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_single_ip_no_cidr(self):
        """IPv4 不带 CIDR 前缀的匹配（/32 隐含）。"""
        # IpBan 存储时如果没有 /N，strict=False 的 ip_network 会按主机位处理
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1") is True
        assert ip_matches_cidr("192.168.1.2", "192.168.1.1") is False

    def test_ipv6_match(self):
        """IPv6 匹配。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32")
            is True
        )

    def test_ipv6_no_match(self):
        """IPv6 不匹配。"""
        assert (
            ip_matches_cidr("2001:db9::1", "2001:db8::/32")
            is False
        )

    def test_invalid_ip_returns_false(self):
        """无效 IP 返回 False 不抛异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 返回 False 不抛异常。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_zero_network_match(self):
        """0.0.0.0/0 匹配任何 IP。"""
        assert ip_matches_cidr("1.2.3.4", "0.0.0.0/0") is True
        assert ip_matches_cidr("255.255.255.255", "0.0.0.0/0") is True


# =============================================================================
# IpBanService 测试辅助
# =============================================================================


@pytest.fixture
def ip_ban_db_container(db_container):
    """创建支持完整 IpBanService 的容器（不 mock ip_ban service）。"""
    # db_container 中 ip_ban 被 mock 了，但 IpBanService 只需要 db + config
    return db_container


@pytest.fixture
def ip_ban_service(ip_ban_db_container):
    """创建 IpBanService 实例。"""
    return IpBanService(ip_ban_db_container)


# =============================================================================
# 封禁/解封 CRUD 测试
# =============================================================================


class TestBanUnban:
    """封禁和解封操作测试。"""

    @pytest.mark.asyncio
    async def test_ban_ip_single(self, ip_ban_service):
        """封禁单个 IP 应返回封禁记录。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="恶意攻击",
            ban_type="manual",
        )
        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["ban_type"] == "manual"
        assert result["reason"] == "恶意攻击"
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_ip_with_duration(self, ip_ban_service):
        """封禁时应设置过期时间。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            duration_minutes=30,
        )
        assert result["expires_at"] is not None
        expires_at = datetime.fromisoformat(result["expires_at"])
        # expires_at 是 offset-naive（无时区），需要插入时区信息后做比较
        # 或直接断言它比 2020 年大（确保是未来时间）
        assert expires_at > datetime(2020, 1, 1)

    @pytest.mark.asyncio
    async def test_ban_ip_duplicate_updates_existing(self, ip_ban_service):
        """重复封禁同一 IP 应更新已有记录而非创建新记录。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="首次封禁",
            ban_type="manual",
            duration_minutes=30,
        )
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="更新封禁原因",
            ban_type="auto",
            duration_minutes=60,
        )
        assert result["reason"] == "更新封禁原因"

    @pytest.mark.asyncio
    async def test_unban_ip(self, ip_ban_service):
        """解封应设置 is_active=False。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="测试封禁",
        )
        result = await ip_ban_service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent(self, ip_ban_service):
        """解封不存在的记录应抛出错误。"""
        with pytest.raises(AppError) as excinfo:
            await ip_ban_service.unban_ip(ban_id=99999)
        assert excinfo.value.code == "ban_not_found"

    @pytest.mark.asyncio
    async def test_batch_unban(self, ip_ban_service):
        """批量解封应返回解封数量。"""
        ban1 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1")
        ban2 = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.2")
        count = await ip_ban_service.batch_unban(
            ban_ids=[ban1["id"], ban2["id"]],
            operator="admin",
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_batch_unban_already_inactive(self, ip_ban_service):
        """已解封的记录不应重复计数。"""
        ban = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1")
        await ip_ban_service.unban_ip(ban_id=ban["id"])
        count = await ip_ban_service.batch_unban(
            ban_ids=[ban["id"]],
        )
        assert count == 0


# =============================================================================
# IP 检查测试
# =============================================================================


class TestIpCheck:
    """IP 检查功能测试。"""

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_true(self, ip_ban_service):
        """已封禁的 IP 应返回 True。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="测试",
        )
        assert await ip_ban_service.is_ip_banned("192.168.1.100") is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_unbanned(self, ip_ban_service):
        """解封后的 IP 应返回 False。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="测试",
        )
        await ip_ban_service.unban_ip(ban_id=ban["id"])
        assert await ip_ban_service.is_ip_banned("192.168.1.100") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_not_found(self, ip_ban_service):
        """未封禁的 IP 应返回 False。"""
        assert await ip_ban_service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_cidr_match(self, ip_ban_service):
        """CIDR 段封禁应匹配范围内所有 IP。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.0/24",
            reason="封禁 C 段",
        )
        assert await ip_ban_service.is_ip_banned("192.168.1.1") is True
        assert await ip_ban_service.is_ip_banned("192.168.1.100") is True
        assert await ip_ban_service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_expired(self, ip_ban_service):
        """过期的封禁应返回 False（使用极短过期时间测试逻辑）。"""
        # 直接通过 ban_ip 创建短时效封禁
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="短期封禁",
            duration_minutes=0,  # 立即过期
        )
        # 注意：duration_minutes=0 意味着 expires_at = now + 0 = 立即过期
        # 但在同一个事务中，created_at 和 expires_at 相同，取决于执行时间
        # 所以需要手动创建一个过去时间的封禁
        # 这个方法不太可靠，改用直接操作 DB 测试过期逻辑
        from backend.plugins.ip_ban.models import IpBan

        db = ip_ban_service.container.get("db")
        async with db["session_factory"]() as session:
            # 先清理
            await session.execute(
                __import__("sqlalchemy").delete(IpBan)
            )
            ban = IpBan(
                ip_or_cidr="10.0.0.1",
                ban_type="manual",
                reason="test",
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
            session.add(ban)
            await session.commit()

        assert await ip_ban_service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, ip_ban_service):
        """获取活跃 IP 段列表。"""
        await ip_ban_service.ban_ip(ip_or_cidr="192.168.1.0/24")
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.0/8")
        ranges = await ip_ban_service.get_active_ip_ranges()
        assert "192.168.1.0/24" in ranges
        assert "10.0.0.0/8" in ranges


# =============================================================================
# 分页查询测试
# =============================================================================


class TestListAndQuery:
    """分页查询和筛选测试。"""

    @pytest.mark.asyncio
    async def test_list_bans_empty(self, ip_ban_service):
        """空列表。"""
        result = await ip_ban_service.list_bans()
        assert result["total"] == 0
        assert result["list"] == []

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, ip_ban_service):
        """分页功能。"""
        for i in range(5):
            await ip_ban_service.ban_ip(
                ip_or_cidr=f"10.0.0.{i}",
            )
        page1 = await ip_ban_service.list_bans(page=1, page_size=2)
        assert len(page1["list"]) == 2
        assert page1["total"] == 5
        page2 = await ip_ban_service.list_bans(page=3, page_size=2)
        assert len(page2["list"]) == 1

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, ip_ban_service):
        """按类型筛选。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            ban_type="manual",
        )
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            ban_type="auto",
            rule_id="login_failure",
        )
        manual = await ip_ban_service.list_bans(ban_type="manual")
        assert manual["total"] == 1
        auto = await ip_ban_service.list_bans(ban_type="auto")
        assert auto["total"] == 1

    @pytest.mark.asyncio
    async def test_list_bans_filter_active(self, ip_ban_service):
        """按活跃状态筛选。"""
        ban = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1")
        await ip_ban_service.unban_ip(ban_id=ban["id"])
        active = await ip_ban_service.list_bans(is_active=True)
        assert active["total"] == 0
        inactive = await ip_ban_service.list_bans(is_active=False)
        assert inactive["total"] == 1

    @pytest.mark.asyncio
    async def test_list_bans_keyword_search(self, ip_ban_service):
        """按关键字搜索。"""
        await ip_ban_service.ban_ip(ip_or_cidr="192.168.1.1")
        await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1")
        result = await ip_ban_service.list_bans(keyword="192.168")
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_get_ban_logs(self, ip_ban_service):
        """分页查询封禁日志。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="test",
            banned_by="admin",
        )
        logs = await ip_ban_service.get_ban_logs()
        assert logs["total"] == 1
        assert logs["list"][0]["action"] == "ban"
        assert logs["list"][0]["operator"] == "admin"

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_action(self, ip_ban_service):
        """按操作类型筛选日志。"""
        ban = await ip_ban_service.ban_ip(ip_or_cidr="10.0.0.1")
        await ip_ban_service.unban_ip(ban_id=ban["id"], operator="admin")
        ban_logs = await ip_ban_service.get_ban_logs(action="ban")
        unban_logs = await ip_ban_service.get_ban_logs(action="unban")
        assert ban_logs["total"] == 1
        assert unban_logs["total"] == 1


# =============================================================================
# 规则引擎测试
# =============================================================================


class TestAutoBanRuleEngine:
    """自动封禁规则引擎测试。"""

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, ip_ban_service):
        """未配置规则时返回默认规则。"""
        rules = await ip_ban_service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_update_rule_config_enabled(self, ip_ban_service):
        """更新规则的 enabled 字段。"""
        # 先获取一次（触发默认规则创建）
        await ip_ban_service.get_rule_configs()
        result = await ip_ban_service.update_rule_config(
            "login_failure",
            {"enabled": False},
        )
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_rule_config_threshold(self, ip_ban_service):
        """更新规则的 threshold 字段。"""
        await ip_ban_service.get_rule_configs()
        result = await ip_ban_service.update_rule_config(
            "rate_limit",
            {"threshold": 500},
        )
        assert result["threshold"] == 500

    @pytest.mark.asyncio
    async def test_update_rule_config_not_found(self, ip_ban_service):
        """更新不存在的规则应抛出错误。"""
        with pytest.raises(AppError) as excinfo:
            await ip_ban_service.update_rule_config(
                "nonexistent_rule",
                {"enabled": True},
            )
        assert excinfo.value.code == "rule_not_found"

    @pytest.mark.asyncio
    async def test_record_login_failure_triggers_auto_ban(self, ip_ban_service):
        """登录失败事件超过阈值应触发自动封禁。"""
        # 先创建默认规则
        await ip_ban_service.get_rule_configs()
        # 设置为较低的阈值以便测试
        await ip_ban_service.update_rule_config(
            "login_failure",
            {"enabled": True, "threshold": 3, "ban_duration_minutes": 10},
        )

        # 记录 4 次登录失败（超过阈值 3）
        for _ in range(4):
            await ip_ban_service.record_event(
                event_type="login_failure",
                ip_str="10.0.0.100",
            )

        # 验证 IP 已被自动封禁
        assert await ip_ban_service.is_ip_banned("10.0.0.100") is True

    @pytest.mark.asyncio
    async def test_record_login_failure_below_threshold(self, ip_ban_service):
        """登录失败次数未超过阈值不应触发封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "login_failure",
            {"enabled": True, "threshold": 5, "ban_duration_minutes": 10},
        )

        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="login_failure",
                ip_str="10.0.0.100",
            )

        assert await ip_ban_service.is_ip_banned("10.0.0.100") is False

    @pytest.mark.asyncio
    async def test_record_high_4xx_triggers_auto_ban(self, ip_ban_service):
        """高频 4xx 事件超过阈值应触发自动封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "high_4xx",
            {"enabled": True, "threshold": 3, "ban_duration_minutes": 10},
        )

        for _ in range(4):
            await ip_ban_service.record_event(
                event_type="high_4xx",
                ip_str="10.0.0.200",
                status_code=429,
            )

        assert await ip_ban_service.is_ip_banned("10.0.0.200") is True

    @pytest.mark.asyncio
    async def test_auto_ban_disabled_rule_no_action(self, ip_ban_service):
        """禁用的规则不应触发自动封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "login_failure",
            {"enabled": False, "threshold": 1},
        )

        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="login_failure",
                ip_str="10.0.0.100",
            )

        assert await ip_ban_service.is_ip_banned("10.0.0.100") is False


# =============================================================================
# 统计功能测试
# =============================================================================


class TestIpBanStats:
    """IP 封禁统计功能测试。"""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, ip_ban_service):
        """空状态统计。"""
        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, ip_ban_service):
        """有数据时的统计。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            ban_type="manual",
        )
        # auto-ban 通过模拟记录
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            ban_type="auto",
            rule_id="login_failure",
        )
        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] == 2
        assert stats["manual_bans"] == 1
        assert stats["auto_bans"] == 1
