"""搜索插件测试。"""

from __future__ import annotations

import pytest

PREFIX = "/api/search"


class TestSearch:
    """搜索建议接口。"""

    @pytest.mark.asyncio
    async def test_suggestions_with_query(self, async_client, auth_headers):
        resp = await async_client.get(
            f"{PREFIX}/suggestions?q=test", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_suggestions_no_query(self, async_client, auth_headers):
        """无查询参数应返回 422（q 是必填参数）。"""
        resp = await async_client.get(f"{PREFIX}/suggestions", headers=auth_headers)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_suggestions_chinese_query(self, async_client, auth_headers):
        resp = await async_client.get(
            f"{PREFIX}/suggestions?q=测试", headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_suggestions_special_chars(self, async_client, auth_headers):
        resp = await async_client.get(
            f"{PREFIX}/suggestions?q=<script>alert(1)</script>",
            headers=auth_headers,
        )
        assert resp.status_code in (200, 400)

    @pytest.mark.asyncio
    async def test_suggestions_very_long_query(self, async_client, auth_headers):
        long_q = "a" * 1000
        resp = await async_client.get(
            f"{PREFIX}/suggestions?q={long_q}", headers=auth_headers
        )
        assert resp.status_code in (200, 400, 422)

    @pytest.mark.asyncio
    async def test_suggestions_no_auth(self, async_client):
        """目前搜索需要认证（未在 PUBLIC_PATHS 中）。"""
        resp = await async_client.get(f"{PREFIX}/suggestions?q=test")
        assert resp.status_code == 401
