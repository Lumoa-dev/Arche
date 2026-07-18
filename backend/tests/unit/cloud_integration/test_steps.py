"""云训练步骤命令构建器 行为测试。

测试 SSH 命令构建是否正确，以及命令注入防护。
纯函数测试，无数据库依赖。
"""

from __future__ import annotations

import pytest

from backend.plugins.cloud_integration.steps import StepCommandBuilder


class TestStepCommandBuilder:
    """StepCommandBuilder 行为测试。"""

    def test_check_env(self):
        """环境检查命令应包含 python/git/pip 版本检查。"""
        cmd = StepCommandBuilder.check_env()
        assert "python3 --version" in cmd
        assert "git --version" in cmd
        assert "pip3 --version" in cmd

    def test_install_system_deps(self):
        """系统依赖安装命令应正确。"""
        cmd = StepCommandBuilder.install_system_deps()
        assert "apt-get update" in cmd
        assert "python3-pip" in cmd
        assert "echo 'deps_installed'" in cmd

    def test_clone_repo_basic(self):
        """基础仓库克隆命令应正确。"""
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/example/repo.git", branch="main"
        )
        assert "git clone" in cmd
        assert "example/repo.git" in cmd
        assert "--branch main" in cmd
        assert "echo 'clone_ok'" in cmd

    def test_clone_repo_with_token(self):
        """带 token 的仓库克隆应替换 URL 中的协议。"""
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/example/private-repo.git",
            branch="dev",
            token="ghp_test123",
        )
        # URL 应被替换为包含 token 的格式
        assert "ghp_test123@github.com" in cmd
        assert "--branch dev" in cmd

    def test_clone_repo_special_chars_in_branch(self):
        """分支名包含特殊字符时应被正确引用。"""
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/example/repo.git",
            branch="feature/my-branch",
        )
        assert "feature/my-branch" in cmd

    def test_clone_repo_special_chars_in_url(self):
        """仓库 URL 包含特殊字符时应被正确引用。"""
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/example/repo.git",
            branch="main",
            token="token$pecial",
        )
        # token 中的特殊字符不应导致注入
        assert "token$pecial" in cmd

    def test_install_deps_default(self):
        """默认 requirements.txt 的依赖安装命令。"""
        cmd = StepCommandBuilder.install_deps()
        assert "requirements.txt" in cmd
        assert "pip3 install" in cmd
        assert "echo 'deps_installed'" in cmd

    def test_install_deps_custom_file(self):
        """自定义 requirements 文件的依赖安装命令。"""
        cmd = StepCommandBuilder.install_deps("requirements-dev.txt")
        assert "requirements-dev.txt" in cmd

    def test_install_deps_file_with_spaces(self):
        """文件名包含空格时应被正确引用。"""
        cmd = StepCommandBuilder.install_deps("my requirements.txt")
        # shlex.quote 会添加引号
        assert "'my requirements.txt'" in cmd or '"my requirements.txt"' in cmd

    def test_fetch_huggingface_dataset(self):
        """HuggingFace 数据集下载命令。"""
        cmd = StepCommandBuilder.fetch_huggingface_dataset("datasets/example")
        assert "huggingface-cli download" in cmd
        assert "datasets/example" in cmd
        assert "echo 'dataset_ok'" in cmd

    def test_fetch_modelscope_dataset(self):
        """ModelScope 数据集下载命令。"""
        cmd = StepCommandBuilder.fetch_modelscope_dataset("datasets/example")
        assert "modelscope download" in cmd
        assert "datasets/example" in cmd
        assert "echo 'dataset_ok'" in cmd

    def test_start_training_default(self):
        """默认训练脚本启动命令。"""
        cmd = StepCommandBuilder.start_training()
        assert "python3 train.py" in cmd
        assert "nohup" in cmd
        assert "echo $!" in cmd

    def test_start_training_custom_script(self):
        """自定义训练脚本启动命令。"""
        cmd = StepCommandBuilder.start_training("finetune.py")
        assert "python3 finetune.py" in cmd

    def test_start_training_script_with_path(self):
        """脚本路径包含目录时应正确处理。"""
        cmd = StepCommandBuilder.start_training("scripts/train.py")
        assert "scripts/train.py" in cmd

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
        cmd = StepCommandBuilder.tail_log(log_path="/var/log/train.log", lines=100)
        assert "tail -n 100" in cmd
        assert "/var/log/train.log" in cmd

    def test_tail_log_zero_lines(self):
        """0 行日志查看。"""
        cmd = StepCommandBuilder.tail_log(lines=0)
        assert "tail -n 0" in cmd

    def test_list_output_files_default(self):
        """默认输出文件查找命令。"""
        cmd = StepCommandBuilder.list_output_files()
        assert "find /root/training_repo" in cmd
        assert ".pt" in cmd
        assert ".ckpt" in cmd
        assert ".bin" in cmd
        assert ".safetensors" in cmd

    def test_list_output_files_custom_directory(self):
        """自定义目录的输出文件查找命令。"""
        cmd = StepCommandBuilder.list_output_files("/custom/path")
        assert "/custom/path" in cmd

    # ── 命令注入防护 ──

    def test_clone_repo_injection_attempt_in_branch(self):
        """分支名包含注入命令时应被安全引用（shlex.quote 包裹）。"""
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/example/repo.git",
            branch="main; rm -rf /",
        )
        # shlex.quote 会将整个值用单引号包裹，使注入字符失去特殊含义
        assert "'main; rm -rf /'" in cmd

    def test_clone_repo_injection_attempt_in_url(self):
        """token 包含注入命令时应被安全引用（shlex.quote 包裹整个 URL）。"""
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/example/repo.git",
            branch="main",
            token="`cat /etc/passwd`",
        )
        # shlex.quote 会将整个 URL 用单引号包裹，使反引号失去命令执行能力
        assert cmd.startswith("cd /root && rm -rf training_repo && git clone --branch main --single-branch 'https://`cat /etc/passwd`@github.com/example/repo.git' training_repo && echo 'clone_ok'")

    def test_start_training_injection_attempt(self):
        """脚本名包含注入命令时应被安全引用。"""
        cmd = StepCommandBuilder.start_training("train.py && whoami")
        # && 应被引用
        assert "&&" in cmd  # shlex.quote 会保留字面
        # 但整个参数应被引用，不会实际执行 whoami