"""IP 封禁服务单元测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import func, select

from backend.core.middleware import AppError
from backend.plugins.ip_ban.models import AutoBanRuleConfig, IpBan, IpBanLog
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr

# =============================================================================
# ip_matches_cidr 函数测试（纯单元测试，无需数据库）
# =============================================================================


class TestIpMatchesCidr:
    """ip_matches_cidr 函数测试。"""

    def test_exact_match_ipv4(self):
        """IPv4 精确匹配（/32）。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_cidr_match_ipv4(self):
        """IPv4 CIDR 段匹配。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_cidr_edge_match_ipv4(self):
        """IPv4 CIDR 段边界匹配。"""
        assert ip_matches_cidr("192.168.1.0", "192.168.1.0/24") is True
        assert ip_matches_cidr("192.168.1.255", "192.168.1.0/24") is True

    def test_no_match_ipv4(self):
        """IPv4 不匹配。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_exact_match_ipv6(self):
        """IPv6 精确匹配。"""
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_cidr_match_ipv6(self):
        """IPv6 CIDR 段匹配。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True

    def test_invalid_ip_returns_false(self):
        """无效 IP 字符串返回 False。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 字符串返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_empty_strings_returns_false(self):
        """空字符串输入返回 False。"""
        assert ip_matches_cidr("", "") is False

    def test_ipv4_mismatch_ipv6(self):
        """IPv4 地址与 IPv6 CIDR 不匹配。"""
        assert ip_matches_cidr("192.168.1.1", "2001:db8::/32") is False


# =============================================================================
# 辅助 fixture
# =============================================================================


@pytest.fixture
def ip_ban_service(db_container):
    """使用真实内存数据库的 IpBanService 实例。"""
    return IpBanService(db_container)


@pytest.fixture
async def seeded_bans(ip_ban_service):
    """预置若干封禁记录供查询测试使用。"""
    ban1 = await ip_ban_service.ban_ip(
        ip_or_cidr="192.168.1.1",
        reason="测试封禁1",
        ban_type="manual",
        banned_by="admin",
        duration_minutes=60,
    )
    ban2 = await ip_ban_service.ban_ip(
        ip_or_cidr="10.0.0.0/24",
        reason="测试封禁2",
        ban_type="auto",
        rule_id="login_failure",
        duration_minutes=30,
    )
    ban3 = await ip_ban_service.ban_ip(
        ip_or_cidr="172.16.0.1",
        reason="测试封禁3",
        ban_type="manual",
        banned_by="admin",
        duration_minutes=None,
    )
    return ban1, ban2, ban3


# =============================================================================
# 数据库集成测试（使用 db_container 真实内存数据库）
# =============================================================================


