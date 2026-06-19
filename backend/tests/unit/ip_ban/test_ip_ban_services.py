"""IpBanService 行为测试。

测试原则：
- 只测公开方法输入输出，不测内部实现
- 用内存数据库做真实交互
- 每个测试独立，不依赖执行顺序
- auto-ban 规则测试通过计数器直接触发，不依赖真实时间
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr

# =============================================================================
# ip_matches_cidr 单元测试（纯函数，无需 DB）
# =============================================================================


class TestIpMatchesCidr:
    """测试 IP 与 CIDR 段匹配逻辑。"""

    @pytest.mark.parametrize(
        "ip_str, cidr_str, expected",
        [
            ("192.168.1.1", "192.168.1.0/24", True),
            ("192.168.2.1", "192.168.1.0/24", False),
            ("10.0.0.5", "10.0.0.0/8", True),
            ("11.0.0.5", "10.0.0.0/8", False),
            ("::1", "::1/128", True),
            ("::2", "::1/128", False),
            ("invalid", "192.168.1.0/24", False),
            ("192.168.1.1", "invalid_cidr", False),
            ("192.168.1.100", "192.168.1.100/32", True),
            ("192.168.1.101", "192.168.1.100/32", False),
        ],
    )
    def test_ip_matches_cidr(self, ip_str, cidr_str, expected):
        assert ip_matches_cidr(ip_str, cidr_str) == expected


# =============================================================================
# 辅助方法：创建 IpBanService 实例
# =============================================================================


def _make_ip_ban_service(container) -> IpBanService:
    """创建 IpBanService，使用 db_container 中的真实 DB。"""
    return IpBanService(container)


# =============================================================================
# 封禁/解封操作测试
# =============================================================================


class TestBanOperations:
    """测试封禁和解封操作。"""

    @pytest.mark.asyncio
    async def test_ban_ip_success(self, db_container):
        """手动封禁单个 IP 应成功返回封禁记录。"""
        service = _make_ip_ban_service(db_container)
        result = await service.ban_ip(
            "192.168.1.100",
            reason="恶意攻击",
            ban_type="manual",
            banned_by="admin",
        )

        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["reason"] == "恶意攻击"
        assert result["ban_type"] == "manual"
        assert result["banned_by"] == "admin"
        assert result["is_active"] is True
        assert result["expires_at"] is None  # 永久封禁
        assert "id" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_ban_ip_with_expiry(self, db_container):
        """带过期时间的封禁应设置 expires_at。"""
        service = _make_ip_ban_service(db_container)
        result = await service.ban_ip(
            "10.0.0.1",
            reason="临时封禁",
            ban_type="manual",
            duration_minutes=60,
        )

        assert result["ip_or_cidr"] == "10.0.0.1"
        assert result["expires_at"] is not None
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_cidr_success(self, db_container):
        """封禁 CIDR 段应成功。"""
        service = _make_ip_ban_service(db_container)
        result = await service.ban_ip(
            "10.0.0.0/24",
            reason="封禁 IP 段",
            ban_type="manual",
        )

        assert result["ip_or_cidr"] == "10.0.0.0/24"
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_duplicate_ip_updates_existing(self, db_container):
        """重复封禁相同 IP 应更新已有记录的过期时间和原因。"""
        service = _make_ip_ban_service(db_container)
        # 第一次封禁（永久）
        first = await service.ban_ip("192.168.1.1", reason="首次", ban_type="manual")
        first_id = first["id"]

        # 第二次封禁（带过期时间+新原因）
        second = await service.ban_ip(
            "192.168.1.1",
            reason="更新原因",
            ban_type="manual",
            duration_minutes=30,
        )

        assert second["id"] == first_id  # 同一记录
        assert second["reason"] == "更新原因"
        assert second["expires_at"] is not None  # 现已过期
        assert second["is_active"] is True

    @pytest.mark.asyncio
    async def test_ban_creates_log_entry(self, db_container):
        """封禁操作应生成一条操作日志。"""

        service = _make_ip_ban_service(db_container)
        await service.ban_ip(
            "10.0.0.5",
            reason="测试日志",
            ban_type="auto",
            banned_by="system",
            duration_minutes=15,
        )

        # 查询日志
        logs_result = await service.get_ban_logs(action="ban")
        assert logs_result["total"] >= 1
        log = logs_result["list"][0]
        assert log["action"] == "ban"
        assert log["ip_or_cidr"] == "10.0.0.5"
        assert log["reason"] == "测试日志"
        assert log["operator"] == "system"
        assert "15分钟" in (log["detail"] or "")

    @pytest.mark.asyncio
    async def test_unban_ip_success(self, db_container):
        """解封有效封禁记录应成功。"""
        service = _make_ip_ban_service(db_container)
        ban = await service.ban_ip("10.0.0.10", reason="测试", ban_type="manual")

        result = await service.unban_ip(ban["id"], operator="admin")
        assert result["is_active"] is False
        assert result["id"] == ban["id"]

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, db_container):
        """解封不存在的记录应抛出错误。"""
        service = _make_ip_ban_service(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(99999, operator="admin")
        assert excinfo.value.code == "ban_not_found"
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_unban_creates_log_entry(self, db_container):
        """解封操作应生成一条解封日志。"""
        service = _make_ip_ban_service(db_container)
        ban = await service.ban_ip("10.0.0.15", reason="测试", ban_type="manual")
        await service.unban_ip(ban["id"], operator="moderator")

        logs = await service.get_ban_logs(action="unban")
        assert logs["total"] >= 1
        log = logs["list"][0]
        assert log["action"] == "unban"
        assert log["operator"] == "moderator"

    @pytest.mark.asyncio
    async def test_batch_unban_multiple_ids(self, db_container):
        """批量解封应返回解封数量。"""
        service = _make_ip_ban_service(db_container)
        ban1 = await service.ban_ip("10.0.0.20", reason="测试1", ban_type="manual")
        ban2 = await service.ban_ip("10.0.0.21", reason="测试2", ban_type="manual")
        ban3 = await service.ban_ip("10.0.0.22", reason="测试3", ban_type="manual")

        count = await service.batch_unban([ban1["id"], ban2["id"], ban3["id"]], operator="admin")
        assert count == 3

        # 验证均已被解封：检查封禁列表
        bans = await service.list_bans(is_active=False)
        assert bans["total"] >= 3
        unban_logs = await service.get_ban_logs(action="unban")
        assert unban_logs["total"] >= 3

    @pytest.mark.asyncio
    async def test_batch_unban_partial_invalid(self, db_container):
        """批量解封包含不存在的 ID 应只解封有效的记录。"""
        service = _make_ip_ban_service(db_container)
        ban = await service.ban_ip("10.0.0.25", reason="测试", ban_type="manual")

        count = await service.batch_unban([ban["id"], 99999], operator="admin")
        assert count == 1  # 只有有效的那个被解封


# =============================================================================
# IP 检查测试
# =============================================================================


class TestIpCheck:
    """测试 IP 封禁检查逻辑。"""

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_true_for_banned_ip(self, db_container):
        """被封禁的 IP 应返回 True。"""
        service = _make_ip_ban_service(db_container)
        await service.ban_ip("10.0.1.50", reason="测试", ban_type="manual")
        assert await service.is_ip_banned("10.0.1.50") is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_for_unknown_ip(self, db_container):
        """未封禁的 IP 应返回 False。"""
        service = _make_ip_ban_service(db_container)
        assert await service.is_ip_banned("192.168.100.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_matches_cidr_range(self, db_container):
        """IP 在封禁的 CIDR 段内应返回 True。"""
        service = _make_ip_ban_service(db_container)
        await service.ban_ip("10.10.0.0/16", reason="封禁段", ban_type="manual")
        assert await service.is_ip_banned("10.10.1.100") is True
        assert await service.is_ip_banned("10.20.1.100") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_after_unban(self, db_container):
        """解封后 IP 不应再被封禁。"""
        service = _make_ip_ban_service(db_container)
        ban = await service.ban_ip("10.0.2.50", reason="测试", ban_type="manual")
        await service.unban_ip(ban["id"])
        assert await service.is_ip_banned("10.0.2.50") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_returns_false_for_expired_ban(self, db_container):
        """过期的封禁记录不应生效。"""
        service = _make_ip_ban_service(db_container)
        # 创建一个已过期的封禁
        from sqlalchemy import select

        from backend.plugins.ip_ban.models import IpBan

        await service.ban_ip(
            "10.0.3.50",
            reason="短时封禁",
            ban_type="auto",
            duration_minutes=0,  # 0 分钟 = 立即过期
        )

        # 手动将 expires_at 设置为过去
        async with db_container.get("db")["session_factory"]() as session:
            result = await session.execute(
                select(IpBan).where(IpBan.ip_or_cidr == "10.0.3.50")
            )
            ban = result.scalar_one()
            ban.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        assert await service.is_ip_banned("10.0.3.50") is False

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges_returns_only_active(self, db_container):
        """get_active_ip_ranges 应只返回活跃的封禁范围。"""
        service = _make_ip_ban_service(db_container)
        await service.ban_ip("10.0.4.0/24", reason="活跃段", ban_type="manual")
        ban2 = await service.ban_ip("10.0.5.0/24", reason="将解封", ban_type="manual")
        await service.unban_ip(ban2["id"])

        ranges = await service.get_active_ip_ranges()
        assert "10.0.4.0/24" in ranges
        assert "10.0.5.0/24" not in ranges


# =============================================================================
# 列表查询测试
# =============================================================================


class TestListQueries:
    """测试分页列表查询功能。"""

    @pytest.fixture
    async def sample_bans(self, db_container):
        """创建一批测试封禁记录。"""
        service = _make_ip_ban_service(db_container)
        bans = []
        for i in range(5):
            ban = await service.ban_ip(
                f"10.0.{i}.1", reason=f"测试{i}", ban_type="manual"
            )
            bans.append(ban)
        return bans

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, db_container, sample_bans):
        """分页查询应正确返回。"""
        service = _make_ip_ban_service(db_container)
        page1 = await service.list_bans(page=1, page_size=2)
        assert len(page1["list"]) == 2
        assert page1["total"] == 5
        assert page1["page"] == 1
        assert page1["page_size"] == 2

        page2 = await service.list_bans(page=3, page_size=2)
        assert len(page2["list"]) == 1

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, db_container, sample_bans):
        """按封禁类型筛选应正确。"""
        service = _make_ip_ban_service(db_container)
        await service.ban_ip(
            "10.0.99.1", reason="自动封禁", ban_type="auto", rule_id="rate_limit"
        )

        result = await service.list_bans(ban_type="auto")
        assert result["total"] == 1

        result = await service.list_bans(ban_type="manual")
        assert result["total"] == 5

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_keyword(self, db_container, sample_bans):
        """按 IP 关键字筛选应正确。"""
        service = _make_ip_ban_service(db_container)
        # 再添加一条便于搜索
        await service.ban_ip("172.16.0.1", reason="特殊", ban_type="manual")

        result = await service.list_bans(keyword="172.16")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "172.16.0.1"

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_active(self, db_container, sample_bans):
        """按活跃状态筛选应正确。"""
        service = _make_ip_ban_service(db_container)
        ban = sample_bans[0]
        await service.unban_ip(ban["id"])

        active = await service.list_bans(is_active=True)
        assert active["total"] == 4

        inactive = await service.list_bans(is_active=False)
        assert inactive["total"] == 1

    @pytest.mark.asyncio
    async def test_get_ban_logs_pagination(self, db_container, sample_bans):
        """操作日志分页查询应正确。"""
        service = _make_ip_ban_service(db_container)
        # 解封一个生成日志
        await service.unban_ip(sample_bans[0]["id"], operator="admin")

        logs = await service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] >= 1
        assert logs["page"] == 1

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_by_action(self, db_container, sample_bans):
        """按操作类型筛选日志应正确。"""
        service = _make_ip_ban_service(db_container)
        await service.unban_ip(sample_bans[0]["id"], operator="admin")

        ban_logs = await service.get_ban_logs(action="ban")
        assert ban_logs["total"] >= 5  # 5 条封禁日志

        unban_logs = await service.get_ban_logs(action="unban")
        assert unban_logs["total"] >= 1


# =============================================================================
# 统计测试
# =============================================================================


class TestStats:
    """测试封禁统计功能。"""

    @pytest.mark.asyncio
    async def test_get_stats_returns_correct_counts(self, db_container):
        """统计应返回正确的计数。"""
        service = _make_ip_ban_service(db_container)
        await service.ban_ip("10.0.1.1", reason="手动", ban_type="manual")
        await service.ban_ip("10.0.1.2", reason="自动", ban_type="auto", rule_id="rate_limit")
        await service.ban_ip("10.0.1.3", reason="自动", ban_type="auto", rule_id="login_failure")

        stats = await service.get_stats()
        assert stats["total_bans"] == 3
        assert stats["auto_bans"] == 2
        assert stats["manual_bans"] == 1
        assert stats["active_bans"] == 3
        assert stats["today_bans"] >= 3


# =============================================================================
# 自动封禁规则配置测试
# =============================================================================


class TestAutoBanRules:
    """测试自动封禁规则配置管理。"""

    @pytest.mark.asyncio
    async def test_get_rule_configs_returns_defaults(self, db_container):
        """首次查询应返回默认规则（自动填充到 DB）。"""
        service = _make_ip_ban_service(db_container)
        rules = await service.get_rule_configs()
        rule_ids = {r["id"] for r in rules}
        assert "login_failure" in rule_ids
        assert "high_4xx" in rule_ids
        assert "rate_limit" in rule_ids
        assert "geo_surge" in rule_ids

        # 验证阈值
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 10
        assert login_rule["window_seconds"] == 300
        assert login_rule["ban_duration_minutes"] == 30

    @pytest.mark.asyncio
    async def test_update_rule_config_success(self, db_container):
        """更新规则配置应生效。"""
        service = _make_ip_ban_service(db_container)
        # 先触发默认规则写入
        await service.get_rule_configs()

        updated = await service.update_rule_config(
            "login_failure",
            {"threshold": 20, "window_seconds": 600, "ban_duration_minutes": 60},
        )
        assert updated["threshold"] == 20
        assert updated["window_seconds"] == 600
        assert updated["ban_duration_minutes"] == 60

        # 验证持久化
        rules = await service.get_rule_configs()
        login_rule = next(r for r in rules if r["id"] == "login_failure")
        assert login_rule["threshold"] == 20

    @pytest.mark.asyncio
    async def test_update_rule_config_invalid_id_raises_error(self, db_container):
        """更新不存在的规则应抛出错误。"""
        service = _make_ip_ban_service(db_container)
        with pytest.raises(AppError) as excinfo:
            await service.update_rule_config("nonexistent_rule", {"threshold": 5})
        assert excinfo.value.code == "rule_not_found"
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_rule_config_ignores_invalid_fields(self, db_container):
        """更新时应忽略非允许字段。"""
        service = _make_ip_ban_service(db_container)
        await service.get_rule_configs()

        updated = await service.update_rule_config(
            "login_failure",
            {"threshold": 15, "invalid_field": "should_be_ignored"},
        )
        assert updated["threshold"] == 15
        # 不会抛出错误，invalid_field 被静默忽略

    @pytest.mark.asyncio
    async def test_disable_rule(self, db_container):
        """禁用规则应生效。"""
        service = _make_ip_ban_service(db_container)
        await service.get_rule_configs()

        updated = await service.update_rule_config(
            "rate_limit", {"enabled": False}
        )
        assert updated["enabled"] is False


# =============================================================================
# 自动封禁规则引擎测试
# =============================================================================


class TestAutoBanEngine:
    """测试自动封禁规则引擎的事件触发逻辑。"""

    @pytest.mark.asyncio
    async def test_login_failure_triggers_auto_ban(self, db_container):
        """登录失败次数超过阈值应自动封禁。"""
        # 设置低阈值以便快速触发
        service = _make_ip_ban_service(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"threshold": 3, "window_seconds": 300, "ban_duration_minutes": 30},
        )

        # 记录低于阈值的事件 — 不应触发封禁
        await service.record_event("login_failure", "10.0.10.1")
        assert await service.is_ip_banned("10.0.10.1") is False

        # 再记录 2 次，累计 3 次触发阈值
        await service.record_event("login_failure", "10.0.10.1")
        await service.record_event("login_failure", "10.0.10.1")

        assert await service.is_ip_banned("10.0.10.1") is True

    @pytest.mark.asyncio
    async def test_login_failure_disabled_rule_does_not_ban(self, db_container):
        """禁用登录失败规则后不应自动封禁。"""
        service = _make_ip_ban_service(db_container)
        await service.get_rule_configs()
        await service.update_rule_config("login_failure", {"enabled": False})

        # 记录多次登录失败
        for _ in range(20):
            await service.record_event("login_failure", "10.0.11.1")

        assert await service.is_ip_banned("10.0.11.1") is False

    @pytest.mark.asyncio
    async def test_high_4xx_triggers_auto_ban(self, db_container):
        """4xx 请求超过阈值应自动封禁。"""
        service = _make_ip_ban_service(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "high_4xx",
            {"threshold": 3, "window_seconds": 3600, "ban_duration_minutes": 60},
        )

        # 记录 2 次 404（应低于阈值）
        await service.record_event("high_4xx", "10.0.12.1", status_code=404)
        await service.record_event("high_4xx", "10.0.12.1", status_code=403)
        assert await service.is_ip_banned("10.0.12.1") is False

        # 第 3 次触发阈值
        await service.record_event("high_4xx", "10.0.12.1", status_code=404)
        assert await service.is_ip_banned("10.0.12.1") is True

    @pytest.mark.asyncio
    async def test_rate_limit_triggers_auto_ban(self, db_container):
        """请求频率超过阈值应自动封禁。"""
        service = _make_ip_ban_service(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "rate_limit",
            {"threshold": 5, "window_seconds": 60, "ban_duration_minutes": 10},
        )

        # 记录 5 次请求
        for _ in range(5):
            await service.record_event("rate_limit", "10.0.13.1")

        assert await service.is_ip_banned("10.0.13.1") is True

    @pytest.mark.asyncio
    async def test_high_4xx_ignores_non_4xx_status(self, db_container):
        """high_4xx 规则应忽略非 4xx 状态码。"""
        service = _make_ip_ban_service(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "high_4xx",
            {"threshold": 3, "window_seconds": 3600},
        )

        # 记录含 200 状态码的事件 — 不应计入
        for _ in range(5):
            await service.record_event("high_4xx", "10.0.14.1", status_code=200)

        assert await service.is_ip_banned("10.0.14.1") is False

    @pytest.mark.asyncio
    async def test_different_ips_independent_counters(self, db_container):
        """不同 IP 的计数器应相互独立。"""
        service = _make_ip_ban_service(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "login_failure",
            {"threshold": 3, "window_seconds": 300},
        )

        # IP_A 触发封禁，IP_B 不应受影响
        for _ in range(3):
            await service.record_event("login_failure", "10.0.15.1")
        assert await service.is_ip_banned("10.0.15.1") is True
        assert await service.is_ip_banned("10.0.15.2") is False

    @pytest.mark.asyncio
    async def test_auto_ban_updates_stats(self, db_container):
        """自动封禁应反映在统计数据中。"""
        service = _make_ip_ban_service(db_container)
        await service.get_rule_configs()
        await service.update_rule_config(
            "rate_limit",
            {"threshold": 2, "window_seconds": 60},
        )

        await service.record_event("rate_limit", "10.0.16.1")
        await service.record_event("rate_limit", "10.0.16.1")

        stats = await service.get_stats()
        assert stats["auto_bans"] >= 1
        assert stats["active_bans"] >= 1
