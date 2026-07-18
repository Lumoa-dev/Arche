"""IpBanService 行为测试。

使用真实内存数据库 + mock 容器，覆盖：
- 封禁/解封 CRUD
- IP 存在性检查
- 自动封禁规则引擎
- 统计信息
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService


# =============================================================================
# Fixture
# =============================================================================


@pytest_asyncio.fixture
async def ip_ban_service(db_container):
    """创建带真实内存数据库的 IpBanService。"""
    # 重写 db_container 的 get 使 ip_ban 返回真实服务
    from backend.plugins.ip_ban.services import IpBanService as RealService

    real_service = RealService(db_container)
    old_get = db_container.get

    def _get(name):
        if name == "ip_ban":
            return real_service
        return old_get(name)

    db_container.get = _get
    return real_service


# =============================================================================
# 封禁/解封 CRUD 测试
# =============================================================================


class TestBanUnban:
    """封禁和解封行为测试。"""

    @pytest.mark.asyncio
    async def test_ban_ip_creates_record(self, ip_ban_service):
        """封禁 IP 应创建记录并返回正确的数据结构。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
            banned_by="admin",
        )
        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["reason"] == "测试封禁"
        assert result["banned_by"] == "admin"
        assert result["is_active"] is True
        assert "id" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_ban_ip_with_duration(self, ip_ban_service):
        """封禁时指定时长应设置 expires_at。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            duration_minutes=30,
            banned_by="admin",
        )
        assert result["expires_at"] is not None
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_ip_permanent(self, ip_ban_service):
        """不指定时长应为永久封禁（expires_at 为 None）。"""
        result = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="永久封禁",
            banned_by="admin",
            duration_minutes=None,
        )
        assert result["expires_at"] is None
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_ip_duplicate_returns_existing(self, ip_ban_service):
        """重复封禁同一 IP 应返回已有记录并更新。"""
        result1 = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="首次封禁",
            banned_by="admin",
            duration_minutes=30,
        )
        result2 = await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="更新封禁",
            banned_by="admin",
            duration_minutes=60,
        )
        assert result2["id"] == result1["id"]
        # 原有记录被更新
        assert result2["reason"] == "更新封禁"

    @pytest.mark.asyncio
    async def test_ban_ip_logs_operation(self, ip_ban_service):
        """封禁操作应记录日志。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.10",
            reason="测试日志",
            banned_by="admin",
        )
        logs = await ip_ban_service.get_ban_logs()
        assert logs["total"] >= 1
        assert logs["list"][0]["action"] == "ban"
        assert logs["list"][0]["ip_or_cidr"] == "10.0.0.10"

    @pytest.mark.asyncio
    async def test_unban_ip_deactivates_record(self, ip_ban_service):
        """解封应将 is_active 设为 False。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.20",
            reason="待解封",
            banned_by="admin",
        )
        result = await ip_ban_service.unban_ip(ban["id"], operator="admin")
        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_ip_not_found_raises_error(self, ip_ban_service):
        """解封不存在的记录应抛出 404。"""
        with pytest.raises(AppError) as excinfo:
            await ip_ban_service.unban_ip(99999, operator="admin")
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "ban_not_found"

    @pytest.mark.asyncio
    async def test_unban_ip_logs_operation(self, ip_ban_service):
        """解封操作应记录日志。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.30",
            reason="解封测试",
            banned_by="admin",
        )
        await ip_ban_service.unban_ip(ban["id"], operator="admin")
        logs = await ip_ban_service.get_ban_logs(action="unban")
        assert logs["total"] >= 1

    @pytest.mark.asyncio
    async def test_batch_unban_multiple(self, ip_ban_service):
        """批量解封应正确解封多个记录。"""
        ids = []
        for i in range(3):
            ban = await ip_ban_service.ban_ip(
                ip_or_cidr=f"10.0.0.{100 + i}",
                reason="批量测试",
                banned_by="admin",
            )
            ids.append(ban["id"])
        count = await ip_ban_service.batch_unban(ids, operator="admin")
        assert count == 3

    @pytest.mark.asyncio
    async def test_batch_unban_mixed_active_inactive(self, ip_ban_service):
        """批量解封应只解封活跃记录。"""
        ban1 = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.200", reason="测试1", banned_by="admin"
        )
        ban2 = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.201", reason="测试2", banned_by="admin"
        )
        # 先解封第一个
        await ip_ban_service.unban_ip(ban1["id"], operator="admin")
        # 批量解封所有
        count = await ip_ban_service.batch_unban(
            [ban1["id"], ban2["id"]], operator="admin"
        )
        assert count == 1  # 只有 ban2 是活跃的


