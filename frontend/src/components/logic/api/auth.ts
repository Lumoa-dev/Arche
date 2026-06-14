// 认证相关接口
import { get, post, type RequestConfig } from '../request'

// 登录参数
export interface LoginParams {
  identity: string
  password: string
}

export interface RegisterParams {
  email: string
  username: string
  nickname: string
  password: string
}

// 用户信息
export interface UserInfo {
  id: string
  username: string
  nickname: string
  email: string
  avatar?: string | undefined
  bio?: string | undefined
  links?: string[] | undefined
  badges?: string[] | undefined
  level: number
  blog_quality_level?: number | undefined
  is_active?: boolean | undefined
  deletion_status?: string | undefined
  deletion_reason?: string | undefined
  deletion_expires_at?: string | null | undefined
  deleted_at?: string | null | undefined
  login_count?: number | undefined
  last_login_at?: string | null | undefined
  last_login_ip?: string | null | undefined
  last_active_at?: string | null | undefined
  created_at?: string | undefined
  updated_at?: string | undefined
  permissions?: string[]
  birthday?: string
}

interface RawUserInfo {
  id: string
  username: string
  nickname: string
  email: string
  level: number
  blog_quality_level?: number
  avatar?: string
  bio?: string
  links?: string[]
  badges?: string[]
  is_active?: boolean
  deletion_status?: string
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

// 登录响应
export interface LoginResponse {
  token?: string
  access_token?: string
  refresh_token?: string
  userInfo?: RawUserInfo
  user?: RawUserInfo
}

const normalizeLoginResponse = (raw: LoginResponse) => {
  const token = raw.token || raw.access_token || ''
  const baseUser = raw.userInfo || raw.user
  const userInfo: UserInfo = {
    id: baseUser?.id || '',
    username: baseUser?.username || '',
    nickname: baseUser?.nickname || baseUser?.username || '',
    email: baseUser?.email || '',
    level: baseUser?.level ?? 5,
    blog_quality_level: baseUser?.blog_quality_level ?? 0,
    avatar: baseUser?.avatar,
    bio: baseUser?.bio,
    links: baseUser?.links,
    badges: baseUser?.badges,
    is_active: baseUser?.is_active,
    deletion_status: baseUser?.deletion_status,
    deletion_reason: baseUser?.deletion_reason,
    deletion_expires_at: baseUser?.deletion_expires_at ?? null,
    deleted_at: baseUser?.deleted_at ?? null,
    login_count: baseUser?.login_count,
    last_login_at: baseUser?.last_login_at ?? null,
    last_login_ip: baseUser?.last_login_ip,
    last_active_at: baseUser?.last_active_at ?? null,
    created_at: baseUser?.created_at,
    updated_at: baseUser?.updated_at
  }

  return {
    token,
    refresh_token: raw.refresh_token,
    userInfo
  }
}

// 登录
export const loginApi = (params: LoginParams, config?: RequestConfig) =>
  post<LoginResponse>('/auth/login', params, config).then(normalizeLoginResponse)

// 注册
export const registerApi = (params: RegisterParams, config?: RequestConfig) =>
  post<LoginResponse>('/auth/register', params, config).then(normalizeLoginResponse)

// 刷新 access token
export const refreshTokenApi = (refresh_token: string, config?: RequestConfig) =>
  post<LoginResponse>('/auth/refresh', { refresh_token }, config).then((raw) => ({
    access_token: raw.access_token || raw.token || ''
  }))

// 登出
export const logoutApi = (config?: RequestConfig) => post<void>('/auth/logout', undefined, config)

// 获取当前用户信息
export const getUserInfoApi = (config?: RequestConfig) =>
  get<Record<string, any>>('/auth/me', undefined, config).then((raw) => {
    const base: UserInfo = {
      id: String(raw.id || ''),
      username: String(raw.username || ''),
      nickname: String(raw.nickname || raw.username || ''),
      email: String(raw.email || ''),
      level: raw.level ?? 5,
      blog_quality_level: raw.blog_quality_level ?? 0,
      avatar: raw.avatar as string | undefined,
      bio: raw.bio as string | undefined,
      links: raw.links as string[] | undefined,
      badges: raw.badges as string[] | undefined,
      is_active: raw.is_active as boolean | undefined,
      deletion_status: raw.deletion_status as string | undefined,
      deletion_reason: raw.deletion_reason as string | undefined,
      deletion_expires_at: raw.deletion_expires_at as string | null | undefined,
      deleted_at: raw.deleted_at as string | null | undefined,
      login_count: raw.login_count as number | undefined,
      last_login_at: raw.last_login_at as string | null | undefined,
      last_login_ip: raw.last_login_ip as string | undefined,
      last_active_at: raw.last_active_at as string | null | undefined,
      created_at: raw.created_at as string | undefined,
      updated_at: raw.updated_at as string | undefined
    }
    return base
  })

// ── 用户管理统计（P0） ──

export interface UserStats {
  total_users: number
  active_users: number
  disabled_users: number
  today_new: number
  by_level: Record<string, number>
  daily_trend: { date: string; count: number }[]
}

export const getUserStatsApi = (config?: RequestConfig) =>
  get<UserStats>('/auth/stats', undefined, config)
