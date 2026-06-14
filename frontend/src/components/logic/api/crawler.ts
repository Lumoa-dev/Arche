import { get, post, type RequestConfig } from '../request'
import type { ApiListParams, BackendPaginated } from './types/common'
import { normalizePaginated } from './types/common'

export interface CrawlRecord {
  id: string
  url: string
  status: string
  created_at?: string
}

export interface CrawlerStatus {
  running: boolean
  queue_size?: number
}

export const getCrawlerStatusApi = (config?: RequestConfig) =>
  get<CrawlerStatus>('/crawler/status', undefined, config)

export const startCrawlerApi = (config?: RequestConfig) =>
  post<void>('/crawler/start', undefined, config)

export const stopCrawlerApi = (config?: RequestConfig) =>
  post<void>('/crawler/stop', undefined, config)

export const getCrawlerRecordsApi = (params?: ApiListParams, config?: RequestConfig) =>
  get<BackendPaginated<CrawlRecord>>('/crawler/records', params, config).then(normalizePaginated)

export const getCrawlerRecordApi = (recordId: string, config?: RequestConfig) =>
  get<CrawlRecord>(`/crawler/records/${recordId}`, undefined, config)

export const getCrawlerStatsApi = (config?: RequestConfig) =>
  get<Record<string, unknown>>('/crawler/stats', undefined, config)

export const addCrawlerSeedApi = (url: string, config?: RequestConfig) =>
  post<void>('/crawler/seeds', { url }, config)

export const getCrawlerSeedsApi = (config?: RequestConfig) =>
  get<string[]>('/crawler/seeds', undefined, config)
