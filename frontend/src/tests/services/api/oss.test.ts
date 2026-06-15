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

describe('oss API', () => {
  it('getMyOssFilesApi 解包 data.files', async () => {
    const { getMyOssFilesApi } = await import('@/lib/services/api/oss')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ data: { files: [{ id: 'f1' }], total: 1 } })
    const result = await getMyOssFilesApi({ limit: 10 })
    expect(get).toHaveBeenCalledWith('/oss/my', { limit: 10 }, undefined)
    expect(result.list).toHaveLength(1)
    expect(result.total).toBe(1)
  })

  it('deleteOssFileApi 拼接 fileId', async () => {
    const { deleteOssFileApi } = await import('@/lib/services/api/oss')
    const { del } = await import('@/lib/services/request')
    vi.mocked(del).mockResolvedValue(undefined)
    await deleteOssFileApi('f1')
    expect(del).toHaveBeenCalledWith('/oss/files/f1', undefined, undefined)
  })

  it('getOssAdminStatsApi', async () => {
    const { getOssAdminStatsApi } = await import('@/lib/services/api/oss')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total_files: 100 })
    await getOssAdminStatsApi()
    expect(get).toHaveBeenCalledWith('/oss/admin/stats', undefined, undefined)
  })

  it('updateOssUserQuotaApi 拼接 userId', async () => {
    const { updateOssUserQuotaApi } = await import('@/lib/services/api/oss')
    const { put } = await import('@/lib/services/request')
    vi.mocked(put).mockResolvedValue({ user_id: 'u1', quota_bytes: 1000 })
    await updateOssUserQuotaApi('u1', { quota_bytes: 1000 })
    expect(put).toHaveBeenCalledWith('/oss/admin/quotas/u1', { quota_bytes: 1000 }, undefined)
  })

  it('getOssRateLimitApi', async () => {
    const { getOssRateLimitApi } = await import('@/lib/services/api/oss')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ global_limit_bytes: 10000 })
    await getOssRateLimitApi()
    expect(get).toHaveBeenCalledWith('/oss/admin/rate-limit', undefined, undefined)
  })
})
