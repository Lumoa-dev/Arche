"""ip_matches_cidr 函数测试。

覆盖：
- IPv4 精确匹配 / CIDR 段匹配 / 不匹配
- IPv6 匹配
- 边界条件（无效 IP、无效 CIDR、空字符串）
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.services import ip_matches_cidr


class TestIpMatchesCIDR:
    """ip_matches_cidr 行为测试。"""

    def test_ipv4_exact_match(self):
        """IPv4 精确 IP 匹配自身。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1")

    def test_ipv4_in_cidr_range(self):
        """IPv4 在 CIDR 段内应匹配。"""
        assert ip_matches_cidr("192.168.1.50", "192.168.1.0/24")

    def test_ipv4_not_in_cidr_range(self):
        """IPv4 不在 CIDR 段内不应匹配。"""
        assert not ip_matches_cidr("10.0.0.1", "192.168.1.0/24")

    def test_ipv4_cidr_single_host(self):
        """IPv4 /32 精确匹配 CIDR。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.5/32")
        assert not ip_matches_cidr("10.0.0.6", "10.0.0.5/32")

    def test_ipv4_large_cidr(self):
        """IPv4 大段 CIDR（如 /8）。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.0/8")
        assert ip_matches_cidr("10.255.255.255", "10.0.0.0/8")
        assert not ip_matches_cidr("11.0.0.1", "10.0.0.0/8")

    def test_ipv6_exact_match(self):
        """IPv6 精确 IP 匹配自身。"""
        assert ip_matches_cidr("::1", "::1")

    def test_ipv6_in_cidr_range(self):
        """IPv6 在 CIDR 段内应匹配。"""
        assert ip_matches_cidr("2001:db8::1", "2001:db8::/32")

    def test_invalid_ip_returns_false(self):
        """无效 IP 字符串返回 False。"""
        assert not ip_matches_cidr("not-an-ip", "192.168.1.0/24")

    def test_invalid_cidr_returns_false(self):
        """无效 CIDR 返回 False。"""
        assert not ip_matches_cidr("192.168.1.1", "not-a-cidr")

    def test_empty_ip_returns_false(self):
        """空 IP 返回 False。"""
        assert not ip_matches_cidr("", "192.168.1.0/24")

    def test_empty_cidr_returns_false(self):
        """空 CIDR 返回 False。"""
        assert not ip_matches_cidr("192.168.1.1", "")

    def test_ipv4_matches_cidr_any(self):
        """0.0.0.0/0 匹配所有 IPv4。"""
        assert ip_matches_cidr("1.2.3.4", "0.0.0.0/0")
        assert ip_matches_cidr("255.255.255.255", "0.0.0.0/0")