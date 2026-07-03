import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('requestLog API', () => {
  it('queryRequestLogsApi 发送正确 URL 和参数', async () => {
    const { queryRequestLogsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })

    await queryRequestLogsApi({ ip: '192.168.1.1', action: 'login', page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/query',
      { ip: '192.168.1.1', action: 'login', page: 1, page_size: 20 },
      undefined
    )
  })

  it('queryRequestLogsApi 无参数时只传空对象', async () => {
    const { queryRequestLogsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })

    await queryRequestLogsApi({})
    expect(get).toHaveBeenCalledWith('/request-log/query', {}, undefined)
  })

  it('getTopIpsApi 发送正确 URL', async () => {
    const { getTopIpsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ ip: '192.168.1.1', count: 100 }])

    await getTopIpsApi({ action: 'login', days: 7, limit: 10 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/top-ips',
      { action: 'login', days: 7, limit: 10 },
      undefined
    )
  })

  it('getTopIpsApi 无参数时传 undefined', async () => {
    const { getTopIpsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([])

    await getTopIpsApi(undefined)
    expect(get).toHaveBeenCalledWith('/request-log/top-ips', undefined, undefined)
  })

  it('getTrendApi 发送正确 URL', async () => {
    const { getTrendApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ date: '2026-07-01', count: 50 }])

    await getTrendApi({ action: 'login', days: 30 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/trend',
      { action: 'login', days: 30 },
      undefined
    )
  })

  it('getCountersApi 发送正确 URL', async () => {
    const { getCountersApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })

    await getCountersApi({ ip: '10.0.0.1', page: 1 })
    expect(get).toHaveBeenCalledWith(
      '/request-log/counters',
      { ip: '10.0.0.1', page: 1 },
      undefined
    )
  })

  it('listActionsApi 发送正确 URL', async () => {
    const { listActionsApi } = await import('@/lib/services/api/requestLog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue(['login', 'logout', 'create'])

    await listActionsApi()
    expect(get).toHaveBeenCalledWith('/request-log/actions', undefined, undefined)
  })
})