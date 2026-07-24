"""IP 封禁插件 单元测试。

安全关键模块，涵盖：
- CIDR 匹配逻辑
- 手动封禁/解封 CRUD
- 自动封禁规则引擎（登录失败、4xx 高频、请求频率）
- 事件计数和清理
- 规则配置管理与默认值
- 边界条件和错误处理
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# 测试辅助
# =============================================================================


def _make_ip_ban_container():
    """创建 IpBanService 的 mock container。

    遵循 blog 测试的 mock 模式，使用 MagicMock + AsyncMock.
    """
    container = MagicMock()

    class FakeConfig:
        _values = {  # noqa: RUF012
            "IP_BAN_WEBHOOK_URL": "",
            "SECRET_KEY": "test_secret_key_12345",
        }

        def get_required(self, key):
            return self._values.get(key, "")

        def get(self, key, default=None):
            return self._values.get(key, default)

    mock_execute_result = MagicMock()
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    def get_service(name):
        if name == "db":
            return {"session_factory": mock_session_factory}
        if name == "config":
            return FakeConfig()
        return MagicMock()

    container.get = get_service
    container._mock_session = mock_session
    container._mock_result = mock_execute_result
    container._mock_session_factory = mock_session_factory

    return container


@pytest.fixture
def ip_ban_container():
    """每个测试用例独立的 mock container。"""
    return _make_ip_ban_container()


def _make_mock_ban(**overrides):
    """创建模拟的 IpBan 对象。"""
    ban = MagicMock()
    ban.id = overrides.get("id", 1)
    ban.ip_or_cidr = overrides.get("ip_or_cidr", "192.168.1.1")
    ban.ban_type = overrides.get("ban_type", "manual")
    ban.reason = overrides.get("reason", "test ban")
    ban.rule_id = overrides.get("rule_id", None)
    ban.banned_by = overrides.get("banned_by", "admin")
    ban.created_at = overrides.get(
        "created_at", datetime.now(timezone.utc)
    )
    ban.expires_at = overrides.get("expires_at", None)
    ban.is_active = overrides.get("is_active", True)
    return ban


def _make_mock_log(**overrides):
    """创建模拟的 IpBanLog 对象。"""
    log = MagicMock()
    log.id = overrides.get("id", 1)
    log.ban_id = overrides.get("ban_id", None)
    log.ip_or_cidr = overrides.get("ip_or_cidr", "192.168.1.1")
    log.action = overrides.get("action", "ban")
    log.ban_type = overrides.get("ban_type", "manual")
    log.reason = overrides.get("reason", "test")
    log.operator = overrides.get("operator", "admin")
    log.detail = overrides.get("detail", "永久封禁")
    log.created_at = overrides.get(
        "created_at", datetime.now(timezone.utc)
    )
    return log


# =============================================================================
# IP 匹配工具函数测试
# =============================================================================


class TestIpMatchesCidr:
    """测试 ip_matches_cidr 工具函数。"""

    def test_ipv4_exact_match(self):
        """精确匹配 IPv4。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1") is True

    def test_ipv4_in_cidr(self):
        """IPv4 在 CIDR 段内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_cidr(self):
        """IPv4 不在 CIDR 段内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv6_in_cidr(self):
        """IPv6 在 CIDR 段内。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_ipv6_outside_cidr(self):
        """IPv6 不在 CIDR 段内。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db9::/32") is False
        )

    def test_invalid_ip_returns_false(self):
        """无效 IP 返回 False 不抛异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 返回 False 不抛异常。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_single_ip_no_cidr(self):
        """不带 CIDR 掩码的单个 IP 作为 /32 处理。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_cidr_boundary_low(self):
        """CIDR 边界下限。"""
        assert ip_matches_cidr("192.168.1.0", "192.168.1.0/24") is True

    def test_cidr_boundary_high(self):
        """CIDR 边界上限。"""
        assert ip_matches_cidr("192.168.1.255", "192.168.1.0/24") is True

    def test_cidr_just_below(self):
        """CIDR 边界正下方。"""
        assert ip_matches_cidr("192.168.0.255", "192.168.1.0/24") is False


