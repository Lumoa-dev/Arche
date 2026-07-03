"""SID 工具库单元测试 —— 统一 ID 生成、格式化、解析。

测试原则：
- 每个函数级行为独立测试
- 涵盖正常路径、边界条件和异常输入
"""

from __future__ import annotations

import uuid

import pytest

from backend.core.uid import (
    SidParts,
    _build_sid_parts,
    _clean_hex,
    _is_pure_hex_segment,
    _parse_as_raw_uuid,
    format_uuid,
    make_sid,
    parse_sid,
)

# 固定的测试 UUID
TEST_UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
TEST_UUID_HEX = "550e8400e29b41d4a716446655440000"
TEST_UUID_FORMATTED = "550e-8400-e29b-41d4-a716-4466-5544-0000"


class TestFormatUuid:
    """format_uuid 格式化测试。"""

    def test_format_standard_uuid(self):
        """标准 UUID 格式化为每 4 位一组。"""
        result = format_uuid(TEST_UUID)
        assert result == TEST_UUID_FORMATTED

    def test_format_all_zero_uuid(self):
        """全零 UUID 格式化为 8 组 0000。"""
        zero = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = format_uuid(zero)
        assert result == "0000-0000-0000-0000-0000-0000-0000-0000"


class TestMakeSid:
    """make_sid SID 生成测试。"""

    def test_make_sid_with_category(self):
        """生成带二级分类的 SID。"""
        result = make_sid("asse", TEST_UUID, "post")
        assert result == f"asse-post-{TEST_UUID_FORMATTED}"

    def test_make_sid_without_category(self):
        """生成不带二级分类的 SID。"""
        result = make_sid("user", TEST_UUID)
        assert result == f"user-{TEST_UUID_FORMATTED}"

    def test_make_sid_all_prefixes(self):
        """所有注册前缀都能生成 SID。"""
        for prefix in ("user", "asse", "task", "log", "modr"):
            sid = make_sid(prefix, TEST_UUID)
            assert sid.startswith(prefix + "-")

    def test_make_sid_unknown_prefix(self):
        """未注册的前缀应抛出 ValueError。"""
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("unknown", TEST_UUID)

    def test_make_sid_empty_category(self):
        """category 为 None 时等价于无分类。"""
        with_cat = make_sid("asse", TEST_UUID, "post")
        without_cat = make_sid("asse", TEST_UUID)
        assert with_cat != without_cat
        assert without_cat.startswith("asse-")


class TestParseSid:
    """parse_sid SID 解析测试。"""

    def test_parse_full_sid(self):
        """解析完整 SID（含二级分类）。"""
        sid = f"asse-post-{TEST_UUID_FORMATTED}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == TEST_UUID

    def test_parse_sid_without_category(self):
        """解析无二级分类的 SID。"""
        sid = f"user-{TEST_UUID_FORMATTED}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None
        assert result.uuid == TEST_UUID

    def test_parse_sid_with_id_prefix(self):
        """解析带 id: 前缀的 SID。"""
        sid = f"id:asse-post-{TEST_UUID_FORMATTED}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_sid_prefix(self):
        """解析带 sid: 前缀的 SID。"""
        sid = f"sid:user-{TEST_UUID_FORMATTED}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "user"

    def test_parse_sid_without_hyphens(self):
        """解析无分隔符的 hex SID。"""
        sid = f"asse-post-{TEST_UUID_HEX}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == TEST_UUID

    def test_parse_standard_uuid(self):
        """解析纯标准 UUID 字符串。"""
        result = parse_sid(str(TEST_UUID))
        # 纯 UUID 无前缀，应返回 None
        assert result is None

    def test_parse_empty_string(self):
        """空字符串返回 None。"""
        assert parse_sid("") is None

    def test_parse_whitespace_only(self):
        """仅空白字符串返回 None。"""
        assert parse_sid("   ") is None

    def test_parse_invalid_hex(self):
        """无效 hex 字符串返回 None。"""
        sid = "user-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz"
        result = parse_sid(sid)
        assert result is None

    def test_parse_short_hex(self):
        """过短的 hex 返回 None。"""
        sid = "user-550e-8400"
        result = parse_sid(sid)
        assert result is None

    def test_parse_case_insensitive_prefix(self):
        """前缀大小写不敏感。"""
        sid = f"ASSE-post-{TEST_UUID_FORMATTED}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_with_trailing_spaces(self):
        """带前后空格的 SID 可解析。"""
        sid = f"  user-{TEST_UUID_FORMATTED}  "
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "user"


class TestCleanHex:
    def test_removes_non_hex(self):
        """只保留 hex 字符。"""
        assert _clean_hex("550e-8400-zzzz") == "550e8400"

    def test_empty_string(self):
        assert _clean_hex("") == ""

    def test_all_hex(self):
        assert _clean_hex("abc123") == "abc123"


class TestIsPureHexSegment:
    def test_pure_hex_multiple_of_4(self):
        assert _is_pure_hex_segment("abcd") is True

    def test_not_multiple_of_4(self):
        assert _is_pure_hex_segment("abc") is False

    def test_contains_non_hex(self):
        assert _is_pure_hex_segment("abcg") is False

    def test_empty_string(self):
        assert _is_pure_hex_segment("") is False


class TestBuildSidParts:
    def test_valid_hex(self):
        result = _build_sid_parts("asse", "post", TEST_UUID_HEX)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == TEST_UUID

    def test_short_hex_returns_none(self):
        assert _build_sid_parts("user", None, "abcd") is None

    def test_invalid_hex_returns_none(self):
        assert _build_sid_parts("user", None, "zzzz" * 8) is None


class TestParseAsRawUuid:
    def test_always_returns_none(self):
        """_parse_as_raw_uuid 始终返回 None（由调用方决策）。"""
        assert _parse_as_raw_uuid("anything") is None