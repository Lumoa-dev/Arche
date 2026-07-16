"""IP 封禁插件——单元测试。

覆盖：ip_matches_cidr、is_ip_banned、ban_ip、unban_ip、自动封禁规则引擎。
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# ip_matches_cidr — IP/CIDR 匹配
# =============================================================================


class TestIpMatchesCidr:
    """ip_matches_cidr 工具函数测试。"""

    def test_ipv4_exact_match(self):
        """精确 IP 匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_cidr(self):
        """IP 在 CIDR 段内。"""
        assert ip_matches_cidr("192.168.1.50", "192.168.1.0/24") is True

    def test_ipv4_outside_cidr(self):
        """IP 不在 CIDR 段内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_invalid_ip(self):
        """非法 IP 字符串返回 False。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr(self):
        """非法 CIDR 格式返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_ipv6_match(self):
        """IPv6 匹配。"""
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_ipv6_in_cidr(self):
        """IPv6 在 CIDR 段内。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True


# =============================================================================
# Fixture
# =============================================================================


@pytest.fixture
def ip_ban_container():
    """创建 IpBanService 的 mock container。"""
    container = MagicMock()

    class FakeConfig:
        def get(self, key, default=""):
            if key == "IP_BAN_WEBHOOK_URL":
                return ""
            return default

    mock_execute_result = MagicMock()
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.rollback = AsyncMock()

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
def ip_ban_service(ip_ban_container):
    """创建 IpBanService 实例。"""
    return IpBanService(ip_ban_container)


# =============================================================================
# is_ip_banned — IP 封禁检查
# =============================================================================


@pytest.mark.asyncio
class TestIsIpBanned:
    """is_ip_banned 检查测试。"""

    async def test_not_banned_empty(self, ip_ban_service, ip_ban_container):
        """空封禁列表。"""
        ip_ban_container._mock_result.scalars.return_value.all.return_value = []
        result = await ip_ban_service.is_ip_banned("192.168.1.1")
        assert result is False

    async def test_not_banned_no_match(self, ip_ban_service, ip_ban_container):
        """IP 不在封禁列表中。"""
        mock_ban = MagicMock()
        mock_ban.ip_or_cidr = "10.0.0.0/8"
        ip_ban_container._mock_result.scalars.return_value.all.return_value = [
            mock_ban
        ]
        result = await ip_ban_service.is_ip_banned("192.168.1.1")
        assert result is False

    async def test_banned_exact_ip(self, ip_ban_service, ip_ban_container):
        """精确 IP 封禁。"""
        mock_ban = MagicMock()
        mock_ban.ip_or_cidr = "192.168.1.1"
        ip_ban_container._mock_result.scalars.return_value.all.return_value = [
            mock_ban
        ]
        result = await ip_ban_service.is_ip_banned("192.168.1.1")
        assert result is True

    async def test_banned_cidr_match(self, ip_ban_service, ip_ban_container):
        """CIDR 段匹配封禁。"""
        mock_ban = MagicMock()
        mock_ban.ip_or_cidr = "192.168.1.0/24"
        ip_ban_container._mock_result.scalars.return_value.all.return_value = [
            mock_ban
        ]
        result = await ip_ban_service.is_ip_banned("192.168.1.100")
        assert result is True


# =============================================================================
# ban_ip — 封禁管理
# =============================================================================


@pytest.mark.asyncio
class TestBanIp:
    """ban_ip 封禁测试。"""

    async def test_ban_ip_permanent(self, ip_ban_service, ip_ban_container):
        """永久封禁。"""
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None
        mock_ban = MagicMock()
        mock_ban.id = 1
        ip_ban_container._mock_session.refresh.return_value = mock_ban

        with patch.object(
            ip_ban_service, "_send_webhook_notification", AsyncMock()
        ):
            result = await ip_ban_service.ban_ip(
                ip_or_cidr="192.168.1.1",
                reason="恶意攻击",
                banned_by="admin",
            )
        assert result is not None

    async def test_ban_ip_temporary(self, ip_ban_service, ip_ban_container):
        """临时封禁（指定时长）。"""
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None
        mock_ban = MagicMock()
        mock_ban.id = 1
        ip_ban_container._mock_session.refresh.return_value = mock_ban

        with patch.object(
            ip_ban_service, "_send_webhook_notification", AsyncMock()
        ):
            result = await ip_ban_service.ban_ip(
                ip_or_cidr="10.0.0.1",
                reason="暴力破解",
                banned_by="system",
                duration_minutes=30,
            )
        assert result is not None

    async def test_ban_ip_duplicate(
        self, ip_ban_service, ip_ban_container
    ):
        """重复封禁已存在的 IP 返回已有记录。"""
        existing_ban = MagicMock()
        existing_ban.is_active = True
        ip_ban_container._mock_result.scalar_one_or_none.return_value = (
            existing_ban
        )

        with patch.object(
            ip_ban_service, "_send_webhook_notification", AsyncMock()
        ):
            result = await ip_ban_service.ban_ip(
                ip_or_cidr="192.168.1.1",
                reason="重复封禁",
            )
        # 返回已有记录（更新了 reason）
        assert existing_ban.reason == "重复封禁"


