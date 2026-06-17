"""爬虫插件 —— 链接提取：从 HTML 中提取 <a href> 值。"""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.links.append(value)


def extract_links(html: str, base_url: str) -> list[str]:
    """从 HTML 中提取有效链接，过滤无效 scheme，转绝对路径。"""
    parser = _LinkExtractor()
    parser.feed(html)
    seen: set[str] = set()
    result: list[str] = []
    for href in parser.links:
        href = href.strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        abs_url = urljoin(base_url, href)
        if not abs_url.startswith(("http://", "https://")):
            continue
        if abs_url not in seen:
            seen.add(abs_url)
            result.append(abs_url)
    return result
