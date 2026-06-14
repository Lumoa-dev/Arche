import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import { $message } from '@/lib/utils/message'

export { blogMockData } from './blog'
export { authMockData } from './auth'

const BACKEND_HEALTH_KEY = 'arche:backend_alive'
const HEALTH_CHECK_INTERVAL_MS = 30000

let healthTimer: ReturnType<typeof setInterval> | null = null

const healthCache = {
  get isAlive(): boolean | null {
    const raw = sessionStorage.getItem(BACKEND_HEALTH_KEY)
    if (raw === null) return null
    return raw === 'true'
  },
  set alive(v: boolean) {
    sessionStorage.setItem(BACKEND_HEALTH_KEY, String(v))
  },
  clear() {
    sessionStorage.removeItem(BACKEND_HEALTH_KEY)
  }
}

export const checkBackendHealth = async (): Promise<boolean> => {
  try {
    await axios.get('/api/health', { timeout: 3000 } as AxiosRequestConfig)
    const wasDown = healthCache.isAlive === false
    healthCache.alive = true
    if (wasDown) {
      $message.success('后端服务已恢复，正在使用实时数据')
    }
    return true
  } catch {
    const wasUp = healthCache.isAlive !== false
    healthCache.alive = false
    if (wasUp) {
      $message.warning('后端服务暂不可用，已切换至演示数据')
    }
    return false
  }
}

export const isBackendAlive = (): boolean | null => healthCache.isAlive

export const resetBackendHealth = () => {
  healthCache.clear()
}

export const startHealthMonitor = () => {
  stopHealthMonitor()
  if (healthCache.isAlive !== false) return
  healthTimer = setInterval(() => {
    void checkBackendHealth()
  }, HEALTH_CHECK_INTERVAL_MS)
}

export const stopHealthMonitor = () => {
  if (healthTimer !== null) {
    clearInterval(healthTimer)
    healthTimer = null
  }
}

const isNetworkError = (error: unknown): boolean => {
  if (error instanceof AxiosError) {
    if (!error.response) return true
    if (error.code === 'ECONNABORTED') return true
  }
  return false
}

export interface WithFallbackOptions {
  silent?: boolean
  fallbackMessage?: string
}

export async function withFallback<T>(
  apiCall: () => Promise<T>,
  mockData: T,
  options: WithFallbackOptions = {}
): Promise<T> {
  try {
    const result = await apiCall()
    healthCache.alive = true
    return result
  } catch (error: unknown) {
    if (isNetworkError(error)) {
      healthCache.alive = false
      if (!options.silent) {
        $message.warning(options.fallbackMessage || '后端暂不可用，已展示演示数据')
      }
      startHealthMonitor()
      return mockData
    }
    throw error
  }
}
