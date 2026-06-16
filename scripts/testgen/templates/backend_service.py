from pathlib import Path

from scripts.testgen.scanner.backend import ServiceClassInfo


def _mock_value_for_type(type_str: str) -> str:
    """根据 Python 类型生成 mock 值"""
    t = type_str.lower()
    if "str" in t or "string" in t:
        return '"test"'
    if "int" in t or "float" in t or "number" in t:
        return "1"
    if "bool" in t or "boolean" in t:
        return "True"
    if "uuid" in t:
        return "uuid.uuid4()"
    if "dict" in t or "list" in t:
        return "{}"
    if "none" in t or t == "none":
        return "None"
    return "None"


def _param_to_fixture(param: tuple[str, str]) -> str:
    """将方法参数转为 pytest fixture"""
    name, type_str = param
    return f"    {name}: {type_str} = {_mock_value_for_type(type_str)}"


def _asyncio_marker(is_async: bool) -> str:
    return "@pytest.mark.asyncio" if is_async else ""


def render(
    service_info: ServiceClassInfo,
    source_path: Path,
    output_path: Path,
) -> str:
    if service_info is None:
        return f"""\
import pytest

# TODO: 自动生成 - 未扫描到 Service 类，请手动补充
# 文件：{source_path.name}

def test_placeholder():
    assert True
"""

    class_name = service_info.class_name
    test_class = f"Test{class_name}"

    lines = []
    lines.append("import pytest")
    lines.append("")
    lines.append("from backend.core.container import ServiceContainer")
    lines.append("")
    lines.append("# TODO: 导入 Service 类")
    lines.append(
        f"# from backend.plugins.{source_path.parent.name}.services import {class_name}"
    )
    lines.append("")

    # 模块级函数测试
    if service_info.module_funcs:
        for func in service_info.module_funcs:
            if not func.is_public:
                continue
            lines.append(f"class Test{func.name[0].upper() + func.name[1:]}:")
            lines.append(f'    """测试模块级函数 {func.name}"""')
            lines.append("")
            mock_values = ", ".join(_mock_value_for_type(t) for _, t in func.params)
            lines.append("    def test_basic(self):")
            lines.append(f"        result = {func.name}({mock_values})")
            lines.append("        assert result is not None")
            lines.append("")

    # Service 类测试
    public_methods = [m for m in service_info.methods if m.is_public]
    if not public_methods:
        lines.append(f"class {test_class}:")
        lines.append(f'    """{class_name} 测试"""')
        lines.append("")
        lines.append("    def test_placeholder(self):")
        lines.append("        assert True")
        lines.append("")
    else:
        lines.append(f"class {test_class}:")
        lines.append(f'    """{class_name} 测试"""')
        lines.append("")

        for method in public_methods:
            marker = _asyncio_marker(method.is_async)
            mock_args = ", ".join(_mock_value_for_type(t) for _, t in method.params)

            if marker:
                lines.append(f"    {marker}")
            lines.append(
                f"    async def test_{method.name}_success(self, db_container):"
            )
            lines.append(f'        """测试 {method.name} 基本功能"""')
            lines.append(f"        service = {class_name}(db_container)")
            lines.append("")
            lines.append(f"        result = await service.{method.name}({mock_args})")
            lines.append("        assert result is not None")
            if method.return_type and method.return_type != "None":
                lines.append(f"        assert isinstance(result, {method.return_type})")
            lines.append("")

    return "\n".join(lines)
