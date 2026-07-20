"""SID (Searchable ID) 工具函数测试。"""

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
    """测试 UUID 格式化。"""

    def test_format_uuid_standard(self):
        """标准 UUID 被格式化为每 4 位一组。"""
        u = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = format_uuid(u)
        assert result == "550e-8400-e29b-41d4-a716-4466-5544-0000"
        assert len(result) == 39  # 32 hex + 7 横杠（8 组，每 4 位一组）

    def test_format_uuid_roundtrip(self):
        """格式化后反解析应得到原始 UUID。"""
        original = uuid.uuid4()
        formatted = format_uuid(original)
        hex_str = formatted.replace("-", "")
        restored = uuid.UUID(hex=hex_str)
        assert restored == original


class TestMakeSid:
    """测试 SID 生成。"""

    def test_make_sid_without_category(self):
        """无分类时生成 prefix-uuid 格式。"""
        u = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = make_sid("user", u)
        assert result.startswith("user-")
        assert "550e" in result

    def test_make_sid_with_category(self):
        """有分类时生成 prefix-category-uuid 格式。"""
        u = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = make_sid("asse", u, category="post")
        assert result.startswith("asse-post-")

    def test_make_sid_invalid_prefix_raises(self):
        """未注册的前缀抛 ValueError。"""
        u = uuid.uuid4()
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid", u)

    def test_make_sid_all_registered_prefixes(self):
        """所有已注册的前缀都应能生成 SID。"""
        from backend.core.uid import SID_PREFIXES

        u = uuid.uuid4()
        for prefix in SID_PREFIXES:
            result = make_sid(prefix, u)
            assert result.startswith(f"{prefix}-")


class TestParseSid:
    """测试 SID 解析。"""

    def test_parse_full_sid_with_category(self):
        """解析完整 SID（含分类）。"""
        result = parse_sid("asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_without_category(self):
        """解析无分类 SID。"""
        result = parse_sid("user-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None

    def test_parse_sid_no_separator_hex(self):
        """解析无分隔符 hex 格式的 SID。"""
        result = parse_sid("asse-post-550e8400e29b41d4a716446655440000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

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

    def test_parse_standard_uuid(self):
        """解析纯标准 UUID 返回 None（无前缀无法解析）。"""
        result = parse_sid("550e8400-e29b-41d4-a716-446655440000")
        assert result is None

    def test_parse_empty_string_returns_none(self):
        """空字符串返回 None。"""
        assert parse_sid("") is None
        assert parse_sid("   ") is None

    def test_parse_invalid_sid_returns_none(self):
        """无效 SID 返回 None。"""
        assert parse_sid("not-a-valid-sid") is None

    def test_parse_short_hex_returns_none(self):
        """hex 长度不足 32 位返回 None。"""
        result = parse_sid("user-550e-8400")
        assert result is None

    def test_parse_case_insensitive_prefix(self):
        """前缀大小写不敏感。"""
        result = parse_sid("Asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_sid_roundtrip(self):
        """生成后再解析应得到原始信息。"""
        u = uuid.uuid4()
        sid = make_sid("asse", u, category="file")
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "file"
        assert parsed.uuid == u