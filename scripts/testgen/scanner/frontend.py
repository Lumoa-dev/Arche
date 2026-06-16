import re
from dataclasses import dataclass, field

# ── API Service 扫描 ──────────────────────────────────────────────


@dataclass
class ApiParam:
    name: str
    type_hint: str = "any"
    optional: bool = False


@dataclass
class ApiEndpoint:
    name: str
    method: str  # get | post | put | del | upload
    url: str
    params: list[ApiParam] = field(default_factory=list)
    return_type: str = "any"
    has_then_chain: bool = False
    is_paginated: bool = False
    url_params: list[str] = field(default_factory=list)


# 匹配 URL 中的 {param} 路径参数
URL_PARAM_PATTERN = re.compile(r"\{(\w+)\}")

# 匹配 .then(normalizePaginated) 或其他 .then 链
THEN_PATTERN = re.compile(r"\.then\s*\(")
NORMALIZE_PAGINATED_PATTERN = re.compile(r"normalizePaginated")


def scan_api_service(content: str) -> list[ApiEndpoint]:
    """扫描前端 API Service 文件，提取所有 API 端点"""
    apis: list[ApiEndpoint] = []

    # 按 export const 切分代码块，避免跨函数串扰
    blocks = re.split(r"\nexport\s+const\s+", content)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # 提取函数名
        name_match = re.match(r"(\w+Api)\s*=", block)
        if not name_match:
            continue
        name = name_match.group(1)

        # 在单个块内查找 HTTP 调用
        http_match = re.search(
            r"(get|post|put|del|upload)\s*<\s*(.+?)\s*>\s*\(\s*"
            r"['`]([^'`]+)['`]",
            block,
        )
        if not http_match:
            continue

        method = http_match.group(1)
        return_type = http_match.group(2).strip()
        url = http_match.group(3)

        url_params = URL_PARAM_PATTERN.findall(url)
        is_paginated = bool(NORMALIZE_PAGINATED_PATTERN.search(block))
        has_then = bool(THEN_PATTERN.search(block))

        apis.append(
            ApiEndpoint(
                name=name,
                method=method,
                url=url,
                return_type=_simplify_type(return_type),
                has_then_chain=has_then,
                is_paginated=is_paginated,
                url_params=url_params,
            )
        )

    return apis


def _simplify_type(raw: str) -> str:
    """简化 TypeScript 类型名"""
    raw = raw.strip()
    raw = re.sub(r"\s+", "", raw)
    raw = raw.replace("import('.*')", "any")
    if len(raw) > 40:
        return "any"
    return raw


# ── Utils 纯函数扫描 ──────────────────────────────────────────


@dataclass
class FuncInfo:
    name: str
    params: list[ApiParam] = field(default_factory=list)
    return_type: str = "unknown"
    has_comment: bool = False


# 匹配 export function xxx(...) 或 export const xxx = (...) =>
FUNC_PATTERN = re.compile(
    r"export\s+(?:function\s+|const\s+)?(\w+)\s*(?:=\s*)?"
    r"\(([^)]*)\)\s*(?::\s*([^{=>]+))?\s*(?:=>|\{)",
    re.MULTILINE,
)

TYPE_HINT_PATTERN = re.compile(r"(\w+)\s*(?:\?)?\s*(?::\s*([^,=)]+))?")


def scan_utils(content: str) -> list[FuncInfo]:
    """扫描前端工具函数文件，提取所有导出的纯函数"""
    # 过滤掉非工具函数（组件、store 等）
    _skip_keywords = ["defineComponent", "defineStore", "ref", "computed"]

    funcs: list[FuncInfo] = []
    for match in FUNC_PATTERN.finditer(content):
        name = match.group(1)
        if any(kw in name for kw in _skip_keywords):
            continue
        params_str = match.group(2)
        return_type = (match.group(3) or "unknown").strip()

        params = []
        for p in params_str.split(","):
            p = p.strip()
            if not p:
                continue
            pm = TYPE_HINT_PATTERN.match(p)
            if pm:
                pname = pm.group(1)
                ptype = (pm.group(2) or "unknown").strip()
                params.append(ApiParam(name=pname, type_hint=ptype, optional="?" in p))

        funcs.append(FuncInfo(name=name, params=params, return_type=return_type))

    return funcs


