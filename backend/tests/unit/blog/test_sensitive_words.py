"""敏感词过滤器 SensitiveWordFilter 单元测试。

测试原则：
- 纯函数逻辑，用参数化测试验证边界条件
- 不依赖外部状态
"""

from __future__ import annotations

import pytest

from backend.plugins.blog.sensitive_words import (
    SensitiveWordFilter,
    get_filter,
    init_filter,
)


class TestSensitiveWordFilter:
    """SensitiveWordFilter 核心功能测试。"""

    def test_check_passes_with_no_words(self):
        """无敏感词列表时任何文本都应通过。"""
        f = SensitiveWordFilter()
        passed, matched = f.check("自由言论")
        assert passed is True
        assert matched == []

    def test_check_passes_with_no_text(self):
        """空文本应直接通过。"""
        f = SensitiveWordFilter(["敏感"])
        passed, matched = f.check("")
        assert passed is True
        assert matched == []

    def test_check_detects_matching_word(self):
        """包含敏感词时应返回 False 和匹配列表。"""
        f = SensitiveWordFilter(["敏感词1", "敏感词2"])
        passed, matched = f.check("这段文本包含敏感词1")
        assert passed is False
        assert "敏感词1" in matched
        assert "敏感词2" not in matched

    def test_check_detects_multiple_matches(self):
        """包含多个敏感词时应全部返回。"""
        f = SensitiveWordFilter(["禁止词A", "禁止词B", "正常词"])
        passed, matched = f.check("包含禁止词A和禁止词B的内容")
        assert passed is False
        assert "禁止词A" in matched
        assert "禁止词B" in matched
        assert "正常词" not in matched

    def test_check_case_insensitive(self):
        """敏感词匹配应忽略大小写。"""
        f = SensitiveWordFilter(["badword"])
        passed, matched = f.check("This contains BADWORD")
        assert passed is False
        assert "badword" in matched

    def test_check_case_insensitive_mixed_case(self):
        """大小写混合的敏感词应被匹配。"""
        f = SensitiveWordFilter(["Spam"])
        passed, matched = f.check("Contains spam in text")
        assert passed is False

    def test_check_no_match(self):
        """不包含敏感词时应通过。"""
        f = SensitiveWordFilter(["敏感词", "违规词"])
        passed, matched = f.check("这是一段完全正常的内容")
        assert passed is True
        assert matched == []

    def test_check_edge_long_text(self):
        """长文本应能正确处理。"""
        words = [f"敏感词{i}" for i in range(100)]
        f = SensitiveWordFilter(words)
        passed, matched = f.check("正常文本" * 1000)
        assert passed is True
        assert matched == []

    def test_check_edge_text_contains_similar_but_not_exact(self):
        """包含敏感词子串但不完全匹配时应通过。"""
        f = SensitiveWordFilter(["敏感词A"])
        # "敏感词AB" 包含 "敏感词A" 作为子串，应被匹配
        passed, matched = f.check("文本包含敏感词AB")
        assert passed is False
        assert "敏感词A" in matched

    def test_check_unicode_text(self):
        """Unicode 文本应正确处理。"""
        f = SensitiveWordFilter(["spam", "bad"])
        passed, matched = f.check("Unicode 文本: 你好，世界！")
        assert passed is True
        assert matched == []


class TestSensitiveWordFilterModule:
    """模块级函数测试。"""

    def test_init_filter_sets_global(self):
        """init_filter 应初始化全局过滤器。"""
        f = init_filter(["测试词"])
        assert isinstance(f, SensitiveWordFilter)

        gf = get_filter()
        assert gf is f

    def test_get_filter_creates_default_if_not_initialized(self):
        """get_filter 在未初始化时应创建默认实例。"""
        # 重置全局状态
        import backend.plugins.blog.sensitive_words as sw

        sw._filter = None
        f = get_filter()
        assert isinstance(f, SensitiveWordFilter)

    def test_get_filter_returns_same_instance(self):
        """get_filter 应返回单例实例。"""
        f1 = get_filter()
        f2 = get_filter()
        assert f1 is f2