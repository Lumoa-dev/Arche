from pathlib import Path

from scripts.testgen.scanner.backend import RouteInfo


def render(
    routes: list[RouteInfo],
    source_path: Path,
    output_path: Path,
) -> str:
    if not routes:
        return f"""\
import pytest

# TODO: 自动生成 - 未扫描到路由定义，请手动补充
# 文件：{source_path.name}

def test_placeholder():
    assert True
"""

    lines = []
    lines.append("import pytest")
    lines.append("from httpx import AsyncClient, ASGITransport")
    lines.append("")
    lines.append("# TODO: 导入路由模块和依赖")
    lines.append("")

    # 按 router 分组
    router_groups: dict[str, list[RouteInfo]] = {}
    for r in routes:
        router_groups.setdefault(r.handler_name or "router", []).append(r)

    test_class_num = 1
    for router_name, group in router_groups.items():
        test_class = f"Test{router_name[0].upper() + router_name[1:] if router_name else f'Router{test_class_num}'}"
        test_class_num += 1

        lines.append(f"class {test_class}:")
        lines.append(f'    """{router_name} 路由集成测试"""')
        lines.append("")

        for route in group:
            test_name = f"test_{route.method}_{route.path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
            lines.append("    @pytest.mark.asyncio")
            lines.append(f"    async def {test_name}(self, client):")
            lines.append(f'        """{route.method.upper()} {route.path}"""')
            path_str = repr(route.path)
            lines.append(f"        response = await client.{route.method}({path_str})")
            lines.append("        assert response.status_code in (200, 201, 204)")
            lines.append("")

    return "\n".join(lines)
