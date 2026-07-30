"""SSH 命令构建器单元测试 —— 验证命令字符串正确性及安全引用。"""

from __future__ import annotations

import pytest

from backend.plugins.cloud_integration.steps import StepCommandBuilder


class TestStepCommandBuilder:
    """StepCommandBuilder 纯函数测试。"""

    def test_check_env(self):
        cmd = StepCommandBuilder.check_env()
        assert "python3 --version" in cmd
        assert "git --version" in cmd
        assert "pip3 --version" in cmd

    def test_install_system_deps(self):
        cmd = StepCommandBuilder.install_system_deps()
        assert "apt-get update" in cmd
        assert "apt-get install" in cmd
        assert "deps_installed" in cmd

    def test_clone_repo(self):
        cmd = StepCommandBuilder.clone_repo("https://github.com/user/repo.git", "main")
        assert "git clone" in cmd
        assert "github.com/user/repo.git" in cmd
        assert "--branch main" in cmd
        assert "clone_ok" in cmd

    def test_clone_repo_with_token(self):
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/user/repo.git", "main", token="my_token"
        )
        assert "my_token@" in cmd
        assert "https://my_token@github.com" in cmd

    def test_clone_repo_special_chars_in_branch(self):
        """分支名含特殊字符时应被 shlex 引用。"""
        cmd = StepCommandBuilder.clone_repo(
            "https://github.com/user/repo.git", "feature/$branch"
        )
        assert "'feature/$branch'" in cmd

    def test_install_deps(self):
        cmd = StepCommandBuilder.install_deps("requirements.txt")
        assert "pip3 install -r requirements.txt" in cmd
        assert "deps_installed" in cmd

    def test_install_deps_custom_file(self):
        cmd = StepCommandBuilder.install_deps("requirements-dev.txt")
        assert "requirements-dev.txt" in cmd

    def test_fetch_huggingface_dataset(self):
        cmd = StepCommandBuilder.fetch_huggingface_dataset("dataset/name")
        assert "huggingface-cli download" in cmd
        assert "dataset/name" in cmd
        assert "dataset_ok" in cmd

    def test_fetch_modelscope_dataset(self):
        cmd = StepCommandBuilder.fetch_modelscope_dataset("dataset/name")
        assert "modelscope download" in cmd
        assert "dataset/name" in cmd
        assert "dataset_ok" in cmd

    def test_start_training(self):
        cmd = StepCommandBuilder.start_training("train.py")
        assert "nohup python3 train.py" in cmd
        assert "echo $!" in cmd

    def test_start_training_custom_script(self):
        cmd = StepCommandBuilder.start_training("finetune.py")
        assert "nohup python3 finetune.py" in cmd

    def test_check_process(self):
        cmd = StepCommandBuilder.check_process("12345")
        assert "kill -0 12345" in cmd
        assert "echo running" in cmd
        assert "echo stopped" in cmd

    def test_tail_log(self):
        cmd = StepCommandBuilder.tail_log("/root/training.log", 50)
        assert "tail -n 50 /root/training.log" in cmd

    def test_tail_log_custom_lines(self):
        cmd = StepCommandBuilder.tail_log("/var/log/train.log", 100)
        assert "tail -n 100 /var/log/train.log" in cmd

    def test_list_output_files(self):
        cmd = StepCommandBuilder.list_output_files("/root/training_repo")
        assert "find /root/training_repo" in cmd
        assert "pt" in cmd
        assert "ckpt" in cmd
        assert "safetensors" in cmd