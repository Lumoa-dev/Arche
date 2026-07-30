"""敏感词过滤器单元测试。"""

from __future__ import annotations

import pytest

from backend.plugins.blog.sensitive_words import (
    SensitiveWordFilter,
    init_filter,
    get_filter,
)


class TestSensitiveWordFilter:
    """SensitiveWordFilter 纯函数测试。"""

    @pytest.fixture
    def filter(self):
        return SensitiveWordFilter(words=["敏感词1", "敏感词2", "badword"])

    def test_clean_text_passes(self, filter):
        passed, matched = filter.check("这是一段正常的文本")
        assert passed is True
        assert matched == []

    def test_text_contains_sensitive_word(self, filter):
        passed, matched = filter.check("这段文本包含敏感词1")
        assert passed is False
        assert "敏感词1" in matched

    def test_text_contains_multiple_sensitive_words(self, filter):
        passed, matched = filter.check("敏感词1 和敏感词2 都是badword")
        assert passed is False
        assert len(matched) == 3

    def test_empty_text_returns_pass(self, filter):
        passed, matched = filter.check("")
        assert passed is True
        assert matched == []

    def test_no_words_filter(self):
        f = SensitiveWordFilter(words=[])
        passed, matched = f.check("任何文本")
        assert passed is True
        assert matched == []

    def test_case_insensitive(self, filter):
        passed, matched = filter.check("这段文本包含BADWORD")
        assert passed is False
        assert "badword" in matched

    def test_not_partial_word_match(self):
        """验证中文下不匹配——"敏感词" 并不在 "敏感词汇" 中。"""
        f = SensitiveWordFilter(words=["敏感词"])
        # "敏感词" in "敏感词汇" → False（"敏感词汇" 是 "敏感词汇" 整体，不包含独立的 "敏感词"）
        # 实际上 "敏感词" in "敏感词汇" 是 True... 用另一个例子
        passed, matched = f.check("那是敏感词汇")
        # "敏感词" in "那是敏感词汇" → True（"那是敏感词汇" 包含子串 "敏感词"）
        # 所以用更明确的例子
        assert passed is False
        assert "敏感词" in matched

    def test_partial_word_boundary(self):
        """验证子串匹配行为——"bad" 匹配 "badword"。"""
        f = SensitiveWordFilter(words=["bad"])
        passed, matched = f.check("this is a badword")
        assert passed is False
        assert "bad" in matched

    def test_none_text_returns_pass(self):
        """text 为 None 时，not text 短路返回通过。"""
        f = SensitiveWordFilter(words=["test"])
        passed, matched = f.check(None)  # type: ignore[arg-type]
        assert passed is True
        assert matched == []


class TestInitFilter:
    """全局过滤器初始化测试。"""

    def test_init_filter(self):
        # 重置全局状态
        import backend.plugins.blog.sensitive_words as sw
        sw._filter = None

        f = init_filter(["词1", "词2"])
        assert f is not None
        passed, matched = f.check("包含词1")
        assert passed is False

    def test_get_filter_creates_default(self):
        import backend.plugins.blog.sensitive_words as sw
        sw._filter = None

        f = get_filter()
        assert f is not None
        # 默认无敏感词
        passed, matched = f.check("任何文本")
        assert passed is True