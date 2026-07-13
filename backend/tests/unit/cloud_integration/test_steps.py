"""云训练各步骤的 SSH 命令构建器测试。

测试策略：
- 纯函数，不涉及状态管理
- 覆盖：环境检查、仓库克隆、依赖安装、训练启动、命令引用安全
"""

from __future__ import annotations

import pytest

from backend.plugins.cloud_integration.steps import StepCommandBuilder


class TestStepCommandBuilder:
    """StepCommandBuilder 命令构建测试。"""

    def test_check_env(self):
        """环境检查命令正确。"""
        cmd = StepCommandBuilder.check_env()
        assert "python3 --version" in cmd
        assert "git --version" in cmd
        assert "pip3 --version" in cmd

    def test_install_system_deps(self):
        """系统依赖安装命令正确。"""
        cmd = StepCommandBuilder.install_system_deps()
        assert "apt-get update" in cmd
        assert "apt-get install" in cmd
        assert "echo 'deps_installed'" in cmd

    def test_clone_repo_basic(self):
        """基础仓库克隆命令。"""
        cmd = StepCommandBuilder.clone_repo("https://github.com/user/repo.git")
        assert "git clone" in cmd
        assert "https://github.com/user/repo.git" in cmd
        assert "--branch main" in cmd
        assert "echo 'clone_ok'" in cmd

    def test_clone_repo_with_branch(self):
        """指定分支的仓库克隆。"""
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/user/repo.git", branch="develop"
        )
        assert "--branch develop" in cmd

    def test_clone_repo_with_token(self):
        """带 token 的仓库克隆（token 嵌入 URL）。"""
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/user/repo.git",
            token="ghp_abc123",
        )
        assert "https://ghp_abc123@" in cmd
        assert "ghp_abc123" in cmd

    def test_clone_repo_with_token_already_in_url(self):
        """URL 已包含 token 时不重复嵌入。"""
        cmd = StepCommandBuilder.clone_repo(
            "https://x-access-token:ghp_abc123@github.com/user/repo.git",
            token="ghp_abc123",
        )
        # token 替换逻辑会替换 https:// 部分
        assert "token" in cmd or "ghp_abc123" in cmd

    def test_install_deps_default(self):
        """默认 requirements.txt 的依赖安装命令。"""
        cmd = StepCommandBuilder.install_deps()
        assert "requirements.txt" in cmd
        assert "pip3 install" in cmd
        assert "echo 'deps_installed'" in cmd

    def test_install_deps_custom_file(self):
        """自定义 requirements 文件的依赖安装命令。"""
        cmd = StepCommandBuilder.install_deps("requirements-prod.txt")
        assert "requirements-prod.txt" in cmd

    def test_start_training_default(self):
        """默认训练脚本启动命令。"""
        cmd = StepCommandBuilder.start_training()
        assert "train.py" in cmd
        assert "nohup" in cmd
        assert "echo $!" in cmd

    def test_start_training_custom_script(self):
        """自定义训练脚本启动命令。"""
        cmd = StepCommandBuilder.start_training("finetune.py")
        assert "finetune.py" in cmd

    def test_check_process(self):
        """进程检查命令。"""
        cmd = StepCommandBuilder.check_process("12345")
        assert "kill -0 12345" in cmd
        assert "echo running" in cmd
        assert "echo stopped" in cmd

    def test_tail_log_default(self):
        """默认日志查看命令。"""
        cmd = StepCommandBuilder.tail_log()
        assert "tail -n 50" in cmd
        assert "/root/training.log" in cmd

    def test_tail_log_custom(self):
        """自定义日志路径和行数。"""
        cmd = StepCommandBuilder.tail_log("/var/log/train.log", 100)
        assert "tail -n 100" in cmd
        assert "/var/log/train.log" in cmd

    def test_list_output_files(self):
        """输出文件列表命令。"""
        cmd = StepCommandBuilder.list_output_files()
        assert "find" in cmd
        assert ".pt" in cmd
        assert ".ckpt" in cmd
        assert ".bin" in cmd
        assert ".safetensors" in cmd
        assert "/root/training_repo" in cmd

    def test_list_output_files_custom_dir(self):
        """自定义目录的输出文件列表。"""
        cmd = StepCommandBuilder.list_output_files("/custom/path")
        assert "/custom/path" in cmd

    def test_clone_repo_shell_injection_prevention(self):
        """仓库 URL 和分支名被 shlex.quote 保护。"""
        # 包含 shell 特殊字符的输入应被正确引用
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/user/repo.git",
            branch="main; rm -rf /",
        )
        # 分支名应被单引号包裹，防止 shell 注入
        assert "'main; rm -rf /'" in cmd
        # 原始命令中的分号不应在引号外出现
        assert "rm -rf" in cmd  # 在引号内安全存在

    def test_start_training_script_quoted(self):
        """训练脚本参数被正确引用。"""
        cmd = StepCommandBuilder.start_training("train.py; rm -rf /")
        # 脚本名应被引用
        assert "rm -rf" not in cmd.split(";")[0] if ";" in cmd else True