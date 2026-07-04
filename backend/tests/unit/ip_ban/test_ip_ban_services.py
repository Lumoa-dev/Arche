"""IpBanService 行为测试。

测试原则：
- 只测公开方法输入输出
- 用内存数据库做真实交互
- 每个测试独立运行
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.models import AutoBanRuleConfig, IpBan, IpBanLog
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr

# =============================================================================
# ip_matches_cidr 工具函数测试
# =============================================================================


class TestIpMatchesCidr:
    """测试 IP-CIDR 匹配逻辑。"""

    def test_ipv4_exact_match(self):
        """精确 IP 匹配自身。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_cidr(self):
        """IP 在 CIDR 段内。"""
        assert ip_matches_cidr("192.168.1.50", "192.168.1.0/24") is True

    def test_ipv4_outside_cidr(self):
        """IP 不在 CIDR 段内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_single_ip_no_cidr(self):
        """不带 CIDR 的纯 IP 匹配。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1") is True
        assert ip_matches_cidr("10.0.0.2", "10.0.0.1") is False

    def test_ipv6_match(self):
        """IPv6 地址匹配。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        assert ip_matches_cidr("2001:db8::1", "2001:db9::/32") is False

    def test_invalid_ip_returns_false(self):
        """无效 IP 应返回 False 而非抛出异常。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 应返回 False 而非抛出异常。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_broadcast_address_in_cidr(self):
        """广播地址在 /24 段内。"""
        assert ip_matches_cidr("192.168.1.255", "192.168.1.0/24") is True

    def test_network_address_in_cidr(self):
        """网络地址在 /24 段内。"""
        assert ip_matches_cidr("192.168.1.0", "192.168.1.0/24") is True

    def test_large_cidr_blocks(self):
        """大段 CIDR 匹配。"""
        assert ip_matches_cidr("10.0.0.1", "0.0.0.0/0") is True
        assert ip_matches_cidr("8.8.8.8", "10.0.0.0/8") is False

    def test_loopback_address(self):
        """回环地址匹配。"""
        assert ip_matches_cidr("127.0.0.1", "127.0.0.0/8") is True


# =============================================================================
# IpBanService 测试
# =============================================================================


class TestBanIP:
    """手动封禁 IP 行为测试。"""

    @pytest.mark.asyncio
    async def test_ban_new_ip(self, in_memory_db):
        """封禁一个新 IP 应创建封禁记录和日志。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        result = await service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="恶意请求",
            ban_type="manual",
            banned_by="admin",
        )

        assert result["ip_or_cidr"] == "192.168.1.100"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert result["reason"] == "恶意请求"

    @pytest.mark.asyncio
    async def test_ban_with_duration(self, in_memory_db):
        """指定封禁时长应设置 expires_at。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="测试",
            duration_minutes=60,
        )

        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_permanent(self, in_memory_db):
        """不指定时长应永久封禁（expires_at=None）。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        result = await service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="永久封禁",
        )

        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_ban_duplicate_updates_existing(self, in_memory_db):
        """重复封禁同一 IP 应更新已有记录而非创建新记录。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        result1 = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="首次封禁",
        )
        result2 = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="更新原因",
        )

        assert result1["id"] == result2["id"]
        assert result2["reason"] == "更新原因"

    @pytest.mark.asyncio
    async def test_ban_creates_log_entry(self, in_memory_db):
        """封禁应创建操作日志。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        await service.ban_ip(
            ip_or_cidr="10.0.0.5",
            reason="测试日志",
        )

        async with in_memory_db["session_factory"]() as session:
            logs = (await session.execute(
                __import__("sqlalchemy").select(IpBanLog)
            )).scalars().all()
            assert len(logs) == 1
            assert logs[0].action == "ban"
            assert logs[0].ip_or_cidr == "10.0.0.5"


class TestUnbanIP:
    """解封 IP 行为测试。"""

    @pytest.mark.asyncio
    async def test_unban_existing(self, in_memory_db):
        """解封已有的封禁记录应成功。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        ban = await service.ban_ip(
            ip_or_cidr="192.168.1.100",
            reason="测试封禁",
        )

        result = await service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, in_memory_db):
        """解封不存在的记录应抛出 AppError。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(ban_id=99999)
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "ban_not_found"

    @pytest.mark.asyncio
    async def test_unban_creates_log(self, in_memory_db):
        """解封应创建操作日志。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        ban = await service.ban_ip(
            ip_or_cidr="10.0.0.10",
            reason="将被解封",
        )
        await service.unban_ip(ban_id=ban["id"], operator="admin")

        async with in_memory_db["session_factory"]() as session:
            logs = (await session.execute(
                __import__("sqlalchemy").select(IpBanLog).where(IpBanLog.action == "unban")
            )).scalars().all()
            assert len(logs) == 1


