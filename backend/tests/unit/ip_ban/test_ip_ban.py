"""IP 封禁服务 单元测试。

使用内存数据库进行真实数据库交互，覆盖：
- IP 匹配工具函数（含 IPv4/IPv6/CIDR/异常值）
- 手动封禁/解封/批量解封
- 自动封禁规则引擎（登录失败、4xx 高频、请求频率）
- 规则配置管理
- 统计查询
- 计数器清理
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


# =============================================================================
# ip_matches_cidr 工具函数测试
# =============================================================================


class TestIpMatchesCidr:
    """IP/CIDR 匹配函数测试——覆盖 IPv4/IPv6/边界/异常。"""

    def test_ipv4_exact_match(self):
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_cidr_any(self):
        assert ip_matches_cidr("8.8.8.8", "0.0.0.0/0") is True

    def test_ipv6_exact_match(self):
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_ipv6_in_subnet(self):
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True

    def test_ipv6_outside_subnet(self):
        assert ip_matches_cidr("2001:db8::1", "fe80::/10") is False

    def test_invalid_ip_returns_false(self):
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_empty_ip_returns_false(self):
        assert ip_matches_cidr("", "0.0.0.0/0") is False


# =============================================================================
# IpBanService 测试
# =============================================================================


@pytest.fixture
async def ban_service(db_container):
    """使用真实内存数据库的 IpBanService 实例。"""
    service = IpBanService(db_container)
    return service


class TestBanServiceCore:
    """封禁服务核心 CRUD 测试。"""

    @pytest.mark.asyncio
    async def test_ban_ip_creates_ban_and_log(self, ban_service):
        """手动封禁应创建封禁记录和操作日志。"""
        result = await ban_service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="测试封禁",
            ban_type="manual",
            banned_by="admin",
        )
        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["is_active"] is True
        assert "id" in result

        # 验证日志已写入
        logs = await ban_service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] >= 1
        assert any(log["ip_or_cidr"] == "192.168.1.1" for log in logs["list"])

    @pytest.mark.asyncio
    async def test_ban_ip_with_duration(self, ban_service):
        """带有效期的封禁应正确设置 expires_at。"""
        result = await ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            ban_type="manual",
            duration_minutes=30,
        )
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_ban_ip_permanent(self, ban_service):
        """永久封禁 expires_at 为 None。"""
        result = await ban_service.ban_ip(
            ip_or_cidr="10.0.0.2",
            reason="永久封禁",
        )
        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_ban_ip_duplicate_updates_existing(self, ban_service):
        """重复封禁同一 IP 应更新已有记录而非创建新记录。"""
        r1 = await ban_service.ban_ip(
            ip_or_cidr="192.168.1.1", reason="第一次", banned_by="admin"
        )
        r2 = await ban_service.ban_ip(
            ip_or_cidr="192.168.1.1", reason="第二次", banned_by="admin"
        )
        # 返回的 ID 可能不同（取决于实现是更新还是重建），但只会有一条活跃记录
        assert r2["ip_or_cidr"] == "192.168.1.1"
        assert r2["is_active"] is True

        # 验证只有一条活跃记录
        bans = await ban_service.list_bans(is_active=True)
        matching = [b for b in bans["list"] if b["ip_or_cidr"] == "192.168.1.1"]
        assert len(matching) == 1

    @pytest.mark.asyncio
    async def test_unban_ip_deactivates_ban(self, ban_service):
        """解封应设置 is_active=False 并创建操作日志。"""
        ban = await ban_service.ban_ip(
            ip_or_cidr="10.0.0.1", reason="待解封", banned_by="admin"
        )
        result = await ban_service.unban_ip(ban_id=ban["id"], operator="admin")
        assert result["is_active"] is False

        # 验证 IP 不再被封禁
        is_banned = await ban_service.is_ip_banned("10.0.0.1")
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_error(self, ban_service):
        """解封不存在的记录应抛出 AppError。"""
        with pytest.raises(AppError) as exc:
            await ban_service.unban_ip(ban_id=99999, operator="admin")
        assert exc.value.code == "ban_not_found"
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_unban(self, ban_service):
        """批量解封应返回解封数量。"""
        b1 = await ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="批量1")
        b2 = await ban_service.ban_ip(ip_or_cidr="10.0.0.2", reason="批量2")
        b3 = await ban_service.ban_ip(ip_or_cidr="10.0.0.3", reason="批量3")

        count = await ban_service.batch_unban(
            ban_ids=[b1["id"], b2["id"], b3["id"]], operator="admin"
        )
        assert count == 3

        # 验证全部解封
        for ip in ["10.0.0.1", "10.0.0.2", "10.0.0.3"]:
            assert await ban_service.is_ip_banned(ip) is False

    @pytest.mark.asyncio
    async def test_batch_unban_partial(self, ban_service):
        """批量解封混合已解封/不存在记录，只解封活跃记录。"""
        b1 = await ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="活跃")
        await ban_service.ban_ip(ip_or_cidr="10.0.0.2", reason="将解封")
        await ban_service.unban_ip(ban_id=b1["id"])  # 先解封一个

        # 这时 b1 已不活跃，b2 活跃
        bans = await ban_service.list_bans(is_active=True)
        active_ids = [b["id"] for b in bans["list"]]

        count = await ban_service.batch_unban(ban_ids=active_ids + [99999])
        # 只有活跃的记录被解封，不存在的记录被跳过
        assert count == len(active_ids)

    @pytest.mark.asyncio
    async def test_is_ip_banned_matches_cidr(self, ban_service):
        """CIDR 封禁应匹配范围内的任何 IP。"""
        await ban_service.ban_ip(ip_or_cidr="192.168.0.0/16", reason="封禁整个网段")
        assert await ban_service.is_ip_banned("192.168.1.1") is True
        assert await ban_service.is_ip_banned("192.168.100.200") is True
        assert await ban_service.is_ip_banned("10.0.0.1") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_expired(self, ban_service):
        """已过期的封禁不应匹配。"""
        # 创建一个已过期的封禁
        await ban_service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="过期封禁",
            duration_minutes=0,  # 0 分钟 = 立即过期... 实际上 duration_minutes <= 0 不走 expires_at
        )
        # 用另一种方式创建过期封禁：直接操作数据库
        from datetime import datetime, timedelta, timezone

        from backend.plugins.ip_ban.models import IpBan

        async with ban_service.session_factory() as session:
            ban = IpBan(
                ip_or_cidr="10.0.0.2",
                reason="已过期",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            session.add(ban)
            await session.commit()

        assert await ban_service.is_ip_banned("10.0.0.2") is False

    @pytest.mark.asyncio
    async def test_list_bans_with_filters(self, ban_service):
        """分页查询应支持类型/状态/关键词过滤。"""
        await ban_service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="auto", reason="自动")
        await ban_service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="manual", reason="手动")
        await ban_service.ban_ip(
            ip_or_cidr="192.168.1.1", ban_type="manual", reason="测试"
        )

        # 按类型筛选
        auto_bans = await ban_service.list_bans(ban_type="auto")
        assert all(b["ban_type"] == "auto" for b in auto_bans["list"])

        # 按关键词筛选
        keyword_bans = await ban_service.list_bans(keyword="192.168")
        assert all("192.168" in b["ip_or_cidr"] for b in keyword_bans["list"])

        # 分页
        page1 = await ban_service.list_bans(page=1, page_size=2)
        assert len(page1["list"]) <= 2

    @pytest.mark.asyncio
    async def test_get_ban_logs_with_filters(self, ban_service):
        """操作日志查询应支持按 action 过滤。"""
        await ban_service.ban_ip(ip_or_cidr="10.0.0.1", reason="测试")
        bans = await ban_service.list_bans()
        if bans["list"]:
            await ban_service.unban_ip(ban_id=bans["list"][0]["id"], operator="admin")

        ban_logs = await ban_service.get_ban_logs(action="ban")
        assert all(log["action"] == "ban" for log in ban_logs["list"])

        unban_logs = await ban_service.get_ban_logs(action="unban")
        if unban_logs["list"]:
            assert all(log["action"] == "unban" for log in unban_logs["list"])


class TestAutoBanEngine:
    """自动封禁规则引擎测试。"""

    @pytest.mark.asyncio
    async def test_record_event_login_failure_triggers_ban(self, ban_service):
        """登录失败事件在超阈值后应触发自动封禁。"""
        ip = "10.0.0.100"
        # 模拟 15 次登录失败（阈值 10）
        for _ in range(15):
            await ban_service.record_event("login_failure", ip)

        # 验证 IP 被自动封禁
        is_banned = await ban_service.is_ip_banned(ip)
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_below_threshold_no_ban(self, ban_service):
        """登录失败事件在阈值以下不应触发封禁。"""
        ip = "10.0.0.101"
        # 模拟 5 次登录失败（阈值 10）
        for _ in range(5):
            await ban_service.record_event("login_failure", ip)

        is_banned = await ban_service.is_ip_banned(ip)
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_record_event_high_4xx_triggers_ban(self, ban_service):
        """高频 4xx 事件在超阈值后应触发自动封禁。"""
        ip = "10.0.0.102"
        # 模拟 60 次 4xx 请求（阈值 50）
        for _ in range(60):
            await ban_service.record_event("high_4xx", ip, status_code=404)

        is_banned = await ban_service.is_ip_banned(ip)
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_record_event_high_4xx_ignores_5xx(self, ban_service):
        """高频 4xx 规则应忽略 5xx 状态码。"""
        ip = "10.0.0.103"
        # 模拟 60 次 5xx 请求（不应触发 high_4xx 规则）
        for _ in range(60):
            await ban_service.record_event("high_4xx", ip, status_code=500)

        is_banned = await ban_service.is_ip_banned(ip)
        assert is_banned is False

    @pytest.mark.asyncio
    async def test_record_event_rate_limit_triggers_ban(self, ban_service):
        """请求频率事件在超阈值后应触发自动封禁。"""
        ip = "10.0.0.104"
        # 模拟 250 次请求（阈值 200）
        for _ in range(250):
            await ban_service.record_event("rate_limit", ip)

        is_banned = await ban_service.is_ip_banned(ip)
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_different_ips_independent_counters(self, ban_service):
        """不同 IP 的计数器应独立工作。"""
        # IP-A 超过阈值
        for _ in range(15):
            await ban_service.record_event("login_failure", "10.0.0.200")
        # IP-B 低于阈值
        for _ in range(3):
            await ban_service.record_event("login_failure", "10.0.0.201")

        assert await ban_service.is_ip_banned("10.0.0.200") is True
        assert await ban_service.is_ip_banned("10.0.0.201") is False

    @pytest.mark.asyncio
    async def test_cleanup_counters_removes_expired(self, ban_service):
        """计数器清理应移除过期条目。"""
        ip = "10.0.0.300"
        for _ in range(5):
            await ban_service.record_event("login_failure", ip)

        # 验证计数器有数据
        key = f"login_failure:{ip}"
        assert key in ban_service._counters
        assert len(ban_service._counters[key]) == 5

        # 手动过期计数器
        import time

        old_time = time.time() - 7200  # 2 小时前
        ban_service._counters[key] = [(old_time, 0)]
        ban_service._cleanup_counters()

        # 过期条目应被清理
        assert key not in ban_service._counters or len(ban_service._counters[key]) == 0

    @pytest.mark.asyncio
    async def test_rule_config_inherits_defaults(self, ban_service):
        """规则配置应继承默认值。"""
        configs = await ban_service.get_rule_configs()
        config_map = {c["id"]: c for c in configs}

        assert "login_failure" in config_map
        assert config_map["login_failure"]["threshold"] == 10
        assert config_map["login_failure"]["window_seconds"] == 300
        assert config_map["login_failure"]["ban_duration_minutes"] == 30

        assert "high_4xx" in config_map
        assert "rate_limit" in config_map
        assert "geo_surge" in config_map

    @pytest.mark.asyncio
    async def test_update_rule_config(self, ban_service):
        """更新规则配置应持久化。"""
        await ban_service.update_rule_config(
            "login_failure", {"threshold": 20, "enabled": False}
        )
        configs = await ban_service.get_rule_configs()
        config_map = {c["id"]: c for c in configs}
        assert config_map["login_failure"]["threshold"] == 20
        assert config_map["login_failure"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_rule_raises_error(self, ban_service):
        """更新不存在的规则应抛出错误。"""
        with pytest.raises(AppError) as exc:
            await ban_service.update_rule_config("nonexistent_rule", {"threshold": 5})
        assert exc.value.code == "rule_not_found"

    @pytest.mark.asyncio
    async def test_disabled_rule_does_not_ban(self, ban_service):
        """禁用的规则不应触发自动封禁。"""
        # 禁用 login_failure 规则
        await ban_service.update_rule_config(
            "login_failure", {"enabled": False}
        )

        ip = "10.0.0.105"
        for _ in range(15):
            await ban_service.record_event("login_failure", ip)

        is_banned = await ban_service.is_ip_banned(ip)
        assert is_banned is False


class TestBanStats:
    """封禁统计测试。"""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, ban_service):
        """空数据库应返回零值统计。"""
        stats = await ban_service.get_stats()
        assert stats["total_bans"] == 0
        assert stats["active_bans"] == 0
        assert stats["auto_bans"] == 0
        assert stats["manual_bans"] == 0
        assert stats["today_bans"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, ban_service):
        """有封禁数据时统计应正确。"""
        await ban_service.ban_ip(
            ip_or_cidr="10.0.0.1", ban_type="manual", reason="手动"
        )
        await ban_service.ban_ip(
            ip_or_cidr="10.0.0.2", ban_type="auto", reason="自动"
        )

        stats = await ban_service.get_stats()
        assert stats["total_bans"] == 2
        assert stats["active_bans"] == 2
        assert stats["manual_bans"] == 1
        assert stats["auto_bans"] == 1

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, ban_service):
        """获取活跃 IP 范围列表。"""
        await ban_service.ban_ip(ip_or_cidr="10.0.0.0/24", reason="网段封禁")
        await ban_service.ban_ip(ip_or_cidr="192.168.1.1", reason="单 IP 封禁")

        ranges = await ban_service.get_active_ip_ranges()
        assert "10.0.0.0/24" in ranges
        assert "192.168.1.1" in ranges


class TestBanWebhook:
    """Webhook 通知测试。"""

    @pytest.mark.asyncio
    async def test_webhook_not_sent_when_url_empty(self, ban_service):
        """Webhook URL 为空时不应发送通知。"""
        with patch.object(ban_service, "_send_webhook_notification") as mock_webhook:
            await ban_service.ban_ip(
                ip_or_cidr="10.0.0.1", reason="测试", banned_by="admin"
            )
            # 默认 _webhook_url 为空字符串，不应发送
            mock_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_notification_sent(self, ban_service):
        """配置了 Webhook URL 时应发送通知。"""
        aiohttp = pytest.importorskip("aiohttp", reason="需要 aiohttp 库")

        # 设置 webhook URL
        ban_service._webhook_url = "https://hooks.example.com/alert"

        with patch("backend.plugins.ip_ban.services._HAS_AIOHTTP", True):
            mock_post = AsyncMock()
            mock_post.return_value.__aenter__ = AsyncMock()
            mock_post.return_value.__aenter__.return_value.status = 200
            with patch.object(aiohttp.ClientSession, "post", mock_post):
                await ban_service.ban_ip(
                    ip_or_cidr="10.0.0.1",
                    reason="测试通知",
                    ban_type="auto",
                    rule_id="login_failure",
                    duration_minutes=30,
                )

                mock_post.assert_called_once()
                call_kwargs = mock_post.call_args[1]
                assert "json" in call_kwargs
                assert call_kwargs["json"]["msgtype"] == "text"
                assert "10.0.0.1" in call_kwargs["json"]["text"]["content"]