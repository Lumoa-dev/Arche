"""GitHub 代理插件测试（require_level=1）。

外部 HTTP 请求通过 pytest-httpx 模拟，无需真实 GitHub API 调用。
"""

from __future__ import annotations

import pytest

PREFIX = "/api/github"


class TestGitHubProxy:
    """GitHub 代理 —— 通过 pytest-httpx 模拟外部调用。"""

    @pytest.mark.asyncio
    async def test_health(self, async_client, admin_headers):
        """健康检查不调用外部 GitHub API。"""
        resp = await async_client.get(f"{PREFIX}/health/status", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert "data" in data

    @pytest.mark.asyncio
    async def test_health_no_auth(self, async_client):
        resp = await async_client.get(f"{PREFIX}/health/status")
        assert resp.status_code == 401
        data = resp.json()
        assert "auth" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_cache_clear_requires_auth(self, async_client):
        resp = await async_client.post(f"{PREFIX}/cache/clear")
        assert resp.status_code == 401
        data = resp.json()
        assert "auth" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_cache_clear(self, async_client, admin_headers):
        resp = await async_client.post(f"{PREFIX}/cache/clear", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"

    @pytest.mark.asyncio
    async def test_raw_file(self, async_client, admin_headers, httpx_mock):
        """GET /raw/{path} 代理到 raw.githubusercontent.com（由 pytest-httpx 拦截）。

        HttpProxyService.proxy_raw_content 内部创建 httpx.AsyncClient 并请求
        https://raw.githubusercontent.com/owner/repo/branch/file.py，
        pytest-httpx 拦截该请求并返回模拟响应。
        """
        httpx_mock.add_response(
            url="https://raw.githubusercontent.com/owner/repo/branch/file.py",
            content=b"print('hello world')\n",
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

        resp = await async_client.get(
            f"{PREFIX}/raw/owner/repo/branch/file.py",
            headers=admin_headers,
        )
        assert resp.status_code == 200, f"raw 代理失败: {resp.text}"
        assert resp.content == b"print('hello world')\n"
        # Content-Type 可能因 pytest-httpx 模拟的响应头大小写而不同，
        # 但一定不是 HTML（proxy_raw_content 走 HTTP 模式返回模拟数据）
        assert resp.headers.get("content-type", "") != "text/html"
