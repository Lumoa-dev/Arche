import { get, post, type RequestConfig } from '../request'

export interface GithubProxyHealth {
  status: string
  mode?: string
}

export const getGithubProxyHealthApi = (config?: RequestConfig) =>
  get<GithubProxyHealth>('/github/health/status', undefined, config)

export const clearGithubProxyCacheApi = (config?: RequestConfig) =>
  post<void>('/github/cache/clear', undefined, config)

export const proxyGithubRawApi = (
  path: string,
  mode: 'auto' | 'http' | 'cli' = 'auto',
  config?: RequestConfig
) => get<string>(`/github/raw/${path}`, { mode }, config)
