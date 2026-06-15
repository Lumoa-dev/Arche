import { del, get, post, type RequestConfig } from '../../../lib/services/request'
import type { ApiListParams, BackendPaginated, Paginated } from './types/common'
import { normalizePaginated } from './types/common'

/** 训练任务 */
export interface CloudJob {
  id: string
  name: string
  creator_id?: string
  model_config?: Record<string, unknown>
  status: string
  logs_path?: string
  result_path?: string
  error_message?: string
  gpu_hours?: number
  total_cost?: number
  artifacts?: string[]
  artifact_verified?: boolean
  repo_url?: string
  repo_branch?: string
  dataset_config?: Record<string, unknown>
  training_script?: string
  requirements_file?: string
  created_at?: string
  orchestrator_step?: string
}

/** 创建任务请求 */
export interface CreateCloudJobPayload {
  name: string
  config?: Record<string, unknown>
  repo_url?: string
  repo_branch?: string
  repo_token?: string
  dataset_config?: Record<string, unknown>
  training_script?: string
  requirements_file?: string
  provider?: string
  gpu_type?: string
  log_pattern?: string
  instance_name?: string
}

/** 训练实例 */
export interface CloudInstance {
  id: string
  job_id?: string
  provider?: string
  provider_instance_id?: string
  instance_name?: string
  gpu_type?: string
  gpu_count?: number
  ssh_host?: string
  ssh_port?: number
  status: string
  created_at?: string
  started_at?: string
}

/** 训练费用 */
export interface CloudCosts {
  total_cost: number
  breakdown?: Array<{
    job_id: string
    instance_id: string
    provider: string
    gpu_type: string
    hourly_rate: number
    duration_hours: number
    total_cost: number
    recorded_at: string
  }>
}

/** 训练进度 */
export interface CloudJobProgress {
  job_id: string
  status: string
  orchestrator_step?: string
  progress_info?: Record<string, unknown>
}

/** 任务步骤 */
export interface CloudJobStep {
  id: string
  step_name: string
  status: string
  started_at?: string
  completed_at?: string
  error_message?: string
  retry_count?: number
}

/** 数据集 */
export interface CloudDataset {
  id: string
  name: string
  description?: string
  path: string
  source?: string
  size_bytes?: number
  file_count?: number
  tags?: string[]
  config?: Record<string, unknown>
  created_by?: string
  created_at?: string
  updated_at?: string
}

/** 代码仓库 */
export interface CloudRepo {
  id: string
  name: string
  git_url: string
  git_branch?: string
  created_by?: string
  created_at?: string
}

/** 制品 */
export interface CloudArtifact {
  id: string
  job_id?: string
  name: string
  path?: string
  artifact_type?: string
  size_bytes?: number
  storage_location?: string
  created_at?: string
}

export interface CloudStats {
  running_jobs: number
  running_instances: number
}

export const getCloudStatsApi = (config?: RequestConfig) =>
  get<CloudStats>('/cloud/stats', undefined, config)

export const getCloudJobsApi = (
  params?: ApiListParams & { status?: string },
  config?: RequestConfig
) => get<BackendPaginated<CloudJob>>('/cloud/jobs', params, config).then(normalizePaginated)

export const getCloudJobDetailApi = (jobId: string, config?: RequestConfig) =>
  get<CloudJob>(`/cloud/jobs/${jobId}`, undefined, config)

export const createCloudJobApi = (payload: CreateCloudJobPayload, config?: RequestConfig) =>
  post<CloudJob>('/cloud/jobs', payload, config)

export const deleteCloudJobApi = (jobId: string, config?: RequestConfig) =>
  del<void>(`/cloud/jobs/${jobId}`, undefined, config)

export const startCloudJobApi = (jobId: string, config?: RequestConfig) =>
  post<CloudJob>(`/cloud/jobs/${jobId}/start`, undefined, config)

export const stopCloudJobApi = (jobId: string, config?: RequestConfig) =>
  post<CloudJob>(`/cloud/jobs/${jobId}/stop`, undefined, config)

export const completeCloudJobApi = (jobId: string, config?: RequestConfig) =>
  post<CloudJob>(`/cloud/jobs/${jobId}/complete`, undefined, config)

export const failCloudJobApi = (jobId: string, error_message: string, config?: RequestConfig) =>
  post<CloudJob>(`/cloud/jobs/${jobId}/fail`, { error_message }, config)

