"""IpBanService 及相关数据结构测试。

测试原则：
- 纯函数（ip_matches_cidr、BloomFilter、LRUSet）用同步测试
- 数据库相关（IpBanService）用异步测试 + db_container 做真实交互
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.core.middleware import AppError
from backend.plugins.ip_ban.middleware import BloomFilter, LRUSet
from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr

# =============================================================================
# IP/CIDR 匹配测试
# =============================================================================


class TestIpCidrMatching:
    """测试 ip_matches_cidr 函数。"""

    def test_ipv4_exact_match(self):
        """192.168.1.1 精确匹配 192.168.1.1/32。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """192.168.1.100 在 192.168.1.0/24 网段内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_not_in_subnet(self):
        """10.0.0.1 不在 192.168.1.0/24 网段内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv6_in_subnet(self):
        """IPv6 地址在 CIDR 范围内应匹配。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True

    def test_invalid_ip_returns_false(self):
        """无效输入应返回 False 而不抛出异常。"""
        assert ip_matches_cidr("not_an_ip", "192.168.1.0/24") is False
        assert ip_matches_cidr("", "192.168.1.0/24") is False
        assert ip_matches_cidr("256.256.256.256", "192.168.1.0/24") is False


# =============================================================================
# 布隆过滤器测试
# =============================================================================


class TestBloomFilter:
    """测试 BloomFilter 数据结构。"""

    def test_add_and_contains(self):
        """添加的元素应能被找到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("192.168.1.1") is True

    def test_not_contains(self):
        """未添加的元素不应被找到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        assert bf.contains("10.0.0.1") is False

    def test_clear(self):
        """清空后，之前添加的元素不应被找到。"""
        bf = BloomFilter(size=1000)
        bf.add("192.168.1.1")
        bf.clear()
        assert bf.contains("192.168.1.1") is False

    def test_multiple_items(self):
        """多个元素可同时添加和检查。"""
        bf = BloomFilter(size=10000)
        items = ["192.168.1.1", "10.0.0.1", "172.16.0.1", "2001:db8::1"]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.contains(item) is True

    def test_false_positive_rate(self):
        """布隆过滤器在合理误报率范围内工作。"""
        bf = BloomFilter(size=10000)
        # 添加一批元素
        known_items = [f"10.0.0.{i}" for i in range(100)]
        for item in known_items:
            bf.add(item)
        # 检查已知元素都能找到
        for item in known_items:
            assert bf.contains(item) is True
        # 检查大量不在集合中的元素，误报率应较低
        false_positives = 0
        test_items = [f"192.168.{i}.{j}" for i in range(10) for j in range(10)]
        for item in test_items:
            if bf.contains(item):
                false_positives += 1
        # 100 个测试项中误报不应超过 10 个
        assert false_positives < 10


# =============================================================================
# LRU 集合测试
# =============================================================================


class TestLRUSet:
    """测试 LRUSet 数据结构。"""

    def test_add_and_contains(self):
        """添加的元素应能被找到。"""
        lru = LRUSet(maxsize=3)
        lru.add("192.168.1.1")
        assert lru.contains("192.168.1.1") is True

    def test_contains_moves_to_end(self):
        """contains() 应将已存在的元素移到末尾（影响淘汰顺序）。"""
        lru = LRUSet(maxsize=3)
        lru.add("A")
        lru.add("B")
        lru.add("C")
        # 访问 B，使其移到末尾
        assert lru.contains("B") is True
        # 添加 D，应淘汰最旧的元素（A）
        lru.add("D")
        assert lru.contains("A") is False  # A 被淘汰
        assert lru.contains("B") is True   # B 仍在
        assert lru.contains("C") is True   # C 仍在
        assert lru.contains("D") is True   # D 新增

    def test_eviction_oldest_removed(self):
        """超过 maxsize 时，最旧的元素应被淘汰。"""
        lru = LRUSet(maxsize=3)
        lru.add("A")
        lru.add("B")
        lru.add("C")
        lru.add("D")  # 应淘汰 A
        assert lru.contains("A") is False
        assert lru.contains("B") is True
        assert lru.contains("C") is True
        assert lru.contains("D") is True
        assert len(lru._data) == 3

    def test_remove(self):
        """移除的元素不应被找到。"""
        lru = LRUSet(maxsize=3)
        lru.add("A")
        lru.add("B")
        lru.remove("A")
        assert lru.contains("A") is False
        assert lru.contains("B") is True

    def test_clear(self):
        """清空后所有元素不应被找到。"""
        lru = LRUSet(maxsize=3)
        lru.add("A")
        lru.add("B")
        lru.clear()
        assert lru.contains("A") is False
        assert lru.contains("B") is False
        assert len(lru._data) == 0


# =============================================================================
# IP 封禁服务测试
# =============================================================================


class TestIpBanService:
    """测试 IpBanService 核心业务逻辑。"""

    @pytest.fixture
    def service(self, db_container):
        """创建 IpBanService 实例，使用真实内存数据库。"""
        return IpBanService(db_container)

    # ── 封禁操作 ──

    @pytest.mark.asyncio
    async def test_ban_ip_creates_record(self, service):
        """ban_ip() 应创建一条数据库记录，字段正确。"""
        result = await service.ban_ip(
            ip_or_cidr="192.168.1.1",
            reason="恶意攻击",
            ban_type="manual",
            banned_by="admin",
        )

        assert result["ip_or_cidr"] == "192.168.1.1"
        assert result["ban_type"] == "manual"
        assert result["reason"] == "恶意攻击"
        assert result["banned_by"] == "admin"
        assert result["is_active"] is True
        assert result["expires_at"] is None  # 永久封禁
        assert result["id"] > 0

    @pytest.mark.asyncio
    async def test_ban_ip_with_expiry(self, service):
        """ban_ip() 指定 duration_minutes 应设置 expires_at。"""
        result = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="临时封禁",
            ban_type="auto",
            duration_minutes=30,
        )

        assert result["expires_at"] is not None
        # expires_at 应在当前时间附近（30 分钟后）
        # 移除 tzinfo 以兼容 SQLite 时区处理差异
        expected = (datetime.now(timezone.utc) + timedelta(minutes=30)).replace(
            tzinfo=None
        )
        actual = datetime.fromisoformat(result["expires_at"]).replace(tzinfo=None)
        # 允许 5 秒误差
        assert abs((actual - expected).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_ban_ip_existing_updates(self, service):
        """对已存在的活跃 IP 再次封禁应更新记录而非新建。"""
        result1 = await service.ban_ip(
            ip_or_cidr="192.168.1.0/24",
            reason="首次封禁",
            ban_type="manual",
        )
        result2 = await service.ban_ip(
            ip_or_cidr="192.168.1.0/24",
            reason="更新封禁原因",
            ban_type="auto",
            duration_minutes=60,
        )

        # 应是同一条记录
        assert result2["id"] == result1["id"]
        # 原因已更新
        assert result2["reason"] == "更新封禁原因"
        # 过期时间已设置
        assert result2["expires_at"] is not None

    # ── 解封操作 ──

    @pytest.mark.asyncio
    async def test_unban_ip_deactivates(self, service):
        """unban_ip() 应设置 is_active=False。"""
        ban = await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="测试解封",
        )
        result = await service.unban_ip(ban["id"], operator="admin")

        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_nonexistent_raises_404(self, service):
        """unban_ip() 不存在的 ban_id 应抛出 AppError。"""
        with pytest.raises(AppError) as excinfo:
            await service.unban_ip(99999, operator="admin")

        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "ban_not_found"

    @pytest.mark.asyncio
    async def test_batch_unban(self, service):
        """batch_unban() 应批量解封多条记录。"""
        ban1 = await service.ban_ip(ip_or_cidr="10.0.0.1")
        ban2 = await service.ban_ip(ip_or_cidr="10.0.0.2")

        count = await service.batch_unban(
            [ban1["id"], ban2["id"]], operator="admin"
        )

        assert count == 2

        # 验证解封后的状态
        bans = await service.list_bans(is_active=False)
        assert bans["total"] == 2

    # ── IP 检查 ──

    @pytest.mark.asyncio
    async def test_is_ip_banned_positive(self, service):
        """is_ip_banned() 对已封禁的 IP 应返回 True。"""
        await service.ban_ip(ip_or_cidr="10.0.0.1")
        assert await service.is_ip_banned("10.0.0.1") is True

    @pytest.mark.asyncio
    async def test_is_ip_banned_negative(self, service):
        """is_ip_banned() 对未封禁的 IP 应返回 False。"""
        assert await service.is_ip_banned("1.2.3.4") is False

    @pytest.mark.asyncio
    async def test_is_ip_banned_expired(self, service):
        """已过期的封禁不应阻止 IP 访问。"""
        from backend.plugins.ip_ban.models import IpBan

        # 创建一个已过期的封禁记录
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        async with service.session_factory() as session:
            ban = IpBan(
                ip_or_cidr="10.0.0.1",
                ban_type="manual",
                reason="已过期",
                expires_at=expired_time,
            )
            session.add(ban)
            await session.commit()

        assert await service.is_ip_banned("10.0.0.1") is False

    # ── 列表查询 ──

    @pytest.mark.asyncio
    async def test_list_bans_pagination(self, service):
        """list_bans() 分页功能应正确工作。"""
        for i in range(5):
            await service.ban_ip(ip_or_cidr=f"10.0.0.{i}")

        page1 = await service.list_bans(page=1, page_size=2)
        assert len(page1["list"]) == 2
        assert page1["total"] == 5
        assert page1["page"] == 1
        assert page1["page_size"] == 2

        page2 = await service.list_bans(page=2, page_size=2)
        assert len(page2["list"]) == 2

        page3 = await service.list_bans(page=3, page_size=2)
        assert len(page3["list"]) == 1

    @pytest.mark.asyncio
    async def test_list_bans_filters(self, service):
        """list_bans() 支持按 ban_type、is_active、keyword 筛选。"""
        # 创建手动封禁（活跃）
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        # 创建自动封禁（活跃）
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="auto")
        # 创建手动封禁后解封（不活跃）
        ban3 = await service.ban_ip(ip_or_cidr="10.0.0.3", ban_type="manual")
        await service.unban_ip(ban3["id"])

        # 按 ban_type 筛选
        manual_bans = await service.list_bans(ban_type="manual")
        assert manual_bans["total"] == 2  # 10.0.0.1 和 10.0.0.3

        auto_bans = await service.list_bans(ban_type="auto")
        assert auto_bans["total"] == 1  # 10.0.0.2

        # 按 is_active 筛选
        active_bans = await service.list_bans(is_active=True)
        assert active_bans["total"] == 2  # 10.0.0.1 和 10.0.0.2

        inactive_bans = await service.list_bans(is_active=False)
        assert inactive_bans["total"] == 1  # 10.0.0.3

        # 按 keyword 筛选
        keyword_bans = await service.list_bans(keyword="10.0.0.1")
        assert keyword_bans["total"] == 1

    # ── 操作日志 ──

    @pytest.mark.asyncio
    async def test_get_ban_logs(self, service):
        """get_ban_logs() 应返回操作日志。"""
        await service.ban_ip(
            ip_or_cidr="10.0.0.1",
            reason="测试日志",
            banned_by="admin",
        )
        ban = await service.ban_ip(ip_or_cidr="10.0.0.2")
        await service.unban_ip(ban["id"], operator="admin")

        logs = await service.get_ban_logs(page=1, page_size=10)
        assert logs["total"] >= 2  # 至少 2 条日志（封禁 + 解封）
        assert len(logs["list"]) >= 2

        # 按 action 筛选
        ban_logs = await service.get_ban_logs(action="ban")
        assert ban_logs["total"] >= 2  # 2 次封禁

        unban_logs = await service.get_ban_logs(action="unban")
        assert unban_logs["total"] == 1  # 1 次解封

    # ── 统计 ──

    @pytest.mark.asyncio
    async def test_get_stats(self, service):
        """get_stats() 应返回正确计数。"""
        # 创建 2 条手动封禁
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.2", ban_type="manual")
        # 创建 1 条自动封禁
        await service.ban_ip(ip_or_cidr="10.0.0.3", ban_type="auto")

        stats = await service.get_stats()

        assert stats["total_bans"] == 3
        assert stats["active_bans"] == 3  # 全部活跃
        assert stats["auto_bans"] == 1
        assert stats["manual_bans"] == 2
        assert stats["today_bans"] == 3  # 今日新增封禁操作

    # ── 自动封禁规则引擎 ──

    @pytest.mark.asyncio
    async def test_record_event_login_failure(self, service):
        """record_event() 记录登录失败事件，超过阈值应自动封禁。"""
        ip_str = "10.0.0.100"
        # 触发 11 次登录失败（默认阈值 10 次 / 300 秒）
        for _ in range(11):
            await service.record_event("login_failure", ip_str)

        # 验证 IP 已被自动封禁
        assert await service.is_ip_banned(ip_str) is True

    @pytest.mark.asyncio
    async def test_record_event_rate_limit(self, service):
        """record_event() 记录频率限制事件，超过阈值应自动封禁。"""
        ip_str = "10.0.0.101"
        # 触发 201 次请求（默认阈值 200 次 / 60 秒）
        for _ in range(201):
            await service.record_event("rate_limit", ip_str)

        # 验证 IP 已被自动封禁
        assert await service.is_ip_banned(ip_str) is True

    # ── 活跃 IP 范围 ──

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, service):
        """get_active_ip_ranges() 应返回所有活跃的 IP/CIDR 字符串。"""
        await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.ban_ip(ip_or_cidr="192.168.1.0/24")
        await service.ban_ip(ip_or_cidr="172.16.0.0/16")

        active_ranges = await service.get_active_ip_ranges()
        assert len(active_ranges) == 3
        assert "10.0.0.1" in active_ranges
        assert "192.168.1.0/24" in active_ranges
        assert "172.16.0.0/16" in active_ranges

        # 解封一个后，应不再返回
        bans = await service.list_bans(is_active=True, keyword="10.0.0.1")
        await service.unban_ip(bans["list"][0]["id"])

        active_ranges = await service.get_active_ip_ranges()
        assert len(active_ranges) == 2
        assert "10.0.0.1" not in active_ranges
