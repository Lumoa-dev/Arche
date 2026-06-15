"""云训练各步骤的 SSH 命令构建器 — 纯函数，不涉及状态管理。"""

from __future__ import annotations

import shlex


class StepCommandBuilder:
    """构建各编排步骤的远程 SSH 命令。"""

    @staticmethod
    def check_env() -> str:
        return "python3 --version && git --version && pip3 --version"

    @staticmethod
    def install_system_deps() -> str:
        return "apt-get update -qq && apt-get install -y -qq python3 python3-pip git curl >/dev/null 2>&1 && echo 'deps_installed'"  # noqa: E501

    @staticmethod
    def clone_repo(
        repo_url: str, branch: str = "main", token: str | None = None
    ) -> str:
        if token:
            repo_url = repo_url.replace("https://", f"https://{token}@")
        br = shlex.quote(branch)
        ru = shlex.quote(repo_url)
        return (
            f"cd /root && rm -rf training_repo && "
            f"git clone --branch {br} --single-branch {ru} training_repo && "
            f"echo 'clone_ok'"
        )

    @staticmethod
    def install_deps(requirements_file: str = "requirements.txt") -> str:
        rf = shlex.quote(requirements_file)
        return (
            f"cd /root/training_repo && "
            f"test -f {rf} && "
            f"pip3 install -r {rf} --quiet && "
            f"echo 'deps_installed'"
        )

    @staticmethod
    def fetch_huggingface_dataset(dataset_path: str) -> str:
        dp = shlex.quote(dataset_path)
        return (
            f"cd /root/training_repo && "
            f"huggingface-cli download {dp} --repo-type dataset "
            f"--local-dir /root/training_repo/data && "
            f"echo 'dataset_ok'"
        )

    @staticmethod
    def fetch_modelscope_dataset(dataset_path: str) -> str:
        dp = shlex.quote(dataset_path)
        return (
            f"cd /root/training_repo && "
            f"modelscope download --dataset {dp} "
            f"--local_dir /root/training_repo/data && "
            f"echo 'dataset_ok'"
        )

    @staticmethod
    def start_training(script: str = "train.py") -> str:
        sc = shlex.quote(script)
        return (
            f"cd /root/training_repo && "
            f"nohup python3 {sc} > /root/training.log 2>&1 & "
            f"echo $!"
        )

    @staticmethod
    def check_process(pid: str) -> str:
        p = shlex.quote(pid)
        return f"kill -0 {p} 2>/dev/null && echo running || echo stopped"

    @staticmethod
    def tail_log(log_path: str = "/root/training.log", lines: int = 50) -> str:
        lp = shlex.quote(log_path)
        return f"tail -n {int(lines)} {lp}"

    @staticmethod
    def list_output_files(directory: str = "/root/training_repo") -> str:
        d = shlex.quote(directory)
        return (
            f"find {d} -type f \\( -name '*.pt' -o -name '*.ckpt' "
            f"-o -name '*.bin' -o -name '*.safetensors' \\) 2>/dev/null"
        )
