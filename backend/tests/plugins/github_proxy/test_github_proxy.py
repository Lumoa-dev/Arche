"""GitHub 代理插件测试（require_level=1）。"""

from __future__ import annotations

import pytest

PREFIX = "/api/github"


class TestGitHubProxy:
    """GitHub 代理 —— 部分端点依赖外部服务。"""

    @pytest.mark.asyncio
    async def test_health(self, async_client, admin_headers):
        """健康检查不调用外部 GitHub API。"""
        resp = await async_client.get(f"{PREFIX}/health/status", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_no_auth(self, async_client):
        resp = await async_client.get(f"{PREFIX}/health/status")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_cache_clear_requires_auth(self, async_client):
        resp = await async_client.post(f"{PREFIX}/cache/clear")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_cache_clear(self, async_client, admin_headers):
        resp = await async_client.post(f"{PREFIX}/cache/clear", headers=admin_headers)
        assert resp.status_code == 200


@pytest.mark.real
class TestGitHubProxyReal:
    """需要真实外部 GitHub 的测试（默认跳过，CI 中通过 -m real 执行）。"""

    @pytest.mark.asyncio
    async def test_raw_file(self, async_client, admin_headers):
        """GET /raw/{path} 代理到 raw.githubusercontent.com。"""
        resp = await async_client.get(
            f"{PREFIX}/raw/owner/repo/branch/file.py",
            headers=admin_headers,
        )
        assert resp.status_code in (200, 301, 302, 404, 502, 503)
