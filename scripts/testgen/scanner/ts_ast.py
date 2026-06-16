"""TypeScript AST 解析器（基于 tree-sitter）

提供比正则更精准的前端代码分析，能提取：
- 函数参数名和类型
- 正确的 HTTP 方法和 URL
- 泛型返回类型（含嵌套泛型）
- 模板字符串中的路径参数

如果 tree-sitter 不可用，自动回退到正则方案。
"""

from scripts.testgen.scanner.frontend import (
    ApiEndpoint,
)
from scripts.testgen.scanner.frontend import (
    scan_api_service as regex_scan_api,
)
from scripts.testgen.scanner.frontend import (
    scan_composable as regex_scan_composable,
)
from scripts.testgen.scanner.frontend import (
    scan_store as regex_scan_store,
)
from scripts.testgen.scanner.frontend import (
    scan_utils as regex_scan_utils,
)

try:
    import tree_sitter_typescript as ts_typescript
    from tree_sitter import Language, Parser

    _TS_LANG = Language(ts_typescript.language_typescript())
    _PARSER = Parser(_TS_LANG)
    _HAS_TS = True
except ImportError:
    _HAS_TS = False


def _parse_ts(source: str):
    if not _HAS_TS:
        return None
    return _PARSER.parse(bytes(source, "utf8"))


def _node_text(node) -> str:
    if node is None:
        return ""
    return node.text.decode("utf8")


def _find_http_call(node) -> tuple[str, str, str] | None:
    """在 AST 节点中查找 get/post/put/del/upload 调用。

    返回 (method, url, return_type)
    """
    if node.type == "call_expression":
        fn = node.child_by_field_name("function")
        if fn and fn.type == "identifier":
            method = _node_text(fn)
            if method in ("get", "post", "put", "del", "upload"):
                args = node.child_by_field_name("arguments")
                if args:
                    url_node = _find_first_arg(args)
                    url = _node_text(url_node).strip("'\"`")

                    type_args = node.child_by_field_name("type_arguments")
                    return_type = _parse_type_args(type_args) if type_args else "any"

                    return (method, url, return_type)

    for child in node.children:
        result = _find_http_call(child)
        if result:
            return result
    return None


def _find_first_arg(args_node):
    """找到 arguments 节点中的第一个实际参数（跳过括号）"""
    for child in args_node.children:
        if child.type not in ("(", ")", ",", ","):
            return child
    return None


def _parse_type_args(node) -> str:
    """从 type_arguments 节点提取类型名"""
    if node is None:
        return "any"
    text = _node_text(node)
    text = text.strip("<>")
    text = " ".join(text.split())
    if len(text) > 50:
        return "any"
    return text


def _find_url_params(url: str) -> list[str]:
    """从 URL 模板字符串中提取参数名"""
    import re

    return re.findall(r"\$\{(\w+)\}", url)


def _has_normalize_paginated(node) -> bool:
    """检查节点中是否包含 normalizePaginated 调用"""
    if node.type in ("call_expression", "member_expression"):
        text = _node_text(node)
        if "normalizePaginated" in text:
            return True
    for child in node.children:
        if _has_normalize_paginated(child):
            return True
    return False


def scan_api_service(source: str) -> list[ApiEndpoint]:
    """使用 tree-sitter AST 扫描 API Service 文件"""
    if not _HAS_TS:
        return regex_scan_api(source)

    tree = _parse_ts(source)
    if tree is None:
        return regex_scan_api(source)

    apis: list[ApiEndpoint] = []

    _walk_exports(tree.root_node, apis, source)

    if not apis:
        return regex_scan_api(source)

    return apis


def _walk_exports(node, apis: list[ApiEndpoint], source: str, depth: int = 0):
    """遍历 AST，提取 export const xxxApi = (...) => httpCall(...) 模式"""
    if depth > 20:
        return

    if node.type == "lexical_declaration":
        for child in node.children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                value_node = child.child_by_field_name("value")
                if name_node and value_node:
                    name = _node_text(name_node)
                    if name.endswith("Api"):
                        result = _extract_api(value_node, name, source)
                        if result:
                            apis.append(result)

    for child in node.children:
        _walk_exports(child, apis, source, depth + 1)


def _extract_api(value_node, name: str, source: str) -> ApiEndpoint | None:
    """从赋值表达式右侧提取 API 信息"""
    http_result = _find_http_call(value_node)
    if not http_result:
        return None

    method, url, return_type = http_result
    url_params = _find_url_params(url)
    is_paginated = _has_normalize_paginated(value_node)

    return ApiEndpoint(
        name=name,
        method=method,
        url=url,
        return_type=return_type,
        is_paginated=is_paginated,
        has_then_chain=is_paginated,
        url_params=url_params,
    )


# 暴露和新版一致的接口
scan_utils = regex_scan_utils
scan_composable = regex_scan_composable
scan_store = regex_scan_store
