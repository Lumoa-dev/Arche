from pathlib import Path

import typer

app = typer.Typer(
    name="testgen",
    help="基于代码扫描的测试代码生成器",
    no_args_is_help=True,
)


@app.callback()
def callback():
    pass


@app.command("gen")
def generate(
    source: str = typer.Argument(
        ..., help="源文件路径，如 frontend/src/services/api/blog.ts"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="输出路径，默认自动推断"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="仅输出生成的代码，不写入文件"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="覆盖已存在的测试文件"),
):
    """根据源码文件自动生成测试代码"""
    source_path = Path(source).resolve()

    if not source_path.exists():
        typer.echo(f"错误：文件不存在 - {source_path}", err=True)
        raise typer.Exit(code=1)

    from scripts.testgen.orchestrator import detect_type, generate_test
    from scripts.testgen.writer import write_test_file

    file_type = detect_type(source_path)
    typer.echo(f"检测到文件类型：{file_type}")

    result = generate_test(source_path, file_type)

    if dry_run:
        typer.echo("=" * 60)
        typer.echo(f"生成路径：{result.output_path}")
        typer.echo("=" * 60)
        typer.echo(result.content)
        return

    output_path = Path(output) if output else result.output_path
    write_result = write_test_file(output_path, result.content, force)

    if write_result.content:
        if write_result.merged:
            typer.echo(
                f"测试文件已合并：{output_path} "
                f"（新增 {write_result.added_count} 个测试, "
                f"跳过 {write_result.skipped_count} 个已有测试）"
            )
        else:
            typer.echo(f"测试文件已生成：{output_path}")
    else:
        typer.echo(f"无需更新：{output_path}（所有测试块已存在）")


@app.command("batch")
def batch_generate(
    directory: str = typer.Argument(
        ..., help="源码目录，如 frontend/src/services/api/"
    ),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="输出目录"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="仅预览"),
    force: bool = typer.Option(False, "--force", "-f", help="覆盖已有文件"),
):
    """批量生成整个目录的测试代码"""
    dir_path = Path(directory).resolve()
    if not dir_path.is_dir():
        typer.echo(f"错误：目录不存在 - {dir_path}", err=True)
        raise typer.Exit(code=1)

    from scripts.testgen.orchestrator import (
        SUPPORTED_PATTERNS,
        detect_type,
        generate_test,
    )
    from scripts.testgen.writer import write_test_file

    matched = []
    for pattern in SUPPORTED_PATTERNS.values():
        for f in dir_path.rglob(pattern):
            file_type = detect_type(f)
            if file_type:
                matched.append((f, file_type))

    if not matched:
        typer.echo("未找到可生成测试的源码文件")
        return

    typer.echo(f"找到 {len(matched)} 个可处理的文件")
    for source_path, file_type in matched:
        rel = source_path.relative_to(Path.cwd())
        typer.echo(f"  [{file_type}] {rel}")
        result = generate_test(source_path, file_type)

        if dry_run:
            typer.echo(f"  → {result.output_path}")
            continue

        output_path = (
            Path(output_dir) / result.output_path.name
            if output_dir
            else result.output_path
        )
        write_result = write_test_file(output_path, result.content, force)

        if write_result.content:
            if write_result.added_count > 0:
                typer.echo(
                    f"  已生成：{output_path}（新增 {write_result.added_count} 个）"
                )
            else:
                typer.echo(f"  已生成：{output_path}")
        elif write_result.skipped_count > 0:
            typer.echo(
                f"  跳过：{output_path.name}（{write_result.skipped_count} 个测试已存在）"
            )
        else:
            typer.echo(f"  跳过：{output_path.name}（已存在）")

    typer.echo("批量生成完成！")


@app.command("clear-cache")
def clear_cache(
    source: str | None = typer.Option(
        None, "--source", "-s", help="仅清除指定源文件的缓存"
    ),
    file_type: str | None = typer.Option(
        None, "--type", "-t", help="仅清除指定类型的缓存"
    ),
):
    """清除 AST 扫描缓存"""
    from scripts.testgen.cache import clear

    source_path = Path(source).resolve() if source else None
    clear(source_path, file_type)
    typer.echo("缓存已清除")


@app.command("learn")
def learn(
    force: bool = typer.Option(False, "--force", "-f", help="强制重新学习"),
):
    """从现有测试文件中学习断言模式"""
    from .cache import load as cache_load
    from .cache import save as cache_save
    from .learner import learn_from_tests

    root = Path.cwd()
    learned = None if force else cache_load(root / ".patterns", "learned")
    if learned is None:
        learned = learn_from_tests(root)
        cache_save(root / ".patterns", "learned", learned)

    assertions = learned.api_assertions
    if hasattr(assertions, "__dict__"):
        assertions = assertions.__dict__
    total_patterns = sum(len(v) for v in assertions.values())
    typer.echo(
        f"学习完成：分析了 {learned.total_tests_analyzed} 个现有测试文件，"
        f"提取了 {total_patterns} 条断言模式"
    )
    for module, pats in sorted(assertions.items()):
        typer.echo(f"  {module}: {len(pats)} 条断言")


@app.command("list-templates")
def list_templates():
    """列出支持的文件类型和对应的模板"""
    from scripts.testgen.orchestrator import FILE_TYPE_LABELS, SUPPORTED_PATTERNS

    typer.echo("支持的文件类型：")
    for type_id, pattern in SUPPORTED_PATTERNS.items():
        label = FILE_TYPE_LABELS.get(type_id, type_id)
        typer.echo(f"  {type_id:20s} {label}")
        typer.echo(f"    {'匹配模式:':12s} {pattern}")
        typer.echo()
