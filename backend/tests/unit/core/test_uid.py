"""SID 工具函数行为测试。

SID 是 Arche 全平台统一的 ID 格式，用于用户、资产、任务等实体。
纯函数测试，无数据库依赖。
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


# =============================================================================
# format_uuid 测试
# =============================================================================


class TestFormatUuid:
    """UUID 格式化行为测试。"""

    def test_format_uuid_standard(self):
        """标准 UUID 应格式化为每 4 位一组、横杠分隔的 32 位 hex。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        formatted = format_uuid(raw)
        assert formatted == "550e-8400-e29b-41d4-a716-4466-5544-0000"
        assert len(formatted.replace("-", "")) == 32

    def test_format_uuid_all_zeros(self):
        """全零 UUID 应正确格式化。"""
        raw = uuid.UUID("00000000-0000-0000-0000-000000000000")
        formatted = format_uuid(raw)
        assert formatted == "0000-0000-0000-0000-0000-0000-0000-0000"

    def test_format_uuid_all_ones(self):
        """全 1 UUID 应正确格式化。"""
        raw = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        formatted = format_uuid(raw)
        assert formatted == "ffff-ffff-ffff-ffff-ffff-ffff-ffff-ffff"


# =============================================================================
# make_sid 测试
# =============================================================================


class TestMakeSid:
    """SID 生成行为测试。"""

    def test_make_sid_with_category(self):
        """带二级分类的 SID 生成。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("asse", raw, category="post")
        assert sid == "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_without_category(self):
        """不带二级分类的 SID 生成。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        sid = make_sid("user", raw)
        assert sid == "user-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_make_sid_unknown_prefix_raises_error(self):
        """未知前缀应抛出 ValueError。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        with pytest.raises(ValueError) as excinfo:
            make_sid("invalid", raw)
        assert "未知的前缀" in str(excinfo.value)

    def test_make_sid_all_prefixes(self):
        """所有已注册前缀都应能生成 SID。"""
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        for prefix in ["user", "asse", "task", "log", "modr"]:
            sid = make_sid(prefix, raw)
            assert sid.startswith(prefix)


# =============================================================================
# parse_sid 测试
# =============================================================================


class TestParseSid:
    """SID 解析行为测试。"""

    def test_parse_sid_full(self):
        """完整 SID 解析。"""
        result = parse_sid(
            "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"
        )
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_no_category(self):
        """无二级分类的 SID 解析。"""
        result = parse_sid("user-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None
        assert result.uuid == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_parse_sid_no_separator_hex(self):
        """无分隔符 hex 格式的 SID 解析。"""
        result = parse_sid("asse-post-550e8400e29b41d4a716446655440000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_id_prefix(self):
        """带 id: 前缀的 SID 解析。"""
        result = parse_sid("id:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_with_sid_prefix(self):
        """带 sid: 前缀的 SID 解析。"""
        result = parse_sid("sid:asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_standard_uuid(self):
        """标准 UUID 解析应返回 None（无前缀时）。"""
        result = parse_sid("550e8400-e29b-41d4-a716-446655440000")
        assert result is None

    def test_parse_sid_empty_string(self):
        """空字符串解析应返回 None。"""
        result = parse_sid("")
        assert result is None

    def test_parse_sid_whitespace_only(self):
        """纯空白字符串解析应返回 None。"""
        result = parse_sid("   ")
        assert result is None

    def test_parse_sid_invalid_hex(self):
        """无效 hex 的 SID 解析应返回 None。"""
        result = parse_sid("user-zzzz-not-hex-here")
        assert result is None

    def test_parse_sid_short_hex(self):
        """hex 长度不足 32 位的 SID 解析应返回 None。"""
        result = parse_sid("user-550e-8400")
        assert result is None

    def test_parse_sid_long_hex(self):
        """hex 超过 32 位的 SID 解析应返回 None。"""
        result = parse_sid("user-550e-8400-e29b-41d4-a716-4466-5544-0000-extra")
        assert result is None

    def test_parse_sid_roundtrip(self):
        """make_sid → parse_sid 应还原原始信息。"""
        raw = uuid.uuid4()
        sid = make_sid("asse", raw, category="file")
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "file"
        assert result.uuid == raw

    def test_parse_sid_roundtrip_no_category(self):
        """无 category 的 SID 应能完整还原。"""
        raw = uuid.uuid4()
        sid = make_sid("user", raw)
        result = parse_sid(sid)
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None
        assert result.uuid == raw

    def test_parse_sid_with_id_prefix_roundtrip(self):
        """带 id: 前缀的 SID 应能完整还原。"""
        raw = uuid.uuid4()
        sid = make_sid("task", raw, category="train")
        result = parse_sid(f"id:{sid}")
        assert result is not None
        assert result.prefix == "task"
        assert result.category == "train"
        assert result.uuid == raw

    def test_parse_sid_case_insensitive_prefix(self):
        """前缀大小写不敏感。"""
        result = parse_sid("ASSE-post-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "asse"
        assert result.category == "post"

    def test_parse_sid_sid_prefix(self):
        """sid: 前缀应被正确剥离。"""
        result = parse_sid("sid:user-550e-8400-e29b-41d4-a716-4466-5544-0000")
        assert result is not None
        assert result.prefix == "user"
        assert result.category is None