"""SensitiveWordFilter 单元测试 —— 敏感词过滤器。

测试原则：
- 只测试公开方法行为
- 覆盖边界条件：空列表、空文本、大小写、部分匹配
"""

from __future__ import annotations

from backend.plugins.blog.sensitive_words import (
    SensitiveWordFilter,
    get_filter,
    init_filter,
)


class TestSensitiveWordFilter:
    """敏感词过滤器行为测试。"""

    def test_empty_word_list(self):
        """空敏感词列表时，任何文本都通过。"""
        filt = SensitiveWordFilter([])
        passed, matched = filt.check("包含敏感词的内容")
        assert passed is True
        assert matched == []

    def test_none_word_list(self):
        """None 敏感词列表时，任何文本都通过。"""
        filt = SensitiveWordFilter()
        passed, matched = filt.check("包含敏感词的内容")
        assert passed is True
        assert matched == []

    def test_empty_text(self):
        """空文本始终通过。"""
        filt = SensitiveWordFilter(["敏感词"])
        passed, matched = filt.check("")
        assert passed is True
        assert matched == []

    def test_no_match(self):
        """文本不包含任何敏感词。"""
        filt = SensitiveWordFilter(["敏感词", "违禁词"])
        passed, matched = filt.check("这是一段正常的内容")
        assert passed is True
        assert matched == []

    def test_single_match(self):
        """文本包含单个敏感词。"""
        filt = SensitiveWordFilter(["敏感词"])
        passed, matched = filt.check("这段内容包含敏感词")
        assert passed is False
        assert matched == ["敏感词"]

    def test_multiple_matches(self):
        """文本包含多个敏感词。"""
        filt = SensitiveWordFilter(["敏感词", "违禁词", "正常词"])
        passed, matched = filt.check("包含敏感词和违禁词")
        assert passed is False
        assert len(matched) == 2
        assert "敏感词" in matched
        assert "违禁词" in matched

    def test_case_insensitive(self):
        """大小写不敏感匹配。"""
        filt = SensitiveWordFilter(["badword"])
        passed, matched = filt.check("This contains BADWORD")
        assert passed is False
        assert matched == ["badword"]

    def test_mixed_case_in_word_list(self):
        """敏感词列表中的大小写混合。"""
        filt = SensitiveWordFilter(["BadWord"])
        passed, matched = filt.check("contains badword")
        assert passed is False
        assert matched == ["BadWord"]

    def test_partial_word_match(self):
        """敏感词是另一个词的一部分时仍匹配。"""
        filt = SensitiveWordFilter(["ass"])
        passed, matched = filt.check("这是单词pass中的一部分")
        # "ass" 在 "pass" 中，所以匹配
        assert passed is False
        assert len(matched) > 0

    def test_unicode_support(self):
        """支持 Unicode 敏感词。"""
        filt = SensitiveWordFilter(["спам", "垃圾"])
        passed, matched = filt.check("这是垃圾信息")
        assert passed is False
        assert matched == ["垃圾"]

    def test_all_words_match(self):
        """所有敏感词都匹配时。"""
        filt = SensitiveWordFilter(["词A", "词B", "词C"])
        passed, matched = filt.check("词A和词B和词C")
        assert passed is False
        assert len(matched) == 3


class TestGlobalFilter:
    """全局过滤器实例测试。"""

    def test_init_filter_creates_instance(self):
        """init_filter 创建全局实例。"""
        # 重置全局状态
        import backend.plugins.blog.sensitive_words as sw

        sw._filter = None
        filt = init_filter(["敏感词"])
        assert filt is not None
        assert get_filter() is filt

    def test_get_filter_default(self):
        """get_filter 在未初始化时创建默认实例。"""
        import backend.plugins.blog.sensitive_words as sw

        sw._filter = None
        filt = get_filter()
        assert filt is not None
        # 默认实例应有空词表
        passed, matched = filt.check("任何内容")
        assert passed is True
        assert matched == []