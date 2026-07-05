"""SID（Searchable ID）工具库单元测试。"""

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

# ── 测试用固定 UUID ──
_TEST_UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
_TEST_FORMATTED = "550e-8400-e29b-41d4-a716-4466-5544-0000"


class TestFormatUuid:
    """测试 format_uuid 函数。"""

    def test_format_standard_uuid(self):
        """标准 UUID 被格式化为每 4 位一组、横杠分隔的字符串。"""
        result = format_uuid(_TEST_UUID)
        assert result == _TEST_FORMATTED

    def test_format_another_uuid(self):
        """不同的 UUID 同样正确格式化。"""
        uid = uuid.UUID("12345678-90ab-cdef-1234-567890abcdef")
        result = format_uuid(uid)
        assert result == "1234-5678-90ab-cdef-1234-5678-90ab-cdef"

    def test_format_all_zero_uuid(self):
        """全零 UUID 也正常格式化。"""
        uid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = format_uuid(uid)
        assert result == "0000-0000-0000-0000-0000-0000-0000-0000"

    def test_format_uuid_length(self):
        """格式化后的字符串总长度为 39（32 位 hex + 7 个横杠）。"""
        result = format_uuid(_TEST_UUID)
        assert len(result) == 39

    def test_format_uuid_group_count(self):
        """格式化结果包含 8 组，每组 4 位 hex。"""
        result = format_uuid(_TEST_UUID)
        groups = result.split("-")
        assert len(groups) == 8
        assert all(len(g) == 4 for g in groups)


class TestMakeSid:
    """测试 make_sid 函数。"""

    def test_make_sid_with_category(self):
        """带二级分类生成 SID。"""
        sid = make_sid("asse", _TEST_UUID, "post")
        assert sid == f"asse-post-{_TEST_FORMATTED}"

    def test_make_sid_without_category(self):
        """不带二级分类生成 SID。"""
        sid = make_sid("user", _TEST_UUID)
        assert sid == f"user-{_TEST_FORMATTED}"

    def test_make_sid_with_different_prefixes(self):
        """所有已注册的前缀都能正常生成 SID。"""
        prefixes = ["user", "asse", "task", "log", "modr"]
        for prefix in prefixes:
            sid = make_sid(prefix, _TEST_UUID)
            assert sid.startswith(prefix + "-")
            assert _TEST_FORMATTED in sid

    def test_make_sid_unknown_prefix_raises_value_error(self):
        """未注册的前缀抛出 ValueError。"""
        with pytest.raises(ValueError, match="未知的前缀 'unknown'"):
            make_sid("unknown", _TEST_UUID)

    def test_make_sid_category_with_special_chars(self):
        """分类名包含字母数字和下划线时仍正常生成。"""
        sid = make_sid("asse", _TEST_UUID, "my_category")
        assert sid == f"asse-my_category-{_TEST_FORMATTED}"

    def test_make_sid_roundtrip_with_category(self):
        """带分类的 SID 生成后可以被 parse_sid 正确解析回来。"""
        sid = make_sid("asse", _TEST_UUID, "post")
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "post"
        assert parsed.uuid == _TEST_UUID

    def test_make_sid_roundtrip_without_category(self):
        """无分类的 SID 生成后可以被 parse_sid 正确解析回来。"""
        sid = make_sid("user", _TEST_UUID)
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "user"
        assert parsed.category is None
        assert parsed.uuid == _TEST_UUID

    def test_make_sid_category_empty_string(self):
        """传入空字符串作为 category 时，视为不带 category。"""
        sid = make_sid("user", _TEST_UUID, "")
        assert sid == f"user-{_TEST_FORMATTED}"
        # 空字符串是 falsy，所以走无 category 路径


