import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

CACHE_DIR = Path(".testgen-cache")


def _source_hash(path: Path) -> str:
    """计算源文件的快速哈希（mtime + size 组合，无需读内容）"""
    try:
        stat = path.stat()
        raw = f"{path}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    except OSError:
        return ""


def _dict_to_obj(obj: Any) -> Any:
    """递归地将 dict 转为 SimpleNamespace，确保 .attr 访问模式兼容"""
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _dict_to_obj(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_dict_to_obj(x) for x in obj]
    return obj


def _cache_path(source_path: Path, file_type: str) -> Path:
    rel = source_path.relative_to(source_path.anchor)
    key = rel.as_posix().replace("/", "_").replace(":", "_")
    return CACHE_DIR / file_type / f"{key}.json"


def _find_project_root(path: Path) -> Path:
    for parent in [path] + list(path.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return path.parent


def load(source_path: Path, file_type: str) -> Any | None:
    """从缓存加载扫描结果。源文件未变化时返回缓存数据，否则返回 None。"""
    root = _find_project_root(source_path)
    cache_file = root / _cache_path(source_path, file_type)

    if not cache_file.exists():
        return None

    try:
        entry = json.loads(cache_file.read_text(encoding="utf-8"))
        current_hash = _source_hash(source_path)
        if entry.get("source_hash") == current_hash:
            return _dict_to_obj(entry.get("result"))
    except (json.JSONDecodeError, KeyError):
        pass

    return None


def save(source_path: Path, file_type: str, result: Any) -> None:
    """保存扫描结果到缓存。"""
    root = _find_project_root(source_path)
    cache_file = root / _cache_path(source_path, file_type)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "source_hash": _source_hash(source_path),
        "result": _dataclass_to_dict(result),
    }
    cache_file.write_text(
        json.dumps(entry, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def clear(source_path: Path | None = None, file_type: str | None = None) -> None:
    """清除缓存。可以按路径或类型过滤。"""
    root = _find_project_root(source_path or Path.cwd())

    if source_path and file_type:
        cache_file = root / _cache_path(source_path, file_type)
        cache_file.unlink(missing_ok=True)
    elif file_type:
        dir_path = root / CACHE_DIR / file_type
        if dir_path.exists():
            import shutil

            shutil.rmtree(dir_path)
    else:
        dir_path = root / CACHE_DIR
        if dir_path.exists():
            import shutil

            shutil.rmtree(dir_path)


def _dataclass_to_dict(obj: Any) -> Any:
    """递归地将 dataclass 对象转为可 JSON 序列化的 dict。"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_dataclass_to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        return {
            f.name: _dataclass_to_dict(getattr(obj, f.name))
            for f in obj.__dataclass_fields__.values()
        }
    return str(obj)
