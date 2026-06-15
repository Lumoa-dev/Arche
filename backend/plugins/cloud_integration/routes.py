"""云集成插件 —— API 路由。"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.core.container import ServiceContainer
from backend.core.middleware import require_level, require_user

router = APIRouter(prefix="/api/cloud", tags=["cloud"])
logger = logging.getLogger(__name__)


# --- 工作台统计 ---
@router.get("/stats")
@require_level(0)
async def get_stats(request: Request):
    """云工作台统计数据（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")

    jobs = await service.list_jobs(page=1, page_size=100, status_filter="running")
    running_jobs = jobs.get("total", 0)

    # 运行中实例数（简化，实际应该统计 provider 实例）
    running_instances = sum(
        1 for j in jobs.get("items", []) if j.get("orchestrator_step") == "running"
    )

    return {
        "code": "ok",
        "message": "获取成功",
        "data": {
            "running_jobs": running_jobs,
            "running_instances": running_instances,
        },
    }


# --- 请求体模型 ---
class CreateJobRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256, description="任务名称")
    config: dict = Field(..., description="模型配置（JSON）")
    repo_url: str = Field(..., description="Git 仓库 URL（必填）")
    repo_branch: str = Field(default="main", description="分支名")
    repo_token: str | None = Field(default=None, description="Git 认证 token")
    dataset_config: dict = Field(default={}, description="数据集配置")
    training_script: str = Field(default="train.py", description="训练脚本路径")
    requirements_file: str = Field(
        default="requirements.txt", description="依赖文件路径"
    )
    log_pattern: str | None = Field(default=None, description="日志解析正则")
    provider: str = Field(default="mock", description="Provider 名称")
    gpu_type: str = Field(default="RTX4090", description="GPU 类型")
    instance_name: str | None = Field(default=None, description="实例名称")


class CreateInstanceRequest(BaseModel):
    instance_name: str = Field(
        ..., min_length=1, max_length=256, description="实例名称"
    )
    gpu_type: str = Field(..., min_length=1, max_length=64, description="GPU 类型")
    provider: str = Field(default="mock", description="Provider 名称")


# --- 任务 CRUD（P0） ---
@router.get("/jobs")
@require_level(0)
async def list_jobs(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str | None = Query(None, description="状态过滤"),
):
    """训练任务列表（P0）。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.list_jobs(
        creator_id=uuid.UUID(user["id"]),
        page=page,
        page_size=page_size,
        status_filter=status,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/jobs/{job_id}")
@require_level(0)
async def get_job(job_id: str, request: Request):
    """训练任务详情（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.get_job(uuid.UUID(job_id))
    return {"code": "ok", "message": "获取成功", "data": result}


@router.post("/jobs")
@require_level(0)
async def create_job(req: CreateJobRequest, request: Request):
    """创建训练任务（P0）。"""
    user = require_user(request)
    creator_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")

    # 将 provider/gpu_type/instance_name 存入 model_config
    model_config = dict(req.config)
    model_config.setdefault("provider", req.provider)
    model_config.setdefault("gpu_type", req.gpu_type)
    if req.instance_name:
        model_config.setdefault("instance_name", req.instance_name)

    result = await service.create_job(
        creator_id=creator_id,
        name=req.name,
        model_config=model_config,
        repo_url=req.repo_url,
        repo_branch=req.repo_branch,
        repo_token=req.repo_token,
        dataset_config=req.dataset_config,
        training_script=req.training_script,
        requirements_file=req.requirements_file,
        log_pattern=req.log_pattern,
    )
    return {"code": "ok", "message": "创建成功", "data": result}


