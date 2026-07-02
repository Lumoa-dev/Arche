"""爬虫插件 —— 链接提取器 extract_links 单元测试。"""
# pylint: disable=redefined-outer-name

from __future__ import annotations

import pytest

from backend.plugins.crawler.link_extractor import extract_links


class TestExtractLinks:
    """extract_links 链接提取行为测试。"""

    def test_extracts_simple_links(self):
        """提取所有 <a href> 链接。"""
        html = '<a href="https://example.com/page1">Link 1</a>'
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page1"]

    def test_converts_relative_to_absolute(self):
        """相对路径应转为绝对 URL。"""
        html = '<a href="/about">About</a>'
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/about"]

    def test_filters_javascript_links(self):
        """javascript: 伪协议链接应被过滤。"""
        html = '<a href="javascript:void(0)">Click</a>'
        links = extract_links(html, "https://example.com")
        assert links == []

    def test_filters_mailto_links(self):
        """mailto: 链接应被过滤。"""
        html = '<a href="mailto:test@example.com">Email</a>'
        links = extract_links(html, "https://example.com")
        assert links == []

    def test_filters_tel_links(self):
        """tel: 链接应被过滤。"""
        html = '<a href="tel:+1234567890">Call</a>'
        links = extract_links(html, "https://example.com")
        assert links == []

    def test_filters_anchor_links(self):
        """# 锚点链接应被过滤。"""
        html = '<a href="#section">Section</a>'
        links = extract_links(html, "https://example.com")
        assert links == []

    def test_deduplicates_links(self):
        """相同链接应去重。"""
        html = """
        <a href="https://example.com/page">Link 1</a>
        <a href="https://example.com/page">Link 2</a>
        """
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/page"]

    def test_multiple_links(self):
        """提取多个链接。"""
        html = """
        <a href="/page1">Page 1</a>
        <a href="/page2">Page 2</a>
        <a href="https://external.com">External</a>
        """
        links = extract_links(html, "https://example.com")
        assert len(links) == 3
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links
        assert "https://external.com" in links

    def test_empty_html(self):
        """空 HTML 应返回空列表。"""
        assert extract_links("", "https://example.com") == []

    def test_html_without_links(self):
        """无链接的 HTML 应返回空列表。"""
        html = "<html><body><p>No links here</p></body></html>"
        assert extract_links(html, "https://example.com") == []

    def test_links_with_trailing_slash_deduplication(self):
        """无协议 scheme 的链接应被过滤。"""
        html = '<a href="ftp://files.example.com">FTP</a>'
        links = extract_links(html, "https://example.com")
        assert links == []

    def test_links_with_query_params(self):
        """带查询参数的链接应被保留。"""
        html = '<a href="https://example.com/search?q=test">Search</a>'
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/search?q=test"]

    def test_no_href_attribute(self):
        """没有 href 属性的 a 标签应被忽略。"""
        html = '<a class="button">Not a link</a>'
        assert extract_links(html, "https://example.com") == []

    def test_multiple_nested_tags(self):
        """嵌套标签中的链接也应被提取。"""
        html = """
        <div>
            <p><a href="/nested">Nested Link</a></p>
        </div>
        """
        links = extract_links(html, "https://example.com")
        assert links == ["https://example.com/nested"]