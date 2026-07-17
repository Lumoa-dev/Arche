"""SID（Searchable ID）工具库测试。

覆盖：
- format_uuid 格式化
- make_sid 生成（含前缀验证、分类）
- parse_sid 解析（含多种输入格式兼容）
- 边界条件（空字符串、无效前缀、无效 hex、标准 UUID 输入）
"""

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
    """format_uuid 测试。"""

    def test_format_standard_uuid(self):
        """标准 UUID 正确格式化为 4 位一组。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = format_uuid(raw)
        assert result == "550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_format_all_zero_uuid(self):
        """全零 UUID 正确格式化。"""
        raw = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = format_uuid(raw)
        assert result == "0000-0000-0000-0000-0000-0000-0000-0000"

    def test_format_random_uuid_length(self):
        """格式化结果始终为 39 位（32 hex + 7 横杠）。"""
        raw = uuid.uuid4()
        result = format_uuid(raw)
        assert len(result) == 39
        assert result.count("-") == 7


class TestMakeSID:
    """make_sid 测试。"""

    def test_make_sid_without_category(self):
        """无分类时生成 {prefix}-{formatted_uuid} 格式。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = make_sid("user", raw)
        assert result == "user-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_with_category(self):
        """有分类时生成 {prefix}-{category}-{formatted_uuid} 格式。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = make_sid("asse", raw, "post")
        assert result == "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_invalid_prefix_raises(self):
        """未注册的前缀抛出 ValueError。"""
        raw = uuid.uuid4()
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid", raw)

    def test_make_sid_empty_prefix_raises(self):
        """空前缀抛出 ValueError。"""
        raw = uuid.uuid4()
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("", raw)

    def test_make_sid_registered_prefixes(self):
        """所有注册的前缀都能正常生成 SID。"""
        raw = uuid.uuid4()
        for prefix in ["user", "asse", "task", "log", "modr"]:
            sid = make_sid(prefix, raw)
            assert sid.startswith(prefix)


class TestParseSID:
    """parse_sid 测试。"""

    def test_parse_full_sid(self):
        """解析完整 SID（含 category）。"""
        result = parse_sid("asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_without_category(self):
        """解析无 category 的 SID。"""
        result = parse_sid("user-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None

    def test_parse_sid_with_id_prefix(self):
        """解析带 id: 前缀的 SID。"""
        result = parse_sid("id:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_sid_prefix(self):
        """解析带 sid: 前缀的 SID。"""
        result = parse_sid("sid:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_standard_uuid_returns_none(self):
        """标准 UUID 输入无前缀，返回 None。"""
        result = parse_sid("550e8400-e29b-41d4-a716-446655440000")
        assert result is None

    def test_parse_raw_hex_returns_none(self):
        """无分隔符 hex 输入无前缀，返回 None。"""
        result = parse_sid("550e8400e29b41d4a716446655440000")
        assert result is None

    def test_parse_empty_string(self):
        """空字符串返回 None。"""
        assert parse_sid("") is None

    def test_parse_whitespace_string(self):
        """纯空白字符串返回 None。"""
        assert parse_sid("   ") is None

    def test_parse_invalid_hex_returns_none(self):
        """无效 hex 内容返回 None。"""
        result = parse_sid("user-zzzz-xxxx-xxxx-xxxx-xxxx-xxxx-xxxx-xxxx")
        assert result is None

    def test_parse_truncated_hex_returns_none(self):
        """长度不足 32 的 hex 返回 None。"""
        result = parse_sid("user-550e-8400")
        assert result is None

    def test_parse_unknown_prefix_no_category(self):
        """未注册前缀当作无前缀处理，返回 None。"""
        # 未知前缀 "xyz" 不在 _SID_PREFIX_LIST 中，走无前缀逻辑
        result = parse_sid("xyz-550e-8400-e29b-41d4-a716-4466-5544-0000")
        # 因为 "xyz" 不是注册前缀，所以被当作无前缀处理，hex 长度不足 32 返回 None
        assert result is None

    def test_parse_case_insensitive_prefix(self):
        """前缀大小写不敏感。"""
        result = parse_sid("ASSE-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_sid_with_leading_trailing_spaces(self):
        """前后空白被 strip。"""
        result = parse_sid("  user-550e-8400-e29b-41d4-a716-4466-5544-0000  ")
        assert result is not None
        assert result.prefix == "user"

    def test_parse_sid_roundtrip(self):
        """make_sid → parse_sid 往返一致。"""
        raw = uuid.uuid4()
        sid = make_sid("asse", raw, "file")
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "file"
        assert parsed.uuid == raw

    def test_parse_sid_roundtrip_no_category(self):
        """无 category 的往返一致。"""
        raw = uuid.uuid4()
        sid = make_sid("user", raw)
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "user"
        assert parsed.category is None
        assert parsed.uuid == raw


class TestSidParts:
    """SidParts dataclass 测试。"""

    def test_sid_parts_dataclass(self):
        """SidParts 正确持有数据。"""
        raw = uuid.uuid4()
        parts = SidParts(prefix="asse", category="post", raw_hex=raw.hex, uuid=raw)
        assert parts.prefix == "asse"
        assert parts.category == "post"
        assert parts.raw_hex == raw.hex
        assert parts.uuid == raw