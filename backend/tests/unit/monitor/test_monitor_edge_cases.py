"""monitor 边界情况测试（模型 + 路由）。"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException, Request

from backend.plugins.monitor import routes
from backend.plugins.monitor.models import MonitorTemplate


class MockSystemMonitorService:
    @staticmethod
    def get_summary():
        return {"cpu_percent": 45.5, "memory_percent": 62.3, "disk_percent": 55.0}

    @staticmethod
    def get_cpu_detail():
        return {"count_logical": 8, "count_physical": 4, "per_cpu_pct": [45.5, 30.2]}

    @staticmethod
    def get_memory_detail():
        return {"total": 16777216000, "percent": 62.3}

    @staticmethod
    def get_disk_detail():
        return {"root_percent": 55.0, "partitions": []}

    @staticmethod
    def get_network_io():
        return {"bytes_sent": 1000, "bytes_recv": 2000}

    @staticmethod
    def get_processes(sort_by="cpu_percent"):  # noqa: ARG004
        return {"items": [], "total": 0, "limit": 50}

    @staticmethod
    def get_history(page=1, page_size=50):  # noqa: ARG004
        return {"items": [], "total": 0, "page": 1, "page_size": 50}


class MockContainer:
    @staticmethod
    def is_available(name):
        return name == "system_monitor"

    @staticmethod
    def get(name):
        if name == "system_monitor":
            return MockSystemMonitorService()
        msg = f"Service '{name}' not found"
        raise KeyError(msg)


class MockContainerNoMonitor:
    @staticmethod
    def is_available(name):  # noqa: ARG004
        return False

    @staticmethod
    def get(name):
        msg = f"Service '{name}' not found"
        raise KeyError(msg)


def _make_mock_request(user_id: str | None = None, container=None) -> Request:
    if user_id is None:
        user_id = uuid.uuid4().hex
    if container is None:
        container = MockContainer()
    mock_app = type(
        "MockApp",
        (),
        {"state": type("MockState", (), {"container": container})()},
    )()
    scope = {"type": "http", "app": mock_app}
    request = Request(scope)
    request.state.user = {
        "id": user_id,
        "username": "testadmin",
        "level": 0,
        "email": "",
        "blog_quality_level": 0,
    }
    return request


@pytest.mark.asyncio
class TestMonitorTemplateEdgeCases:
    """模板模型边界情况测试。"""

    async def test_empty_components_list(
        self, in_memory_db, monkeypatch, monitor_template_payload
    ):
        def _get_factory():
            return in_memory_db["session_factory"]

        monkeypatch.setattr(routes, "get_session_factory", _get_factory)
        payload = {**monitor_template_payload, "components": []}
        request = _make_mock_request()
        created = await routes.create_template(
            routes.TemplateCreate(**payload), request=request
        )
        assert created["components"] == []

    async def test_missing_user_id(self):
        tpl = MonitorTemplate(
            name="No User Template",
            user_id=None,
            components=[],
            refresh_interval=30,
            created_at=None,
            updated_at=None,
        )
        data = tpl.to_dict()
        assert data["user_id"] is None

    async def test_very_long_name(self, in_memory_db, monkeypatch):
        def _get_factory():
            return in_memory_db["session_factory"]

        monkeypatch.setattr(routes, "get_session_factory", _get_factory)
        long_name = "A" * 200
        request = _make_mock_request()
        created = await routes.create_template(
            routes.TemplateCreate(name=long_name, components=[]), request=request
        )
        assert created["name"] == long_name

    async def test_to_dict_with_none_timestamps(self):
        tpl = MonitorTemplate(
            name="No Timestamps",
            user_id=None,
            components=[],
            refresh_interval=30,
            created_at=None,
            updated_at=None,
        )
        data = tpl.to_dict()
        assert data["created_at"] is None
        assert data["updated_at"] is None


@pytest.mark.asyncio
class TestMonitorRouteEdgeCases:
    """路由边界情况测试。"""

    async def test_get_component_data_invalid_id(self):
        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await routes.get_component_data("invalid_component", request=request)
        assert exc.value.status_code == 400

    async def test_get_component_data_service_unavailable(self):
        request = _make_mock_request(container=MockContainerNoMonitor())
        with pytest.raises(HTTPException) as exc:
            await routes.get_component_data("cpu", request=request)
        assert exc.value.status_code == 503

    async def test_invalid_uuid_format_returns_404(self, in_memory_db, monkeypatch):
        def _get_factory():
            return in_memory_db["session_factory"]

        monkeypatch.setattr(routes, "get_session_factory", _get_factory)
        request = _make_mock_request()
        with pytest.raises(HTTPException) as exc:
            await routes.get_template("not-a-uuid", request=request)
        assert exc.value.status_code == 404

    async def test_cross_user_isolation(
        self, in_memory_db, monkeypatch, monitor_template_payload
    ):
        def _get_factory():
            return in_memory_db["session_factory"]

        monkeypatch.setattr(routes, "get_session_factory", _get_factory)
        user_a_id = uuid.uuid4().hex
        user_b_id = uuid.uuid4().hex
        request_a = _make_mock_request(user_id=user_a_id)
        request_b = _make_mock_request(user_id=user_b_id)

        created = await routes.create_template(
            routes.TemplateCreate(**monitor_template_payload), request=request_a
        )
        tid = created["id"]

        listed_b = await routes.list_templates(request=request_b)
        assert len(listed_b) == 0

        with pytest.raises(HTTPException) as exc:
            await routes.get_template(tid, request=request_b)
        assert exc.value.status_code == 404

    async def test_empty_template_list_for_new_user(self, in_memory_db, monkeypatch):
        def _get_factory():
            return in_memory_db["session_factory"]

        monkeypatch.setattr(routes, "get_session_factory", _get_factory)
        request = _make_mock_request()
        listed = await routes.list_templates(request=request)
        assert listed == []
