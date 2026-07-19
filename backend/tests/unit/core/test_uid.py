"""SID（Searchable ID）生成、格式化、解析测试。"""

from __future__ import annotations

import uuid

import pytest

from backend.core.uid import (
    SidParts,
    format_uuid,
    make_sid,
    parse_sid,
)


class TestFormatUUID:
    """测试 UUID 格式化。"""

    def test_format_uuid_standard(self):
        """标准 UUID 格式化为 4 位一组横杠分隔。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = format_uuid(raw)
        assert result == "550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_format_uuid_another(self):
        """另一个 UUID 的格式化结果。"""
        raw = uuid.UUID("12345678-1234-5678-1234-567812345678")
        result = format_uuid(raw)
        assert result == "1234-5678-1234-5678-1234-5678-1234-5678"


class TestMakeSID:
    """测试 SID 生成。"""

    def test_make_sid_with_category(self):
        """生成带二级分类的 SID。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("asse", raw, category="post")
        assert sid == "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_without_category(self):
        """生成不带二级分类的 SID。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("user", raw)
        assert sid == "user-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_invalid_prefix(self):
        """使用未注册的前缀应抛出 ValueError。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        with pytest.raises(ValueError, match="未知的前缀"):
            make_sid("invalid", raw)

    def test_make_sid_all_prefixes(self):
        """所有注册前缀都能正常生成 SID。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        for prefix in ["user", "asse", "task", "log", "modr"]:
            sid = make_sid(prefix, raw)
            assert sid.startswith(prefix)


class TestParseSID:
    """测试 SID 解析。"""

    def test_parse_full_sid(self):
        """解析完整 SID（带二级分类）。"""
        sid = "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_without_category(self):
        """解析不带二级分类的 SID。"""
        sid = "user-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None

    def test_parse_sid_with_id_prefix(self):
        """解析带 'id:' 前缀的 SID。"""
        sid = "id:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_sid_prefix(self):
        """解析带 'sid:' 前缀的 SID。"""
        sid = "sid:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_without_separator_hex(self):
        """解析无分隔符 hex 的 SID。"""
        sid = "asse-post-550e8400e29b41d4a716446655440000"
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_standard_uuid(self):
        """解析标准 UUID 字符串（无前缀）。"""
        sid = "550e8400-e29b-41d4-a716-446655440000"
        result = parse_sid(sid)
        assert result is None  # 无前缀时返回 None

    def test_parse_empty_string(self):
        """解析空字符串返回 None。"""
        assert parse_sid("") is None

    def test_parse_whitespace_string(self):
        """解析纯空白字符串返回 None。"""
        assert parse_sid("   ") is None

    def test_parse_invalid_hex(self):
        """解析无效 hex 的 SID 返回 None。"""
        sid = "asse-post-XXXX-8400-e29b-41d4-a716-4466-5544-0000"
        result = parse_sid(sid)
        assert result is None

    def test_parse_short_hex(self):
        """解析 hex 长度不足 32 的 SID 返回 None。"""
        sid = "user-550e-8400"
        result = parse_sid(sid)
        assert result is None

    def test_parse_roundtrip(self):
        """生成再解析应得到相同结果。"""
        raw = uuid.uuid4()
        original_sid = make_sid("asse", raw, category="file")
        parsed = parse_sid(original_sid)
        assert parsed is not None
        assert parsed.prefix == "asse"
        assert parsed.category == "file"
        assert parsed.uuid == raw

    def test_parse_sid_parts_dataclass(self):
        """SidParts 数据类属性正确。"""
        parts = SidParts(
            prefix="asse",
            category="post",
            raw_hex="550e8400e29b41d4a716446655440000",
            uuid=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        )
        assert parts.prefix == "asse"
        assert parts.category == "post"
        assert parts.raw_hex == "550e8400e29b41d4a716446655440000"
        assert parts.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")