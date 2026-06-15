import { get, type RequestConfig } from '../../../lib/services/request'

export interface RequestLogItem {
  id: string
  ip: string
  method: string
  path: string
  status_code: number
  user_agent: string | null
  referer: string | null
  duration_ms: number
  user_id: string | null
  region: string | null
  isp: string | null
  action: string
  created_at: string
}

export interface IpActionCounterItem {
  id: number
  ip: string
  action: string
  action_date: string
  hour: number
  count: number
}

export interface PaginatedLogs {
  total: number
  page: number
  page_size: number
  items: RequestLogItem[]
}

export interface PaginatedCounters {
  total: number
  page: number
  page_size: number
  items: IpActionCounterItem[]
}

export interface TopIpItem {
  ip: string
  count: number
}

export interface TrendItem {
  date: string
  count: number
}

export interface LogQueryParams {
  ip?: string
  action?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export const queryRequestLogsApi = (params: LogQueryParams, config?: RequestConfig) =>
  get<PaginatedLogs>('/request-log/query', params, config)

export const getTopIpsApi = (
  params?: { action?: string; days?: number; limit?: number },
  config?: RequestConfig
) => get<TopIpItem[]>('/request-log/top-ips', params, config)

export const getTrendApi = (params?: { action?: string; days?: number }, config?: RequestConfig) =>
  get<TrendItem[]>('/request-log/trend', params, config)

export const getCountersApi = (params: LogQueryParams, config?: RequestConfig) =>
  get<PaginatedCounters>('/request-log/counters', params, config)

export const listActionsApi = (config?: RequestConfig) =>
  get<string[]>('/request-log/actions', undefined, config)
