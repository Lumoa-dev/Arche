import { get, type RequestConfig } from '../request'
import type { ApiListParams, BackendPaginated } from './types/common'
import { normalizePaginated } from './types/common'

export interface AssetItem {
  id: string
  name: string
  asset_type: string
  created_at?: string
}

export interface AssetFileStats {
  count: number
  total_size_bytes: number
}

export interface AssetStats {
  total: number
  by_type: Record<string, number | AssetFileStats>
}

export interface AssetQueryParams extends ApiListParams {
  asset_type?: string
}

export interface AssetSearchParams extends AssetQueryParams {
  keyword?: string
  date_from?: string
  date_to?: string
}

export const getAssetsApi = (params?: AssetQueryParams, config?: RequestConfig) =>
  get<BackendPaginated<AssetItem>>('/assets', params, config).then(normalizePaginated)

export const searchAssetsApi = (params?: AssetSearchParams, config?: RequestConfig) =>
  get<BackendPaginated<AssetItem>>('/assets/search', params, config).then(normalizePaginated)

export const getAssetStatsApi = (config?: RequestConfig) =>
  get<AssetStats>('/assets/stats', undefined, config)