class TestBatchUnban:
    """批量解封行为测试。"""

    @pytest.mark.asyncio
    async def test_batch_unban_multiple(self, in_memory_db):
        """批量解封多个 IP 应返回解封数量。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        ban1 = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="批量1")
        ban2 = await service.ban_ip(ip_or_cidr="10.0.0.2", reason="批量2")

        count = await service.batch_unban(
            ban_ids=[ban1["id"], ban2["id"]],
            operator="admin",
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_batch_unban_partial(self, in_memory_db):
        """混合已解封和未封禁的 ID 应只解封有效的。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        ban1 = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="有效")
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="将被提前解封")
        await service.unban_ip(ban_id=2)  # ID=2 是第二个封禁

        count = await service.batch_unban(
            ban_ids=[ban1["id"], 99999, 2],
        )
        assert count == 1  # 只有 ID=1 是有效的待解封记录


class TestListBans:
    """封禁列表查询行为测试。"""

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, in_memory_db):
        """分页查询应返回正确页码和总数。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        for i in range(5):
            await service.ban_ip(
                ip_or_cidr=f"10.0.0.{i}",
                reason=f"测试{i}",
            )

        result = await service.list_bans(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["list"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2

    @pytest.mark.asyncio
    async def test_list_bans_filter_by_type(self, in_memory_db):
        """按封禁类型筛选应返回正确结果。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="手动", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="自动", ban_type="auto")

        result = await service.list_bans(ban_type="auto")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "10.0.0.2"

    @pytest.mark.asyncio
    async def test_list_bans_keyword_search(self, in_memory_db):
        """按关键词搜索应返回匹配结果。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        await service.ban_ip(ip_or_cidr="192.168.1.1", reason="测试")
        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")

        result = await service.list_bans(keyword="192.168")
        assert result["total"] == 1
        assert result["list"][0]["ip_or_cidr"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_list_bans_filter_active(self, in_memory_db):
        """按活跃状态筛选应返回正确结果。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")
        await service.unban_ip(ban_id=ban["id"])

        result = await service.list_bans(is_active=False)
        assert result["total"] == 1


