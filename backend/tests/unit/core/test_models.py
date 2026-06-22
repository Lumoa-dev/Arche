"""核心模型测试 —— HasSID mixin、ConfigEntry 模型。"""

from __future__ import annotations

import uuid

import pytest

from backend.core.models import ConfigEntry, HasSID, _default_sid


class TestDefaultSid:
    """测试默认 SID 生成函数。"""

    def test_default_sid_returns_32_hex(self):
        """_default_sid() 返回 32 位 hex 字符串。"""
        sid = _default_sid()
        assert len(sid) == 32
        assert all(c in "0123456789abcdef" for c in sid)

    def test_default_sid_unique(self):
        """多次调用生成不同值。"""
        sids = {_default_sid() for _ in range(100)}
        assert len(sids) == 100


class TestHasSID:
    """测试 HasSID mixin。"""

    def test_has_sid_attribute_defined(self):
        """HasSID 定义了 sid 属性（通过 mapped_column）。"""
        assert hasattr(HasSID, "sid")

    def test_generate_sid_without_category(self):
        """generate_sid 无分类生成 'user-xxxx' 格式。"""

        class FakeModel(HasSID):
            id = None

        model = FakeModel()
        model.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        model.generate_sid("user")
        assert model.sid == "user-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_generate_sid_with_category(self):
        """generate_sid 带分类生成 'asse-post-xxxx' 格式。"""

        class FakeModel(HasSID):
            id = None

        model = FakeModel()
        model.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        model.generate_sid("asse", "post")
        assert model.sid == "asse-post-550e-8400-e29b-41d4-a716-4466-5544-0000"

    def test_generate_sid_auto_assigns_id(self):
        """id 为 None 时自动分配 UUID。"""

        class FakeModel(HasSID):
            id = None

        model = FakeModel()
        model.generate_sid("user")
        assert model.id is not None
        assert isinstance(model.id, uuid.UUID)
        assert model.sid.startswith("user-")

    def test_generate_sid_preserves_existing_id(self):
        """已有 id 时不重新分配。"""

        class FakeModel(HasSID):
            id = None

        model = FakeModel()
        existing_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        model.id = existing_id
        model.generate_sid("user")
        assert model.id == existing_id


class TestConfigEntry:
    """测试 ConfigEntry 模型字段。"""

    def test_config_entry_defaults(self):
        """ConfigEntry 默认值正确。"""
        entry = ConfigEntry()
        # server_default 仅作用于 DB 层，Python 级默认值为 None
        assert entry.value is None
        assert entry.group is None
        assert entry.is_sensitive is None
        assert entry.description is None

    def test_config_entry_with_values(self):
        """ConfigEntry 带初始值。"""
        entry = ConfigEntry(
            key="test_key",
            value="test_value",
            group="auth",
            is_sensitive=True,
        )
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.group == "auth"
        assert entry.is_sensitive is True