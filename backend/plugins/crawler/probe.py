"""爬虫插件 —— 探嗅回路：httpx 轻量 HTTP 探测。"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

# 功能性页面的 URL 路径特征
_FUNCTIONAL_PATTERNS = [
    "/login",
    "/signin",
    "/signup",
    "/register",
    "/auth",
    "/logout",
    "/forgot",
    "/reset-password",
    "/verify",
    "/captcha",
    "/challenge",
]

# 功能性页面的 title 特征
_FUNCTIONAL_TITLES = [
    "login",
    "sign in",
    "register",
    "sign up",
    "captcha",
    "verify",
    "access denied",
    "403",
    "404",
    "500",
    "502",
    "503",
]

MAX_PROBE_BYTES = 64 * 1024


class ProbeService:
    """探嗅回路：用 httpx 轻量请求快速判断页面类型，决定是否收入种子池。"""

    def __init__(self, timeout: float = 5.0):
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",  # noqa: E501
                    "Accept-Encoding": "gzip, deflate",
                },
            )
        return self._client

    async def probe(self, url: str) -> dict:
        """
        轻量探测，返回:
        {
            "url": str,
            "status_code": int,
            "content_type": str | None,
            "has_content": bool,
            "is_functional": bool,
            "title": str | None,
        }
        """
        try:
            client = await self._get_client()
            response = await client.get(url)
            content_type = response.headers.get("content-type", "")
            content_length = response.headers.get("content-length")
            if (
                content_type
                and "html" not in content_type.lower()
                and "text/plain" not in content_type.lower()
            ):
                return {
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "has_content": False,
                    "is_functional": False,
                    "title": None,
                }
            if content_length and int(content_length) > MAX_PROBE_BYTES:
                return {
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "has_content": False,
                    "is_functional": False,
                    "title": None,
                }

            html = response.text[:5000]  # 只取前 5KB 用于分析
            title = self._extract_title(html)
            path = urlparse(str(response.url)).path.lower()

            # 判断是否为功能性页面
            is_functional = any(p in path for p in _FUNCTIONAL_PATTERNS)
            if title and any(p in title.lower() for p in _FUNCTIONAL_TITLES):
                is_functional = True

            # 判断是否有内容
            text = self._strip_tags(html)
            has_content = len(text.strip()) > 50

            return {
                "url": str(response.url),
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "has_content": has_content,
                "is_functional": is_functional,
                "title": title,
            }
        except Exception:
            return {
                "url": url,
                "status_code": 0,
                "content_type": None,
                "has_content": False,
                "is_functional": False,
                "title": None,
            }

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _extract_title(html: str) -> str | None:
        import re

        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        return m.group(1).strip() if m else None

    @staticmethod
    def _strip_tags(html: str) -> str:
        import re

        text = re.sub(
            r"<script\b[^>]*>[\s\S]*?</script\b[^>]*>",
            "",
            html,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"<style\b[^>]*>[\s\S]*?</style\b[^>]*>",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return re.sub(r"<[^>]+>", " ", text)
