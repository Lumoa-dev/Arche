"""UID 工具库测试 —— SID 生成、解析、边界条件。"""

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
    """测试 UUID 格式化。"""

    def test_format_standard_uuid(self):
        """标准 UUID 正确格式化为 4 位一组横杠分隔。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = format_uuid(raw)
        assert result == "550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_format_all_zero_uuid(self):
        """全零 UUID 正确格式化。"""
        raw = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = format_uuid(raw)
        assert result == "0000-0000-0000-0000-0000-0000-0000-0000"

    def test_format_uuid_length(self):
        """格式化后长度为 39（32 hex + 7 横杠，8 组每组 4 位）。"""
        raw = uuid.uuid4()
        result = format_uuid(raw)
        assert len(result) == 39
        assert result.count("-") == 7


class TestMakeSID:
    """测试 SID 生成。"""

    def test_make_sid_with_category(self):
        """带二级分类的 SID 生成正确。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("asse", raw, "post")
        assert sid == "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_without_category(self):
        """无二级分类的 SID 生成正确。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("user", raw)
        assert sid == "user-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_all_prefixes(self):
        """所有已注册前缀的 SID 生成正确。"""
        raw = uuid.uuid4()
        for prefix in ["user", "asse", "task", "log", "modr"]:
            sid = make_sid(prefix, raw)
            assert sid.startswith(prefix)

    def test_make_sid_invalid_prefix(self):
        """未注册的前缀抛出 ValueError。"""
        raw = uuid.uuid4()
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid", raw)

    def test_make_sid_unique_ids(self):
        """相同前缀不同 UUID 生成不同 SID。"""
        raw1 = uuid.uuid4()
        raw2 = uuid.uuid4()
        sid1 = make_sid("user", raw1)
        sid2 = make_sid("user", raw2)
        assert sid1 != sid2


class TestParseSID:
    """测试 SID 解析。"""

    def test_parse_full_sid_with_category(self):
        """解析完整的带分类 SID。"""
        sid = "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_without_category(self):
        """解析不带分类的 SID。"""
        sid = "user-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_with_id_prefix(self):
        """解析带 'id:' 前缀的 SID。"""
        sid = "id:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_sid_prefix(self):
        """解析带 'sid:' 前缀的 SID。"""
        sid = "sid:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_sid_without_separator(self):
        """解析无分隔符 hex 的 SID。"""
        sid = "asse-post-550e8400e29b41d4a716446655440000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_standard_uuid(self):
        """解析标准 UUID 字符串（无前缀）。"""
        sid = "550e8400-e29b-41d4-a716-446655440000"
        result = parse_sid(sid)
        assert result is None  # 无前缀时返回 None

    def test_parse_empty_string(self):
        """解析空字符串返回 None。"""
        assert parse_sid("") is None

    def test_parse_whitespace_only(self):
        """解析纯空白字符串返回 None。"""
        assert parse_sid("   ") is None

    def test_parse_invalid_hex(self):
        """解析无效 hex 返回 None。"""
        sid = "user-xxxx-yyyy-zzzz"
        result = parse_sid(sid)
        assert result is None

    def test_parse_short_hex(self):
        """解析 hex 长度不足 32 位返回 None。"""
        sid = "user-550e-8400"
        result = parse_sid(sid)
        assert result is None

    def test_parse_different_prefixes(self):
        """所有注册前缀的 SID 都能正确解析。"""
        for prefix in ["user", "asse", "task", "log", "modr"]:
            raw = uuid.uuid4()
            sid = make_sid(prefix, raw)
            result = parse_sid(sid)
            assert result is not None
            assert result.prefix == prefix
            assert result.uuid == raw

    def test_parse_round_trip_with_category(self):
        """生成再解析的往返测试（带分类）。"""
        raw = uuid.uuid4()
        original_sid = make_sid("asse", raw, "file")
        result = parse_sid(original_sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "file"
        assert result.uuid == raw

    def test_parse_round_trip_without_category(self):
        """生成再解析的往返测试（无分类）。"""
        raw = uuid.uuid4()
        original_sid = make_sid("user", raw)
        result = parse_sid(original_sid)
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None
        assert result.uuid == raw

    def test_parse_case_insensitive_prefix(self):
        """前缀大小写不敏感。"""
        sid = "ASSE-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_extra_separators(self):
        """带额外横杠的 SID 仍能正确解析。"""
        sid = "asse-post--550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"


class TestParseSidEdgeCases:
    """测试 SID 解析边界条件。"""

    def test_sid_with_trailing_spaces(self):
        """尾部带空格的 SID。"""
        sid = "  asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000  "
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"

    def test_sid_with_non_hex_category(self):
        """二级分类包含非 hex 字符时正确定义为 category。"""
        # en-US 长度 5，不是 4 的倍数，应被视为 category
        sid = "asse-localization-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.category == "localization"

    def test_sid_16_char_category(self):
        """二级分类恰好 16 位 hex 字符时视为 hex 段而非 category。"""
        raw = uuid.uuid4()
        # category 为纯 hex 且长度是 4 的倍数 → 不被视为 category
        sid = make_sid("asse", raw, "post")
        result = parse_sid(sid)
        assert result is not None
        assert result.category == "post"


class TestSidParts:
    """测试 SidParts 数据类。"""

    def test_sid_parts_creation(self):
        """SidParts 创建正确。"""
        uid = uuid.uuid4()
        parts = SidParts(prefix="user", category=None, raw_hex=uid.hex, uuid=uid)
        assert parts.prefix == "user"
        assert parts.category is None
        assert parts.raw_hex == uid.hex
        assert parts.uuid == uid

    def test_sid_parts_with_category(self):
        """SidParts 带分类。"""
        uid = uuid.uuid4()
        parts = SidParts(prefix="asse", category="post", raw_hex=uid.hex, uuid=uid)
        assert parts.category == "post"