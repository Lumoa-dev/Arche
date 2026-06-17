"""根据 git 变更自动推导测试目录。

用法：
    python scripts/test_changed.py
    python scripts/test_changed.py --run       # 实际执行 pytest
    python scripts/test_changed.py --verbose   # 显示推导结果

策略：
    1. git diff HEAD~1 --name-only 获取变更文件
    2. 提取变更路径中的插件名（backend/plugins/<name>/）
    3. 如果变更在 core/ 则跑 core + 所有插件测试
    4. 如果变更在某个插件目录，跑该插件测试 + core 测试
    5. 如果变更在多个插件，跑所有受影响的
    6. 如果没有变更或无法匹配，回退到全量测试
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def get_changed_files(base_ref: str = "HEAD~1") -> list[str]:
    """获取自 base_ref 以来的变更文件列表。"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parent.parent,
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        return []


_TEST_DIRS: dict[str, str] = {
    "core": "backend/tests/core/",
    "auth": "backend/tests/plugins/auth/",
    "blog": "backend/tests/plugins/blog/",
    "oss": "backend/tests/plugins/oss/",
    "ip_ban": "backend/tests/plugins/ip_ban/",
    "asset_mgmt": "backend/tests/plugins/asset_mgmt/",
    "cloud_integration": "backend/tests/plugins/cloud_integration/",
    "config_mgmt": "backend/tests/plugins/config_mgmt/",
    "crawler": "backend/tests/plugins/crawler/",
    "deploy_webhook": "backend/tests/plugins/deploy_webhook/",
    "github_proxy": "backend/tests/plugins/github_proxy/",
    "monitor": "backend/tests/plugins/monitor/",
    "request_log": "backend/tests/plugins/request_log/",
    "search": "backend/tests/plugins/search/",
    "system_monitor": "backend/tests/plugins/system_monitor/",
}


def resolve_test_dirs(changed_files: list[str]) -> list[str]:
    """从变更文件列表推导出需要跑的测试目录。"""
    affected: set[str] = set()

    for path in changed_files:
        # 核心层变更 → core + 所有插件
        if path.startswith("backend/core/"):
            return ["backend/tests/"]  # 全量

        # migration 变更 → core tests
        if path.startswith("backend/migrations/"):
            affected.add("backend/tests/core/")

        # 插件变更 → 对应插件测试
        if path.startswith("backend/plugins/"):
            parts = path.split("/")
            if len(parts) >= 3:
                plugin_name = parts[2]
                if plugin_name in _TEST_DIRS:
                    affected.add(_TEST_DIRS[plugin_name])

        # 测试文件本身变更 → 直接用该文件
        if path.startswith("backend/tests/"):
            full = Path(path)
            if full.is_file() and str(full).endswith(".py"):
                affected.add(str(full))
            elif full.is_dir():
                affected.add(str(full))

    if not affected:
        return []

    # 总保证跑 core 测试
    affected.add("backend/tests/core/")
    return sorted(affected)


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    should_run = "--run" in sys.argv or "-r" in sys.argv

    changed = get_changed_files()
    if not changed:
        print("无法获取 git 变更，回退到全量测试")
        print("pytest backend/tests/ -m 'not real' -q --tb=short")
        if should_run:
            subprocess.run(
                ["uv", "run", "pytest", "backend/tests/", "-m", "not real", "-q", "--tb=short"],
                check=False,
            )
        return

    if verbose:
        print(f"变更文件 ({len(changed)}):")
        for f in changed:
            print(f"  {f}")
        print()

    dirs = resolve_test_dirs(changed)
    if not dirs:
        print("无法推导测试目录（无后端变更），跳过")
        return

    pytest_args = ["uv", "run", "pytest", *dirs, "-q", "--tb=short", "-m", "not real"]

    print(f"推导出 {len(dirs)} 个测试目录:")
    for d in dirs:
        print(f"  pytest {d}")
    print()
    print(f"完整命令: {' '.join(pytest_args)}")

    if should_run:
        subprocess.run(pytest_args, check=False)
    else:
        print("\n使用 --run 参数实际执行测试")


if __name__ == "__main__":
    main()
