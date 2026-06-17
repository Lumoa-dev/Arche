"""测试环境检测 —— 自动识别运行环境并推荐测试策略。

为测试底座提供"眼睛"：自动判断当前运行环境并决定使用哪套测试基础设施。

检测维度：
  - Docker 容器内 → 应使用 PostgreSQL + MinIO（生产级测试）
  - WSL 环境    → 可通过 Windows 主机代理访问 PostgreSQL/MinIO
  - 裸金属       → 使用 SQLite + 本地文件系统（轻量测试）
  - 服务探测     → 检查 PostgreSQL/MinIO 端口是否可达
"""

from __future__ import annotations

import os
import platform
import socket
from pathlib import Path


# ── 缓存（避免重复检测） ──────────────────────────────────────────

_CACHE: dict[str, bool] = {}


def _reset_cache() -> None:
    """重置缓存，仅用于测试。"""
    _CACHE.clear()


# =============================================================================
# 环境类型检测
# =============================================================================


def _detect_docker() -> bool:
    """检测是否运行在 Docker 容器内。

    标准检测方式：
      1. /.dockerenv 文件存在
      2. /proc/1/cgroup 包含 "docker" 字符串（Linux only）
    """
    if Path("/.dockerenv").exists():
        return True

    try:
        cgroup = Path("/proc/1/cgroup")
        if cgroup.exists():
            content = cgroup.read_text(encoding="utf-8")
            if "docker" in content or "kubepods" in content:
                return True
    except (OSError, PermissionError):
        pass

    return False


def _detect_wsl() -> bool:
    """检测是否运行在 WSL 环境中。

    检测方式：
      1. /proc/version 包含 "microsoft" 或 "WSL"（不区分大小写）
      2. 环境变量 WSL_DISTRO_NAME 存在
    """
    if "WSL_DISTRO_NAME" in os.environ:
        return True

    try:
        version = Path("/proc/version")
        if version.exists():
            text = version.read_text(encoding="utf-8").lower()
            if "microsoft" in text or "wsl" in text:
                return True
    except (OSError, PermissionError):
        pass

    return False


def _detect_ci() -> bool:
    """检测是否运行在 CI 环境中。

    常见 CI 环境变量：CI, GITHUB_ACTIONS, GITLAB_CI, JENKINS_URL 等。
    """
    ci_indicators = [
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_URL",
        "TRAVIS",
        "CIRCLECI",
    ]
    return any(os.environ.get(var) for var in ci_indicators)


# =============================================================================
# 外部服务可用性检测
# =============================================================================


