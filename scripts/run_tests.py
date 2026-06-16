#!/usr/bin/env python3
"""智能测试运行器。

本地开发用：分析 git diff，只跑变更影响的测试目录，节省资源。
CI 环境用：全量跑（12 路并行）。

用法：
  uv run python scripts/run_tests.py                # 本地 diff 模式
  uv run python scripts/run_tests.py --all           # 全量跑
  uv run python scripts/run_tests.py --ci            # CI 模式（全量 + 无美化）
  uv run python scripts/run_tests.py --help          # 帮助
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

console = Console()

# ── 源码目录 → 测试目录映射 ──
TEST_MAP: dict[str, list[str]] = {
    "backend/core/": ["backend/tests/unit/core/"],
    "backend/plugins/auth/": [
        "backend/tests/unit/auth/",
        "backend/tests/integration/test_auth_api.py",
    ],
    "backend/plugins/blog/": [
        "backend/tests/unit/blog/",
        "backend/tests/integration/test_blog_api.py",
    ],
    "backend/plugins/oss/": [
        "backend/tests/unit/oss/",
        "backend/tests/integration/test_oss_api.py",
    ],
    "backend/plugins/github_proxy/": [
        "backend/tests/unit/github_proxy/",
        "backend/tests/integration/test_github_proxy_api.py",
    ],
    "backend/plugins/crawler/": [
        "backend/tests/unit/crawler/",
        "backend/tests/integration/test_crawler_api.py",
    ],
    "backend/plugins/cloud_integration/": [
        "backend/tests/unit/cloud_integration/",
        "backend/tests/integration/test_cloud_routes_api.py",
    ],
    "backend/plugins/monitor/": [
        "backend/tests/unit/monitor/",
        "backend/tests/integration/test_monitor_api.py",
    ],
    "backend/plugins/asset_mgmt/": [
        "backend/tests/unit/asset_mgmt/",
        "backend/tests/integration/test_asset_mgmt_api.py",
    ],
    "backend/plugins/system_monitor/": [
        "backend/tests/unit/system_monitor/",
        "backend/tests/integration/test_system_monitor_api.py",
    ],
    "backend/plugins/config_mgmt/": [
        "backend/tests/integration/test_config_mgmt_api.py"
    ],
    "frontend/src/": ["frontend/"],
    "pyproject.toml": ["backend/"],
    "frontend/package.json": ["frontend/"],
}

# 其他总是要跑的目录（core 变更了但没被上面抓到的情况）
ALWAYS_RUN = ["backend/tests/unit/core/"]


def get_changed_files(branch: str = "HEAD~1") -> list[str]:
    """获取与指定分支相比有变更的文件列表。"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", branch],
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJECT_ROOT,
        )
        files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
        return files
    except subprocess.CalledProcessError:
        console.print("[yellow]⚠  git diff 失败，回退到全量模式[/yellow]")
        return []


def get_affected_dirs(changed_files: list[str]) -> list[str]:
    """根据变更文件找出需要跑的测试目录。"""
    affected = set(ALWAYS_RUN)

    for f in changed_files:
        for src_pattern, test_dirs in TEST_MAP.items():
            if f.startswith(src_pattern):
                affected.update(test_dirs)
                break
        else:
            # 后端源文件变更但没被具体插件匹配到，跑全量
            if f.startswith("backend/") and not f.startswith("backend/tests/"):
                affected.update(ALWAYS_RUN)

    return sorted(affected)


def run_tests_sequential(
    test_dirs: list[str], extra_args: list[str]
) -> tuple[int, int]:
    """顺序执行多个测试目录，返回 (passed, failed)。"""
    total_passed = 0
    total_failed = 0
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for i, test_dir in enumerate(test_dirs):
            task = progress.add_task(
                f"[cyan]测试 {i + 1}/{len(test_dirs)}: {test_dir}", total=None
            )

            start = time.time()
            cmd = [
                "uv",
                "run",
                "pytest",
                test_dir,
                "-n",
                "auto",
                "--tb=short",
                "--no-header",
            ] + extra_args
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=PROJECT_ROOT
            )
            elapsed = time.time() - start

            progress.remove_task(task)

            passed = "passed" in result.stderr.lower() or result.returncode == 0
            if passed:
                total_passed += 1
                results.append((test_dir, "PASSED", elapsed, ""))
            else:
                total_failed += 1
                # 提取失败摘要
                summary = ""
                for line in result.stderr.split("\n"):
                    if "FAILED" in line or "ERROR" in line:
                        summary += line.strip() + "\n"
                results.append((test_dir, "FAILED", elapsed, summary))

    return results


def run_tests_all(extra_args: list[str]) -> tuple[int, int]:
    """全量跑所有测试（CI 模式）。"""
    cmd = ["uv", "run", "pytest"] + extra_args
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def print_results(results: list[tuple[str, str, float, str]]):
    """用 Rich 输出测试结果。"""
    table = Table(title="测试结果", show_header=True, header_style="bold")
    table.add_column("测试目录", style="cyan")
    table.add_column("结果", style="bold")
    table.add_column("耗时", justify="right")
    table.add_column("说明")

    all_passed = True
    for test_dir, status, elapsed, summary in results:
        style = "green" if status == "PASSED" else "red"
        status_text = Text(status, style=style)
        elapsed_str = f"{elapsed:.1f}s"
        note = summary.split("\n")[0] if summary else ""
        table.add_row(test_dir, status_text, elapsed_str, note)
        if status != "PASSED":
            all_passed = False

    console.print(table)
    return all_passed


def main():
    # ── 主逻辑 ──
    global PROJECT_ROOT
    PROJECT_ROOT = Path(__file__).parent.parent

    parser = argparse.ArgumentParser(description="智能测试运行器")
    parser.add_argument("--all", action="store_true", help="全量跑所有测试")
    parser.add_argument("--ci", action="store_true", help="CI 模式：全量 + 无美化输出")
    parser.add_argument("--diff", default="HEAD~1", help="对比分支（默认 HEAD~1）")
    parser.add_argument("extra", nargs="*", help="传给 pytest 的额外参数")

    args = parser.parse_args()
    is_ci = args.ci or os.environ.get("CI") == "true"

    if is_ci or args.all:
        console.print(Panel("[bold]全量测试[/bold]", style="blue"))
        rc = run_tests_all(args.extra)
        sys.exit(rc)

    # ── Diff 模式 ──
    console.print(Panel("[bold]智能测试 (Diff 模式)[/bold]", style="green"))

    with console.status("分析变更文件..."):
        changed = get_changed_files(args.diff)

    if not changed:
        console.print("[yellow]没有检测到文件变更，跳过测试[/yellow]")
        sys.exit(0)

    console.print(f"变更文件: [cyan]{len(changed)}[/cyan] 个")

    affected = get_affected_dirs(changed)
    if not affected:
        console.print("[yellow]变更不涉及测试目录，跳过[/yellow]")
        sys.exit(0)

    console.print(f"需运行测试: [cyan]{len(affected)}[/cyan] 个目录\n")
    for d in affected:
        console.print(f"  📁 {d}")

    console.print()
    results = run_tests_sequential(affected, args.extra)
    all_passed = print_results(results)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
