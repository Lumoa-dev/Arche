from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.plugins.oss.services import ALLOWED_MIME_TYPES
from backend.tests.conftest import patch_container_service


def _validate_mime(content_type):
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        from backend.core.middleware import AppError

        raise AppError(
            f"不支持的文件类型: {content_type}",
            code="file_type_not_allowed",
            status_code=415,
        )


def _validate_filename(filename):
    if ".." in filename or "/" in filename or "\\" in filename:
        from backend.core.middleware import AppError

        raise AppError("文件名包含非法字符", code="invalid_filename", status_code=400)


def _make_mock_storage():
    mock = AsyncMock()

    async def upload_file(file, owner_id, user_level=5, is_private=False):
        _validate_mime(file.content_type)
        filename = file.filename or "unnamed"
        _validate_filename(filename)
        content = await file.read()
        return {
            "id": "mock-id",
            "owner_id": str(owner_id),
            "path": f"users/{owner_id}/{filename}",
            "size": len(content),
            "mime_type": file.content_type,
            "storage_type": "local",
            "is_private": is_private,
        }

    mock.upload_file = upload_file
    return mock


class TestFileUploadSecurity:
    @pytest.fixture(autouse=True)
    def setup_storage_service(self, db_container):
        mock = _make_mock_storage()
        patch_container_service(db_container, "storage", mock)

    async def test_mismatched_mime_type(self, client, auth_headers):
        shell_script = b"#!/bin/bash\necho pwned"
        resp = await client.post(
            "/api/oss/upload",
            files={"file": ("exploit.sh", shell_script, "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code != 500, "MIME mismatch caused 500"
        data = resp.json()
        if resp.status_code == 200:
            assert data["code"] == "ok"
        else:
            assert "code" in data

    async def test_special_chars_in_filename(self, client, auth_headers):
        resp = await client.post(
            "/api/oss/upload",
            files={"file": ("foo<>bar.txt", b"test content", "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code != 500, "Special chars filename caused 500"
        data = resp.json()
        if resp.status_code == 200:
            assert data["code"] == "ok"
        else:
            assert "code" in data

    async def test_zero_byte_file(self, client, auth_headers):
        resp = await client.post(
            "/api/oss/upload",
            files={"file": ("empty.png", b"", "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code != 500, "Zero-byte file caused 500"
        data = resp.json()
        if resp.status_code == 200:
            assert data["code"] == "ok"
        else:
            assert "code" in data

    async def test_double_extension(self, client, auth_headers):
        resp = await client.post(
            "/api/oss/upload",
            files={
                "file": (
                    "shell.php.jpg",
                    b"<?php system($_GET['cmd']); ?>",
                    "image/jpeg",
                )
            },
            headers=auth_headers,
        )
        assert resp.status_code != 500, "Double extension file caused 500"
        data = resp.json()
        if resp.status_code == 200:
            assert data["code"] == "ok"
        else:
            assert "code" in data

    async def test_svg_with_embedded_xss(self, client, auth_headers):
        """SVG 文件中嵌入 XSS 脚本应被安全处理。"""
        svg_xss = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b"<script>alert(1)</script>"
            b"<text>hello</text></svg>"
        )
        resp = await client.post(
            "/api/oss/upload",
            files={"file": ("evil.svg", svg_xss, "image/svg+xml")},
            headers=auth_headers,
        )
        # SVG 可能不在 ALLOWED_MIME_TYPES 中，所以可能被拒绝
        # 关键是不要返回 500
        assert resp.status_code != 500, "SVG XSS file caused 500"

    async def test_oversized_filename(self, client, auth_headers):
        """超长文件名应被拒绝或安全处理。"""
        long_name = "x" * 500 + ".png"
        resp = await client.post(
            "/api/oss/upload",
            files={"file": (long_name, b"test content", "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code != 500, "Oversized filename caused 500"
        data = resp.json()
        assert "code" in data

    async def test_unicode_normalization_attack(self, client, auth_headers):
        """Unicode 规范化绕过测试。"""
        unicode_names = [
            "shell\u2024png",  # 使用 U+2024 ONE DOT LEADER 代替 .
            "shell\uff0ephp",  # 使用全角 .
            "a\u0000b.png",  # null byte injection
            "..%252f..%252fetc",  # double URL encoding
        ]
        for name in unicode_names:
            resp = await client.post(
                "/api/oss/upload",
                files={"file": (name, b"test", "image/png")},
                headers=auth_headers,
            )
            assert resp.status_code != 500, (
                f"Unicode filename attack caused 500: {name}"
            )
