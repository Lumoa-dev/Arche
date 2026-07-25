"""IP 封禁插件 单元测试。

覆盖范围：
- ip_matches_cidr() CIDR 匹配函数（IPv4/IPv6/边界情况）
- BloomFilter 布隆过滤器数据结构
- LRUSet LRU 缓存数据结构
- IpBanService 核心业务逻辑（CRUD、自动封禁规则、统计）
- IpBanMiddleware 中间件分发逻辑

所有测试使用纯 mock，不启动真实数据库。
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet, IpBanMiddleware
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# ip_matches_cidr 测试
# =============================================================================


class TestIpMatchesCIDR:
    """CIDR 匹配函数测试。"""

    def test_ipv4_exact_match(self):
        """IPv4 精确匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IPv4 在子网内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IPv4 不在子网内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv6_match(self):
        """IPv6 匹配。"""
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_ipv6_in_subnet(self):
        """IPv6 在子网内。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_invalid_ip_returns_false(self):
        """非法 IP 返回 False。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """非法 CIDR 返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_cidr_not_strict(self):
        """非严格 CIDR（网络位非全1）也能匹配。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.0/8") is True

    def test_empty_strings(self):
        """空字符串返回 False。"""
        assert ip_matches_cidr("", "") is False


# =============================================================================
# BloomFilter 测试
# =============================================================================


