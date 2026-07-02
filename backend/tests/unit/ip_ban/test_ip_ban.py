"""IP 封禁插件 单元测试。

当前覆盖：
- ip_matches_cidr() IP 匹配工具函数
"""

from __future__ import annotations

import pytest

from backend.plugins.ip_ban.services import ip_matches_cidr


class TestIpMatchesCidr:
    """ip_matches_cidr IP 匹配行为测试。"""

    # ── IPv4 精确匹配 ──

    def test_ipv4_exact_match(self):
        """IPv4 地址精确匹配 /32 CIDR。"""
        assert ip_matches_cidr("192.168.1.1", "192.168.1.1/32") is True

    def test_ipv4_exact_match_no_prefix(self):
        """不指定前缀长度的 /32 应被视为精确匹配。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.1") is True

    def test_ipv4_no_match(self):
        """不匹配的 IPv4 应返回 False。"""
        assert ip_matches_cidr("192.168.2.1", "192.168.1.0/24") is False

    # ── IPv4 CIDR 范围 ──

    def test_ipv4_in_cidr_range(self):
        """IPv4 地址在 CIDR 范围内应返回 True。"""
        assert ip_matches_cidr("192.168.1.100", "192.168.1.0/24") is True

    def test_ipv4_network_address(self):
        """CIDR 的网络地址本身应匹配。"""
        assert ip_matches_cidr("192.168.1.0", "192.168.1.0/24") is True

    def test_ipv4_broadcast_address(self):
        """CIDR 的广播地址应匹配。"""
        assert ip_matches_cidr("192.168.1.255", "192.168.1.0/24") is True

    # ── IPv6 ──

    def test_ipv6_exact_match(self):
        """IPv6 地址精确匹配。"""
        assert (
            ip_matches_cidr("2001:db8::1", "2001:db8::1/128")
            is True
        )

    def test_ipv6_in_cidr_range(self):
        """IPv6 地址在 CIDR 范围内。"""
        assert (
            ip_matches_cidr("2001:db8::42", "2001:db8::/32")
            is True
        )

    def test_ipv6_no_match(self):
        """IPv6 不匹配 CIDR 范围。"""
        assert (
            ip_matches_cidr("2001:db9::1", "2001:db8::/32")
            is False
        )

    # ── 边界条件 ──

    def test_single_ip_no_cidr(self):
        """单个 IP 字符串（无 /前缀）应精确匹配。"""
        assert ip_matches_cidr("10.0.0.5", "10.0.0.5") is True

    def test_invalid_ip_returns_false(self):
        """无效的 IP 字符串应返回 False。"""
        assert ip_matches_cidr("not-an-ip", "10.0.0.0/8") is False

    def test_invalid_cidr_returns_false(self):
        """无效的 CIDR 字符串应返回 False。"""
        assert ip_matches_cidr("10.0.0.1", "not-a-cidr") is False

    def test_single_ip_not_in_range(self):
        """单个 IP 不在指定 CIDR 范围内。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.1.0/24") is False

    # ── 实用场景 ──

    def test_private_ip_ranges(self):
        """私有 IP 范围 10.x.x.x 匹配。"""
        assert ip_matches_cidr("10.0.0.1", "10.0.0.0/8") is True
        assert ip_matches_cidr("10.255.255.255", "10.0.0.0/8") is True
        assert ip_matches_cidr("11.0.0.1", "10.0.0.0/8") is False

    def test_localhost(self):
        """localhost (127.0.0.1) 匹配 127.0.0.0/8。"""
        assert ip_matches_cidr("127.0.0.1", "127.0.0.0/8") is True
        assert ip_matches_cidr("127.255.255.255", "127.0.0.0/8") is True