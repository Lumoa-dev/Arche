"""IpBanService 单元测试。

测试原则：
- 核心业务逻辑用 mock 数据库隔离测试
- 自动封禁规则引擎用真实计数器验证
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# ip_matches_cidr 纯函数测试
# =============================================================================


class TestIpMatchesCidr:
    """ip_matches_cidr 纯函数测试。"""

    def test_ipv4_in_cidr(self):
        """IPv4 地址在 CIDR 段内应返回 True。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_not_in_cidr(self):
        """IPv4 地址不在 CIDR 段内应返回 False。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_single_ip(self):
        """单个 IP 地址（/32）应精确匹配。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.5/32") is True
        assert ip_matches_cidr("10.0.0.6", "10.0.0.5/32") is False

    def test_ipv6_in_cidr(self):
        """IPv6 地址在 CIDR 段内应返回 True。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_ipv6_not_in_cidr(self):
        """IPv6 地址不在 CIDR 段内应返回 False。"""
        assert (
            ip_matches_cidr("2001:db9::1", "2001:db8::/32") is False
        )

    def test_invalid_ip_returns_false(self):
        """无效 IP 地址应返回 False 而不抛出异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 段应返回 False 而不抛出异常。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_private_ip_range(self):
        """私有地址段应正确匹配。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.0/8") is True
        assert ip_matches_cidr("172.16.0.1", "172.16.0.0/12") is True
        assert ip_matches_cidr("192.168.0.1", "192.168.0.0/16") is True


# =============================================================================
# Mock 辅助
# =============================================================================


def _make_mock_container():
    """创建 IpBanService 的 mock container。

    返回的 container 提供 mock db session_factory 和 config，
    外部可通过 container._mock_session 控制查询结果。
    """
    mock_execute_result = MagicMock()
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_config = MagicMock()
    mock_config.get.return_value = ""

    container = MagicMock()
    container.get.side_effect = lambda name: {
        "db": {"session_factory": mock_session_factory},
        "config": mock_config,
    }.get(name, MagicMock())
    container._mock_session = mock_session
    container._mock_result = mock_execute_result
    container._mock_session_factory = mock_session_factory
    container._mock_config = mock_config
    return container


# 辅助函数：创建 mock ban 对象
def _make_mock_ban(**kwargs):
    ban = MagicMock()
    ban.id = kwargs.get("id", 1)
    ban.ip_or_cidr = kwargs.get("ip_or_cidr", "192.168.1.100")
    ban.ban_type = kwargs.get("ban_type", "manual")
    ban.reason = kwargs.get("reason", "")
    ban.rule_id = kwargs.get("rule_id", None)
    ban.banned_by = kwargs.get("banned_by", None)
    ban.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    ban.expires_at = kwargs.get("expires_at", None)
    ban.is_active = kwargs.get("is_active", True)
    return ban


# =============================================================================
# IpBanService 基础操作测试
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceBasic:
    """IpBanService 基础 CRUD 操作测试。"""

    async def test_is_ip_banned_returns_true_when_matched(self):
        """IP 在活跃封禁列表中应返回 True。"""
        container = _make_mock_container()
        service = IpBanService(container)

        mock_ban = _make_mock_ban(ip_or_cidr="192.168.1.0/24")
        container._mock_result.scalars.return_value.all.return_value = [mock_ban]

        result = await service.is_ip_banned("192.168.1.100")
        assert result is True

    async def test_is_ip_banned_returns_false_when_no_match(self):
        """IP 不在封禁列表中应返回 False。"""
        container = _make_mock_container()
        service = IpBanService(container)

        mock_ban = _make_mock_ban(ip_or_cidr="10.0.0.0/8")
        container._mock_result.scalars.return_value.all.return_value = [mock_ban]

        result = await service.is_ip_banned("192.168.1.100")
        assert result is False

    async def test_is_ip_banned_returns_false_when_empty(self):
        """封禁列表为空时应返回 False。"""
        container = _make_mock_container()
        service = IpBanService(container)
        container._mock_result.scalars.return_value.all.return_value = []

        result = await service.is_ip_banned("192.168.1.100")
        assert result is False

    async def test_is_ip_banned_skips_expired_bans(self):
        """已过期的封禁记录不应匹配（SQL 层过滤，mock 仅验证 CIDR 匹配逻辑）。"""
        # 注：过期过滤由 SQL 查询的 or_(expires_at.is_(None), expires_at > now) 完成，
        # mock 层不模拟 SQL 过滤。此测试验证有效期查询仅返回活跃记录时的行为。
        container = _make_mock_container()
        service = IpBanService(container)

        # 模拟同时存在过期和未过期记录时，仅返回未过期记录
        active_ban = _make_mock_ban(
            ip_or_cidr="10.0.0.0/8",
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        container._mock_result.scalars.return_value.all.return_value = [active_ban]

        # 过期记录对应的 IP 不匹配
        result = await service.is_ip_banned("192.168.1.100")
        assert result is False

        # 活跃记录对应的 IP 匹配
        result = await service.is_ip_banned("10.0.0.5")
        assert result is True

    async def test_get_active_ip_ranges_returns_list(self):
        """获取活跃 IP 段列表应返回正确格式。"""
        container = _make_mock_container()
        service = IpBanService(container)

        container._mock_result.all.return_value = [
            ("192.168.1.0/24",),
            ("10.0.0.0/8",),
        ]

        result = await service.get_active_ip_ranges()
        assert result == ["192.168.1.0/24", "10.0.0.0/8"]

    async def test_get_active_ip_ranges_empty(self):
        """无活跃封禁时应返回空列表。"""
        container = _make_mock_container()
        service = IpBanService(container)
        container._mock_result.all.return_value = []

        result = await service.get_active_ip_ranges()
        assert result == []

    async def test_ban_ip_creates_new_ban(self):
        """封禁新 IP 应创建记录并返回封禁信息。"""
        container = _make_mock_container()
        service = IpBanService(container)

        # 首次查询无已有记录
        container._mock_result.scalar_one_or_none.return_value = None

        # mock 创建的 ban 对象
        new_ban = _make_mock_ban(
            id=1,
            ip_or_cidr="10.0.0.5",
            ban_type="manual",
            reason="恶意攻击",
            banned_by="admin",
        )
        container._mock_session.refresh = AsyncMock()

        # 使 session.add 捕获后设置返回值
        async def _refresh_side_effect(obj):
            for attr, value in {
                "id": 1,
                "ip_or_cidr": "10.0.0.5",
                "ban_type": "manual",
                "reason": "恶意攻击",
                "rule_id": None,
                "banned_by": "admin",
                "created_at": datetime.now(timezone.utc),
                "expires_at": None,
                "is_active": True,
            }.items():
                setattr(obj, attr, value)

        container._mock_session.refresh = AsyncMock(side_effect=_refresh_side_effect)
        container._mock_result.scalar_one_or_none.return_value = None

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.5",
            reason="恶意攻击",
            banned_by="admin",
        )

        assert result["ip_or_cidr"] == "10.0.0.5"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True

    async def test_ban_ip_updates_existing_ban(self):
        """已存在的活跃封禁应更新其过期时间和原因。"""
        container = _make_mock_container()
        service = IpBanService(container)

        existing = _make_mock_ban(
            id=1,
            ip_or_cidr="10.0.0.5",
            ban_type="auto",
            reason="旧原因",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        container._mock_result.scalar_one_or_none.return_value = existing

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.5",
            reason="新原因",
            duration_minutes=120,
        )

        assert existing.reason == "新原因"
        assert existing.expires_at is not None
        container._mock_session.commit.assert_awaited_once()

    async def test_ban_ip_with_duration_sets_expiry(self):
        """指定封禁时长应正确设置过期时间。"""
        container = _make_mock_container()
        service = IpBanService(container)
        container._mock_result.scalar_one_or_none.return_value = None

        new_ban = MagicMock()
        container._mock_session.refresh = AsyncMock()

        async def _refresh_side_effect(obj):
            for attr, value in {
                "id": 2,
                "ip_or_cidr": "10.0.0.6",
                "ban_type": "manual",
                "reason": "临时封禁",
                "rule_id": None,
                "banned_by": None,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
                "is_active": True,
            }.items():
                setattr(obj, attr, value)

        container._mock_session.refresh = AsyncMock(side_effect=_refresh_side_effect)

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.6",
            reason="临时封禁",
            duration_minutes=30,
        )

        assert result["is_active"] is True

    async def test_unban_ip_deactivates_ban(self):
        """解封应设置 is_active=False 并记录日志。"""
        container = _make_mock_container()
        service = IpBanService(container)

        ban = _make_mock_ban(id=1, ip_or_cidr="10.0.0.5", is_active=True)
        container._mock_result.scalar_one_or_none.return_value = ban

        result = await service.unban_ip(ban_id=1, operator="admin")

        assert ban.is_active is False
        assert result["is_active"] is False

    async def test_unban_ip_non_existent_raises_error(self):
        """解封不存在的记录应抛出 AppError。"""
        from backend.core.middleware import AppError

        container = _make_mock_container()
        service = IpBanService(container)
        container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(ban_id=999)
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "ban_not_found"

    async def test_batch_unban_deactivates_multiple(self):
        """批量解封应正确设置多条记录。"""
        container = _make_mock_container()
        service = IpBanService(container)

        ban1 = _make_mock_ban(id=1, is_active=True)
        ban2 = _make_mock_ban(id=2, is_active=True)
        ban3 = _make_mock_ban(id=3, is_active=False)

        # 三次查询依次返回不同的 ban
        container._mock_result.scalar_one_or_none.side_effect = [ban1, ban2, ban3]

        count = await service.batch_unban(ban_ids=[1, 2, 3], operator="admin")

        assert count == 2
        assert ban1.is_active is False
        assert ban2.is_active is False
        assert ban3.is_active is False  # 已经 inactive，不计数

    async def test_list_bans_pagination(self):
        """分页查询封禁列表应返回正确的分页信息。"""
        container = _make_mock_container()
        service = IpBanService(container)

        mock_ban = _make_mock_ban(id=1, ip_or_cidr="10.0.0.5")
        container._mock_result.scalars.return_value.all.return_value = [mock_ban]
        container._mock_result.scalar_one.return_value = 1

        result = await service.list_bans(page=1, page_size=10)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert len(result["list"]) == 1

    async def test_list_bans_filter_by_type(self):
        """查询封禁列表可按 ban_type 过滤。"""
        container = _make_mock_container()
        service = IpBanService(container)
        container._mock_result.scalars.return_value.all.return_value = []
        container._mock_result.scalar_one.return_value = 0

        result = await service.list_bans(ban_type="auto")
        assert result["total"] == 0

    async def test_list_bans_filter_by_keyword(self):
        """查询封禁列表可按 keyword 过滤。"""
        container = _make_mock_container()
        service = IpBanService(container)
        container._mock_result.scalars.return_value.all.return_value = []
        container._mock_result.scalar_one.return_value = 0

        result = await service.list_bans(keyword="192.168")
        assert result["total"] == 0

    async def test_get_ban_logs_pagination(self):
        """分页查询封禁日志应返回正确的格式。"""
        container = _make_mock_container()
        service = IpBanService(container)

        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.ban_id = 1
        mock_log.ip_or_cidr = "10.0.0.5"
        mock_log.action = "ban"
        mock_log.ban_type = "manual"
        mock_log.reason = "test"
        mock_log.operator = "admin"
        mock_log.detail = "永久封禁"
        mock_log.created_at = datetime.now(timezone.utc)
        container._mock_result.scalars.return_value.all.return_value = [mock_log]
        container._mock_result.scalar_one.return_value = 1

        result = await service.get_ban_logs(page=1, page_size=20)

        assert result["total"] == 1
        assert len(result["list"]) == 1
        assert result["list"][0]["action"] == "ban"

    async def test_get_ban_logs_filter_by_action(self):
        """查询封禁日志可按 action 过滤。"""
        container = _make_mock_container()
        service = IpBanService(container)
        container._mock_result.scalars.return_value.all.return_value = []
        container._mock_result.scalar_one.return_value = 0

        result = await service.get_ban_logs(action="unban")
        assert result["total"] == 0


# =============================================================================
# IpBanService 统计查询测试
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceStats:
    """IpBanService 统计功能测试。"""

    async def test_get_stats_returns_all_counts(self):
        """get_stats 应返回完整的统计信息。"""
        container = _make_mock_container()
        service = IpBanService(container)

        # 5 次 scalar_one 调用分别返回不同统计值
        container._mock_result.scalar_one.side_effect = [100, 30, 20, 80, 5]

        result = await service.get_stats()

        assert result["total_bans"] == 100
        assert result["active_bans"] == 30
        assert result["auto_bans"] == 20
        assert result["manual_bans"] == 80
        assert result["today_bans"] == 5

    async def test_get_stats_empty(self):
        """没有封禁记录时统计应全为 0。"""
        container = _make_mock_container()
        service = IpBanService(container)
        container._mock_result.scalar_one.side_effect = [0, 0, 0, 0, 0]

        result = await service.get_stats()

        for key in ("total_bans", "active_bans", "auto_bans", "manual_bans", "today_bans"):
            assert result[key] == 0


# =============================================================================
# IpBanService 自动封禁规则引擎测试
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceAutoBanEngine:
    """自动封禁规则引擎测试。"""

    async def test_record_event_triggers_login_failure_check(self):
        """record_event 应触发登录失败规则检查。"""
        container = _make_mock_container()
        service = IpBanService(container)

        with patch.object(service, "_check_login_failure_rule") as mock_check:
            await service.record_event("login_failure", "10.0.0.5")
            mock_check.assert_awaited_once_with("10.0.0.5")

    async def test_record_event_triggers_high_4xx_check(self):
        """record_event 应触发高频 4xx 规则检查。"""
        container = _make_mock_container()
        service = IpBanService(container)

        with patch.object(service, "_check_high_4xx_rule") as mock_check:
            await service.record_event("high_4xx", "10.0.0.5", status_code=404)
            mock_check.assert_awaited_once_with("10.0.0.5")

    async def test_record_event_triggers_rate_limit_check(self):
        """record_event 应触发请求频率规则检查。"""
        container = _make_mock_container()
        service = IpBanService(container)

        with patch.object(service, "_check_rate_limit_rule") as mock_check:
            await service.record_event("rate_limit", "10.0.0.5")
            mock_check.assert_awaited_once_with("10.0.0.5")

    async def test_record_event_unknown_type_no_check(self):
        """未知事件类型不应触发任何规则检查。"""
        container = _make_mock_container()
        service = IpBanService(container)

        with (
            patch.object(service, "_check_login_failure_rule") as mock_login,
            patch.object(service, "_check_high_4xx_rule") as mock_4xx,
            patch.object(service, "_check_rate_limit_rule") as mock_rate,
        ):
            await service.record_event("unknown_type", "10.0.0.5")
            mock_login.assert_not_awaited()
            mock_4xx.assert_not_awaited()
            mock_rate.assert_not_awaited()

    async def test_login_failure_rule_triggers_ban_when_threshold_exceeded(self):
        """登录失败次数超过阈值应触发自动封禁。"""
        container = _make_mock_container()
        service = IpBanService(container)

        with patch.object(
            service, "get_rule_configs"
        ) as mock_get_rules, patch.object(service, "ban_ip") as mock_ban:
            mock_get_rules.return_value = [
                {
                    "id": "login_failure",
                    "enabled": True,
                    "threshold": 3,
                    "window_seconds": 300,
                    "ban_duration_minutes": 30,
                }
            ]

            # 添加 5 次失败记录（超过阈值后每次 record_event 都会触发 ban）
            for _ in range(5):
                await service.record_event("login_failure", "10.0.0.5")

            # 至少触发一次封禁，且参数正确
            mock_ban.assert_awaited()
            last_call = mock_ban.call_args
            assert last_call.kwargs["ip_or_cidr"] == "10.0.0.5"
            assert last_call.kwargs["ban_type"] == "auto"
            assert last_call.kwargs["rule_id"] == "login_failure"

    async def test_login_failure_rule_not_triggers_when_below_threshold(self):
        """登录失败次数未超过阈值不应触发自动封禁。"""
        container = _make_mock_container()
        service = IpBanService(container)

        with patch.object(
            service, "get_rule_configs"
        ) as mock_get_rules, patch.object(service, "ban_ip") as mock_ban:
            mock_get_rules.return_value = [
                {
                    "id": "login_failure",
                    "enabled": True,
                    "threshold": 10,
                    "window_seconds": 300,
                    "ban_duration_minutes": 30,
                }
            ]

            for _ in range(3):
                await service.record_event("login_failure", "10.0.0.5")

            mock_ban.assert_not_awaited()

    async def test_high_4xx_rule_triggers_ban_when_threshold_exceeded(self):
        """4xx 高频超过阈值应触发自动封禁。"""
        container = _make_mock_container()
        service = IpBanService(container)

        with patch.object(
            service, "get_rule_configs"
        ) as mock_get_rules, patch.object(service, "ban_ip") as mock_ban:
            mock_get_rules.return_value = [
                {
                    "id": "high_4xx",
                    "enabled": True,
                    "threshold": 3,
                    "window_seconds": 3600,
                    "ban_duration_minutes": 60,
                }
            ]

            for _ in range(5):
                await service.record_event("high_4xx", "10.0.0.5", status_code=404)

            mock_ban.assert_awaited()

    async def test_rate_limit_rule_triggers_ban_when_threshold_exceeded(self):
        """请求频率超过阈值应触发自动封禁。"""
        container = _make_mock_container()
        service = IpBanService(container)

        with patch.object(
            service, "get_rule_configs"
        ) as mock_get_rules, patch.object(service, "ban_ip") as mock_ban:
            mock_get_rules.return_value = [
                {
                    "id": "rate_limit",
                    "enabled": True,
                    "threshold": 5,
                    "window_seconds": 60,
                    "ban_duration_minutes": 10,
                }
            ]

            for _ in range(10):
                await service.record_event("rate_limit", "10.0.0.5")

            mock_ban.assert_awaited()

    async def test_auto_ban_rule_disabled_does_not_trigger(self):
        """禁用的规则不应触发自动封禁。"""
        container = _make_mock_container()
        service = IpBanService(container)

        with patch.object(
            service, "get_rule_configs"
        ) as mock_get_rules, patch.object(service, "ban_ip") as mock_ban:
            mock_get_rules.return_value = [
                {
                    "id": "login_failure",
                    "enabled": False,
                    "threshold": 1,
                    "window_seconds": 300,
                    "ban_duration_minutes": 30,
                }
            ]

            await service.record_event("login_failure", "10.0.0.5")

            mock_ban.assert_not_awaited()


# =============================================================================
# IpBanService 规则配置测试
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceRuleConfig:
    """自动封禁规则配置管理测试。"""

    async def test_get_rule_configs_merges_default_and_db(self):
        """get_rule_configs 应合并数据库规则和默认规则。"""
        container = _make_mock_container()
        service = IpBanService(container)

        # 数据库返回一条规则
        db_rule = MagicMock()
        db_rule.id = "login_failure"
        db_rule.name = "登录失败封禁"
        db_rule.enabled = True
        db_rule.threshold = 10
        db_rule.window_seconds = 300
        db_rule.ban_duration_minutes = 30
        db_rule.description = "test"
        container._mock_result.scalars.return_value.all.return_value = [db_rule]

        with patch.object(service, "_ensure_default_rule") as mock_ensure:
            result = await service.get_rule_configs()

        assert len(result) >= 1
        login_rule = next(r for r in result if r["id"] == "login_failure")
        assert login_rule["threshold"] == 10

    async def test_update_rule_config_updates_fields(self):
        """update_rule_config 应更新允许的字段。"""
        container = _make_mock_container()
        service = IpBanService(container)

        rule = MagicMock()
        rule.id = "login_failure"
        rule.enabled = True
        rule.threshold = 10
        rule.window_seconds = 300
        rule.ban_duration_minutes = 30
        rule.description = "old desc"
        rule.name = "登录失败封禁"
        container._mock_result.scalar_one_or_none.return_value = rule

        result = await service.update_rule_config(
            "login_failure",
            {"threshold": 20, "description": "new desc"},
        )

        assert rule.threshold == 20
        assert rule.description == "new desc"
        assert rule.enabled is True  # 未更新的字段保持不变

    async def test_update_rule_config_non_existent_raises_error(self):
        """更新不存在的规则应抛出 AppError。"""
        from backend.core.middleware import AppError

        container = _make_mock_container()
        service = IpBanService(container)
        container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("non_existent", {"threshold": 5})
        assert excinfo.value.status_code == 404

    async def test_update_rule_config_ignores_unknown_fields(self):
        """update_rule_config 不应更新不在允许列表中的字段。"""
        container = _make_mock_container()
        service = IpBanService(container)

        rule = MagicMock(spec=[
            "id", "enabled", "threshold", "window_seconds",
            "ban_duration_minutes", "description", "name",
        ])
        rule.id = "login_failure"
        rule.enabled = True
        rule.threshold = 10
        rule.window_seconds = 300
        rule.ban_duration_minutes = 30
        rule.description = "desc"
        rule.name = "登录失败封禁"
        container._mock_result.scalar_one_or_none.return_value = rule

        result = await service.update_rule_config(
            "login_failure",
            {"threshold": 15, "dummy_field": "should_ignore"},
        )

        # 已知字段应被更新
        assert rule.threshold == 15
        # 未知字段不应被设置（spec 限制了 MagicMock 的属性）
        with pytest.raises(AttributeError):
            _ = rule.dummy_field


# =============================================================================
# IpBanService 计数器清理测试
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceCounterCleanup:
    """计数器清理机制测试。"""

    async def test_cleanup_counters_removes_expired_entries(self):
        """_cleanup_counters 应移除超过 1 小时的计数器条目。"""
        import time

        container = _make_mock_container()
        service = IpBanService(container)

        # 填入过期和未过期的条目
        now = time.time()
        service._counters = {
            "login_failure:10.0.0.1": [
                (now - 4000, 0),  # 过期 (>3600s)
                (now - 100, 0),   # 未过期
            ],
            "login_failure:10.0.0.2": [
                (now - 200, 0),   # 未过期
            ],
        }

        service._cleanup_counters()

        assert "login_failure:10.0.0.1" in service._counters
        assert len(service._counters["login_failure:10.0.0.1"]) == 1
        assert "login_failure:10.0.0.2" in service._counters

    async def test_cleanup_counters_removes_empty_keys(self):
        """_cleanup_counters 应移除所有条目都已过期的键。"""
        import time

        container = _make_mock_container()
        service = IpBanService(container)

        now = time.time()
        service._counters = {
            "login_failure:10.0.0.1": [
                (now - 4000, 0),  # 过期
            ],
        }

        service._cleanup_counters()

        assert "login_failure:10.0.0.1" not in service._counters