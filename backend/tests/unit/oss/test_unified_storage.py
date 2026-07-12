"""UnifiedStorage 无感存储层单元测试。

测试原则：
- 使用 AsyncMock/MagicMock 模拟后端依赖，不涉及真实网络
- 每个测试用例独立、可重复、无副作用
- 代码注释使用中文（项目规范）
"""

from __future__ import annotations

import asyncio
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from backend.plugins.oss.services import UnifiedStorage, StorageError


# =============================================================================
# 辅助函数
# =============================================================================


async def _async_bytes_iter(content: bytes):
    """将字节内容包装为异步迭代器，模拟 download 返回值。"""
    yield content


def _make_download_side_effect(content: bytes):
    """创建 download mock 的 side_effect：返回指定内容的异步迭代器。"""
    def _side_effect(key):  # noqa: ARG001
        return _async_bytes_iter(content)
    return _side_effect


# =============================================================================
# Mock 后端
# =============================================================================


class MockStorageBackend:
    """存储后端的 Mock 封装。

    upload_stream/delete/exists/list 使用 AsyncMock 模拟（被 await 调用）。
    download 使用 MagicMock 模拟（返回异步生成器，非 await 调用）。
    """

    def __init__(self):
        self.upload_stream = AsyncMock()
        # download 是 async generator 函数，调用返回异步生成器对象而非协程
        self.download = MagicMock()
        self.delete = AsyncMock()
        self.exists = AsyncMock(return_value=False)
        self.list = AsyncMock(return_value=[])
        self.get_disk_usage = MagicMock(return_value=0)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def storage():
    """创建 UnifiedStorage 实例，同时 Mock MinIO 和阿里云后端。"""
    minio = MockStorageBackend()
    aliyun = MockStorageBackend()

    service = MagicMock()
    service._get_minio = MagicMock(return_value=minio)
    service._get_aliyun = MagicMock(return_value=aliyun)

    storage = UnifiedStorage(service)
    yield storage

    # 清理：取消后台 sync worker 任务
    if storage._sync_worker_task and not storage._sync_worker_task.done():
        storage._sync_worker_task.cancel()
        try:
            await storage._sync_worker_task
        except (asyncio.CancelledError, Exception):
            pass


@pytest.fixture
async def storage_no_aliyun():
    """创建 UnifiedStorage 实例，仅有 MinIO（无阿里云后端）。"""
    minio = MockStorageBackend()

    service = MagicMock()
    service._get_minio = MagicMock(return_value=minio)
    service._get_aliyun = MagicMock(return_value=None)

    storage = UnifiedStorage(service)
    yield storage

    if storage._sync_worker_task and not storage._sync_worker_task.done():
        storage._sync_worker_task.cancel()
        try:
            await storage._sync_worker_task
        except (asyncio.CancelledError, Exception):
            pass


# =============================================================================
# 测试 UnifiedStorage
# =============================================================================


