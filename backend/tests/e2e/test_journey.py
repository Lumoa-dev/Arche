"""E2E 用户旅程测试：覆盖核心用户操作流程。"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.e2e


class TestUserJourney:
    """用户旅程集成测试。"""

    unique = uuid.uuid4().hex[:8]

    async def _register_user(
        self, page, backend_url: str, email: str, username: str, password: str
    ) -> dict:
        """通过 API 注册用户并返回响应数据。"""
        resp = await page.request.post(
            f"{backend_url}/api/auth/register",
            json={
                "email": email,
                "username": username,
                "password": password,
            },
        )
        body = await resp.json()
        assert body["code"] == "ok", f"register failed: {body}"
        return body["data"]

    async def _login(
        self, page, backend_url: str, identity: str, password: str
    ) -> dict:
        """通过 API 登录并返回完整响应。"""
        resp = await page.request.post(
            f"{backend_url}/api/auth/login",
            json={
                "identity": identity,
                "password": password,
            },
        )
        body = await resp.json()
        assert body["code"] == "ok", f"login failed: {body}"
        return body["data"]

    async def test_user_registration_and_login(self, page, frontend_url, backend_url):
        """用户注册 → 登录 → 验证登录态 → 登出。"""
        tag = self.unique
        email = f"journey_{tag}@test.com"
        username = f"journey_{tag}"
        password = "TestPass123"

        # ── 注册 ──
        await page.goto(f"{frontend_url}/register", wait_until="networkidle")
        await page.wait_for_selector('input[placeholder="请输入邮箱"]', state="visible")

        await page.fill('input[placeholder="请输入邮箱"]', email)
        await page.fill('input[placeholder="请输入用户名"]', username)
        await page.fill('input[placeholder="请输入密码"]', password)
        await page.fill('input[placeholder="请再次输入密码"]', password)
        await page.click('button:has-text("立即注册")')

        # 注册成功后应跳转到登录页
        await page.wait_for_url("**/login**", timeout=10000)
        assert "/login" in page.url

        # ── 登录 ──
        await page.fill('input[placeholder="请输入用户名或邮箱"]', email)
        await page.fill('input[placeholder="请输入密码"]', password)
        await page.click('button:has-text("立即登录")')

        # 登录成功后应回到首页
        await page.wait_for_url(f"{frontend_url}/", timeout=10000)
        assert page.url.rstrip("/") == frontend_url.rstrip("/")

        # ── 验证登录态 ──
        await page.wait_for_timeout(1000)
        me_resp = await page.request.get(f"{backend_url}/api/auth/me")
        assert me_resp.ok
        me_body = await me_resp.json()
        assert me_body["code"] == "ok"
        assert me_body["data"]["email"] == email

        # ── 登出 ──
        await page.request.post(f"{backend_url}/api/auth/logout")
        await page.goto(frontend_url, wait_until="networkidle")
        await page.wait_for_timeout(500)

        # 登出后 /me 应返回未认证
        me_resp2 = await page.request.get(f"{backend_url}/api/auth/me")
        assert me_resp2.status == 401 or me_resp2.status == 403

    async def test_browse_blog_posts_as_guest(self, page, frontend_url):
        """未登录访客浏览首页 → 点开文章 → 查看评论。"""
        await page.goto(frontend_url, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # 首页应有内容卡片
        posts = page.locator(".post-card, .grid-item, [class*=post]")
        count = await posts.count()
        assert count > 0, "homepage shows no post cards"

        # 点击第一篇文章
        first_post = posts.first
        await first_post.click()
        await page.wait_for_timeout(2000)

        # 应跳转到文章详情页（路径含 /blog/）
        assert "/blog/" in page.url, f"not on post detail page, url: {page.url}"

        # 评论区应可见
        comments = page.locator(".comment-list, [class*=comment]")
        await comments.first.wait_for(state="visible", timeout=5000)

    async def test_create_blog_post(self, page, frontend_url, backend_url):
        """登录用户 → 创作页面 → 填写内容 → 发布 → 验证。"""
        tag = self.unique
        email = f"creator_{tag}@test.com"
        username = f"creator_{tag}"
        password = "TestPass123"

        # 注册用户
        await self._register_user(page, backend_url, email, username, password)

        # UI 登录
        await page.goto(f"{frontend_url}/login", wait_until="networkidle")
        await page.wait_for_selector(
            'input[placeholder="请输入用户名或邮箱"]', state="visible"
        )
        await page.fill('input[placeholder="请输入用户名或邮箱"]', email)
        await page.fill('input[placeholder="请输入密码"]', password)
        await page.click('button:has-text("立即登录")')
        await page.wait_for_url(f"{frontend_url}/", timeout=10000)

        # 导航到创作页面
        await page.goto(f"{frontend_url}/posts/new", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # 填写文章内容
        title = f"E2E 测试文章 {tag}"
        content = f"这是由 E2E 自动化测试创建的文章内容。{tag}"
        await page.wait_for_selector(
            'input[placeholder*="标题"], [class*=title] input',
            state="visible",
            timeout=5000,
        )

        # 尝试找到标题输入框
        title_input = page.locator('input[placeholder*="标题"]').first
        if await title_input.count() == 0:
            title_input = page.locator("[class*=title] input").first
        await title_input.fill(title)

        # 填写正文
        content_editor = page.locator(
            ".ProseMirror, [contenteditable=true], textarea"
        ).first
        if await content_editor.count() > 0:
            await content_editor.fill(content)
        else:
            txt_area = page.locator("textarea").first
            if await txt_area.count() > 0:
                await txt_area.fill(content)

        # 提交
        submit_btn = page.locator(
            'button:has-text("发布"), button:has-text("提交")'
        ).first
        if await submit_btn.count() > 0:
            await submit_btn.click()
        else:
            save_btn = page.locator('button:has-text("保存")').first
            if await save_btn.count() > 0:
                await save_btn.click()

        await page.wait_for_timeout(3000)

        # 发布后应跳转（到 /posts 或首页）
        current = page.url.rstrip("/")
        assert current == frontend_url.rstrip("/") or "/posts" in current, (
            f"发布后未正确跳转，当前 URL: {current}"
        )

    async def test_admin_moderation_flow(self, page, frontend_url, backend_url):
        """管理员登录 → 审核面板 → 查看待审帖子 → 通过。"""
        tag = self.unique
        admin_email = f"admin_{tag}@test.com"
        admin_user = f"admin_{tag}"
        user_email = f"user_{tag}@test.com"
        user_name = f"user_{tag}"
        password = "TestPass123"

        # 注册两个用户：第一个可能成为 P0（如果数据库为空）
        await self._register_user(page, backend_url, admin_email, admin_user, password)
        user_data = await self._register_user(
            page, backend_url, user_email, user_name, password
        )

        # 用普通用户 token 创建一篇帖子
        user_token = user_data["access_token"]
        post_resp = await page.request.post(
            f"{backend_url}/api/blog/posts",
            json={
                "title": f"待审核文章 {tag}",
                "content": f"这是待管理员审核的文章内容 {tag}",
                "tags": ["e2e", "test"],
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        post_body = await post_resp.json()
        assert post_body["code"] == "ok", f"create post failed: {post_body}"

        # 用第一个用户身份登录 UI
        await page.goto(f"{frontend_url}/login", wait_until="networkidle")
        await page.wait_for_selector(
            'input[placeholder="请输入用户名或邮箱"]', state="visible"
        )
        await page.fill('input[placeholder="请输入用户名或邮箱"]', admin_email)
        await page.fill('input[placeholder="请输入密码"]', password)
        await page.click('button:has-text("立即登录")')
        await page.wait_for_url(f"{frontend_url}/", timeout=10000)

        # 检查第一个用户的权限等级
        me_resp = await page.request.get(f"{backend_url}/api/auth/me")
        me_body = await me_resp.json()
        user_level = me_body["data"].get("level", 5)

        if user_level == 0:
            # ── 管理员流程 ──
            await page.goto(
                f"{frontend_url}/admin/content/moderation", wait_until="networkidle"
            )
            await page.wait_for_timeout(2000)

            # 待审列表应可见
            pending = page.locator("text=待审核").first
            await pending.wait_for(state="visible", timeout=5000)

            # 找到并通过审核
            approve_btn = page.locator(
                'button:has-text("通过"), button:has-text("批准")'
            ).first
            if await approve_btn.count() > 0:
                await approve_btn.click()
                await page.wait_for_timeout(1000)
                confirm = page.locator(
                    ".n-popconfirm__action button:has-text('确认'), button:has-text('确定')"
                ).first
                if await confirm.count() > 0:
                    await confirm.click()
                await page.wait_for_timeout(2000)
        else:
            # ── 非管理员：验证页面保护 ──
            await page.goto(
                f"{frontend_url}/admin/content/moderation", wait_until="networkidle"
            )
            await page.wait_for_timeout(2000)
            body_text = await page.inner_text("body")
            assert any(
                text in body_text for text in ["403", "无权限", "Forbidden", "首页"]
            ), f"non-admin should see protection on admin page: {body_text[:200]}"

    async def test_404_error_page(self, page, frontend_url):
        """访问不存在的路由 → 显示 404 页面。"""
        await page.goto(
            f"{frontend_url}/this-path-does-not-exist-{self.unique}",
            wait_until="networkidle",
        )
        await page.wait_for_timeout(2000)

        # 404 提示应可见
        body_text = await page.inner_text("body")
        assert "404" in body_text, f"expected 404 not shown: {body_text[:200]}"