class TestIsIpBanned:
    """IP 封禁检查行为测试。"""

    @pytest.mark.asyncio
    async def test_is_banned_ip(self, in_memory_db):
        """被封禁的 IP 应返回 True。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        await service.ban_ip(ip_or_cidr="10.0.0.50", reason="测试")

        assert await service.is_ip_banned("10.0.0.50") is True

    @pytest.mark.asyncio
    async def test_is_not_banned_ip(self, in_memory_db):
        """未封禁的 IP 应返回 False。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        assert await service.is_ip_banned("10.0.0.99") is False

    @pytest.mark.asyncio
    async def test_expired_ban_not_active(self, in_memory_db):
        """已过期的封禁不应视为活跃。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        # 创建一个已在过去过期的封禁
        async with in_memory_db["session_factory"]() as session:
            expired_ban = IpBan(
                ip_or_cidr="10.0.0.1",
                reason="已过期",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                is_active=True,
            )
            session.add(expired_ban)
            await session.commit()

        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_cidr_ban_matches_sub_ip(self, in_memory_db):
        """封禁 CIDR 段后，段内任意 IP 均被识别为封禁。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        await service.ban_ip(ip_or_cidr="192.168.0.0/16", reason="整段封禁")

        assert await service.is_ip_banned("192.168.1.1") is True
        assert await service.is_ip_banned("192.168.50.100") is True
        assert await service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_unbanned_ip_not_detected(self, in_memory_db):
        """解封后 IP 不应被检测为封禁。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        ban = await service.ban_ip(ip_or_cidr="10.0.0.50", reason="测试")
        assert await service.is_ip_banned("10.0.0.50") is True

        await service.unban_ip(ban_id=ban["id"])
        assert await service.is_ip_banned("10.0.0.50") is False


class TestGetBanLogs:
    """封禁日志查询行为测试。"""

    @pytest.mark.asyncio
    async def test_get_ban_logs_pagination(self, in_memory_db):
        """日志分页查询应返回正确结果。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        for i in range(3):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}", reason=f"测试{i}")

        result = await service.get_ban_logs(page=1, page_size=2)
        assert result["total"] == 3
        assert len(result["list"]) == 2

    @pytest.mark.asyncio
    async def test_get_ban_logs_filter_action(self, in_memory_db):
        """按操作类型筛选日志。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        ban = await service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")
        await service.unban_ip(ban_id=ban["id"])

        ban_logs = await service.get_ban_logs(action="ban")
        unban_logs = await service.get_ban_logs(action="unban")

        assert len(ban_logs["list"]) == 1
        assert len(unban_logs["list"]) == 1
        assert ban_logs["list"][0]["action"] == "ban"
        assert unban_logs["list"][0]["action"] == "unban"


class TestGetStats:
    """封禁统计行为测试。"""

    @pytest.mark.asyncio
    async def test_get_stats_counts(self, in_memory_db):
        """统计应返回正确的计数。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        await service.ban_ip(ip_or_cidr="10.0.0.1", reason="手动", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", reason="自动", ban_type="auto")

        stats = await service.get_stats()
        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 2
        assert stats["manual_bans"] == 1
        assert stats["auto_bans"] == 1


class TestRecordEvent:
    """事件记录与自动规则触发行为测试。"""

    @pytest.mark.asyncio
    async def test_record_event_login_failure(self, in_memory_db):
        """记录登录失败事件不应抛出异常。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        # record_event 是 fire-and-forget 风格，验证不抛出异常即可
        await service.record_event(
            event_type="login_failure",
            ip_str="10.0.0.1",
        )

    @pytest.mark.asyncio
    async def test_record_event_high_4xx(self, in_memory_db):
        """记录 4xx 事件不应抛出异常。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        await service.record_event(
            event_type="high_4xx",
            ip_str="10.0.0.1",
            status_code=401,
        )

    @pytest.mark.asyncio
    async def test_record_event_rate_limit(self, in_memory_db):
        """记录限流事件不应抛出异常。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        await service.record_event(
            event_type="rate_limit",
            ip_str="10.0.0.1",
        )


class TestGetActiveIpRanges:
    """活跃 IP 段查询行为测试。"""

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges_returns_non_expired(self, in_memory_db):
        """应只返回活跃且未过期的 IP/CIDR。"""
        container = MagicMock()
        container.get = lambda n: in_memory_db if n == "db" else MagicMock()
        service = IpBanService(container)

        await service.ban_ip(ip_or_cidr="10.0.0.0/24", reason="段封禁")
        await service.ban_ip(ip_or_cidr="192.168.1.1", reason="单 IP")

        ranges = await service.get_active_ip_ranges()
        assert "10.0.0.0/24" in ranges
        assert "192.168.1.1" in ranges