"""SID 工具库测试 —— format_uuid / make_sid / parse_sid。"""

import uuid

import pytest

from backend.core.uid import (
    SidParts,
    format_uuid,
    make_sid,
    parse_sid,
    _clean_hex,
    _is_pure_hex_segment,
    _build_sid_parts,
)


class TestFormatUuid:
    """测试 format_uuid 函数。"""

    def test_format_uuid_standard(self):
        """标准 UUID 格式化为每 4 位一组横杠分隔。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = format_uuid(raw)
        assert result == "550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_format_uuid_all_zero(self):
        """全零 UUID 格式化正确。"""
        raw = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = format_uuid(raw)
        assert result == "0000-0000-0000-0000-0000-0000-0000-0000"

    def test_format_uuid_length(self):
        """格式化后的字符串长度正确（32 hex + 7 横杠 = 39）。"""
        raw = uuid.uuid4()
        result = format_uuid(raw)
        assert len(result) == 39
        assert result.count("-") == 7


class TestMakeSid:
    """测试 make_sid 函数。"""

    def test_make_sid_without_category(self):
        """无二级分类时生成正确格式。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("user", raw)
        assert sid == "user-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_with_category(self):
        """有二级分类时生成正确格式。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("asse", raw, "post")
        assert sid == "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_invalid_prefix(self):
        """未注册的前缀抛出 ValueError。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid", raw)

    def test_make_sid_all_prefixes(self):
        """所有注册前缀都能生成 SID。"""
        raw = uuid.uuid4()
        for prefix in ("user", "asse", "task", "log", "modr"):
            sid = make_sid(prefix, raw)
            assert sid.startswith(prefix)

    def test_make_sid_category_none(self):
        """category=None 等同于无 category。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid_no_cat = make_sid("user", raw)
        sid_none_cat = make_sid("user", raw, None)
        assert sid_no_cat == sid_none_cat

    def test_make_sid_empty_category(self):
        """空字符串作为 category 被视为 falsy，等同于无 category。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("asse", raw, "")
        # 空字符串是 falsy，所以不走 category 分支
        assert sid == "asse-550e-8400-e29b-41d4-a716-4466-5544-0000"


class TestCleanHex:
    """测试 _clean_hex 函数。"""

    def test_clean_hex_removes_dashes(self):
        """移除横杠分隔符。"""
        assert _clean_hex("550e-8400-e29b") == "550e8400e29b"

    def test_clean_hex_removes_non_hex(self):
        """移除非十六进制字符。"""
        assert _clean_hex("550e-8400-xyz-!@#") == "550e8400"

    def test_clean_hex_preserves_valid_hex(self):
        """保留有效的十六进制字符。"""
        assert _clean_hex("abcdef0123456789") == "abcdef0123456789"

    def test_clean_hex_case_insensitive(self):
        """大小写都保留。"""
        assert _clean_hex("ABCDEFabcdef") == "ABCDEFabcdef"

    def test_clean_hex_empty_string(self):
        """空字符串返回空字符串。"""
        assert _clean_hex("") == ""


class TestIsPureHexSegment:
    """测试 _is_pure_hex_segment 函数。"""

    def test_pure_hex_valid(self):
        """纯 hex 且长度为 4 的倍数返回 True。"""
        assert _is_pure_hex_segment("550e") is True
        assert _is_pure_hex_segment("550e8400") is True

    def test_pure_hex_invalid_length(self):
        """长度不是 4 的倍数返回 False。"""
        assert _is_pure_hex_segment("550") is False
        assert _is_pure_hex_segment("550e8") is False

    def test_pure_hex_non_hex(self):
        """包含非 hex 字符返回 False。"""
        assert _is_pure_hex_segment("55og") is False

    def test_pure_hex_empty(self):
        """空字符串返回 False。"""
        assert _is_pure_hex_segment("") is False


class TestBuildSidParts:
    """测试 _build_sid_parts 函数。"""

    def test_build_sid_parts_valid(self):
        """有效的 hex 字符串构建成功。"""
        result = _build_sid_parts(
            "asse", "post", "550e8400e29b41d4a716446655440000"
        )
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.raw_hex == "550e8400e29b41d4a716446655440000"
        assert isinstance(result.uuid, uuid.UUID)

    def test_build_sid_parts_invalid_hex_length(self):
        """hex 长度不是 32 返回 None。"""
        result = _build_sid_parts("user", None, "550e")
        assert result is None

    def test_build_sid_parts_invalid_hex_chars(self):
        """包含非法 hex 字符的 hex 返回 None。"""
        result = _build_sid_parts(
            "user", None, "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
        )
        assert result is None

    def test_build_sid_parts_none_prefix(self):
        """prefix 为 None 时返回空字符串。"""
        result = _build_sid_parts(
            None, None, "550e8400e29b41d4a716446655440000"
        )
        assert result is not None
        assert result.prefix == ""


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

    def test_parse_sid_no_dashes_in_hex(self):
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
        result = parse_sid("sid:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_standard_uuid(self):
        """解析标准 UUID 格式返回 None（无前缀）。"""
        result = parse_sid("550e8400-e29b-41d4-a716-446655440000")
        assert result is None

    def test_parse_sid_empty_string(self):
        """空字符串返回 None。"""
        assert parse_sid("") is None
        assert parse_sid("   ") is None

    def test_parse_sid_invalid_prefix(self):
        """未注册前缀返回 None。"""
        result = parse_sid("invalid-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is None

    def test_parse_sid_numeric_category(self):
        """数字作为 category 被正确识别（长度非 4 倍数时视为 category）。"""
        result = parse_sid("asse-123-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        # "123" 长度是 3，不是 4 的倍数 → 被当作 category
        assert result.category == "123"

    def test_parse_sid_with_spaces(self):
        """带前后空格的 SID 能正常解析。"""
        result = parse_sid("  asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000  ")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    @pytest.mark.parametrize(
        "sid",
        [
            "user-550e-8400-e29b-41d4-a716-4466-5544-0000",
            "log-550e-8400-e29b-41d4-a716-4466-5544-0000",
            "task-550e-8400-e29b-41d4-a716-4466-5544-0000",
            "modr-550e-8400-e29b-41d4-a716-4466-5544-0000",
        ],
    )
    def test_parse_all_prefixes(self, sid):
        """所有注册前缀的 SID 都能正确解析。"""
        result = parse_sid(sid)
        assert result is not None
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_invalid_hex(self):
        """hex 部分无效时返回 None。"""
        result = parse_sid("asse-post-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz")
        assert result is None

    def test_parse_sid_short_hex(self):
        """hex 部分太短时返回 None。"""
        result = parse_sid("asse-post-550e-8400")
        assert result is None

    def test_parse_sid_sid_parts_dataclass(self):
        """SidParts 数据类字段正确。"""
        result = parse_sid("asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert isinstance(result, SidParts)
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.raw_hex == "550e8400e29b41d4a716446655440000"
        assert isinstance(result.uuid, uuid.UUID)