class TestBloomFilter:
    """布隆过滤器数据结构测试。"""

    def test_contains_after_add(self):
        """添加后应能检测到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains_before_add(self):
        """未添加的项不应被检测到。"""
        bf = BloomFilter(size=1000)
        assert bf.contains("10.0.0.1") is False

    def test_clear_removes_all(self):
        """清空后所有项应被移除。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.add("10.0.0.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False
        assert bf.contains("10.0.0.1") is False

    def test_false_positive_low_probability(self):
        """小规模测试误报率应较低。"""
        bf = BloomFilter(size=10000)
        # 添加 100 个 IP
        for i in range(100):
            bf.add(f"192.168.1.{i}")
        # 检查 100 个未添加的 IP
        false_positives = sum(
            1 for i in range(100, 200) if bf.contains(f"10.0.0.{i}")
        )
        # 误报率应低于 5%
        assert false_positives < 5

    def test_different_items_have_different_hashes(self):
        """不同项的哈希应不同。"""
        bf = BloomFilter(size=10000)
        bf.add("item_a")
        bf.add("item_b")
        assert bf.contains("item_a") is True
        assert bf.contains("item_b") is True


# =============================================================================
# LRUSet 测试
# =============================================================================


class TestLRUSet:
    """LRU 缓存集合测试。"""

    def test_add_and_contains(self):
        """添加后应能检测到。"""
        cache = LRUSet(maxsize=5)
        cache.add("192.168.1.1")
        assert cache.contains("192.168.1.1") is True

    def test_not_contains_before_add(self):
        """未添加的项应返回 False。"""
        cache = LRUSet(maxsize=5)
        assert cache.contains("10.0.0.1") is False

    def test_evicts_oldest_when_full(self):
        """超过 maxsize 时应淘汰最旧的项。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        cache.add("d")  # 应淘汰 "a"
        assert cache.contains("a") is False
        assert cache.contains("b") is True
        assert cache.contains("c") is True
        assert cache.contains("d") is True

    def test_recently_accessed_is_kept(self):
        """最近访问的项应被保持。"""
        cache = LRUSet(maxsize=3)
        cache.add("a")
        cache.add("b")
        cache.add("c")
        # 访问 "a"，使其成为最近使用的
        cache.contains("a")
        cache.add("d")  # 应淘汰 "b"（最旧的）
        assert cache.contains("a") is True
        assert cache.contains("b") is False

    def test_remove(self):
        """移除指定项。"""
        cache = LRUSet(maxsize=5)
        cache.add("a")
        cache.add("b")
        cache.remove("a")
        assert cache.contains("a") is False
        assert cache.contains("b") is True

    def test_remove_nonexistent(self):
        """移除不存在的项不应报错。"""
        cache = LRUSet(maxsize=5)
        cache.remove("nonexistent")  # 不应抛出异常

    def test_clear(self):
        """清空所有项。"""
        cache = LRUSet(maxsize=5)
        cache.add("a")
        cache.add("b")
        cache.clear()
        assert cache.contains("a") is False
        assert cache.contains("b") is False


# =============================================================================
# IpBanService 测试辅助
# =============================================================================


def _make_ip_ban_container():
    """创建支持 IpBanService 的轻量 mock container。"""
    container = MagicMock()

    class FakeConfig:
        _values = {  # noqa: RUF012
            "IP_BAN_WEBHOOK_URL": "",
        }

        def get(self, key, default=None):
            return self._values.get(key, default)

        def get_required(self, key):
            return self._values.get(key, "")

    # 构造 mock session
    mock_execute_result = MagicMock()
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.add = MagicMock()
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
def ip_ban_container():
    """每个测试用例独立的轻量 ip_ban container。"""
    return _make_ip_ban_container()


# =============================================================================
# IpBanService 测试 — CIDR 匹配和 IP 检查
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceCheck:
    """IP 检查功能测试。"""

    async def test_is_ip_banned_no_active_bans(self, ip_ban_container):
        """无活跃封禁时返回 False。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.scalars.return_value.all.return_value = []

        result = await service.is_ip_banned("192.168.1.1")
        assert result is False

    async def test_is_ip_banned_with_match(self, ip_ban_container):
        """IP 匹配活跃封禁时返回 True。"""
        service = IpBanService(ip_ban_container)
        mock_ban = MagicMock()
        mock_ban.ip_or_cidr = "192.168.1.0/24"
        ip_ban_container._mock_result.scalars.return_value.all.return_value = [
            mock_ban
        ]

        result = await service.is_ip_banned("192.168.1.100")
        assert result is True

    async def test_is_ip_banned_no_match(self, ip_ban_container):
        """IP 不匹配任何封禁时返回 False。"""
        service = IpBanService(ip_ban_container)
        mock_ban = MagicMock()
        mock_ban.ip_or_cidr = "10.0.0.0/8"
        ip_ban_container._mock_result.scalars.return_value.all.return_value = [
            mock_ban
        ]

        result = await service.is_ip_banned("192.168.1.1")
        assert result is False

    async def test_get_active_ip_ranges(self, ip_ban_container):
        """获取活跃 IP 段列表。"""
        service = IpBanService(ip_ban_container)
        mock_ban1 = MagicMock()
        mock_ban1.ip_or_cidr = "10.0.0.0/8"
        mock_ban2 = MagicMock()
        mock_ban2.ip_or_cidr = "192.168.1.1"
        ip_ban_container._mock_result.all.return_value = [
            (mock_ban1.ip_or_cidr,),
            (mock_ban2.ip_or_cidr,),
        ]

        result = await service.get_active_ip_ranges()
        assert result == ["10.0.0.0/8", "192.168.1.1"]


# =============================================================================
# IpBanService 测试 — 封禁管理 CRUD
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceCRUD:
    """封禁管理 CRUD 测试。"""

    async def test_ban_ip_new(self, ip_ban_container):
        """新封禁一个 IP。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None

        mock_ban = MagicMock()
        mock_ban.id = 1
        mock_ban.ip_or_cidr = "10.0.0.5"
        mock_ban.ban_type = "manual"
        mock_ban.reason = "test"
        mock_ban.rule_id = None
        mock_ban.banned_by = "admin"
        mock_ban.created_at = datetime.now(timezone.utc)
        mock_ban.expires_at = None
        mock_ban.is_active = True
        ip_ban_container._mock_session.refresh = AsyncMock(return_value=mock_ban)

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.5",
            reason="test",
            ban_type="manual",
            banned_by="admin",
        )

        assert result["ip_or_cidr"] == "10.0.0.5"
        assert result["ban_type"] == "manual"

    async def test_ban_ip_existing_updates(self, ip_ban_container):
        """封禁已存在的 IP 时更新记录。"""
        service = IpBanService(ip_ban_container)
        existing_ban = MagicMock()
        existing_ban.ip_or_cidr = "10.0.0.5"
        existing_ban.ban_type = "manual"
        existing_ban.reason = "old reason"
        existing_ban.is_active = True
        ip_ban_container._mock_result.scalar_one_or_none.return_value = existing_ban

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.5", reason="new reason"
        )

        assert existing_ban.reason == "new reason"
        ip_ban_container._mock_session.commit.assert_called_once()

    async def test_unban_ip_success(self, ip_ban_container):
        """解封一个封禁记录。"""
        service = IpBanService(ip_ban_container)
        mock_ban = MagicMock()
        mock_ban.id = 1
        mock_ban.ip_or_cidr = "10.0.0.5"
        mock_ban.ban_type = "manual"
        mock_ban.reason = "test"
        mock_ban.is_active = True
        ip_ban_container._mock_result.scalar_one_or_none.return_value = mock_ban

        result = await service.unban_ip(ban_id=1, operator="admin")

        assert mock_ban.is_active is False

    async def test_unban_ip_not_found(self, ip_ban_container):
        """解封不存在的记录应报错。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await service.unban_ip(ban_id=999)
        assert "封禁记录不存在" in str(excinfo.value)

    async def test_batch_unban(self, ip_ban_container):
        """批量解封。"""
        service = IpBanService(ip_ban_container)
        mock_ban1 = MagicMock()
        mock_ban1.id = 1
        mock_ban1.is_active = True
        mock_ban2 = MagicMock()
        mock_ban2.id = 2
        mock_ban2.is_active = True

        def scalar_one_or_none_side_effect():
            calls = []
            # 第一次调用返回 mock_ban1，第二次返回 mock_ban2
            if not hasattr(scalar_one_or_none_side_effect, "call_count"):
                scalar_one_or_none_side_effect.call_count = 0
            scalar_one_or_none_side_effect.call_count += 1
            if scalar_one_or_none_side_effect.call_count == 1:
                return mock_ban1
            return mock_ban2

        ip_ban_container._mock_result.scalar_one_or_none.side_effect = [
            mock_ban1,
            mock_ban2,
        ]

        count = await service.batch_unban(ban_ids=[1, 2], operator="admin")
        assert count == 2

    async def test_list_bans_pagination(self, ip_ban_container):
        """分页查询封禁列表。"""
        service = IpBanService(ip_ban_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        ban_result = MagicMock()
        mock_ban = MagicMock()
        mock_ban.id = 1
        mock_ban.ip_or_cidr = "10.0.0.5"
        mock_ban.ban_type = "manual"
        mock_ban.reason = "test"
        mock_ban.rule_id = None
        mock_ban.banned_by = "admin"
        mock_ban.created_at = datetime.now(timezone.utc)
        mock_ban.expires_at = None
        mock_ban.is_active = True
        ban_result.scalars.return_value.all.return_value = [mock_ban]

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, ban_result]
        )
        ip_ban_container._mock_result = count_result

        result = await service.list_bans(page=1, page_size=20)
        assert result["total"] == 1
        assert len(result["list"]) == 1

    async def test_get_ban_logs(self, ip_ban_container):
        """查询封禁操作日志。"""
        service = IpBanService(ip_ban_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        log_result = MagicMock()
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
        log_result.scalars.return_value.all.return_value = [mock_log]

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, log_result]
        )
        ip_ban_container._mock_result = count_result

        result = await service.get_ban_logs(page=1, page_size=20)
        assert result["total"] == 1
        assert len(result["list"]) == 1
        assert result["list"][0]["action"] == "ban"

    async def test_get_stats(self, ip_ban_container):
        """获取封禁统计。"""
        service = IpBanService(ip_ban_container)

        # 需要 6 个 count 查询结果
        results = []
        for val in [10, 3, 5, 2, 1, 0]:
            r = MagicMock()
            r.scalar_one.return_value = val
            results.append(r)

        ip_ban_container._mock_session.execute = AsyncMock(side_effect=results)
        ip_ban_container._mock_result = results[0]

        stats = await service.get_stats()
        assert stats["total_bans"] == 10
        assert stats["active_bans"] == 3
        assert stats["auto_bans"] == 5
        assert stats["manual_bans"] == 2
        assert stats["today_bans"] == 1


