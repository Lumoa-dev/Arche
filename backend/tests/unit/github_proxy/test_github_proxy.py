"""GitHub 代理插件 行为测试。

测试原则：
- 不关注内部实现细节
- 只验证公开方法的输入输出行为
- 用 mock 隔离外部依赖（网络、子进程）
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.core.middleware import AppError
from backend.plugins.github_proxy.services import (
    GhCliService,
    GitHubProxyError,
    GitHubService,
    HttpProxyService,
)

# =============================================================================
# GhCliService 行为测试
# =============================================================================


class TestGhCliService:
    """测试 GitHub CLI 服务的行为。"""

    @pytest.mark.asyncio
    async def test_proxy_get_returns_parsed_json(self, fake_container):
        """GET 请求应返回解析后的 JSON 数据和状态码。"""
        service = GhCliService(fake_container)

        mock_response = json.dumps({"login": "testuser", "id": 123}).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ):
            result = await service.proxy_request(
                method="GET",
                path="/user",
                query_params={},
                headers={},
                body=None,
            )

            assert result["status_code"] == 200
            assert result["data"]["login"] == "testuser"
            assert result["data"]["id"] == 123
            assert result["cached"] is True  # GET 请求应被缓存

    @pytest.mark.asyncio
    async def test_proxy_post_sends_body(self, fake_container):
        """POST 请求应把请求体传给 gh 命令。"""
        service = GhCliService(fake_container)

        mock_response = json.dumps({"id": 1, "name": "test-repo"}).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ) as mock_exec:
            body = json.dumps({"name": "test-repo"}).encode()
            result = await service.proxy_request(
                method="POST",
                path="/user/repos",
                query_params={},
                headers={},
                body=body,
            )

            assert result["status_code"] == 200
            # 验证 gh 命令被正确调用
            mock_exec.assert_called_once()
            call_args = mock_exec.call_args[0]
            assert "POST" in call_args  # 方法正确
            assert "user/repos" in call_args  # 路径正确（前面的斜杠被去掉了）

    @pytest.mark.asyncio
    async def test_cli_not_installed_raises_error(self, fake_container):
        """gh 未安装时应抛出清晰的错误。"""
        service = GhCliService(fake_container)

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("gh: not found"),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_request("GET", "/user", {}, {}, None, "test")

            assert "未找到 gh 命令" in str(excinfo.value)
            assert excinfo.value.code == "gh_not_installed"

    @pytest.mark.asyncio
    async def test_cli_timeout_raises_error(self, fake_container):
        """命令超时应抛出清晰的错误。"""
        service = GhCliService(fake_container)

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=TimeoutError("timeout"),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_request("GET", "/user", {}, {}, None, "test")

            assert "超时" in str(excinfo.value)


# =============================================================================
# GhCliService 静态资源代理测试
# =============================================================================


class TestGhCliServiceRawContent:
    """测试 GhCliService 静态资源代理行为。"""

    @pytest.mark.asyncio
    async def test_proxy_raw_returns_decoded_content(self, fake_container):
        """raw 内容代理应返回 base64 解码后的二进制内容。"""
        service = GhCliService(fake_container)

        # 模拟 GitHub API 返回 base64 编码的内容
        import base64

        test_content = b"# Test README\nThis is a test file."
        encoded_content = base64.b64encode(test_content).decode()

        mock_response = json.dumps(
            {"encoding": "base64", "content": encoded_content, "type": "text/plain"}
        ).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ) as mock_exec:
            result = await service.proxy_raw_content(
                path="owner/repo/main/README.md",
            )

            assert result["status_code"] == 200
            assert result["data"] == test_content
            assert result["headers"]["Content-Type"] == "text/plain"
            assert result["cached"] is True

            # 验证 gh 命令被正确调用，路径已转换
            mock_exec.assert_called_once()
            call_args = mock_exec.call_args[0]
            assert "GET" in call_args
            assert "repos/owner/repo/contents/README.md" in call_args
            assert "-f" in call_args
            assert "ref=main" in call_args

    @pytest.mark.asyncio
    async def test_proxy_raw_invalid_path_raises_error(self, fake_container):
        """无效的 raw 路径格式应抛出 400 错误。"""
        service = GhCliService(fake_container)

        # 路径少于3部分（owner/repo/branch）
        with pytest.raises(GitHubProxyError) as excinfo:
            await service.proxy_raw_content(
                path="owner/repo",  # 缺少 branch 和文件路径
            )

        assert "无效的 raw 路径格式" in str(excinfo.value)
        assert excinfo.value.code == "invalid_raw_path"
        assert excinfo.value.status_code == 400

    @pytest.mark.asyncio
    async def test_proxy_raw_caching_behavior(self, fake_container):
        """相同的 raw 请求第二次应命中缓存。"""
        service = GhCliService(fake_container)

        import base64

        test_content = b"cached content"
        encoded_content = base64.b64encode(test_content).decode()

        mock_response = json.dumps(
            {"encoding": "base64", "content": encoded_content, "type": "text/plain"}
        ).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ) as mock_exec:
            # 第一次调用，未命中缓存
            result1 = await service.proxy_raw_content(
                path="owner/repo/main/file.txt",
            )
            assert result1["cached"] is True
            assert mock_exec.call_count == 1

            # 第二次调用，命中缓存
            result2 = await service.proxy_raw_content(
                path="owner/repo/main/file.txt",
            )
            assert result2["cached"] is True
            assert mock_exec.call_count == 1  # 没有再次调用 subprocess
            assert result2["data"] == test_content

    @pytest.mark.asyncio
    async def test_proxy_raw_non_base64_content(self, fake_container):
        """非 base64 编码的内容应直接返回。"""
        service = GhCliService(fake_container)

        # 模拟返回非 base64 编码的内容（比如目录）
        mock_response = json.dumps({"type": "dir", "entries": []}).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ):
            result = await service.proxy_raw_content(
                path="owner/repo/main/src",
            )

            assert result["status_code"] == 200
            assert isinstance(result["data"], dict)
            assert result["data"]["type"] == "dir"


# =============================================================================
# HttpProxyService 行为测试
# =============================================================================


class TestHttpProxyService:
    """测试 HTTP 代理服务的行为。"""

    @pytest.mark.asyncio
    async def test_get_request_returns_json(self, fake_container):
        """GET 请求应返回 JSON 数据。"""
        service = HttpProxyService(fake_container)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser"}
        mock_response.headers = {"Content-Type": "application/json"}

        with patch.object(
            service._client,
            "request",
            return_value=mock_response,
        ):
            result = await service.proxy_request(
                method="GET",
                path="/user",
                query_params={},
                headers={},
                body=None,
            )

            assert result["status_code"] == 200
            assert result["data"]["login"] == "testuser"
            assert result["cached"] is True

    @pytest.mark.asyncio
    async def test_connect_error_raises_proxy_error(self, fake_container):
        """连接失败应抛出 GitHubProxyError。"""
        import httpx

        service = HttpProxyService(fake_container)

        with patch.object(
            service._client,
            "request",
            side_effect=httpx.ConnectError("connection failed"),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_request("GET", "/user", {}, {}, None, "test")

            assert "无法连接 GitHub" in str(excinfo.value)
            assert excinfo.value.code == "github_connect_error"


# =============================================================================
# HttpProxyService 静态资源代理测试
# =============================================================================


class TestHttpProxyServiceRawContent:
    """测试 HttpProxyService 静态资源代理行为。"""

    @pytest.mark.asyncio
    async def test_proxy_raw_returns_binary_content(self, fake_container):
        """raw 内容代理应返回二进制内容。"""
        service = HttpProxyService(fake_container)

        test_content = b"# Test README\nThis is a test file."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = test_content
        mock_response.headers = {
            "Content-Type": "text/plain",
            "Cache-Control": "max-age=3600",
        }

        with patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ) as mock_get:
            result = await service.proxy_raw_content(
                path="owner/repo/main/README.md",
            )

            assert result["status_code"] == 200
            assert result["data"] == test_content
            assert result["headers"]["Content-Type"] == "text/plain"
            assert result["cached"] is False  # 第一次请求未命中缓存

            # 验证请求 URL 正确
            mock_get.assert_called_once()
            call_args = mock_get.call_args[0][0]
            assert "raw.githubusercontent.com/owner/repo/main/README.md" in call_args

    @pytest.mark.asyncio
    async def test_proxy_raw_caching_behavior(self, fake_container):
        """相同的 raw 请求第二次应命中缓存。"""
        service = HttpProxyService(fake_container)

        test_content = b"cached content"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = test_content
        mock_response.headers = {
            "Content-Type": "text/plain",
            "Cache-Control": "max-age=3600",
        }

        with patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ) as mock_get:
            # 第一次调用，未命中缓存
            result1 = await service.proxy_raw_content(
                path="owner/repo/main/file.txt",
            )
            assert result1["cached"] is False
            assert mock_get.call_count == 1

            # 第二次调用，命中缓存
            result2 = await service.proxy_raw_content(
                path="owner/repo/main/file.txt",
            )
            assert result2["cached"] is True
            assert mock_get.call_count == 1  # 没有再次发送 HTTP 请求
            assert result2["data"] == test_content

    @pytest.mark.asyncio
    async def test_proxy_raw_timeout_raises_error(self, fake_container):
        """静态资源请求超时应抛出 504 错误。"""
        service = HttpProxyService(fake_container)
        import httpx

        with patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_raw_content(
                    path="owner/repo/main/large-file.bin",
                )

            assert "超时" in str(excinfo.value)
            assert excinfo.value.code == "github_timeout"
            assert excinfo.value.status_code == 504

    @pytest.mark.asyncio
    async def test_proxy_raw_connect_error_raises_error(self, fake_container):
        """连接失败应抛出 502 错误。"""
        service = HttpProxyService(fake_container)
        import httpx

        with patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.ConnectError("connection failed"),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_raw_content(
                    path="owner/repo/main/file.txt",
                )

            assert "无法连接 GitHub" in str(excinfo.value)
            assert excinfo.value.code == "github_connect_error"
            assert excinfo.value.status_code == 502

    def test_parse_cache_ttl(self, fake_container):
        """测试 Cache-Control 头部解析逻辑。"""
        service = HttpProxyService(fake_container)

        # 正常 max-age
        assert service._parse_cache_ttl("max-age=3600") == 3600
        assert service._parse_cache_ttl("public, max-age=1800") == 1800

        # 包含 no-cache 或 no-store
        assert service._parse_cache_ttl("no-cache") == 0
        assert service._parse_cache_ttl("max-age=3600, no-store") == 0
        assert service._parse_cache_ttl("private, max-age=0") == 0

        # 无效格式
        assert service._parse_cache_ttl("") is None
        assert service._parse_cache_ttl("invalid") is None
        assert service._parse_cache_ttl("max-age=abc") is None

        # 负的 max-age
        assert service._parse_cache_ttl("max-age=-100") is None


# =============================================================================
# GitHubService 自动降级 行为测试
# =============================================================================


class TestGitHubServiceAutoFallback:
    """测试统一门面的自动降级行为。"""

    @pytest.mark.asyncio
    async def test_http_success_no_fallback(self, fake_container):
        """HTTP 成功时，不降级，使用 HTTP 模式。"""
        service = GitHubService(fake_container)

        # Mock HTTP 成功
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"from": "http"}
        mock_response.headers = {}

        with patch.object(
            service.http_service._client, "request", return_value=mock_response
        ):
            result = await service.proxy_request(
                method="GET",
                path="/user",
                query_params={},
                headers={},
                body=None,
                user_id="test",
                mode="auto",
            )

            assert result["mode"] == "http"
            assert "fallback_from" not in result
            assert result["data"]["from"] == "http"

    @pytest.mark.asyncio
    async def test_http_failure_fallbacks_to_cli(self, fake_container):
        """HTTP 失败时，自动降级到 CLI 模式。"""
        service = GitHubService(fake_container)

        # Mock HTTP 失败
        import httpx

        with patch.object(
            service.http_service._client,
            "request",
            side_effect=httpx.ConnectError("failed"),
        ):
            # Mock CLI 成功
            mock_response = json.dumps({"from": "cli"}).encode()
            with patch(
                "asyncio.create_subprocess_exec",
                return_value=mock_subprocess_success(mock_response),
            ):
                result = await service.proxy_request(
                    method="GET",
                    path="/user",
                    query_params={},
                    headers={},
                    body=None,
                    user_id="test",
                    mode="auto",
                )

                assert result["mode"] == "cli"
                assert result["fallback_from"] == "http"
                assert result["data"]["from"] == "cli"

    @pytest.mark.asyncio
    async def test_cli_mode_skips_http(self, fake_container):
        """mode=cli 时，直接用 CLI，不尝试 HTTP。"""
        service = GitHubService(fake_container)

        mock_response = json.dumps({"from": "cli"}).encode()
        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ) as mock_exec:
            result = await service.proxy_request(
                method="GET",
                path="/user",
                query_params={},
                headers={},
                body=None,
                user_id="test",
                mode="cli",
            )

            assert result["mode"] == "cli"
            # HTTP 客户端不应被调用
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_both_fail_raises_original_error(self, fake_container):
        """HTTP 和 CLI 都失败时，抛出原始错误。"""
        service = GitHubService(fake_container)

        import httpx

        with (
            patch.object(
                service.http_service._client,
                "request",
                side_effect=httpx.ConnectError("http failed"),
            ),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError("gh not found"),
            ),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_request(
                    method="GET",
                    path="/user",
                    mode="auto",
                )

            # 应该是 HTTP 的错误，因为是第一个失败的
            assert "http" in str(excinfo.value).lower()


# =============================================================================
# GitHubService 静态资源代理测试
# =============================================================================


class TestGitHubServiceRawContent:
    """测试 GitHubService 静态资源代理的自动降级行为。"""

    @pytest.mark.asyncio
    async def test_cli_mode_uses_cli_service(self, fake_container):
        """mode=cli 时，直接使用 CLI 服务。"""
        service = GitHubService(fake_container)

        # Mock CLI 服务返回结果
        mock_result = {
            "data": b"cli content",
            "status_code": 200,
            "headers": {"Content-Type": "text/plain"},
            "cached": False,
        }
        with (
            patch.object(
                service.cli_service,
                "proxy_raw_content",
                return_value=mock_result,
            ) as mock_cli,
            patch.object(
                service.http_service,
                "proxy_raw_content",
            ) as mock_http,
        ):
            result = await service.proxy_raw_content(
                path="owner/repo/main/file.txt",
                mode="cli",
            )

            assert result["mode"] == "cli"
            assert result["data"] == b"cli content"
            mock_cli.assert_called_once_with("owner/repo/main/file.txt")
            mock_http.assert_not_called()  # HTTP 服务不应被调用

    @pytest.mark.asyncio
    async def test_http_mode_uses_http_service(self, fake_container):
        """mode=http 时，直接使用 HTTP 服务。"""
        service = GitHubService(fake_container)

        # Mock HTTP 服务返回结果
        mock_result = {
            "data": b"http content",
            "status_code": 200,
            "headers": {"Content-Type": "text/plain"},
            "cached": False,
        }
        with (
            patch.object(
                service.http_service,
                "proxy_raw_content",
                return_value=mock_result,
            ) as mock_http,
            patch.object(
                service.cli_service,
                "proxy_raw_content",
            ) as mock_cli,
        ):
            result = await service.proxy_raw_content(
                path="owner/repo/main/file.txt",
                mode="http",
            )

            assert result["mode"] == "http"
            assert result["data"] == b"http content"
            mock_http.assert_called_once_with("owner/repo/main/file.txt")
            mock_cli.assert_not_called()  # CLI 服务不应被调用

    @pytest.mark.asyncio
    async def test_auto_mode_http_success_no_fallback(self, fake_container):
        """auto 模式下 HTTP 成功时，不降级。"""
        service = GitHubService(fake_container)

        # Mock HTTP 服务成功
        mock_http_result = {
            "data": b"http content",
            "status_code": 200,
            "headers": {},
            "cached": False,
        }
        with (
            patch.object(
                service.http_service,
                "proxy_raw_content",
                return_value=mock_http_result,
            ) as mock_http,
            patch.object(
                service.cli_service,
                "proxy_raw_content",
            ) as mock_cli,
        ):
            result = await service.proxy_raw_content(
                path="owner/repo/main/file.txt",
                mode="auto",
            )

            assert result["mode"] == "http"
            assert result["data"] == b"http content"
            mock_http.assert_called_once()
            mock_cli.assert_not_called()  # 不需要降级到 CLI

    @pytest.mark.asyncio
    async def test_auto_mode_http_failure_fallbacks_to_cli(self, fake_container):
        """auto 模式下 HTTP 失败时，自动降级到 CLI。"""
        service = GitHubService(fake_container)

        # Mock HTTP 服务失败
        with patch.object(
            service.http_service,
            "proxy_raw_content",
            side_effect=GitHubProxyError("http failed"),
        ):
            # Mock CLI 服务成功
            mock_cli_result = {
                "data": b"cli content",
                "status_code": 200,
                "headers": {},
                "cached": False,
            }
            with patch.object(
                service.cli_service,
                "proxy_raw_content",
                return_value=mock_cli_result,
            ) as mock_cli:
                result = await service.proxy_raw_content(
                    path="owner/repo/main/file.txt",
                    mode="auto",
                )

                assert result["mode"] == "cli"
                assert result["data"] == b"cli content"
                mock_cli.assert_called_once()


# =============================================================================
# 缓存 行为测试
# =============================================================================


class TestCachingBehavior:
    """测试缓存行为。"""

    @pytest.mark.asyncio
    async def test_get_requests_are_cached(self, fake_container):
        """相同的 GET 请求第二次应命中缓存。"""
        service = GhCliService(fake_container)

        mock_response = json.dumps({"value": "first"}).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ) as mock_exec:
            # 第一次调用
            result1 = await service.proxy_request("GET", "/user", {}, {}, None, "test")
            assert result1["cached"] is True  # 写入缓存了

            # 第二次调用
            result2 = await service.proxy_request("GET", "/user", {}, {}, None, "test")
            assert result2["cached"] is True  # 命中缓存

            # subprocess 应该只被调用了一次
            assert mock_exec.call_count == 1

    @pytest.mark.asyncio
    async def test_post_requests_are_not_cached(self, fake_container):
        """POST 请求不应该被缓存。"""
        service = GhCliService(fake_container)

        mock_response = json.dumps({"ok": True}).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ) as mock_exec:
            await service.proxy_request("POST", "/user/repos", {}, {}, b"{}", "test")
            await service.proxy_request("POST", "/user/repos", {}, {}, b"{}", "test")

            # POST 应该每次都调用 subprocess
            assert mock_exec.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_cache_removes_all_entries(self, fake_container):
        """clear_cache 应该清空所有缓存。"""
        service = GhCliService(fake_container)

        mock_response = json.dumps({"ok": True}).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ) as mock_exec:
            # 填充缓存
            await service.proxy_request("GET", "/user", {}, {}, None, "test")
            assert mock_exec.call_count == 1

            # 命中缓存
            await service.proxy_request("GET", "/user", {}, {}, None, "test")
            assert mock_exec.call_count == 1

            # 清空缓存
            service.clear_cache()

            # 应该重新请求
            await service.proxy_request("GET", "/user", {}, {}, None, "test")
            assert mock_exec.call_count == 2


# =============================================================================
# 限流逻辑测试
# =============================================================================


class TestRateLimiting:
    """测试请求限流逻辑。"""

    @pytest.mark.asyncio
    async def test_rate_limit_not_triggered_for_few_requests(self, fake_container):
        """少于最大请求数时不触发限流。"""
        service = GhCliService(fake_container)
        user_id = "test-user"

        mock_response = json.dumps({"ok": True}).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ):
            # 发送59个请求，不应触发限流
            for _i in range(59):
                result = await service.proxy_request(
                    "GET", "/user", {}, {}, None, user_id
                )
                assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_rate_limit_triggered_when_exceeded(self, fake_container):
        """超过最大请求数时触发429限流。"""
        service = GhCliService(fake_container)
        user_id = "test-user"

        mock_response = json.dumps({"ok": True}).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ):
            # 先发送60个请求，刚好达到上限
            for _i in range(60):
                result = await service.proxy_request(
                    "GET", "/user", {}, {}, None, user_id
                )
                assert result["status_code"] == 200

            # 第61个请求应该触发限流
            with pytest.raises(AppError) as excinfo:
                await service.proxy_request("GET", "/user", {}, {}, None, user_id)

            assert "请求过于频繁" in str(excinfo.value)
            assert excinfo.value.code == "rate_limit_exceeded"
            assert excinfo.value.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_window(self, fake_container):
        """时间窗口过后限流重置。"""
        service = GhCliService(fake_container)
        user_id = "test-user"

        mock_response = json.dumps({"ok": True}).encode()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ):
            # 先发送60个请求，达到上限
            for _i in range(60):
                await service.proxy_request("GET", "/user", {}, {}, None, user_id)

            # 第61个请求触发限流
            with pytest.raises(AppError):
                await service.proxy_request("GET", "/user", {}, {}, None, user_id)

            # 模拟时间过去61秒，超过限流窗口
            import time

            with patch("time.monotonic", return_value=time.monotonic() + 61):
                # 现在应该可以正常请求了
                result = await service.proxy_request(
                    "GET", "/user", {}, {}, None, user_id
                )
                assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_http_service_rate_limiting(self, fake_container):
        """HTTP 服务也应遵守相同的限流逻辑。"""
        service = HttpProxyService(fake_container)
        user_id = "test-user"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_response.headers = {}

        with patch.object(
            service._client,
            "request",
            return_value=mock_response,
        ):
            # 发送60个请求，达到上限
            for _i in range(60):
                result = await service.proxy_request(
                    "GET", "/user", {}, {}, None, user_id
                )
                assert result["status_code"] == 200

            # 第61个请求触发限流
            with pytest.raises(AppError) as excinfo:
                await service.proxy_request("GET", "/user", {}, {}, None, user_id)

            assert excinfo.value.code == "rate_limit_exceeded"


class TestGitHubServiceAdditionalMethods:
    """测试 GitHubService 的其他方法。"""

    def test_clear_cache_clears_both_services(self, fake_container):
        """clear_cache 应同时清空 HTTP 和 CLI 服务的缓存。"""
        service = GitHubService(fake_container)

        # Mock 两个服务的 clear_cache 方法
        with (
            patch.object(
                service.http_service,
                "clear_cache",
                return_value=10,
            ) as mock_http_clear,
            patch.object(
                service.cli_service,
                "clear_cache",
                return_value=5,
            ) as mock_cli_clear,
        ):
            result = service.clear_cache()

            assert result == {"http": 10, "cli": 5}
            mock_http_clear.assert_called_once()
            mock_cli_clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_closes_http_service(self, fake_container):
        """close 方法应关闭 HTTP 服务的客户端。"""
        service = GitHubService(fake_container)

        with patch.object(
            service.http_service,
            "close",
        ) as mock_http_close:
            await service.close()

            mock_http_close.assert_called_once()


# =============================================================================
# 错误处理分支测试
# =============================================================================


class TestGhCliServiceErrorHandling:
    """测试 GhCliService 的各种错误处理场景。"""

    @pytest.mark.asyncio
    async def test_gh_cli_error_404(self, fake_container):
        """gh 命令返回 404 错误时应抛出 404 状态码。"""
        service = GhCliService(fake_container)

        # Mock 命令返回非0状态码和404错误信息
        class MockProc:
            returncode = 1

            async def communicate(self, input=None):
                return b"", b"HTTP 404: Not Found"

            async def wait(self):
                return 1

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=MockProc(),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_request("GET", "/nonexistent", {}, {}, None, "test")

            assert excinfo.value.status_code == 404
            assert "404" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_gh_cli_error_401(self, fake_container):
        """gh 命令返回 401 错误时应抛出 401 状态码。"""
        service = GhCliService(fake_container)

        class MockProc:
            returncode = 1

            async def communicate(self, input=None):
                return b"", b"HTTP 401: Unauthorized"

            async def wait(self):
                return 1

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=MockProc(),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_request("GET", "/user", {}, {}, None, "test")

            assert excinfo.value.status_code == 401

    @pytest.mark.asyncio
    async def test_gh_cli_error_403(self, fake_container):
        """gh 命令返回 403 错误时应抛出 403 状态码。"""
        service = GhCliService(fake_container)

        class MockProc:
            returncode = 1

            async def communicate(self, input=None):
                return b"", b"HTTP 403: Forbidden"

            async def wait(self):
                return 1

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=MockProc(),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_request("GET", "/user", {}, {}, None, "test")

            assert excinfo.value.status_code == 403

    @pytest.mark.asyncio
    async def test_gh_cli_error_422(self, fake_container):
        """gh 命令返回 422 错误时应抛出 422 状态码。"""
        service = GhCliService(fake_container)

        class MockProc:
            returncode = 1

            async def communicate(self, input=None):
                return b"", b"HTTP 422: Unprocessable Entity"

            async def wait(self):
                return 1

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=MockProc(),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_request("GET", "/user", {}, {}, None, "test")

            assert excinfo.value.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, fake_container):
        """无效的 JSON 响应应被正确处理，返回 raw 字段。"""
        service = GhCliService(fake_container)

        # Mock 返回非 JSON 格式的响应
        mock_response = b"this is not json"

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_subprocess_success(mock_response),
        ):
            result = await service.proxy_request("GET", "/user", {}, {}, None, "test")

            assert result["status_code"] == 200
            assert result["data"]["raw"] == "this is not json"  # 被包装到 raw 字段

    @pytest.mark.asyncio
    async def test_timeout_kills_process(self, fake_container):
        """命令超时时应杀死进程。"""
        service = GhCliService(fake_container)

        class MockProc:
            returncode = None  # 进程还在运行
            killed = False

            async def communicate(self, input=None):
                raise asyncio.TimeoutError("timeout")

            def kill(self):
                self.killed = True

            async def wait(self):
                self.returncode = -9

        mock_proc = MockProc()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            with pytest.raises(GitHubProxyError, match="超时"):
                await service.proxy_request("GET", "/user", {}, {}, None, "test")

            # 验证进程被杀死
            assert mock_proc.killed is True


class TestHttpProxyServiceErrorHandling:
    """测试 HttpProxyService 的错误处理场景。"""

    @pytest.mark.asyncio
    async def test_http_timeout(self, fake_container):
        """HTTP 请求超时应抛出 504 错误。"""
        service = HttpProxyService(fake_container)
        import httpx

        with patch.object(
            service._client,
            "request",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            with pytest.raises(GitHubProxyError) as excinfo:
                await service.proxy_request("GET", "/user", {}, {}, None, "test")

            assert excinfo.value.code == "github_timeout"
            assert excinfo.value.status_code == 504

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, fake_container):
        """无效的 JSON 响应应被正确处理。"""
        service = HttpProxyService(fake_container)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("invalid json", "", 0)
        mock_response.text = "this is not json"
        mock_response.headers = {"Content-Type": "text/plain"}

        with patch.object(
            service._client,
            "request",
            return_value=mock_response,
        ):
            result = await service.proxy_request("GET", "/user", {}, {}, None, "test")

            assert result["status_code"] == 200
            assert result["data"] == {
                "raw": "this is not json"
            }  # 无效JSON被包装到raw字段中


# =============================================================================
# 辅助函数
# =============================================================================


def mock_subprocess_success(stdout: bytes = b'{"ok": true}', stderr: bytes = b""):
    """创建成功的 subprocess mock。"""

    class MockProc:
        returncode = 0

        async def communicate(self, input=None):
            return stdout, stderr

        async def wait(self):
            return 0

    return MockProc()
