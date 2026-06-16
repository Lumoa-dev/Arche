import ast
from dataclasses import dataclass, field


@dataclass
class MethodInfo:
    name: str
    is_async: bool
    params: list[tuple[str, str]] = field(default_factory=list)
    return_type: str = "None"
    docstring: str = ""
    is_public: bool = True


@dataclass
class ServiceClassInfo:
    class_name: str
    methods: list[MethodInfo] = field(default_factory=list)
    module_funcs: list[MethodInfo] = field(default_factory=list)
    container_deps: list[str] = field(default_factory=list)


@dataclass
class RouteInfo:
    method: str  # get | post | put | delete
    path: str
    handler_name: str
    is_async: bool = True


def _parse_type_annotation(node) -> str:
    """将 AST 类型注解节点转为字符串"""
    if node is None:
        return "None"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Subscript):
        value = _parse_type_annotation(node.value)
        if isinstance(node.slice, ast.Tuple):
            slice_str = ", ".join(_parse_type_annotation(e) for e in node.slice.elts)
            return f"{value}[{slice_str}]"
        if isinstance(node.slice, ast.Name):
            return f"{value}[{node.slice.id}]"
        return f"{value}[{_parse_type_annotation(node.slice)}]"
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Attribute):
        return f"{_parse_type_annotation(node.value)}.{node.attr}"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _parse_type_annotation(node.left)
        right = _parse_type_annotation(node.right)
        return f"{left} | {right}"
    return "any"


def _extract_return_type(func_def: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """提取函数返回类型"""
    if func_def.returns:
        return _parse_type_annotation(func_def.returns)
    return "None"


def _extract_params(
    func_def: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[str, str]]:
    """提取函数参数列表"""
    params = []
    for i, arg in enumerate(func_def.args.args):
        if i == 0 and arg.arg == "self":
            continue
        type_str = _parse_type_annotation(arg.annotation) if arg.annotation else "any"
        params.append((arg.arg, type_str))

    # 处理默认参数
    defaults_start = len(func_def.args.args) - len(func_def.args.defaults)
    for i, default in enumerate(func_def.args.defaults):
        idx = defaults_start + i
        val = _default_value_str(default)
        if idx < len(params) and idx > 0:
            param_name, param_type = params[idx - 1]
            params[idx - 1] = (param_name, f"{param_type} = {val}")
        elif idx < len(params):
            param_name, param_type = params[idx]
            params[idx] = (param_name, f"{param_type} = {val}")

    return params


def _default_value_str(node) -> str:
    """将 AST 默认值节点转为可读的字符串"""
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.List):
        return "[]"
    if isinstance(node, ast.Dict):
        return "{}"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return f"-{_default_value_str(node.operand)}"
    return "..."


def _extract_container_deps(tree: ast.Module) -> list[str]:
    """提取从 container 中获取的依赖"""
    deps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "container"
                ):
                    if node.args:
                        if isinstance(node.args[0], ast.Constant):
                            deps.append(str(node.args[0].value))
    return list(set(deps))


def scan_service(content: str) -> ServiceClassInfo | None:
    """扫描后端 Service 类，提取类和方法信息"""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None

    service_info = None
    module_funcs = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    is_async = isinstance(item, ast.AsyncFunctionDef)
                    methods.append(
                        MethodInfo(
                            name=item.name,
                            is_async=is_async,
                            params=_extract_params(item),
                            return_type=_extract_return_type(item),
                            docstring=ast.get_docstring(item) or "",
                            is_public=not item.name.startswith("_"),
                        )
                    )

            container_deps = _extract_container_deps(tree)
            service_info = ServiceClassInfo(
                class_name=node.name,
                methods=methods,
                container_deps=container_deps,
            )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_async = isinstance(node, ast.AsyncFunctionDef)
            module_funcs.append(
                MethodInfo(
                    name=node.name,
                    is_async=is_async,
                    params=_extract_params(node),
                    return_type=_extract_return_type(node),
                    docstring=ast.get_docstring(node) or "",
                    is_public=not node.name.startswith("_"),
                )
            )

    if service_info:
        service_info.module_funcs = module_funcs

    return service_info


def scan_routes(content: str) -> list[RouteInfo]:
    """扫描后端路由文件，提取路由定义"""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    routes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in (
                "get",
                "post",
                "put",
                "delete",
                "patch",
            ):
                method = node.func.attr
                path = ""
                if node.args and isinstance(node.args[0], ast.Constant):
                    path = node.args[0].value

                handler_name = ""
                if isinstance(node.func.value, ast.Name):
                    handler_name = node.func.value.id

                routes.append(
                    RouteInfo(method=method, path=path, handler_name=handler_name)
                )

    return routes