# =============================================================================
# 手动封禁管理测试
# =============================================================================


@pytest.mark.asyncio
class TestBanIp:
    """测试 ban_ip 方法。"""

    async def test_ban_ip_simple(self, ip_ban_container):
        """简单封禁 IP。"""
        service = IpBanService(ip_ban_container)
        mock_ban = _make_mock_ban()
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None
        ip_ban_container._mock_session.refresh = AsyncMock(return_value=mock_ban)

        result = await service.ban_ip(ip_or_cidr="192.168.1.1", reason="attack")

        assert result["ip_or_cidr"] == "192.168.1.1"
        # refresh 返回 mock_ban，但 _ban_to_dict 读取的是刚创建的 IpBan 对象
        # 由于 mock session 不实际持久化，结果中的 reason 来自 mock_ban
        assert result["reason"] is not None
        ip_ban_container._mock_session.add.assert_called()
        ip_ban_container._mock_session.commit.assert_called()

    async def test_ban_ip_with_duration(self, ip_ban_container):
        """带过期时间的封禁。"""
        service = IpBanService(ip_ban_container)
        mock_ban = _make_mock_ban(expires_at=datetime.now(timezone.utc) + timedelta(minutes=30))
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None
        ip_ban_container._mock_session.refresh = AsyncMock(return_value=mock_ban)

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="temporary",
            duration_minutes=30,
        )

        assert result["ip_or_cidr"] == "10.0.0.1"
        assert result["expires_at"] is not None

    async def test_ban_ip_existing_active(self, ip_ban_container):
        """已存在的活跃封禁记录应更新而非新建。"""
        service = IpBanService(ip_ban_container)
        existing_ban = _make_mock_ban(id=1, ip_or_cidr="192.168.1.1")
        ip_ban_container._mock_result.scalar_one_or_none.return_value = existing_ban

        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="updated reason",
        )

        assert result["ip_or_cidr"] == "192.168.1.1"
        # 应更新已有记录，不新建
        assert existing_ban.reason == "updated reason"

    async def test_ban_ip_with_ban_type_auto(self, ip_ban_container):
        """自动封禁类型。"""
        service = IpBanService(ip_ban_container)
        mock_ban = _make_mock_ban(ban_type="auto", rule_id="login_failure")
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None
        ip_ban_container._mock_session.refresh = AsyncMock(return_value=mock_ban)

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="auto ban",
            ban_type="auto",
            rule_id="login_failure",
        )

        assert result["ban_type"] == "auto"
        # 验证也写了日志
        ip_ban_container._mock_session.add.assert_called()