def _check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """检查指定主机的端口是否可达。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout, ConnectionRefusedError):
        return False


def _get_db_host() -> str:
    """获取数据库主机地址。

    在 Docker 容器内，其他容器通过服务名可达（由 docker-compose DNS 解析）。
    在 WSL/裸金属上，默认使用 localhost。
    """
    if in_docker():
        return os.environ.get("POSTGRES_HOST", "postgres")
    return os.environ.get("POSTGRES_HOST", "localhost")


def _get_minio_host() -> str:
    """获取 MinIO 主机地址。"""
    if in_docker():
        return os.environ.get("MINIO_HOST", "minio")
    return os.environ.get("MINIO_HOST", "localhost")


def _check_postgres() -> bool:
    """检测 PostgreSQL 是否可达。"""
    host = _get_db_host()
    env_url = os.environ.get("ARCHE_TEST_DB_URL", "")
    if env_url and env_url.startswith("postgresql"):
        # 用户显式指定了 PostgreSQL URL，信任该配置
        return True
    return _check_port(host, 5432)


def _check_minio() -> bool:
    """检测 MinIO 是否可达。"""
    host = _get_minio_host()
    # MinIO API 端口是 9000
    return _check_port(host, 9000)


# =============================================================================
# 对外接口（带缓存）
# =============================================================================


def in_docker() -> bool:
    """当前是否运行在 Docker 容器内。"""
    key = "in_docker"
    if key not in _CACHE:
        _CACHE[key] = _detect_docker()
    return _CACHE[key]


def in_wsl() -> bool:
    """当前是否运行在 WSL 环境中。"""
    key = "in_wsl"
    if key not in _CACHE:
        _CACHE[key] = _detect_wsl()
    return _CACHE[key]


def in_ci() -> bool:
    """当前是否运行在 CI 环境中。"""
    key = "in_ci"
    if key not in _CACHE:
        _CACHE[key] = _detect_ci()
    return _CACHE[key]


def postgres_available() -> bool:
    """PostgreSQL 服务是否可达。"""
    key = "pg_avail"
    if key not in _CACHE:
        _CACHE[key] = _check_postgres()
    return _CACHE[key]


def minio_available() -> bool:
    """MinIO 服务是否可达。"""
    key = "minio_avail"
    if key not in _CACHE:
        _CACHE[key] = _check_minio()
    return _CACHE[key]


def services_ready() -> bool:
    """所有外部服务（PostgreSQL + MinIO）是否就绪。

    这是测试底座的核心判断：如果外部服务就绪，走全真测试；
    否则自动降级到本地轻量测试。
    """
    return postgres_available() and minio_available()


# =============================================================================
# 测试策略推荐
# =============================================================================


def running_on_windows() -> bool:
    """检测是否在 Windows（非 WSL）上运行。"""
    return platform.system() == "Windows" and not in_wsl()


def recommended_db_url() -> str:
    """推荐测试用的 DATABASE_URL。

    优先级：
      1. 用户显式设置的 ARCHE_TEST_DB_URL
      2. 环境检测到外部服务就绪 → PostgreSQL
      3. 降级 → SQLite in-memory
    """
    explicit = os.environ.get("ARCHE_TEST_DB_URL")
    if explicit:
        return explicit

    if postgres_available():
        host = _get_db_host()
        user = os.environ.get("POSTGRES_USER", "postgres")
        password = os.environ.get("POSTGRES_PASSWORD", "postgres")
        db = os.environ.get("POSTGRES_DB", "arche_test")
        return f"postgresql+asyncpg://{user}:{password}@{host}:5432/{db}"

    # 降级到 SQLite in-memory（每个测试独立数据库）
    return ""  # 调用方应使用默认 SQLite URL


def recommended_storage() -> dict:
    """推荐测试用的 OSS 存储配置。

    返回值：
      策略名 + 配置参数字典
    """
    if minio_available():
        return {
            "strategy": "minio",
            "endpoint": f"{_get_minio_host()}:9000",
            "bucket": "arche-test",
            "secure": False,
        }

    # 降级到本地临时目录（由 conftest 的 tmp_path 提供）
    return {
        "strategy": "local",
        "storage_dir": "",  # 调用方用 pytest tmp_path 填充
    }


def describe_environment() -> str:
    """返回当前环境的可读描述，供日志和调试使用。"""
    parts = []
    if in_docker():
        parts.append("Docker")
    if in_wsl():
        parts.append("WSL")
    if in_ci():
        parts.append("CI")
    if running_on_windows():
        parts.append("Windows")

    env = " + ".join(parts) if parts else "bare metal"
    services = []
    if postgres_available():
        services.append("PostgreSQL")
    if minio_available():
        services.append("MinIO")

    services_str = ", ".join(services) if services else "none (using local fallbacks)"
    return f"Environment: {env} | Services available: {services_str}"


# =============================================================================
# WSL 桥接工具（备用）
# =============================================================================


def wsl_windows_host_ip() -> str | None:
    """获取 WSL 中 Windows 主机的 IP 地址。

    WSL 将 Windows 主机的 IP 写入 /etc/resolv.conf 的 nameserver 字段。
    可用于连接到 Windows 上运行的服务。
    """
    if not in_wsl():
        return None
    try:
        resolv = Path("/etc/resolv.conf")
        if resolv.exists():
            for line in resolv.read_text(encoding="utf-8").splitlines():
                if line.startswith("nameserver"):
                    return line.split()[1]
    except (OSError, IndexError):
        pass
    return None
