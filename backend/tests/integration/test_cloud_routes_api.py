"""云训练全链路集成测试。

Mock 边界：无。CloudTrainingService 使用 MockProvider（纯内存实现，不调用任何外部 API）。  # noqa: E501
所有 CRUD 操作使用真实的内存 SQLite 数据库。
不 mock CloudTrainingService 或其任何内部方法。
"""

from __future__ import annotations

import pytest

from backend.plugins.cloud_integration.services import CloudTrainingService
from backend.tests.conftest import patch_container_service


@pytest.fixture
def cloud_training_service(db_container):
    """使用真实 CloudTrainingService（MockProvider 纯内存）注入容器。"""
    svc = CloudTrainingService(db_container)
    patch_container_service(db_container, "cloud_training", svc)
    return svc


@pytest.mark.asyncio
class TestCloudRoutesAPI:
    """云训练 API 全链路集成测试。"""

    async def test_unauthenticated_returns_401(self, client):
        """未登录访问云训练接口应返回 401。"""
        for path in [
            "/api/cloud/jobs",
            "/api/cloud/costs",
            "/api/cloud/stats",
        ]:
            response = await client.get(path)
            assert response.status_code == 401

    async def test_create_and_list_jobs(
        self, client, admin_headers, cloud_training_service
    ):
        """创建训练任务后可在列表中查到。"""
        list1 = await client.get("/api/cloud/jobs", headers=admin_headers)
        assert list1.status_code == 200
        assert list1.json()["data"]["total"] == 0

        payload = {
            "name": "test-job",
            "config": {"provider": "mock", "gpu_type": "RTX4090"},
            "repo_url": "https://github.com/a/b.git",
            "repo_branch": "main",
        }
        created = await client.post(
            "/api/cloud/jobs", headers=admin_headers, json=payload
        )
        assert created.status_code == 200
        job_id = created.json()["data"]["id"]

        list2 = await client.get("/api/cloud/jobs", headers=admin_headers)
        assert list2.status_code == 200
        assert list2.json()["data"]["total"] == 1

        detail = await client.get(f"/api/cloud/jobs/{job_id}", headers=admin_headers)
        assert detail.status_code == 200
        assert detail.json()["data"]["name"] == "test-job"

    async def test_job_status_transition(
        self, client, admin_headers, cloud_training_service
    ):
        """任务状态转换：pending → running → completed。"""
        payload = {
            "name": "status-test",
            "config": {"provider": "mock", "gpu_type": "RTX4090"},
            "repo_url": "https://github.com/a/b.git",
        }
        created = await client.post(
            "/api/cloud/jobs", headers=admin_headers, json=payload
        )
        job_id = created.json()["data"]["id"]

        started = await client.post(
            f"/api/cloud/jobs/{job_id}/start", headers=admin_headers
        )
        assert started.status_code == 200

        completed = await client.post(
            f"/api/cloud/jobs/{job_id}/complete",
            params={"result_path": "runs/out"},
            headers=admin_headers,
        )
        assert completed.status_code == 200

    async def test_删除任务(self, client, admin_headers, cloud_training_service):
        """创建后删除任务。"""
        payload = {
            "name": "delete-test",
            "config": {"provider": "mock", "gpu_type": "RTX4090"},
            "repo_url": "https://github.com/a/b.git",
        }
        created = await client.post(
            "/api/cloud/jobs", headers=admin_headers, json=payload
        )
        job_id = created.json()["data"]["id"]

        deleted = await client.delete(
            f"/api/cloud/jobs/{job_id}", headers=admin_headers
        )
        assert deleted.status_code == 200
        assert deleted.json()["code"] == "ok"

    async def test_实例创建和列表(self, client, admin_headers, cloud_training_service):
        """为任务创建和管理训练实例。"""
        payload = {
            "name": "instance-test",
            "config": {"provider": "mock", "gpu_type": "RTX4090"},
            "repo_url": "https://github.com/a/b.git",
        }
        created = await client.post(
            "/api/cloud/jobs", headers=admin_headers, json=payload
        )
        job_id = created.json()["data"]["id"]

        inst_payload = {
            "instance_name": "gpu-1",
            "gpu_type": "RTX4090",
            "provider": "mock",
        }
        created_inst = await client.post(
            f"/api/cloud/jobs/{job_id}/instances",
            headers=admin_headers,
            json=inst_payload,
        )
        assert created_inst.status_code == 200
        instance_id = created_inst.json()["data"]["id"]

        inst_list = await client.get(
            f"/api/cloud/jobs/{job_id}/instances", headers=admin_headers
        )
        assert inst_list.status_code == 200
        assert inst_list.json()["data"]["total"] >= 1

        # 启动实例（pending → running）
        started = await client.post(
            f"/api/cloud/instances/{instance_id}/start", headers=admin_headers
        )
        assert started.status_code == 200

    async def test_dataset_management(
        self, client, admin_headers, cloud_training_service
    ):
        """数据集的 CRUD 和同步操作。"""
        ds_payload = {
            "name": "my-dataset",
            "description": "test dataset",
            "path": "datasets/test/v1",
            "source": "local",
            "tags": ["demo"],
            "config": {},
        }
        created = await client.post(
            "/api/cloud/datasets", headers=admin_headers, json=ds_payload
        )
        assert created.status_code == 200
        dataset_id = created.json()["data"]["id"]

        detail = await client.get(
            f"/api/cloud/datasets/{dataset_id}", headers=admin_headers
        )
        assert detail.status_code == 200
        assert detail.json()["data"]["name"] == "my-dataset"

        list_resp = await client.get("/api/cloud/datasets", headers=admin_headers)
        assert list_resp.status_code == 200
        assert list_resp.json()["data"]["total"] >= 1

        sync_resp = await client.post(
            f"/api/cloud/datasets/{dataset_id}/sync", headers=admin_headers
        )
        assert sync_resp.status_code == 200

        delete_resp = await client.delete(
            f"/api/cloud/datasets/{dataset_id}", headers=admin_headers
        )
        assert delete_resp.status_code == 200

    async def test_repo_management(self, client, admin_headers, cloud_training_service):
        """代码仓库的 CRUD 和同步。"""
        repo_payload = {
            "name": "my-repo",
            "git_url": "https://github.com/a/b.git",
            "git_branch": "main",
        }
        created = await client.post(
            "/api/cloud/repos", headers=admin_headers, json=repo_payload
        )
        assert created.status_code == 200
        repo_id = created.json()["data"]["id"]

        list_resp = await client.get("/api/cloud/repos", headers=admin_headers)
        assert list_resp.status_code == 200
        assert list_resp.json()["data"]["total"] >= 1

        sync_resp = await client.post(
            f"/api/cloud/repos/{repo_id}/sync", headers=admin_headers
        )
        assert sync_resp.status_code == 200

        delete_resp = await client.delete(
            f"/api/cloud/repos/{repo_id}", headers=admin_headers
        )
        assert delete_resp.status_code == 200

    async def test_费用查询(self, client, admin_headers, cloud_training_service):
        """费用查询接口应返回合法结构。"""
        response = await client.get("/api/cloud/costs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert "total_cost" in data["data"]

    async def test_statistics(self, client, admin_headers, cloud_training_service):
        """工作台统计接口。"""
        response = await client.get("/api/cloud/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert "running_jobs" in data["data"]
        assert "running_instances" in data["data"]
