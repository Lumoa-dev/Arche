"""爬虫插件 —— 抓取车间：轻量 HTTP 请求，能拿则拿，拿不到则跳过。"""

from __future__ import annotations

import httpx

from backend.plugins.crawler.pipeline.base import BaseStage, CrawlItem

MAX_HTML_BYTES = 512 * 1024

# 保守请求头：保持普通 HTTP 访问形态，不模拟浏览器执行环境。
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",  # noqa: E501
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


class FetchStage(BaseStage):
    """抓取车间：httpx 请求，限制处理体量，不渲染 JS。"""

    name = "fetch"

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers=_HEADERS,
            )
        return self._client

    async def process(self, item: CrawlItem) -> CrawlItem | None:
        try:
            client = await self._get_client()
            response = await client.get(item.url)
            item.status_code = response.status_code
            item.headers = dict(response.headers)

            content_type = response.headers.get("content-type", "").lower()
            if (
                content_type
                and "html" not in content_type
                and "text/plain" not in content_type
            ):
                item.error = f"non_html_content: {content_type}"
                return item

            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_HTML_BYTES:
                item.error = f"content_too_large: {content_length}"
                return item

            html = response.text
            if (
                len(html.encode(response.encoding or "utf-8", errors="ignore"))
                > MAX_HTML_BYTES
            ):
                html = html[:MAX_HTML_BYTES]

            import re

            # 提取 title
            title_m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            title = title_m.group(1).strip() if title_m else ""

            # 提取链接
            links = []
            seen_links: set[str] = set()
            for m in re.finditer(
                r'<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE
            ):
                href = m.group(1).strip()
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                from urllib.parse import urljoin

                abs_url = urljoin(item.url, href)
                if (
                    abs_url.startswith(("http://", "https://"))
                    and abs_url not in seen_links
                ):
                    seen_links.add(abs_url)
                    links.append(abs_url)

            # 简易文本提取
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
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            item.raw_html = html
            item.title = title
            item.content = text[:10000]
            item.links = links
            return item
        except Exception as e:
            item.error = f"Fetch failed: {e}"
            return item

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
