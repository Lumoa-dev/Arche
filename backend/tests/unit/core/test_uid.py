"""UID 工具库单元测试 —— SID 生成、格式化、解析。

测试重点：
- format_uuid / make_sid / parse_sid 核心函数
- 6 种输入格式兼容性（完整SID / 无分类 / 无分隔符 / id:前缀 / sid:前缀 / 标准UUID）
- 无效输入的错误处理和返回值
- 边界条件：空字符串、无效前缀、畸形hex
"""

from __future__ import annotations

import uuid

import pytest

from backend.core.uid import (
    SidParts,
    _clean_hex,
    _is_pure_hex_segment,
    format_uuid,
    make_sid,
    parse_sid,
)


# =============================================================================
# format_uuid
# =============================================================================


class TestFormatUUID:
    """UUID 格式化测试。"""

    def test_format_standard_uuid(self):
        """标准 UUID 应格式化为 8 组 4 位 hex 加横杠。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = format_uuid(raw)
        assert result == "550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_format_another_uuid(self):
        """不同 UUID 应正确格式化。"""
        raw = uuid.UUID("00000000-0000-0000-0000-000000000001")
        result = format_uuid(raw)
        assert result == "0000-0000-0000-0000-0000-0000-0000-0001"

    def test_format_all_zeros(self):
        """全零 UUID 应正确格式化。"""
        raw = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = format_uuid(raw)
        assert result == "0000-0000-0000-0000-0000-0000-0000-0000"

    def test_format_all_ones(self):
        """全 F UUID 应正确格式化。"""
        raw = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        result = format_uuid(raw)
        assert result == "ffff-ffff-ffff-ffff-ffff-ffff-ffff-ffff"


# =============================================================================
# make_sid
# =============================================================================


class TestMakeSID:
    """SID 生成测试。"""

    def test_make_sid_with_category(self):
        """带二级分类应生成 asse-post-xxxx 格式。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = make_sid("asse", raw, category="post")
        assert result == "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_without_category(self):
        """无二级分类应生成 user-xxxx 格式。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = make_sid("user", raw)
        assert result == "user-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_invalid_prefix(self):
        """未注册的前缀应抛出 ValueError。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid", raw)

    def test_make_sid_all_prefixes(self):
        """所有已注册前缀应正常工作。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        prefixes = ["user", "asse", "task", "log", "modr"]
        for prefix in prefixes:
            result = make_sid(prefix, raw)
            assert result.startswith(prefix)

    def test_make_sid_category_with_hyphen(self):
        """分类含横杠应正确处理。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = make_sid("asse", raw, category="deep-link")
        assert result.startswith("asse-deep-link-")


# =============================================================================
# parse_sid
# =============================================================================


