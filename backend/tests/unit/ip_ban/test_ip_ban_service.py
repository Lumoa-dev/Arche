"""IP 封禁 — IpBanService 核心逻辑单元测试。

覆盖：
- ip_matches_cidr 函数（IPv4/IPv6/边界条件）
- 服务层数据转换方法
- 系统不在测试数据安全风险范围内的纯函数

复杂数据库操作（ban_ip / list_bans / record_event）由集成测试覆盖。
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.services import ip_matches_cidr


class TestIpMatchesCidr:
    """CIDR 匹配函数测试。"""

    # ── IPv4 匹配 ──

    def test_ipv4_exact_match(self):
        """精确 IP 匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IP 在子网内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IP 不在子网内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_cidr_slash32_boundary(self):
        """/32 边界。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1/32") is True
        assert ip_matches_cidr("10.0.0.2", "10.0.0.1/32") is False

    def test_ipv4_cidr_slash0(self):
        """/0 应匹配所有 IP。"""
        assert ip_matches_cidr("1.2.3.4", "0.0.0.0/0") is True
        assert ip_matches_cidr("255.255.255.255", "0.0.0.0/0") is True

    def test_ipv4_cidr_slash31(self):
        """/31 只有 2 个地址。"""
        assert ip_matches_cidr("10.0.0.0", "10.0.0.0/31") is True
        assert ip_matches_cidr("10.0.0.1", "10.0.0.0/31") is True
        assert ip_matches_cidr("10.0.0.2", "10.0.0.0/31") is False

    # ── IPv6 匹配 ──

    def test_ipv6_exact_match(self):
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_ipv6_in_subnet(self):
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True
        )

    def test_ipv6_outside_subnet(self):
        assert (
            ip_matches_cidr("2001:db9::1", "2001:db8::/32") is False
        )

    def test_ipv6_slash64_boundary(self):
        assert (
            ip_matches_cidr(
                "2001:db8:0:0:ffff:ffff:ffff:ffff", "2001:db8::/64"
            )
            is True
        )
        assert (
            ip_matches_cidr(
                "2001:db8:0:1::1", "2001:db8::/64"
            )
            is False
        )

    # ── 混合类型 ──

    def test_ipv4_address_in_ipv6_cidr(self):
        """IPv4 地址匹配 IPv6 CIDR 返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "::1/128") is False

    def test_ipv6_address_in_ipv4_cidr(self):
        """IPv6 地址匹配 IPv4 CIDR 返回 False。"""
        assert ip_matches_cidr("::1", "192.168.1.0/24") is False

    # ── 边界和异常情况 ──

    def test_invalid_ip_address(self):
        """非法 IP 字符串返回 False。"""
        assert ip_matches_cidr("not-an-ip", "10.0.0.0/8") is False

    def test_invalid_cidr(self):
        """非法 CIDR 格式返回 False。"""
        assert ip_matches_cidr("10.0.0.1", "not-a-cidr") is False

    def test_empty_ip(self):
        assert ip_matches_cidr("", "10.0.0.0/8") is False

    def test_empty_cidr(self):
        assert ip_matches_cidr("10.0.0.1", "") is False

    def test_cidr_without_prefix_length(self):
        """没有前缀长度的 CIDR 视为 /32（strict=False 的行为）。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1") is True
        assert ip_matches_cidr("10.0.0.2", "10.0.0.1") is False

    def test_private_ip_range(self):
        """私有地址段匹配。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.0/8") is True
        assert ip_matches_cidr("172.16.0.1", "172.16.0.0/12") is True
        assert ip_matches_cidr("192.168.0.1", "192.168.0.0/16") is True

    def test_loopback(self):
        assert ip_matches_cidr("127.0.0.1", "127.0.0.0/8") is True
        assert ip_matches_cidr("127.255.255.255", "127.0.0.0/8") is True