"""ip_matches_cidr 函数测试 —— IP/CIDR 段匹配逻辑。

覆盖：
- IPv4 精确匹配、子网包含、不匹配
- IPv6 匹配
- CIDR 段边界情况（/0、/32、/128）
- 无效输入保护
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.services import ip_matches_cidr


class TestIpMatchesCIDR:
    """测试 IP/CIDR 匹配函数。"""

    # ── IPv4 匹配 ──

    @pytest.mark.asyncio
    async def test_ipv4_exact_match(self):
        """精确 IPv4 地址应匹配自身 /32 段。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    @pytest.mark.asyncio
    async def test_ipv4_in_subnet(self):
        """IP 在子网内应返回 True。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.0/24") is True

    @pytest.mark.asyncio
    async def test_ipv4_not_in_subnet(self):
        """IP 不在子网内应返回 False。"""
        assert ip_matches_cidr("10.0.1.5", "10.0.0.0/24") is False

    @pytest.mark.asyncio
    async def test_ipv4_zero_network(self):
        """0.0.0.0/0 应匹配任何 IPv4 地址。"""
        assert ip_matches_cidr("8.8.8.8", "0.0.0.0/0") is True

    @pytest.mark.asyncio
    async def test_ipv4_private_range(self):
        """私有地址段匹配。"""
        assert ip_matches_cidr("172.16.0.1", "172.16.0.0/12") is True
        assert ip_matches_cidr("172.31.255.255", "172.16.0.0/12") is True
        assert ip_matches_cidr("172.32.0.1", "172.16.0.0/12") is False

    # ── IPv6 匹配 ──

    @pytest.mark.asyncio
    async def test_ipv6_exact_match(self):
        """精确 IPv6 地址应匹配自身 /128 段。"""
        assert (
            ip_matches_cidr(
                "2001:db8::1",
                "2001:db8::1/128",
            )
            is True
        )

    @pytest.mark.asyncio
    async def test_ipv6_in_subnet(self):
        """IPv6 地址在子网内应返回 True。"""
        assert (
            ip_matches_cidr(
                "2001:db8::42",
                "2001:db8::/32",
            )
            is True
        )

    @pytest.mark.asyncio
    async def test_ipv6_not_in_subnet(self):
        """IPv6 地址不在子网内应返回 False。"""
        assert (
            ip_matches_cidr(
                "2001:db9::1",
                "2001:db8::/32",
            )
            is False
        )

    # ── 无效输入保护 ──

    @pytest.mark.asyncio
    async def test_invalid_ip_returns_false(self):
        """无效 IP 字符串应返回 False 而非抛出异常。"""
        assert ip_matches_cidr("not-an-ip", "10.0.0.0/24") is False

    @pytest.mark.asyncio
    async def test_invalid_cidr_returns_false(self):
        """无效 CIDR 段应返回 False 而非抛出异常。"""
        assert ip_matches_cidr("10.0.0.1", "not-a-cidr") is False

    @pytest.mark.asyncio
    async def test_invalid_both_returns_false(self):
        """IP 和 CIDR 均无效时应返回 False。"""
        assert ip_matches_cidr("bad", "worse") is False

    @pytest.mark.asyncio
    async def test_empty_ip_returns_false(self):
        """空 IP 字符串应返回 False。"""
        assert ip_matches_cidr("", "10.0.0.0/24") is False

    # ── 边界情况 ──

    @pytest.mark.asyncio
    async def test_loopback_address(self):
        """127.0.0.1 应在 127.0.0.0/8 内。"""
        assert ip_matches_cidr("127.0.0.1", "127.0.0.0/8") is True

    @pytest.mark.asyncio
    async def test_broadcast_address(self):
        """广播地址不匹配具体子网。"""
        assert ip_matches_cidr("10.0.0.255", "10.0.0.0/24") is True
        assert ip_matches_cidr("10.0.1.255", "10.0.0.0/24") is False

    @pytest.mark.asyncio
    async def test_ipv4_mapped_ipv6_not_match_ipv4_cidr(self):
        """IPv4-mapped IPv6 地址不应匹配 IPv4 CIDR（类型不同）。"""
        assert ip_matches_cidr("::ffff:10.0.0.1", "10.0.0.0/24") is False