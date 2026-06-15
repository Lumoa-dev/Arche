"""monitor routes 单元测试。"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException, Request

from backend.plugins.monitor import routes


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


def _make_mock_request(user_id: str | None = None) -> Request:
    """创建一个带有认证用户状态和 mock 容器的 Request。"""
    if user_id is None:
        user_id = uuid.uuid4().hex
    mock_app = type(
        "MockApp",
        (),
        {"state": type("MockState", (), {"container": MockContainer()})()},
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
class TestMonitorRoutes:
    async def test_get_session_factory_db_not_ready(self, monkeypatch):
        class _Container:
            @staticmethod
            def get(_name):
                return None

        monkeypatch.setattr("backend.core.container.container", _Container())
        with pytest.raises(HTTPException) as exc:
            routes.get_session_factory()
        assert exc.value.status_code == 500

    async def test_template_crud_and_component_data(
        self, in_memory_db, monkeypatch, monitor_template_payload
    ):
        monkeypatch.setattr(
            routes, "get_session_factory", lambda: in_memory_db["session_factory"]
        )
        request = _make_mock_request()

        created = await routes.create_template(
            routes.TemplateCreate(**monitor_template_payload), request=request
        )
        assert created["name"] == "CPU Dashboard"
        tid = created["id"]

        listed = await routes.list_templates(request=request)
        assert len(listed) == 1

        one = await routes.get_template(tid, request=request)
        assert one["id"] == tid

        updated = await routes.update_template(
            tid,
            routes.TemplateUpdate(name="CPU Dashboard V2", refresh_interval=20),
            request=request,
        )
        assert updated["name"] == "CPU Dashboard V2"
        assert updated["refresh_interval"] == 20

        comp = await routes.get_component_data("cpu", request=request)
        assert comp["count_logical"] == 8
        assert comp["count_physical"] == 4

        deleted = await routes.delete_template(tid, request=request)
        assert deleted["message"] == "Template deleted"

    async def test_not_found_paths(self, in_memory_db, monkeypatch):
        monkeypatch.setattr(
            routes, "get_session_factory", lambda: in_memory_db["session_factory"]
        )
        request = _make_mock_request()

        with pytest.raises(HTTPException) as exc_get:
            await routes.get_template("missing", request=request)
        assert exc_get.value.status_code == 404

        with pytest.raises(HTTPException) as exc_put:
            await routes.update_template(
                "missing", routes.TemplateUpdate(name="x"), request=request
            )
        assert exc_put.value.status_code == 404

        with pytest.raises(HTTPException) as exc_del:
            await routes.delete_template("missing", request=request)
        assert exc_del.value.status_code == 404