export const getCloudJobLogsApi = (jobId: string, lines?: number, config?: RequestConfig) =>
  get<{ logs: string[]; total_lines: number }>(`/cloud/jobs/${jobId}/logs`, { lines }, config)

export const getCloudInstancesApi = (
  jobId: string,
  params?: ApiListParams,
  config?: RequestConfig
) =>
  get<BackendPaginated<CloudInstance>>(`/cloud/jobs/${jobId}/instances`, params, config).then(
    normalizePaginated
  )

export const createCloudInstanceApi = (
  jobId: string,
  payload: { instance_name: string; gpu_type: string; provider?: string },
  config?: RequestConfig
) => post<CloudInstance>(`/cloud/jobs/${jobId}/instances`, payload, config)

export const startCloudInstanceApi = (instanceId: string, config?: RequestConfig) =>
  post<Record<string, unknown>>(`/cloud/instances/${instanceId}/start`, undefined, config)

export const stopCloudInstanceApi = (instanceId: string, config?: RequestConfig) =>
  post<Record<string, unknown>>(`/cloud/instances/${instanceId}/stop`, undefined, config)

export const getCloudJobProgressApi = (jobId: string, config?: RequestConfig) =>
  get<CloudJobProgress>(`/cloud/jobs/${jobId}/progress`, undefined, config)

export const getCloudJobStepsApi = (jobId: string, config?: RequestConfig) =>
  get<CloudJobStep[]>(`/cloud/jobs/${jobId}/steps`, undefined, config)

export const launchCloudJobApi = (jobId: string, config?: RequestConfig) =>
  post<Record<string, unknown>>(`/cloud/jobs/${jobId}/launch`, undefined, config)

export const getCloudCostsApi = (
  params?: { job_id?: string; start_date?: string; end_date?: string },
  config?: RequestConfig
) => get<CloudCosts>('/cloud/costs', params, config)

export const getGpuMetricsApi = (instanceId: string, config?: RequestConfig) =>
  get<Record<string, unknown>>(`/cloud/instances/${instanceId}/gpu-metrics`, undefined, config)

/**
 * 数据集管理
 */
export const listDatasetsApi = (
  params?: ApiListParams & { source?: string },
  config?: RequestConfig
) => get<Paginated<CloudDataset>>('/cloud/datasets', params, config)

export const createDatasetApi = (
  payload: {
    name: string
    description?: string
    path: string
    source?: string
    tags?: string[]
    config?: Record<string, unknown>
  },
  config?: RequestConfig
) => post<CloudDataset>('/cloud/datasets', payload, config)

export const getDatasetApi = (datasetId: string, config?: RequestConfig) =>
  get<CloudDataset>(`/cloud/datasets/${datasetId}`, undefined, config)

export const deleteDatasetApi = (datasetId: string, config?: RequestConfig) =>
  del<void>(`/cloud/datasets/${datasetId}`, undefined, config)

export const syncDatasetApi = (datasetId: string, config?: RequestConfig) =>
  post<Record<string, unknown>>(`/cloud/datasets/${datasetId}/sync`, undefined, config)

/**
 * 代码仓库管理
 */
export const listReposApi = (params?: ApiListParams, config?: RequestConfig) =>
  get<Paginated<CloudRepo>>('/cloud/repos', params, config)

export const createRepoApi = (
  payload: { name: string; git_url: string; git_branch?: string; git_token?: string },
  config?: RequestConfig
) => post<CloudRepo>('/cloud/repos', payload, config)

export const deleteRepoApi = (repoId: string, config?: RequestConfig) =>
  del<void>(`/cloud/repos/${repoId}`, undefined, config)

export const syncRepoApi = (repoId: string, config?: RequestConfig) =>
  post<Record<string, unknown>>(`/cloud/repos/${repoId}/sync`, undefined, config)

/**
 * 制品管理
 */
export const listArtifactsApi = (
  params?: ApiListParams & { job_id?: string; artifact_type?: string },
  config?: RequestConfig
) => get<Paginated<CloudArtifact>>('/cloud/artifacts', params, config)

export const getArtifactApi = (artifactId: string, config?: RequestConfig) =>
  get<CloudArtifact>(`/cloud/artifacts/${artifactId}`, undefined, config)

export const downloadArtifactApi = (artifactId: string, config?: RequestConfig) =>
  get<{ download_url: string }>(`/cloud/artifacts/${artifactId}/download`, undefined, config)

export const deleteArtifactApi = (artifactId: string, config?: RequestConfig) =>
  del<void>(`/cloud/artifacts/${artifactId}`, undefined, config)
