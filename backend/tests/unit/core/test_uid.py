"""SID (Searchable ID) 工具库测试。

测试原则：
- 纯函数测试，无外部依赖
- 覆盖 format_uuid, make_sid, parse_sid 的典型路径和边缘情况
- 验证与文档中的 doctest 示例一致
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

# 测试用 UUID
TEST_UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
TEST_UUID_HEX = "550e-8400-e29b-41d4-a716-4466-5544-0000"


class TestFormatUuid:
    """UUID 格式化测试。"""

    def test_format_standard_uuid(self):
        """标准 UUID 应格式化为 8 组 4 位 hex。"""
        result = format_uuid(TEST_UUID)
        assert result == TEST_UUID_HEX
        assert len(result.replace("-", "")) == 32

    def test_format_another_uuid(self):
        """其他 UUID 也应正确格式化。"""
        u = uuid.UUID("00000000-0000-0000-0000-000000000000")
        assert format_uuid(u) == "0000-0000-0000-0000-0000-0000-0000-0000"

    def test_format_random_uuid_consistent(self):
        """同一 UUID 格式化结果应一致。"""
        u = uuid.uuid4()
        assert format_uuid(u) == format_uuid(u)


class TestMakeSid:
    """SID 生成测试。"""

    def test_make_sid_with_category(self):
        """带二级分类的 SID 应正确生成。"""
        result = make_sid("asse", TEST_UUID, "post")
        assert result == f"asse-post-{TEST_UUID_HEX}"

    def test_make_sid_without_category(self):
        """无二级分类的 SID 应正确生成。"""
        result = make_sid("user", TEST_UUID)
        assert result == f"user-{TEST_UUID_HEX}"

    def test_make_sid_unknown_prefix(self):
        """未注册的前缀应抛出 ValueError。"""
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid", TEST_UUID)

    def test_make_sid_all_registered_prefixes(self):
        """所有注册前缀都应能生成 SID。"""
        from backend.core.uid import SID_PREFIXES

        for prefix in SID_PREFIXES:
            result = make_sid(prefix, TEST_UUID)
            assert result.startswith(f"{prefix}-")

    def test_make_sid_roundtrip(self):
        """make_sid 后再 parse_sid 应得到原始信息。"""
        sid = make_sid("asse", TEST_UUID, "file")
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "file"
        assert parsed.uuid == TEST_UUID


class TestParseSid:
    """SID 解析测试。"""

    def test_parse_full_sid(self):
        """完整 SID 应解析出 prefix, category, uuid。"""
        sid = f"asse-post-{TEST_UUID_HEX}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == TEST_UUID

    def test_parse_sid_without_category(self):
        """无 category 的 SID 应正确解析。"""
        sid = f"user-{TEST_UUID_HEX}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None
        assert result.uuid == TEST_UUID

    def test_parse_prefixed_id(self):
        """带 id: 前缀的 SID 应正确解析。"""
        result = parse_sid(f"id:asse-post-{TEST_UUID_HEX}")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_prefixed_sid(self):
        """带 sid: 前缀的 SID 应正确解析。"""
        result = parse_sid(f"sid:asse-post-{TEST_UUID_HEX}")
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_raw_uuid(self):
        """纯 UUID 字符串（无前缀）当前返回 None（_parse_as_raw_uuid 未实现）。"""
        # 当前实现中 _parse_as_raw_uuid 始终返回 None
        result = parse_sid(str(TEST_UUID))
        assert result is None

    def test_parse_raw_hex(self):
        """纯 32 位 hex 字符串（无前缀）当前返回 None（_parse_as_raw_uuid 未实现）。"""
        result = parse_sid(TEST_UUID.hex)
        assert result is None

    def test_parse_compact_hex(self):
        """无分隔符的 hex 应能被正确解析。"""
        sid = f"asse-post-{TEST_UUID.hex}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == TEST_UUID

    def test_parse_empty_string(self):
        """空字符串应返回 None。"""
        assert parse_sid("") is None

    def test_parse_whitespace_only(self):
        """纯空白字符串应返回 None。"""
        assert parse_sid("   ") is None

    def test_parse_invalid_sid(self):
        """无效 SID 应返回 None。"""
        assert parse_sid("this-is-not-a-valid-sid") is None

    def test_parse_too_short_hex(self):
        """hex 太短的 SID 应返回 None。"""
        result = parse_sid("asse-post-550e")
        assert result is None

    def test_parse_leading_trailing_spaces(self):
        """SID 带前后空格应能正常解析。"""
        sid = f"  asse-post-{TEST_UUID_HEX}  "
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_case_insensitive_prefix(self):
        """前缀匹配应不区分大小写。"""
        sid = f"ASSE-post-{TEST_UUID_HEX}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_numeric_category(self):
        """二级分类可以是数字。"""
        # 生成一个 SID，其中 category 是纯数字
        raw_hex = format_uuid(TEST_UUID)
        # 数字段如果全是 hex 且长度为 4 的倍数会被视为 hex 段
        sid = f"asse-123-{raw_hex}"
        result = parse_sid(sid)
        # "123" 长度为 3，不是 4 的倍数，所以会被视为 category
        assert result is not None
        assert result.category == "123"


class TestCleanHex:
    """clean_hex 工具函数测试。"""

    def test_clean_hex_only_hex(self):
        """纯 hex 字符串不变。"""
        assert _clean_hex("550e8400e29b") == "550e8400e29b"

    def test_clean_hex_with_dashes(self):
        """带横杠的 hex 应移除横杠。"""
        assert _clean_hex("550e-8400-e29b") == "550e8400e29b"

    def test_clean_hex_with_spaces(self):
        """带空格的 hex 应移除空格。"""
        assert _clean_hex("550e 8400 e29b") == "550e8400e29b"

    def test_clean_hex_non_hex_removed(self):
        """非 hex 字符应被移除。"""
        assert _clean_hex("55 0e-84*00") == "550e8400"

    def test_clean_hex_empty(self):
        """空字符串返回空。"""
        assert _clean_hex("") == ""


class TestIsPureHexSegment:
    """is_pure_hex_segment 工具函数测试。"""

    def test_pure_hex_4_chars(self):
        """4 位纯 hex 返回 True。"""
        assert _is_pure_hex_segment("550e") is True

    def test_pure_hex_8_chars(self):
        """8 位纯 hex 返回 True。"""
        assert _is_pure_hex_segment("550e8400") is True

    def test_not_pure_hex(self):
        """含非 hex 字符返回 False。"""
        assert _is_pure_hex_segment("55oe") is False

    def test_length_not_multiple_of_4(self):
        """长度不是 4 的倍数返回 False。"""
        assert _is_pure_hex_segment("550") is False

    def test_empty_string(self):
        """空字符串返回 False。"""
        assert _is_pure_hex_segment("") is False

    def test_lowercase_hex(self):
        """小写 hex 返回 True。"""
        assert _is_pure_hex_segment("abcd") is True

    def test_uppercase_hex(self):
        """大写 hex 返回 True。"""
        assert _is_pure_hex_segment("ABCD") is True


class TestBuildSidParts:
    """_build_sid_parts 工具函数测试。"""

    def test_valid_32_hex_returns_sid_parts(self):
        """32 位有效 hex 应返回 SidParts。"""
        result = _build_sid_parts("asse", "post", TEST_UUID.hex)
        assert result is not None
        assert isinstance(result, SidParts)
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == TEST_UUID

    def test_invalid_hex_length_returns_none(self):
        """不是 32 位的 hex 应返回 None。"""
        assert _build_sid_parts("asse", "post", "550e") is None
        assert _build_sid_parts("asse", "post", "") is None

    def test_invalid_hex_string_returns_none(self):
        """无效的 hex 字符串应返回 None。"""
        invalid_hex = "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"  # 32 位但部分不是 hex
        assert _build_sid_parts("asse", "post", invalid_hex) is None


class TestSidPartsDataclass:
    """SidParts 数据类行为测试。"""

    def test_sid_parts_fields(self):
        """SidParts 应包含预期字段。"""
        parts = SidParts(
            prefix="asse",
            category="post",
            raw_hex=TEST_UUID.hex,
            uuid=TEST_UUID,
        )
        assert parts.prefix == "asse"
        assert parts.category == "post"
        assert parts.raw_hex == TEST_UUID.hex
        assert parts.uuid == TEST_UUID

    def test_sid_parts_category_none(self):
        """category 可为 None。"""
        parts = SidParts(
            prefix="user",
            category=None,
            raw_hex=TEST_UUID.hex,
            uuid=TEST_UUID,
        )
        assert parts.category is None