class TestParseSid:
    """测试 parse_sid 函数。"""

    def test_parse_full_sid_with_category(self):
        """解析完整 SID（含二级分类）。"""
        sid = f"asse-post-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "post"
        assert parsed.raw_hex == "550e8400e29b41d4a716446655440000"
        assert parsed.uuid == _TEST_UUID

    def test_parse_sid_without_category(self):
        """解析无二级分类的 SID。"""
        sid = f"user-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "user"
        assert parsed.category is None
        assert parsed.uuid == _TEST_UUID

    def test_parse_sid_with_id_prefix(self):
        """解析带 'id:' 前缀的 SID。"""
        sid = f"id:asse-post-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "post"
        assert parsed.uuid == _TEST_UUID

    def test_parse_sid_with_sid_prefix(self):
        """解析带 'sid:' 前缀的 SID。"""
        sid = f"sid:asse-post-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "post"
        assert parsed.uuid == _TEST_UUID

    def test_parse_sid_no_delimiter_hex(self):
        """解析无分隔符 hex 的 SID。"""
        sid = "asse-post-550e8400e29b41d4a716446655440000"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "post"
        assert parsed.uuid == _TEST_UUID

    def test_parse_sid_with_id_prefix_uppercase(self):
        """解析带大写 'ID:' 前缀的 SID。"""
        sid = f"ID:asse-post-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"

    def test_parse_sid_with_sid_prefix_uppercase(self):
        """解析带大写 'SID:' 前缀的 SID。"""
        sid = f"SID:asse-post-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"

    def test_parse_sid_with_id_prefix_with_spaces(self):
        """解析带 'id: ' 前缀（含空格）的 SID。"""
        sid = f"id: asse-post-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"

    def test_parse_sid_standard_uuid_no_prefix(self):
        """解析标准 UUID 字符串（无前缀）返回 None。"""
        # 无前缀时 _parse_as_raw_uuid 返回 None
        sid = str(_TEST_UUID)
        parsed = parse_sid(sid)
        assert parsed is None

    def test_parse_sid_invalid_returns_none(self):
        """无效的 SID 字符串返回 None。"""
        assert parse_sid("not-a-valid-sid") is None

    def test_parse_sid_empty_string_returns_none(self):
        """空字符串返回 None。"""
        assert parse_sid("") is None

    def test_parse_sid_whitespace_only_returns_none(self):
        """仅含空白字符的字符串返回 None。"""
        assert parse_sid("   ") is None

    def test_parse_sid_with_padding_spaces(self):
        """带前后空格的 SID 能正确解析。"""
        sid = f"  asse-post-{_TEST_FORMATTED}  "
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"

    def test_parse_sid_mixed_case_prefix(self):
        """前缀大小写混用时仍能匹配。"""
        sid = f"ASSE-post-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"

    def test_parse_sid_invalid_hex_returns_none(self):
        """SID 中包含无效 hex 字符时返回 None。"""
        sid = "asse-post-55zz-8400-e29b-zzzz-a716-4466-5544-0000"
        parsed = parse_sid(sid)
        assert parsed is None

    def test_parse_sid_short_hex_returns_none(self):
        """SID 中 hex 段不足 32 位时返回 None。"""
        sid = "asse-post-550e-8400-e29b"
        parsed = parse_sid(sid)
        assert parsed is None

    def test_parse_sid_long_hex_returns_none(self):
        """SID 中 hex 段超过 32 位时返回 None。"""
        sid = "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000-1234"
        parsed = parse_sid(sid)
        assert parsed is None

    def test_parse_sid_unknown_prefix(self):
        """未知前缀的 SID 返回 None（因为没有匹配的前缀）。"""
        sid = f"unknown-post-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        assert parsed is None

    def test_parse_sid_no_prefix_but_pure_uuid(self):
        """无前缀但能匹配 UUID 的字符串——当前 _parse_as_raw_uuid 返回 None。"""
        # _parse_as_raw_uuid 目前直接返回 None
        sid = "550e8400e29b41d4a716446655440000"
        parsed = parse_sid(sid)
        assert parsed is None

    def test_parse_sid_category_with_hyphen(self):
        """分类名本身包含横杠的情况。"""
        # "xyz" 不含 hex 字符，被当作 category；"xyz" 长度不是 4 的倍数，不是纯 hex
        # 剩余部分 "label-{_TEST_FORMATTED}" 中 "label" 含非 hex 字符，
        # 但 "labe" 是 4 的倍数... 实际上 "label" 中有 'a', 'b', 'e' 是 hex 字符
        # 使用不含 hex 字符的分类名来验证
        sid = f"asse-xyz-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "xyz"
        assert parsed.uuid == _TEST_UUID

    def test_parse_sid_category_is_hex_like(self):
        """分类名看起来像 hex（纯 hex 且长度 4 的倍数）时，被视为 hex 而非 category。"""
        # "abcd" 是纯 hex 且长度 4 → 不被当作 category，被计入 hex 段
        # 但这样 hex 总长度会超过 32 位，导致解析失败返回 None
        sid = f"asse-abcd-{_TEST_FORMATTED}"
        parsed = parse_sid(sid)
        # 因为 "abcd" 被当作 hex 加入后总长度变为 36，超出 32 位限制
        assert parsed is None