class TestBanIp:
    """ban_ip 方法测试。"""

    async def test_ban_ip_creates_ban_and_log(self, ip_ban_service, db_container):
        """封禁操作创建封禁记录和操作日志。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="恶意攻击",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=60,
        )
        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["reason"] == "恶意攻击"
        assert result["banned_by"] == "admin"
        assert result["is_active"] is True
        assert result["expires_at"] is not None

        # 验证日志也被创建
        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            logs_result = await session.execute(
                select(IpBanLog).where(IpBanLog.ip_or_cidr == "192.168.1.1")
            )
            logs = logs_result.scalars().all()
            assert len(logs) == 1
            assert logs[0].action == "ban"
            assert logs[0].operator == "admin"
            assert logs[0].ban_type == "manual"

    async def test_ban_ip_permanent(self, ip_ban_service):
        """永久封禁（duration_minutes 为 None）时 expires_at 为 None。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="永久封禁",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=None,
        )
        assert result["expires_at"] is None

    async def test_ban_ip_zero_duration_treated_as_permanent(self, ip_ban_service):
        """duration_minutes 为 0 时视为永久封禁。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="零时长",
            ban_type="manual",
            duration_minutes=0,
        )
        assert result["expires_at"] is None

    async def test_reban_existing_ip_updates_record(self, ip_ban_service):
        """重新封禁已存在的 IP 更新记录而非新建。"""
        ban1 = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="初次封禁",
            ban_type="manual",
            duration_minutes=30,
        )
        ban2 = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="再次封禁",
            ban_type="auto",
            duration_minutes=60,
        )
        # 两条操作应返回同一条记录（id 相同）
        assert ban1["id"] == ban2["id"]
        # 记录被更新
        assert ban2["reason"] == "再次封禁"
        # 仅生成一条日志（reban 不创建新日志，因为 ban_ip 在 existing 分支不创建日志）
        # 验证：只有首次封禁创建了日志
        # 注：reban 分支不创建日志，所以只有首次的一条 ban 日志

    async def test_reban_updates_expiry(self, ip_ban_service):
        """重新封禁时更新过期时间。"""
        ban1 = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="首次",
            duration_minutes=30,
        )
        ban2 = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="更新",
            duration_minutes=120,
        )
        assert ban1["id"] == ban2["id"]
        # expires_at 应该被更新（更长的时间）
        assert ban2["expires_at"] != ban1["expires_at"]


class TestUnbanIp:
    """unban_ip 方法测试。"""

    async def test_unban_ip_deactivates_and_creates_log(
        self, ip_ban_service, db_container
    ):
        """解封操作将封禁记录设为非活跃，并创建日志。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
            banned_by="admin",
        )
        result = await ip_ban_service.unban_ip(ban["id"], operator="operator1")
        assert result["is_active"] is False

        # 验证解封日志
        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            logs_result = await session.execute(
                select(IpBanLog).where(
                    IpBanLog.ban_id == ban["id"], IpBanLog.action == "unban"
                )
            )
            logs = logs_result.scalars().all()
            assert len(logs) == 1
            assert logs[0].operator == "operator1"
            assert logs[0].ip_or_cidr == "192.168.1.1"

    async def test_unban_nonexistent_raises_error(self, ip_ban_service):
        """解封不存在的记录抛出 AppError。"""
        with pytest.raises(AppError) as exc_info:
            await ip_ban_service.unban_ip(99999, operator="admin")
        assert exc_info.value.code == "ban_not_found"
        assert exc_info.value.status_code == 404


