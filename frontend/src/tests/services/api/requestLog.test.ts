import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('requestLog API', () => {
  it('queryRequestLogsApi 传递查询参数', async () => {
    const { queryRequestLogsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 0, page: 1, page_size: 20, items: [] })
    await queryRequestLogsApi({ ip: '10.0.0.1', action: 'api_call', page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/query',
      { ip: '10.0.0.1', action: 'api_call', page: 1, page_size: 20 },
      undefined
    )
  })

  it('getTopIpsApi 传递参数', async () => {
    const { getTopIpsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ ip: '10.0.0.1', count: 100 }])
    const result = await getTopIpsApi({ action: 'api_call', days: 7, limit: 10 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/top-ips',
      { action: 'api_call', days: 7, limit: 10 },
      undefined
    )
    expect(result).toHaveLength(1)
    expect(result[0].ip).toBe('10.0.0.1')
  })

  it('getTrendApi 传递参数', async () => {
    const { getTrendApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ date: '2026-07-01', count: 50 }])
    const result = await getTrendApi({ action: 'login_fail', days: 7 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/trend',
      { action: 'login_fail', days: 7 },
      undefined
    )
    expect(result[0].count).toBe(50)
  })

  it('getCountersApi 传递查询参数', async () => {
    const { getCountersApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 0, page: 1, page_size: 20, items: [] })
    await getCountersApi({ ip: '10.0.0.1', page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/counters',
      { ip: '10.0.0.1', page: 1, page_size: 20 },
      undefined
    )
  })

  it('listActionsApi 获取行为分类列表', async () => {
    const { listActionsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue(['api_call', 'login_fail', 'page_view'])
    const result = await listActionsApi()
    expect(get).toHaveBeenCalledWith('/request-log/actions', undefined, undefined)
    expect(result).toContain('api_call')
    expect(result).toContain('login_fail')
  })
})