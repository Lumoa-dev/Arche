import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
  AxiosError,
  CanceledError
} from 'axios'
import { $message } from '@/lib/utils/message'
import { AUTH_UNAUTHORIZED_EVENT } from '@/lib/constants/auth'

// 响应数据格式定义，和后端约定
export interface ResponseData<T = any> {
  code: number | string
  message: string
  data: T
  success: boolean
}

export interface RequestOptions {
  silent?: boolean
  dedupe?: boolean
  dedupeKey?: string
  skipAuthLogout?: boolean
}

export type RequestConfig = AxiosRequestConfig & RequestOptions

interface RequestInternalConfig extends InternalAxiosRequestConfig {
  requestOptions?: RequestOptions
  dedupeKey?: string
}

// 创建axios实例
const service: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000, // 请求超时时间
  headers: {
    'Content-Type': 'application/json;charset=utf-8'
  }
})

// --- refresh_token 自动续期 ---
let isRefreshing = false
// eslint-disable-next-line no-unused-vars
let failedQueue: Array<{ resolve: (t: string) => void; reject: (e: unknown) => void }> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else if (token) {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

const refreshAccessTokenDirect = async (): Promise<string | null> => {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return null
  try {
    const baseURL = import.meta.env.VITE_API_BASE_URL || ''
    const refreshAxios = axios.create({ baseURL, timeout: 10000 })
    const res = await refreshAxios.post<ResponseData<{ access_token: string }>>(
      '/api/auth/refresh',
      { refresh_token: refreshToken }
    )
    const data = res.data
    if (data.code === 200 || data.code === 'ok') {
      const newToken = data.data?.access_token
      if (newToken) {
        localStorage.setItem('token', newToken)
        return newToken
      }
    }
    return null
  } catch {
    return null
  }
}

const clearAuthStorage = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('userInfo')
}

const notifyUnauthorized = () => {
  window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT))
}

const pendingControllers = new Map<string, AbortController>()

const getRequestKey = (config: RequestInternalConfig) => {
  if (config.requestOptions?.dedupeKey) {
    return config.requestOptions.dedupeKey
  }
  const method = (config.method || 'get').toUpperCase()
  const url = config.url || ''
  const params = config.params ? JSON.stringify(config.params) : ''
  const data =
    typeof config.data === 'string' ? config.data : config.data ? JSON.stringify(config.data) : ''
  return `${method}:${url}:${params}:${data}`
}

const shouldEnableDedupe = (config: RequestInternalConfig) => {
  if (typeof config.requestOptions?.dedupe === 'boolean') {
    return config.requestOptions.dedupe
  }
  const method = (config.method || 'get').toLowerCase()
  return ['post', 'put', 'patch', 'delete'].includes(method)
}

const removePendingController = (config?: RequestInternalConfig) => {
  const dedupeKey = config?.dedupeKey
  if (dedupeKey && pendingControllers.has(dedupeKey)) {
    pendingControllers.delete(dedupeKey)
  }
}

export const cancelAllPendingRequests = (reason = '路由切换，取消未完成请求') => {
  pendingControllers.forEach((controller) => {
    controller.abort(reason)
  })
  pendingControllers.clear()
}

