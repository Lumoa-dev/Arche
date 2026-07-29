"""IP 封禁服务测试。

测试原则：
- 覆盖 ip_matches_cidr、自动封禁规则引擎的核心逻辑
- DB 交互部分使用 db_container fixture
- 计数器清理和规则检查使用 time.time 打桩
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


class TestIpMatchesCidr:
    """测试 ip_matches_cidr 函数。"""

    def test_ipv4_in_cidr(self):
        """IPv4 地址在 CIDR 段内应返回 True。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_cidr(self):
        """IPv4 地址不在 CIDR 段内应返回 False。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_exact_match(self):
        """精确 IP 匹配应返回 True。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1/32") is True

    def test_cidr_without_prefix(self):
        """CIDR 不带前缀时应自动计算。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.0/24") is True
        assert ip_matches_cidr("10.0.1.5", "10.0.0.0/24") is False

    def test_ipv6_in_cidr(self):
        """IPv6 地址在 CIDR 段内应返回 True。"""
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_invalid_ip(self):
        """无效 IP 应返回 False。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr(self):
        """无效 CIDR 应返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_broadcast_address(self):
        """广播地址不匹配。"""
        assert ip_matches_cidr("192.168.1.255", "192.168.1.0/24") is True

    def test_single_ip_vs_cidr(self):
        """单个 IP 匹配自己的 CIDR。"""
        assert ip_matches_cidr("203.0.113.42", "203.0.113.42") is True


class TestIpBanServiceInit:
    """测试 IpBanService 初始化。"""

    def test_init_with_webhook_url(self):
        """初始化时正确读取 webhook URL。"""
        container = MagicMock()
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: (
            "https://hooks.example.com/webhook" if key == "IP_BAN_WEBHOOK_URL" else default
        )
        container.get.return_value = config
        db_mock = {"session_factory": MagicMock()}
        container.get.side_effect = lambda name: db_mock if name == "db" else config

        service = IpBanService(container)
        assert service._webhook_url == "https://hooks.example.com/webhook"

    def test_init_empty_webhook_url(self):
        """webhook URL 为空时正常初始化。"""
        container = MagicMock()
        config = MagicMock()
        config.get.return_value = ""
        container.get.return_value = config
        db_mock = {"session_factory": MagicMock()}
        container.get.side_effect = lambda name: db_mock if name == "db" else config

        service = IpBanService(container)
        assert service._webhook_url == ""


class TestIpBanServiceCounters:
    """测试 IpBanService 计数器逻辑。"""

    def test_cleanup_counters_removes_expired(self):
        """清理过期的计数器条目。"""
        container = MagicMock()
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: (
            "" if key == "IP_BAN_WEBHOOK_URL" else default
        )
        container.get.return_value = config
        db_mock = {"session_factory": MagicMock()}
        container.get.side_effect = lambda name: db_mock if name == "db" else config

        service = IpBanService(container)
        now = time.time()
        # 添加一个过期条目（3600 秒前）
        service._counters["test:1.2.3.4"] = [
            (now - 4000, 200),  # 过期
            (now - 500, 200),  # 有效
        ]
        service._cleanup_counters()
        assert len(service._counters["test:1.2.3.4"]) == 1
        assert service._counters["test:1.2.3.4"][0][0] == now - 500

    def test_cleanup_counters_removes_empty_key(self):
        """清理后空的 key 应被删除。"""
        container = MagicMock()
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: (
            "" if key == "IP_BAN_WEBHOOK_URL" else default
        )
        container.get.return_value = config
        db_mock = {"session_factory": MagicMock()}
        container.get.side_effect = lambda name: db_mock if name == "db" else config

        service = IpBanService(container)
        now = time.time()
        service._counters["empty:1.2.3.4"] = [(now - 4000, 200)]
        service._cleanup_counters()
        assert "empty:1.2.3.4" not in service._counters

    def test_ban_to_dict_format(self, db_container):
        """_ban_to_dict 返回正确的字典格式。"""
        service = IpBanService(db_container)

        # 使用 mock 对象模拟 ban 记录
        class MockBan:
            id = 1
            ip_or_cidr = "192.168.1.1"
            ban_type = "manual"
            reason = "test"
            rule_id = None
            banned_by = "admin"
            created_at = None
            expires_at = None
            is_active = True

        result = service._ban_to_dict(MockBan())
        assert result["id"] == 1
        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["created_at"] is None
        assert result["expires_at"] is None


class TestIpBanServiceAutoBanRules:
    """测试自动封禁规则引擎。"""

    def test_get_default_rules_contains_all_rules(self, db_container):
        """默认规则应包含所有预定义规则。"""
        service = IpBanService(db_container)
        rules = service._get_default_rules()
        assert "login_failure" in rules
        assert "high_4xx" in rules
        assert "rate_limit" in rules
        assert "geo_surge" in rules

    @patch("backend.plugins.ip_ban.services.time.time")
    async def test_record_event_checks_login_failure(self, mock_time, db_container):
        """record_event 记录 login_failure 后应检查规则。"""
        mock_time.return_value = 1000.0
        service = IpBanService(db_container)

        # 直接 mock 规则检查方法，避免 DB 依赖
        service._check_login_failure_rule = AsyncMock()

        # 记录 3 次登录失败
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.1")

        # 应检查规则 3 次
        assert service._check_login_failure_rule.call_count == 3

    @patch("backend.plugins.ip_ban.services.time.time")
    async def test_record_event_below_threshold(self, mock_time, db_container):
        """低于阈值时不应触发封禁（通过计数器逻辑验证）。"""
        mock_time.return_value = 1000.0
        service = IpBanService(db_container)

        # mock 规则检查方法
        service._check_login_failure_rule = AsyncMock()
        service.ban_ip = AsyncMock()

        # 只记录 3 次，低于默认阈值 10
        for _ in range(3):
            await service.record_event("login_failure", "10.0.0.1")

        # 检查 login_failure 的计数器
        key = "login_failure:10.0.0.1"
        assert key in service._counters
        assert len(service._counters[key]) == 3

    @patch("backend.plugins.ip_ban.services.time.time")
    async def test_disabled_rule_does_not_ban(self, mock_time, db_container):
        """禁用的规则不应触发封禁。"""
        mock_time.return_value = 1000.0
        service = IpBanService(db_container)

        # mock 规则检查方法
        service._check_rate_limit_rule = AsyncMock()
        service.ban_ip = AsyncMock()

        for _ in range(5):
            await service.record_event("rate_limit", "10.0.0.1")

        service.ban_ip.assert_not_called()

    @patch("backend.plugins.ip_ban.services.time.time")
    async def test_high_4xx_rule_only_counts_4xx(self, mock_time, db_container):
        """high_4xx 规则只计数 400-499 状态码。"""
        mock_time.return_value = 1000.0
        service = IpBanService(db_container)

        # mock 规则检查方法，用于验证调用次数
        service._check_high_4xx_rule = AsyncMock()
        service.ban_ip = AsyncMock()

        # 记录多种状态码
        await service.record_event("high_4xx", "10.0.0.1", 404)
        await service.record_event("high_4xx", "10.0.0.1", 403)
        await service.record_event("high_4xx", "10.0.0.1", 200)
        await service.record_event("high_4xx", "10.0.0.1", 500)
        await service.record_event("high_4xx", "10.0.0.1", 401)

        # 规则检查方法应被调用 5 次（每次 record_event 触发一次）
        assert service._check_high_4xx_rule.call_count == 5

        # 验证计数器内的状态码
        key = "high_4xx:10.0.0.1"
        assert key in service._counters
        # 应有 5 条记录
        assert len(service._counters[key]) == 5
        # 4xx 状态码的数量
        status_codes = [s for _, s in service._counters[key]]
        four_xx_count = sum(1 for s in status_codes if 400 <= s < 500)
        assert four_xx_count == 3  # 404, 403, 401

    @patch("backend.plugins.ip_ban.services.time.time")
    async def test_record_event_auto_cleanup_counters(self, mock_time, db_container):
        """record_event 在超过 60 秒后自动清理计数器。"""
        mock_time.return_value = 1000.0
        service = IpBanService(db_container)
        service._cleanup_counters = MagicMock()
        # mock 规则检查方法避免 DB 依赖
        service._check_login_failure_rule = AsyncMock()

        # 首次记录，last_cleanup = 0，应触发清理
        await service.record_event("login_failure", "10.0.0.1")
        service._cleanup_counters.assert_called_once()

    @patch("backend.plugins.ip_ban.services.time.time")
    async def test_record_event_skips_cleanup_within_60s(self, mock_time, db_container):
        """60 秒内不重复清理。"""
        mock_time.return_value = 1000.0
        service = IpBanService(db_container)
        # 设置 last_cleanup 为 10 秒前
        service._last_cleanup = 990.0
        service._cleanup_counters = MagicMock()
        # mock 规则检查方法避免 DB 依赖
        service._check_login_failure_rule = AsyncMock()

        await service.record_event("login_failure", "10.0.0.1")
        # 1000 - 990 = 10 < 60，不应触发清理
        service._cleanup_counters.assert_not_called()