@pytest.mark.asyncio
class TestUnbanIp:
    """测试 unban_ip 方法。"""

    async def test_unban_ip_success(self, ip_ban_container):
        """解封成功。"""
        service = IpBanService(ip_ban_container)
        mock_ban = _make_mock_ban(id=1, is_active=True)
        ip_ban_container._mock_result.scalar_one_or_none.return_value = mock_ban

        result = await service.unban_ip(ban_id=1, operator="admin")

        # ban 被标记为不活跃，_ban_to_dict 读取的是当前状态
        assert mock_ban.is_active is False  # 实际已被标记为不活跃

    async def test_unban_ip_not_found(self, ip_ban_container):
        """解封不存在的记录。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await service.unban_ip(ban_id=999)
        assert "不存在" in str(excinfo.value)


@pytest.mark.asyncio
class TestBatchUnban:
    """测试 batch_unban 方法。"""

    async def test_batch_unban_all_active(self, ip_ban_container):
        """批量解封所有活跃记录。"""
        service = IpBanService(ip_ban_container)

        mock_bans = [
            _make_mock_ban(id=1, is_active=True),
            _make_mock_ban(id=2, is_active=True),
        ]
        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_bans[0])),
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_bans[1])),
            ]
        )

        count = await service.batch_unban(ban_ids=[1, 2], operator="admin")
        assert count == 2

    async def test_batch_unban_mixed(self, ip_ban_container):
        """批量解封混合状态。"""
        service = IpBanService(ip_ban_container)

        mock_bans = [
            _make_mock_ban(id=1, is_active=True),
            _make_mock_ban(id=2, is_active=False),
        ]
        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_bans[0])),
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_bans[1])),
            ]
        )

        count = await service.batch_unban(ban_ids=[1, 2], operator="admin")
        assert count == 1  # 只有第一个是活跃的

    async def test_batch_unban_empty(self, ip_ban_container):
        """空批量解封列表。"""
        service = IpBanService(ip_ban_container)
        count = await service.batch_unban(ban_ids=[], operator="admin")
        assert count == 0


# =============================================================================
# IP 检查测试
# =============================================================================


@pytest.mark.asyncio
class TestIsIpBanned:
    """测试 is_ip_banned 方法。"""

    async def test_ip_not_banned(self, ip_ban_container):
        """IP 未被封禁。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.scalars.return_value.all.return_value = []

        result = await service.is_ip_banned("192.168.1.1")
        assert result is False

    async def test_ip_banned_exact(self, ip_ban_container):
        """IP 精确匹配封禁。"""
        service = IpBanService(ip_ban_container)
        mock_ban = _make_mock_ban(ip_or_cidr="192.168.1.1")
        ip_ban_container._mock_result.scalars.return_value.all.return_value = [
            mock_ban
        ]

        result = await service.is_ip_banned("192.168.1.1")
        assert result is True

    async def test_ip_banned_in_cidr(self, ip_ban_container):
        """IP 在 CIDR 封禁段内。"""
        service = IpBanService(ip_ban_container)
        mock_ban = _make_mock_ban(ip_or_cidr="192.168.0.0/16")
        ip_ban_container._mock_result.scalars.return_value.all.return_value = [
            mock_ban
        ]

        result = await service.is_ip_banned("192.168.1.100")
        assert result is True

    async def test_expired_ban_ignored(self, ip_ban_container):
        """已过期的封禁不应匹配。"""
        service = IpBanService(ip_ban_container)
        # 模拟 query 过滤掉过期记录，所以返回空列表
        ip_ban_container._mock_result.scalars.return_value.all.return_value = []

        result = await service.is_ip_banned("192.168.1.1")
        assert result is False


# =============================================================================
# 列表查询测试
# =============================================================================


