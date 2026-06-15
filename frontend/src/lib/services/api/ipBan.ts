import { get, post, put, type RequestConfig } from '../../../lib/services/request'
import type { ApiListParams, Paginated } from './types/common'

export interface IpBanRecord {
  id: number
  ip_or_cidr: string
  ban_type: 'auto' | 'manual'
  reason: string
  rule_id?: string | null
  banned_by?: string | null
  created_at?: string | null
  expires_at?: string | null
  is_active: boolean
}

export interface IpBanLogRecord {
  id: number
  ban_id?: number | null
  ip_or_cidr: string
  action: 'ban' | 'unban'
  ban_type: 'auto' | 'manual'
  reason: string
  operator?: string | null
  detail?: string | null
  created_at?: string | null
}

export interface AutoBanRule {
  id: string
  name: string
  enabled: boolean
  threshold: number
  window_seconds: number
  ban_duration_minutes: number
  description?: string | null
}

export interface BanIpPayload {
  ip_or_cidr: string
  reason?: string
  duration_minutes?: number | null
}

export interface BatchUnbanPayload {
  ban_ids: number[]
}

export interface UpdateRulePayload {
  enabled?: boolean
  threshold?: number
  window_seconds?: number
  ban_duration_minutes?: number
  description?: string
  name?: string
}

export interface IpBanQueryParams extends ApiListParams {
  ban_type?: string
  is_active?: string
  keyword?: string
}

export interface IpBanStats {
  total_bans: number
  active_bans: number
  auto_bans: number
  manual_bans: number
  today_bans: number
}

export const getIpBansApi = (params?: IpBanQueryParams, config?: RequestConfig) =>
  get<Paginated<IpBanRecord>>('/ip-ban/bans', params, config)

export const banIpApi = (payload: BanIpPayload, config?: RequestConfig) =>
  post<IpBanRecord>('/ip-ban/bans', payload, config)

export const batchUnbanApi = (payload: BatchUnbanPayload, config?: RequestConfig) =>
  post<{ count: number }>('/ip-ban/bans/batch-unban', payload, config)

export const unbanIpApi = (banId: number, config?: RequestConfig) =>
  post<IpBanRecord>(`/ip-ban/bans/${banId}/unban`, undefined, config)

export const getBanLogsApi = (
  params?: ApiListParams & { action?: string },
  config?: RequestConfig
) => get<Paginated<IpBanLogRecord>>('/ip-ban/logs', params, config)

export const getBanRulesApi = (config?: RequestConfig) =>
  get<AutoBanRule[]>('/ip-ban/rules', undefined, config)

export const updateBanRuleApi = (
  ruleId: string,
  payload: UpdateRulePayload,
  config?: RequestConfig
) => put<AutoBanRule>(`/ip-ban/rules/${ruleId}`, payload, config)

export const getIpBanStatsApi = (config?: RequestConfig) =>
  get<IpBanStats>('/ip-ban/stats', undefined, config)
