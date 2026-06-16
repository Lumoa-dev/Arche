"""TrainingOrchestrator 集成测试 — 使用真实内存数据库。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text

from backend.plugins.cloud_integration.orchestrator import TrainingOrchestrator


@pytest.mark.asyncio
class TestTrainingOrchestratorIntegration:
    """集成测试：验证 orchestrator 在真实数据库上的生命周期和韧性。"""

    async def test_start_stop_lifecycle(self, db_container):
        """验证 orchestrator start/stop 在真实内存数据库中正常执行。"""
        orch = TrainingOrchestrator(db_container)

        # start → 初始化会话工厂
        await orch.start()
        assert orch._running is True
        assert orch._session_factory_instance is not None
        assert orch._task is not None and not orch._task.done()

        # stop → 取消任务并清理
        await orch.stop()
        assert orch._running is False
        assert orch._session_factory_instance is None

    async def test_daemon_loop_no_jobs(self, db_container):
        """验证 daemon loop 在没有 Job 时不报错。"""
        orch = TrainingOrchestrator(db_container)

        # mock _get_service 避免找不到 cloud_training 服务
        orch._get_service = MagicMock(
            return_value=MagicMock(
                create_instance=AsyncMock(return_value={"id": "inst-1"})
            )
        )

        await orch.start()
        # 等一次循环迭代执行完毕
        await asyncio.sleep(0.5)

        # 检查循环是否活着（没有因异常退出）
        assert orch._running is True
        assert orch._task is not None and not orch._task.done()

        await orch.stop()

    async def test_session_factory_init_and_reset(self, db_container):
        """验证会话工厂的初始化、缓存和重置。"""
        orch = TrainingOrchestrator(db_container)

        # 初始状态：未初始化
        assert orch._session_factory_instance is None

        # 第一次访问 _session_factory 触发惰性初始化
        factory1 = orch._session_factory
        assert orch._session_factory_instance is not None
        assert factory1 is not None

        # 第二次访问返回相同实例
        factory2 = orch._session_factory
        assert factory2 is factory1  # 同一对象

        # 重置后重新获取
        orch._reset_session_factory()
        assert orch._session_factory_instance is None
        factory3 = orch._session_factory
        assert factory3 is not None
        # 新工厂应该能创建可用的 session
        async with factory3() as session:
            result = await session.execute(text("SELECT 1 AS test_col"))
            row = result.fetchone()
            assert row is not None

    async def test_recover_session_factory(self, db_container):
        """验证会话工厂恢复机制能正常运行。"""
        orch = TrainingOrchestrator(db_container)

        # 先初始化
        factory_before = orch._session_factory
        assert factory_before is not None

        # 模拟引擎失效 → 重置 → 恢复
        orch._reset_session_factory()
        assert orch._session_factory_instance is None

        # 恢复
        orch._try_recover_session_factory()
        assert orch._session_factory_instance is not None

        # 恢复后的工厂能正常建 session 和执行查询
        factory_after = orch._session_factory
        assert factory_after is not None
        async with factory_after() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.fetchone() is not None