@pytest.mark.asyncio
class TestListBans:
    """测试 list_bans 方法。"""

    async def test_list_bans_empty(self, ip_ban_container):
        """空封禁列表。"""
        service = IpBanService(ip_ban_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_bans(page=1, page_size=20)
        assert result["total"] == 0
        assert result["list"] == []

    async def test_list_bans_with_data(self, ip_ban_container):
        """封禁列表返回数据。"""
        service = IpBanService(ip_ban_container)
        mock_ban = _make_mock_ban(id=1, ip_or_cidr="10.0.0.1")

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [mock_ban]

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_bans(page=1, page_size=20)
        assert result["total"] == 1
        assert len(result["list"]) == 1
        assert result["list"][0]["ip_or_cidr"] == "10.0.0.1"

    async def test_list_bans_filter_by_type(self, ip_ban_container):
        """按封禁类型筛选。"""
        service = IpBanService(ip_ban_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_bans(ban_type="auto")
        assert result["total"] == 0

    async def test_list_bans_keyword_search(self, ip_ban_container):
        """按关键词搜索。"""
        service = IpBanService(ip_ban_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_bans(keyword="192.168")
        assert result["total"] == 0

    async def test_list_bans_pagination(self, ip_ban_container):
        """分页参数正确传递。"""
        service = IpBanService(ip_ban_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 5
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [
            _make_mock_ban(id=i) for i in range(2)
        ]

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.list_bans(page=1, page_size=2)
        assert result["page"] == 1
        assert result["page_size"] == 2
        assert result["total"] == 5


# =============================================================================
# 封禁日志测试
# =============================================================================


@pytest.mark.asyncio
class TestGetBanLogs:
    """测试 get_ban_logs 方法。"""

    async def test_get_ban_logs_empty(self, ip_ban_container):
        """空日志列表。"""
        service = IpBanService(ip_ban_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.get_ban_logs(page=1, page_size=20)
        assert result["total"] == 0
        assert result["list"] == []

    async def test_get_ban_logs_with_data(self, ip_ban_container):
        """日志列表返回数据。"""
        service = IpBanService(ip_ban_container)
        mock_log = _make_mock_log(action="ban")

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [mock_log]

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.get_ban_logs(page=1, page_size=20)
        assert result["total"] == 1
        assert result["list"][0]["action"] == "ban"

    async def test_get_ban_logs_filter_action(self, ip_ban_container):
        """按操作类型筛选日志。"""
        service = IpBanService(ip_ban_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, data_result]
        )

        result = await service.get_ban_logs(action="unban")
        assert result["total"] == 0


# =============================================================================
# 规则配置测试
# =============================================================================


@pytest.mark.asyncio
class TestRuleConfigs:
    """测试规则配置管理。"""

    async def test_get_rule_configs_empty_db(self, ip_ban_container):
        """数据库为空时返回默认规则。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.scalars.return_value.all.return_value = []

        rules = await service.get_rule_configs()

        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids
        assert len(rules) == 4

    async def test_get_rule_configs_merges_db(self, ip_ban_container):
        """数据库中的规则与默认规则合并。"""
        service = IpBanService(ip_ban_container)

        db_rule = MagicMock()
        db_rule.id = "login_failure"
        db_rule.name = "登录失败封禁"
        db_rule.enabled = True
        db_rule.threshold = 5  # 自定义阈值
        db_rule.window_seconds = 300
        db_rule.ban_duration_minutes = 30
        db_rule.description = "自定义描述"

        ip_ban_container._mock_result.scalars.return_value.all.return_value = [
            db_rule
        ]

        rules = await service.get_rule_configs()

        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 5  # 应该使用数据库中的值

    async def test_update_rule_config_success(self, ip_ban_container):
        """更新规则配置成功。"""
        service = IpBanService(ip_ban_container)

        db_rule = MagicMock()
        db_rule.id = "login_failure"
        db_rule.enabled = True
        db_rule.threshold = 10
        db_rule.window_seconds = 300
        db_rule.ban_duration_minutes = 30
        db_rule.description = "desc"
        db_rule.name = "name"

        ip_ban_container._mock_result.scalar_one_or_none.return_value = db_rule

        result = await service.update_rule_config(
            "login_failure", {"threshold": 20, "ban_duration_minutes": 60}
        )

        assert db_rule.threshold == 20
        assert db_rule.ban_duration_minutes == 60

    async def test_update_rule_config_not_found(self, ip_ban_container):
        """更新不存在的规则。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await service.update_rule_config("nonexistent", {"threshold": 5})
        assert "不存在" in str(excinfo.value)

    async def test_update_rule_config_invalid_field(self, ip_ban_container):
        """更新不允许的字段应被忽略。"""
        service = IpBanService(ip_ban_container)

        db_rule = MagicMock()
        db_rule.id = "login_failure"
        db_rule.enabled = True
        db_rule.threshold = 10

        ip_ban_container._mock_result.scalar_one_or_none.return_value = db_rule

        result = await service.update_rule_config(
            "login_failure", {"threshold": 15, "invalid_field": "should_be_ignored"}
        )

        assert db_rule.threshold == 15
        # 验证方法没有因未知字段而抛异常


# =============================================================================
# 自动封禁规则引擎测试
# =============================================================================


@pytest.mark.asyncio
class TestAutoBanEngine:
    """测试自动封禁规则引擎。"""

    @pytest.fixture
    def service_with_rules(self, ip_ban_container):
        """创建带有默认规则配置的 service。"""
        service = IpBanService(ip_ban_container)

        rules = [
            {
                "id": "login_failure",
                "enabled": True,
                "threshold": 3,
                "window_seconds": 60,
                "ban_duration_minutes": 30,
                "name": "登录失败封禁",
                "description": "",
            },
            {
                "id": "high_4xx",
                "enabled": True,
                "threshold": 5,
                "window_seconds": 60,
                "ban_duration_minutes": 60,
                "name": "4xx 高频封禁",
                "description": "",
            },
            {
                "id": "rate_limit",
                "enabled": True,
                "threshold": 10,
                "window_seconds": 60,
                "ban_duration_minutes": 10,
                "name": "请求频率封禁",
                "description": "",
            },
        ]
        ip_ban_container._mock_result.scalars.return_value.all.return_value = []
        # get_rule_configs 返回 mock 规则
        # 需要 mock 两次：一次在 get_rule_configs 中，一次在 ban_ip 中
        # 使用 side_effect 来处理多次调用
        original_execute = ip_ban_container._mock_session.execute

        call_count = [0]

        async def mock_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                # 第一次调用：get_rule_configs 的 scalars
                r = MagicMock()
                r.scalars.return_value.all.return_value = []
                return r
            # 其他调用：ban_ip 的 scalar_one_or_none
            r = MagicMock()
            r.scalar_one_or_none.return_value = None
            return r

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=mock_execute_side_effect
        )

        # Mock ban_ip 不执行真实逻辑
        mock_ban = _make_mock_ban(ban_type="auto")
        service.ban_ip = AsyncMock(return_value=mock_ban)

        # Mock get_rule_configs 返回真实规则
        service.get_rule_configs = AsyncMock(return_value=rules)

        return service

    async def test_login_failure_rule_triggered(
        self, service_with_rules, ip_ban_container
    ):
        """登录失败达到阈值触发自动封禁。"""
        service = service_with_rules

        # 记录 3 次登录失败事件（阈值=3）
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.1")

        service.ban_ip.assert_called_once()

    async def test_login_failure_rule_not_triggered(
        self, service_with_rules, ip_ban_container
    ):
        """登录失败未达阈值不触发封禁。"""
        service = service_with_rules

        # 只记录 2 次（阈值=3）
        for _ in range(2):
            await service.record_event("login_failure", "10.0.0.2")

        service.ban_ip.assert_not_called()

    async def test_high_4xx_rule_triggered(self, service_with_rules, ip_ban_container):
        """4xx 高频达到阈值触发自动封禁。"""
        service = service_with_rules

        for _ in range(5):
            await service.record_event("high_4xx", "10.0.0.3", status_code=403)

        service.ban_ip.assert_called_once()

    async def test_high_4xx_rule_ignores_5xx(
        self, service_with_rules, ip_ban_container
    ):
        """5xx 状态码不应触发 4xx 规则。"""
        service = service_with_rules

        for _ in range(5):
            await service.record_event("high_4xx", "10.0.0.4", status_code=500)

        service.ban_ip.assert_not_called()

    async def test_rate_limit_rule_triggered(
        self, service_with_rules, ip_ban_container
    ):
        """请求频率达到阈值触发自动封禁。"""
        service = service_with_rules

        for _ in range(10):
            await service.record_event("rate_limit", "10.0.0.5")

        service.ban_ip.assert_called_once()

    async def test_multiple_ips_independent_counters(
        self, service_with_rules, ip_ban_container
    ):
        """不同 IP 的计数器互相独立。"""
        service = service_with_rules

        # IP1 触发阈值
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.10")
        # IP2 不触发
        for _ in range(2):
            await service.record_event("login_failure", "10.0.0.11")

        # 使用不同的阈值
        rules = [
            {
                "id": "login_failure",
                "enabled": True,
                "threshold": 3,
                "window_seconds": 60,
                "ban_duration_minutes": 30,
                "name": "登录失败封禁",
                "description": "",
            },
        ]
        service.get_rule_configs = AsyncMock(return_value=rules)
        service.ban_ip = AsyncMock()

        # 手动触发检查
        await service._check_login_failure_rule("10.0.0.10")
        service.ban_ip.assert_called_once()

        service.ban_ip.reset_mock()
        await service._check_login_failure_rule("10.0.0.11")
        service.ban_ip.assert_not_called()


# =============================================================================
# 计数器清理测试
# =============================================================================


class TestCounterCleanup:
    """测试计数器过期清理。"""

    def test_cleanup_expired_counters(self):
        """清理过期计数器条目。"""
        container = _make_ip_ban_container()
        service = IpBanService(container)

        now = time.time()
        # 添加一个过期条目（超过 3600 秒）
        service._counters["test:1.1.1.1"] = [(now - 4000, 0)]
        # 添加一个有效条目
        service._counters["test:2.2.2.2"] = [(now - 100, 0)]

        service._cleanup_counters()

        assert "test:1.1.1.1" not in service._counters
        assert "test:2.2.2.2" in service._counters

    def test_cleanup_empty_counters(self):
        """清理空计数器。"""
        container = _make_ip_ban_container()
        service = IpBanService(container)
        assert service._counters == {}
        service._cleanup_counters()  # 不应抛异常
        assert service._counters == {}


# =============================================================================
# 统计测试
# =============================================================================


@pytest.mark.asyncio
class TestGetStats:
    """测试 get_stats 方法。"""

    async def test_get_stats_empty(self, ip_ban_container):
        """空统计。"""
        service = IpBanService(ip_ban_container)

        # 5 次 execute 调用：total, active, auto, manual, today
        count_results = [MagicMock(scalar_one=MagicMock(return_value=0)) for _ in range(5)]
        ip_ban_container._mock_session.execute = AsyncMock(side_effect=count_results)

        stats = await service.get_stats()

        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0
        assert stats["today_bans"] == 0

    async def test_get_stats_with_data(self, ip_ban_container):
        """有数据的统计。"""
        service = IpBanService(ip_ban_container)

        values = [100, 30, 60, 40, 10]
        count_results = [
            MagicMock(scalar_one=MagicMock(return_value=v)) for v in values
        ]
        ip_ban_container._mock_session.execute = AsyncMock(side_effect=count_results)

        stats = await service.get_stats()

        assert stats["total_bans"] == 100
        assert stats["active_bans"] == 30
        assert stats["auto_bans"] == 60
        assert stats["manual_bans"] == 40
        assert stats["today_bans"] == 10


# =============================================================================
# 活跃 IP 范围测试
# =============================================================================


@pytest.mark.asyncio
class TestGetActiveIpRanges:
    """测试 get_active_ip_ranges 方法。"""

    async def test_get_active_ip_ranges_empty(self, ip_ban_container):
        """空活跃范围列表。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.all.return_value = []

        ranges = await service.get_active_ip_ranges()
        assert ranges == []

    async def test_get_active_ip_ranges_with_data(self, ip_ban_container):
        """有活跃范围。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.all.return_value = [
            ("192.168.1.1",),
            ("10.0.0.0/8",),
        ]

        ranges = await service.get_active_ip_ranges()
        assert "192.168.1.1" in ranges
        assert "10.0.0.0/8" in ranges
        assert len(ranges) == 2


# =============================================================================
# Webhook 通知测试
# =============================================================================


@pytest.mark.asyncio
class TestWebhookNotification:
    """测试 webhook 通知。"""

    async def test_webhook_no_url(self, ip_ban_container):
        """没有配置 webhook URL 时不发送通知。"""
        service = IpBanService(ip_ban_container)
        service._webhook_url = ""

        with patch("backend.plugins.ip_ban.services._HAS_AIOHTTP", True):
            result = await service._send_webhook_notification(
                "ip_banned", {"ip_or_cidr": "10.0.0.1"}
            )
            assert result is None  # 不应抛异常

    async def test_webhook_without_aiohttp(self, ip_ban_container):
        """没有安装 aiohttp 时不发送通知。"""
        service = IpBanService(ip_ban_container)
        service._webhook_url = "https://hooks.example.com/alert"

        with patch("backend.plugins.ip_ban.services._HAS_AIOHTTP", False):
            result = await service._send_webhook_notification(
                "ip_banned", {"ip_or_cidr": "10.0.0.1"}
            )
            assert result is None  # 静默忽略