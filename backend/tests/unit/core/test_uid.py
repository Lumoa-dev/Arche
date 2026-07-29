"""SID（Searchable ID）工具库测试。

测试原则：
- 覆盖 format_uuid / make_sid / parse_sid 的输入输出
- 边界情况：无效前缀、空字符串、无分类、带 id:/sid: 前缀、标准 UUID
- 解析兼容性：无分隔符 hex、混合格式
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


class TestFormatUuid:
    """测试 format_uuid 函数。"""

    def test_format_uuid_standard(self):
        """标准 UUID 被格式化为 4 位一组横杠分隔格式。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = format_uuid(raw)
        assert result == "550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_format_uuid_all_zeros(self):
        """全零 UUID 正确格式化。"""
        raw = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = format_uuid(raw)
        assert result == "0000-0000-0000-0000-0000-0000-0000-0000"

    def test_format_uuid_roundtrip(self):
        """format_uuid 的结果应能被 uuid.UUID 正确解析。"""
        raw = uuid.uuid4()
        formatted = format_uuid(raw)
        # 去掉横杠后应为 32 位 hex
        hex_str = formatted.replace("-", "")
        assert len(hex_str) == 32
        assert uuid.UUID(hex=hex_str) == raw


class TestMakeSid:
    """测试 make_sid 函数。"""

    def test_make_sid_with_category(self):
        """带二级分类的 SID 生成。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("asse", raw, category="post")
        assert sid == "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_without_category(self):
        """无二级分类的 SID 生成。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("user", raw)
        assert sid == "user-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_invalid_prefix(self):
        """未注册的前缀应抛出 ValueError。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid", raw)

    def test_make_sid_all_registered_prefixes(self):
        """所有注册前缀都应能生成 SID。"""
        from backend.core.uid import SID_PREFIXES

        raw = uuid.uuid4()
        for prefix in SID_PREFIXES:
            sid = make_sid(prefix, raw)
            assert sid.startswith(prefix)


class TestParseSid:
    """测试 parse_sid 函数。"""

    def test_parse_full_sid(self):
        """解析完整 SID（含二级分类）。"""
        result = parse_sid("asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_without_category(self):
        """解析无二级分类的 SID。"""
        result = parse_sid("user-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_no_separator_hex(self):
        """解析无分隔符 hex 的 SID。"""
        result = parse_sid("asse-post-550e8400e29b41d4a716446655440000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_with_id_prefix(self):
        """解析带 id: 前缀的 SID。"""
        result = parse_sid("id:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_sid_prefix(self):
        """解析带 sid: 前缀的 SID。"""
        result = parse_sid("sid:user-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None

    def test_parse_sid_standard_uuid(self):
        """解析标准 UUID 格式（无前缀），应返回 None。"""
        result = parse_sid("550e8400-e29b-41d4-a716-446655440000")
        # 无前缀时返回 None，由调用方处理
        assert result is None

    def test_parse_sid_empty_string(self):
        """空字符串应返回 None。"""
        assert parse_sid("") is None

    def test_parse_sid_whitespace_only(self):
        """纯空白字符应返回 None。"""
        assert parse_sid("   ") is None

    def test_parse_sid_invalid_hex(self):
        """无效 hex 应返回 None。"""
        result = parse_sid("user-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz")
        assert result is None

    def test_parse_sid_short_hex(self):
        """hex 长度不足 32 位应返回 None。"""
        result = parse_sid("user-550e-8400")
        assert result is None

    def test_parse_sid_case_insensitive_prefix(self):
        """前缀匹配应忽略大小写。"""
        result = parse_sid("USER-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "user"

    def test_parse_sid_roundtrip(self):
        """make_sid → parse_sid 应保持一致。"""
        raw = uuid.uuid4()
        for prefix in ("user", "asse", "task", "log", "modr"):
            for category in (None, "post", "file", "crawl"):
                sid = make_sid(prefix, raw, category=category)
                parsed = parse_sid(sid)
                assert parsed is not None
                assert parsed.prefix == prefix
                assert parsed.category == category
                assert parsed.uuid == raw

    def test_parse_sid_sid_prefix_case_insensitive(self):
        """id:/sid: 前缀应忽略大小写。"""
        result = parse_sid("SID:user-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "user"

    def test_parse_sid_unknown_prefix(self):
        """未知前缀应返回 None。"""
        result = parse_sid("unknown-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is None