"""OSS 存储后端——单元测试。

覆盖 LocalBackend 的路径穿越防护、完整的 upload/download/delete/exists 生命周期。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from backend.plugins.oss.backends import LocalBackend


# =============================================================================
# LocalBackend — 路径穿越防护
# =============================================================================


class TestLocalBackendPathTraversal:
    """LocalBackend._resolve 路径穿越防护测试。"""

    def test_normal_path(self, tmp_path: Path):
        """正常路径解析。"""
        backend = LocalBackend(tmp_path)
        resolved = backend._resolve("normal/file.txt")
        assert resolved == (tmp_path / "normal" / "file.txt").resolve()
        assert resolved.exists() is False  # 不创建文件

    def test_path_traversal_dotdot(self, tmp_path: Path):
        """路径穿越：../ 尝试逃逸。"""
        backend = LocalBackend(tmp_path)
        with pytest.raises(ValueError, match="非法路径"):
            backend._resolve("../../etc/passwd")

    def test_path_traversal_absolute(self, tmp_path: Path):
        """路径穿越：绝对路径被安全处理（前导 / 被剥离）。"""
        backend = LocalBackend(tmp_path)
        resolved = backend._resolve("/etc/passwd")
        # 前导 / 被 lstrip，实际解析为 base_path/etc/passwd
        assert resolved == (tmp_path / "etc" / "passwd").resolve()

    def test_path_traversal_deep(self, tmp_path: Path):
        """深层路径穿越。"""
        backend = LocalBackend(tmp_path)
        deep_path = "a/b/../../../etc/passwd"
        with pytest.raises(ValueError, match="非法路径"):
            backend._resolve(deep_path)

    def test_path_traversal_with_symlink_not_checked(self, tmp_path: Path):
        """带符号链接的路径（不在 resolve 层面检查，但会检测到逃逸）。"""
        backend = LocalBackend(tmp_path)
        # 创建目录内子目录
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        # 创建一个指向外部的符号链接
        link_path = sub_dir / "external"
        link_path.symlink_to("/tmp")
        # 通过符号链接访问外部 → 应被检测为路径穿越
        with pytest.raises(ValueError, match="非法路径"):
            backend._resolve("sub/external/../outside.txt")

    def test_nested_path_within_base(self, tmp_path: Path):
        """深层嵌套路径在 base 内。"""
        backend = LocalBackend(tmp_path)
        resolved = backend._resolve("a/b/c/d/file.txt")
        expected = (tmp_path / "a" / "b" / "c" / "d" / "file.txt").resolve()
        assert resolved == expected


# =============================================================================
# LocalBackend — 完整生命周期
# =============================================================================


@pytest.mark.asyncio
class TestLocalBackendLifecycle:
    """LocalBackend 上传/下载/删除/存在性全链路测试。"""

    async def test_upload_and_download(self, tmp_path: Path):
        """上传后下载验证内容一致。"""
        backend = LocalBackend(tmp_path)

        async def _stream():
            yield b"Hello, "
            yield b"World!"

        await backend.upload_stream("test/hello.txt", _stream(), 13)

        # 验证文件存在
        assert await backend.exists("test/hello.txt") is True

        # 下载验证内容
        chunks = []
        async for chunk in backend.download("test/hello.txt"):
            chunks.append(chunk)
        assert b"".join(chunks) == b"Hello, World!"

    async def test_upload_overwrite(self, tmp_path: Path):
        """覆盖上传已有文件。"""
        backend = LocalBackend(tmp_path)

        async def _stream1():
            yield b"Old content"

        async def _stream2():
            yield b"New content"

        await backend.upload_stream("test/overwrite.txt", _stream1(), 11)
        await backend.upload_stream("test/overwrite.txt", _stream2(), 11)

        chunks = []
        async for chunk in backend.download("test/overwrite.txt"):
            chunks.append(chunk)
        assert b"".join(chunks) == b"New content"

    async def test_delete_existing(self, tmp_path: Path):
        """删除已存在的文件。"""
        backend = LocalBackend(tmp_path)

        async def _stream():
            yield b"To be deleted"

        await backend.upload_stream("test/to_delete.txt", _stream(), 14)
        assert await backend.exists("test/to_delete.txt") is True

        await backend.delete("test/to_delete.txt")
        assert await backend.exists("test/to_delete.txt") is False

    async def test_delete_non_existent(self, tmp_path: Path):
        """删除不存在的文件不报错。"""
        backend = LocalBackend(tmp_path)
        await backend.delete("non/existent.txt")
        # 不应抛出异常

    async def test_exists_false(self, tmp_path: Path):
        """不存在的文件返回 False。"""
        backend = LocalBackend(tmp_path)
        assert await backend.exists("non/existent.txt") is False

    async def test_exists_true(self, tmp_path: Path):
        """存在的文件返回 True。"""
        backend = LocalBackend(tmp_path)
        (tmp_path / "test.txt").write_text("hello")
        assert await backend.exists("test.txt") is True

    async def test_list_empty(self, tmp_path: Path):
        """空目录列出空列表。"""
        backend = LocalBackend(tmp_path)
        result = await backend.list()
        assert result == []

    async def test_list_with_prefix(self, tmp_path: Path):
        """按前缀列出文件。"""
        backend = LocalBackend(tmp_path)
        img_dir = tmp_path / "images"
        img_dir.mkdir(parents=True)
        (img_dir / "a.png").write_text("a")
        (img_dir / "b.png").write_text("b")
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir(parents=True)
        (doc_dir / "readme.md").write_text("readme")

        result = await backend.list(prefix="images")
        assert len(result) == 2
        assert all("images" in p for p in result)

    async def test_disk_usage(self, tmp_path: Path):
        """磁盘使用量统计。"""
        backend = LocalBackend(tmp_path)
        (tmp_path / "file1.txt").write_text("hello")
        (tmp_path / "sub" / "file2.txt").parent.mkdir()
        (tmp_path / "sub" / "file2.txt").write_text("world")

        usage = backend.get_disk_usage()
        assert usage == 10  # 5 + 5

    async def test_disk_usage_empty(self, tmp_path: Path):
        """空目录磁盘使用量为 0。"""
        backend = LocalBackend(tmp_path)
        assert backend.get_disk_usage() == 0

    async def test_upload_empty_file(self, tmp_path: Path):
        """上传空文件。"""
        backend = LocalBackend(tmp_path)

        async def _empty_stream():
            return
            yield  # pragma: no cover

        await backend.upload_stream("empty.txt", _empty_stream(), 0)

        chunks = []
        async for chunk in backend.download("empty.txt"):
            chunks.append(chunk)
        assert b"".join(chunks) == b""


# =============================================================================
# LocalBackend — 初始化
# =============================================================================


class TestLocalBackendInit:
    """LocalBackend 初始化测试。"""

    def test_init_creates_base_path(self, tmp_path: Path):
        """初始化时创建 base_path 目录。"""
        new_path = tmp_path / "new" / "nested" / "dir"
        assert new_path.exists() is False
        backend = LocalBackend(new_path)
        assert new_path.exists() is True
        assert backend._base_path == new_path.resolve()

    def test_init_existing_path(self, tmp_path: Path):
        """初始化已存在的目录。"""
        backend = LocalBackend(tmp_path)
        assert backend._base_path == tmp_path.resolve()