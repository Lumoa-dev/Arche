"""核心 — UID/SID 工具单元测试。

覆盖 format_uuid / make_sid / parse_sid 的全部路径：
正规路径、边界条件、非法输入。
纯 mock，无数据库依赖。
"""

from __future__ import annotations

import uuid

import pytest

from backend.core.uid import (
    SidParts,
    _build_sid_parts,
    _clean_hex,
    _is_pure_hex_segment,
    format_uuid,
    make_sid,
    parse_sid,
)


class TestFormatUuid:
    """UUID 格式化测试。"""

    def test_format_standard_uuid(self):
        u = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = format_uuid(u)
        # 每 4 位一组横杠分隔
        assert result == "550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_format_all_zero_uuid(self):
        u = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = format_uuid(u)
        assert result == "0000-0000-0000-0000-0000-0000-0000-0000"


class TestMakeSid:
    """SID 生成测试。"""

    def test_make_sid_with_category(self):
        u = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("asse", u, category="post")
        assert sid == "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_without_category(self):
        u = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("user", u)
        assert sid == "user-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_invalid_prefix(self):
        u = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid", u)

    def test_make_sid_empty_category(self):
        """空字符串 category 视为 None，无分类段。"""
        u = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("asse", u, category="")
        # 空字符串在 if category: 判断中为 False，所以无 category 段
        assert sid.startswith("asse-")


class TestParseSid:
    """SID 解析测试。"""

    def test_parse_full_sid(self):
        sid = "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert isinstance(result, SidParts)
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_without_category(self):
        sid = "user-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None

    def test_parse_sid_with_id_prefix(self):
        sid = "id:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_sid_prefix(self):
        sid = "sid:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_no_separator_hex(self):
        """无分隔符的 hex 也应能解析。"""
        sid = "asse-post-550e8400e29b41d4a716446655440000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_standard_uuid(self):
        """纯 UUID 格式应返回 None（无前缀）。"""
        result = parse_sid("550e8400-e29b-41d4-a716-446655440000")
        assert result is None

    def test_parse_empty_string(self):
        assert parse_sid("") is None

    def test_parse_whitespace_only(self):
        assert parse_sid("   ") is None

    def test_parse_nonexistent_prefix(self):
        sid = "unknown-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is None

    def test_parse_invalid_hex(self):
        sid = "asse-post-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
        result = parse_sid(sid)
        assert result is None

    def test_parse_truncated_hex(self):
        """不到 32 位的 hex 返回 None。"""
        sid = "user-550e-8400"
        result = parse_sid(sid)
        # 解析出的 raw_hex 会不足 32 位
        assert result is None

    def test_parse_case_insensitive_prefix(self):
        sid = "ASSE-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_leading_trailing_spaces(self):
        sid = "  asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000  "
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"


class TestInternalHelpers:
    """内部辅助函数测试。"""

    def test_clean_hex_removes_non_hex(self):
        assert _clean_hex("550e-8400-xyz!") == "550e8400"

    def test_clean_hex_empty(self):
        assert _clean_hex("") == ""

    def test_clean_hex_all_valid(self):
        assert _clean_hex("550e8400e29b") == "550e8400e29b"

    def test_is_pure_hex_segment_valid(self):
        assert _is_pure_hex_segment("550e") is True

    def test_is_pure_hex_segment_invalid_chars(self):
        assert _is_pure_hex_segment("55oe") is False

    def test_is_pure_hex_segment_wrong_length(self):
        assert _is_pure_hex_segment("550") is False

    def test_is_pure_hex_segment_empty(self):
        assert _is_pure_hex_segment("") is False

    def test_build_sid_parts_valid(self):
        result = _build_sid_parts("asse", "post", "550e8400e29b41d4a716446655440000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_build_sid_parts_wrong_hex_length(self):
        result = _build_sid_parts("asse", "post", "1234")
        assert result is None

    def test_build_sid_parts_invalid_hex(self):
        result = _build_sid_parts("asse", "post", "X" * 32)
        assert result is None

    def test_build_sid_parts_no_prefix(self):
        result = _build_sid_parts(None, None, "550e8400e29b41d4a716446655440000")
        assert result is not None
        assert result.prefix == ""


class TestRoundtrip:
    """生成→解析的往返测试。"""

    def test_roundtrip_with_category(self):
        u = uuid.uuid4()
        sid = make_sid("asse", u, category="post")
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "post"
        assert parsed.uuid == u

    def test_roundtrip_without_category(self):
        u = uuid.uuid4()
        sid = make_sid("user", u)
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "user"
        assert parsed.category is None
        assert parsed.uuid == u

    def test_roundtrip_log_prefix(self):
        u = uuid.uuid4()
        sid = make_sid("log", u, category="crawl")
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "log"
        assert parsed.category == "crawl"

    def test_roundtrip_task_prefix(self):
        u = uuid.uuid4()
        sid = make_sid("task", u, category="train")
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "task"