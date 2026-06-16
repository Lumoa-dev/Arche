import re
from dataclasses import dataclass
from pathlib import Path

DESCRIBE_PATTERN = re.compile(
    r"(?:describe|class)\s*\(\s*['\"]([^'\"]+)['\"]",
)


@dataclass
class MergeResult:
    content: str
    merged: bool
    added_count: int
    skipped_count: int


def _extract_names(content: str) -> set[str]:
    return set(DESCRIBE_PATTERN.findall(content))


def _split_blocks(content: str) -> list[tuple[str, str]]:
    """将测试内容按 describe/class 切分为 (名称, 块内容) 列表"""
    blocks: list[tuple[str, str]] = []
    current_lines: list[str] = []
    current_name: str | None = None

    for line in content.split("\n"):
        m = DESCRIBE_PATTERN.search(line)
        if m:
            if current_name and current_lines:
                blocks.append((current_name, "\n".join(current_lines)))
            current_name = m.group(1)
            current_lines = [line]
        elif current_name:
            current_lines.append(line)

    if current_name and current_lines:
        blocks.append((current_name, "\n".join(current_lines)))

    return blocks


def merge_test_file(
    output_path: Path,
    new_content: str,
    force: bool = False,
) -> MergeResult:
    """将新生成的测试内容与已有测试文件合并。

    合并策略：
    - 文件不存在或 force=True：直接写入新内容
    - 文件已存在：追加新的 describe 块，已有块不动
    """
    if not output_path.exists() or force:
        return MergeResult(
            content=new_content, merged=False, added_count=0, skipped_count=0
        )

    existing_content = output_path.read_text(encoding="utf-8")
    existing_names = _extract_names(existing_content)

    new_blocks = _split_blocks(new_content)
    total_new = len(new_blocks)
    blocks_to_add = [block for name, block in new_blocks if name not in existing_names]

    if not blocks_to_add:
        return MergeResult(
            content="",
            merged=True,
            added_count=0,
            skipped_count=total_new,
        )

    merged = existing_content.rstrip() + "\n\n" + "\n\n".join(blocks_to_add) + "\n"

    return MergeResult(
        content=merged,
        merged=True,
        added_count=len(blocks_to_add),
        skipped_count=total_new - len(blocks_to_add),
    )


def write_test_file(
    output_path: Path,
    new_content: str,
    force: bool = False,
) -> MergeResult:
    """写入测试文件（合并或覆盖）"""
    result = merge_test_file(output_path, new_content, force)
    if result.content:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.content, encoding="utf-8")
    return result
