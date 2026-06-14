import { del, get, post, put, type RequestConfig } from '../request'
import type { ApiListParams, Paginated } from './types/common'

export interface AdminUser {
  id: string
  email?: string
  username: string
  nickname: string
  avatar?: string
  bio?: string
  links?: string[]
  badges?: string[]
  is_active?: boolean
  level?: number
  blog_quality_level?: number
  /** active | deleted_by_admin | user_requested_deletion */
  deletion_status?: string
  /** violation | user_request */
  deletion_reason?: string
  deletion_expires_at?: string | null
  deleted_at?: string | null
  login_count?: number
  last_login_at?: string | null
  last_login_ip?: string | null
  last_active_at?: string | null
  created_at?: string
  updated_at?: string
}

export interface UsersQueryParams extends ApiListParams {
  status?: string
}

export interface UpdateUserPayload {
  level?: number
  is_active?: boolean
  nickname?: string
  avatar?: string
  bio?: string
  links?: string[]
}

export interface CreateAdminUserPayload {
  email: string
  username: string
  nickname?: string
  password: string
  level?: number
}

export interface SoftDeletePayload {
  reason: 'violation' | 'user_request'
  expires_in_days: 30 | 60 | 90
}

export interface HotPost {
  id: string
  title: string
  author_username: string
  views: number
  likes: number
  comments: number
  created_at: string
}

export const getUsersApi = (params?: UsersQueryParams, config?: RequestConfig) =>
  get<Paginated<AdminUser>>('/auth/users', params, config)

export const getUserDetailApi = (userId: string, config?: RequestConfig) =>
  get<AdminUser>(`/auth/users/${userId}`, undefined, config)

export const updateUserApi = (userId: string, payload: UpdateUserPayload, config?: RequestConfig) =>
  put<AdminUser>(`/auth/users/${userId}`, payload, config)

export const deleteUserApi = (userId: string, config?: RequestConfig) =>
  del<void>(`/auth/users/${userId}`, undefined, config)

export const disableUserApi = (userId: string, config?: RequestConfig) =>
  post<void>(`/auth/users/${userId}/disable`, undefined, config)

export const enableUserApi = (userId: string, config?: RequestConfig) =>
  post<void>(`/auth/users/${userId}/enable`, undefined, config)

export const createAdminUserApi = (payload: CreateAdminUserPayload, config?: RequestConfig) =>
  post<AdminUser>('/auth/admin/users', payload, config)

export const softDeleteUserApi = (
  userId: string,
  payload: SoftDeletePayload,
  config?: RequestConfig
) => post<AdminUser>(`/auth/users/${userId}/soft-delete`, payload, config)

export const getHotPostsApi = (limit?: number, config?: RequestConfig) =>
  get<HotPost[]>('/blog/admin/hot-posts', { limit }, config)

export const resetUserPasswordApi = (userId: string, newPassword: string, config?: RequestConfig) =>
  post<AdminUser>(`/auth/users/${userId}/reset-password`, { new_password: newPassword }, config)
