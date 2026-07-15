"""部署 Webhook 插件 单元测试。

测试：
- Token 验证逻辑（安全关键）
- 部署脚本执行（subprocess 调用）
- 错误处理路径（脚本不存在、超时、非零退出码）
- 输入验证
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

import subprocess

from backend.plugins import deploy_webhook as dw


class TestDeployRequest:
    """DeployRequest 模型验证。"""

    def test_valid_token(self):
        """有效的 token 应通过验证。"""
        req = dw.DeployRequest(token="my-token")
        assert req.token == "my-token"

    def test_empty_token(self):
        """空字符串也是合法 token（但后端会拒绝）。"""
        req = dw.DeployRequest(token="")
        assert req.token == ""


class TestGetDeployScript:
    """获取部署脚本路径测试。"""

    def test_returns_configured_path(self, monkeypatch):
        """应返回配置的脚本路径。"""
        monkeypatch.setattr(
            dw, "config_manager", MagicMock(get=MagicMock(return_value="/custom/deploy.sh"))
        )
        assert dw._get_deploy_script() == "/custom/deploy.sh"

    def test_fallback_to_default(self, monkeypatch):
        """配置返回 None 时应回退到默认路径。"""
        monkeypatch.setattr(
            dw, "config_manager", MagicMock(get=MagicMock(return_value=None))
        )
        assert dw._get_deploy_script() == "/home/admin/arche/deploy.sh"


class TestTriggerDeploy:
    """部署触发接口测试。"""

    async def test_invalid_token_returns_401(self):
        """token 不匹配应返回 401。"""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            dw, "config_manager", MagicMock(get=MagicMock(return_value="correct-token"))
        )
        request = dw.DeployRequest(token="wrong-token")

        with pytest.raises(HTTPException) as exc:
            await dw.trigger_deploy(request)
        assert exc.value.status_code == 401

        monkeypatch.undo()

    async def test_missing_token_in_config_returns_401(self):
        """配置中无 token 时应拒绝所有请求。"""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            dw, "config_manager", MagicMock(get=MagicMock(return_value=""))
        )
        request = dw.DeployRequest(token="any-token")

        with pytest.raises(HTTPException) as exc:
            await dw.trigger_deploy(request)
        assert exc.value.status_code == 401

        monkeypatch.undo()

    async def test_script_not_found_returns_500(self):
        """部署脚本不存在时应返回 500。"""
        with (
            patch.object(dw, "config_manager") as mock_cfg,
            patch("os.path.isfile") as mock_isfile,
        ):
            mock_cfg.get.return_value = "correct-token"
            mock_isfile.return_value = False

            with pytest.raises(HTTPException) as exc:
                await dw.trigger_deploy(dw.DeployRequest(token="correct-token"))
            assert exc.value.status_code == 500
            assert "not found" in exc.value.detail

    async def test_successful_deploy(self):
        """部署成功应返回 status 为 success。"""
        with (
            patch.object(dw, "config_manager") as mock_cfg,
            patch("os.path.isfile") as mock_isfile,
            patch.object(dw, "asyncio") as mock_asyncio,
        ):
            mock_cfg.get.return_value = "correct-token"
            mock_isfile.return_value = True
            mock_asyncio.to_thread = AsyncMock(
                return_value=(0, "Deploy OK\n", "")
            )

            result = await dw.trigger_deploy(dw.DeployRequest(token="correct-token"))
            assert result["status"] == "success"
            assert "Deploy OK" in result["stdout"]

    async def test_failed_deploy_returns_failure_status(self):
        """脚本返回非零退出码时应返回失败状态。"""
        with (
            patch.object(dw, "config_manager") as mock_cfg,
            patch("os.path.isfile") as mock_isfile,
            patch.object(dw, "asyncio") as mock_asyncio,
        ):
            mock_cfg.get.return_value = "correct-token"
            mock_isfile.return_value = True
            mock_asyncio.to_thread = AsyncMock(
                return_value=(1, "stdout", "error: something failed")
            )

            result = await dw.trigger_deploy(dw.DeployRequest(token="correct-token"))
            assert result["status"] == "failed"
            assert result["returncode"] == 1
            assert "error: something failed" in result["stderr"]

    async def test_stdout_stderr_are_truncated(self):
        """stdout 和 stderr 应被截断到合理长度。"""
        with (
            patch.object(dw, "config_manager") as mock_cfg,
            patch("os.path.isfile") as mock_isfile,
            patch.object(dw, "asyncio") as mock_asyncio,
        ):
            mock_cfg.get.return_value = "correct-token"
            mock_isfile.return_value = True
            long_stdout = "line\n" * 5000
            long_stderr = "err\n" * 3000
            mock_asyncio.to_thread = AsyncMock(
                return_value=(1, long_stdout, long_stderr)
            )

            result = await dw.trigger_deploy(dw.DeployRequest(token="correct-token"))
            assert len(result["stdout"]) <= 2000
            assert len(result["stderr"]) <= 1000


class TestRunScript:
    """_run_script 底层函数测试。"""

    def test_run_script_success(self, monkeypatch):
        """脚本成功执行应返回 0 退出码。"""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "success"
        mock_proc.stderr = ""
        monkeypatch.setattr(
            dw, "subprocess", MagicMock(run=MagicMock(return_value=mock_proc))
        )

        rc, stdout, stderr = dw._run_script()
        assert rc == 0
        assert stdout == "success"

    def test_run_script_failure(self, monkeypatch):
        """脚本失败应返回非零退出码。"""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "error"
        monkeypatch.setattr(
            dw, "subprocess", MagicMock(run=MagicMock(return_value=mock_proc))
        )

        rc, stdout, stderr = dw._run_script()
        assert rc == 1
        assert stderr == "error"

    def test_run_script_timeout(self, monkeypatch):
        """脚本超时应传播异常。"""
        monkeypatch.setattr(
            dw,
            "subprocess",
            MagicMock(
                run=MagicMock(side_effect=subprocess.TimeoutExpired(cmd="bash", timeout=300))
            ),
        )

        with pytest.raises(subprocess.TimeoutExpired):
            dw._run_script()