# =============================================================================
# IpBanService 测试 — 自动封禁规则引擎
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceAutoBan:
    """自动封禁规则引擎测试。"""

    async def test_record_event_login_failure_triggers_ban(
        self, ip_ban_container
    ):
        """登录失败达到阈值触发自动封禁。"""
        service = IpBanService(ip_ban_container)

        # mock get_rule_configs 返回 login_failure 规则
        mock_rule = {
            "id": "login_failure",
            "enabled": True,
            "threshold": 3,
            "window_seconds": 300,
            "ban_duration_minutes": 30,
            "name": "登录失败封禁",
            "description": "",
        }
        with patch.object(
            service, "get_rule_configs", return_value=[mock_rule]
        ):
            with patch.object(service, "ban_ip", AsyncMock()) as mock_ban:
                for _ in range(5):
                    await service.record_event(
                        "login_failure", "10.0.0.5", 401
                    )
                mock_ban.assert_called()
                # ban_ip 使用关键字参数调用
                _, kwargs = mock_ban.call_args
                assert kwargs.get("ip_or_cidr") == "10.0.0.5"
                assert kwargs.get("rule_id") == "login_failure"

    async def test_record_event_rate_limit_triggers_ban(
        self, ip_ban_container
    ):
        """请求频率达到阈值触发自动封禁。"""
        service = IpBanService(ip_ban_container)

        mock_rule = {
            "id": "rate_limit",
            "enabled": True,
            "threshold": 5,
            "window_seconds": 60,
            "ban_duration_minutes": 10,
            "name": "请求频率封禁",
            "description": "",
        }
        with patch.object(service, "get_rule_configs", return_value=[mock_rule]
        ):
            with patch.object(service, "ban_ip", AsyncMock()) as mock_ban:
                for _ in range(6):
                    await service.record_event(
                        "rate_limit", "10.0.0.5"
                    )
                mock_ban.assert_called()

    async def test_record_event_high_4xx_triggers_ban(
        self, ip_ban_container
    ):
        """4xx 高频达到阈值触发自动封禁。"""
        service = IpBanService(ip_ban_container)

        mock_rule = {
            "id": "high_4xx",
            "enabled": True,
            "threshold": 3,
            "window_seconds": 3600,
            "ban_duration_minutes": 60,
            "name": "4xx 高频封禁",
            "description": "",
        }
        with patch.object(
            service, "get_rule_configs", return_value=[mock_rule]
        ):
            with patch.object(service, "ban_ip", AsyncMock()) as mock_ban:
                for _ in range(4):
                    await service.record_event(
                        "high_4xx", "10.0.0.5", 404
                    )
                mock_ban.assert_called()

    async def test_disabled_rule_does_not_trigger(self, ip_ban_container):
        """禁用的规则不应触发自动封禁。"""
        service = IpBanService(ip_ban_container)

        mock_rule = {
            "id": "login_failure",
            "enabled": False,
            "threshold": 3,
            "window_seconds": 300,
            "ban_duration_minutes": 30,
            "name": "登录失败封禁",
            "description": "",
        }
        with patch.object(
            service, "get_rule_configs", return_value=[mock_rule]
        ):
            with patch.object(service, "ban_ip", AsyncMock()) as mock_ban:
                for _ in range(5):
                    await service.record_event(
                        "login_failure", "10.0.0.5", 401
                    )
                mock_ban.assert_not_called()

    async def test_cleanup_counters_expired_entries(self, ip_ban_container):
        """过期计数器应被清理。"""
        service = IpBanService(ip_ban_container)

        # 添加一个旧的计数器条目
        old_time = time.time() - 7200  # 2 小时前
        service._counters["login_failure:10.0.0.5"] = [
            (old_time, 401)
        ]

        service._cleanup_counters()
        assert "login_failure:10.0.0.5" not in service._counters

    async def test_get_rule_configs_returns_defaults(self, ip_ban_container):
        """获取规则配置时返回默认规则。"""
        service = IpBanService(ip_ban_container)

        # mock 查询返回空列表（无 DB 规则）
        ip_ban_container._mock_result.scalars.return_value.all.return_value = []

        rules = await service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    async def test_update_rule_config(self, ip_ban_container):
        """更新规则配置。"""
        service = IpBanService(ip_ban_container)

        mock_rule = MagicMock()
        mock_rule.id = "login_failure"
        mock_rule.name = "登录失败封禁"
        mock_rule.enabled = True
        mock_rule.threshold = 10
        mock_rule.window_seconds = 300
        mock_rule.ban_duration_minutes = 30
        mock_rule.description = ""

        ip_ban_container._mock_result.scalar_one_or_none.return_value = mock_rule

        result = await service.update_rule_config(
            "login_failure", {"threshold": 5}
        )
        assert mock_rule.threshold == 5

    async def test_update_rule_config_not_found(self, ip_ban_container):
        """更新不存在的规则应报错。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as excinfo:
            await service.update_rule_config(
                "nonexistent", {"threshold": 5}
            )
        assert "规则不存在" in str(excinfo.value)


# =============================================================================
# IpBanMiddleware 测试
# =============================================================================


class TestIpBanMiddleware:
    """IP 封禁中间件测试。"""

    def test_public_paths_bypass(self):
        """公开路径应跳过封禁检查。"""
        assert "/api/auth/register" in IpBanMiddleware.PUBLIC_PATHS
        assert "/api/auth/login" in IpBanMiddleware.PUBLIC_PATHS

    def test_bloom_filter_reload_clears_cache(self):
        """reload_cache 应清空布隆过滤器和 LRU 缓存。"""
        middleware = IpBanMiddleware.__new__(IpBanMiddleware)
        middleware._bloom = BloomFilter(size=1000)
        middleware._whitelist_cache = LRUSet(maxsize=100)
        middleware._last_sync = 0.0

        # 添加一些数据
        middleware._bloom.add("10.0.0.1")
        middleware._whitelist_cache.add("10.0.0.1")

        mock_service = MagicMock()
        mock_service.get_active_ip_ranges = AsyncMock(return_value=["10.0.0.0/8"])

        import asyncio
        asyncio.run(middleware.reload_cache(mock_service))

        # reload 后布隆过滤器应被清空，然后加入活跃 IP
        assert middleware._bloom.contains("10.0.0.1") is False
        # 注意：reload_cache 会添加活跃 IP 到布隆过滤器
        # 但这里 mock_service 返回的是 "10.0.0.0/8"，不是具体 IP
        # 所以布隆过滤器里应该有 "10.0.0.0/8"
        assert middleware._bloom.contains("10.0.0.0/8") is True
        # LRU 缓存应被完全清空
        assert middleware._whitelist_cache.contains("10.0.0.1") is False


# =============================================================================
# IpBanService 测试 — 封禁管理（含 duration）
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceBanWithDuration:
    """带有效期的封禁测试。"""

    async def test_ban_ip_with_duration(self, ip_ban_container):
        """封禁时设置有效期。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None

        mock_ban = MagicMock()
        mock_ban.id = 1
        mock_ban.ip_or_cidr = "10.0.0.5"
        mock_ban.ban_type = "manual"
        mock_ban.reason = "test"
        mock_ban.rule_id = None
        mock_ban.banned_by = "admin"
        mock_ban.created_at = datetime.now(timezone.utc)
        mock_ban.expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        mock_ban.is_active = True
        ip_ban_container._mock_session.refresh = AsyncMock(return_value=mock_ban)

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.5",
            reason="test",
            banned_by="admin",
            duration_minutes=30,
        )

        assert result["ip_or_cidr"] == "10.0.0.5"

    async def test_ban_ip_zero_duration_is_permanent(self, ip_ban_container):
        """duration_minutes=0 表示永久封禁（不设置 expires_at）。"""
        service = IpBanService(ip_ban_container)
        ip_ban_container._mock_result.scalar_one_or_none.return_value = None

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.5",
            reason="permanent",
            banned_by="admin",
            duration_minutes=0,
        )

        assert result["ip_or_cidr"] == "10.0.0.5"
        assert result["reason"] == "permanent"


# =============================================================================
# IpBanService 测试 — 列表查询过滤
# =============================================================================


@pytest.mark.asyncio
class TestIpBanServiceListFilter:
    """封禁列表过滤测试。"""

    async def test_list_bans_filter_by_type(self, ip_ban_container):
        """按封禁类型过滤。"""
        service = IpBanService(ip_ban_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        ban_result = MagicMock()
        ban_result.scalars.return_value.all.return_value = []

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, ban_result]
        )
        ip_ban_container._mock_result = count_result

        result = await service.list_bans(ban_type="auto")
        assert result["total"] == 0

    async def test_list_bans_filter_by_keyword(self, ip_ban_container):
        """按关键词过滤。"""
        service = IpBanService(ip_ban_container)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        ban_result = MagicMock()
        ban_result.scalars.return_value.all.return_value = []

        ip_ban_container._mock_session.execute = AsyncMock(
            side_effect=[count_result, ban_result]
        )
        ip_ban_container._mock_result = count_result

        result = await service.list_bans(keyword="192.168")
        assert result["total"] == 0