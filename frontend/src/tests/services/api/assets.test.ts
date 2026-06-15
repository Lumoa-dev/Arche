import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('assets API', () => {
  it('getAssetsApi 发送正确 URL', async () => {
    const { getAssetsApi } = await import('@/lib/services/api/assets')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })

    await getAssetsApi({ page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith('/assets', { page: 1, page_size: 20 }, undefined)
  })

  it('getAssetStatsApi 发送正确 URL', async () => {
    const { getAssetStatsApi } = await import('@/lib/services/api/assets')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 10, by_type: {} })

    await getAssetStatsApi()
    expect(get).toHaveBeenCalledWith('/assets/stats', undefined, undefined)
  })
})
