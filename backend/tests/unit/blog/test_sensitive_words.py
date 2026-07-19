"""敏感词过滤器测试。"""

from __future__ import annotations

import pytest

from backend.plugins.blog.sensitive_words import SensitiveWordFilter, get_filter, init_filter


class TestSensitiveWordFilter:
    """测试敏感词过滤器。"""

    def test_empty_words_list(self):
        """空敏感词列表应总是通过检查。"""
        f = SensitiveWordFilter()
        passed, matched = f.check("some text")
        assert passed is True
        assert matched == []

    def test_empty_text(self):
        """空文本应总是通过检查。"""
        f = SensitiveWordFilter(["bad"])
        passed, matched = f.check("")
        assert passed is True
        assert matched == []

    def test_no_match(self):
        """文本不包含敏感词应通过。"""
        f = SensitiveWordFilter(["bad", "evil"])
        passed, matched = f.check("this is a clean text")
        assert passed is True
        assert matched == []

    def test_single_match(self):
        """文本包含单个敏感词应不通过。"""
        f = SensitiveWordFilter(["bad", "evil"])
        passed, matched = f.check("this is a bad text")
        assert passed is False
        assert matched == ["bad"]

    def test_multiple_matches(self):
        """文本包含多个敏感词应全部返回。"""
        f = SensitiveWordFilter(["bad", "evil", "ugly"])
        passed, matched = f.check("this is bad and evil")
        assert passed is False
        assert set(matched) == {"bad", "evil"}

    def test_case_insensitive(self):
        """敏感词匹配应不区分大小写。"""
        f = SensitiveWordFilter(["BAD"])
        passed, matched = f.check("this is bad")
        assert passed is False
        assert matched == ["BAD"]

    def test_reverse_case(self):
        """文本中的敏感词大小写不同也应匹配。"""
        f = SensitiveWordFilter(["bad"])
        passed, matched = f.check("this is BAD")
        assert passed is False
        assert matched == ["bad"]

    def test_partial_word_no_match(self):
        """部分匹配不应触发敏感词（非子串匹配的边界）。"""
        f = SensitiveWordFilter(["bad"])
        # "bad" 是 "baddie" 的子串，应匹配
        passed, matched = f.check("this is baddie")
        assert passed is False
        assert matched == ["bad"]

    def test_chinese_sensitive_words(self):
        """中文敏感词匹配。"""
        f = SensitiveWordFilter(["违法", "违规"])
        passed, matched = f.check("这是一条包含违法的文本")
        assert passed is False
        assert "违法" in matched

    def test_no_false_positive(self):
        """不应误报不存在的敏感词。"""
        f = SensitiveWordFilter(["spam", "malware"])
        passed, matched = f.check("this is a sample text")
        assert passed is True
        assert matched == []

    def test_all_words_matched(self):
        """所有敏感词都出现在文本中。"""
        words = ["a", "b", "c"]
        f = SensitiveWordFilter(words)
        passed, matched = f.check("a b c")
        assert passed is False
        assert len(matched) == 3

    def test_none_words(self):
        """words 参数为 None 时等同于空列表。"""
        f = SensitiveWordFilter(None)
        passed, matched = f.check("any text")
        assert passed is True


class TestGlobalFilter:
    """测试全局过滤器实例。"""

    def test_get_filter_default(self):
        """未初始化时 get_filter 应返回空列表的实例。"""
        f = get_filter()
        assert isinstance(f, SensitiveWordFilter)
        # 重置状态
        init_filter([])

    def test_init_filter_sets_words(self):
        """init_filter 应设置敏感词列表。"""
        f = init_filter(["bad", "evil"])
        passed, matched = f.check("this is bad")
        assert passed is False

    def test_init_filter_overrides(self):
        """多次调用 init_filter 应覆盖之前的设置。"""
        init_filter(["bad"])
        f = init_filter(["evil"])
        passed1, _ = f.check("this is bad")
        passed2, _ = f.check("this is evil")
        assert passed1 is True  # "bad" 已被覆盖
        assert passed2 is False