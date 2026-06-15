"""云训练任务编排器 — 后台 daemon loop 自动推进任务链路。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from backend.plugins.cloud_integration.log_parser import LogParser
from backend.plugins.cloud_integration.models import (
    TrainingCost,
    TrainingInstance,
    TrainingJob,
    TrainingTaskStep,
)
from backend.plugins.cloud_integration.steps import StepCommandBuilder

if TYPE_CHECKING:
    from backend.core.container import ServiceContainer

logger = logging.getLogger(__name__)


class Step:
    IDLE = "idle"
    CREATING_INSTANCE = "creating_instance"
    WAITING_INSTANCE = "waiting_instance"
    CONNECTING_SSH = "connecting_ssh"
    SETTING_UP_ENV = "setting_up_env"
    CLONING_REPO = "cloning_repo"
    INSTALLING_DEPS = "installing_deps"
    FETCHING_DATASET = "fetching_dataset"
    STARTING_TRAINING = "starting_training"
    MONITORING_TRAINING = "monitoring_training"
    COLLECTING_ARTIFACTS = "collecting_artifacts"
    SHUTTING_DOWN = "shutting_down"
    COMPLETED = "completed"
    FAILED = "failed"


NEXT_STEP = {
    Step.IDLE: Step.CREATING_INSTANCE,
    Step.CREATING_INSTANCE: Step.WAITING_INSTANCE,
    Step.WAITING_INSTANCE: Step.CONNECTING_SSH,
    Step.CONNECTING_SSH: Step.SETTING_UP_ENV,
    Step.SETTING_UP_ENV: Step.CLONING_REPO,
    Step.CLONING_REPO: Step.INSTALLING_DEPS,
    Step.INSTALLING_DEPS: Step.FETCHING_DATASET,
    Step.FETCHING_DATASET: Step.STARTING_TRAINING,
    Step.STARTING_TRAINING: Step.MONITORING_TRAINING,
    Step.MONITORING_TRAINING: Step.MONITORING_TRAINING,  # 由 _update_progress 处理
    Step.COLLECTING_ARTIFACTS: Step.SHUTTING_DOWN,
    Step.SHUTTING_DOWN: Step.COMPLETED,
}

# 步骤超时（秒）
STEP_TIMEOUTS = {
    Step.WAITING_INSTANCE: 300,  # 5 分钟
    Step.CONNECTING_SSH: 120,
    Step.CLONING_REPO: 300,
    Step.INSTALLING_DEPS: 600,  # 10 分钟
    Step.FETCHING_DATASET: 600,
}


class TrainingOrchestrator:
    """后台守护进程：自动扫描并推进训练任务到下一步。"""

    SCAN_INTERVAL = 10  # 秒，扫描间隔
    PROGRESS_INTERVAL = 30  # 秒，训练中间隔读取日志
    MAX_RETRY: int = 3  # 每步最大重试次数

    def __init__(self, container: ServiceContainer):
        self.container = container
        self._running = False
        self._task: asyncio.Task | None = None
        self._engine: AsyncEngine | None = None

    # --- 公开接口 ---

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        db = self.container.get("db")
        self._engine = db["engine"]
        self._task = asyncio.create_task(self._daemon_loop())
        logger.info("训练编排器已启动")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._engine = None
        logger.info("训练编排器已停止")

    # --- Daemon Loop ---

    async def _daemon_loop(self) -> None:
        while self._running:
            try:
                await self._process_active_jobs()
                await self._update_progress_for_running_jobs()
            except Exception:
                logger.exception("编排器循环异常")
            await asyncio.sleep(self.SCAN_INTERVAL)

    async def _process_active_jobs(self) -> None:
        """扫描需要推进的 Job，按步骤推进。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(TrainingJob).where(
                    TrainingJob.orchestrator_step.notin_(
                        ["idle", "completed", "failed", None]
                    )
                )
            )
            jobs = result.scalars().all()

        for job in jobs:
            await self._process_job(job)

    async def _update_progress_for_running_jobs(self) -> None:
        """扫描正在训练的 Job，更新进度。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(TrainingJob).where(
                    TrainingJob.orchestrator_step == Step.MONITORING_TRAINING
                )
            )
            jobs = result.scalars().all()

        for job in jobs:
            await self._check_training_progress(job)

    # --- Job 处理 ---

    async def _process_job(self, job: TrainingJob) -> None:
        step = job.orchestrator_step or Step.IDLE

        if step == Step.IDLE:
            await self._advance_step(job.id, Step.CREATING_INSTANCE)
            return

        if step == Step.CREATING_INSTANCE:
            await self._step_create_instance(job)
        elif step == Step.WAITING_INSTANCE:
            await self._step_wait_instance_ready(job)
        elif step == Step.CONNECTING_SSH:
            await self._step_connect_ssh(job)
        elif step == Step.SETTING_UP_ENV:
            await self._step_setup_env(job)
        elif step == Step.CLONING_REPO:
            await self._step_clone_repo(job)
        elif step == Step.INSTALLING_DEPS:
            await self._step_install_deps(job)
        elif step == Step.FETCHING_DATASET:
            await self._step_fetch_dataset(job)
        elif step == Step.STARTING_TRAINING:
            await self._step_start_training(job)
        elif step == Step.COLLECTING_ARTIFACTS:
            await self._step_collect_artifacts(job)
        elif step == Step.SHUTTING_DOWN:
            await self._step_shutdown_instance(job)

    # --- 步骤实现 ---

    async def _step_create_instance(self, job: TrainingJob) -> None:
        """创建远程 GPU 实例。"""
        await self._begin_step(job, Step.CREATING_INSTANCE)
        try:
            service = self._get_service()
            gpu_type = job.model_config.get("gpu_type", "RTX4090")
            provider_name = job.model_config.get("provider", "mock")
            instance_name = job.model_config.get(
                "instance_name", f"train-{job.name[:20]}"
            )

            instance = await service.create_instance(
                job_id=job.id,
                instance_name=instance_name,
                gpu_type=gpu_type,
                provider=provider_name,
            )
            await self._complete_step(
                job, Step.CREATING_INSTANCE, {"instance_id": instance["id"]}
            )
            await self._advance_step(job.id, Step.WAITING_INSTANCE)
        except Exception as e:
            await self._fail_job(job.id, f"创建实例失败: {e}")

    async def _step_wait_instance_ready(self, job: TrainingJob) -> None:
        """等待远程实例启动就绪。"""
        await self._begin_step(job, Step.WAITING_INSTANCE)
        try:
            async with self._session_factory() as session:
                inst_result = await session.execute(
                    select(TrainingInstance)
                    .where(TrainingInstance.job_id == job.id)
                    .order_by(TrainingInstance.created_at.desc())
                )
                inst = inst_result.scalar_one_or_none()

            if not inst:
                return  # 还在创建中

            provider = self._get_service()._get_provider()
            status = await provider.get_instance_status(inst.provider_instance_id)

            if status.get("status") == "running" and status.get("host"):
                # 更新 SSH 信息
                async with self._session_factory() as session:
                    result = await session.execute(
                        select(TrainingInstance).where(TrainingInstance.id == inst.id)
                    )
                    inst = result.scalar_one()
                    inst.ssh_host = status.get("host", inst.ssh_host)
                    inst.ssh_port = status.get("port", inst.ssh_port)
                    inst.ssh_user = status.get("user", inst.ssh_user)
                    inst.status = "running"
                    await session.commit()

                await self._complete_step(job, Step.WAITING_INSTANCE, status)
                await self._advance_step(job.id, Step.CONNECTING_SSH)
        except Exception as e:
            await self._fail_job(job.id, f"等待实例失败: {e}")

    async def _step_connect_ssh(self, job: TrainingJob) -> None:
        """SSH 连接远程实例。"""
        await self._begin_step(job, Step.CONNECTING_SSH)
        try:
            async with self._session_factory() as session:
                inst_result = await session.execute(
                    select(TrainingInstance)
                    .where(
                        TrainingInstance.job_id == job.id,
                        TrainingInstance.status == "running",
                    )
                    .order_by(TrainingInstance.created_at.desc())
                )
                inst = inst_result.scalar_one_or_none()

            if not inst or not inst.ssh_host:
                await self._retry_step(job, Step.CONNECTING_SSH, "实例 SSH 信息未就绪")
                return

            conn_key = f"{inst.ssh_host}:{inst.ssh_port}"
            ssh = self._get_service()._get_ssh()
            await ssh.connect(
                host=inst.ssh_host,
                port=inst.ssh_port,
                user=inst.ssh_user or "root",
                key_path=inst.ssh_key_path,
                password=inst.ssh_password,
            )
            await ssh.close(conn_key)

            await self._complete_step(job, Step.CONNECTING_SSH, {"host": inst.ssh_host})
            await self._advance_step(job.id, Step.SETTING_UP_ENV)
        except Exception as e:
            await self._retry_step(job, Step.CONNECTING_SSH, f"SSH 连接失败: {e}")

    async def _step_setup_env(self, job: TrainingJob) -> None:
        """检查并安装基础环境。"""
        await self._begin_step(job, Step.SETTING_UP_ENV)
        try:
            conn_key = await self._get_conn_key(job.id)
            ssh = self._get_service()._get_ssh()

            # 尝试检查环境
            try:
                await ssh.execute(conn_key, StepCommandBuilder.check_env(), timeout=30)
            except Exception:
                # 环境不完整，安装
                await ssh.execute(
                    conn_key, StepCommandBuilder.install_system_deps(), timeout=120
                )

            await self._complete_step(job, Step.SETTING_UP_ENV, {})
            await self._advance_step(job.id, Step.CLONING_REPO)
        except Exception as e:
            await self._retry_step(job, Step.SETTING_UP_ENV, f"环境配置失败: {e}")

    async def _step_clone_repo(self, job: TrainingJob) -> None:
        """从 Git 仓库拉取代码。"""
        await self._begin_step(job, Step.CLONING_REPO)
        try:
            conn_key = await self._get_conn_key(job.id)
            ssh = self._get_service()._get_ssh()

            cmd = StepCommandBuilder.clone_repo(
                repo_url=job.repo_url or "",
                branch=job.repo_branch or "main",
                token=job.repo_token,
            )
            await ssh.execute(conn_key, cmd, timeout=120)

            await self._complete_step(job, Step.CLONING_REPO, {"repo": job.repo_url})
            await self._advance_step(job.id, Step.INSTALLING_DEPS)
        except Exception as e:
            await self._fail_job(job.id, f"代码拉取失败: {e}")

    async def _step_install_deps(self, job: TrainingJob) -> None:
        """安装 Python 依赖。"""
        await self._begin_step(job, Step.INSTALLING_DEPS)
        try:
            conn_key = await self._get_conn_key(job.id)
            ssh = self._get_service()._get_ssh()

            cmd = StepCommandBuilder.install_deps(
                job.requirements_file or "requirements.txt"
            )
            await ssh.execute(conn_key, cmd, timeout=300)

            await self._complete_step(job, Step.INSTALLING_DEPS, {})
            await self._advance_step(job.id, Step.FETCHING_DATASET)
        except Exception as e:
            await self._retry_step(job, Step.INSTALLING_DEPS, f"依赖安装失败: {e}")

    async def _step_fetch_dataset(self, job: TrainingJob) -> None:
        """拉取数据集（可选步骤）。"""
        await self._begin_step(job, Step.FETCHING_DATASET)
        try:
            dataset_config = job.dataset_config or {}
            source = dataset_config.get("source", "")

            if source:
                conn_key = await self._get_conn_key(job.id)
                ssh = self._get_service()._get_ssh()

                if source == "huggingface":
                    cmd = StepCommandBuilder.fetch_huggingface_dataset(
                        dataset_config.get("path", "")
                    )
                elif source == "modelscope":
                    cmd = StepCommandBuilder.fetch_modelscope_dataset(
                        dataset_config.get("path", "")
                    )
                else:
                    cmd = None

                if cmd:
                    await ssh.execute(conn_key, cmd, timeout=300)

            await self._complete_step(job, Step.FETCHING_DATASET, {})
            await self._advance_step(job.id, Step.STARTING_TRAINING)
        except Exception as e:
            await self._fail_job(job.id, f"数据集拉取失败: {e}")

    async def _step_start_training(self, job: TrainingJob) -> None:
        """启动训练进程。"""
        await self._begin_step(job, Step.STARTING_TRAINING)
        try:
            conn_key = await self._get_conn_key(job.id)
            ssh = self._get_service()._get_ssh()

            script = job.training_script or "train.py"
            cmd = StepCommandBuilder.start_training(script)
            pid_output = await ssh.execute(conn_key, cmd, timeout=30)
            pid = pid_output.strip().split()[-1]

            # 更新 Job 信息
            async with self._session_factory() as session:
                result = await session.execute(
                    select(TrainingJob).where(TrainingJob.id == job.id)
                )
                j = result.scalar_one()
                j.log_file_path = "/root/training.log"
                j.progress_info = j.progress_info or {}
                j.progress_info["pid"] = pid
                await session.commit()

            # 更新 Job 状态为 running
            async with self._session_factory() as session:
                result = await session.execute(
                    select(TrainingJob).where(TrainingJob.id == job.id)
                )
                j = result.scalar_one()
                j.status = "running"
                j.started_at = datetime.now(timezone.utc)
                await session.commit()

            await self._complete_step(job, Step.STARTING_TRAINING, {"pid": pid})
            await self._advance_step(job.id, Step.MONITORING_TRAINING)
        except Exception as e:
            await self._fail_job(job.id, f"训练启动失败: {e}")

    async def _check_training_progress(self, job: TrainingJob) -> None:
        """读取日志，更新进度，检查进程存活。"""
        try:
            conn_key = await self._get_conn_key(job.id)
            ssh = self._get_service()._get_ssh()

            # 连接 SSH
            async with self._session_factory() as session:
                inst_result = await session.execute(
                    select(TrainingInstance)
                    .where(
                        TrainingInstance.job_id == job.id,
                        TrainingInstance.status == "running",
                    )
                    .order_by(TrainingInstance.created_at.desc())
                )
                inst = inst_result.scalar_one_or_none()

            if not inst or not inst.ssh_host:
                return

            await ssh.connect(
                host=inst.ssh_host,
                port=inst.ssh_port,
                user=inst.ssh_user or "root",
                key_path=inst.ssh_key_path,
                password=inst.ssh_password,
            )

            # 检查进程存活
            pid = (job.progress_info or {}).get("pid", "")
            if pid:
                proc_status = await ssh.execute(
                    conn_key, StepCommandBuilder.check_process(pid), timeout=10
                )
                if "stopped" in proc_status:
                    # 进程已结束，检查是成功还是失败
                    log_content = await ssh.execute(
                        conn_key,
                        StepCommandBuilder.tail_log("/root/training.log", 20),
                        timeout=10,
                    )
                    await ssh.close(conn_key)

                    # 简单判断：日志中是否有 "error"、"traceback" 等关键词
                    if any(
                        kw in log_content.lower()
                        for kw in ["error", "traceback", "exception", "failed"]
                    ):
                        await self._fail_job(
                            job.id, f"训练进程异常退出。日志: {log_content[-500:]}"
                        )
                    else:
                        await self._advance_step(job.id, Step.COLLECTING_ARTIFACTS)
                    return

            # 读取最新日志
            log_content = await ssh.execute(
                conn_key,
                StepCommandBuilder.tail_log("/root/training.log", 50),
                timeout=10,
            )

            # 解析进度
            from backend.plugins.cloud_integration.log_parser import DEFAULT_LOG_PATTERN

            pattern = job.log_pattern or DEFAULT_LOG_PATTERN
            progress = LogParser.parse_training_log(log_content, pattern)

            # 如果没有匹配，尝试 HuggingFace JSON 格式
            if not progress:
                progress = LogParser.parse_json_log(log_content)

            if progress:
                async with self._session_factory() as session:
                    result = await session.execute(
                        select(TrainingJob).where(TrainingJob.id == job.id)
                    )
                    j = result.scalar_one()
                    j.progress_info = j.progress_info or {}
                    j.progress_info.update(progress)
                    j.last_heartbeat = (
                        datetime.now(timezone.utc)
                        if hasattr(j, "last_heartbeat")
                        else j.progress_info.get("last_update")
                    )
                    await session.commit()

            await ssh.close(conn_key)

        except Exception as e:
            logger.warning(f"任务 {job.id} 进度更新失败: {e}")

    async def _step_collect_artifacts(self, job: TrainingJob) -> None:
        """拉取训练产物。"""
        await self._begin_step(job, Step.COLLECTING_ARTIFACTS)
        try:
            conn_key = await self._get_conn_key(job.id)
            ssh = self._get_service()._get_ssh()

            # 列出产物文件
            files_output = await ssh.execute(
                conn_key, StepCommandBuilder.list_output_files(), timeout=30
            )
            artifact_files = [f for f in files_output.strip().split("\n") if f]

            # 简单记录产物路径
            async with self._session_factory() as session:
                result = await session.execute(
                    select(TrainingJob).where(TrainingJob.id == job.id)
                )
                j = result.scalar_one()
                j.artifacts = artifact_files or []
                j.result_path = artifact_files[0] if artifact_files else None
                await session.commit()

            await self._complete_step(
                job, Step.COLLECTING_ARTIFACTS, {"files": artifact_files}
            )
            await self._advance_step(job.id, Step.SHUTTING_DOWN)
        except Exception as e:
            logger.warning(f"任务 {job.id} 产物收集失败: {e}")
            # 产物拉取失败不阻断流程，继续关停
            await self._advance_step(job.id, Step.SHUTTING_DOWN)

    async def _step_shutdown_instance(self, job: TrainingJob) -> None:
        """停止实例，结算费用。"""
        await self._begin_step(job, Step.SHUTTING_DOWN)
        try:
            service = self._get_service()

            # 获取实例
            async with self._session_factory() as session:
                inst_result = await session.execute(
                    select(TrainingInstance)
                    .where(TrainingInstance.job_id == job.id)
                    .order_by(TrainingInstance.created_at.desc())
                )
                inst = inst_result.scalar_one_or_none()

            if inst and inst.status == "running":
                await service.stop_instance(inst.id)

            # 计算并回写费用
            async with self._session_factory() as session:
                cost_result = await session.execute(
                    select(TrainingCost)
                    .where(
                        TrainingCost.job_id == job.id,
                        TrainingCost.instance_id == (inst.id if inst else uuid.uuid4()),
                    )
                    .order_by(TrainingCost.recorded_at.desc())
                )
                cost = cost_result.scalar_one_or_none()

                result = await session.execute(
                    select(TrainingJob).where(TrainingJob.id == job.id)
                )
                j = result.scalar_one()
                j.status = "completed"
                j.completed_at = datetime.now(timezone.utc)
                if cost:
                    j.gpu_hours = cost.duration_hours
                    j.total_cost = cost.total_cost
                await session.commit()

            await self._complete_step(job, Step.SHUTTING_DOWN, {})
            await self._advance_step(job.id, Step.COMPLETED)
        except Exception as e:
            await self._fail_job(job.id, f"实例关停失败: {e}")

    # --- 辅助方法 ---

    async def _advance_step(self, job_id: uuid.UUID, new_step: str) -> None:
        """原子推进步骤（CAS 操作）。"""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE training_jobs SET orchestrator_step = :new_step "
                    "WHERE id = :job_id"
                ),
                {"new_step": new_step, "job_id": str(job_id)},
            )
            await session.commit()
            if result.rowcount == 0:
                logger.warning(f"任务 {job_id} 步骤推进被跳过（记录未找到）")

    async def _fail_job(self, job_id: uuid.UUID, error: str) -> None:
        """标记任务失败。"""
        logger.error(f"任务 {job_id} 失败: {error}")
        async with self._session_factory() as session:
            await session.execute(
                text(
                    "UPDATE training_jobs SET "
                    "orchestrator_step = :step, orchestrator_error = :error, "
                    "status = 'failed', completed_at = :now "
                    "WHERE id = :job_id"
                ),
                {
                    "step": Step.FAILED,
                    "error": error,
                    "now": datetime.now(timezone.utc).isoformat(),
                    "job_id": str(job_id),
                },
            )
            await session.commit()

    async def _begin_step(self, job: TrainingJob, step_name: str) -> None:
        """记录步骤开始。"""
        async with self._session_factory() as session:
            step = TrainingTaskStep(
                job_id=job.id,
                step_name=step_name,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            session.add(step)
            await session.commit()

    async def _complete_step(
        self, job: TrainingJob, step_name: str, result_data: dict
    ) -> None:
        """标记步骤完成。"""
        async with self._session_factory() as session:
            await session.execute(
                text(
                    "UPDATE training_task_steps SET "
                    "status = 'completed', completed_at = :now, result_data = :result "
                    "WHERE job_id = :job_id AND step_name = :step AND status = 'running' "  # noqa: E501
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {
                    "now": datetime.now(timezone.utc).isoformat(),
                    "result": str(result_data),
                    "job_id": str(job.id),
                    "step": step_name,
                },
            )
            await session.commit()

    async def _retry_step(self, job: TrainingJob, step_name: str, error: str) -> None:
        """重试步骤。"""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT retry_count FROM training_task_steps "
                    "WHERE job_id = :job_id AND step_name = :step AND status = 'running' "  # noqa: E501
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"job_id": str(job.id), "step": step_name},
            )
            row = result.fetchone()
            retry_count = row[0] if row else 0

            if retry_count >= self.MAX_RETRY:
                await self._fail_job(job.id, f"步骤 {step_name} 重试耗尽: {error}")
                return

            # 更新重试计数
            await session.execute(
                text(
                    "UPDATE training_task_steps SET retry_count = retry_count + 1, "
                    "error_message = :error WHERE job_id = :job_id "
                    "AND step_name = :step AND status = 'running' "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"error": error, "job_id": str(job.id), "step": step_name},
            )
            await session.commit()
            logger.warning(
                f"任务 {job.id} 步骤 {step_name} 重试 {retry_count + 1}/{self.MAX_RETRY}: {error}"  # noqa: E501
            )

    async def _get_conn_key(self, job_id: uuid.UUID) -> str:
        """获取 Job 关联实例的 SSH 连接 key。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(TrainingInstance)
                .where(
                    TrainingInstance.job_id == job_id,
                    TrainingInstance.status == "running",
                )
                .order_by(TrainingInstance.created_at.desc())
            )
            inst = result.scalar_one_or_none()
            if not inst or not inst.ssh_host:
                raise RuntimeError(f"任务 {job_id} 没有运行中的实例")
            return f"{inst.ssh_host}:{inst.ssh_port}"

    # --- 延迟初始化 ---

    @property
    def _session_factory(self):
        if self._engine is not None:
            return async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )
        # 回退到容器的 session factory（用于测试或未调用 start 的场景）
        db = self.container.get("db")
        return db["session_factory"]

    def _get_service(self):
        return self.container.get("cloud_training")
