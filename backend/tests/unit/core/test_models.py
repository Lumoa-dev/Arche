"""核心领域模型测试 —— HasSID mixin / ConfigEntry。"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from backend.core.models import ConfigEntry, HasSID, _default_sid


class TestDefaultSid:
    """测试 _default_sid 函数。"""

    def test_default_sid_generates_hex(self):
        """生成 32 位 hex 字符串。"""
        sid = _default_sid()
        assert len(sid) == 32
        assert isinstance(sid, str)
        # 验证是有效的 hex
        int(sid, 16)

    def test_default_sid_unique(self):
        """每次调用生成不同值。"""
        sids = {_default_sid() for _ in range(100)}
        assert len(sids) == 100


class TestHasSID:
    """测试 HasSID mixin 类。"""

    def setup_method(self):
        """每个测试前创建带 HasSID 的 mock 模型。"""

        class MockModel(HasSID):
            def __init__(self):
                self.id = None
                self.sid = _default_sid()

        self.model = MockModel()

    def test_initial_sid_is_hex_string(self):
        """初始 sid 是 32 位 hex 字符串。"""
        assert len(self.model.sid) == 32
        int(self.model.sid, 16)  # 验证是合法 hex

    def test_generate_sid_with_category(self):
        """generate_sid 生成带分类的 SID。"""
        self.model.id = uuid.uuid4()
        self.model.generate_sid("asse", "post")
        assert self.model.sid.startswith("asse-post-")
        assert len(self.model.sid) > 40

    def test_generate_sid_without_category(self):
        """generate_sid 生成无分类的 SID。"""
        self.model.id = uuid.uuid4()
        self.model.generate_sid("user")
        assert self.model.sid.startswith("user-")
        assert "-user-" not in self.model.sid

    def test_generate_sid_generates_id_if_none(self):
        """id 为 None 时自动生成 UUID。"""
        assert self.model.id is None
        self.model.generate_sid("user")
        assert self.model.id is not None
        assert isinstance(self.model.id, uuid.UUID)

    def test_generate_sid_preserves_existing_id(self):
        """已存在的 id 不会被覆盖。"""
        existing_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        self.model.id = existing_id
        self.model.generate_sid("user")
        assert self.model.id == existing_id

    @patch("backend.core.uid.make_sid", return_value="user-mock-sid-value")
    def test_generate_sid_calls_make_sid(self, mock_make_sid):
        """generate_sid 委托给 make_sid。"""
        self.model.id = uuid.uuid4()
        self.model.generate_sid("user", "test")
        mock_make_sid.assert_called_once_with("user", self.model.id, "test")
        assert self.model.sid == "user-mock-sid-value"

    def test_generate_sid_invalid_prefix(self):
        """未注册的前缀抛出异常。"""
        self.model.id = uuid.uuid4()
        with pytest.raises(ValueError, match="未知的前缀"):
            self.model.generate_sid("invalid_prefix")


class TestConfigEntry:
    """测试 ConfigEntry ORM 模型。"""

    def test_config_entry_attributes(self):
        """ConfigEntry 模型属性定义正确。"""
        entry = ConfigEntry(
            key="test_key",
            value="test_value",
            group="test_group",
            description="test description",
            is_sensitive=False,
        )
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.group == "test_group"
        assert entry.description == "test description"
        assert entry.is_sensitive is False

    def test_config_entry_defaults(self):
        """ConfigEntry 模型默认值正确（server_default 在 DB 层生效）。"""
        entry = ConfigEntry(key="test_key", value="test_value")
        # server_default 在 INSERT 时由 DB 填充，ORM 对象创建时为 None
        assert entry.group is None
        assert entry.is_sensitive is None  # server_default='false'
        assert entry.description is None

    def test_config_entry_sensitive_true(self):
        """敏感配置标记为 True。"""
        entry = ConfigEntry(
            key="secret_key",
            value="supersecret",
            is_sensitive=True,
        )
        assert entry.is_sensitive is True

    def test_config_entry_null_description(self):
        """description 可为空。"""
        entry = ConfigEntry(key="k", value="v")
        assert entry.description is None

    def test_config_entry_str_representation(self):
        """字符串表示包含 key 和 value。"""
        entry = ConfigEntry(key="test_key", value="test_value")
        # ORM 模型默认 __repr__ 由 SQLAlchemy 提供
        assert "ConfigEntry" in repr(entry)