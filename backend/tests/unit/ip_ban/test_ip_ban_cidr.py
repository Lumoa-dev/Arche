"""ip_matches_cidr 工具函数测试。

测试 IP/CIDR 匹配的核心逻辑，包括 IPv4、IPv6、边界条件和无效输入。
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.services import ip_matches_cidr


class TestIpMatchesCidr:
    """ip_matches_cidr 函数测试。"""

    # ── IPv4 基础匹配 ──

    def test_ipv4_exact_match(self):
        """精确 IP 匹配。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_in_subnet(self):
        """IP 在 CIDR 段内。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_outside_subnet(self):
        """IP 不在 CIDR 段内。"""
        assert ip_matches_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_ipv4_zero_network(self):
        """0.0.0.0/0 匹配所有 IP。"""
        assert ip_matches_cidr("8.8.8.8", "0.0.0.0/0") is True

    def test_ipv4_single_host(self):
        """单个主机（非 CIDR）匹配。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.5") is True
        assert ip_matches_cidr("10.0.0.6", "10.0.0.5") is False

    # ── IPv6 匹配 ──

    def test_ipv6_exact_match(self):
        """IPv6 精确匹配。"""
        assert ip_matches_cidr("::1", "::1/128") is True

    def test_ipv6_in_subnet(self):
        """IPv6 在 CIDR 段内。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32") is True

    def test_ipv6_outside_subnet(self):
        """IPv6 不在 CIDR 段内。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db9::/32") is False

    def test_ipv6_loopback(self):
        """IPv6 回环地址。"""
        assert ip_matches_cidr("::1", "::1/128") is True

    # ── 边界条件 ──

    def test_invalid_ip_returns_false(self):
        """无效 IP 字符串返回 False。"""
        assert ip_matches_cidr("not-an-ip", "192.168.1.0/24") is False

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 字符串返回 False。"""
        assert ip_matches_cidr("192.168.1.1", "not-a-cidr") is False

    def test_empty_strings_returns_false(self):
        """空字符串返回 False。"""
        assert ip_matches_cidr("", "") is False

    def test_ipv4_mapped_ipv6(self):
        """IPv4-mapped IPv6 地址。"""
        assert ip_matches_cidr("::ffff:192.168.1.1", "192.168.1.1/32") is False

    # ── 边界网络段 ──

    def test_subnet_boundary_first_ip(self):
        """子网第一个 IP。"""
        assert ip_matches_cidr("192.168.1.0", "192.168.1.0/24") is True

    def test_subnet_boundary_last_ip(self):
        """子网最后一个 IP。"""
        assert ip_matches_cidr("192.168.1.255", "192.168.1.0/24") is True

    # ── 跨协议不匹配 ──

    def test_ipv4_not_match_ipv6_cidr(self):
        """IPv4 不匹配 IPv6 CIDR。"""
        assert ip_matches_cidr("192.168.1.1", "::1/128") is False

    def test_ipv6_not_match_ipv4_cidr(self):
        """IPv6 不匹配 IPv4 CIDR。"""
        assert ip_matches_cidr("::1", "192.168.1.0/24") is False