class TestBatchUnban:
    """batch_unban 方法测试。"""

    async def test_batch_unban_partial_success(self, ip_ban_service):
        """批量解封：部分成功（部分 ID 不存在）。"""
        ban1 = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="封禁1",
            banned_by="admin",
        )
        ban2 = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="封禁2",
            banned_by="admin",
        )
        # 第三个 ID 不存在
        count = await ip_ban_service.batch_unban(
            [ban1["id"], ban2["id"], 99999], operator="admin"
        )
        assert count == 2

    async def test_batch_unban_skips_inactive_bans(self, ip_ban_service):
        """批量解封跳过已非活跃的封禁记录。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="封禁",
            banned_by="admin",
        )
        await ip_ban_service.unban_ip(ban["id"], operator="admin")
        # 再次解封已被解封的记录，不应计入
        count = await ip_ban_service.batch_unban([ban["id"]], operator="admin")
        assert count == 0

    async def test_batch_unban_empty_list(self, ip_ban_service):
        """批量解封空列表返回 0。"""
        count = await ip_ban_service.batch_unban([], operator="admin")
        assert count == 0


class TestIsIpBanned:
    """is_ip_banned 方法测试。"""

    async def test_banned_ip_returns_true(self, ip_ban_service):
        """被封禁的 IP 返回 True。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
            duration_minutes=60,
        )
        assert await ip_ban_service.is_ip_banned("192.168.1.1") is True

    async def test_unbanned_ip_returns_false(self, ip_ban_service):
        """未被封禁的 IP 返回 False。"""
        assert await ip_ban_service.is_ip_banned("192.168.1.99") is False

    async def test_cidr_match_returns_true(self, ip_ban_service):
        """IP 匹配封禁的 CIDR 段返回 True。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.0/24",
            reason="段封禁",
            duration_minutes=60,
        )
        # 段内的 IP 应被匹配
        assert await ip_ban_service.is_ip_banned("10.0.0.50") is True
        # 段外的 IP 不应被匹配
        assert await ip_ban_service.is_ip_banned("10.0.1.1") is False

    async def test_expired_ban_returns_false(self, ip_ban_service, db_container):
        """已过期的封禁返回 False。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="过期封禁",
            duration_minutes=60,
        )
        # 手动将 expires_at 设为过去时间
        session_factory = db_container.get("db")["session_factory"]
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        async with session_factory() as session:
            result = await session.execute(select(IpBan).where(IpBan.id == ban["id"]))
            db_ban = result.scalar_one()
            db_ban.expires_at = past_time
            await session.commit()

        assert await ip_ban_service.is_ip_banned("192.168.1.1") is False

    async def test_unbanned_after_unban_returns_false(self, ip_ban_service):
        """解封后 IP 不再被封禁。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
            duration_minutes=60,
        )
        await ip_ban_service.unban_ip(ban["id"], operator="admin")
        assert await ip_ban_service.is_ip_banned("192.168.1.1") is False


class TestGetActiveIpRanges:
    """get_active_ip_ranges 方法测试。"""

    async def test_get_active_ip_ranges(self, ip_ban_service):
        """获取所有活跃的 IP/CIDR 段。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="封禁1",
            duration_minutes=60,
        )
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.0/24",
            reason="封禁2",
            duration_minutes=30,
        )
        ranges = await ip_ban_service.get_active_ip_ranges()
        assert "192.168.1.1" in ranges
        assert "10.0.0.0/24" in ranges
        assert len(ranges) == 2

    async def test_get_active_ip_ranges_excludes_unbanned(self, ip_ban_service):
        """已解封的记录不包含在活跃列表中。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试",
            duration_minutes=60,
        )
        await ip_ban_service.unban_ip(ban["id"], operator="admin")
        ranges = await ip_ban_service.get_active_ip_ranges()
        assert "192.168.1.1" not in ranges


class TestListBans:
    """list_bans 方法测试。"""

    async def test_list_bans_pagination(self, ip_ban_service, seeded_bans):
        """分页查询返回正确数量和分页信息。"""
        result = await ip_ban_service.list_bans(page=1, page_size=2)
        assert len(result["list"]) == 2
        assert result["total"] == 3
        assert result["page"] == 1
        assert result["page_size"] == 2

    async def test_list_bans_second_page(self, ip_ban_service, seeded_bans):
        """第二页返回剩余数据。"""
        result = await ip_ban_service.list_bans(page=2, page_size=2)
        assert len(result["list"]) == 1
        assert result["total"] == 3

    async def test_list_bans_filter_by_type(self, ip_ban_service, seeded_bans):
        """按 ban_type 过滤。"""
        result = await ip_ban_service.list_bans(ban_type="manual")
        assert result["total"] == 2
        for ban in result["list"]:
            assert ban["ban_type"] == "manual"

        result = await ip_ban_service.list_bans(ban_type="auto")
        assert result["total"] == 1
        for ban in result["list"]:
            assert ban["ban_type"] == "auto"

    async def test_list_bans_filter_by_active(self, ip_ban_service, seeded_bans):
        """按 is_active 过滤。"""
        # 先解封一个
        ban1, _ban2, _ban3 = seeded_bans
        await ip_ban_service.unban_ip(ban1["id"], operator="admin")

        result = await ip_ban_service.list_bans(is_active=True)
        assert result["total"] == 2

        result = await ip_ban_service.list_bans(is_active=False)
        assert result["total"] == 1

    async def test_list_bans_keyword_search(self, ip_ban_service, seeded_bans):
        """按 IP/CIDR 关键字搜索。"""
        result = await ip_ban_service.list_bans(keyword="192.168")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "192.168.1.1"

        result = await ip_ban_service.list_bans(keyword="10.0")
        assert result["total"] == 1

        result = await ip_ban_service.list_bans(keyword="不存在的")
        assert result["total"] == 0

    async def test_list_bans_combined_filters(self, ip_ban_service, seeded_bans):
        """组合过滤条件。"""
        # 解封 manual 类型的一个
        ban1, _ban2, _ban3 = seeded_bans
        await ip_ban_service.unban_ip(ban1["id"], operator="admin")

        # 查询 active=True + ban_type=manual
        result = await ip_ban_service.list_bans(is_active=True, ban_type="manual")
        # ban3 是 manual + active（未被解封）
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "172.16.0.1"

    async def test_list_bans_empty_result(self, ip_ban_service):
        """无封禁记录时返回空列表。"""
        result = await ip_ban_service.list_bans()
        assert result["total"] == 0
        assert result["list"] == []
        assert result["page"] == 1
        assert result["page_size"] == 20


class TestGetBanLogs:
    """get_ban_logs 方法测试。"""

    async def test_get_ban_logs_pagination(self, ip_ban_service, seeded_bans):
        """分页查询日志返回正确数量和分页信息。"""
        # seeded_bans 创建了 3 条封禁，共 3 条 ban 日志
        result = await ip_ban_service.get_ban_logs(page=1, page_size=2)
        assert len(result["list"]) == 2
        assert result["total"] == 3
        assert result["page"] == 1
        assert result["page_size"] == 2

    async def test_get_ban_logs_filter_by_action(self, ip_ban_service, seeded_bans):
        """按 action 过滤日志。"""
        # 先解封一个，产生 unban 日志
        ban1, _ban2, _ban3 = seeded_bans
        await ip_ban_service.unban_ip(ban1["id"], operator="admin")

        ban_logs = await ip_ban_service.get_ban_logs(action="ban")
        assert ban_logs["total"] == 3

        unban_logs = await ip_ban_service.get_ban_logs(action="unban")
        assert unban_logs["total"] == 1

    async def test_get_ban_logs_empty_result(self, ip_ban_service):
        """无日志时返回空列表。"""
        result = await ip_ban_service.get_ban_logs()
        assert result["total"] == 0
        assert result["list"] == []


class TestGetRuleConfigs:
    """get_rule_configs 方法测试。"""

    async def test_get_rule_configs_returns_defaults_when_empty(
        self, ip_ban_service, db_container
    ):
        """数据库无规则配置时返回默认值并写入数据库。"""
        # 第一次调用：写入默认值并返回（_get_default_rules 不含 enabled 字段）
        rules = await ip_ban_service.get_rule_configs()
        rule_ids = [r["id"] for r in rules]
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 10
        assert login_rule["window_seconds"] == 300
        assert login_rule["ban_duration_minutes"] == 30

        # 验证已写入数据库
        session_factory = db_container.get("db")["session_factory"]
        async with session_factory() as session:
            result = await session.execute(select(func.count(AutoBanRuleConfig.id)))
            count = result.scalar_one()
            assert count == 4

            # 验证数据库中的 enabled 字段使用 server_default True
            db_result = await session.execute(
                select(AutoBanRuleConfig).where(AutoBanRuleConfig.id == "login_failure")
            )
            db_rule = db_result.scalar_one()
            assert db_rule.enabled is True

        # 第二次调用：从数据库读取，enabled 字段正确
        rules2 = await ip_ban_service.get_rule_configs()
        login_rule2 = next(r for r in rules2 if r["id"] == "login_failure")
        assert login_rule2["enabled"] is True

    async def test_get_rule_configs_merges_with_existing(
        self, ip_ban_service, db_container
    ):
        """已存在的规则配置与默认值合并。"""
        # 先调用一次写入默认值
        await ip_ban_service.get_rule_configs()

        # 修改一个规则
        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 20, "enabled": False}
        )

        # 再次获取
        rules = await ip_ban_service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 20
        assert login_rule["enabled"] is False

    async def test_get_rule_configs_geo_surge_has_zero_duration(self, ip_ban_service):
        """geo_surge 规则的 ban_duration_minutes 为 0（不自动封禁）。"""
        rules = await ip_ban_service.get_rule_configs()
        geo_rule = next(r for r in rules if r["id"] == "geo_surge")
        assert geo_rule["ban_duration_minutes"] == 0


class TestUpdateRuleConfig:
    """update_rule_config 方法测试。"""

    async def test_update_rule_config_allowed_fields(self, ip_ban_service):
        """更新规则配置的允许字段。"""
        # 先初始化默认规则
        await ip_ban_service.get_rule_configs()

        result = await ip_ban_service.update_rule_config(
            "login_failure",
            {
                "enabled": False,
                "threshold": 15,
                "window_seconds": 600,
                "ban_duration_minutes": 60,
                "description": "更新后的描述",
                "name": "新名称",
            },
        )
        assert result["enabled"] is False
        assert result["threshold"] == 15
        assert result["window_seconds"] == 600
        assert result["ban_duration_minutes"] == 60
        assert result["description"] == "更新后的描述"
        assert result["name"] == "新名称"

    async def test_update_rule_config_ignores_unknown_fields(self, ip_ban_service):
        """更新时忽略不允许的字段。"""
        await ip_ban_service.get_rule_configs()

        result = await ip_ban_service.update_rule_config(
            "login_failure",
            {"threshold": 25, "non_existent_field": "should_be_ignored"},
        )
        assert result["threshold"] == 25
        # 不报错即可

    async def test_update_rule_config_nonexistent_raises_error(self, ip_ban_service):
        """更新不存在的规则抛出 AppError。"""
        with pytest.raises(AppError) as exc_info:
            await ip_ban_service.update_rule_config(
                "non_existent_rule", {"threshold": 10}
            )
        assert exc_info.value.code == "rule_not_found"
        assert exc_info.value.status_code == 404


class TestGetStats:
    """get_stats 方法测试。"""

    async def test_get_stats_empty(self, ip_ban_service):
        """无封禁记录时统计返回 0。"""
        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0
        assert stats["today_bans"] == 0

    async def test_get_stats_with_data(self, ip_ban_service):
        """有封禁记录时统计正确。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="手动封禁",
            ban_type="manual",
            banned_by="admin",
            duration_minutes=60,
        )
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="自动封禁",
            ban_type="auto",
            rule_id="login_failure",
            duration_minutes=30,
        )
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="自动封禁2",
            ban_type="auto",
            rule_id="rate_limit",
            duration_minutes=10,
        )

        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] == 3
        assert stats["active_bans"] == 3
        assert stats["auto_bans"] == 2
        assert stats["manual_bans"] == 1
        assert stats["today_bans"] == 3

    async def test_get_stats_active_count_excludes_unbanned(self, ip_ban_service):
        """活跃封禁数不包括已解封的记录。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="封禁",
            ban_type="manual",
            duration_minutes=60,
        )
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="封禁2",
            ban_type="auto",
            duration_minutes=30,
        )
        await ip_ban_service.unban_ip(ban["id"], operator="admin")

        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 1
        assert stats["manual_bans"] == 1
        assert stats["auto_bans"] == 1


# =============================================================================
# 规则引擎 Mock 测试（mock session_factory，避免 DB 依赖）
# =============================================================================


class TestRecordEvent:
    """record_event 方法测试。"""

    @pytest.fixture
    def mock_service(self):
        """创建 session_factory 被 mock 的 IpBanService。"""
        container = MagicMock()

        # mock db
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session_factory = MagicMock(return_value=AsyncMock())
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None
        db_mock = {"session_factory": mock_session_factory}

        def _mock_container_get(name):
            lookup = {
                "db": db_mock,
                "config": {"IP_BAN_WEBHOOK_URL": ""},
            }
            return lookup.get(name)

        container.get.side_effect = _mock_container_get

        service = IpBanService(container)
        # mock get_rule_configs 返回启用的规则
        service.get_rule_configs = AsyncMock(
            return_value=[
                {
                    "id": "login_failure",
                    "name": "登录失败封禁",
                    "enabled": True,
                    "threshold": 3,
                    "window_seconds": 300,
                    "ban_duration_minutes": 30,
                    "description": "测试规则",
                },
                {
                    "id": "high_4xx",
                    "name": "4xx 高频封禁",
                    "enabled": True,
                    "threshold": 3,
                    "window_seconds": 3600,
                    "ban_duration_minutes": 60,
                    "description": "测试规则",
                },
                {
                    "id": "rate_limit",
                    "name": "请求频率封禁",
                    "enabled": True,
                    "threshold": 3,
                    "window_seconds": 60,
                    "ban_duration_minutes": 10,
                    "description": "测试规则",
                },
            ]
        )
        # mock ban_ip 避免实际 DB 操作
        service.ban_ip = AsyncMock(return_value={"id": 1})
        return service

    async def test_record_event_login_failure_triggers_ban(self, mock_service):
        """登录失败事件达到阈值触发自动封禁。"""
        # 3 次触发阈值，我们只记录 3 次
        for _ in range(3):
            await mock_service.record_event("login_failure", "192.168.1.1")
        assert mock_service.ban_ip.await_count >= 1
        # 验证 ban_ip 被以正确的参数调用
        call_kwargs = mock_service.ban_ip.await_args.kwargs
        assert call_kwargs["ip_or_cidr"] == "192.168.1.1"
        assert call_kwargs["ban_type"] == "auto"
        assert call_kwargs["rule_id"] == "login_failure"

    async def test_record_event_high_4xx_triggers_ban(self, mock_service):
        """4xx 高频事件达到阈值触发自动封禁。"""
        for _ in range(3):
            await mock_service.record_event("high_4xx", "10.0.0.1", status_code=404)
        assert mock_service.ban_ip.await_count >= 1
        call_kwargs = mock_service.ban_ip.await_args.kwargs
        assert call_kwargs["rule_id"] == "high_4xx"

    async def test_record_event_high_4xx_ignores_non_4xx(self, mock_service):
        """high_4xx 事件只统计 4xx 状态码，忽略非 4xx。"""
        # 记录 3 次但 status_code 不是 4xx，不应触发
        for _ in range(3):
            await mock_service.record_event("high_4xx", "10.0.0.1", status_code=200)
        assert mock_service.ban_ip.await_count == 0

    async def test_record_event_rate_limit_triggers_ban(self, mock_service):
        """请求频率事件达到阈值触发自动封禁。"""
        for _ in range(3):
            await mock_service.record_event("rate_limit", "172.16.0.1")
        assert mock_service.ban_ip.await_count >= 1
        call_kwargs = mock_service.ban_ip.await_args.kwargs
        assert call_kwargs["rule_id"] == "rate_limit"

    async def test_record_event_below_threshold_no_ban(self, mock_service):
        """事件未达到阈值时不触发自动封禁。"""
        # 只记录 2 次（阈值是 3）
        for _ in range(2):
            await mock_service.record_event("login_failure", "192.168.1.1")
        assert mock_service.ban_ip.await_count == 0

    async def test_record_event_different_ips_independent_counters(self, mock_service):
        """不同 IP 的计数器相互独立。"""
        # IP_A 触发 3 次，IP_B 触发 1 次
        for _ in range(3):
            await mock_service.record_event("login_failure", "192.168.1.1")
        await mock_service.record_event("login_failure", "10.0.0.1")

        # 只有 IP_A 触发封禁
        assert mock_service.ban_ip.await_count >= 1
        call_kwargs = mock_service.ban_ip.await_args.kwargs
        assert call_kwargs["ip_or_cidr"] == "192.168.1.1"

    async def test_record_event_different_event_types_independent(self, mock_service):
        """不同事件类型的计数器相互独立。"""
        # login_failure 3 次，rate_limit 1 次
        for _ in range(3):
            await mock_service.record_event("login_failure", "192.168.1.1")
        await mock_service.record_event("rate_limit", "192.168.1.1")

        assert mock_service.ban_ip.await_count >= 1
        call_kwargs = mock_service.ban_ip.await_args.kwargs
        assert call_kwargs["rule_id"] == "login_failure"


class TestRuleCheckWithDisabledRule:
    """规则禁用时不触发自动封禁。"""

    @pytest.fixture
    def mock_service_disabled(self):
        """创建规则被禁用的 mock service。"""
        container = MagicMock()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session_factory = MagicMock(return_value=AsyncMock())
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = None
        db_mock = {"session_factory": mock_session_factory}

        def _mock_container_get_disabled(name):
            lookup = {
                "db": db_mock,
                "config": {"IP_BAN_WEBHOOK_URL": ""},
            }
            return lookup.get(name)

        container.get.side_effect = _mock_container_get_disabled

        service = IpBanService(container)
        service.get_rule_configs = AsyncMock(
            return_value=[
                {
                    "id": "login_failure",
                    "name": "登录失败封禁",
                    "enabled": False,  # 禁用
                    "threshold": 3,
                    "window_seconds": 300,
                    "ban_duration_minutes": 30,
                    "description": "测试规则（已禁用）",
                },
            ]
        )
        service.ban_ip = AsyncMock(return_value={"id": 1})
        return service

    async def test_disabled_rule_does_not_trigger_ban(self, mock_service_disabled):
        """禁用的规则不会触发自动封禁。"""
        for _ in range(5):
            await mock_service_disabled.record_event("login_failure", "192.168.1.1")
        # 即使超过阈值，因为规则禁用，也不应触发封禁
        assert mock_service_disabled.ban_ip.await_count == 0
