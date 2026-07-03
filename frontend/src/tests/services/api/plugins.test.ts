import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('plugins API', () => {
  it('getMonitorTemplatesApi 发送正确 URL', async () => {
    const { getMonitorTemplatesApi } = await import('@/lib/services/api/plugins')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ id: 'cpu', name: 'CPU Dashboard' }])

    await getMonitorTemplatesApi()
    expect(get).toHaveBeenCalledWith('/monitor/templates', undefined, undefined)
  })

  it('getPluginLikeListApi 发送正确 URL', async () => {
    const { getPluginLikeListApi } = await import('@/lib/services/api/plugins')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ list: [], total: 0 })

    await getPluginLikeListApi({ page: 1, page_size: 10 })
    expect(get).toHaveBeenCalledWith('/assets', { page: 1, page_size: 10 }, undefined)
  })

  it('getPluginLikeListApi 无参数时传 undefined', async () => {
    const { getPluginLikeListApi } = await import('@/lib/services/api/plugins')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ list: [], total: 0 })

    await getPluginLikeListApi(undefined)
    expect(get).toHaveBeenCalledWith('/assets', undefined, undefined)
  })
})