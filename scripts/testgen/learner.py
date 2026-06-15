"""模板学习：逆向分析现有测试文件，提炼断言模式。

扫描项目中的已有测试文件，提取常见的断言模式并分类存储。
生成的模式数据可用于提升新生成测试的断言质量。
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

EXPECT_PATTERN = re.compile(
    r"expect\(([^)]+)\)\.([a-zA-Z]+)\(([^)]*)\)",
)
DESCRIBE_NAME_PATTERN = re.compile(
    r"describe\s*\(\s*['\"]([^'\"]+)['\"]",
)


@dataclass
class AssertionPattern:
    subject: str  # 断言主体，如 'get', 'result'
    matcher: str  # 匹配器，如 'toHaveBeenCalledWith', 'toBeDefined'
    args: str  # 参数，如 "['/auth/login', params, undefined]"
    frequency: int = 1  # 出现次数


@dataclass
class LearnedPatterns:
    api_assertions: dict[str, list[AssertionPattern]] = field(default_factory=dict)
    mock_patterns: dict[str, list[str]] = field(default_factory=dict)
    total_tests_analyzed: int = 0


def _scan_assertions(content: str) -> list[AssertionPattern]:
    """从测试文件内容中提取所有断言模式"""
    patterns: list[AssertionPattern] = []
    for m in EXPECT_PATTERN.finditer(content):
        subject = m.group(1).strip()
        matcher = m.group(2)
        args = m.group(3).strip()
        patterns.append(AssertionPattern(subject=subject, matcher=matcher, args=args))
    return patterns


def _describe_name(content: str) -> str:
    """获取文件中第一个 describe 的名称"""
    m = DESCRIBE_NAME_PATTERN.search(content)
    return m.group(1) if m else "unknown"


def learn_from_tests(root: Path | None = None) -> LearnedPatterns:
    """扫描项目中所有现有测试文件，学习断言模式。"""
    if root is None:
        root = Path.cwd()

    patterns = LearnedPatterns()

    # 扫描前端 API 测试
    api_test_dir = root / "frontend" / "src" / "tests" / "services" / "api"
    if api_test_dir.exists():
        for f in sorted(api_test_dir.glob("*.test.ts")):
            content = f.read_text(encoding="utf-8")
            module = _describe_name(content)
            assertions = _scan_assertions(content)

            filtered = [
                a
                for a in assertions
                if a.matcher
                in (
                    "toHaveBeenCalledWith",
                    "toHaveBeenCalled",
                    "toBeDefined",
                    "toBe",
                    "toEqual",
                    "mockResolvedValue",
                    "mockRejectedValue",
                )
            ]
            patterns.api_assertions[module] = filtered
            patterns.total_tests_analyzed += 1

    # 扫描前端工具函数测试
    util_test_dir = root / "frontend" / "src" / "tests" / "utils"
    if util_test_dir.exists():
        for f in sorted(util_test_dir.glob("*.test.ts")):
            module = f.stem.replace(".test", "")
            content = f.read_text(encoding="utf-8")
            assertions = _scan_assertions(content)
            if module not in patterns.api_assertions:
                patterns.api_assertions[module] = []
            patterns.api_assertions[module].extend(assertions)
            patterns.total_tests_analyzed += 1

    return patterns


def _frequency_sort_key(p):
    return -p.frequency


def get_top_patterns(
    patterns: LearnedPatterns, module: str, top_n: int = 5
) -> list[AssertionPattern]:
    """获取某个模块最常用的断言模式"""
    module_patterns = patterns.api_assertions.get(module, [])
    seen: dict[str, AssertionPattern] = {}
    for p in module_patterns:
        key = f"{p.matcher}:{p.args}"
        if key in seen:
            seen[key].frequency += 1
        else:
            seen[key] = p
    sorted_p = sorted(seen.values(), key=_frequency_sort_key)
    return sorted_p[:top_n]


def enhance_with_patterns(
    generated_content: str,
    learned: LearnedPatterns,
    module: str,
) -> str:
    """用学习到的断言模式增强生成的测试内容。

    目前实现：在生成内容的末尾追加已知的断言模式（去重后）。
    """
    top = get_top_patterns(learned, module, 3)
    if not top:
        return generated_content

    existing_assertions = set(EXPECT_PATTERN.findall(generated_content))
    new_assertions = []
    for p in top:
        key = (p.subject, p.matcher, p.args)
        if key not in existing_assertions:
            new_assertions.append(f"    expect({p.subject}).{p.matcher}({p.args})")

    if not new_assertions:
        return generated_content

    lines = generated_content.split("\n")
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("describe(") or line.strip().startswith("class "):
            insert_pos = i
            break

    if insert_pos > 0:
        comment = "\n// 从已有测试学习到的断言模式\n"
        for i, a in enumerate(new_assertions):
            lines.insert(insert_pos + i, a)
        lines.insert(insert_pos, comment)

    return "\n".join(lines)
