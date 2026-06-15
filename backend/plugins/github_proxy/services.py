"""GitHub Proxy Service — HTTP 代理 + CLI 双模式，支持自动降级。"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import httpx

from backend.core.middleware import AppError

if TYPE_CHECKING:
    from backend.core.container import ServiceContainer


class GitHubProxyError(AppError):
    def __init__(
        self,
        message: str = "GitHub 代理请求失败",
        code: str = "github_proxy_error",
        status_code: int = 502,
    ):
        super().__init__(message, code, status_code)


# === 限流常量 ===
RATE_LIMIT_WINDOW = 60  # 秒
RATE_LIMIT_MAX_REQUESTS = 60  # 每分钟最大请求数


class CacheEntry:
    """简单的内存缓存条目。"""

    def __init__(
        self, data: Any, status_code: int, headers: dict[str, str], ttl: int = 300
    ):
        self.data = data
        self.status_code = status_code
        self.headers = headers
        self.expires_at = time.monotonic() + ttl

    @property
    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


# =============================================================================
# GhCliService - 通过 GitHub CLI (gh) 调用 API
# =============================================================================


class GhCliService:
    """
    GitHub CLI 代理服务，通过 subprocess 调用 `gh api` 命令。

    优势：
    - gh 命令有自己的连接机制，在国内环境下可能绕过网络限制
    - 自动处理认证、分页、重试
    - 完整支持所有 GitHub API
    """

    def __init__(self, container: ServiceContainer):
        self.container = container
        config = container.get("config")
        self.github_token = config.get_required("GITHUB_TOKEN")
        self.default_ttl = config.get("GITHUB_CACHE_TTL", 300)
        self.timeout = config.get("GITHUB_TIMEOUT", 30)
        self.default_mode = config.get("GITHUB_DEFAULT_MODE", "auto")

        self._cache: dict[str, CacheEntry] = {}
        # 限流追踪：{user_id: [timestamp, ...]}
        self._rate_tracker: dict[str, list[float]] = defaultdict(list)

    def _check_rate_limit(self, user_id: str) -> None:
        """检查用户是否在限流窗口内超出请求数。"""
        now = time.monotonic()
        timestamps = self._rate_tracker[user_id]

        # 清理过期时间戳
        cutoff = now - RATE_LIMIT_WINDOW
        self._rate_tracker[user_id] = [t for t in timestamps if t > cutoff]
        timestamps = self._rate_tracker[user_id]

        if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
            raise AppError(
                f"请求过于频繁，请等待 {RATE_LIMIT_WINDOW} 秒后重试",
                code="rate_limit_exceeded",
                status_code=429,
            )

        timestamps.append(now)

    def _cache_key(self, method: str, path: str, params: dict) -> str:
        raw = f"{method}:{path}:{sorted(params.items())}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> CacheEntry | None:
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            return entry
        if entry:
            del self._cache[key]
        return None

    def _set_cache(
        self,
        key: str,
        data: Any,
        status_code: int,
        headers: dict[str, str],
        ttl: int | None = None,
    ) -> None:
        if ttl is None:
            ttl = self.default_ttl if self.default_ttl is not None else 300
        if isinstance(ttl, int) and ttl > 0:
            self._cache[key] = CacheEntry(data, status_code, headers, ttl)

    async def _run_gh_command(
        self,
        method: str,
        path: str,
        query_params: dict | None = None,
        body: dict | None = None,
    ) -> dict:
        """
        执行 gh api 命令。

        参考: gh api <endpoint> [flags]
        -X, --method: HTTP 方法
        -f, --field: 添加参数 (key=value)
        -i, --include: 包含响应头
        -q, --jq: JQ 表达式过滤
        --input: 从文件读取输入
        """
        # 构建 gh 命令参数
        cmd = ["gh", "api", "-X", method.upper()]

        # 添加查询参数
        if query_params:
            for k, v in query_params.items():
                cmd.extend(["-f", f"{k}={v}"])

        # 添加请求体 (JSON)
        stdin_data = None
        if body and method.upper() in ("POST", "PUT", "PATCH"):
            stdin_data = json.dumps(body).encode("utf-8")
            cmd.extend(["--input", "-"])  # 从 stdin 读取

        # API 路径
        cmd.append(path.lstrip("/"))

        # 执行命令
        env = {}
        if self.github_token:
            env["GH_TOKEN"] = self.github_token

        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if stdin_data else None,
                env=env if env else None,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_data),
                timeout=self.timeout,
            )

            if proc.returncode != 0:
                # 解析错误信息
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                # 尝试从错误中提取状态码
                status_code = 500
                if "404" in error_msg:
                    status_code = 404
                elif "401" in error_msg:
                    status_code = 401
                elif "403" in error_msg:
                    status_code = 403
                elif "422" in error_msg:
                    status_code = 422

                raise GitHubProxyError(
                    f"gh 命令失败: {error_msg}",
                    code="gh_cli_error",
                    status_code=status_code,
                )

            # 解析响应
            output = stdout.decode("utf-8", errors="replace")
            try:
                data = json.loads(output) if output.strip() else {}
            except json.JSONDecodeError:
                data = {"raw": output}

            return {
                "data": data,
                "status_code": 200,
                "headers": {"Content-Type": "application/json"},
                "cached": False,
            }

        except asyncio.TimeoutError:
            if proc is not None and proc.returncode is None:
                proc.kill()
                await proc.wait()
            raise GitHubProxyError(  # noqa: B904
                "gh 命令执行超时", code="gh_timeout", status_code=504
            )
        except FileNotFoundError:
            raise GitHubProxyError(  # noqa: B904
                "未找到 gh 命令，请先安装 GitHub CLI: https://cli.github.com/",
                code="gh_not_installed",
                status_code=500,
            )
        except GitHubProxyError:
            # 已经是 GitHubProxyError，直接抛出，不重新包装
            raise
        except Exception as e:
            raise GitHubProxyError(  # noqa: B904
                f"gh 命令执行失败: {e!s}", code="gh_error", status_code=500
            )

    async def proxy_request(
        self,
        method: str,
        path: str,
        query_params: dict | None = None,
        headers: dict | None = None,  # noqa: ARG002
        body: bytes | None = None,
        user_id: str | None = None,
    ) -> dict:
        """通过 gh 命令代理请求到 GitHub API。"""
        # 限流检查
        if user_id:
            self._check_rate_limit(user_id)

        query_params = query_params or {}
        cache_key = self._cache_key(method, path, query_params)

        # GET 请求查缓存
        if method.upper() == "GET":
            cached = self._get_cached(cache_key)
            if cached:
                return {
                    "data": cached.data,
                    "status_code": cached.status_code,
                    "headers": cached.headers,
                    "cached": True,
                }

        # 解析 body (bytes -> dict)
        body_dict = None
        if body and body.strip():
            with contextlib.suppress(json.JSONDecodeError, UnicodeDecodeError):
                body_dict = json.loads(body.decode("utf-8"))

        result = await self._run_gh_command(
            method=method,
            path=path,
            query_params=query_params,
            body=body_dict,
        )

        # 缓存 GET 请求
        if method.upper() == "GET" and 200 <= result["status_code"] < 300:
            self._set_cache(
                cache_key,
                result["data"],
                result["status_code"],
                result["headers"],
            )
            result["cached"] = True

        return result

    async def proxy_raw_content(self, path: str) -> dict:
        """代理 GitHub 静态资源（通过 gh api 获取内容）。"""
        cache_key = self._cache_key("GET", f"raw:{path}", {})
        cached = self._get_cached(cache_key)
        if cached:
            return {
                "data": cached.data,
                "status_code": cached.status_code,
                "headers": cached.headers,
                "cached": True,
            }

        # raw.githubusercontent.com 路径转换为 API 路径
        # owner/repo/branch/path -> /repos/owner/repo/contents/path?ref=branch
        parts = path.lstrip("/").split("/")
        if len(parts) >= 3:
            owner = parts[0]
            repo = parts[1]
            ref = parts[2]
            file_path = "/".join(parts[3:])

            result = await self._run_gh_command(
                method="GET",
                path=f"/repos/{owner}/{repo}/contents/{file_path}",
                query_params={"ref": ref},
            )

            # GitHub API 返回的是 base64 编码内容，需要解码
            data = result["data"]
            if isinstance(data, dict) and data.get("encoding") == "base64":
                import base64

                content = base64.b64decode(data.get("content", ""))
                result["data"] = content
                result["headers"]["Content-Type"] = data.get(
                    "type", "application/octet-stream"
                )

            if 200 <= result["status_code"] < 300:
                self._set_cache(
                    cache_key,
                    result["data"],
                    result["status_code"],
                    result["headers"],
                )
                result["cached"] = True

            return result

        raise GitHubProxyError(
            "无效的 raw 路径格式", code="invalid_raw_path", status_code=400
        )

    def clear_cache(self) -> int:
        """清空所有缓存，返回清空的条目数。"""
        count = len(self._cache)
        self._cache.clear()
        return count


# =============================================================================
# GitHubProxyService - 原 HTTP 代理模式（保留）
# =============================================================================


class HttpProxyService:
    """GitHub API HTTP 反向代理服务：转发请求、缓存响应、注入 Token、限流。"""

    def __init__(self, container: ServiceContainer):
        self.container = container
        config = container.get("config")
        self.github_token = config.get_required("GITHUB_TOKEN")
        self.base_url = config.get("GITHUB_API_BASE", "https://api.github.com")
        self.raw_base_url = config.get(
            "GITHUB_RAW_BASE", "https://raw.githubusercontent.com"
        )
        self.default_ttl = config.get("GITHUB_CACHE_TTL", 300)
        self.timeout = config.get("GITHUB_TIMEOUT", 30)

        self._cache: dict[str, CacheEntry] = {}
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=True,
        )

        # 限流追踪：{user_id: [timestamp, ...]}
        self._rate_tracker: dict[str, list[float]] = defaultdict(list)

    def _check_rate_limit(self, user_id: str) -> None:
        now = time.monotonic()
        timestamps = self._rate_tracker[user_id]
        cutoff = now - RATE_LIMIT_WINDOW
        self._rate_tracker[user_id] = [t for t in timestamps if t > cutoff]
        timestamps = self._rate_tracker[user_id]

        if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
            raise AppError(
                f"请求过于频繁，请等待 {RATE_LIMIT_WINDOW} 秒后重试",
                code="rate_limit_exceeded",
                status_code=429,
            )

        timestamps.append(now)

    async def close(self) -> None:
        await self._client.aclose()

    def _cache_key(self, method: str, path: str, params: dict) -> str:
        raw = f"{method}:{path}:{sorted(params.items())}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> CacheEntry | None:
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            return entry
        if entry:
            del self._cache[key]
        return None

    def _set_cache(
        self,
        key: str,
        data: Any,
        status_code: int,
        headers: dict[str, str],
        ttl: int | None = None,
    ) -> None:
        if ttl is None:
            ttl = self.default_ttl if self.default_ttl is not None else 300
        if isinstance(ttl, int) and ttl > 0:
            self._cache[key] = CacheEntry(data, status_code, headers, ttl)

    def _build_headers(
        self, extra_headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Veil-GitHub-Proxy/0.1.0",
        }
        if extra_headers:
            skip = {"authorization", "host", "connection", "content-length"}
            for k, v in extra_headers.items():
                if k.lower() not in skip:
                    headers[k] = v
        return headers

    async def proxy_request(
        self,
        method: str,
        path: str,
        query_params: dict | None = None,
        headers: dict | None = None,
        body: bytes | None = None,
        user_id: str | None = None,
    ) -> dict:
        if user_id:
            self._check_rate_limit(user_id)

        query_params = query_params or {}
        cache_key = self._cache_key(method, path, query_params)

        if method.upper() == "GET":
            cached = self._get_cached(cache_key)
            if cached:
                return {
                    "data": cached.data,
                    "status_code": cached.status_code,
                    "headers": cached.headers,
                    "cached": True,
                }

        proxied_headers = self._build_headers(headers)

        try:
            response = await self._client.request(
                method=method.upper(),
                url=f"/{path.lstrip('/')}",
                params=query_params,
                headers=proxied_headers,
                content=body,
            )
        except httpx.TimeoutException:
            raise GitHubProxyError(  # noqa: B904
                "GitHub API 请求超时", code="github_timeout", status_code=504
            )
        except httpx.ConnectError:
            raise GitHubProxyError(  # noqa: B904
                "无法连接 GitHub", code="github_connect_error", status_code=502
            )

        status_code = response.status_code

        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text}

        resp_headers = dict(response.headers)

        if method.upper() == "GET" and 200 <= status_code < 300:
            cache_control = resp_headers.get("Cache-Control", "")
            ttl = self._parse_cache_ttl(cache_control)
            self._set_cache(cache_key, data, status_code, resp_headers, ttl)

        return {
            "data": data,
            "status_code": status_code,
            "headers": resp_headers,
            "cached": method.upper() == "GET"
            and self._get_cached(cache_key) is not None,
        }

    async def proxy_raw_content(self, path: str) -> dict:
        cache_key = self._cache_key("GET", f"raw:{path}", {})
        cached = self._get_cached(cache_key)
        if cached:
            return {
                "data": cached.data,
                "status_code": cached.status_code,
                "headers": cached.headers,
                "cached": True,
            }

        async with httpx.AsyncClient(
            timeout=self.timeout, follow_redirects=True
        ) as client:
            try:
                response = await client.get(f"{self.raw_base_url}/{path.lstrip('/')}")
            except httpx.TimeoutException:
                raise GitHubProxyError(  # noqa: B904
                    "GitHub 静态资源请求超时", code="github_timeout", status_code=504
                )
            except httpx.ConnectError:
                raise GitHubProxyError(  # noqa: B904
                    "无法连接 GitHub", code="github_connect_error", status_code=502
                )

            status_code = response.status_code
            content = response.content
            resp_headers = dict(response.headers)

            if 200 <= status_code < 300:
                ttl = self._parse_cache_ttl(resp_headers.get("Cache-Control", ""))
                self._set_cache(cache_key, content, status_code, resp_headers, ttl)

            return {
                "data": content,
                "status_code": status_code,
                "headers": resp_headers,
                "cached": False,
            }

    def _parse_cache_ttl(self, cache_control: str) -> int | None:
        if not cache_control:
            return None
        max_age = None
        for part in cache_control.split(","):
            part = part.strip()
            if part == "no-cache" or part == "no-store" or part == "max-age=0":
                return 0
            if part.startswith("max-age="):
                try:
                    age = int(part.split("=", 1)[1])
                    if age >= 0:
                        max_age = age
                except ValueError:
                    pass
        return max_age

    def clear_cache(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count


# =============================================================================
# GitHubService - 统一门面，自动降级
# =============================================================================


class GitHubService:
    """
    GitHub 统一服务门面，支持 HTTP 代理和 CLI 双模式，自动降级。

    模式选择：
    - auto: 优先 HTTP，失败自动降级到 CLI（默认）
    - http: 仅使用 HTTP 代理
    - cli: 仅使用 CLI
    """

    def __init__(self, container: ServiceContainer):
        self.container = container
        config = container.get("config")
        self.default_mode = config.get("GITHUB_DEFAULT_MODE", "auto")
        self.http_service = HttpProxyService(container)
        self.cli_service = GhCliService(container)

    async def proxy_request(
        self,
        method: str,
        path: str,
        query_params: dict | None = None,
        headers: dict | None = None,
        body: bytes | None = None,
        user_id: str | None = None,
        mode: str = "auto",  # auto | http | cli
    ) -> dict:
        """
        代理 GitHub API 请求，支持模式选择和自动降级。
        """
        if mode == "cli":
            result = await self.cli_service.proxy_request(
                method=method,
                path=path,
                query_params=query_params,
                headers=headers,
                body=body,
                user_id=user_id,
            )
            result["mode"] = "cli"
            return result

        if mode == "http":
            result = await self.http_service.proxy_request(
                method=method,
                path=path,
                query_params=query_params,
                headers=headers,
                body=body,
                user_id=user_id,
            )
            result["mode"] = "http"
            return result

        # auto 模式：先试 HTTP，失败降级 CLI
        try:
            result = await self.http_service.proxy_request(
                method=method,
                path=path,
                query_params=query_params,
                headers=headers,
                body=body,
                user_id=user_id,
            )
            result["mode"] = "http"
            return result
        except GitHubProxyError as e:
            # HTTP 失败，降级到 CLI
            try:
                result = await self.cli_service.proxy_request(
                    method=method,
                    path=path,
                    query_params=query_params,
                    headers=headers,
                    body=body,
                    user_id=user_id,
                )
                result["mode"] = "cli"
                result["fallback_from"] = "http"
                result["fallback_reason"] = str(e)
                return result
            except GitHubProxyError:
                # CLI 也失败，抛出原始 HTTP 错误
                raise

    async def proxy_raw_content(
        self,
        path: str,
        mode: str = "auto",
    ) -> dict:
        """代理 GitHub 静态资源，支持模式选择和自动降级。"""
        if mode == "cli":
            result = await self.cli_service.proxy_raw_content(path)
            result["mode"] = "cli"
            return result

        if mode == "http":
            result = await self.http_service.proxy_raw_content(path)
            result["mode"] = "http"
            return result

        # auto 模式
        try:
            result = await self.http_service.proxy_raw_content(path)
            result["mode"] = "http"
            return result
        except GitHubProxyError:
            result = await self.cli_service.proxy_raw_content(path)
            result["mode"] = "cli"
            return result

    def clear_cache(self) -> dict:
        """清空所有缓存，返回各服务清空的条目数。"""
        return {
            "http": self.http_service.clear_cache(),
            "cli": self.cli_service.clear_cache(),
        }

    async def close(self) -> None:
        await self.http_service.close()