async def _verify_job_owner(service, job_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    """校验当前用户是否为训练任务的创建者。"""
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    creator_id = uuid.UUID(job["creator_id"])
    if creator_id != user_id:
        raise HTTPException(status_code=403, detail="无权操作其他用户的训练任务")
    return job


@router.delete("/jobs/{job_id}")
@require_level(0)
async def delete_job(job_id: str, request: Request):
    """删除训练任务（P0）。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    await _verify_job_owner(service, uuid.UUID(job_id), uuid.UUID(user["id"]))
    await service.delete_job(uuid.UUID(job_id))
    return {"code": "ok", "message": "删除成功", "data": {}}


# --- 任务状态操作（P0） ---
@router.post("/jobs/{job_id}/start")
@require_level(0)
async def start_job(job_id: str, request: Request):
    """启动训练任务（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.start_job(uuid.UUID(job_id))
    return {"code": "ok", "message": "启动成功", "data": result}


@router.post("/jobs/{job_id}/stop")
@require_level(0)
async def stop_job(job_id: str, request: Request):
    """停止训练任务（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.stop_job(uuid.UUID(job_id))
    return {"code": "ok", "message": "停止成功", "data": result}


@router.post("/jobs/{job_id}/complete")
@require_level(0)
async def complete_job(
    job_id: str,
    request: Request,
    result_path: str | None = Query(None, description="结果路径"),
):
    """标记任务完成（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.complete_job(uuid.UUID(job_id), result_path=result_path)
    return {"code": "ok", "message": "标记完成", "data": result}


@router.post("/jobs/{job_id}/fail")
@require_level(0)
async def fail_job(
    job_id: str,
    request: Request,
    error_message: str = Query(..., description="错误信息"),
):
    """标记任务失败（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.fail_job(uuid.UUID(job_id), error_message=error_message)
    return {"code": "ok", "message": "标记失败", "data": result}


# --- 训练日志（P0） ---
@router.get("/jobs/{job_id}/logs")
@require_level(0)
async def get_job_logs(
    job_id: str,
    request: Request,
    lines: int = Query(100, ge=1, le=1000, description="日志行数"),
):
    """获取训练日志（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.get_job_logs(uuid.UUID(job_id), lines=lines)
    return {"code": "ok", "message": "获取成功", "data": result}


# --- 实例管理（P0） ---
@router.get("/jobs/{job_id}/instances")
@require_level(0)
async def list_instances(
    job_id: str,
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """训练实例列表（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.list_instances(
        job_id=uuid.UUID(job_id),
        page=page,
        page_size=page_size,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.post("/jobs/{job_id}/instances")
@require_level(0)
async def create_instance(job_id: str, req: CreateInstanceRequest, request: Request):
    """创建训练实例（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.create_instance(
        job_id=uuid.UUID(job_id),
        instance_name=req.instance_name,
        gpu_type=req.gpu_type,
        provider=req.provider,
    )
    return {"code": "ok", "message": "创建成功", "data": result}


@router.post("/instances/{instance_id}/start")
@require_level(0)
async def start_instance(instance_id: str, request: Request):
    """启动训练实例（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.start_instance(uuid.UUID(instance_id))
    return {"code": "ok", "message": "启动成功", "data": result}


@router.post("/instances/{instance_id}/stop")
@require_level(0)
async def stop_instance(instance_id: str, request: Request):
    """停止训练实例（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.stop_instance(uuid.UUID(instance_id))
    return {"code": "ok", "message": "停止成功", "data": result}


# --- 费用查询（P0） ---
@router.get("/costs")
@require_level(0)
async def get_costs(
    request: Request,
    job_id: str | None = Query(None, description="按任务 ID 过滤"),
    start_date: str | None = Query(None, description="起始日期 ISO 8601"),
    end_date: str | None = Query(None, description="结束日期 ISO 8601"),
):
    """训练费用汇总（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.get_costs(
        job_id=uuid.UUID(job_id) if job_id else None,
        start_date=start_date,
        end_date=end_date,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


# --- GPU 指标（P0） ---
@router.get("/instances/{instance_id}/gpu-metrics")
@require_level(0)
async def get_gpu_metrics(instance_id: str, request: Request):
    """GPU 实时指标（P0）。"""
    from sqlalchemy import select

    from backend.plugins.cloud_integration.models import TrainingInstance
    from backend.plugins.cloud_integration.providers.registry import get_provider

    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")

    async with service.session_factory() as session:
        inst_result = await session.execute(
            select(TrainingInstance).where(
                TrainingInstance.id == uuid.UUID(instance_id)
            )
        )
        inst = inst_result.scalar_one_or_none()

    if not inst:
        return {"code": "error", "message": "实例不存在", "data": {}}

    cloud_provider = get_provider(inst.provider)
    try:
        metrics = await cloud_provider.get_gpu_metrics(instance_id)
        return {"code": "ok", "message": "获取成功", "data": metrics}
    except Exception:
        logger.exception("Failed to fetch GPU metrics for instance %s", instance_id)
        return {"code": "error", "message": "获取 GPU 指标失败", "data": {}}


# --- 编排控制（P1） ---
@router.post("/jobs/{job_id}/launch")
@require_level(0)
async def launch_job(job_id: str, request: Request):
    """一键启动全链路（P1）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.launch_job(uuid.UUID(job_id))
    return {"code": "ok", "message": "已提交编排任务", "data": result}


@router.get("/jobs/{job_id}/progress")
@require_level(0)
async def get_job_progress(job_id: str, request: Request):
    """查询实时训练进度（P1）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.get_job_progress(uuid.UUID(job_id))
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/jobs/{job_id}/steps")
@require_level(0)
async def get_job_steps(job_id: str, request: Request):
    """查询步骤执行历史（P1）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.get_job_steps(uuid.UUID(job_id))
    return {"code": "ok", "message": "获取成功", "data": result}


# --- 数据集管理（新） ---
class CreateDatasetRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256, description="数据集名称")
    description: str | None = Field(default=None, description="数据集描述")
    path: str = Field(..., description="虚拟路径，如 datasets/my_data/v1")
    source: str = Field(
        default="local", description="数据来源：local/modelscope/aliyun"
    )
    tags: list[str] | None = Field(default=[], description="标签列表")
    config: dict | None = Field(
        default={}, description="扩展配置（如modelscope ID、token等）"
    )


@router.get("/datasets")
@require_level(0)
async def list_datasets(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    source: str | None = Query(None, description="按来源过滤"),
):
    """数据集列表（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    user = require_user(request)
    result = await service.list_datasets(
        creator_id=uuid.UUID(user["id"]),
        page=page,
        page_size=page_size,
        source_filter=source,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.post("/datasets")
@require_level(0)
async def create_dataset(req: CreateDatasetRequest, request: Request):
    """创建/导入数据集（P0）。"""
    user = require_user(request)
    creator_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")

    result = await service.create_dataset(
        creator_id=creator_id,
        name=req.name,
        description=req.description,
        path=req.path,
        source=req.source,
        tags=req.tags,
        config=req.config,
    )
    return {"code": "ok", "message": "创建成功", "data": result}


@router.get("/datasets/{dataset_id}")
@require_level(0)
async def get_dataset(dataset_id: str, request: Request):
    """数据集详情（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.get_dataset(uuid.UUID(dataset_id))
    return {"code": "ok", "message": "获取成功", "data": result}


@router.delete("/datasets/{dataset_id}")
@require_level(0)
async def delete_dataset(dataset_id: str, request: Request):
    """删除数据集（P0）。"""
    user = require_user(request)
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    dataset = await service.get_dataset(uuid.UUID(dataset_id))
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    if uuid.UUID(dataset["created_by"]) != uuid.UUID(user["id"]):
        raise HTTPException(status_code=403, detail="无权删除其他用户的数据集")
    await service.delete_dataset(uuid.UUID(dataset_id))
    return {"code": "ok", "message": "删除成功", "data": {}}


@router.post("/datasets/{dataset_id}/sync")
@require_level(0)
async def sync_dataset(dataset_id: str, request: Request):
    """同步数据集到阿里云（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.sync_dataset(uuid.UUID(dataset_id))
    return {"code": "ok", "message": "同步任务已提交", "data": result}


# --- 代码仓库管理（新） ---
class CreateCodeRepoRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256, description="仓库名称")
    git_url: str = Field(..., description="Git仓库URL")
    git_branch: str = Field(default="main", description="分支名")
    git_token: str | None = Field(default=None, description="Git认证token（加密存储）")


@router.get("/repos")
@require_level(0)
async def list_repos(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """代码仓库列表（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    user = require_user(request)
    result = await service.list_repos(
        creator_id=uuid.UUID(user["id"]),
        page=page,
        page_size=page_size,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.post("/repos")
@require_level(0)
async def create_repo(req: CreateCodeRepoRequest, request: Request):
    """添加代码仓库（P0）。"""
    user = require_user(request)
    creator_id = uuid.UUID(user["id"])

    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")

    result = await service.create_repo(
        creator_id=creator_id,
        name=req.name,
        git_url=req.git_url,
        git_branch=req.git_branch,
        git_token=req.git_token,
    )
    return {"code": "ok", "message": "添加成功", "data": result}


@router.delete("/repos/{repo_id}")
@require_level(0)
async def delete_repo(repo_id: str, request: Request):
    """删除代码仓库（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    await service.delete_repo(uuid.UUID(repo_id))
    return {"code": "ok", "message": "删除成功", "data": {}}


@router.post("/repos/{repo_id}/sync")
@require_level(0)
async def sync_repo(repo_id: str, request: Request):
    """同步代码仓库最新版本（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.sync_repo(uuid.UUID(repo_id))
    return {"code": "ok", "message": "同步任务已提交", "data": result}


# --- 制品管理（新） ---
@router.get("/artifacts")
@require_level(0)
async def list_artifacts(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    job_id: str | None = Query(None, description="按训练任务过滤"),
    artifact_type: str | None = Query(
        None, description="按制品类型过滤：checkpoint/log/config"
    ),
):
    """制品列表（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    user = require_user(request)
    result = await service.list_artifacts(
        creator_id=uuid.UUID(user["id"]),
        job_id=uuid.UUID(job_id) if job_id else None,
        artifact_type=artifact_type,
        page=page,
        page_size=page_size,
    )
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/artifacts/{artifact_id}")
@require_level(0)
async def get_artifact(artifact_id: str, request: Request):
    """制品详情（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    result = await service.get_artifact(uuid.UUID(artifact_id))
    return {"code": "ok", "message": "获取成功", "data": result}


@router.get("/artifacts/{artifact_id}/download")
@require_level(0)
async def download_artifact(artifact_id: str, request: Request):
    """下载制品（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    download_url = await service.download_artifact(uuid.UUID(artifact_id))
    return {
        "code": "ok",
        "message": "获取下载链接成功",
        "data": {"download_url": download_url},
    }


@router.delete("/artifacts/{artifact_id}")
@require_level(0)
async def delete_artifact(artifact_id: str, request: Request):
    """删除制品（P0）。"""
    container: ServiceContainer = request.app.state.container
    service = container.get("cloud_training")
    await service.delete_artifact(uuid.UUID(artifact_id))
    return {"code": "ok", "message": "删除成功", "data": {}}
