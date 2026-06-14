import { get, type RequestConfig } from '../request'
import type { ApiListParams, Paginated } from './types/common'

export interface PluginSummary {
  id: string
  name: string
  description?: string
  version?: string
  status?: string
  author?: string
}

export interface MonitorTemplate {
  id: string
  name: string
  description?: string
}

export const getMonitorTemplatesApi = (config?: RequestConfig) =>
  get<MonitorTemplate[]>('/monitor/templates', undefined, config)

export const getPluginLikeListApi = (params?: ApiListParams, config?: RequestConfig) =>
  get<Paginated<PluginSummary>>('/assets', params, config)
