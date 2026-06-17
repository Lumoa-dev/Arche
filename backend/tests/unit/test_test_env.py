"""环境感知底座测试 —— 验证 test_env 检测逻辑正确性。

注意：这些测试不依赖真实 Docker/WSL 环境。
Docker/WSL 检测通过模拟文件系统和环境变量来验证。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# ============================================================================
# Docker 检测
# ============================================================================


class TestDetectDocker:
    """Docker 容器检测逻辑测试。"""

    def test_dockerenv_file_exists(self, monkeypatch):
        """/.dockerenv 文件存在 → 判定为 Docker。"""
        from backend.tests import test_env

        monkeypatch.setattr(Path, "exists", lambda self: str(self) == "/.dockerenv")
        monkeypatch.setattr(test_env, "_detect_docker", lambda: True)
        test_env._reset_cache()
        assert test_env.in_docker() is True

    def test_dockerenv_not_exists(self, monkeypatch):
        """/.dockerenv 不存在且 cgroup 无 docker → 非 Docker。"""
        from backend.tests import test_env

        def fake_exists(path):
            return False

        monkeypatch.setattr(Path, "exists", fake_exists)
        monkeypatch.setattr(test_env, "_detect_docker", lambda: False)
        test_env._reset_cache()
        assert test_env.in_docker() is False


# ============================================================================
# WSL 检测
# ============================================================================


class TestDetectWSL:
    """WSL 环境检测逻辑测试。"""

    def test_wsl_distro_env(self, monkeypatch):
        """WSL_DISTRO_NAME 环境变量存在 → 判定为 WSL。"""
        from backend.tests import test_env

        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        monkeypatch.setattr(test_env, "_detect_wsl", lambda: True)
        test_env._reset_cache()
        assert test_env.in_wsl() is True

    def test_no_wsl_indicators(self, monkeypatch):
        """无 WSL 指示器 → 非 WSL。"""
        from backend.tests import test_env

        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        monkeypatch.setattr(test_env, "_detect_wsl", lambda: False)
        test_env._reset_cache()
        assert test_env.in_wsl() is False


# ============================================================================
# CI 检测
# ============================================================================


class TestDetectCI:
    """CI 环境检测逻辑测试。"""

    def test_github_actions(self, monkeypatch):
        """GITHUB_ACTIONS=true → 判定为 CI。"""
        from backend.tests import test_env

        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        test_env._reset_cache()
        assert test_env.in_ci() is True

    def test_ci_env(self, monkeypatch):
        """CI=true → 判定为 CI。"""
        from backend.tests import test_env

        monkeypatch.setenv("CI", "true")
        test_env._reset_cache()
        assert test_env.in_ci() is True

    def test_no_ci_indicators(self, monkeypatch):
        """无任何 CI 环境变量 → 非 CI。"""
        from backend.tests import test_env

        for var in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"]:
            monkeypatch.delenv(var, raising=False)
        test_env._reset_cache()
        assert test_env.in_ci() is False


# ============================================================================
# 服务端口检测
# ============================================================================


class TestServiceDetection:
    """外部服务端口检测逻辑测试。"""

    def test_postgres_available_via_env(self, monkeypatch):
        """ARCHE_TEST_DB_URL 指定 PostgreSQL → 认为可用。"""
        from backend.tests import test_env

        monkeypatch.setenv("ARCHE_TEST_DB_URL", "postgresql+asyncpg://localhost:5432/test")
        test_env._reset_cache()
        assert test_env.postgres_available() is True

    def test_postgres_not_available(self, monkeypatch):
        """无 PostgreSQL 端口响应 → 不可用。"""
        from backend.tests import test_env

        monkeypatch.delenv("ARCHE_TEST_DB_URL", raising=False)

        def fake_check_port(host, port, timeout=2.0):
            return False

        monkeypatch.setattr(test_env, "_check_port", fake_check_port)
        test_env._reset_cache()
        assert test_env.postgres_available() is False


# ============================================================================
# 推荐策略
# ============================================================================


class TestRecommendedStrategy:
    """测试推荐策略逻辑。"""

    def test_recommended_db_url_explicit(self, monkeypatch):
        """显式设置 ARCHE_TEST_DB_URL → 返回该 URL。"""
        from backend.tests import test_env

        monkeypatch.setenv("ARCHE_TEST_DB_URL", "postgresql+asyncpg://user:pass@host:5432/db")
        assert test_env.recommended_db_url() == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_recommended_db_url_fallback(self, monkeypatch):
        """无显式 URL 且 PostgreSQL 不可用 → 返回空字符串。"""
        from backend.tests import test_env

        monkeypatch.delenv("ARCHE_TEST_DB_URL", raising=False)
        monkeypatch.setattr(test_env, "postgres_available", lambda: False)
        assert test_env.recommended_db_url() == ""

    def test_recommended_storage_local(self, monkeypatch):
        """MinIO 不可用 → 推荐 local 策略。"""
        from backend.tests import test_env

        monkeypatch.setattr(test_env, "minio_available", lambda: False)
        result = test_env.recommended_storage()
        assert result["strategy"] == "local"
        assert result["storage_dir"] == ""

    def test_describe_environment(self, monkeypatch):
        """环境描述不崩溃。"""
        from backend.tests import test_env

        test_env._reset_cache()
        desc = test_env.describe_environment()
        assert isinstance(desc, str)
        assert desc.startswith("Environment:")
