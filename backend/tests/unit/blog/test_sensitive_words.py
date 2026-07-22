"""敏感词过滤器 单元测试。

测试覆盖：
- SensitiveWordFilter.check: 匹配、大小写不敏感、无敏感词、空文本、空词表
- init_filter / get_filter: 全局单例模式
"""

from __future__ import annotations

import pytest

from backend.plugins.blog.sensitive_words import (
    SensitiveWordFilter,
    get_filter,
    init_filter,
)


class TestSensitiveWordFilter:
    def test_check_passes_when_no_match(self):
        """文本不含敏感词应返回 (True, [])。"""
        word_filter = SensitiveWordFilter(["bad", "spam"])
        passed, matched = word_filter.check("hello world")
        assert passed is True
        assert matched == []

    def test_check_rejects_when_match_found(self):
        """文本含敏感词应返回 (False, [匹配到的词])。"""
        word_filter = SensitiveWordFilter(["bad", "spam"])
        passed, matched = word_filter.check("this is bad content")
        assert passed is False
        assert "bad" in matched

    def test_check_matches_multiple_words(self):
        """文本含多个敏感词应全部返回。"""
        word_filter = SensitiveWordFilter(["bad", "spam", "evil"])
        passed, matched = word_filter.check("bad spam content")
        assert passed is False
        assert sorted(matched) == ["bad", "spam"]

    def test_check_case_insensitive(self):
        """敏感词匹配应大小写不敏感。"""
        word_filter = SensitiveWordFilter(["BAD", "SpAm"])
        passed, matched = word_filter.check("this is bad and spam")
        assert passed is False
        # 匹配到的词返回原始词表中的形式
        assert len(matched) == 2

    def test_check_empty_text(self):
        """空文本应返回通过。"""
        word_filter = SensitiveWordFilter(["bad"])
        passed, matched = word_filter.check("")
        assert passed is True
        assert matched == []

    def test_check_empty_word_list(self):
        """空词表应返回通过。"""
        word_filter = SensitiveWordFilter([])
        passed, matched = word_filter.check("any content")
        assert passed is True
        assert matched == []

    def test_check_none_word_list(self):
        """未初始化词表应返回通过。"""
        word_filter = SensitiveWordFilter()
        passed, matched = word_filter.check("any content")
        assert passed is True
        assert matched == []

    def test_check_partial_word_match(self):
        """中文/英文边界的子串匹配不应误判。"""
        # "ass" 是 "classic" 的子串，简单字符串匹配会误判 -
        # 这是当前实现的设计限制，测试记录此行为
        word_filter = SensitiveWordFilter(["ass"])
        # 当前实现使用简单子串匹配，所以 "classic" 中的 "ass" 会被匹配到
        # 如果需要更精确的匹配，应使用词边界匹配
        passed, matched = word_filter.check("this is a classic example")
        # 当前预期：简单子串匹配会匹配到
        assert passed is False
        assert "ass" in matched

    def test_check_unicode_text(self):
        """Unicode 文本中的敏感词应被正确匹配。"""
        word_filter = SensitiveWordFilter(["敏感词"])
        passed, matched = word_filter.check("这段文本包含敏感词")
        assert passed is False
        assert "敏感词" in matched


class TestSensitiveWordSingleton:
    def test_init_filter_returns_instance(self):
        """init_filter 应返回 SensitiveWordFilter 实例。"""
        instance = init_filter(["word1", "word2"])
        assert isinstance(instance, SensitiveWordFilter)

    def test_get_filter_after_init_returns_same(self):
        """init_filter 后 get_filter 应返回同一实例。"""
        # 重置全局状态
        import backend.plugins.blog.sensitive_words as sw

        sw._filter = None
        instance1 = init_filter(["test"])
        instance2 = get_filter()
        assert instance1 is instance2

    def test_get_filter_without_init_creates_default(self):
        """未调用 init_filter 时 get_filter 应创建默认实例。"""
        import backend.plugins.blog.sensitive_words as sw

        sw._filter = None
        instance = get_filter()
        assert isinstance(instance, SensitiveWordFilter)
        # 默认实例应通过所有检查（空词表）
        passed, matched = instance.check("any text")
        assert passed is True
        assert matched == []