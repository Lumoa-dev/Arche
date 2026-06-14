import { del, get, put as putReq, upload, type RequestConfig } from '../request'
import type { ApiListParams, Paginated } from './types/common'

export interface OSSFile {
  id: string
  owner_id: string | null
  tenant_id: string | null
  path: string
  size: number
  mime_type: string
  storage_type: string
  is_private: boolean
  created_at: string | null
  last_accessed: string | null
}

export interface OSSUploadResponse {
  code: string
  message: string
  data: OSSFile
}

export interface OSSFileListResponse {
  code: string
  message: string
  data: {
    files: OSSFile[]
    total: number
  }
}

export const uploadOssFileApi = (file: File, isPrivate = false, config?: RequestConfig) =>
  upload<OSSUploadResponse>(`/oss/upload?is_private=${isPrivate}`, file, config).then((r) => r.data)

export const getMyOssFilesApi = (
  params?: ApiListParams & { limit?: number; offset?: number },
  config?: RequestConfig
) =>
  get<OSSFileListResponse>('/oss/my', params, config).then((r) => ({
    list: r.data.files,
    total: r.data.total,
    page: 1,
    page_size: params?.page_size || 50
  })) as Promise<Paginated<OSSFile>>

export const deleteOssFileApi = (fileId: string, config?: RequestConfig) =>
  del<void>(`/oss/files/${fileId}`, undefined, config)

export const getOssFileUrl = (fileId: string) => `/api/oss/files/${fileId}`

// ── 管理端 API ──

export interface OSSAdminStats {
  total_files: number
  total_size: number
  total_users: number
  minio_size?: number
  aliyun_size?: number
}

export interface OSSQuota {
  user_id: string
  username?: string
  quota_bytes: number
  speed_multiplier: number
  used_bytes: number
  usage_percent: number
}

export interface OSSTopUser {
  user_id: string
  username: string
  file_count: number
  total_size: number
}

export interface OSSRateLimitConfig {
  global_limit_bytes: number
}

export const getOssAdminStatsApi = (config?: RequestConfig) =>
  get<OSSAdminStats>('/oss/admin/stats', undefined, config)

export const getOssAdminTopUsersApi = (config?: RequestConfig) =>
  get<OSSTopUser[]>('/oss/admin/stats/top-users', undefined, config)

export const getOssAdminFilesApi = (
  params?: ApiListParams & { owner_id?: string },
  config?: RequestConfig
) => get<{ files: OSSFile[]; total: number }>('/oss/admin/files', params, config)

export const deleteOssAdminFileApi = (fileId: string, config?: RequestConfig) =>
  del<void>(`/oss/admin/files/${fileId}`, undefined, config)

export const getOssAdminQuotasApi = (config?: RequestConfig) =>
  get<{ items: OSSQuota[]; list: OSSQuota[]; total: number }>(
    '/oss/admin/quotas',
    undefined,
    config
  )

export const updateOssUserQuotaApi = (
  userId: string,
  payload: { quota_bytes: number; speed_multiplier?: number },
  config?: RequestConfig
) => putReq<OSSQuota>(`/oss/admin/quotas/${userId}`, payload, config)

export const getOssRateLimitApi = (config?: RequestConfig) =>
  get<OSSRateLimitConfig>('/oss/admin/rate-limit', undefined, config)

export const updateOssRateLimitApi = (
  payload: { global_limit_bytes: number },
  config?: RequestConfig
) => putReq<void>('/oss/admin/rate-limit', payload, config)
