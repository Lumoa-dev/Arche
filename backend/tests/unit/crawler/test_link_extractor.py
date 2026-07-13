"""链接提取器测试 —— 从 HTML 中提取 <a href> 值。

测试策略：
- 纯函数，无外部依赖，使用固定 HTML 确保确定性
- 覆盖：基础链接提取、无效 scheme 过滤、去重、相对路径转绝对路径
"""

from __future__ import annotations

import pytest

from backend.plugins.crawler.link_extractor import extract_links


class TestLinkExtractor:
    """link_extractor 核心功能测试。"""

    def test_extract_basic_links(self):
        """提取基本的 <a href> 链接。"""
        html = """
        <html>
            <body>
                <a href="https://example.com/page1">Page 1</a>
                <a href="https://example.com/page2">Page 2</a>
            </body>
        </html>
        """
        links = extract_links(html, "https://example.com")
        assert len(links) == 2
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links

    def test_extract_relative_urls(self):
        """相对路径被转换为绝对路径。"""
        html = """
        <html>
            <body>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
            </body>
        </html>
        """
        links = extract_links(html, "https://example.com")
        assert "https://example.com/about" in links
        assert "https://example.com/contact" in links

    def test_extract_relative_urls_with_path_base(self):
        """基础 URL 带路径时相对路径正确拼接。"""
        html = """
        <html>
            <body>
                <a href="details">Details</a>
            </body>
        </html>
        """
        links = extract_links(html, "https://example.com/articles/")
        assert "https://example.com/articles/details" in links

    def test_filter_invalid_schemes(self):
        """过滤 javascript:、mailto:、tel: 等无效 scheme。"""
        html = """
        <html>
            <body>
                <a href="javascript:void(0)">JS</a>
                <a href="mailto:test@example.com">Email</a>
                <a href="tel:+1234567890">Phone</a>
                <a href="#section">Anchor</a>
                <a href="https://example.com/valid">Valid</a>
            </body>
        </html>
        """
        links = extract_links(html, "https://example.com")
        assert len(links) == 1
        assert links[0] == "https://example.com/valid"

    def test_filter_empty_href(self):
        """过滤空 href 属性。"""
        html = """
        <html>
            <body>
                <a href="">Empty</a>
                <a href="  ">Whitespace</a>
                <a href="https://example.com/ok">OK</a>
            </body>
        </html>
        """
        links = extract_links(html, "https://example.com")
        assert len(links) == 1
        assert links[0] == "https://example.com/ok"

    def test_deduplication(self):
        """重复链接只保留一个。"""
        html = """
        <html>
            <body>
                <a href="https://example.com/page">Page 1</a>
                <a href="https://example.com/page">Page 2</a>
            </body>
        </html>
        """
        links = extract_links(html, "https://example.com")
        assert len(links) == 1
        assert links[0] == "https://example.com/page"

    def test_relative_url_deduplication(self):
        """相对路径重复也去重。"""
        html = """
        <html>
            <body>
                <a href="/page">Page 1</a>
                <a href="/page">Page 2</a>
            </body>
        </html>
        """
        links = extract_links(html, "https://example.com")
        # 相对路径转为绝对路径后应去重
        assert len(links) == 1
        assert links[0] == "https://example.com/page"

    def test_no_links(self):
        """无链接的 HTML 返回空列表。"""
        html = "<html><body><p>No links here</p></body></html>"
        links = extract_links(html, "https://example.com")
        assert links == []

    def test_empty_html(self):
        """空 HTML 返回空列表。"""
        links = extract_links("", "https://example.com")
        assert links == []

    def test_ignore_non_http_schemes(self):
        """过滤非 http/https 的绝对 URL。"""
        html = """
        <html>
            <body>
                <a href="ftp://files.example.com/file.txt">FTP</a>
                <a href="file:///local/file.txt">Local</a>
                <a href="https://example.com/valid">Valid</a>
            </body>
        </html>
        """
        links = extract_links(html, "https://example.com")
        assert len(links) == 1
        assert links[0] == "https://example.com/valid"

    def test_links_with_attributes(self):
        """带其他属性的 <a> 标签仍能正确提取。"""
        html = """
        <html>
            <body>
                <a href="https://example.com/page" class="link" rel="nofollow" target="_blank">Page</a>
            </body>
        </html>
        """
        links = extract_links(html, "https://example.com")
        assert len(links) == 1
        assert links[0] == "https://example.com/page"

    def test_mixed_valid_and_invalid(self):
        """混合有效和无效链接，只返回有效的。"""
        html = """
        <html>
            <body>
                <a href="https://example.com/valid">Valid</a>
                <a href="javascript:alert(1)">XSS</a>
                <a href="mailto:spam@example.com">Spam</a>
                <a href="https://example.com/also-valid">Also Valid</a>
                <a href="/relative">Relative</a>
            </body>
        </html>
        """
        links = extract_links(html, "https://example.com")
        assert len(links) == 3
        assert "https://example.com/valid" in links
        assert "https://example.com/also-valid" in links
        assert "https://example.com/relative" in links