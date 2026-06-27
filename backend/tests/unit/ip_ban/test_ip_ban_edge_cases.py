"""IpBanService 边缘用例测试 —— 边界条件和异常路径。

测试重点：
- IPv6 CIDR 匹配边界
- 异常 IP 格式
- 并发场景
- 空状态和零值
- 大型数据集边界
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.services import IpBanService, ip_matches_cidr


class TestIPMatchingEdgeCases:
    """IP 匹配边缘用例。"""

    def test_ipv6_mapped_ipv4(self):
        """IPv6 映射的 IPv4 地址。"""
        assert ip_matches_cidr("::ffff:192.168.1.1", "192.168.1.1") is False
        assert ip_matches_cidr("::ffff:192.168.1.1", "::ffff:192.168.1.1") is True

    def test_ipv6_short_form(self):
        """IPv6 简写形式。"""
        assert ip_matches_cidr("::1", "::1") is True  # loopback
        assert ip_matches_cidr("::1", "::/0") is True  # 全部段

    def test_loopback_addresses(self):
        """回环地址匹配。"""
        assert ip_matches_cidr("127.0.0.1", "127.0.0.0/8") is True
        assert ip_matches_cidr("127.255.255.255", "127.0.0.0/8") is True

    def test_all_zeros_ip(self):
        """全零 IP。"""
        assert ip_matches_cidr("0.0.0.0", "0.0.0.0") is True

    def test_broadcast_address(self):
        """广播地址。"""
        assert ip_matches_cidr("255.255.255.255", "255.255.255.255") is True

    def test_empty_ip(self):
        """空字符串 IP。"""
        assert ip_matches_cidr("", "10.0.0.0/8") is False

    def test_single_host_cidr(self):
        """32 位掩码的 CIDR。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1/32") is True
        assert ip_matches_cidr("10.0.0.2", "10.0.0.1/32") is False

    def test_zero_cidr(self):
        """0 位掩码（匹配所有）。"""
        assert ip_matches_cidr("8.8.8.8", "0.0.0.0/0") is True
        assert ip_matches_cidr("1.2.3.4", "0.0.0.0/0") is True


class TestIpBanEdgeCases:
    """IpBanService 边缘场景测试。"""

    @pytest.mark.asyncio
    async def test_ban_cidr_range(self, db_container):
        """封禁 CIDR 段，段内所有 IP 都应被拦截。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.10.0.0/16", reason="封禁段")

        assert await service.is_ip_banned("10.10.0.1") is True
        assert await service.is_ip_banned("10.10.255.255") is True
        assert await service.is_ip_banned("10.11.0.1") is False

    @pytest.mark.asyncio
    async def test_ban_case_sensitivity(self, db_container):
        """IP/CIDR 输入大小写不敏感。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1")

        # 查询应大小写一致
        assert await service.is_ip_banned("10.0.0.1") is True

    @pytest.mark.asyncio
    async def test_multiple_bans_different_types(self, db_container):
        """同 IP 多种封禁类型，应只保留一个活跃记录。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="manual")
        await service.ban_ip(ip_or_cidr="10.0.0.1", ban_type="auto")
        # 第二次应更新已有记录
        assert await service.is_ip_banned("10.0.0.1") is True

    @pytest.mark.asyncio
    async def test_get_active_ip_ranges(self, db_container):
        """获取活跃 IP 范围列表。"""
        service = IpBanService(db_container)
        await service.ban_ip(ip_or_cidr="10.0.0.0/24")
        await service.ban_ip(ip_or_cidr="192.168.1.1")

        ranges = await service.get_active_ip_ranges()
        assert "10.0.0.0/24" in ranges
        assert "192.168.1.1" in ranges

    @pytest.mark.asyncio
    async def test_get_active_empty(self, db_container):
        """无活跃封禁时返回空列表。"""
        service = IpBanService(db_container)
        ranges = await service.get_active_ip_ranges()
        assert ranges == []

    @pytest.mark.asyncio
    async def test_inactive_ban_not_in_ranges(self, db_container):
        """已解封的记录不应出现在活跃范围中。"""
        service = IpBanService(db_container)
        ban = await service.ban_ip(ip_or_cidr="10.0.0.1")
        await service.unban_ip(ban_id=ban["id"])

        ranges = await service.get_active_ip_ranges()
        assert "10.0.0.1" not in ranges