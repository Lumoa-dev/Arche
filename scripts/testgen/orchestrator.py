from dataclasses import dataclass
from pathlib import Path

from scripts.testgen.cache import load as cache_load
from scripts.testgen.cache import save as cache_save
from scripts.testgen.learner import enhance_with_patterns, learn_from_tests

SUPPORTED_PATTERNS = {
    "frontend_api": "services/api/*.ts",
    "frontend_utils": "utils/*.ts",
    "frontend_composable": "composables/use*.ts",
    "frontend_store": "store/modules/*.ts",
    "backend_service": "**/services.py",
    "backend_routes": "**/routes.py",
}

FILE_TYPE_LABELS = {
    "frontend_api": "前端 API Service",
    "frontend_utils": "前端工具函数",
    "frontend_composable": "前端组合式函数",
    "frontend_store": "前端状态管理 Store",
    "backend_service": "后端 Service 层",
    "backend_routes": "后端路由层",
}


def _name_with_test_suffix(p: Path) -> str:
    return p.stem + ".test.ts"


def _name_backend_test(p: Path) -> str:
    return f"test_{p.parent.name}_{p.stem}.py"


OUTPUT_PATH_MAP = {
    "frontend_api": (
        "frontend/src/tests/services/api",
        _name_with_test_suffix,
    ),
    "frontend_utils": ("frontend/src/tests/utils", _name_with_test_suffix),
    "frontend_composable": ("frontend/src/tests/composables", _name_with_test_suffix),
    "frontend_store": ("frontend/src/tests/store/modules", _name_with_test_suffix),
    "backend_service": (
        "backend/tests/unit",
        _name_backend_test,
    ),
    "backend_routes": (
        "backend/tests/integration",
        _name_backend_test,
    ),
}

DETECT_RULES = [
    ("services/api/", "frontend_api"),
    ("utils/", "frontend_utils"),
    ("composables/", "frontend_composable"),
    ("store/modules/", "frontend_store"),
]


@dataclass
class GenerateResult:
    content: str
    output_path: Path
    file_type: str


def detect_type(source_path: Path) -> str | None:
    """根据文件路径推断文件类型"""
    source_str = source_path.as_posix()

    for keyword, file_type in DETECT_RULES:
        if keyword in source_str:
            return file_type

    # 后端文件通过文件名匹配
    name = source_path.name
    if name == "services.py":
        return "backend_service"
    if name == "routes.py":
        return "backend_routes"

    return None


def infer_output_path(source_path: Path, file_type: str) -> Path:
    """自动推断测试文件的输出路径"""
    if file_type not in OUTPUT_PATH_MAP:
        base_dir = source_path.parent
        return base_dir / f"test_{source_path.stem}.py"

    base_rel, namer = OUTPUT_PATH_MAP[file_type]
    root = _find_project_root(source_path)
    return root / base_rel / namer(source_path)


def _find_project_root(path: Path) -> Path:
    """向上查找项目根目录（含 .git 或 pyproject.toml 的目录）"""
    for parent in [path] + list(path.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return path.parent


def generate_test(source_path: Path, file_type: str) -> GenerateResult:
    """扫描源码并生成测试代码（带缓存）"""
    source_content = source_path.read_text(encoding="utf-8")
    output_path = infer_output_path(source_path, file_type)

    if file_type == "frontend_api":
        from scripts.testgen.scanner.ts_ast import scan_api_service
        from scripts.testgen.templates.frontend_api import render

        apis = cache_load(source_path, file_type)
        if apis is None:
            apis = scan_api_service(source_content)
            cache_save(source_path, file_type, apis)
        content = render(apis, source_path.stem)
    elif file_type == "frontend_utils":
        from scripts.testgen.scanner.frontend import scan_utils
        from scripts.testgen.templates.frontend_utils import render

        funcs = cache_load(source_path, file_type)
        if funcs is None:
            funcs = scan_utils(source_content)
            cache_save(source_path, file_type, funcs)
        content = render(funcs, source_path.stem)
    elif file_type == "frontend_composable":
        from scripts.testgen.scanner.frontend import scan_composable
        from scripts.testgen.templates.frontend_composable import render

        composable = cache_load(source_path, file_type)
        if composable is None:
            composable = scan_composable(source_content)
            if composable:
                cache_save(source_path, file_type, composable)
        content = render(composable, source_path.stem)
    elif file_type == "frontend_store":
        from scripts.testgen.scanner.frontend import scan_store
        from scripts.testgen.templates.frontend_store import render

        store_info = cache_load(source_path, file_type)
        if store_info is None:
            store_info = scan_store(source_content)
            if store_info:
                cache_save(source_path, file_type, store_info)
        content = render(store_info, source_path.stem)
    elif file_type == "backend_service":
        from scripts.testgen.scanner.backend import scan_service
        from scripts.testgen.templates.backend_service import render

        service_info = cache_load(source_path, file_type)
        if service_info is None:
            service_info = scan_service(source_content)
            if service_info:
                cache_save(source_path, file_type, service_info)
        content = render(service_info, source_path, output_path)
    elif file_type == "backend_routes":
        from scripts.testgen.scanner.backend import scan_routes
        from scripts.testgen.templates.backend_routes import render

        routes_info = cache_load(source_path, file_type)
        if routes_info is None:
            routes_info = scan_routes(source_content)
            cache_save(source_path, file_type, routes_info)
        content = render(routes_info, source_path, output_path)
    else:
        content = _fallback_generate(source_content, source_path)

    # 用学习到的模式增强生成内容
    if file_type in ("frontend_api", "frontend_utils"):
        root = _find_project_root(source_path)
        learned = cache_load(root / ".patterns", "learned")
        if learned is None:
            learned = learn_from_tests(root)
            cache_save(root / ".patterns", "learned", learned)
        # 缓存恢复后 api_assertions 是 SimpleNamespace，转回 dict
        if hasattr(learned.api_assertions, "__dict__"):
            learned.api_assertions = learned.api_assertions.__dict__
        content = enhance_with_patterns(content, learned, source_path.stem)

    return GenerateResult(content=content, output_path=output_path, file_type=file_type)


def _fallback_generate(content: str, source_path: Path) -> str:
    """兜底生成：无法识别类型时生成简单占位"""
    name = source_path.stem
    return f"""import {{ describe, it, expect }} from 'vitest'

// TODO: 自动生成的测试骨架 - {source_path.name}
// 当前文件类型暂不支持自动分析，请手动补充测试

describe('{name}', () => {{
  it('待完善', () => {{
    expect(true).toBe(true)
  }})
}})
"""
