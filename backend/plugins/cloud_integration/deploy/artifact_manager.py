"""制品管理器 —— 从远程实例拉取训练产物并验证完整性。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.plugins.cloud_integration.deploy.ssh_executor import SSHExecutor


class ArtifactManager:
    """训练产物管理：SFTP 回传 + SHA256 校验。"""

    def __init__(self, ssh_executor: SSHExecutor):
        self._ssh = ssh_executor

    async def pull_artifacts(
        self,
        conn_key: str,
        remote_paths: list[str],
        local_dir: Path,
    ) -> list[dict]:
        """从远程实例拉取产物文件并验证 SHA256。

        Returns:
            [{filename, local_path, sha256, size_bytes, verified}]
        """
        local_dir.mkdir(parents=True, exist_ok=True)
        artifacts = []

        for remote_path in remote_paths:
            filename = Path(remote_path).name
            local_path = local_dir / filename

            # 下载
            await self._ssh.download(conn_key, remote_path, local_path)

            # 远程和本地 SHA256 对比
            remote_sha = await self._ssh.compute_sha256(conn_key, remote_path)
            local_sha = await self._ssh.compute_local_sha256(local_path)

            artifacts.append(
                {
                    "filename": filename,
                    "local_path": str(local_path),
                    "remote_path": remote_path,
                    "sha256": local_sha,
                    "size_bytes": local_path.stat().st_size,
                    "verified": remote_sha == local_sha,
                }
            )

        return artifacts

    async def pull_directory(
        self,
        conn_key: str,
        remote_dir: str,
        local_dir: Path,
        pattern: str = "*",
    ) -> list[dict]:
        """拉取远程目录下匹配的文件。"""
        names = await self._ssh.list_remote_filenames(conn_key, remote_dir, pattern)
        if not names:
            return []

        base = remote_dir.rstrip("/")
        full_paths = [f"{base}/{f}" for f in names]
        return await self.pull_artifacts(conn_key, full_paths, local_dir)
