export interface ApiListParams {
  page?: number
  page_size?: number
}

export interface Paginated<T> {
  total: number
  page: number
  page_size: number
  list: T[]
}

export interface BackendPaginated<T> {
  total: number
  page: number
  page_size: number
  items?: T[]
  list?: T[]
}

export interface BatchActionPayload {
  post_ids: string[]
}

export const normalizePaginated = <T>(raw: BackendPaginated<T>): Paginated<T> => ({
  total: raw.total || 0,
  page: raw.page || 1,
  page_size: raw.page_size || 20,
  list: raw.list || raw.items || []
})
