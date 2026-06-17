"""云训练插件测试（全部 require_level=0）。"""

from __future__ import annotations

import pytest

PREFIX = "/api/cloud"


class TestCloudIntegration:
    """内部路由 —— 不调用外部云 API。"""

    @pytest.mark.asyncio
    async def test_stats(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        # stats 应包含统计字段
        assert "data" in data

    @pytest.mark.asyncio
    async def test_stats_forbidden(self, async_client, auth_headers):
        resp = await async_client.get(f"{PREFIX}/stats", headers=auth_headers)
        assert resp.status_code == 403
        data = resp.json()
        assert "permission" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_stats_no_auth(self, async_client):
        resp = await async_client.get(f"{PREFIX}/stats")
        assert resp.status_code == 401
        data = resp.json()
        assert "auth" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/jobs", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert "data" in data

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, async_client, admin_headers):
        """不存在的任务返回 not_found 或 internal_error。"""
        resp = await async_client.get(
            f"{PREFIX}/jobs/nonexistent-job-id", headers=admin_headers
        )
        data = resp.json()
        assert data["code"] in ("not_found", "error", "internal_error")

    @pytest.mark.asyncio
    async def test_costs(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/costs", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert "data" in data

    @pytest.mark.asyncio
    async def test_datasets(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/datasets", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert "data" in data

    @pytest.mark.asyncio
    async def test_artifacts(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/artifacts", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert "data" in data

    @pytest.mark.asyncio
    async def test_repos(self, async_client, admin_headers):
        resp = await async_client.get(f"{PREFIX}/repos", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ok"
        assert "data" in data

    @pytest.mark.asyncio
    async def test_gpu_metrics_invalid_id(self, async_client, admin_headers):
        """无效实例 ID 返回 error/not_found/internal_error。"""
        resp = await async_client.get(
            f"{PREFIX}/instances/invalid-id/gpu-metrics", headers=admin_headers
        )
        data = resp.json()
        assert data["code"] in ("error", "not_found", "internal_error")
