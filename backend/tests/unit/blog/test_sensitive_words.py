"""敏感词过滤器测试 —— SensitiveWordFilter。"""

import pytest

from backend.plugins.blog.sensitive_words import (
    SensitiveWordFilter,
    init_filter,
    get_filter,
)


class TestSensitiveWordFilter:
    """测试敏感词过滤器核心功能。"""

    def test_init_with_words(self):
        """初始化时传入敏感词列表。"""
        f = SensitiveWordFilter(["bad", "spam"])
        assert f._words == ["bad", "spam"]

    def test_init_without_words(self):
        """初始化时不传参数使用空列表。"""
        f = SensitiveWordFilter()
        assert f._words == []

    def test_init_with_none(self):
        """初始化时传入 None 使用空列表。"""
        f = SensitiveWordFilter(None)
        assert f._words == []

    def test_check_clean_text(self):
        """无敏感词的文本通过检查。"""
        f = SensitiveWordFilter(["bad", "spam"])
        passed, matched = f.check("hello world")
        assert passed is True
        assert matched == []

    def test_check_with_sensitive_word(self):
        """包含敏感词的文本被拦截。"""
        f = SensitiveWordFilter(["bad", "spam"])
        passed, matched = f.check("this is a bad word")
        assert passed is False
        assert matched == ["bad"]

    def test_check_multiple_sensitive_words(self):
        """返回所有匹配的敏感词。"""
        f = SensitiveWordFilter(["bad", "spam", "evil"])
        passed, matched = f.check("bad spam is evil")
        assert passed is False
        assert len(matched) == 3
        assert "bad" in matched
        assert "spam" in matched
        assert "evil" in matched

    def test_case_insensitive(self):
        """大小写不敏感匹配。"""
        f = SensitiveWordFilter(["BAD", "Spam"])
        passed, matched = f.check("this is bad and spam")
        assert passed is False
        # 返回的是原始敏感词列表中的值
        assert "BAD" in matched
        assert "Spam" in matched

    def test_empty_text(self):
        """空文本通过检查。"""
        f = SensitiveWordFilter(["bad"])
        passed, matched = f.check("")
        assert passed is True
        assert matched == []

    def test_empty_words_list(self):
        """空敏感词列表时所有文本通过。"""
        f = SensitiveWordFilter([])
        passed, matched = f.check("bad spam evil")
        assert passed is True
        assert matched == []

    def test_partial_word_match(self):
        """部分匹配也触发（子串匹配）。"""
        f = SensitiveWordFilter(["ass"])
        passed, matched = f.check("this is a classic example")
        # "ass" 在 "classic" 中作为子串
        assert passed is False
        assert "ass" in matched

    def test_unicode_text(self):
        """Unicode 文本正常处理。"""
        f = SensitiveWordFilter(["fóo"])
        passed, matched = f.check("this is fóo text")
        assert passed is False
        assert "fóo" in matched

    def test_special_characters(self):
        """特殊字符文本正常处理。"""
        f = SensitiveWordFilter(["bad!@#"])
        passed, matched = f.check("contains bad!@# here")
        assert passed is False

    def test_whitespace_handling(self):
        """空白字符不影响匹配。"""
        f = SensitiveWordFilter(["bad word"])
        passed, matched = f.check("contains bad word here")
        assert passed is False


class TestInitFilter:
    """测试 init_filter 和 get_filter 全局函数。"""

    def teardown_method(self):
        """重置全局过滤器状态。"""
        import backend.plugins.blog.sensitive_words as sw
        sw._filter = None

    def test_init_filter_returns_filter(self):
        """init_filter 返回 SensitiveWordFilter 实例。"""
        f = init_filter(["test"])
        assert isinstance(f, SensitiveWordFilter)
        assert f._words == ["test"]

    def test_get_filter_after_init(self):
        """init_filter 后 get_filter 返回同一实例。"""
        f1 = init_filter(["test"])
        f2 = get_filter()
        assert f1 is f2

    def test_get_filter_without_init(self):
        """未 init 时 get_filter 返回默认实例。"""
        f = get_filter()
        assert isinstance(f, SensitiveWordFilter)
        assert f._words == []

    def test_get_filter_singleton(self):
        """get_filter 多次调用返回同一实例。"""
        f1 = get_filter()
        f2 = get_filter()
        assert f1 is f2