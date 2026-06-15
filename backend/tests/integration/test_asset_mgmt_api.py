"""Asset Mgmt 模块 API 集成测试。

测试真实 HTTP 请求-响应链路（HTTP → 中间件 → AssetMgmtService → 真实数据库）。
不 mock AssetMgmtService，使用真实 DB。

覆盖：
- 资产目录列表
- 资产搜索
- 资产统计
- 鉴权失败（403）边界
"""

from __future__ import annotations

import uuid

import pytest

from backend.plugins.asset_mgmt.services import AssetMgmtService
from backend.tests.conftest import patch_container_service


@pytest.fixture(autouse=True)
def real_asset_service(db_container):
    """用真实 AssetMgmtService 替换容器中的 mock 服务。"""
    asset_service = AssetMgmtService(db_container)
    patch_container_service(db_container, "asset_mgmt", asset_service)


@pytest.fixture
async def seed_blog_posts(in_memory_db, db_container):
    """为 admin 用户预置博客帖子资产。"""
    from backend.plugins.auth.services import AuthService

    # 创建 admin 用户（与 admin_headers 相同的方式）
    svc = AuthService(db_container)
    result = await svc.register(
        email="asset_admin@example.com",
        username="asset_admin",
        nickname="test_user",
        password="password123",
    )
    admin_id = uuid.UUID(result["user"]["id"])

    # 直接写 DB 创建帖子（绕过敏感词检测等复杂流程）
    from backend.plugins.blog.models import BlogPost

    async with in_memory_db["session_factory"]() as session:
        post1 = BlogPost(
            id=uuid.uuid4(),
            author_id=admin_id,
            title="资产测试文章1",
            slug="asset-test-post-1",
            status="published",
            required_level=5,
        )
        post1.generate_sid("asse")
        session.add(post1)

        post2 = BlogPost(
            id=uuid.uuid4(),
            author_id=admin_id,
            title="资产测试文章2",
            slug="asset-test-post-2",
            status="pending",
            required_level=5,
        )
        post2.generate_sid("asse")
        session.add(post2)
        await session.commit()

    return {"admin_id": admin_id}


@pytest.fixture
async def asset_admin_headers(db_container, seed_blog_posts):
    """返回 admin 用户的认证头。"""
    from backend.plugins.auth.services import AuthService

    svc = AuthService(db_container)
    result = await svc.login(identity="asset_admin@example.com", password="password123")
    return {"Authorization": f"Bearer {result['access_token']}"}


@pytest.mark.asyncio
class TestAssetMgmtAPI:
    """资产管理接口测试。"""

    async def test_asset_routes_require_admin(self, client, auth_headers):
        """普通用户无法访问资产管理接口。"""
        response = await client.get("/api/assets", headers=auth_headers)
        assert response.status_code == 403

    async def test_list_assets(self, client, asset_admin_headers, seed_blog_posts):
        """管理员可以列出资产。"""
        response = await client.get("/api/assets", headers=asset_admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert data["data"]["total"] >= 2
        titles = [item["title"] for item in data["data"]["items"]]
        assert "资产测试文章1" in titles
        assert "资产测试文章2" in titles

    async def test_list_assets_with_pagination(
        self, client, asset_admin_headers, seed_blog_posts
    ):
        """资产管理支持分页参数。"""
        response = await client.get(
            "/api/assets",
            params={"page": 1, "page_size": 1},
            headers=asset_admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["items"]) == 1
        assert data["data"]["total"] >= 2
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 1

    async def test_search_assets(self, client, asset_admin_headers, seed_blog_posts):
        """资产搜索按关键词过滤。"""
        response = await client.get(
            "/api/assets/search",
            params={"keyword": "资产测试"},
            headers=asset_admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert data["data"]["total"] >= 1
        titles = [item["title"] for item in data["data"]["items"]]
        assert "资产测试文章1" in titles

    async def test_asset_stats(self, client, asset_admin_headers, seed_blog_posts):
        """资产统计返回按类型分组的数据。"""
        response = await client.get("/api/assets/stats", headers=asset_admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "ok"
        assert data["data"]["total_assets"] >= 2
        assert "by_type" in data["data"]
        assert data["data"]["by_type"]["blog_post"] >= 2
