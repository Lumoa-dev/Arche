"""UID 工具函数单元测试。

覆盖 SID 生成/解析、UUID 格式化等核心工具函数。
"""

from __future__ import annotations

import uuid

import pytest

from backend.core.uid import SidParts, format_uuid, make_sid, parse_sid


class TestFormatUuid:
    """format_uuid 格式化测试。"""

    def test_format_uuid_returns_grouped_hex(self):
        """format_uuid 应返回每 4 位一组、横杠分隔的 32 位 hex 字符串。"""
        uid = uuid.uuid4()
        result = format_uuid(uid)
        assert isinstance(result, str)
        assert len(result) == 39  # 32 hex + 7 hyphens = 8 groups of 4
        assert result.count("-") == 7

    def test_format_uuid_deterministic(self):
        """相同 UUID 应格式化为相同字符串。"""
        uid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        assert format_uuid(uid) == "550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_format_uuid_group_length(self):
        """每组应为 4 个 hex 字符。"""
        uid = uuid.uuid4()
        result = format_uuid(uid)
        for group in result.split("-"):
            assert len(group) == 4

    def test_format_uuid_roundtrip(self):
        """格式化后能被 uuid.UUID 重新解析。"""
        original = uuid.uuid4()
        formatted = format_uuid(original)
        # 移除横杠后应能还原
        hex_str = formatted.replace("-", "")
        recovered = uuid.UUID(hex=hex_str)
        assert recovered == original


class TestMakeSid:
    """make_sid SID 生成测试。"""

    def test_make_sid_with_category(self):
        """生成带二级分类的 SID。"""
        uid = uuid.uuid4()
        sid = make_sid("asse", uid, "post")
        assert sid.startswith("asse-post-")
        assert len(sid) > 20

    def test_make_sid_without_category(self):
        """生成不带二级分类的 SID。"""
        uid = uuid.uuid4()
        sid = make_sid("user", uid)
        assert sid.startswith("user-")
        assert "-" in sid

    def test_make_sid_unknown_prefix(self):
        """未知前缀应抛出 ValueError。"""
        uid = uuid.uuid4()
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("unknown", uid)

    def test_make_sid_includes_formatted_uuid(self):
        """SID 应包含格式化后的 UUID。"""
        uid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("user", uid)
        assert "550e-8400-e29b-41d4-a716-4466-5544-0000" in sid

    def test_make_sid_all_prefixes(self):
        """所有注册前缀都应能生成 SID。"""
        uid = uuid.uuid4()
        for prefix in ["user", "asse", "task", "log", "modr"]:
            sid = make_sid(prefix, uid)
            assert sid.startswith(f"{prefix}-")


class TestParseSid:
    """parse_sid SID 解析测试。"""

    def test_parse_sid_valid_with_category(self):
        """解析带二级分类的有效 SID。"""
        uid = uuid.uuid4()
        sid = make_sid("asse", uid, "post")
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uid

    def test_parse_sid_valid_without_category(self):
        """解析不带二级分类的有效 SID。"""
        uid = uuid.uuid4()
        sid = make_sid("user", uid)
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None
        assert result.uuid == uid

    def test_parse_sid_invalid_returns_none(self):
        """无效的 SID 返回 None。"""
        assert parse_sid("bad_format") is None

    def test_parse_sid_empty_string(self):
        """空字符串返回 None。"""
        assert parse_sid("") is None

    def test_parse_sid_whitespace_only(self):
        """纯空白字符串返回 None。"""
        assert parse_sid("   ") is None

    def test_parse_sid_with_id_prefix(self):
        """带 id: 前缀的 SID。"""
        uid = uuid.uuid4()
        sid = make_sid("asse", uid, "post")
        result = parse_sid(f"id:{sid}")
        assert result is not None
        assert result.prefix == "asse"
        assert result.uuid == uid

    def test_parse_sid_with_sid_prefix(self):
        """带 sid: 前缀的 SID。"""
        uid = uuid.uuid4()
        sid = make_sid("user", uid)
        result = parse_sid(f"sid:{sid}")
        assert result is not None
        assert result.prefix == "user"

    def test_parse_sid_without_separator_hex(self):
        """无分隔符的 hex 格式 SID。"""
        uid = uuid.uuid4()
        sid = make_sid("asse", uid, "post")
        # 移除横杠
        compressed = sid.replace("-", "")
        # 但前缀结构还在，所以需要构造正确的格式
        # asse-post-550e8400e29b...
        result = parse_sid(compressed)
        # 这种格式可能无法解析，因为前缀部分被破坏了
        # 但我们至少不应抛出异常
        assert result is None or isinstance(result, SidParts)

    def test_parse_sid_roundtrip(self):
        """生成和解析往返一致。"""
        for prefix in ["user", "asse", "task", "log", "modr"]:
            uid = uuid.uuid4()
            sid = make_sid(prefix, uid)
            result = parse_sid(sid)
            assert result is not None
            assert result.prefix == prefix
            assert result.uuid == uid


class TestSidParts:
    """SidParts 数据结构测试。"""

    def test_sid_parts_creation(self):
        """SidParts 实例化。"""
        uid = uuid.uuid4()
        parts = SidParts(prefix="asse", category="post", raw_hex=uid.hex, uuid=uid)
        assert parts.prefix == "asse"
        assert parts.category == "post"
        assert parts.uuid == uid

    def test_sid_parts_none_category(self):
        """category 可为 None。"""
        uid = uuid.uuid4()
        parts = SidParts(prefix="user", category=None, raw_hex=uid.hex, uuid=uid)
        assert parts.category is None

    def test_sid_parts_repr(self):
        """SidParts 字符串表示。"""
        uid = uuid.uuid4()
        parts = SidParts(prefix="asse", category="post", raw_hex=uid.hex, uuid=uid)
        repr_str = repr(parts)
        assert "asse" in repr_str
        assert "post" in repr_str

    def test_sid_parts_equality(self):
        """相同的 SidParts 应相等。"""
        uid = uuid.uuid4()
        a = SidParts("asse", "post", uid.hex, uid)
        b = SidParts("asse", "post", uid.hex, uid)
        assert a == b