# ── Composable 扫描 ──────────────────────────────────────────


@dataclass
class ComposableInfo:
    name: str
    params: list[ApiParam] = field(default_factory=list)
    return_keys: list[str] = field(default_factory=list)


# 匹配 export const useXxx = (...) => {
COMPOSABLE_PATTERN = re.compile(
    r"export\s+(?:const\s+)?(use\w+)\s*(?:<[^>]*>)?\s*=\s*"
    r"\(([^)]*)\)\s*(?::\s*[^{]+)?\s*=>\s*\{",
    re.MULTILINE,
)

# 匹配 return { ... } 的内容
RETURN_KEYS_PATTERN = re.compile(r"return\s*\{([^}]+)\}", re.MULTILINE | re.DOTALL)


def scan_composable(content: str) -> ComposableInfo | None:
    """扫描前端 Composable 文件，提取组合式函数信息"""
    match = COMPOSABLE_PATTERN.search(content)
    if not match:
        return None

    name = match.group(1)
    params_str = match.group(2)

    params = []
    for p in params_str.split(","):
        p = p.strip()
        if not p:
            continue
        pm = TYPE_HINT_PATTERN.match(p)
        if pm:
            pname = pm.group(1)
            ptype = (pm.group(2) or "unknown").strip()
            params.append(ApiParam(name=pname, type_hint=ptype, optional="?" in p))

    return_keys = []
    rm = RETURN_KEYS_PATTERN.search(content)
    if rm:
        for k in rm.group(1).split(","):
            k = k.strip().split(":")[0].strip()
            if k:
                return_keys.append(k)

    return ComposableInfo(name=name, params=params, return_keys=return_keys)


# ── Store 扫描 ──────────────────────────────────────────


@dataclass
class StoreInfo:
    store_id: str
    state_keys: list[str] = field(default_factory=list)
    actions: list[FuncInfo] = field(default_factory=list)
    has_persist: bool = False


# 匹配 defineStore('xxx', () => {
STORE_PATTERN = re.compile(
    r"defineStore\s*\(\s*'(\w+)'",
    re.MULTILINE,
)

# 匹配 const xxx = ref(...) 状态声明
REF_PATTERN = re.compile(r"const\s+(\w+)\s*=\s*ref")

# 匹配 const xxx = async (...) => { 或 const xxx = (...) => {
ACTION_PATTERN = re.compile(
    r"const\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*(?::\s*[^{]+)?\s*(?:=>|\{)"
)

# 匹配 persist 配置
PERSIST_PATTERN = re.compile(r"persist\s*:")


def scan_store(content: str) -> StoreInfo | None:
    """扫描前端 Pinia Store 文件，提取 Store 信息"""
    store_match = STORE_PATTERN.search(content)
    if not store_match:
        return None

    store_id = store_match.group(1)

    state_keys = [m.group(1) for m in REF_PATTERN.finditer(content)]

    _skip_action_keywords = ["route", "router", "store"]
    actions = []
    for m in ACTION_PATTERN.finditer(content):
        name = m.group(1)
        if any(kw in name for kw in _skip_action_keywords):
            continue
        params_str = m.group(2)
        params = []
        for p in params_str.split(","):
            p = p.strip()
            if not p or p == "self":
                continue
            pm = TYPE_HINT_PATTERN.match(p)
            if pm:
                pname = pm.group(1)
                ptype = (pm.group(2) or "unknown").strip()
                params.append(ApiParam(name=pname, type_hint=ptype, optional="?" in p))
        actions.append(FuncInfo(name=name, params=params))

    has_persist = bool(PERSIST_PATTERN.search(content))

    return StoreInfo(
        store_id=store_id,
        state_keys=state_keys,
        actions=actions,
        has_persist=has_persist,
    )
