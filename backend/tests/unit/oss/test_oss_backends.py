"""OSS 存储后端测试 —— LocalBackend（本地文件系统后端）。"""

import tempfile
from pathlib import Path

import pytest

from backend.plugins.oss.backends import LocalBackend


class TestLocalBackend:
    """测试本地文件系统存储后端。"""

    @pytest.fixture
    def backend(self):
        """创建临时目录作为后端存储。"""
        with tempfile.TemporaryDirectory(prefix="arche-test-oss-") as tmpdir:
            yield LocalBackend(Path(tmpdir))

    @pytest.mark.asyncio
    async def test_upload_and_download(self, backend):
        """上传后可以下载相同内容。"""
        async def _stream():
            yield b"hello world"

        await backend.upload_stream("test.txt", _stream(), 11)
        result = b"".join([chunk async for chunk in backend.download("test.txt")])
        assert result == b"hello world"

    @pytest.mark.asyncio
    async def test_upload_large_file(self, backend):
        """上传较大文件。"""
        content = b"x" * 1024 * 100  # 100KB

        async def _stream():
            yield content

        await backend.upload_stream("large.bin", _stream(), len(content))
        result = b"".join([chunk async for chunk in backend.download("large.bin")])
        assert result == content
        assert len(result) == 1024 * 100

    @pytest.mark.asyncio
    async def test_exists(self, backend):
        """文件存在检查。"""
        assert await backend.exists("nonexistent.txt") is False

        async def _stream():
            yield b"test"

        await backend.upload_stream("existing.txt", _stream(), 4)
        assert await backend.exists("existing.txt") is True

    @pytest.mark.asyncio
    async def test_delete(self, backend):
        """删除文件后不再存在。"""
        async def _stream():
            yield b"to-delete"

        await backend.upload_stream("to-delete.txt", _stream(), 9)
        assert await backend.exists("to-delete.txt") is True
        await backend.delete("to-delete.txt")
        assert await backend.exists("to-delete.txt") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, backend):
        """删除不存在的文件不报错。"""
        await backend.delete("nonexistent.txt")  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_list_empty(self, backend):
        """空目录列出空列表。"""
        files = await backend.list()
        assert files == []

    @pytest.mark.asyncio
    async def test_list_with_files(self, backend):
        """列出目录中的文件。"""
        async def _stream_a():
            yield b"aaa"

        async def _stream_b():
            yield b"bbb"

        await backend.upload_stream("dir/a.txt", _stream_a(), 3)
        await backend.upload_stream("dir/b.txt", _stream_b(), 3)
        await backend.upload_stream("root.txt", _stream_a(), 3)

        files = await backend.list()
        assert len(files) == 3

    @pytest.mark.asyncio
    async def test_list_with_prefix(self, backend):
        """按前缀列出文件。"""
        async def _stream():
            yield b"x"

        await backend.upload_stream("dir/a.txt", _stream(), 1)
        await backend.upload_stream("dir/b.txt", _stream(), 1)
        await backend.upload_stream("other/c.txt", _stream(), 1)

        files = await backend.list("dir/")
        assert len(files) == 2
        assert all("dir/" in f for f in files)

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, backend):
        """路径穿越攻击被阻止。"""
        async def _stream():
            yield b"should not escape"

        with pytest.raises(ValueError, match="非法路径"):
            await backend.upload_stream("../../etc/passwd", _stream(), 19)

    @pytest.mark.asyncio
    async def test_path_traversal_download(self, backend):
        """路径穿越下载被阻止。"""
        with pytest.raises(ValueError, match="非法路径"):
            async for _ in backend.download("../../etc/passwd"):
                pass

    @pytest.mark.asyncio
    async def test_disk_usage(self, backend):
        """磁盘使用量正确统计。"""
        async def _stream():
            yield b"x" * 100

        await backend.upload_stream("file1.bin", _stream(), 100)
        await backend.upload_stream("file2.bin", _stream(), 100)
        usage = backend.get_disk_usage()
        assert usage >= 200

    @pytest.mark.asyncio
    async def test_backend_type(self, backend):
        """后端类型标识正确。"""
        assert backend.backend_type == "local"

    @pytest.mark.asyncio
    async def test_upload_subdirectory(self, backend):
        """上传到子目录。"""
        async def _stream():
            yield b"nested content"

        await backend.upload_stream("nested/path/file.txt", _stream(), 14)
        assert await backend.exists("nested/path/file.txt") is True

        result = b"".join([chunk async for chunk in backend.download("nested/path/file.txt")])
        assert result == b"nested content"

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, backend):
        """上传空文件。"""
        async def _stream():
            yield b""

        await backend.upload_stream("empty.txt", _stream(), 0)
        assert await backend.exists("empty.txt") is True
        result = b"".join([chunk async for chunk in backend.download("empty.txt")])
        assert result == b""

    @pytest.mark.asyncio
    async def test_list_nonexistent_prefix(self, backend):
        """列出不存在的目录返回空列表。"""
        files = await backend.list("nonexistent/")
        assert files == []

    @pytest.mark.asyncio
    async def test_init_creates_base_dir(self):
        """初始化时创建基础目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "auto-created"
            assert not base.exists()
            backend = LocalBackend(base)
            assert base.exists()
            assert backend.backend_type == "local"