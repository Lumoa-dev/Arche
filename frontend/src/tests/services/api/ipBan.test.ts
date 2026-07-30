import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ipBan API', () => {
  it('getIpBansApi 调用 GET /ip-ban/bans', async () => {
    const { getIpBansApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get).mockResolvedValue({ list: [], total: 0, page: 1, page_size: 20 })

    const result = await getIpBansApi({ page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith('/ip-ban/bans', { page: 1, page_size: 20 }, undefined)
    expect(result.list).toEqual([])
  })

  it('getIpBansApi 传递过滤参数', async () => {
    const { getIpBansApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get).mockResolvedValue({ list: [], total: 0, page: 1, page_size: 20 })

    await getIpBansApi({ ban_type: 'auto', is_active: 'true', keyword: '192.168' })
    expect(get).toHaveBeenCalledWith(
      '/ip-ban/bans',
      { ban_type: 'auto', is_active: 'true', keyword: '192.168' },
      undefined
    )
  })

  it('banIpApi 调用 POST /ip-ban/bans', async () => {
    const { banIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')

    vi.mocked(post).mockResolvedValue({
      id: 1,
      ip_or_cidr: '192.168.1.1',
      ban_type: 'manual',
      reason: 'test',
      is_active: true
    })

    const result = await banIpApi({ ip_or_cidr: '192.168.1.1', reason: 'test' })
    expect(post).toHaveBeenCalledWith('/ip-ban/bans', { ip_or_cidr: '192.168.1.1', reason: 'test' }, undefined)
    expect(result.ip_or_cidr).toBe('192.168.1.1')
  })

  it('batchUnbanApi 调用 POST /ip-ban/bans/batch-unban', async () => {
    const { batchUnbanApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')

    vi.mocked(post).mockResolvedValue({ count: 2 })

    const result = await batchUnbanApi({ ban_ids: [1, 2] })
    expect(post).toHaveBeenCalledWith('/ip-ban/bans/batch-unban', { ban_ids: [1, 2] }, undefined)
    expect(result.count).toBe(2)
  })

  it('unbanIpApi 拼接 banId 到路径', async () => {
    const { unbanIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')

    vi.mocked(post).mockResolvedValue({ id: 1, is_active: false })

    await unbanIpApi(1)
    expect(post).toHaveBeenCalledWith('/ip-ban/bans/1/unban', undefined, undefined)
  })

  it('getBanLogsApi 调用 GET /ip-ban/logs', async () => {
    const { getBanLogsApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get).mockResolvedValue({ list: [], total: 0, page: 1, page_size: 20 })

    await getBanLogsApi({ page: 1, action: 'ban' })
    expect(get).toHaveBeenCalledWith('/ip-ban/logs', { page: 1, action: 'ban' }, undefined)
  })

  it('getBanRulesApi 调用 GET /ip-ban/rules', async () => {
    const { getBanRulesApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get).mockResolvedValue([{ id: 'login_failure', name: 'Login Failure', enabled: true }])

    const result = await getBanRulesApi()
    expect(get).toHaveBeenCalledWith('/ip-ban/rules', undefined, undefined)
    expect(result).toHaveLength(1)
  })

  it('updateBanRuleApi 调用 PUT /ip-ban/rules/:ruleId', async () => {
    const { updateBanRuleApi } = await import('@/lib/services/api/ipBan')
    const { put } = await import('@/lib/services/request')

    vi.mocked(put).mockResolvedValue({ id: 'login_failure', enabled: false })

    await updateBanRuleApi('login_failure', { enabled: false })
    expect(put).toHaveBeenCalledWith('/ip-ban/rules/login_failure', { enabled: false }, undefined)
  })

  it('getIpBanStatsApi 调用 GET /ip-ban/stats', async () => {
    const { getIpBanStatsApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get).mockResolvedValue({ total_bans: 10, active_bans: 5, auto_bans: 3, manual_bans: 2, today_bans: 1 })

    const result = await getIpBanStatsApi()
    expect(get).toHaveBeenCalledWith('/ip-ban/stats', undefined, undefined)
    expect(result.total_bans).toBe(10)
  })
})