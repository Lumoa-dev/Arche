import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({ get: vi.fn() }))
beforeEach(() => {
  vi.clearAllMocks()
})

describe('requestLog API', () => {
  it('queryRequestLogsApi', async () => {
    const { queryRequestLogsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 1, page: 1, page_size: 20, items: [] })
    await queryRequestLogsApi({ ip: '192.168.1.1', page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/query',
      { ip: '192.168.1.1', page: 1, page_size: 20 },
      undefined
    )
  })

  it('queryRequestLogsApi with filters', async () => {
    const { queryRequestLogsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 1, page: 1, page_size: 20, items: [] })
    await queryRequestLogsApi({ action: 'api_call', start_date: '2026-01-01', end_date: '2026-01-31' })
    expect(get).toHaveBeenCalledWith(
      '/request-log/query',
      { action: 'api_call', start_date: '2026-01-01', end_date: '2026-01-31' },
      undefined
    )
  })

  it('getTopIpsApi', async () => {
    const { getTopIpsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ ip: '192.168.1.1', count: 100 }])
    await getTopIpsApi({ action: 'api_call', days: 7, limit: 10 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/top-ips',
      { action: 'api_call', days: 7, limit: 10 },
      undefined
    )
  })

  it('getTopIpsApi without params', async () => {
    const { getTopIpsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([])
    await getTopIpsApi()
    expect(get).toHaveBeenCalledWith('/request-log/top-ips', undefined, undefined)
  })

  it('getTrendApi', async () => {
    const { getTrendApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ date: '2026-01-01', count: 50 }])
    await getTrendApi({ action: 'page_view', days: 30 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/trend',
      { action: 'page_view', days: 30 },
      undefined
    )
  })

  it('getTrendApi without params', async () => {
    const { getTrendApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([])
    await getTrendApi()
    expect(get).toHaveBeenCalledWith('/request-log/trend', undefined, undefined)
  })

  it('getCountersApi', async () => {
    const { getCountersApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 1, page: 1, page_size: 20, items: [] })
    await getCountersApi({ ip: '10.0.0.1', page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/counters',
      { ip: '10.0.0.1', page: 1, page_size: 20 },
      undefined
    )
  })

  it('listActionsApi', async () => {
    const { listActionsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue(['api_call', 'page_view', 'login_fail'])
    await listActionsApi()
    expect(get).toHaveBeenCalledWith('/request-log/actions', undefined, undefined)
  })
})