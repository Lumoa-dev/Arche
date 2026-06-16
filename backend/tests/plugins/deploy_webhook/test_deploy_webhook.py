"""部署 Webhook 插件测试（公开接口 Token 校验）。"""

from __future__ import annotations

import pytest


class TestDeployWebhook:
    """部署 Webhook —— 公开 POST 端点，依赖 DEPLOY_TOKEN 环境变量。"""

    DEPLOY_URL = "/api/deploy"

    @pytest.mark.asyncio
    async def test_deploy_without_token(self, async_client):
        """无 Token 返回 401。"""
        resp = await async_client.post(self.DEPLOY_URL, json={})
        assert resp.status_code == 401
        data = resp.json()
        assert "detail" in data or "auth" in data.get("code", "").lower() or "token" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_deploy_with_invalid_token(self, async_client):
        """无效 Token 返回 401。"""
        resp = await async_client.post(self.DEPLOY_URL, json={"token": "wrong-token"})
        assert resp.status_code == 401
        data = resp.json()
        assert "auth" in data.get("code", "").lower()

    @pytest.mark.asyncio
    async def test_deploy_with_empty_body(self, async_client):
        """空 body 返回 401 或 422。"""
        resp = await async_client.post(
            self.DEPLOY_URL,
            json={},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (401, 422)
        if resp.status_code == 422:
            assert "validation" in resp.json().get("code", "").lower()

    @pytest.mark.asyncio
    async def test_deploy_without_content_type(self, async_client):
        """无 Content-Type 返回 422 或 401。"""
        resp = await async_client.post(self.DEPLOY_URL, content=b"{}")
        assert resp.status_code in (401, 422)
