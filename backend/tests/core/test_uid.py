"""UID 工具库单元测试 —— SID 生成、格式化、解析。"""

from __future__ import annotations

import uuid

import pytest

from backend.core.uid import (
    SidParts,
    format_uuid,
    make_sid,
    parse_sid,
)


class TestFormatUUID:
    def test_format_uuid(self):
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = format_uuid(raw)
        assert result == "550e-8400-e29b-41d4-a716-4466-5544-0000"
        assert len(result.replace("-", "")) == 32

    def test_format_uuid_preserves_hex(self):
        raw = uuid.uuid4()
        result = format_uuid(raw)
        assert result.replace("-", "") == raw.hex

    def test_format_uuid_segments(self):
        raw = uuid.UUID("12345678-1234-5678-1234-567812345678")
        result = format_uuid(raw)
        assert result.count("-") == 7


class TestMakeSID:
    def test_make_sid_with_category(self):
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("asse", raw, "post")
        assert sid == "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_without_category(self):
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("user", raw)
        assert sid == "user-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_raises_on_unknown_prefix(self):
        raw = uuid.uuid4()
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid_prefix", raw)

    def test_make_sid_all_valid_prefixes(self):
        from backend.core.uid import SID_PREFIXES

        raw = uuid.uuid4()
        for prefix in SID_PREFIXES:
            sid = make_sid(prefix, raw)
            assert sid.startswith(prefix)


class TestParseSID:
    def test_parse_full_sid(self):
        result = parse_sid("asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_no_category(self):
        result = parse_sid("user-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None

    def test_parse_no_separator_hex(self):
        """无分隔符的 hex 也能解析。"""
        result = parse_sid("asse-post-550e8400e29b41d4a716446655440000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_with_id_prefix(self):
        result = parse_sid("id:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_with_sid_prefix(self):
        result = parse_sid("sid:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_standard_uuid(self):
        """标准 UUID 字符串，无前缀。"""
        result = parse_sid("550e8400-e29b-41d4-a716-446655440000")
        # 无前缀时返回 None
        assert result is None

    def test_parse_empty_string(self):
        assert parse_sid("") is None

    def test_parse_whitespace_only(self):
        assert parse_sid("   ") is None

    def test_parse_invalid_hex(self):
        """无效 hex 返回 None。"""
        result = parse_sid("user-zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz")
        # 32 位非 hex 字符, 无法通过校验
        assert result is None

    def test_parse_roundtrip(self):
        """make_sid → parse_sid 往返。"""
        raw = uuid.uuid4()
        sid = make_sid("asse", raw, "file")
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "file"
        assert result.uuid == raw

    def test_parse_short_hex_returns_none(self):
        """长度不足 32 的 hex 返回 None。"""
        result = parse_sid("user-550e-8400")
        assert result is None

    def test_parse_nonexistent_prefix(self):
        """不存在的 prefix 作为普通字符串处理，无法解析。"""
        result = parse_sid("unknown-550e-8400-e29b-41d4-a716-4466-5544-0000")
        # prefix 不匹配 → 尝试作为纯 UUID 解析 → 前缀 unknown 无法通过 → None
        assert result is None