class TestUnifiedStorage:
    """测试 UnifiedStorage 无感存储层各方法的行为。"""

    # ------------------------------------------------------------------
    # put()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_put_writes_to_minio(self, storage):
        """put() 将内容写入 MinIO 后端。"""
        await storage.put("test/path/file.txt", b"hello world")

        storage._minio.upload_stream.assert_awaited_once_with(
            "test/path/file.txt", ANY, 11
        )

    @pytest.mark.asyncio
    async def test_put_with_sync_to_aliyun(self, storage):
        """put() 设置 sync_to_aliyun=True 时，将同步任务加入队列并异步同步到阿里云。"""
        await storage.put("test/path/file.txt", b"sync content", sync_to_aliyun=True)

        # 验证写入 MinIO
        storage._minio.upload_stream.assert_awaited_once()

        # 等待 sync worker 处理完队列中的同步任务
        await storage._sync_queue.join()

        # 验证同步到阿里云
        storage._aliyun.upload_stream.assert_awaited()

    @pytest.mark.asyncio
    async def test_put_without_sync(self, storage):
        """put() 设置 sync_to_aliyun=False 时，不同步到阿里云。"""
        await storage.put("test/path/file.txt", b"no sync", sync_to_aliyun=False)

        # 验证写入 MinIO
        storage._minio.upload_stream.assert_awaited_once()

        # 同步队列应为空
        assert storage._sync_queue.empty()

        # 阿里云不应被调用
        storage._aliyun.upload_stream.assert_not_awaited()

    # ------------------------------------------------------------------
    # get()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_from_minio(self, storage):
        """get() 从 MinIO 读取文件内容。"""
        content = b"minio content"
        storage._minio.download.side_effect = _make_download_side_effect(content)

        result = await storage.get("test/path/file.txt")

        assert result == content
        storage._minio.download.assert_called_once_with("test/path/file.txt")
        # 不应回退到阿里云
        storage._aliyun.download.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_from_aliyun_fallback(self, storage):
        """get() 在 MinIO 不存在时，回退到阿里云拉取并缓存到 MinIO。"""
        content = b"aliyun content"

        # MinIO 下载失败
        storage._minio.download.side_effect = Exception("not found in minio")
        # 阿里云下载成功
        storage._aliyun.download.side_effect = _make_download_side_effect(content)

        result = await storage.get("test/path/file.txt")

        assert result == content
        storage._minio.download.assert_called_once_with("test/path/file.txt")
        storage._aliyun.download.assert_called_once_with("test/path/file.txt")
        # 验证内容已缓存回 MinIO
        storage._minio.upload_stream.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_not_found(self, storage_no_aliyun):
        """get() 文件在两个后端都不存在时抛出 StorageError。"""
        storage_no_aliyun._minio.download.side_effect = Exception("not found")

        with pytest.raises(StorageError) as excinfo:
            await storage_no_aliyun.get("test/path/nonexistent.txt")

        assert "文件不存在" in str(excinfo.value)

    # ------------------------------------------------------------------
    # delete()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_delete_removes_from_both(self, storage):
        """delete() 同时删除 MinIO 和阿里云中的文件。"""
        await storage.delete("test/path/file.txt")

        storage._minio.delete.assert_awaited_once_with("test/path/file.txt")
        storage._aliyun.delete.assert_awaited_once_with("test/path/file.txt")

    @pytest.mark.asyncio
    async def test_delete_ignores_not_found(self, storage):
        """delete() 文件不存在时不抛出异常，静默忽略。"""
        # 两个后端都抛出异常
        storage._minio.delete.side_effect = Exception("not found")
        storage._aliyun.delete.side_effect = Exception("not found")

        # 不应抛出任何异常
        await storage.delete("test/path/file.txt")

    # ------------------------------------------------------------------
    # exists()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_exists_in_minio(self, storage):
        """exists() 文件在 MinIO 中存在时返回 True，不查询阿里云。"""
        storage._minio.exists.return_value = True

        result = await storage.exists("test/path/file.txt")

        assert result is True
        storage._minio.exists.assert_awaited_once_with("test/path/file.txt")
        # 阿里云不应被查询
        storage._aliyun.exists.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_exists_in_aliyun(self, storage):
        """exists() 文件仅在阿里云中存在时返回 True。"""
        storage._minio.exists.return_value = False
        storage._aliyun.exists.return_value = True

        result = await storage.exists("test/path/file.txt")

        assert result is True
        storage._minio.exists.assert_awaited_once_with("test/path/file.txt")
        storage._aliyun.exists.assert_awaited_once_with("test/path/file.txt")

    @pytest.mark.asyncio
    async def test_exists_not_found(self, storage):
        """exists() 文件在两个后端都不存在时返回 False。"""
        storage._minio.exists.return_value = False
        storage._aliyun.exists.return_value = False

        result = await storage.exists("test/path/file.txt")

        assert result is False

    # ------------------------------------------------------------------
    # list()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_merges_and_deduplicates(self, storage):
        """list() 合并两个后端的结果并去重排序。"""
        storage._minio.list.return_value = ["a.txt", "b.txt", "c.txt"]
        storage._aliyun.list.return_value = ["b.txt", "c.txt", "d.txt"]

        result = await storage.list("test/")

        assert result == ["a.txt", "b.txt", "c.txt", "d.txt"]
        storage._minio.list.assert_awaited_once_with("test/")
        storage._aliyun.list.assert_awaited_once_with("test/")