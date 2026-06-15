import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({ get: vi.fn() }))
beforeEach(() => {
  vi.clearAllMocks()
})

describe('plugins API', () => {
  it('getMonitorTemplatesApi', async () => {
    const { getMonitorTemplatesApi } = await import('@/lib/services/api/plugins')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([])
    await getMonitorTemplatesApi()
    expect(get).toHaveBeenCalledWith('/monitor/templates', undefined, undefined)
  })

  it('getPluginLikeListApi', async () => {
    const { getPluginLikeListApi } = await import('@/lib/services/api/plugins')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })
    await getPluginLikeListApi({ page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith('/assets', { page: 1, page_size: 20 }, undefined)
  })
})