# =============================================================================
# IP 检查测试
# =============================================================================


class TestIpCheck:
    """IP 封禁检查行为测试。"""

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_true_for_banned_ip(self, ip_ban_service):
        """被封禁的 IP 应返回 True。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试",
            banned_by="admin",
        )
        assert await ip_ban_service.is_ip_banned("192.168.1.1") is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_for_free_ip(self, ip_ban_service):
        """未被封禁的 IP 应返回 False。"""
        assert await ip_ban_service.is_ip_banned("10.0.0.99") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_cidr_range(self, ip_ban_service):
        """CIDR 段封禁应匹配段内所有 IP。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.0/24",
            reason="封禁整个段",
            banned_by="admin",
        )
        assert await ip_ban_service.is_ip_banned("10.0.0.1") is True
        assert await ip_ban_service.is_ip_banned("10.0.0.255") is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_cidr_outside_range(self, ip_ban_service):
        """CIDR 段外的 IP 不应被匹配。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.0/24",
            reason="封禁整个段",
            banned_by="admin",
        )
        assert await ip_ban_service.is_ip_banned("10.0.1.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_after_unban(self, ip_ban_service):
        """解封后 IP 应不再被标记为封禁。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.50",
            reason="临时封禁",
            banned_by="admin",
        )
        await ip_ban_service.unban_ip(ban["id"], operator="admin")
        assert await ip_ban_service.is_ip_banned("10.0.0.50") is False

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, ip_ban_service):
        """获取活跃 IP 范围列表。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.0/24",
            reason="段封禁",
            banned_by="admin",
        )
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="单 IP",
            banned_by="admin",
        )
        ranges = await ip_ban_service.get_active_ip_ranges()
        assert "10.0.0.0/24" in ranges
        assert "192.168.1.1" in ranges


# =============================================================================
# 列表查询测试
# =============================================================================


class TestListBans:
    """封禁列表查询行为测试。"""

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, ip_ban_service):
        """分页查询应正确工作。"""
        for i in range(5):
            await ip_ban_service.ban_ip(
                ip_or_cidr=f"10.0.0.{i}",
                reason=f"测试{i}",
                banned_by="admin",
            )
        result = await ip_ban_service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, ip_ban_service):
        """按封禁类型筛选应正确。"""
        # 一个手动封禁
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="手动",
            ban_type="manual",
            banned_by="admin",
        )
        # 一个自动封禁（直接调用 ban_ip 模拟）
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="自动",
            ban_type="auto",
            rule_id="rate_limit",
            banned_by="system",
        )
        manual = await ip_ban_service.list_bans(ban_type="manual")
        auto = await ip_ban_service.list_bans(ban_type="auto")
        assert manual["total"] >= 1
        assert auto["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_active(self, ip_ban_service):
        """按活跃状态筛选应正确。"""
        # 创建两个封禁，然后解封其中一个
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.10",
            reason="活跃封禁",
            banned_by="admin",
        )
        ban2 = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.11",
            reason="已解封",
            banned_by="admin",
        )
        await ip_ban_service.unban_ip(ban2["id"], operator="admin")
        active = await ip_ban_service.list_bans(is_active=True)
        inactive = await ip_ban_service.list_bans(is_active=False)
        assert len(active["list"]) > 0
        assert len(inactive["list"]) > 0

    @pytest.mark.asyncio
    async def test_list_bans_search_by_keyword(self, ip_ban_service):
        """按关键词搜索应正确。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试",
            banned_by="admin",
        )
        result = await ip_ban_service.list_bans(keyword="192.168")
        assert result["total"] >= 1
        result_no_match = await ip_ban_service.list_bans(keyword="no-match")
        assert result_no_match["total"] == 0


# =============================================================================
# 统计测试
# =============================================================================


