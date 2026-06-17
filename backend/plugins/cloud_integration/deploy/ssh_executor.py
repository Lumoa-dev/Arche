"""SSH 执行器，用于远程命令执行和文件传输。"""

from __future__ import annotations

import fnmatch
import hashlib
import os
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import asyncssh

from backend.core.middleware import AppError

if TYPE_CHECKING:
    from asyncssh.connection import SSHClientConnection


class SSHError(AppError):
    def __init__(
        self,
        message: str = "SSH 操作失败",
        code: str = "ssh_error",
        status_code: int = 500,
    ):
        super().__init__(message, code, status_code)


def _assert_safe_remote_path(path: str) -> None:
    """拒绝路径穿越与空字节（远程路径来自任务配置时需校验）。"""
    if not path or "\x00" in path or not path.startswith("/"):
        raise SSHError("非法远程路径")
    if ".." in Path(path).parts:
        raise SSHError("非法远程路径")


class SSHExecutor:
    """SSH 远程命令执行 + SFTP 文件传输封装。"""

    def __init__(self) -> None:
        self._connections: dict[str, SSHClientConnection] = {}

    async def connect(
        self,
        host: str,
        port: int = 22,
        user: str = "root",
        key_path: str | None = None,
        password: str | None = None,
    ) -> SSHClientConnection:
        """建立 SSH 连接。"""
        conn_key = f"{host}:{port}"
        if conn_key in self._connections:
            return self._connections[conn_key]

        connect_kwargs: dict = {
            "host": host,
            "port": port,
            "username": user,
        }
        kh_env = os.environ.get("SSH_KNOWN_HOSTS")
        kh_path = (
            Path(kh_env).expanduser()
            if kh_env
            else (Path.home() / ".ssh" / "known_hosts")
        )
        if kh_path.is_file():
            connect_kwargs["known_hosts"] = str(kh_path)
        else:
            # 无 known_hosts 文件时与历史行为一致；生产请配置 SSH_KNOWN_HOSTS 或写入 ~/.ssh/known_hosts  # noqa: E501
            connect_kwargs["known_hosts"] = None

        if key_path:
            connect_kwargs["client_keys"] = [key_path]
        elif password:
            connect_kwargs["password"] = password
        else:
            raise SSHError("SSH 认证失败：需要提供密钥路径或密码")

        try:
            conn = await asyncssh.connect(**connect_kwargs)
            self._connections[conn_key] = conn
            return conn
        except Exception as e:
            raise SSHError(f"SSH 连接失败 ({host}:{port}): {e}")  # noqa: B904

    async def execute(
        self, conn_key: str, command: str | Sequence[str], timeout: int = 300
    ) -> str:
        """执行远程命令。传入 argv 序列（list/tuple）时由 asyncssh 直接 exec，不经 shell。"""  # noqa: E501
        conn = self._connections.get(conn_key)
        if not conn:
            raise SSHError(f"SSH 连接不存在: {conn_key}")

        try:
            result = await conn.run(command, timeout=timeout, check=True)
            stdout = result.stdout
            return stdout.decode() if isinstance(stdout, bytes) else (stdout or "")
        except asyncssh.Error as e:
            raise SSHError(f"远程命令执行失败: {command!r}\n{e!s}")  # noqa: B904
        except Exception as e:
            raise SSHError(f"SSH 执行失败: {e}")  # noqa: B904

    async def download(self, conn_key: str, remote_path: str, local_path: Path) -> None:
        """SFTP 下载远程文件。"""
        _assert_safe_remote_path(remote_path)
        conn = self._connections.get(conn_key)
        if not conn:
            raise SSHError(f"SSH 连接不存在: {conn_key}")

        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with conn.start_sftp_client() as sftp:
                await sftp.get(remote_path, str(local_path))
        except Exception as e:
            raise SSHError(f"SFTP 下载失败: {remote_path} -> {local_path}: {e}")  # noqa: B904

    async def upload(self, conn_key: str, local_path: Path, remote_path: str) -> None:
        """SFTP 上传本地文件。"""
        _assert_safe_remote_path(remote_path)
        conn = self._connections.get(conn_key)
        if not conn:
            raise SSHError(f"SSH 连接不存在: {conn_key}")

        try:
            async with conn.start_sftp_client() as sftp:
                await sftp.put(str(local_path), remote_path)
        except Exception as e:
            raise SSHError(f"SFTP 上传失败: {local_path} -> {remote_path}: {e}")  # noqa: B904

    async def list_remote_filenames(
        self, conn_key: str, remote_dir: str, pattern: str = "*"
    ) -> list[str]:
        """列出远程目录下的文件名（不含路径），按 pattern 做 fnmatch 过滤。"""
        _assert_safe_remote_path(remote_dir)
        conn = self._connections.get(conn_key)
        if not conn:
            raise SSHError(f"SSH 连接不存在: {conn_key}")

        try:
            async with conn.start_sftp_client() as sftp:
                raw = await sftp.listdir(remote_dir)
        except Exception as e:
            raise SSHError(f"SFTP 列目录失败: {remote_dir}: {e}")  # noqa: B904

        names = [n.decode() if isinstance(n, bytes) else str(n) for n in raw]
        names = [n for n in names if n not in (".", "..")]
        return sorted(n for n in names if fnmatch.fnmatch(n, pattern))

    async def compute_sha256(self, conn_key: str, remote_path: str) -> str:
        """计算远程文件的 SHA256。"""
        _assert_safe_remote_path(remote_path)
        output = await self.execute(conn_key, ["sha256sum", remote_path])
        return output.split()[0] if output else ""

    async def compute_local_sha256(self, local_path: Path) -> str:
        """计算本地文件的 SHA256。"""
        h = hashlib.sha256()
        with open(local_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    async def close(self, conn_key: str) -> None:
        """关闭指定连接。"""
        conn = self._connections.pop(conn_key, None)
        if conn:
            conn.close()
            await conn.wait_closed()

    async def close_all(self) -> None:
        """关闭所有连接。"""
        for key in list(self._connections):
            await self.close(key)