// 请求拦截器
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const requestConfig = config as RequestInternalConfig

    // 在发送请求之前做些什么
    // 从localStorage获取token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    if (shouldEnableDedupe(requestConfig)) {
      const dedupeKey = getRequestKey(requestConfig)
      requestConfig.dedupeKey = dedupeKey

      const previousController = pendingControllers.get(dedupeKey)
      if (previousController) {
        previousController.abort('重复请求已取消')
      }

      const controller = new AbortController()
      requestConfig.signal = controller.signal
      pendingControllers.set(dedupeKey, controller)
    }

    return requestConfig
  },
  (error: unknown) => {
    // 对请求错误做些什么
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response: AxiosResponse<ResponseData>) => {
    const config = response.config as RequestInternalConfig
    removePendingController(config)

    const res = response.data
    // 后端可能返回 code: 200 或 code: "ok"（插件路由常用字符串）
    const isOk = res.code === 200 || res.code === 'ok' || res.success === true
    if (!isOk) {
      if (!config.requestOptions?.silent) {
        $message.error(res.message || '请求失败')
      }

      // 401: 未登录或token过期
      if (res.code === 401) {
        clearAuthStorage()
        notifyUnauthorized()
      }

      // 403: 权限不足
      if (res.code === 403 && !config.requestOptions?.silent) {
        $message.error('权限不足，无法访问')
      }

      return Promise.reject(new Error(res.message || '请求失败'))
    } else {
      const data = res.data
      if (data && typeof data === 'object' && 'items' in data) {
        ;(data as Record<string, unknown>).list = (data as Record<string, unknown>).items
      }
      return data
    }
  },
  async (error: unknown) => {
    const axiosError = error as AxiosError
    const config = axiosError.config as RequestInternalConfig | undefined
    removePendingController(config)

    if (error instanceof CanceledError || axios.isCancel(error)) {
      return Promise.reject(error)
    }

    // 401/timeout/无响应 是预期行为（后端未就绪或 token 过期），不刷 error 级别
    const isExpected =
      !axiosError.response ||
      axiosError.response?.status === 401 ||
      axiosError.code === 'ECONNABORTED'
    if (isExpected) {
      console.warn('Request warning:', axiosError.message || error)
    } else {
      console.error('Response error:', error)
    }
    let errorMessage = '网络错误，请稍后重试'

    if (axiosError.response) {
      switch (axiosError.response.status) {
        case 400:
          errorMessage = '请求参数错误'
          break
        case 401:
          // 跳过自身 refresh 请求的刷新逻辑，避免无限循环
          if (config?.url?.includes('/auth/refresh')) {
            clearAuthStorage()
            notifyUnauthorized()
            break
          }
          if (config && !config.requestOptions?.skipAuthLogout) {
            // 尝试用 refresh_token 续期
            if (!isRefreshing) {
              isRefreshing = true
              const newToken = await refreshAccessTokenDirect()
              isRefreshing = false
              if (newToken && config) {
                processQueue(null, newToken)
                // 用新 token 重试原始请求
                config.headers.Authorization = `Bearer ${newToken}`
                return service(config)
              }
              // 刷新失败，清空状态
              processQueue(new Error('刷新 token 失败'), null)
              clearAuthStorage()
              notifyUnauthorized()
            } else {
              // 已有刷新请求进行中，将当前请求入队等待
              return new Promise((resolve, reject) => {
                failedQueue.push({
                  resolve: (token: string) => {
                    if (config) {
                      config.headers.Authorization = `Bearer ${token}`
                      resolve(service(config))
                    } else {
                      reject(new Error('配置丢失'))
                    }
                  },
                  reject
                })
              })
            }
          }
          errorMessage = '未登录或登录已过期，请重新登录'
          break
        case 403:
          errorMessage = '权限不足，无法访问'
          break
        case 404:
          errorMessage = '请求的资源不存在'
          break
        case 500:
          errorMessage = '服务器内部错误'
          break
        case 422: {
          const data = axiosError.response.data as Record<string, unknown> | undefined
          if (data?.message && typeof data.message === 'string') {
            errorMessage = data.message
          } else if (data?.detail && Array.isArray(data.detail)) {
            const detailMessages = (data.detail as Array<Record<string, unknown>>).map((item) => {
              const loc = (item.loc as string[]) ?? []
              const field = loc.length > 1 ? loc[loc.length - 1] : (loc[0] ?? '')
              const msg = (item.msg as string) ?? '校验失败'
              return field ? `${field}: ${msg}` : msg
            })
            errorMessage = detailMessages.join('；')
          } else {
            errorMessage = '请求参数校验失败'
          }
          break
        }
        default:
          errorMessage = `请求错误 ${axiosError.response.status}`
      }
    } else if (axiosError.request) {
      errorMessage = '网络连接异常，请检查网络设置'
    }

    if (!config?.requestOptions?.silent) {
      $message.error(errorMessage)
    }
    return Promise.reject(error)
  }
)

// 封装请求方法
const request = <T = any>(config: RequestConfig): Promise<T> => {
  const { silent, dedupe, dedupeKey, skipAuthLogout, ...axiosConfig } = config
  return service.request<any, T>({
    ...axiosConfig,
    requestOptions: {
      silent,
      dedupe,
      dedupeKey,
      skipAuthLogout
    }
  } as RequestInternalConfig)
}

// 封装常用方法
export const get = <T = any>(url: string, params?: any, config?: RequestConfig): Promise<T> => {
  return request<T>({
    method: 'get',
    url,
    params,
    ...config
  })
}

export const post = <T = any>(url: string, data?: any, config?: RequestConfig): Promise<T> => {
  return request<T>({
    method: 'post',
    url,
    data,
    ...config
  })
}

export const put = <T = any>(url: string, data?: any, config?: RequestConfig): Promise<T> => {
  return request<T>({
    method: 'put',
    url,
    data,
    ...config
  })
}

export const del = <T = any>(url: string, params?: any, config?: RequestConfig): Promise<T> => {
  return request<T>({
    method: 'delete',
    url,
    params,
    ...config
  })
}

// 上传文件方法
export const upload = <T = any>(url: string, file: File, config?: RequestConfig): Promise<T> => {
  const formData = new FormData()
  formData.append('file', file)

  return request<T>({
    method: 'post',
    url,
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    ...config
  })
}

export default request