class TestStats:
    """封禁统计行为测试。"""

    @pytest.mark.asyncio
    async def test_get_stats_returns_correct_counts(self, ip_ban_service):
        """统计信息应返回正确的计数。"""
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="手动",
            ban_type="manual",
            banned_by="admin",
        )
        await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="自动",
            ban_type="auto",
            rule_id="rate_limit",
            banned_by="system",
        )
        stats = await ip_ban_service.get_stats()
        assert stats["total_bans"] >= 2
        assert stats["manual_bans"] >= 1
        assert stats["auto_bans"] >= 1
        assert stats["active_bans"] >= 2

    @pytest.mark.asyncio
    async def test_get_stats_after_unban(self, ip_ban_service):
        """解封后活跃计数应减少。"""
        ban = await ip_ban_service.ban_ip(
            ip_or_cidr="10.0.0.50",
            reason="测试",
            banned_by="admin",
        )
        stats_before = await ip_ban_service.get_stats()
        await ip_ban_service.unban_ip(ban["id"], operator="admin")
        stats_after = await ip_ban_service.get_stats()
        assert stats_after["active_bans"] < stats_before["active_bans"]


# =============================================================================
# 自动封禁规则引擎测试
# =============================================================================


class TestAutoBanRuleEngine:
    """自动封禁规则引擎行为测试。"""

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, ip_ban_service):
        """获取规则配置应返回默认规则。"""
        rules = await ip_ban_service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

    @pytest.mark.asyncio
    async def test_update_rule_config(self, ip_ban_service):
        """更新规则配置应生效。"""
        # 先调用 get_rule_configs 确保默认规则已入库
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 5, "enabled": False}
        )
        rules = await ip_ban_service.get_rule_configs()
        rule = next(r for r in rules if r["id"] == "login_failure")
        assert rule["threshold"] == 5
        assert rule["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_non_existent_rule_raises_error(self, ip_ban_service):
        """更新不存在的规则应抛出 404。"""
        with pytest.raises(AppError) as excinfo:
            await ip_ban_service.update_rule_config(
                "non_existent", {"threshold": 5}
            )
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "rule_not_found"

    @pytest.mark.asyncio
    async def test_record_event_login_failure_triggers_ban(self, ip_ban_service):
        """登录失败事件达到阈值应触发自动封禁。"""
        # 先调用 get_rule_configs 确保默认规则已入库
        await ip_ban_service.get_rule_configs()
        # 设置低阈值以触发规则
        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 3, "ban_duration_minutes": 10}
        )
        # 模拟 3 次登录失败
        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="login_failure", ip_str="10.0.0.100", status_code=401
            )
        # 检查 IP 是否被封禁
        is_banned = await ip_ban_service.is_ip_banned("10.0.0.100")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_below_threshold_no_ban(self, ip_ban_service):
        """登录失败未达阈值不应触发封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 5, "ban_duration_minutes": 10}
        )
        # 只模拟 2 次失败（低于阈值 5）
        for _ in range(2):
            await ip_ban_service.record_event(
                event_type="login_failure", ip_str="10.0.0.101", status_code=401
            )
        is_banned = await ip_ban_service.is_ip_banned("10.0.0.101")
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_record_event_rate_limit_triggers_ban(self, ip_ban_service):
        """请求频率事件达到阈值应触发自动封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "rate_limit", {"threshold": 3, "ban_duration_minutes": 5}
        )
        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="rate_limit", ip_str="10.0.0.200"
            )
        is_banned = await ip_ban_service.is_ip_banned("10.0.0.200")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_disabled_rule_no_ban(self, ip_ban_service):
        """禁用的规则不应触发封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "login_failure", {"threshold": 1, "enabled": False}
        )
        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="login_failure", ip_str="10.0.0.102", status_code=401
            )
        is_banned = await ip_ban_service.is_ip_banned("10.0.0.102")
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_record_event_high_4xx_triggers_ban(self, ip_ban_service):
        """高频 4xx 事件达到阈值应触发自动封禁。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "high_4xx", {"threshold": 3, "ban_duration_minutes": 10}
        )
        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="high_4xx", ip_str="10.0.0.103", status_code=404
            )
        is_banned = await ip_ban_service.is_ip_banned("10.0.0.103")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_high_4xx_ignores_5xx(self, ip_ban_service):
        """高频 4xx 事件应忽略 5xx 状态码。"""
        await ip_ban_service.get_rule_configs()
        await ip_ban_service.update_rule_config(
            "high_4xx", {"threshold": 2, "ban_duration_minutes": 10}
        )
        # 3 次 5xx 不应触发 4xx 规则
        for _ in range(3):
            await ip_ban_service.record_event(
                event_type="high_4xx", ip_str="10.0.0.104", status_code=500
            )
        is_banned = await ip_ban_service.is_ip_banned("10.0.0.104")
        assert is_banned is False