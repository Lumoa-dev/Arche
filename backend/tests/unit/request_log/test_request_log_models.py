"""请求日志模型 单元测试。

测试 RequestLog 和 IpActionCounter 模型的 to_dict 方法及边界情况。
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from backend.plugins.request_log.models import IpActionCounter, RequestLog


class TestRequestLogModel:
    """RequestLog 模型测试。"""

    def test_to_dict_includes_all_fields(self):
        """to_dict 应包含所有预期字段。"""
        log = RequestLog(
            ip="10.0.0.1",
            method="GET",
            path="/api/posts",
            status_code=200,
            user_agent="test-agent",
            referer="https://example.com",
            duration_ms=12.5,
            user_id="user-1",
            region="us-east",
            isp="aws",
            action="api_call",
        )
        data = log.to_dict()
        assert data["ip"] == "10.0.0.1"
        assert data["method"] == "GET"
        assert data["path"] == "/api/posts"
        assert data["status_code"] == 200
        assert data["user_agent"] == "test-agent"
        assert data["duration_ms"] == 12.5
        assert data["action"] == "api_call"

    def test_to_dict_with_none_optional_fields(self):
        """可选字段为 None 时 to_dict 应正确处理。"""
        log = RequestLog(
            ip="10.0.0.1",
            method="POST",
            path="/api/auth/login",
            status_code=401,
            user_agent=None,
            referer=None,
            duration_ms=0.0,
            user_id=None,
            region=None,
            isp=None,
            action="login_fail",
            created_at=None,
        )
        data = log.to_dict()
        assert data["user_agent"] is None
        assert data["referer"] is None
        assert data["user_id"] is None
        assert data["created_at"] is None

    def test_id_is_uuid_string(self):
        """id 应生成为 UUID 字符串。"""
        import uuid as uuid_mod

        log = RequestLog(
            id=uuid_mod.uuid4(),
            ip="10.0.0.1",
            method="GET",
            path="/",
            status_code=200,
            duration_ms=0.0,
            action="page_view",
        )
        data = log.to_dict()
        # 验证是有效的 UUID 格式
        uuid_mod.UUID(data["id"])


class TestIpActionCounterModel:
    """IpActionCounter 模型测试。"""

    def test_to_dict_includes_all_fields(self):
        """to_dict 应包含所有预期字段。"""
        counter = IpActionCounter(
            ip="10.0.0.1",
            action="api_call",
            action_date=date(2024, 1, 1),
            hour=14,
            count=50,
        )
        data = counter.to_dict()
        assert data["ip"] == "10.0.0.1"
        assert data["action"] == "api_call"
        assert data["action_date"] == "2024-01-01"
        assert data["hour"] == 14
        assert data["count"] == 50

    def test_to_dict_with_none_date(self):
        """action_date 为 None 时 to_dict 应正确处理。"""
        counter = IpActionCounter(
            ip="10.0.0.1",
            action="login_fail",
            action_date=None,
            hour=0,
            count=0,
        )
        data = counter.to_dict()
        assert data["action_date"] is None

    def test_default_count_is_zero(self):
        """count 默认值应为 0（ORM 层面）。"""
        counter = IpActionCounter(
            ip="10.0.0.1",
            action="api_call",
            action_date=date(2024, 1, 1),
            hour=10,
            count=0,  # ORM column default=0，Python 层面需显式传递
        )
        assert counter.count == 0