class TestInternalHelpers:
    """测试内部辅助函数。"""

    def test_clean_hex_removes_non_hex(self):
        """_clean_hex 只保留 0-9a-fA-F 字符。"""
        assert _clean_hex("550e-8400-e29b") == "550e8400e29b"

    def test_clean_hex_with_garbage(self):
        """_clean_hex 移除所有非 hex 字符（包括横杠、空格、字母 g-z）。"""
        text = "55-0e 84x00!e29bGHIJ"
        assert _clean_hex(text) == "550e8400e29b"

    def test_clean_hex_empty_string(self):
        """_clean_hex 处理空字符串。"""
        assert _clean_hex("") == ""

    def test_clean_hex_all_removed(self):
        """_clean_hex 处理全为非 hex 字符的字符串。"""
        assert _clean_hex("xyz-!@#") == ""

    def test_is_pure_hex_segment_pure_hex(self):
        """纯 hex 且长度为 4 的倍数时返回 True。"""
        assert _is_pure_hex_segment("550e") is True
        assert _is_pure_hex_segment("abcd1234") is True

    def test_is_pure_hex_segment_not_pure_hex(self):
        """包含非 hex 字符时返回 False。"""
        assert _is_pure_hex_segment("55oe") is False
        assert _is_pure_hex_segment("abcde!") is False

    def test_is_pure_hex_segment_wrong_length(self):
        """长度为 4 的倍数时返回 False。"""
        assert _is_pure_hex_segment("550") is False
        assert _is_pure_hex_segment("550e8") is False

    def test_is_pure_hex_segment_empty(self):
        """空字符串返回 False。"""
        assert _is_pure_hex_segment("") is False

    def test_parse_as_raw_uuid_returns_none(self):
        """_parse_as_raw_uuid 始终返回 None。"""
        assert _parse_as_raw_uuid("anything") is None
        assert _parse_as_raw_uuid(str(_TEST_UUID)) is None

    def test_build_sid_parts_success(self):
        """_build_sid_parts 正常构建 SidParts。"""
        result = _build_sid_parts("asse", "post", "550e8400e29b41d4a716446655440000")
        assert result is not None
        assert isinstance(result, SidParts)
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.raw_hex == "550e8400e29b41d4a716446655440000"
        assert result.uuid == _TEST_UUID

    def test_build_sid_parts_wrong_length(self):
        """raw_hex 长度不为 32 时返回 None。"""
        assert _build_sid_parts("asse", None, "550e") is None
        assert _build_sid_parts("asse", None, "123456789012345678901234567890123") is None  # 33 位

    def test_build_sid_parts_invalid_uuid(self):
        """raw_hex 不能转换为 UUID 时返回 None。"""
        result = _build_sid_parts("asse", None, "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")
        assert result is None

    def test_build_sid_parts_empty_prefix(self):
        """prefix 为 None 时返回空字符串。"""
        result = _build_sid_parts(None, None, "550e8400e29b41d4a716446655440000")
        assert result is not None
        assert result.prefix == ""


