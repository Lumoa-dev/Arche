"""GitHub Proxy 全链路集成测试。

Mock 边界：httpx.AsyncClient（外部 HTTP 调用）和 asyncio.create_subprocess_exec（CLI 子进程）。  # noqa: E501
不 mock GitHubService 或 GhCliService 等业务服务层。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.plugins.github_proxy.services import GitHubService
from backend.tests.conftest import patch_container_service


@pytest.fixture
def github_service(db_container):
    """创建 GitHubService 实例并注入容器，确保路由和服务使用同一实例。"""
    svc = GitHubService(db_container)
    patch_container_service(db_container, "github", svc)
    return svc


@pytest.fixture
def mock_http_client(github_service):
    """替换 GitHub HttpProxyService 内部的 httpx 客户端为 mock。"""

    def _make(
        json_data: dict | None = None, content: bytes = b"", status_code: int = 200
    ):
        http_svc = github_service.http_service
        mock_client = AsyncMock()

        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.content = content
        resp.text = (content or b"").decode("utf-8", errors="replace")
        resp.headers = {"Content-Type": "application/json"}

        mock_client.request = AsyncMock(return_value=resp)
        mock_client.get = AsyncMock(return_value=resp)

        http_svc._client = mock_client
        return mock_client

    return _make


@pytest.fixture
def mock_subprocess():
    """Mock asyncio.create_subprocess_exec 返回模拟子进程。"""

    def _make(
        stdout_bytes: bytes = b'{"ok": true}',
        stderr_bytes: bytes = b"",
        returncode: int = 0,
    ):
        mock_proc = AsyncMock()
        mock_proc.returncode = returncode
        mock_proc.communicate.return_value = (stdout_bytes, stderr_bytes)
        mock_proc.wait.return_value = returncode

        patcher = patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
        mock_exec = patcher.start()
        mock_exec.return_value = mock_proc

        def _stop():
            patcher.stop()

        return mock_exec, _stop

    return _make


@pytest.mark.asyncio
class TestGitHubProxyAPI:
    """GitHub 代理 API 全链路集成测试。"""

    async def test_搜索仓库(self, client, admin_headers, mock_http_client):
        """搜索仓库接口应返回正确结构。"""
        mock_http_client(
            json_data={
                "total_count": 1,
                "items": [{"name": "test-repo", "full_name": "owner/test-repo"}],
            }
        )
        response = await client.get(
            "/api/github/search/repositories",
            params={"q": "python"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["total_count"] == 1

    async def test_代理GET请求(self, client, admin_headers, mock_http_client):
        """GET 代理接口应返回数据。"""
        mock_http_client(json_data={"login": "testuser", "id": 123})
        response = await client.get(
            "/api/github/user",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["login"] == "testuser"

    async def test_代理POST请求(self, client, admin_headers, mock_http_client):
        """POST 代理接口应转发 body 给 GitHub API。"""
        mock_client = mock_http_client(
            json_data={"id": 1, "name": "new-repo"},
            status_code=201,
        )
        response = await client.post(
            "/api/github/user/repos",
            headers=admin_headers,
            json={"name": "new-repo", "private": True},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new-repo"

        call_kwargs = mock_client.request.call_args.kwargs
        sent_body = call_kwargs.get("content")
        if sent_body:
            assert json.loads(sent_body) == {
                "name": "new-repo",
                "private": True,
            }

    async def test_代理原始文件(self, client, admin_headers, github_service):
        """静态资源代理接口——mock httpx.AsyncClient 构造器。

        proxy_raw_content 使用全新的 httpx.AsyncClient，需 mock 其构造器。
        """
        test_content = b"# Test README\nThis is a test file."

        class _FakeResponse:
            def __init__(self):
                self.status_code = 200
                self.content = test_content
                self.text = test_content.decode()
                self.headers = {"Content-Type": "text/plain"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_FakeResponse())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(httpx, "AsyncClient", return_value=mock_client):
            response = await client.get(
                "/api/github/raw/owner/repo/main/README.md",
                headers=admin_headers,
            )
        assert response.status_code == 200
        assert response.content == test_content

    async def test_健康检查(
        self, client, admin_headers, mock_subprocess, github_service
    ):
        """健康检查接口应返回 CLI 和 HTTP 状态。"""
        _mock_exec, stop = mock_subprocess(
            stdout_bytes=b'{"rate": {"limit": 5000, "used": 10}}'
        )
        try:
            response = await client.get(
                "/api/github/health/status",
                headers=admin_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == "ok"
            assert "cli" in data["data"]
            assert "http" in data["data"]
        finally:
            stop()

    async def test_清空缓存(self, client, admin_headers):
        """清空缓存接口（纯内存操作，无需 mock）。"""
        response = await client.post(
            "/api/github/cache/clear",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert "已清空" in data["message"]

    async def test_未登录返回401(self, client):
        """未登录用户访问应返回 401。"""
        for path in [
            "/api/github/health/status",
            "/api/github/user",
            "/api/github/raw/owner/repo/main/README.md",
            "/api/github/cache/clear",
        ]:
            response = await client.get(path)
            assert response.status_code == 401, (
                f"期望 401，实际 {response.status_code}：{path}"
            )

    async def test_proxy_mode参数传递(
        self, client, admin_headers, mock_http_client, mock_subprocess, github_service
    ):
        """mode 参数应被正确传递。"""
        # mode=cli —— 需要 mock subprocess
        _mock_exec, stop = mock_subprocess(stdout_bytes=b'{"ok": true}')
        try:
            resp = await client.get(
                "/api/github/user",
                params={"mode": "cli"},
                headers=admin_headers,
            )
            assert resp.status_code == 200
        finally:
            stop()

        # mode=http
        mock_http_client(json_data={})
        resp = await client.get(
            "/api/github/user",
            params={"mode": "http"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    async def test_缺失query参数不报错(self, client, admin_headers, mock_http_client):
        """缺失查询参数时不应抛出异常。"""
        mock_http_client(json_data={"total_count": 0, "items": []})
        response = await client.get(
            "/api/github/search/repositories",
            headers=admin_headers,
        )
        assert response.status_code == 200
