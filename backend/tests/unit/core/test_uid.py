"""SID（Searchable ID）工具库测试。

测试策略：
- 纯函数，无外部依赖，使用固定 UUID 确保确定性
- 覆盖：生成、解析、各类格式兼容、异常输入、边界情况
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

# 固定 UUID 用于确定性测试
_UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
_UUID_HEX = "550e8400e29b41d4a716446655440000"
_FORMATTED = "550e-8400-e29b-41d4-a716-4466-5544-0000"


class TestFormatUuid:
    """format_uuid 测试。"""

    def test_format_uuid_standard(self):
        """标准 UUID 格式化为每 4 位一组。"""
        result = format_uuid(_UUID)
        assert result == _FORMATTED

    def test_format_uuid_zero_uuid(self):
        """全零 UUID。"""
        result = format_uuid(uuid.UUID("00000000-0000-0000-0000-000000000000"))
        assert result == "0000-0000-0000-0000-0000-0000-0000-0000"

    def test_format_uuid_preserves_hex_order(self):
        """格式化不改变 hex 顺序。"""
        result = format_uuid(_UUID)
        # 去掉横杠后应与原始 hex 一致
        assert result.replace("-", "") == _UUID_HEX


class TestMakeSid:
    """make_sid 测试。"""

    def test_make_sid_no_category(self):
        """无二级分类的 SID 生成。"""
        result = make_sid("user", _UUID)
        assert result == f"user-{_FORMATTED}"

    def test_make_sid_with_category(self):
        """带二级分类的 SID 生成。"""
        result = make_sid("asse", _UUID, "post")
        assert result == f"asse-post-{_FORMATTED}"

    def test_make_sid_unknown_prefix(self):
        """未知前缀应抛出 ValueError。"""
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid", _UUID)

    def test_make_sid_all_valid_prefixes(self):
        """所有注册前缀都能生成 SID。"""
        for prefix in ["user", "asse", "task", "log", "modr"]:
            result = make_sid(prefix, _UUID, category="test")
            assert result.startswith(prefix)


class TestParseSid:
    """parse_sid 测试。"""

    def test_parse_full_sid(self):
        """解析完整 SID（带二级分类）。"""
        sid = make_sid("asse", _UUID, "post")
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == _UUID
        assert result.raw_hex == _UUID_HEX

    def test_parse_sid_no_category(self):
        """解析无二级分类的 SID。"""
        sid = make_sid("user", _UUID)
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None
        assert result.uuid == _UUID

    def test_parse_sid_with_id_prefix(self):
        """解析带 id: 前缀的 SID。"""
        result = parse_sid(f"id:asse-post-{_FORMATTED}")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_sid_prefix(self):
        """解析带 sid: 前缀的 SID。"""
        result = parse_sid(f"sid:asse-post-{_FORMATTED}")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_no_separator_hex(self):
        """解析无分隔符的 hex 格式。"""
        sid = f"asse-post-{_UUID_HEX}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == _UUID

    def test_parse_sid_standard_uuid(self):
        """解析标准 UUID 格式（无前缀）。"""
        result = parse_sid(str(_UUID))
        # 无前缀时返回 None，由调用方处理
        assert result is None

    def test_parse_sid_empty_string(self):
        """空字符串返回 None。"""
        assert parse_sid("") is None

    def test_parse_sid_whitespace(self):
        """纯空白字符串返回 None。"""
        assert parse_sid("   ") is None

    def test_parse_sid_invalid_prefix(self):
        """无效前缀被视为无前缀，返回 None。"""
        result = parse_sid(f"badprefix-{_FORMATTED}")
        assert result is None

    def test_parse_sid_trailing_spaces(self):
        """带前后空格的 SID 能正常解析。"""
        sid = f"  asse-post-{_FORMATTED}  "
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_sid_case_insensitive_prefix(self):
        """前缀大小写不敏感。"""
        sid = f"ASSE-post-{_FORMATTED}"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"

    def test_parse_sid_invalid_hex(self):
        """无效 hex 返回 None。"""
        sid = "asse-post-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz"
        result = parse_sid(sid)
        assert result is None

    def test_parse_sid_truncated_hex(self):
        """截断的 hex 返回 None。"""
        sid = "asse-post-550e-8400"
        result = parse_sid(sid)
        assert result is None

    def test_parse_sid_build_sid_parts_none(self):
        """_build_sid_parts 在 hex 长度不对时返回 None。"""
        assert _build_sid_parts("test", None, "abc") is None
        assert _build_sid_parts("test", None, "") is None

    def test_parse_sid_build_sid_parts_invalid_uuid(self):
        """_build_sid_parts 在 UUID 无效时返回 None。"""
        assert _build_sid_parts("test", None, "x" * 32) is None


class TestInternalHelpers:
    """内部工具函数测试。"""

    def test_clean_hex_removes_non_hex(self):
        """_clean_hex 只保留 hex 字符。"""
        assert _clean_hex("550e-8400-xyz") == "550e8400"
        assert _clean_hex("") == ""
        assert _clean_hex("abc123") == "abc123"

    def test_is_pure_hex_segment(self):
        """_is_pure_hex_segment 判断正确。"""
        assert _is_pure_hex_segment("550e") is True
        assert _is_pure_hex_segment("abc1") is True
        assert _is_pure_hex_segment("") is False
        assert _is_pure_hex_segment("abc") is False  # 长度不是 4 的倍数
        assert _is_pure_hex_segment("abcde") is False  # 长度不是 4 的倍数
        assert _is_pure_hex_segment("xyz1") is False  # 含非 hex 字符

    def test_sid_parts_dataclass(self):
        """SidParts dataclass 正确。"""
        parts = SidParts(prefix="asse", category="post", raw_hex=_UUID_HEX, uuid=_UUID)
        assert parts.prefix == "asse"
        assert parts.category == "post"
        assert parts.raw_hex == _UUID_HEX
        assert parts.uuid == _UUID


class TestRoundtrip:
    """生成 → 解析 往返测试。"""

    def test_roundtrip_no_category(self):
        """无分类的 SID 生成后能解析回来。"""
        original = make_sid("user", _UUID)
        result = parse_sid(original)
        assert result is not None
        assert result.prefix == "user"
        assert result.uuid == _UUID

    def test_roundtrip_with_category(self):
        """带分类的 SID 生成后能解析回来。"""
        original = make_sid("asse", _UUID, "file")
        result = parse_sid(original)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "file"
        assert result.uuid == _UUID

    def test_roundtrip_all_prefixes(self):
        """所有前缀的 SID 都能正确生成和解析。"""
        for prefix in ["user", "asse", "task", "log", "modr"]:
            original = make_sid(prefix, _UUID, "test")
            result = parse_sid(original)
            assert result is not None, f"Failed to parse {prefix} SID"
            assert result.prefix == prefix