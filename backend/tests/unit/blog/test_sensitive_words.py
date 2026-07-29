"""敏感词过滤器测试。

测试原则：
- 覆盖空词列表、大小写匹配、无匹配、部分匹配
- 模块级单例函数 init_filter / get_filter 行为
"""

from __future__ import annotations

import pytest

from backend.plugins.blog.sensitive_words import (
    SensitiveWordFilter,
    get_filter,
    init_filter,
)


class TestSensitiveWordFilter:
    """测试 SensitiveWordFilter 核心行为。"""

    def test_no_words_list(self):
        """空词列表时 check 应返回 (True, [])。"""
        f = SensitiveWordFilter()
        ok, matched = f.check("任何文本都不应该被拦截")
        assert ok is True
        assert matched == []

    def test_empty_words_list(self):
        """空列表时 check 应返回 (True, [])。"""
        f = SensitiveWordFilter([])
        ok, matched = f.check("任何文本都不应该被拦截")
        assert ok is True
        assert matched == []

    def test_empty_text(self):
        """空文本应返回 (True, [])。"""
        f = SensitiveWordFilter(["敏感词"])
        ok, matched = f.check("")
        assert ok is True
        assert matched == []

    def test_text_contains_sensitive_word(self):
        """文本包含敏感词时返回 (False, 匹配列表)。"""
        f = SensitiveWordFilter(["赌博", "色情", "暴力"])
        ok, matched = f.check("这篇文章包含赌博和暴力内容")
        assert ok is False
        assert "赌博" in matched
        assert "暴力" in matched
        assert "色情" not in matched

    def test_text_no_sensitive_word(self):
        """文本不包含敏感词时返回 (True, [])。"""
        f = SensitiveWordFilter(["赌博", "色情", "暴力"])
        ok, matched = f.check("这是一篇正常的文章")
        assert ok is True
        assert matched == []

    def test_case_insensitive_matching(self):
        """敏感词匹配应忽略大小写。"""
        f = SensitiveWordFilter(["spam", "bad"])
        ok, matched = f.check("This contains SPAM")
        assert ok is False
        assert "spam" in matched

    def test_mixed_case_text(self):
        """敏感词在文本中大小写混合时应能匹配。"""
        f = SensitiveWordFilter(["spam"])
        ok, matched = f.check("contains SpAm")
        assert ok is False
        assert "spam" in matched

    def test_partial_word_no_match(self):
        """部分匹配不应触发（需要完整子串匹配）。"""
        f = SensitiveWordFilter(["spam"])
        ok, matched = f.check("spamming")  # "spam" 是 "spamming" 的子串，应匹配
        assert ok is False
        assert "spam" in matched

    def test_multiple_matches_dedup_strategy(self):
        """多个敏感词匹配时返回所有匹配项。"""
        f = SensitiveWordFilter(["foo", "bar", "baz"])
        ok, matched = f.check("foo and bar and foo again")
        assert ok is False
        assert "foo" in matched
        assert "bar" in matched
        assert "baz" not in matched

    def test_unicode_sensitive_words(self):
        """Unicode 敏感词正确匹配。"""
        f = SensitiveWordFilter(["攻击", "谩骂"])
        ok, matched = f.check("请不要在这里谩骂他人")
        assert ok is False
        assert "谩骂" in matched

    def test_whitespace_around_text(self):
        """文本前后空白不影响匹配。"""
        f = SensitiveWordFilter(["敏感词"])
        ok, matched = f.check("  文本包含敏感词内容  ")
        assert ok is False
        assert "敏感词" in matched


class TestSensitiveWordFilterSingleton:
    """测试模块级单例函数。"""

    def test_init_filter_returns_instance(self):
        """init_filter 应返回 SensitiveWordFilter 实例。"""
        f = init_filter(["spam"])
        assert isinstance(f, SensitiveWordFilter)

    def test_get_filter_lazy_init(self):
        """get_filter 在未初始化时创建默认空实例。"""
        # 强制重置模块状态
        import backend.plugins.blog.sensitive_words as sw

        sw._filter = None
        f = get_filter()
        assert isinstance(f, SensitiveWordFilter)
        # 空过滤器应通过所有检查
        ok, matched = f.check("任何文本")
        assert ok is True
        assert matched == []

    def test_init_filter_then_get_filter(self):
        """init_filter 后 get_filter 返回同一实例。"""
        import backend.plugins.blog.sensitive_words as sw

        sw._filter = None
        f1 = init_filter(["spam"])
        f2 = get_filter()
        assert f1 is f2
        # 实例应持有 init_filter 传入的词列表
        ok, matched = f2.check("contains SPAM")
        assert ok is False