class TestParseSID:
    """SID 解析测试 —— 6 种输入格式。"""

    def test_parse_full_sid(self):
        """完整 SID 格式（asse-post-xxxx）应正确解析。"""
        result = parse_sid(
            "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        )
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.raw_hex == "550e8400e29b41d4a716446655440000"
        assert isinstance(result.uuid, uuid.UUID)

    def test_parse_sid_without_category(self):
        """无二级分类 SID（user-xxxx）应正确解析。"""
        result = parse_sid("user-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None

    def test_parse_sid_no_separator_hex(self):
        """无分隔符 hex 格式（asse-post-550e8400...）应正确解析。"""
        result = parse_sid(
            "asse-post-550e8400e29b41d4a716446655440000"
        )
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_id_prefix(self):
        """id: 前缀格式应正确解析。"""
        result = parse_sid(
            "id:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        )
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_sid_prefix(self):
        """sid: 前缀格式应正确解析。"""
        result = parse_sid(
            "SID:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        )
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_standard_uuid(self):
        """标准 UUID 输入应返回 None（无前缀时 _parse_as_raw_uuid 返回 None）。"""
        result = parse_sid("550e8400-e29b-41d4-a716-446655440000")
        assert result is None

    def test_parse_mixed_case_prefix(self):
        """前缀大小写不敏感。"""
        result = parse_sid(
            "ASSE-POST-550e-8400-e29b-41d4-a716-4466-5544-0000"
        )
        assert result is not None
        assert result.prefix == "asse"
        # 分类保留原始大小写
        assert result.category == "POST"


class TestParseSIDEdgeCases:
    """SID 解析边界条件测试。"""

    def test_parse_empty_string(self):
        """空字符串应返回 None。"""
        assert parse_sid("") is None

    def test_parse_whitespace_only(self):
        """纯空白字符串应返回 None。"""
        assert parse_sid("   ") is None

    def test_parse_invalid_prefix(self):
        """未知前缀应尝试解析为 UUID，但非 UUID 格式返回 None。"""
        result = parse_sid("unknown-prefix-aaaa")
        assert result is None

    def test_parse_truncated_hex(self):
        """不完整的 hex（不足 32 位）应返回 None。"""
        result = parse_sid("user-550e-8400")
        assert result is None

    def test_parse_invalid_hex_chars(self):
        """含非法 hex 字符的 SID 应返回 None。"""
        result = parse_sid(
            "asse-post-zzzz-8400-e29b-41d4-a716-4466-5544-0000"
        )
        assert result is None

    def test_parse_category_is_numeric(self):
        """分类为数字时仍应识别为 category（带非 hex 字符的数字段）。"""
        # "1234" 是纯 hex（4位），会被视为 hex 段而非 category
        # 使用 "123x" 确保包含非 hex 字符
        result = parse_sid("asse-123x-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "123x"

    def test_parse_long_category(self):
        """长分类名称（无额外横杠）应正确处理。"""
        result = parse_sid(
            "asse-verylongname-550e-8400-e29b-41d4-a716-4466-5544-0000"
        )
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "verylongname"

    def test_parse_with_trailing_spaces(self):
        """尾部空白应在 strip 后被忽略。"""
        result = parse_sid(
            "user-550e-8400-e29b-41d4-a716-4466-5544-0000  "
        )
        assert result is not None
        assert result.prefix == "user"

    def test_parse_extra_segments_ignored(self):
        """额外段应被忽略（合并到 hex 中可能产生无效 hex）。"""
        result = parse_sid(
            "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000-extra"
        )
        # 多余的 extra 会导致 hex 长度 > 32
        assert result is None


class TestParseSIDWithIdPrefix:
    """带 id:/sid: 前缀的 SID 解析。"""

    def test_id_prefix_with_spaces(self):
        """id: 后带空格应正确解析。"""
        result = parse_sid(
            "id: asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        )
        assert result is not None
        assert result.prefix == "asse"

    def test_sid_prefix_uppercase(self):
        """SID: 大写前缀应正确解析。"""
        result = parse_sid(
            "SID:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        )
        assert result is not None
        assert result.prefix == "asse"

    def test_only_id_prefix_no_sid(self):
        """只有 id: 前缀但没有有效 SID 应返回 None。"""
        result = parse_sid("id:invalid")
        assert result is None


# =============================================================================
# 内部工具函数
# =============================================================================


class TestCleanHex:
    """_clean_hex 工具函数测试。"""

    def test_removes_dashes(self):
        """应移除横杠。"""
        assert _clean_hex("550e-8400") == "550e8400"

    def test_removes_non_hex_chars(self):
        """应移除非 hex 字符。"""
        assert _clean_hex("55 0e 84 00") == "550e8400"

    def test_preserves_valid_hex(self):
        """纯 hex 字符串应保持不变。"""
        assert _clean_hex("550e8400") == "550e8400"

    def test_empty_string(self):
        """空字符串应返回空字符串。"""
        assert _clean_hex("") == ""

    def test_all_invalid_chars(self):
        """全非法字符应返回空字符串。"""
        assert _clean_hex("xyz!@#") == ""


class TestIsPureHexSegment:
    """_is_pure_hex_segment 工具函数测试。"""

    def test_valid_hex_4_chars(self):
        """4 位纯 hex 返回 True。"""
        assert _is_pure_hex_segment("550e") is True

    def test_valid_hex_8_chars(self):
        """8 位纯 hex 返回 True。"""
        assert _is_pure_hex_segment("550e8400") is True

    def test_non_hex_characters(self):
        """含非 hex 字符返回 False。"""
        assert _is_pure_hex_segment("55oe") is False

    def test_length_not_multiple_of_4(self):
        """长度不是 4 的倍数返回 False。"""
        assert _is_pure_hex_segment("550") is False

    def test_empty_string(self):
        """空字符串返回 False。"""
        assert _is_pure_hex_segment("") is False

    def test_mixed_case_hex(self):
        """大小写混合 hex 返回 True。"""
        assert _is_pure_hex_segment("AbCd") is True