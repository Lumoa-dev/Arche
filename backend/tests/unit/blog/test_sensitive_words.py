"""SensitiveWordFilter 敏感词过滤器测试。

测试原则：
- 纯内存实现，无需数据库
- 测试边界条件：空列表、空文本、大小写、子串匹配
"""

from __future__ import annotations

import pytest

from backend.plugins.blog.sensitive_words import (
    SensitiveWordFilter,
    get_filter,
    init_filter,
)


class TestSensitiveWordFilter:
    """敏感词过滤器行为测试。"""

    def test_empty_word_list_allows_all(self):
        """空敏感词列表应允许所有文本通过。"""
        f = SensitiveWordFilter(words=[])
        passed, matched = f.check("任何文本都不会被拦截")
        assert passed is True
        assert matched == []

    def test_no_initial_words_allows_all(self):
        """未初始化敏感词列表应允许所有文本通过。"""
        f = SensitiveWordFilter()
        passed, matched = f.check("任何文本都不会被拦截")
        assert passed is True
        assert matched == []

    def test_empty_text_passes(self):
        """空文本应通过检查。"""
        f = SensitiveWordFilter(words=["敏感"])
        passed, matched = f.check("")
        assert passed is True
        assert matched == []

    def test_single_word_matched(self):
        """文本包含敏感词应返回匹配的单词列表。"""
        f = SensitiveWordFilter(words=["暴力", "色情"])
        passed, matched = f.check("这是一篇包含暴力的文章")
        assert passed is False
        assert matched == ["暴力"]

    def test_multiple_words_matched(self):
        """文本包含多个敏感词应全部返回。"""
        f = SensitiveWordFilter(words=["暴力", "色情", "赌博"])
        passed, matched = f.check("暴力、色情和赌博内容")
        assert passed is False
        assert set(matched) == {"暴力", "色情", "赌博"}

    def test_no_match(self):
        """文本不包含敏感词应返回通过。"""
        f = SensitiveWordFilter(words=["暴力", "色情"])
        passed, matched = f.check("这是一篇健康的文章")
        assert passed is True
        assert matched == []

    def test_case_insensitive(self):
        """敏感词匹配应忽略大小写。"""
        f = SensitiveWordFilter(words=["violence"])
        passed, matched = f.check("This contains Violence")
        assert passed is False
        assert matched == ["violence"]

    def test_partial_word_match(self):
        """敏感词作为子串出现在单词中应被检测。"""
        f = SensitiveWordFilter(words=["ass"])
        passed, matched = f.check("this is a class assignment")
        # "class" 包含 "ass" 子串
        assert passed is False
        assert matched == ["ass"]

    def test_unicode_support(self):
        """应支持中文字符（基于子串匹配）。"""
        f = SensitiveWordFilter(words=["违禁词"])
        passed, matched = f.check("这是一篇普通的文章")
        assert passed is True
        assert matched == []

    def test_whitespace_handling(self):
        """应正确处理空白字符。"""
        f = SensitiveWordFilter(words=["敏感词"])
        passed, matched = f.check("  包含 敏感词 的文章  ")
        assert passed is False
        assert matched == ["敏感词"]


class TestSensitiveWordFilterGlobal:
    """全局过滤器实例测试。"""

    def test_init_filter_sets_global(self):
        """init_filter() 应初始化全局过滤器。"""
        f = init_filter(["敏感词A"])
        assert f is get_filter()

    def test_get_filter_default_empty(self):
        """未初始化时 get_filter() 应返回空过滤器。"""
        # 重置全局状态（注意：测试间可能相互影响，但这是模块级单例的设计）
        import backend.plugins.blog.sensitive_words as sw

        sw._filter = None
        f = get_filter()
        assert isinstance(f, SensitiveWordFilter)