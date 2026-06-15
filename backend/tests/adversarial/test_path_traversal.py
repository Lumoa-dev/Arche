from __future__ import annotations

import pytest

from backend.tests.adversarial.conftest import PATH_TRAVERSAL_PAYLOADS
from backend.tests.conftest import patch_container_service


class TestPathTraversal:
    PAYLOADS = PATH_TRAVERSAL_PAYLOADS

    @pytest.fixture(autouse=True)
    def setup_storage_service(self, db_container):
        from backend.plugins.oss.services import StorageService

        storage_service = StorageService(db_container)
        patch_container_service(db_container, "storage", storage_service)

    async def _upload_with_filename(self, client, auth_headers, filename):
        resp = await client.post(
            "/api/oss/upload",
            files={"file": (filename, b"safe content", "image/png")},
            headers=auth_headers,
        )
        return resp

    async def test_oss_upload_rejects_path_traversal(self, client, auth_headers):
        for payload in self.PAYLOADS:
            resp = await self._upload_with_filename(client, auth_headers, payload)
            assert resp.status_code in (400, 415, 422), (
                f"Path traversal payload not rejected: {payload}, got {resp.status_code}"
            )
            data = resp.json()
            assert data["code"] in (
                "error",
                "invalid_filename",
                "file_type_not_allowed",
            )

    async def test_crawler_file_download_rejects_path_traversal(
        self, client, admin_headers, db_container
    ):
        import uuid
        from unittest.mock import AsyncMock

        record_id = str(uuid.uuid4())

        async def mock_get_record(rid):
            return {
                "file_path": "../../../etc/passwd",
                "id": rid,
                "url": "http://example.com",
            }

        crawler_mock = AsyncMock()
        crawler_mock.get_record = mock_get_record
        patch_container_service(db_container, "crawler", crawler_mock)

        resp = await client.get(
            f"/api/crawler/records/{record_id}/file",
            headers=admin_headers,
        )
        data = resp.json()
        assert data["code"] in ("error", "not_found")

    async def test_crawler_file_download_rejects_absolute_path(
        self, client, admin_headers, db_container
    ):
        import uuid
        from unittest.mock import AsyncMock

        record_id = str(uuid.uuid4())

        async def mock_get_record(rid):
            return {
                "file_path": "/etc/passwd",
                "id": rid,
                "url": "http://example.com",
            }

        crawler_mock = AsyncMock()
        crawler_mock.get_record = mock_get_record
        patch_container_service(db_container, "crawler", crawler_mock)

        resp = await client.get(
            f"/api/crawler/records/{record_id}/file",
            headers=admin_headers,
        )
        data = resp.json()
        assert data["code"] in ("error", "not_found")
