"""链接提取器单元测试 —— 覆盖 HTML 解析、URL 过滤及去重。"""

from __future__ import annotations

import pytest

from backend.plugins.crawler.link_extractor import extract_links


class TestExtractLinks:
    """extract_links 纯函数测试。"""

    def test_simple_link(self):
        html = '<a href="https://example.com/page">link</a>'
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_relative_to_absolute(self):
        html = '<a href="/page">link</a>'
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_relative_with_subdir(self):
        html = '<a href="sub/page">link</a>'
        links = extract_links(html, "https://example.com/base/")
        assert links == ["https://example.com/base/sub/page"]

    def test_filter_invalid_schemes(self):
        html = (
            '<a href="javascript:void(0)">js</a>'
            '<a href="mailto:test@example.com">mail</a>'
            '<a href="tel:+123456789">tel</a>'
            '<a href="#section">anchor</a>'
        )
        links = extract_links(html, "https://example.com")
        assert links == []

    def test_filter_non_http_scheme(self):
        html = '<a href="ftp://files.example.com">ftp</a>'
        links = extract_links(html, "https://example.com")
        assert links == []

    def test_duplicate_links_deduplicated(self):
        html = (
            '<a href="https://example.com/page">link1</a>'
            '<a href="https://example.com/page">link2</a>'
        )
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_duplicate_relative_to_absolute(self):
        html = (
            '<a href="/page">link1</a>'
            '<a href="https://example.com/page">link2</a>'
        )
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_empty_html(self):
        links = extract_links("", "https://example.com")
        assert links == []

    def test_no_links(self):
        html = "<html><body><p>No links here</p></body></html>"
        links = extract_links(html, "https://example.com")
        assert links == []

    def test_multiple_links(self):
        html = (
            '<a href="https://example.com/a">A</a>'
            '<a href="https://example.com/b">B</a>'
            '<a href="https://other.com/c">C</a>'
        )
        links = extract_links(html, "https://example.com")
        assert len(links) == 3
        assert "https://example.com/a" in links
        assert "https://example.com/b" in links
        assert "https://other.com/c" in links

    def test_strip_whitespace(self):
        html = '<a href="  https://example.com/page  ">link</a>'
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_empty_href_skipped(self):
        html = '<a href="">link</a><a href="  ">space</a>'
        links = extract_links(html, "https://example.com")
        assert links == []