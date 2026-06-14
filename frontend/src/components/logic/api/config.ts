import { del, get, post, put, type RequestConfig } from '../request'

export interface ConfigItem {
  key: string
  value: string
  group?: string
  description?: string
  is_sensitive?: boolean
}

export interface CreateConfigPayload {
  key: string
  value: string
  group?: string
  description?: string
  is_sensitive?: boolean
}

export interface ConfigListParams {
  group?: string
}

export const getConfigListApi = (params?: ConfigListParams, config?: RequestConfig) =>
  get<ConfigItem[]>('/admin/config', params, config)

export const getConfigItemApi = (key: string, config?: RequestConfig) =>
  get<ConfigItem>(`/admin/config/${key}`, undefined, config)

export const updateConfigItemApi = (key: string, value: string, config?: RequestConfig) =>
  put<ConfigItem>(`/admin/config/${key}`, { value }, config)

export const createConfigItemApi = (payload: CreateConfigPayload, config?: RequestConfig) =>
  post<ConfigItem>('/admin/config', payload, config)

export const deleteConfigItemApi = (key: string, config?: RequestConfig) =>
  del<void>(`/admin/config/${key}`, undefined, config)

export const getConfigGroupsApi = (config?: RequestConfig) =>
  get<string[]>('/admin/config/groups', undefined, config)

export const reloadConfigApi = (config?: RequestConfig) =>
  post<void>('/admin/config/reload', undefined, config)