# =============================================================================
# unban_ip — 解封
# =============================================================================


@pytest.mark.asyncio
class TestUnbanIp:
    """unban_ip 解封测试。"""

    async def test_unban_ip(self, ip_ban_service, ip_ban_container):
        """正常解封。"""
        mock_ban = MagicMock()
        mock_ban.id = 1
        mock_ban.is_active = True
        ip_ban_container._mock_result.scalar_one_or_none.return_value = mock_ban
        ip_ban_container._mock_session.refresh.return_value = mock_ban

        result = await ip_ban_service.unban_ip(ban_id=1, operator="admin")
        assert mock_ban.is_active is False

    async def test_unban_not_found(self, ip_ban_service, ip_ban_container):
        """解封不存在的记录→404。"""
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await ip_ban_service.unban_ip(ban_id=999)
        assert "封禁记录不存在" in str(excinfo.value)


# =============================================================================
# 自动封禁规则引擎
# =============================================================================


@pytest.mark.asyncio
class TestAutoBanRules:
    """自动封禁规则引擎测试。"""

    async def test_get_rule_configs_defaults(
        self, ip_ban_service, ip_ban_container
    ):
        """获取默认规则配置。"""
        ip_ban_container._mock_result.scalars.return_value.all.return_value = []
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None

        rules = await ip_ban_service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    async def test_record_login_failure_below_threshold(
        self, ip_ban_service, ip_ban_container
    ):
        """登录失败未达阈值不触发封禁。"""
        # mock get_rule_configs 返回完整的规则字典
        mock_rule = {
            "id": "login_failure",
            "name": "登录失败封禁",
            "enabled": True,
            "threshold": 10,
            "window_seconds": 300,
            "ban_duration_minutes": 30,
            "description": "test",
        }
        with patch.object(
            ip_ban_service, "get_rule_configs", return_value=[mock_rule]
        ):
            # 只记录 3 次（阈值 10）
            for _ in range(3):
                await ip_ban_service.record_event(
                    event_type="login_failure", ip_str="10.0.0.1"
                )
        # 不应触发 ban_ip 调用（session.add 只来自 cleanup）
        assert ip_ban_container._mock_session.add.call_count == 0

    async def test_record_login_failure_above_threshold(
        self, ip_ban_service, ip_ban_container
    ):
        """登录失败达阈值触发自动封禁。"""
        mock_rule = {
            "id": "login_failure",
            "name": "登录失败封禁",
            "enabled": True,
            "threshold": 5,
            "window_seconds": 300,
            "ban_duration_minutes": 30,
            "description": "test",
        }

        with (
            patch.object(
                ip_ban_service, "get_rule_configs", return_value=[mock_rule]
            ),
            patch.object(
                ip_ban_service, "ban_ip", AsyncMock(return_value={"id": 1})
            ) as mock_ban_ip,
        ):
            for _ in range(6):
                await ip_ban_service.record_event(
                    event_type="login_failure", ip_str="10.0.0.2"
                )
            # 第 6 次应超过阈值 5，触发 ban_ip 调用
            mock_ban_ip.assert_called()

    async def test_rule_disabled(
        self, ip_ban_service, ip_ban_container
    ):
        """规则禁用时不触发封禁。"""
        mock_rule = {
            "id": "login_failure",
            "name": "登录失败封禁",
            "enabled": False,
            "threshold": 3,
            "window_seconds": 300,
            "ban_duration_minutes": 30,
            "description": "test",
        }
        with patch.object(
            ip_ban_service, "get_rule_configs", return_value=[mock_rule]
        ):
            for _ in range(10):
                await ip_ban_service.record_event(
                    event_type="login_failure", ip_str="10.0.0.3"
                )
        # 规则禁用，不应触发封禁
        assert ip_ban_container._mock_session.add.call_count == 0


# =============================================================================
# 计数器清理
# =============================================================================


class TestCounterCleanup:
    """计数器清理测试。"""

    def test_cleanup_expired_counters(self, ip_ban_service):
        """清理过期计数器。"""
        import time

        # 添加一个过期条目
        ip_ban_service._counters["login_failure:10.0.0.1"] = [
            (time.time() - 7200, 0)  # 2 小时前，已过期
        ]
        # 添加一个有效条目
        ip_ban_service._counters["login_failure:10.0.0.2"] = [
            (time.time() - 100, 0)  # 100 秒前，有效
        ]

        ip_ban_service._cleanup_counters()

        assert "login_failure:10.0.0.1" not in ip_ban_service._counters
        assert "login_failure:10.0.0.2" in ip_ban_service._counters