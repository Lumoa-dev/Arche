import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('requestLog API', () => {
  it('queryRequestLogsApi 查询日志', async () => {
    const { queryRequestLogsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 1, page: 1, page_size: 20, items: [] })
    await queryRequestLogsApi({ ip: '10.0.0.1', page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/query',
      { ip: '10.0.0.1', page: 1, page_size: 20 },
      undefined
    )
  })

  it('getTopIpsApi 获取 TOP IP', async () => {
    const { getTopIpsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ ip: '10.0.0.1', count: 100 }])
    await getTopIpsApi({ days: 7, limit: 10 })
    expect(get).toHaveBeenCalledWith('/request-log/top-ips', { days: 7, limit: 10 }, undefined)
  })

  it('getTrendApi 获取趋势数据', async () => {
    const { getTrendApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ date: '2024-01-01', count: 10 }])
    await getTrendApi({ days: 30 })
    expect(get).toHaveBeenCalledWith('/request-log/trend', { days: 30 }, undefined)
  })

  it('getCountersApi 获取聚合计数', async () => {
    const { getCountersApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 1, page: 1, page_size: 20, items: [] })
    await getCountersApi({ ip: '10.0.0.1', action: 'api_call' })
    expect(get).toHaveBeenCalledWith(
      '/request-log/counters',
      { ip: '10.0.0.1', action: 'api_call' },
      undefined
    )
  })

  it('listActionsApi 获取行为分类列表', async () => {
    const { listActionsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue(['api_call', 'login_fail'])
    const result = await listActionsApi()
    expect(get).toHaveBeenCalledWith('/request-log/actions', undefined, undefined)
    expect(result).toContain('api_call')
  })
})