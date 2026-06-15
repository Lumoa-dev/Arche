"""爬虫插件 —— 解析车间：从 HTML 提取正文、标题、链接。"""

from __future__ import annotations

import re

from backend.plugins.crawler.link_extractor import extract_links
from backend.plugins.crawler.pipeline.base import BaseStage, CrawlItem


class ParseStage(BaseStage):
    """解析车间：从 HTML 提取正文、标题、链接列表。"""

    name = "parse"

    async def process(self, item: CrawlItem) -> CrawlItem | None:
        if item.error:
            return item

        html = item.raw_html or ""
        if not html:
            item.error = "No HTML to parse"
            return item

        # 标题
        if not item.title:
            item.title = self._extract_title(html)

        # 正文
        if not item.content:
            item.content = self._extract_text(html)

        # 链接
        if not item.links:
            item.links = extract_links(html, item.url)

        return item

    @staticmethod
    def _extract_title(html: str) -> str:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _extract_text(html: str) -> str:
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
        return text[:10000]