class TestSidPartsDataclass:
    """测试 SidParts 数据类。"""

    def test_sid_parts_construction(self):
        """SidParts 能正确构造。"""
        parts = SidParts(
            prefix="asse",
            category="post",
            raw_hex="550e8400e29b41d4a716446655440000",
            uuid=_TEST_UUID,
        )
        assert parts.prefix == "asse"
        assert parts.category == "post"
        assert parts.raw_hex == "550e8400e29b41d4a716446655440000"
        assert parts.uuid == _TEST_UUID

    def test_sid_parts_category_none(self):
        """category 可以为 None。"""
        parts = SidParts(
            prefix="user",
            category=None,
            raw_hex="550e8400e29b41d4a716446655440000",
            uuid=_TEST_UUID,
        )
        assert parts.category is None

    def test_sid_parts_equality(self):
        """相同内容的 SidParts 实例相等。"""
        p1 = SidParts("asse", "post", "550e8400e29b41d4a716446655440000", _TEST_UUID)
        p2 = SidParts("asse", "post", "550e8400e29b41d4a716446655440000", _TEST_UUID)
        assert p1 == p2

    def test_sid_parts_repr(self):
        """SidParts 的 repr 包含关键字段。"""
        parts = SidParts("asse", "post", "550e8400e29b41d4a716446655440000", _TEST_UUID)
        r = repr(parts)
        assert "SidParts" in r
        assert "asse" in r
        assert "post" in r


class TestEdgeCases:
    """边界情况测试。"""

    def test_make_sid_with_prefix_case_sensitivity(self):
        """make_sid 对前缀大小写敏感——必须完全匹配 SID_PREFIXES 中的键。"""
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("ASSE", _TEST_UUID)

    def test_parse_sid_extremely_long_string(self):
        """超长字符串返回 None 而不是崩溃。"""
        long_sid = "user-" + "a" * 10000
        parsed = parse_sid(long_sid)
        assert parsed is None

    def test_parse_sid_only_prefix_and_dash(self):
        """只有前缀和横杠的字符串返回 None。"""
        parsed = parse_sid("user-")
        assert parsed is None

    def test_parse_sid_just_prefix(self):
        """只有前缀（无横杠）的字符串返回 None。"""
        parsed = parse_sid("user")
        assert parsed is None

    def test_parse_sid_with_newline(self):
        """SID 中包含换行符时仍能解析。"""
        sid = f"asse-post-{_TEST_FORMATTED}\n"
        parsed = parse_sid(sid)
        # strip 会移除换行，后续 hex 部分不受影响
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "post"

    def test_parse_sid_hex_with_extra_dashes(self):
        """hex 段含额外横杠时仍能正确清理。"""
        sid = "asse-post-550e-84-00-e29b-41d4-a716-4466-5544-0000"
        parsed = parse_sid(sid)
        assert parsed is not None
        assert parsed.uuid == _TEST_UUID

    def test_parse_sid_all_possible_prefixes(self):
        """所有已注册前缀的 SID 都能正确解析。"""
        prefixes = ["user", "asse", "task", "log", "modr"]
        for prefix in prefixes:
            sid = f"{prefix}-{_TEST_FORMATTED}"
            parsed = parse_sid(sid)
            assert parsed is not None, f"前缀 '{prefix}' 解析失败"
            assert parsed.prefix == prefix
            assert parsed.category is None
            assert parsed.uuid == _TEST_UUID

    def test_format_uuid_preserves_value(self):
        """format_uuid 不会改变 UUID 的值。"""
        formatted = format_uuid(_TEST_UUID)
        # 移除横杠后应该等于原始 hex
        assert formatted.replace("-", "") == _TEST_UUID.hex

    def test_make_sid_empty_category_vs_none(self):
        """空字符串 category 和 None category 结果相同。"""
        sid_none = make_sid("user", _TEST_UUID, None)
        sid_empty = make_sid("user", _TEST_UUID, "")
        assert sid_none == sid_empty == f"user-{_TEST_FORMATTED}"