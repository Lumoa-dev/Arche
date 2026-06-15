import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('system API', () => {
  it('getSystemSummaryApi 发送正确 URL', async () => {
    const { getSystemSummaryApi } = await import('@/lib/services/api/system')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ cpu_percent: 50, memory_percent: 60, disk_percent: 70 })

    await getSystemSummaryApi()
    expect(get).toHaveBeenCalledWith('/system/summary', undefined, undefined)
  })

  it('getProcessesApi 提取 items 并返回数组', async () => {
    const { getProcessesApi } = await import('@/lib/services/api/system')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({
      items: [{ pid: 1, name: 'test', cpu_percent: 10, memory_percent: 20 }],
      total: 1,
      limit: 50
    })

    const result = await getProcessesApi({ limit: 50 })
    expect(result).toHaveLength(1)
    expect(result[0]?.pid).toBe(1)
    expect(get).toHaveBeenCalledWith('/system/processes', { limit: 50 }, undefined)
  })

  it('getCpuMetricsApi 发送正确 URL', async () => {
    const { getCpuMetricsApi } = await import('@/lib/services/api/system')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([])

    await getCpuMetricsApi()
    expect(get).toHaveBeenCalledWith('/system/cpu', undefined, undefined)
  })

  it('getMemoryMetricsApi 发送正确 URL', async () => {
    const { getMemoryMetricsApi } = await import('@/lib/services/api/system')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([])

    await getMemoryMetricsApi()
    expect(get).toHaveBeenCalledWith('/system/memory', undefined, undefined)
  })
})
