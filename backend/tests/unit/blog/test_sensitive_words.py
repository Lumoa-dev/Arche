"""敏感词过滤单元测试。

测试覆盖：SensitiveWordFilter 检查逻辑、大小写不敏感匹配、空文本/空词表、
全局过滤器单例模式。
"""

from __future__ import annotations

import pytest

from backend.plugins.blog.sensitive_words import (
    SensitiveWordFilter,
    get_filter,
    init_filter,
)


class TestSensitiveWordFilter:
    """测试 SensitiveWordFilter 核心逻辑。"""

    def test_clean_text_passes(self):
        """不含敏感词的文本应通过检查。"""
        f = SensitiveWordFilter(words=["bad", "spam"])
        passed, matched = f.check("hello world")
        assert passed is True
        assert matched == []

    def test_text_with_sensitive_words_fails(self):
        """含敏感词的文本应不通过检查。"""
        f = SensitiveWordFilter(words=["bad", "spam"])
        passed, matched = f.check("this is bad content")
        assert passed is False
        assert "bad" in matched

    def test_case_insensitive_matching(self):
        """敏感词匹配应忽略大小写。"""
        f = SensitiveWordFilter(words=["bad", "spam"])
        passed, matched = f.check("This is BAD content")
        assert passed is False
        assert "bad" in matched

    def test_multiple_matched_words(self):
        """应返回所有匹配到的敏感词。"""
        f = SensitiveWordFilter(words=["bad", "spam", "evil"])
        passed, matched = f.check("bad spam content")
        assert passed is False
        assert len(matched) == 2
        assert "bad" in matched
        assert "spam" in matched

    def test_empty_word_list(self):
        """空词表时，任何文本都应通过。"""
        f = SensitiveWordFilter(words=[])
        passed, matched = f.check("any content at all")
        assert passed is True
        assert matched == []

    def test_none_word_list(self):
        """未指定词表时，任何文本都应通过。"""
        f = SensitiveWordFilter()
        passed, matched = f.check("any content")
        assert passed is True
        assert matched == []

    def test_empty_text(self):
        """空文本应通过检查。"""
        f = SensitiveWordFilter(words=["bad"])
        passed, matched = f.check("")
        assert passed is True
        assert matched == []

    def test_none_text(self):
        """空字符串文本应通过检查。"""
        f = SensitiveWordFilter(words=["bad"])
        passed, matched = f.check("")
        assert passed is True
        assert matched == []

    def test_partial_word_not_matched(self):
        """部分匹配不应触发。"""
        f = SensitiveWordFilter(words=["bad"])
        passed, matched = f.check("battery")
        assert passed is True
        assert matched == []

    def test_special_characters(self):
        """特殊字符不应影响准确匹配。"""
        f = SensitiveWordFilter(words=["bad"])
        passed, matched = f.check("bad!")
        assert passed is False
        assert "bad" in matched


class TestGlobalFilter:
    """测试全局过滤器单例。"""

    def test_init_filter_creates_instance(self):
        """init_filter 应创建并返回过滤器实例。"""
        f = init_filter(["bad", "spam"])
        assert isinstance(f, SensitiveWordFilter)
        assert get_filter() is f

    def test_get_filter_returns_singleton(self):
        """get_filter 应返回同一实例。"""
        f1 = get_filter()
        f2 = get_filter()
        assert f1 is f2

    def test_get_filter_defaults_to_empty(self):
        """未初始化时，get_filter 应创建空词表过滤器。"""
        # 重置全局状态
        import backend.plugins.blog.sensitive_words as sw

        sw._filter = None
        f = sw.get_filter()
        assert isinstance(f, SensitiveWordFilter)
        passed, matched = f.check("任何内容")
        assert passed is True
        assert matched == []